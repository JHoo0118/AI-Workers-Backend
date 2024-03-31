import json
from typing import List
from openai import BaseModel
from pydantic import Field

from app.model.ai.ai_model import ChatModel
from app.model.base_model import BaseSchema


class AlgorithmAdviceGenerateInputs(BaseSchema):
    messages: List[ChatModel]
    lang: str

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_to_json

    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value


class AlgorithmAdviceGenerateOutputs(BaseModel):
    result: str
