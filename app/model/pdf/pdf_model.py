from typing import List
from fastapi import UploadFile
from pydantic import BaseModel, Field

from app.model.base_model import BaseSchema


class PdfMergeResponse(BaseModel):
    filename: str = Field(description="병합된 PDF 파일명")


class PdfToWordResponse(BaseModel):
    result: List[str] = Field


class PdfSplitInputs(BaseSchema):
    start_page_number: str
    end_page_number: str


class PdfSplitResponse(BaseModel):
    filename: str = Field(description="분할된 PDF 파일명")
