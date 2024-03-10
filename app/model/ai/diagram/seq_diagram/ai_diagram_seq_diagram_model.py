import json
from openai import BaseModel
from pydantic import Field


class SeqDiagramGenerateInputs(BaseModel):
    request: str

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_to_json

    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value


class SeqDiagramGenerateOutputs(BaseModel):
    image: str = Field("생성된 Sequence Diagram 이미지")
