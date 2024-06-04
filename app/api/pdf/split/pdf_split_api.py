from fastapi import APIRouter, File, Form
from app.model import *
from app.service.pdf import get_pdf_split_result

router = APIRouter(
    prefix="/split",
    tags=["pdf"],
    dependencies=[],
    responses={404: {"description": "찾을 수 없습니다."}},
)


@router.post("")
def pdf_split(
    startPageNumber: str = Form(...),
    endPageNumber: str = Form(...),
    files: List[UploadFile] = File(...),
) -> PdfSplitResponse:
    inputs = PdfSplitInputs(
        startPageNumber=startPageNumber,
        endPageNumber=endPageNumber,
    )
    filename = get_pdf_split_result(
        start_page_number=inputs.start_page_number,
        end_page_number=inputs.end_page_number,
        files=files,
    )
    return PdfSplitResponse(filename=filename)
