from fastapi import APIRouter, Body, Depends
from typing import Annotated

from fastapi.responses import StreamingResponse

from app.model.ai.code.algorithm.ai_algorithm_advisor_model import (
    AlgorithmAdviceGenerateInputs,
    AlgorithmAdviceGenerateOutputs,
)
from app.model.user.user_model import UserModel
from app.service.ai.code.algorithm.ai_algorithm_advisor_service import (
    AIAlgorithmAdvisorService,
)
from app.service.auth.jwt_bearer import JwtBearer


router = APIRouter(
    prefix="/algorithm",
    tags=["ai"],
    dependencies=[],
    responses={404: {"description": "찾을 수 없습니다."}},
)


# @router.post("/generate")
# async def algorithm_advice_generate(
#     email: Annotated[UserModel, Depends(JwtBearer(only_email=True))],
#     body: AlgorithmAdviceGenerateInputs = Body(...),
# ) -> AlgorithmAdviceGenerateOutputs:
#     result = await AIAlgorithmAdvisorService().invoke(email=email, inputs=body)
#     return AlgorithmAdviceGenerateOutputs(result=result)


@router.post("/generate")
async def generate_algorithm_advice(
    email: Annotated[UserModel, Depends(JwtBearer(only_email=True))],
    body: AlgorithmAdviceGenerateInputs = Body(...),
) -> StreamingResponse:

    lastMessage = body.messages[-1]

    return StreamingResponse(
        AIAlgorithmAdvisorService(email).invoke_chain(
            email=email,
            lang=body.lang,
            message=lastMessage.content,
        ),
    )
