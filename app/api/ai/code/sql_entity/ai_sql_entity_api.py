from typing import Annotated
from fastapi import APIRouter, Body, Depends
from app.service.auth.jwt_bearer import JwtBearer
from app.model.user.user_model import UserModel
from app.model.ai.code.sql_entity.ai_sql_entity_model import (
    SqlToEntityGenerateInputs,
    SqlToEntityGenerateOutputs,
)
from app.service.ai.code.sql_entity.ai_sql_service import AICodeSqlService

router = APIRouter(
    prefix="/sqlentity",
    tags=["ai"],
    dependencies=[],
    responses={404: {"description": "찾을 수 없습니다."}},
)


@router.post("/generate")
async def sql_to_entity(
    email: Annotated[UserModel, Depends(JwtBearer(only_email=True))],
    body: SqlToEntityGenerateInputs = Body(...),
) -> SqlToEntityGenerateOutputs:
    result = await AICodeSqlService().invoke_chain(email=email, inputs=body)
    return SqlToEntityGenerateOutputs(result=result)
