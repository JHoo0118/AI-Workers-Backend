import os
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from app.model.ai.code.code_convert.ai_code_convert_model import (
    CodeConvertGenerateInputs,
)


class AICodeCodeConvertService(object):
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)

        return class_._instance

    def __init__(self):
        if not os.path.exists("./backend/.cache"):
            os.makedirs("./backend/.cache")

        if not os.path.exists("./backend/.cache/code_convert"):
            os.makedirs("./backend/.cache/code_convert")

    def __init_path(self, email: str):
        if not os.path.exists(f"./backend/.cache/code_convert/{email}"):
            os.makedirs(f"./backend/.cache/code_convert/{email}")

    async def invoke_chain(self, email: str, inputs: CodeConvertGenerateInputs):
        self.__init_path(email=email)

        prompt = PromptTemplate(
            template="""Given the original code in a specific programming language and the target programming language, your task is to convert the code from the original language to the target language. This process requires understanding the syntax, data types, control structures, and libraries or frameworks used in both the original and target languages. 

            
            The programming language type is: {code_type}
            The target programming language tpye is: {target_code_type}
            Here is the code snippet.
            ```
            {code}
            ```
            1. Start by analyzing the given code snippet to identify its core functionality, including variables, functions, loops, conditionals, and any library or API calls.
            2. Research the equivalent syntax, library and constructs in the target programming language. This may involve looking up documentation, tutorials, or code examples online.
            3. Begin converting the code section by section, starting with variable declarations and initialization, followed by control structures (if-else statements, loops), functions or methods, and finally, any specialized library or API usage.
            4. Pay special attention to data types and their compatibility between the two languages, as this can be a common source of bugs or errors.
            5. If there are any new variables, functions, classes, etc., use names that fit the role.
            6. If the variable name is a reserved word in the changed language, it should be changed appropriately.
            7. After converting the code, perform a self-review to ensure the logic and functionality match the original code. Look for any syntax errors or overlooked language-specific nuances.
            8. Test the converted code with the same inputs used for the original code to verify that it produces the same outputs. Adjust the code as necessary to fix any discrepancies or errors encountered during testing.

            Output: JUST PRINT OUT CODE, Nothing else.
            IMPORATNT: Output only plain text. Do not output markdown.

            Self Evaluation:
            - Was the import statement of the library you used written?
            - Did the converted code compile and run without errors in the target language environment?
            - Does the converted code accurately replicate the functionality of the original code, producing the same outputs for given inputs?
            - Were there any parts of the original code that required specific consideration due to differences in the programming languages (e.g., memory management, concurrency, library support)?
            - If any bugs or errors were encountered during testing, were they addressed effectively, and what was the root cause?
            - How could the conversion process be improved for efficiency or readability of the converted code?

            Re-answer based on self-evaluation results:
            - Adjust the conversion approach if necessary, focusing on areas where the initial conversion may have missed language-specific features or introduced bugs.
            - Apply any insights gained from the self-evaluation to refine the converted code, ensuring it is as efficient, readable, and true to the original functionality as possible.
            
            """,
            input_variables=["code", "code_type", "target_code_type"],
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
        return result
