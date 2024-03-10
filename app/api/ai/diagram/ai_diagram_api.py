from fastapi import APIRouter


router = APIRouter(
    prefix="/diagram",
    tags=["ai"],
    dependencies=[],
    responses={404: {"description": "찾을 수 없습니다."}},
)
