import json
from pydantic import BaseModel
from typing import List

from app.model.ai.ai_model import ChatModel


class DocsSummaryAskInputs(BaseModel):
    messages: List[ChatModel]

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_to_json

    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value


class DocsSummaryAskOutputs(BaseModel):
    result: str
