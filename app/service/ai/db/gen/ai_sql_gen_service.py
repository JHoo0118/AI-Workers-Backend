import os
from operator import itemgetter

from typing import AsyncGenerator, Dict, TypedDict
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from langchain.memory import ConversationSummaryBufferMemory

from langchain.prompts import ChatPromptTemplate


class AISqlGenService(object):
    _instance = None
    _memory_llm: ChatOpenAI
    _memory: ConversationSummaryBufferMemory

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)

        return class_._instance

    def __init__(self):
        self._memory_llm = ChatOpenAI(
            temperature=0.1,
            model="gpt-4-0125-preview",
        )

        self._memory = ConversationSummaryBufferMemory(
            llm=self._memory_llm,
            max_token_limit=500,
            memory_key="chat_history",
            return_messages=True,
        )

    def save_message(self, input, output):
        self._memory.save_context(inputs={"input": input}, outputs={"output": output})

    async def invoke_chain(
        self,
        email,
        message,
    ) -> AsyncGenerator[str, None]:
        """
        Summarize the user request.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates request key with summarized request
        """

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are Database Design & Database Architecture EXPERT!!

                    OUTPUT
                    1. First, converts user request into a short summarized goal
                    2. You can search the database architect based on the summarized goals.
                    3. You must have to write code of the table schemas.
                    4. Make sure that the created schemas is no errors.
                    5. If there is no error, create the schema in more detail.

                    IMPORTATNT: YOU must print code of the table schemas you created.
                    IMPORTANT: Just print out summarized result, nothing else.

                    user request is "{question}"
                    """,
                ),
                ("human", "{question}"),
            ]
        )

        # LLM gpt-3.5-turbo gpt-4-0125-preview"
        llm = ChatOpenAI(
            model_name="gpt-4-0125-preview", temperature=0, max_tokens=1000
        )
        # llm = ChatOllama(model="mistral:latest")

        # Chain
        chain = (
            {
                "question": RunnablePassthrough(),
            }
            | RunnablePassthrough.assign(
                chat_history=RunnableLambda(self._memory.load_memory_variables)
                | itemgetter("chat_history")
            )
            | prompt
            | llm
            | StrOutputParser()
        )

        response = ""
        async for token in chain.astream(input=message):
            yield token
            response += token
        self.save_message(message, response)
