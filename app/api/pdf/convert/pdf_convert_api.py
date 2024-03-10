from typing import List
from fastapi import UploadFile
from fastapi import APIRouter
from app.model import *
from app.service.pdf import get_pdf_to_word_result

router = APIRouter(
    prefix="/convert",
    tags=["pdf"],
    dependencies=[],
    responses={404: {"description": "찾을 수 없습니다."}},
)


@router.post("/word")
async def pdf_to_word(files: List[UploadFile]) -> PdfToWordResponse:
    result = await get_pdf_to_word_result(files=files)
    return PdfToWordResponse(result=result)
