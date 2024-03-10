from fastapi import APIRouter


router = APIRouter(
    prefix="/ai",
    tags=["ai"],
    dependencies=[],
    responses={404: {"description": "찾을 수 없습니다."}},
)
