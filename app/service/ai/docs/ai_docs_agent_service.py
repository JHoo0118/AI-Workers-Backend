import os
import json
import shutil

from pyparsing import Any
from typing import Dict, List, TypedDict
from dotenv import load_dotenv
from fastapi import HTTPException, UploadFile, status
from upstash_redis import Redis
from langchain import hub
from langchain.output_parsers.openai_tools import PydanticToolsParser
from langchain.prompts import PromptTemplate
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain_core.output_parsers import StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_community.chat_message_histories.upstash_redis import (
    UpstashRedisChatMessageHistory,
)
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


load_dotenv()
PREFIX = "docs-summary"
UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")
redis_client = Redis(url=UPSTASH_REDIS_REST_URL, token=UPSTASH_REDIS_REST_TOKEN)
splitter = CharacterTextSplitter.from_tiktoken_encoder(
    separator="\n",
    chunk_size=600,
    chunk_overlap=100,
)

embeddings = OpenAIEmbeddings()


class CustomCallbackHandler(AsyncIteratorCallbackHandler):
    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        **kwargs: Any,
    ):
        print("model started")

    def on_llm_start(self, *args, **kwargs):
        print("START!!")

    def on_llm_end(self, *args, **kwargs):
        print("END!!")

    def on_llm_new_token(self, token, *args, **kwargs):
        print(f"TOKEN: {token}")


class AIDocsAgentService(object):
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
        os.makedirs(f"{self._tmp_usage_dir}/{email}/docs", exist_ok=True)

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

            cache_dir = UpstashRedisByteStore(
                client=redis_client,
                ttl=60 * 60 * 2,
                namespace=f"{PREFIX}-{pFilename}-{email}",
            )
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

    def retrieve(self, state):
        """
        Retrieve documents

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, documents, that contains retrieved documents
        """
        print("---RETRIEVE---")
        state_dict = state["keys"]
        question = state_dict["question"]
        documents = self._retriever.get_relevant_documents(question)
        return {"keys": {"documents": documents, "question": question}}

    def generate(self, state):
        """
        Generate answer

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, generation, that contains LLM generation
        """
        print("---GENERATE---")
        state_dict = state["keys"]
        question = state_dict["question"]
        documents = state_dict["documents"]

        # Prompt
        prompt = hub.pull("rlm/rag-prompt")

        # LLM
        llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

        # Post-processing
        def format_docs(self, docs):
            return "\n\n".join(doc.page_content for doc in docs)

        # Chain
        rag_chain = prompt | llm | StrOutputParser()

        # Run
        generation = rag_chain.invoke({"context": documents, "question": question})
        return {
            "keys": {
                "documents": documents,
                "question": question,
                "generation": generation,
            }
        }

    def grade_documents(self, state):
        """
        Determines whether the retrieved documents are relevant to the question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates documents key with relevant documents
        """

        print("---CHECK RELEVANCE---")
        state_dict = state["keys"]
        question = state_dict["question"]
        documents = state_dict["documents"]

        # Data model
        class grade(BaseModel):
            """Binary score for relevance check."""

            binary_score: str = Field(description="Relevance score 'yes' or 'no'")

        # LLM gpt-4-0125-preview
        model = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-1106", streaming=True)

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
            template="""You are a grader assessing relevance of a retrieved document to a user question. \n 
            Here is the retrieved document: \n\n {context} \n\n
            Here is the user question: {question} \n
            If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n
            Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question.""",
            input_variables=["context", "question"],
        )

        # Chain
        chain = prompt | llm_with_tool | parser_tool

        # Score
        filtered_docs = []
        for d in documents:
            score = chain.invoke({"question": question, "context": d.page_content})
            grade = score[0].binary_score
            if grade == "yes":
                print("---GRADE: DOCUMENT RELEVANT---")
                filtered_docs.append(d)
            else:
                print("---GRADE: DOCUMENT NOT RELEVANT---")
                continue

        return {"keys": {"documents": filtered_docs, "question": question}}

    def transform_query(self, state):
        """
        Transform the query to produce a better question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates question key with a re-phrased question
        """

        print("---TRANSFORM QUERY---")
        state_dict = state["keys"]
        question = state_dict["question"]
        documents = state_dict["documents"]

        # Create a prompt template with format instructions and the query
        prompt = PromptTemplate(
            template="""You are generating questions that is well optimized for retrieval. \n 
            Look at the input and try to reason about the underlying sematic intent / meaning. \n 
            Here is the initial question:
            \n ------- \n
            {question} 
            \n ------- \n
            Formulate an improved question: """,
            input_variables=["question"],
        )

        # Grader
        model = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-1106", streaming=True)

        # Prompt
        chain = prompt | model | StrOutputParser()
        better_question = chain.invoke({"question": question})

        return {"keys": {"documents": documents, "question": better_question}}

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
        documents = state_dict["documents"]
        generation = state_dict["generation"]

        return {
            "keys": {
                "documents": documents,
                "question": question,
                "generation": generation,
            }
        }

    ### Edges ###

    def decide_to_generate(self, state):
        """
        Determines whether to generate an answer, or re-generate a question.

        Args:
            state (dict): The current state of the agent, including all keys.

        Returns:
            str: Next node to call
        """

        print("---DECIDE TO GENERATE---")
        state_dict = state["keys"]
        question = state_dict["question"]
        filtered_documents = state_dict["documents"]

        if not filtered_documents:
            # All documents have been filtered check_relevance
            # We will re-generate a new query
            print("---DECISION: TRANSFORM QUERY---")
            return "transform_query"
        else:
            # We have relevant documents, so generate answer
            print("---DECISION: GENERATE---")
            return "generate"

    def grade_generation_v_documents(self, state):
        """
        Determines whether the generation is grounded in the document.

        Args:
            state (dict): The current state of the agent, including all keys.

        Returns:
            str: Binary decision
        """

        print("---GRADE GENERATION vs DOCUMENTS---")
        state_dict = state["keys"]
        question = state_dict["question"]
        documents = state_dict["documents"]
        generation = state_dict["generation"]

        # Data model
        class grade(BaseModel):
            """Binary score for relevance check."""

            binary_score: str = Field(description="Supported score 'yes' or 'no'")

        # LLM
        model = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-1106", streaming=True)

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
            {documents} 
            \n ------- \n
            Here is the answer: {generation}
            Give a binary score 'yes' or 'no' to indicate whether the answer is grounded in / supported by a set of facts.""",
            input_variables=["generation", "documents"],
        )

        # Chain
        chain = prompt | llm_with_tool | parser_tool

        score = chain.invoke({"generation": generation, "documents": documents})
        grade = score[0].binary_score

        if grade == "yes":
            print("---DECISION: SUPPORTED, MOVE TO FINAL GRADE---")
            return "supported"
        else:
            print("---DECISION: NOT SUPPORTED, GENERATE AGAIN---")
            return "not supported"

    def grade_generation_v_question(self, state):
        """
        Determines whether the generation addresses the question.

        Args:
            state (dict): The current state of the agent, including all keys.

        Returns:
            str: Binary decision
        """

        print("---GRADE GENERATION vs QUESTION---")
        state_dict = state["keys"]
        question = state_dict["question"]
        documents = state_dict["documents"]
        generation = state_dict["generation"]

        # Data model
        class grade(BaseModel):
            """Binary score for relevance check."""

            binary_score: str = Field(description="Useful score 'yes' or 'no'")

        # LLM
        model = ChatOpenAI(
            temperature=0,
            model="gpt-3.5-turbo-1106",
            streaming=True,
            # callbacks=[self._callback],
        )

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
            template="""You are a grader assessing whether an answer is useful to resolve a question. \n 
            Here is the answer:
            \n ------- \n
            {generation} 
            \n ------- \n
            Here is the question: {question}
            Give a binary score 'yes' or 'no' to indicate whether the answer is useful to resolve a question.""",
            input_variables=["generation", "question"],
        )

        # Prompt
        chain = prompt | llm_with_tool | parser_tool

        score = chain.invoke({"generation": generation, "question": question})
        grade = score[0].binary_score

        if grade == "yes":
            print("---DECISION: USEFUL---")
            return "useful"
        else:
            print("---DECISION: NOT USEFUL---")
            return "not useful"

    async def invoke_chain(self, email: str, filename: str, message: str, ip: str):
        self.__init_path(email=email)
        self.get_retriever(email=email, filename=filename, ip=ip)
        workflow = StateGraph(self.GraphState)

        # Define the nodes
        workflow.add_node("retrieve", self.retrieve)  # retrieve
        workflow.add_node("grade_documents", self.grade_documents)  # grade documents
        workflow.add_node("generate", self.generate)  # generatae
        workflow.add_node("transform_query", self.transform_query)  # transform_query
        workflow.add_node(
            "prepare_for_final_grade", self.prepare_for_final_grade
        )  # passthrough

        # Build graph
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "grade_documents")
        workflow.add_conditional_edges(
            "grade_documents",
            self.decide_to_generate,
            {
                "transform_query": "transform_query",
                "generate": "generate",
            },
        )
        workflow.add_edge("transform_query", "retrieve")
        workflow.add_conditional_edges(
            "generate",
            self.grade_generation_v_documents,
            {
                "supported": "prepare_for_final_grade",
                "not supported": "generate",
            },
        )
        workflow.add_conditional_edges(
            "prepare_for_final_grade",
            self.grade_generation_v_question,
            {
                "useful": END,
                "not useful": "transform_query",
            },
        )
        # Compile
        app = workflow.compile()
        inputs = {"keys": {"question": message}}
        try:
            # task = asyncio.create_task(app.ainvoke(inputs, {"recursion_limit": 10}))
            # try:
            #     async for token in self._callback.aiter():
            #         print(f"token: {token}")
            #         yield token
            # except Exception as e:
            #     print(f"Caught exception: {e}")
            # finally:
            #     self._callback.done.set()
            # await task
            final_response = await app.ainvoke(inputs, {"recursion_limit": 10})
            return final_response["keys"]["generation"]
        except:
            return "해당 문서에서 질문에 대한 답을 찾을 수 없습니다."
