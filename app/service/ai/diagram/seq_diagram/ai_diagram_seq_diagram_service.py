import base64
import os

from typing import Dict, TypedDict
from fastapi import HTTPException, status
from langgraph.graph import END, StateGraph
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from app.model.ai.diagram.seq_diagram.ai_diagram_seq_diagram_model import (
    SeqDiagramGenerateInputs,
)


class AIDiagramSeqDiagramService(object):
    _instance = None

    class GraphState(TypedDict):
        """
        Represents the state of our graph.

        Attributes:
            keys: A dictionary where each key is a string.
        """

        keys: Dict[str, any]

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)

        return class_._instance

    def __init__(self):
        if not os.path.exists("./backend/.cache"):
            os.makedirs("./backend/.cache")

        if not os.path.exists("./backend/.cache/seq_diagram"):
            os.makedirs("./backend/.cache/seq_diagram")

    def __init_path(self, email: str):
        if not os.path.exists(f"./backend/.cache/seq_diagram/{email}"):
            os.makedirs(f"./backend/.cache/seq_diagram/{email}")

    ### Nodes ###
    def summarize_user_request(self, state):
        """
        Summarize the user request.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates request key with summarized request
        """

        state_dict = state["keys"]
        request = state_dict["request"]

        prompt = PromptTemplate(
            template="""A step-by-step process is given by the request. You should summarize step by step in chronological order while maintaining important information.

            example: 
            request: When the user sends a use request to the client, the client requests the authorization server for an authorization approval code. In this case, parameters included in the request are client_id, redirect_url, and response_type. Simultaneously with the previous process, when the user requests a login to the authorization server, the authorization server transmits the authorization approval code to the client.
            summarized: 1. user sends a use request to the client
                        2. ....

            user request is "{request}"
            IMPORTANT: Just print out summarized result, nothing else.
            """,
            input_variables=["request"],
        )

        # LLM gpt-3.5-turbo gpt-4-0125-preview"
        llm = ChatOpenAI(model_name="gpt-4-0125-preview", temperature=0)
        # llm = ChatOllama(model="mistral:latest")

        # Chain
        chain = prompt | llm | StrOutputParser()

        # Run
        summarized = chain.invoke({"request": request})
        return {"keys": {"request": summarized}}

    def convert_to_mermaidjs_code(self, state):
        """
        Convert summarized user request to mermaidjs code for making a sequence diagram.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates mermaid key with coverted code
        """

        prompt = PromptTemplate(
            template="""The goal is to craft a prompt that enables the creation of a sequence diagram using MermaidJS syntax, as defined by the documentation and examples from the MermaidJS official site. This prompt should guide the generation process to ensure it includes all necessary elements for a comprehensive sequence diagram. To achieve this, the prompt will encapsulate instructions on defining participants, illustrating message exchanges, and utilizing MermaidJS's advanced features such as activations, loops, notes, break, and conditional interactions.

        Instructions:
        - Begin by defining the diagram type to ensure MermaidJS interprets it as a sequence diagram.
        - Clearly list all participants in the interaction, ensuring each is uniquely identified.
        - Detail the sequence of messages exchanged between participants, using arrows to denote direction and message type (solid for direct messages, dotted for responses, etc.).
        - Use 'Notes' for parameters or additional explanations.
        - Do not use that Participant name is "AS".
        - Background color is white, foreground color is black.
        - activation/deactivation (+/-) should be equal to single activate/deactivate instruction.
        - Incorporate advanced diagramming features such as activation bars to indicate when a participant is active, loops for repetitive actions, and conditional blocks to represent decision-making processes.
        - Include comments to explain complex parts of the diagram or to provide additional context.
        - Just print out mermaidjs code, do not user markdown. Your answer starts with 'sequenceDiagram'.

        user request: {request}
        answer: ? """,
            input_variables=["request"],
        )

        state_dict = state["keys"]
        request = state_dict["request"]

        # LLM
        llm = ChatOpenAI(model_name="gpt-4-0125-preview", temperature=0)
        # llm = ChatOllama(model="mistral:latest")

        # Chain
        chain = prompt | llm | StrOutputParser()

        # Run
        mermaidjs = chain.invoke(
            {
                "request": request,
            }
        )
        mermaidjs = mermaidjs.replace("mermaidjs", "")
        mermaidjs = mermaidjs.replace("```mermaidjs", "")
        mermaidjs = mermaidjs.replace("```", "")
        return {"keys": {"request": request, "mermaidjs": mermaidjs}}

    def make_graph(self, state):
        """
        Make a graph based on mermaidjs

        Args:
            state (dict): The current graph state

        Returns:
            graph Image URL base64 string
        """

        state_dict = state["keys"]
        request = state_dict["request"]
        mermaidjs = state_dict["mermaidjs"]

        graphbytes = mermaidjs.encode("ascii")
        base64_bytes = base64.b64encode(graphbytes)
        base64_string = base64_bytes.decode("ascii")

        return {
            "keys": {
                "request": request,
                "mermaidjs": mermaidjs,
                "image": "https://mermaid.ink/img/" + base64_string,
            }
        }

    async def invoke(self, email: str, inputs: SeqDiagramGenerateInputs):
        self.__init_path(email=email)
        pInputs = {"keys": inputs.model_dump()}

        workflow = StateGraph(self.GraphState)

        # Define the nodes
        workflow.add_node(
            "summarize_user_request", self.summarize_user_request
        )  # summarize_user_request
        workflow.add_node(
            "convert_to_mermaidjs_code", self.convert_to_mermaidjs_code
        )  # convert_to_mermaidjs_code
        workflow.add_node("make_graph", self.make_graph)  # make_graph

        # Build graph
        workflow.set_entry_point("summarize_user_request")
        workflow.add_edge("summarize_user_request", "convert_to_mermaidjs_code")
        workflow.add_edge("convert_to_mermaidjs_code", "make_graph")
        workflow.add_edge("make_graph", END)

        # Compile
        app = workflow.compile()

        try:
            final_response = await app.ainvoke(pInputs, {"recursion_limit": 10})
            return final_response["keys"]["image"]
        except:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Sequence Diagram 이미지 생성에 실패했습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )
