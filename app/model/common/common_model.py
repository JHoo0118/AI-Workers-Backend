from typing import Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class APIResponse(BaseModel, Generic[T]):
    ok: bool = Field("Success or not")
    data: Optional[T] = Field("Data")
    message: Optional[str] = Field("Additional Message")
    status_code: Optional[int] = Field("Status Code", alias="statusCode")
