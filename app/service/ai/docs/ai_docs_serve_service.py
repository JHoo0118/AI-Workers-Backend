import os
import json
import shutil

from pyparsing import Any
from typing import Dict, List, TypedDict
from dotenv import load_dotenv
from fastapi import HTTPException, UploadFile, status
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from langchain.output_parsers.openai_tools import PydanticToolsParser
from langchain.prompts import PromptTemplate
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain_core.output_parsers import StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain.storage import LocalFileStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import UnstructuredFileLoader
from langchain.storage.upstash_redis import UpstashRedisByteStore
from langchain_community.vectorstores.supabase import SupabaseVectorStore
from langchain.embeddings import CacheBackedEmbeddings
from langchain.memory import ConversationSummaryBufferMemory
from langchain.text_splitter import CharacterTextSplitter
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_community.vectorstores.supabase import SupabaseVectorStore
from langgraph.graph import END, StateGraph
from langchain_core.messages.base import BaseMessage
from app.service.file.file_service import FileService
from app.db.prisma import prisma
from app.const import *


from app.db.supabase import SupabaseService

# template="""
#                     You're a master of document summarization. You'll sum up all the documents nicely
#                     IMPORTANT: Answer the question ONLY the following context. If you don't know the answer just say you don't know. DON'T make anything up.
#                     IMPORTANT: Please make sure to include important information and summarize it.
#                     IMPORTANT: Do not refer to documents other than those to answer.
#                     Context: {context}
#                     You need to make sure that the answer is answered in the following json format.

#                     {{
#                         1: {{
#                             summary: Page 1 Summary contents...
#                             keyword: something
#                         }},
#                         2: {{
#                             summary: Page 2 Summary contents...
#                             keyword: something
#                         }},
#                         3: {{
#                             summary: Page 3 Summary contents...
#                             keyword: something
#                         }}
#                         ...
#                     }}

#                     1 is page number.
#                     summary is Summary of that page.
#                     keyword: Key Keywords on that page.

#                     IMPORTATNT: If the user doesn't ask you to answer in any language, please generate answer in the language you asked.
#                     """,
#             input_variables=["context"],

load_dotenv()
PREFIX = "docs-summary"
splitter = CharacterTextSplitter.from_tiktoken_encoder(
    separator="\n",
    chunk_size=600,
    chunk_overlap=100,
)

embeddings = OpenAIEmbeddings()


class AIDocsServeService(object):
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

        # history = UpstashRedisChatMessageHistory(
        #     url=UPSTASH_REDIS_REST_URL,
        #     token=UPSTASH_REDIS_REST_TOKEN,
        #     session_id=email,
        #     ttl=0,
        #     key_prefix=f"{PREFIX}-{email}",
        # )
        os.makedirs(self._tmp_dir, exist_ok=True)
        os.makedirs(self._tmp_usage_dir, exist_ok=True)

    def __init_path(self, email: str):
        os.makedirs(f"./.cache/docs/embeddings/{email}", exist_ok=True)
        os.makedirs(f"{self._tmp_usage_dir}/{email}/docs", exist_ok=True)

    def get_supabase_output_file_path(self, email: str, filename: str):
        return f"{self._base_output_dir}/{email}/docs/{filename}"

    def get_tmp_output_file_path(self, filename: str):
        return f"{self._tmp_dir}/{filename}"

    def clean_text(self, text):
        return text.replace('\u0000', '')

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

        pFilename = file.filename
        try:
            tmp_usage_path = f"{self._tmp_usage_dir}/{email}/docs/{pFilename}"
            self.download_file_from_supabase(
                email=email, tmp_usage_path=tmp_usage_path, filename=pFilename, ip=ip
            )

            cache_dir = LocalFileStore(f"./.cache/docs/embeddings/{email}/{pFilename}")
            loader = UnstructuredFileLoader(tmp_usage_path)
            docs = loader.load_and_split(text_splitter=splitter)
            cached_embeddings = CacheBackedEmbeddings.from_bytes_store(
                embeddings, cache_dir
            )

            for doc in docs:
                doc['text'] = self.clean_text(doc['text'])

            vectorstore = SupabaseVectorStore.from_documents(
                docs,
                cached_embeddings,
                client=self._supabaseService.supabase,
                table_name="Documents",
                query_name="match_documents",
                chunk_size=500,
            )
            self._retriever = vectorstore.as_retriever()
            return self._retriever
        except Exception as e:
            print(e)
            tmp_usage_path = f"{self._tmp_usage_dir}/{email}/docs/{pFilename}"
            self._fileService.delete_file(tmp_usage_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문서 요약 중 오류가 발생했습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def format_docs(self, docs):
        return "\n\n".join(doc.page_content for doc in docs)

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

    class GraphState(TypedDict):
        """
        Represents the state of our graph.

        Attributes:
            keys: A dictionary where each key is a string.
        """

        keys: Dict[str, any]

    def generate(self, state):
        """
        Generate answer. If the user doesn't ask you to answer in any language, please generate answer in the language you asked.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, generation, that contains LLM generation
        """
        print("---GENERATE---")
        state_dict = state["keys"]
        question = state_dict["question"]

        # Prompt
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
                    You're a master of document summarization. You'll sum up all the documents nicely.
                    You should summarize whole pages.
                    IMPORTANT: Answer the question ONLY the following context. If you don't know the answer just say you don't know. DON'T make anything up.
                    IMPORTANT: Please make sure to include important information and summarize it.
                    IMPORTANT: Do not refer to documents other than those to answer.
                    Context: {context}
                    You need to make sure that the answer is answered in the following json format.

                    [
                        {{
                            page: "1",
                            summary: Page 1 Summary contents...
                        }},
                        {{
                            page: "2",
                            summary: Page 2 Summary contents...
                        }},
                        {{  page: "3",
                            summary: Page 3 Summary contents...
                        }}
                        ...
                    ]
                    
                    page is page number and add double quotes for string type. this prproperty matched by page_number of documents object.
                    summary is Summary of that page of document. refer page_number.

                    IMPORTATNT: If the user doesn't ask you to answer in any language, please generate answer in the language you asked.
                    """,
                ),
                ("human", "{question}"),
            ]
        )

        # LLM gpt-3.5-turbo-1106 gpt-4-0125-preview
        llm = ChatOpenAI(model_name="gpt-3.5-turbo-1106", temperature=0)

        # Post-processing

        # Chain
        rag_chain = (
            {
                "context": self._retriever | RunnableLambda(self.format_docs),
                "question": RunnablePassthrough(),
            }
            | prompt
            | llm
            | StrOutputParser()
        )

        # Run
        generation = rag_chain.invoke(input=question)
        return {
            "keys": {
                "question": question,
                "generation": generation,
            }
        }

    def prepare_for_final_grade(self, state):
        """
        Passthrough state for final grade.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): The current graph state
        """

        print("---FINAL GRADE---")
        state_dict = state["keys"]
        question = state_dict["question"]
        generation = state_dict["generation"]

        return {
            "keys": {
                "question": question,
                "generation": generation,
            }
        }

    def grade_generation_v_documents(self, state):
        """
        Determines whether the generation is grounded in the document.
        Make sure all the pages for that document are summarized.

        Args:
            state (dict): The current state of the agent, including all keys.

        Returns:
            str: Binary decision
        """

        print("---GRADE GENERATION vs DOCUMENTS---")
        state_dict = state["keys"]
        question = state_dict["question"]
        generation = state_dict["generation"]

        # Data model
        class grade(BaseModel):
            """Binary score for relevance check."""

            binary_score: str = Field(description="Supported score 'yes' or 'no'")

        # LLM
        model = ChatOpenAI(temperature=0, model="gpt-4-0125-preview", streaming=True)

        # Tool
        grade_tool_oai = convert_to_openai_tool(grade)

        # LLM with tool and enforce invocation
        llm_with_tool = model.bind(
            tools=[convert_to_openai_tool(grade_tool_oai)],
            tool_choice={"type": "function", "function": {"name": "grade"}},
        )

        # Parser
        parser_tool = PydanticToolsParser(tools=[grade])

        # Prompt
        prompt = PromptTemplate(
            template="""You are a grader assessing whether an answer is grounded in / supported by a set of facts. \n 
            Here are the facts:
            \n ------- \n
            Context: {context}
            \n ------- \n
            Here is the user question: {question} \n
            Here is the answer: {generation}
            
            You need to make sure that the answer is answered in the following json format.
            page is page number and add double quotes for string type. this prproperty matched by page_number of documents object.
            summary is Summary of that page of document. refer page_number.

            [
                {{
                    page: "1",
                    summary: Page 1 Summary contents...
                }},
                {{
                    page: "2",
                    summary: Page 2 Summary contents...
                }},
                {{  page: "3",
                    summary: Page 3 Summary contents...
                }}
                ...
            ]
            

            Give a binary score 'yes' or 'no' to indicate whether the answer is grounded in / supported by a set of json format.""",
            input_variables=["context", "question", "generation"],
        )

        # Chain
        chain = prompt | llm_with_tool | parser_tool

        score = chain.invoke(
            {
                "context": self._retriever | RunnableLambda(self.format_docs),
                "question": question,
                "generation": generation,
            }
        )
        grade = score[0].binary_score

        if grade == "yes":
            print("---DECISION: SUPPORTED, MOVE TO FINAL GRADE---")
            return "useful"
        else:
            print("---DECISION: NOT SUPPORTED, GENERATE AGAIN---")
            return "generate"

    async def invoke_chain(self, email: str, file: UploadFile, ip: str, jwt: str):
        self.__init_path(email=email)
        self.embed_file(email=email, file=file, ip=ip, jwt=jwt)
        workflow = StateGraph(self.GraphState)

        # Define the nodes
        workflow.add_node("generate", self.generate)
        workflow.add_node("prepare_for_final_grade", self.prepare_for_final_grade)

        # Build graph
        workflow.set_entry_point("generate")
        workflow.add_edge("generate", "prepare_for_final_grade")
        workflow.add_conditional_edges(
            "prepare_for_final_grade",
            self.grade_generation_v_documents,
            {
                "useful": END,
                "generate": "generate",
            },
        )
        # Compile
        app = workflow.compile()
        inputs = {"keys": {"question": "모든 페이지를 페이지별로 요약해 줘."}}
        try:
            final_response = await app.ainvoke(inputs, {"recursion_limit": 15})
            return final_response["keys"]["generation"]
        except:
            return "해당 문서에서 대해 요약에 실패했습니다."
