from typing import List
from pydantic import BaseModel, Field


class PdfMergeResponse(BaseModel):
    filename: str = Field(description="병합된 PDF 파일명")


class PdfToWordResponse(BaseModel):
    result: List[str] = Field
