from fastapi import APIRouter, Body, Depends
from typing import Annotated

from app.model.user.user_model import UserModel
from app.service.auth.jwt_bearer import JwtBearer
from app.service.ai.diagram.erd.ai_diagram_erd_service import AIDiagramErdService
from app.model.ai.diagram.erd.ai_diagram_erd_model import (
    ErdGenerateInputs,
    ErdGenerateOutputs,
)


router = APIRouter(
    prefix="/erd",
    tags=["ai"],
    dependencies=[],
    responses={404: {"description": "찾을 수 없습니다."}},
)


@router.post("/generate")
async def erd_generate(
    email: Annotated[UserModel, Depends(JwtBearer(only_email=True))],
    body: ErdGenerateInputs = Body(...),
) -> ErdGenerateOutputs:
    result = await AIDiagramErdService().invoke(email=email, inputs=body)
    return ErdGenerateOutputs(image=result)
