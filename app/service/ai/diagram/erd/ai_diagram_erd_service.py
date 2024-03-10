import base64
import os
import json
import zlib
import matplotlib.pyplot as plt
import operator

from typing import Dict, TypedDict, Annotated, Sequence
from fastapi import HTTPException, status
from langchain import hub
from langgraph.graph import END, StateGraph
from langchain.output_parsers.openai_tools import PydanticToolsParser
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_openai import ChatOpenAI
from IPython.display import Image, display

from app.model.ai.diagram.erd.ai_diagram_erd_model import ErdGenerateInputs


class AIDiagramErdService(object):
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

        if not os.path.exists("./backend/.cache/erd"):
            os.makedirs("./backend/.cache/erd")

    def __init_path(self, email: str):
        if not os.path.exists(f"./backend/.cache/erd/{email}"):
            os.makedirs(f"./backend/.cache/erd/{email}")

    ### Nodes ###
    def improve_query(self, state):
        """
        Convert DML to DDL.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): The current graph state
        """
        state_dict = state["keys"]
        query = state_dict["query"]

        prompt = PromptTemplate(
            template="""
            "Design a system that transforms Database Manipulation Language (DML) commands into Data Definition Language (DDL) statements. This process involves translating operations that modify data (INSERT, UPDATE, DELETE) into statements that define or alter the database structure (CREATE, ALTER, DROP). The goal is to generate DDL statements that, when executed, would set up a database schema capable of reflecting the changes implied by the original DML commands, without actually altering any data. This requires analyzing the DML commands to infer structural changes like new tables, columns, or constraints that would be necessary to support the data modifications implied by the DML.
            1. Input the DML commands into the system.
            2. Analyze each DML command to identify the type of data operation (INSERT, UPDATE, DELETE) and the target tables and columns involved.
            3. For SELECT OR INSERT commands:
            - Generate CREATE TABLE statements for any tables that do not already exist.
            - Consider JOIN clauses if exists.
            - Infer column data types and constraints based on the values and structure in the INSERT command.
            4. For UPDATE commands:
            - Identify any new columns or modifications to existing columns (such as data type changes) that the UPDATE implies.
            - Generate CREATE TABLE statements to reflect these changes.
            5. For DELETE commands:
            - Consider if the DELETE operation suggests any structural modifications, such as the need for cascading deletes or updates to constraints.
            - Generate CREATE TABLE statements to add or modify constraints as needed.
            6. Compile all generated DDL statements, ensuring they are ordered logically to respect dependencies (e.g., creating tables before altering them).
            7. Provide a summary of the DDL statements that have been generated, explaining the rationale behind each based on the original DML commands.

            Self Evaluation:
            - Create primary keys and foreign keys if you think they're necessary.
            - Ensure the system accurately interprets the implications of each DML command for the database schema.
            - Check that the generated DDL statements are syntactically correct and logically ordered.
            - Verify the explanations clearly link DDL statements to their corresponding DML commands, making the transformation process transparent.
            - Assess whether the system effectively handles a wide range of DML commands and their potential impact on database structure.

            IMPORTANT: JUST PRINT OUT Converted code ONLY, nothing else!!.
            IMPORATNT: Output only plain text. Do not output markdown.


            before:{query}
            after:?

            """,
            input_variables=["query"],
        )

        # LLM
        llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

        # Chain
        rag_chain = prompt | llm | StrOutputParser()

        # Run
        query = rag_chain.invoke({"query": query})
        query = query.replace("```", "")
        return {"keys": {"query": query}}

    def convert_to_mermaidjs_code(self, state):
        """
        Convert query to mermaidjs code for making a diagram.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates mermaid key with coverted code
        """
        state_dict = state["keys"]
        query = state_dict["query"]

        prompt = PromptTemplate(
            template="""
            "Given an SQL query, the goal is to convert it into a visual representation using Mermaid.js, a JavaScript library that generates diagrams and flowcharts from text in a similar syntax to Markdown. Your task is to analyze the SQL query, identify its components such as SELECT, FROM, WHERE, JOIN, and ORDER BY clauses, and then map these components to their corresponding visual elements in Mermaid.js. This will include creating entities for tables, illustrating relationships between them (such as joins), and representing query flow or logic. 

            1. Start by breaking down the SQL query into its primary components.
            2. For each table mentioned in the FROM and JOIN clauses, create a class or entity in Mermaid.js.
            3. Use arrows or lines to represent relationships and joins, specifying the type of join (INNER, LEFT, RIGHT, FULL) and the joining conditions.
            4. Represent SELECT fields and WHERE conditions, perhaps as annotations or notes attached to the entities or relationships.
            5. If there are subqueries, represent them as nested diagrams or separate diagrams that are linked.
            6. Consider ORDER BY or GROUP BY clauses as additional annotations or as part of the diagram flow.

            IMPORTANT: A script or set of instructions in Mermaid.js syntax that visually represents the structure and logic of the SQL query, ensuring clarity in how data flows and is manipulated from the source tables to the final query result."

            Self Evaluation:
            - Ensure the prompt clearly separates each step of the conversion process for clarity.
            - Verify that the prompt addresses all common SQL query components and provides guidance on how to represent them in Mermaid.js.
            - Assess whether the instructions are general enough to apply to a wide range of SQL queries but specific enough to offer actionable guidance.
            - Consider the usability of the final Mermaid.js code – it should be easy to read and understand by someone familiar with both SQL and Mermaid.js.

            EXAMPLE:
            before:
            ```sql
            CREATE TABLE Students ( StudentID INT PRIMARY KEY AUTO_INCREMENT, StudentName VARCHAR(50), FeesPaid DATE, DateOfBirth DATE, Address VARCHAR(100) );

            CREATE TABLE Subjects ( SubjectID INT PRIMARY KEY AUTO_INCREMENT, SubjectName VARCHAR(50), CourseName VARCHAR(50) );

            CREATE TABLE Teachers ( TeacherID INT PRIMARY KEY AUTO_INCREMENT, TeacherName VARCHAR(50), TeacherAddress VARCHAR(100) );

            CREATE TABLE Student_Subject ( StudentID INT, SubjectID INT, FOREIGN KEY (StudentID) REFERENCES Students(StudentID), FOREIGN KEY (SubjectID) REFERENCES Subjects(SubjectID) );

            CREATE TABLE Subject_Teacher ( SubjectID INT, TeacherID INT, FOREIGN KEY (SubjectID) REFERENCES Subjects(SubjectID), FOREIGN KEY (TeacherID) REFERENCES Teachers(TeacherID) );
            ```

            after:
            ```
            erDiagram
            Students ||--|{{ Student_Subject : "has" 
            Subjects ||--|{{ Student_Subject : "taught in" 
            Teachers ||--|{{ Subject_Teacher : "teaches"
            Subjects ||--|{{ Subject_Teacher : "taught by" 

            Students {{
                int StudentID
                string StudentName
                date FeesPaid
                date DateOfBirth
                string Address
            }}

            Subjects {{
                int SubjectID
                string SubjectName
                string CourseName
            }}

            Teachers {{
                int TeacherID
                string TeacherName
                string TeacherAddress
            }}

            Student_Subject {{
                int StudentID
                int SubjectID
            }}

            Subject_Teacher {{
                int SubjectID
                int TeacherID
            }}
            ```
            
            YOUR TURN! JUST PRINT OUT CODE.
            IMPORATNT: Output only plain text. Do not output markdown.
            before:{query}
            after:?
            
            """,
            input_variables=["query"],
        )
        # LLM
        llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0, max_tokens=1000)

        # Chain
        rag_chain = prompt | llm | StrOutputParser()

        # Run
        mermaidjs = rag_chain.invoke({"query": query})
        mermaidjs = mermaidjs.replace("mermaidjs", "")
        mermaidjs = mermaidjs.replace("mermaid", "")
        mermaidjs = mermaidjs.replace("```", "")
        return {"keys": {"query": query, "mermaidjs": mermaidjs}}

    def make_graph(self, state):
        """
        Make a graph based on mermaidjs

        Args:
            state (dict): The current graph state

        Returns:
            graph Image URL base64 string
        """

        state_dict = state["keys"]
        query = state_dict["query"]
        mermaidjs = state_dict["mermaidjs"]

        # 1
        graphbytes = mermaidjs.encode("ascii")
        base64_bytes = base64.b64encode(graphbytes)
        base64_string = base64_bytes.decode("ascii")

        # 2
        # jGraph = {"code": mermaidjs, "mermaid": {"theme": "default"}}
        # byteStr = bytes(json.dumps(jGraph), "ascii")

        # compress = zlib.compressobj(9, zlib.DEFLATED, 15, 8, zlib.Z_DEFAULT_STRATEGY)
        # compressed_data = compress.compress(byteStr)
        # compressed_data += compress.flush()

        # dEncode = base64.b64encode(compressed_data)
        # link = "http://mermaid.live/view#pako:" + dEncode.decode("ascii")

        # display(Image(url='https://mermaid.ink/img/' + base64_string))
        return {
            "keys": {
                "query": query,
                "mermaidjs": mermaidjs,
                "image": "https://mermaid.ink/img/" + base64_string,
                # "image": link,
            }
        }

    ### Edges ###
    def check_query(self, state):
        """
        Check query if a query is correct.

        Args:
            state (dict): state (dict): The current state of the agent

        Returns:
            str: Descision next node to call
        """

        state_dict = state["keys"]
        query = state_dict["query"]

        # Data model
        class safe(BaseModel):
            """Check the query for grammer errors"""

            is_exist_error: str = Field(description="Supported value 'yes' or 'no'")

        llm = ChatOpenAI(temperature=0, model="gpt-4-0125-preview", streaming=True)

        safe_tool_oai = convert_to_openai_tool(safe)

        # LLM with tool and enforce invocation
        llm_with_tool = llm.bind(
            tools=[convert_to_openai_tool(safe_tool_oai)],
            tool_choice={"type": "function", "function": {"name": "safe"}},
        )

        # Parser
        parser_tool = PydanticToolsParser(tools=[safe])

        # Prompt
        prompt = PromptTemplate(
            template=""""Create a system that evaluates the correctness of an SQL query, ensuring it follows proper syntax, structure, and logic without errors. This system should be capable of parsing the SQL query, identifying various components such as SELECT, FROM, WHERE, JOIN, and ORDER BY clauses, and validating each part against SQL syntax rules. Additionally, it should check for common logical errors, such as mismatched column names, incorrect table references, or invalid operations.

            1. Input the SQL query into the system.
            2. Parse the query to extract its main components (Create, Alter, Delete, SELECT, FROM, WHERE, etc.).
            3. For each component, validate its syntax according to SQL standards.
            4. Check for the existence of tables and columns referenced in the query against a predefined schema or database metadata.
            5. Verify that JOIN operations have correct and existing keys on both sides.
            6. Ensure WHERE, GROUP BY, and HAVING clauses use columns correctly and logical conditions are valid.
            7. Validate ORDER BY clauses for correct column references and sorting directions.
            8. If subqueries are present, recursively apply these validation steps to each subquery.
            9. Report any errors found during the validation process, specifying the type of error and its location within the query.

            Output: A detailed report indicating whether the SQL query is correct or listing any syntax or logical errors found, providing specific feedback to help correct the errors."

            Self Evaluation:
            - Check if the prompt systematically addresses both syntax and logical validation steps.
            - Ensure the instructions cover a comprehensive range of SQL components and potential error types.
            - Assess the clarity of the output specification, ensuring it provides actionable feedback.
            - Confirm that the prompt encourages a recursive approach to subquery validation, enhancing thoroughness.

            Here is the sql query.
            ```sql
            {query}
            ```
            IMPORTANT: You only print 'yes' or 'no'.
            IMPORTANT: If there is an error on query, PRINT 'yes', and if there is no error, PRINT 'no'.
            
            """,
            input_variables=["query"],
        )

        state_dict = state["keys"]
        query = state_dict["query"]

        # Chain
        chain = prompt | llm_with_tool | parser_tool

        result = chain.invoke({"query": query})
        print(result)
        safe = result[0].is_exist_error

        if safe == "no":
            print("there are no error found.")
            return "no"
        else:
            print("error existed.")
            return "yes"

    async def invoke(self, email: str, inputs: ErdGenerateInputs):
        self.__init_path(email=email)
        pInputs = {"keys": inputs.model_dump()}
        workflow = StateGraph(self.GraphState)

        # Define the nodes
        workflow.add_node("improve_query", self.improve_query)  # improve_query
        workflow.add_node(
            "convert_to_mermaidjs_code", self.convert_to_mermaidjs_code
        )  # convert_to_mermaidjs_code
        workflow.add_node("make_graph", self.make_graph)  # make_graph

        # Build graph
        workflow.set_entry_point("improve_query")
        workflow.add_conditional_edges(
            "improve_query",
            self.check_query,
            {
                "yes": END,
                "no": "convert_to_mermaidjs_code",
            },
        )
        workflow.add_edge("convert_to_mermaidjs_code", "make_graph")
        workflow.add_edge("make_graph", END)

        # Compile
        app = workflow.compile()

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
            final_response = await app.ainvoke(pInputs, {"recursion_limit": 10})
            return final_response["keys"]["image"]
        except:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ERD 이미지 생성에 실패했습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )
