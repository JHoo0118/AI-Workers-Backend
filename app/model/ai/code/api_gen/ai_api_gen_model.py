import json
from openai import BaseModel
from pydantic import Field

from app.model.base_model import BaseSchema


class ApiGenerateInputs(BaseModel):
    input: str
    framework: str

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_to_json

    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value


class ApiGenerateOutputs(BaseSchema):
    backend_code: str = Field("생성된 백엔드 코드")
