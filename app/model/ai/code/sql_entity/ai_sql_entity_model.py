import json
from openai import BaseModel
from pydantic import Field


class SqlToEntityGenerateInputs(BaseModel):
    sql: str
    framework: str

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_to_json

    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value


class SqlToEntityGenerateOutputs(BaseModel):
    result: str = Field("생성된 엔티티")
