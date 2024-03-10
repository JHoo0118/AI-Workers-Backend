from pydantic import Field
from app.model.base_model import BaseSchema


class IsExistFileOutputs(BaseSchema):
    is_exist: bool = Field(
        description="존재하는 파일이면 true, 아니면 false",
    )
