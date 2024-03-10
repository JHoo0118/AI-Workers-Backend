from fastapi import APIRouter, Body, Depends
from typing import Annotated

from app.model.user.user_model import UserModel
from app.service.auth.jwt_bearer import JwtBearer
from app.model.ai.code.api_gen.ai_api_gen_model import (
    ApiGenerateInputs,
    ApiGenerateOutputs,
)
from app.service.ai.code.api_gen.ai_api_gen_service import AICodeApiGenService


router = APIRouter(
    prefix="/apigen",
    tags=["ai"],
    dependencies=[],
    responses={404: {"description": "찾을 수 없습니다."}},
)


@router.post("/generate")
async def api_generate(
    email: Annotated[UserModel, Depends(JwtBearer(only_email=True))],
    body: ApiGenerateInputs = Body(...),
) -> ApiGenerateOutputs:
    result = await AICodeApiGenService().invoke(email=email, inputs=body)
    return ApiGenerateOutputs(backend_code=result)
