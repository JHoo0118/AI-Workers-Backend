import os
import json
import shutil

from dotenv import load_dotenv
from operator import itemgetter
from typing import AsyncGenerator
from fastapi import HTTPException, UploadFile, status
from upstash_redis import Redis
from langchain_community.chat_message_histories.upstash_redis import (
    UpstashRedisChatMessageHistory,
)
from langchain.storage import LocalFileStore
from langchain_community.document_loaders import UnstructuredFileLoader
from langchain.embeddings import CacheBackedEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain.storage.upstash_redis import UpstashRedisByteStore
from langchain.text_splitter import CharacterTextSplitter
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from langchain.schema import messages_to_dict, messages_from_dict
from langchain.memory import ConversationSummaryBufferMemory
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores.supabase import SupabaseVectorStore
from app.db.supabase import SupabaseService
from app.db.prisma import prisma
from app.const import *
from app.service.file.file_service import FileService


load_dotenv()
PREFIX = "docs-summary"
UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")
redis_client = Redis(url=UPSTASH_REDIS_REST_URL, token=UPSTASH_REDIS_REST_TOKEN)
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You're a master of document summarization.
            IMPORTANT: Answer the question ONLY the following context. If you don't know the answer just say you don't know. DON'T make anything up.
            Context: {context}

            And you will get about summaried context of previous chat. If it's empty you don't have to care
            Previous-chat-context: {chat_history}
            IMPORTATNT: Please do all the answers in Korean.
            """,
        ),
        ("human", "{question}"),
    ]
)

splitter = CharacterTextSplitter.from_tiktoken_encoder(
    separator="\n",
    chunk_size=600,
    chunk_overlap=100,
)

embeddings = OpenAIEmbeddings()


class AIDocsService(object):
    _instance = None
    _memory_llm: ChatOpenAI
    _memory: ConversationSummaryBufferMemory
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
        super().__init__(*args, **kwargs)
        self._supabaseService = SupabaseService()
        self._fileService = FileService()

        history = UpstashRedisChatMessageHistory(
            url=UPSTASH_REDIS_REST_URL,
            token=UPSTASH_REDIS_REST_TOKEN,
            session_id=email,
            ttl=60 * 60 * 2,
            key_prefix=f"{PREFIX}-{email}",
        )
        self._memory_llm = ChatOpenAI(
            temperature=0.1,
            model="gpt-4-0125-preview",
        )

        self._memory = ConversationSummaryBufferMemory(
            llm=self._memory_llm,
            max_token_limit=120,
            memory_key="chat_history",
            return_messages=True,
            chat_memory=history,
        )

        os.makedirs(self._tmp_dir, exist_ok=True)
        os.makedirs(self._tmp_usage_dir, exist_ok=True)

    def __init_path(self, email: str):
        os.makedirs(f"./.cache/docs/embeddings/{email}", exist_ok=True)
        os.makedirs(f"{self._tmp_usage_dir}/{email}/docs", exist_ok=True)

    def load_json(self, path):
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            return json.load(f)

    def save_message(self, input, output):
        self._memory.save_context(inputs={"input": input}, outputs={"output": output})

    def get_history(self):
        return self._memory.load_memory_variables({})

    def format_docs(self, docs):
        return "\n\n".join(doc.page_content for doc in docs)

    def get_supabase_output_file_path(self, email: str, filename: str):
        return f"{self._base_output_dir}/{email}/docs/{filename}"

    def get_tmp_output_file_path(self, filename: str):
        return f"{self._tmp_dir}/{filename}"

    def embed_file(
        self,
        email: str,
        file: UploadFile,
        ip: str,
        jwt: str,
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
            self._memory.clear()

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
            # shutil.move(f"{tmp_output_file_path}", tmp_usage_file_path)
            self._fileService.delete_file(tmp_output_file_path)

            return self.get_retriever(email=email, filename=filename, ip=ip)
        except Exception as e:
            self._fileService.delete_file(tmp_output_file_path)
            self._fileService.delete_file(tmp_usage_file_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문서 요약 중 오류가 발생했습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def get_retriever(self, email: str, filename: str, ip: str):

        file = prisma.file.find_first_or_raise(
            order={
                "uploadDate": "desc",
            },
            where={"userEmail": email, "originFilename": filename},
        )

        # if file is None:
        #     raise HTTPException(
        #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #         detail="문서 요약 중 오류가 발생했습니다.",
        #         headers={"WWW-Authenticate": "Bearer"},
        #     )

        pFilename = file.filename
        try:
            tmp_usage_path = f"{self._tmp_usage_dir}/{email}/docs/{pFilename}"
            self.download_file_from_supabase(
                email=email, tmp_usage_path=tmp_usage_path, filename=pFilename, ip=ip
            )

            # cache_dir = UpstashRedisByteStore(
            #     client=redis_client,
            #     ttl=60 * 60 * 2,
            #     namespace=f"{PREFIX}-{pFilename}-{email}",
            # )

            cache_dir = LocalFileStore(f"./.cache/docs/embeddings/{email}/{pFilename}")
            loader = UnstructuredFileLoader(tmp_usage_path)
            docs = loader.load_and_split(text_splitter=splitter)
            cached_embeddings = CacheBackedEmbeddings.from_bytes_store(
                embeddings, cache_dir
            )

            vectorstore = SupabaseVectorStore.from_documents(
                docs,
                cached_embeddings,
                client=self._supabaseService.supabase,
                table_name="Documents",
                query_name="match_documents",
                chunk_size=500,
            )
            retriever = vectorstore.as_retriever()

            return retriever
        except Exception as e:
            print(e)
            tmp_usage_path = f"{self._tmp_usage_dir}/{email}/docs/{pFilename}"
            self._fileService.delete_file(tmp_usage_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문서 요약 중 오류가 발생했습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )

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

    async def invoke_chain(
        self,
        email: str,
        filename: str,
        message,
        ip: str,
    ) -> AsyncGenerator[str, None]:
        self.__init_path(email=email)
        llm = ChatOpenAI(
            # "gpt-4-0125-preview"
            model="gpt-4-0125-preview",
            temperature=0.1,
            streaming=True,
        )

        # invoke the chain
        parser = StrOutputParser()
        retriever = self.get_retriever(email=email, filename=filename, ip=ip)

        chain = (
            {
                "context": retriever | RunnableLambda(self.format_docs),
                "question": RunnablePassthrough(),
            }
            | RunnablePassthrough.assign(
                chat_history=RunnableLambda(self._memory.load_memory_variables)
                | itemgetter("chat_history")
            )
            | prompt
            | llm
            | parser
        )
        response = ""
        async for token in chain.astream(input=message):
            yield token
            response += token

        self.save_message(input=message, output=response)

    # async def generator(self, chain: RunnableSerializable, message):
    #     for chunk in chain.stream(input=message):
    #         print(chunk, end="|", flush=True)
    #         yield chunk
