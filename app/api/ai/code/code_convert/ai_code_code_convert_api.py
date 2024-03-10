from typing import Annotated
from fastapi import APIRouter, Body, Depends
from app.service.auth.jwt_bearer import JwtBearer
from app.service.ai.code.code_convert.ai_code_convert_service import (
    AICodeCodeConvertService,
)
from app.model.ai.code.code_convert.ai_code_convert_model import (
    CodeConvertGenerateInputs,
    CodeConvertGenerateOutputs,
)
from app.model.user.user_model import UserModel

router = APIRouter(
    prefix="/codeconvert",
    tags=["ai"],
    dependencies=[],
    responses={404: {"description": "찾을 수 없습니다."}},
)


@router.post("/generate")
async def code_convert_generate(
    email: Annotated[UserModel, Depends(JwtBearer(only_email=True))],
    body: CodeConvertGenerateInputs = Body(...),
) -> CodeConvertGenerateOutputs:
    pass
    result = await AICodeCodeConvertService().invoke_chain(email=email, inputs=body)
    return CodeConvertGenerateOutputs(result=result)
