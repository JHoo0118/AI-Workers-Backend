from typing import Annotated
from fastapi import APIRouter, Body, Depends
from fastapi.responses import StreamingResponse

from app.model.user.user_model import UserModel
from app.service.auth.jwt_bearer import JwtBearer
from app.model.ai.db.ai_sql_model import SqlGenerateInputs, SqlGenerateOutputs
from app.service.ai.db.gen.ai_sql_gen_service import AISqlGenService


router = APIRouter(
    prefix="/sql",
    tags=["ai"],
    dependencies=[],
    responses={404: {"description": "찾을 수 없습니다."}},
)


@router.post("/generate")
async def generate_sql(
    email: Annotated[UserModel, Depends(JwtBearer(only_email=True))],
    body: SqlGenerateInputs = Body(...),
) -> StreamingResponse:

    lastMessage = body.messages[-1]

    return StreamingResponse(
        AISqlGenService(email).invoke_chain(
            email=email,
            message=lastMessage.content,
        ),
    )
