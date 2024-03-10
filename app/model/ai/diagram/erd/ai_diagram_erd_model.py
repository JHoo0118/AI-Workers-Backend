import json
from openai import BaseModel
from pydantic import Field


class ErdGenerateInputs(BaseModel):
    query: str

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_to_json

    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value


class ErdGenerateOutputs(BaseModel):
    image: str = Field("생성된 ERD 이미지")
