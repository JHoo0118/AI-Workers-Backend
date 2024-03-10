from fastapi import APIRouter, Body, Depends
from typing import Annotated

from app.model.user.user_model import UserModel
from app.service.auth.jwt_bearer import JwtBearer
from app.model.ai.diagram.seq_diagram.ai_diagram_seq_diagram_model import (
    SeqDiagramGenerateInputs,
    SeqDiagramGenerateOutputs,
)
from app.service.ai.diagram.seq_diagram.ai_diagram_seq_diagram_service import (
    AIDiagramSeqDiagramService,
)


router = APIRouter(
    prefix="/seqdiagram",
    tags=["ai"],
    dependencies=[],
    responses={404: {"description": "찾을 수 없습니다."}},
)


@router.post("/generate")
async def seq_diagram_generate(
    email: Annotated[UserModel, Depends(JwtBearer(only_email=True))],
    body: SeqDiagramGenerateInputs = Body(...),
) -> SeqDiagramGenerateOutputs:
    result = await AIDiagramSeqDiagramService().invoke(email=email, inputs=body)
    return SeqDiagramGenerateOutputs(image=result)
