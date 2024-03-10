from typing import List
from fastapi import UploadFile
from fastapi import APIRouter
from app.model import *
from app.service.pdf import get_pdf_merge_result

router = APIRouter(
    prefix="/merge",
    tags=["pdf"],
    dependencies=[],
    responses={404: {"description": "찾을 수 없습니다."}},
)


@router.post("")
def pdf_merge(files: List[UploadFile]) -> PdfMergeResponse:
    filename = get_pdf_merge_result(files=files)
    return PdfMergeResponse(filename=filename)
