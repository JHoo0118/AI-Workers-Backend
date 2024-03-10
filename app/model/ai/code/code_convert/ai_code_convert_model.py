import json

from openai import BaseModel
from pydantic import Field
from app.model.base_model import BaseSchema


class CodeConvertGenerateInputs(BaseSchema):
    code: str
    code_type: str
    target_code_type: str

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_to_json

    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value


class CodeConvertGenerateOutputs(BaseModel):
    result: str = Field("변환된 코드")
