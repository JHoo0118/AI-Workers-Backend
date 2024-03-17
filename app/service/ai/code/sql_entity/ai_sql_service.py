import os
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from app.model.ai.code.sql_entity.ai_sql_entity_model import SqlToEntityGenerateInputs
from app.utils.data_utils import replace_ignore_case


class AICodeSqlService(object):
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)

        return class_._instance

    async def invoke_chain(self, email: str, inputs: SqlToEntityGenerateInputs):

        prompt = PromptTemplate(
            template="""The AI model is tasked with generating entity code for a specific framework based on the SQL code provided by the user. This task involves parsing the SQL code to extract schema information, such as table names, column details (names, data types, constraints), and relationships between tables. The model will then use this information to create entity classes or models in the framework specified by the user, aligning with the framework's conventions for object-relational mapping (ORM).

            sql is: {sql}
            framework is: {framework} 
            
            The prompt instructs the model to:
            1. **Parse SQL Code**: Analyze the given SQL code to identify key components of the database schema. This includes extracting information about tables, columns (with data types and constraints like primary keys, foreign keys, unique, not null), and any defined relationships or indexes.
            2. **Framework Identification**: Identify the framework specified by the user (e.g., Django for Python, Hibernate for Java, Entity Framework for .NET) to determine the appropriate syntax and conventions for generating entity code.
            3. **Generate Entity Code**: Based on the extracted schema information and the identified framework, generate the code for entities or models that represent the database tables. This code should include:
                - Class definitions for each table with properties or fields corresponding to the table columns.
                - Annotations or decorators to specify primary keys, relationships (one-to-many, many-to-one, many-to-many), column constraints, and any framework-specific configurations.
                - Necessary imports or using statements required by the framework for ORM functionality.
            4. **Ensure Compatibility and Conventions**: Make sure that the generated entity code adheres to the best practices and conventions of the specified framework, including naming conventions, data type mappings, and relationship handling.
            5. **Comment and Documentation**: Include inline comments or documentation within the generated code to explain the purpose and structure of each entity, especially highlighting any non-trivial mappings or relationship configurations.
            6. make getter, setter and build method.
            
            Self Evaluation:
            - After generating the entity code, the model should review the code for accuracy in representing the original SQL schema, ensuring all tables and columns are correctly mapped to entities and fields.
            - Verify that the code follows the specific conventions and requirements of the chosen framework, including correct data type mappings and relationship annotations.
            - Assess the readability and maintainability of the generated code, ensuring that it is well-organized and documented for future development and integration into the larger project.

            This prompt ensures that the model focuses on accurately converting SQL schema definitions into framework-specific entity code, facilitating database interactions within the application through ORM techniques.

            IMPORATNT: Print ONLY the code, nothing else and Output only plain text. Do not output markdown.
            """,
            input_variables=["sql", "framework"],
        )

        # LLM
        llm = ChatOpenAI(
            # model_name="gpt-4-0125-preview",
            model="gpt-3.5-turbo",
            temperature=0,
            max_tokens=1000,
        )  # 4000자

        # Chain
        chain = prompt | llm | StrOutputParser()

        # Run
        result = await chain.ainvoke(inputs.model_dump())

        langs = ["go", "java", "python", "javascript", "typescript", "csharp"]
        for lang in langs:
            result = replace_ignore_case(result, f"```{lang}", "")
        result = result.replace("```", "")
        return result
