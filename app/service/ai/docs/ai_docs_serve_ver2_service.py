import os
import shutil
from collections import defaultdict
from langchain_community.document_loaders.pdf import PyPDFLoader
from dotenv import load_dotenv
from fastapi import HTTPException, UploadFile, status
from langchain.prompts import PromptTemplate
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain_core.vectorstores import VectorStoreRetriever
from app.service.file.file_service import FileService
from langchain.chains.summarize import load_summarize_chain
from langchain.docstore.document import Document
from app.db.prisma import prisma
from app.const import *


from app.db.supabase import SupabaseService


load_dotenv()
PREFIX = "docs-summary"
splitter = CharacterTextSplitter.from_tiktoken_encoder(
    separator="\n",
    chunk_size=800,
    chunk_overlap=200,
)

embeddings = OpenAIEmbeddings()


class AIDocsServeVer2Service(object):
    _instance = None
    _retriever: VectorStoreRetriever
    _callback: AsyncIteratorCallbackHandler
    _supabaseService: SupabaseService
    _fileService: FileService
    _tmp_dir = file_output_dir["tmp"]
    _tmp_usage_dir = file_output_dir["tmp_usage"]
    _base_output_dir = file_output_dir["private_ai"]

    def __new__(class_, email, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)

        return class_._instance

    def __init__(self, email, *args, **kwargs):
        self._supabaseService = SupabaseService()
        self._fileService = FileService()

        os.makedirs(self._tmp_dir, exist_ok=True)
        os.makedirs(self._tmp_usage_dir, exist_ok=True)

    def __init_path(self, email: str):
        os.makedirs(f"./.cache/docs/embeddings/{email}", exist_ok=True)
        os.makedirs(f"{self._tmp_usage_dir}/{email}/docs", exist_ok=True)

    def get_supabase_output_file_path(self, email: str, filename: str):
        return f"{self._base_output_dir}/{email}/docs/{filename}"

    def get_tmp_output_file_path(self, filename: str):
        return f"{self._tmp_dir}/{filename}"

    def download_file_from_supabase(
        self,
        email: str,
        tmp_usage_path: str,
        filename: str,
        ip: str,
    ) -> None:
        if not os.path.exists(tmp_usage_path):
            supabase_file_path = self.get_supabase_output_file_path(email, filename)
            SupabaseService().file_donwload_on_supabase(
                file_path_include_filename=supabase_file_path,
                filename=filename,
                ip=ip,
                tmp_file_path=tmp_usage_path,
            )

        else:
            print(f"File already downloaded. Using cached version at {tmp_usage_path}")

    def extract_text_from_pdf(self, email: str, filename: str, ip: str):
        file = prisma.file.find_first_or_raise(
            order={
                "uploadDate": "desc",
            },
            where={"userEmail": email, "originFilename": filename},
        )

        pFilename = file.filename
        try:
            tmp_usage_path = f"{self._tmp_usage_dir}/{email}/docs/{pFilename}"
            self.download_file_from_supabase(
                email=email, tmp_usage_path=tmp_usage_path, filename=pFilename, ip=ip
            )
            loader = PyPDFLoader(tmp_usage_path)
            # pdf_document = loader.load_and_split()
            pdf_document = loader.load()
            # combined_document = self.combine_duplicate_pages(pdf_document)
            # return combined_document
            return pdf_document
        except Exception as e:
            print(e)
            tmp_usage_path = f"{self._tmp_usage_dir}/{email}/docs/{pFilename}"
            self._fileService.delete_file(tmp_usage_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문서 요약 중 오류가 발생했습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def summarize_text_by_page(self, email: str, file: UploadFile, ip: str, jwt: str):
        pdf_document = self.embed_file(email=email, file=file, ip=ip, jwt=jwt)

        refine_template = (
            "Your job is to produce a final summary\n"
            "We have provided an existing summary up to a certain point: {existing_answer}\n"
            "We have the opportunity to refine the existing summary"
            "(only if needed) with some more context below.\n"
            "------------\n"
            "{text}\n"
            "------------\n"
            """
            You need to make sure that the answer is answered in the following json format.
            [
                {{
                    "page": "0",
                    "summary": Page 0 Summary contents...
                    "keyword": something,
                }},
                {{
                    "page": "1",
                    "summary": Page 1 Summary contents...
                    "keyword": something,
                }},
                {{
                    "page": "2",
                    "summary": Page 2 Summary contents...
                    "keyword": something,
                }},
                {{  "page": "3",
                    "summary": Page 3 Summary contents...
                    "keyword": something,
                }},
                {{  "page": "4",
                    "summary": Page 4 Summary contents...
                    "keyword": something,
                }},
                ...
            ]
            Your turn !
            the answer array length is equal to {total_pages}. so each of the {total_pages} pages must be summarized.
            page is page number. initial page number is 0. this prproperty matched by 'page' property of documents object.
            summary is Summary of that page of document. if page property value is "1", you should only include summary of page "1" of documents"
            keyword: Key Keywords on that page. refer 'page' property.
            """
            "IMPORTANT: Summarize it in Korean."
            "IMPORTANT: I will give you the page number and the document. Please summarize the document by page number."
            "IMPORTANT: If the user doesn't ask you to answer in any language, please generate answer in the language you asked."
        )
        refine_prompt = PromptTemplate.from_template(refine_template)

        llm = ChatOpenAI(model_name="gpt-4o", temperature=0)
        texts = []
        for page_number in range(1, len(pdf_document) + 1):
            view = pdf_document[page_number - 1]
            page_texts = splitter.split_text(view.page_content)
            texts.extend(page_texts)
        docs = [Document(page_content=t) for t in texts]
        chain = load_summarize_chain(
            llm,
            chain_type="refine",
            refine_prompt=refine_prompt,
            return_intermediate_steps=True,
            input_key="input_documents",
            output_key="output_text",
        )
        summary = chain.invoke(
            {"input_documents": docs, "total_pages": len(pdf_document)},
            return_only_outputs=True,
        )

        return summary["output_text"]

    def combine_duplicate_pages(self, pdf_document: list[Document]):
        combined_pages = defaultdict(str)
        page_metadata = {}

        for page in pdf_document:
            page_number = page.metadata["page"]
            combined_pages[page_number] += page.page_content
            page_metadata[page_number] = page.metadata

        sorted_pages = [
            Document(page_content=combined_pages[page], metadata=page_metadata[page])
            for page in sorted(combined_pages.keys())
        ]

        return sorted_pages

    async def summarize_text_by_page_for_stream(self, email: str, path: str, ip: str):
        pdf_document = self.extract_text_from_pdf(email=email, filename=path, ip=ip)

        refine_template = (
            "모든 답변은 한국어로 해주세요."
            "You are the expert who wrote the article. Your job is to produce a final summary and translate into Korean\n"
            "We have provided an existing summary up to a certain point: {existing_answer}\n"
            "We have the opportunity to refine the existing summary"
            "(only if needed) with some more context below.\n"
            "------------\n"
            "{text}\n"
            "------------\n"
            """

            IMPORTANT: Translate into Korean.
            IMPORTANT: I will give you the page number and the document. Please summarize the document by page number.
            IMPORTANT: Be sure to put in the key points and summarize them in detail.
            """
        )
        refine_prompt = PromptTemplate.from_template(refine_template)

        llm = ChatOpenAI(model_name="gpt-4o", temperature=0)
        summaries = []
        page_summaries: dict[str, dict[str, str]] = {}
        for page_index in range(1, len(pdf_document) + 1):
            view = pdf_document[page_index - 1]
            page_number = view.metadata.get("page")
            texts = splitter.split_text(view.page_content)
            docs = [Document(page_content=t) for t in texts]
            chain = load_summarize_chain(
                llm,
                chain_type="refine",
                refine_prompt=refine_prompt,
                return_intermediate_steps=True,
                input_key="input_documents",
                output_key="output_text",
            )
            summary = await chain.ainvoke(
                {"input_documents": docs},
                return_only_outputs=True,
            )
            str_page_number = str(page_number)
            if page_summaries.get(str_page_number):
                page_summaries[str_page_number]["summary"] += (
                    "\n" + summary["output_text"]
                )

            else:
                page_summary = {
                    "page": str_page_number,
                    "summary": summary["output_text"],
                }
                page_summaries[str_page_number] = page_summary

        summaries = [page_summaries[key] for key in sorted(page_summaries)]
        return summaries

    def embed_file(
        self, email: str, file: UploadFile, ip: str, jwt: str, usage_path=False
    ):
        file_content = file.file.read()
        filename = file.filename
        dest = f"{self._tmp_usage_dir}/{email}/docs"
        pFilename = self._fileService.get_converted_filename(
            suffix=PREFIX,
            filename=filename,
        )
        tmp_usage_file_path = f"{dest}/{pFilename}"
        try:
            self.__init_path(email=email)

            tmp_output_file_path = self.get_tmp_output_file_path(filename=pFilename)
            supabase_output_file_path = self.get_supabase_output_file_path(
                email, pFilename
            )

            with open(tmp_output_file_path, "wb") as f:
                f.write(file_content)

            shutil.copyfile(f"{tmp_output_file_path}", tmp_usage_file_path)
            SupabaseService().file_upload_on_supabase_private(
                tmp_file_path=tmp_output_file_path,
                tmp_usage_file_path=tmp_usage_file_path,
                output_file_path=supabase_output_file_path,
                filename=pFilename,
                originFilename=filename,
                email=email,
                jwt=jwt,
            )
            self._fileService.delete_file(tmp_output_file_path)
            if usage_path:
                return filename

            return self.extract_text_from_pdf(email=email, filename=filename, ip=ip)
        except Exception as e:
            self._fileService.delete_file(tmp_output_file_path)
            self._fileService.delete_file(tmp_usage_file_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문서 요약 중 오류가 발생했습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )
