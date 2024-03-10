from typing import Annotated
from fastapi import APIRouter, Depends, Request, Response, UploadFile, Body
from fastapi.responses import StreamingResponse

from app.model.user.user_model import UserModel
from app.service.ai.docs.ai_docs_service import AIDocsService
from app.service.auth.jwt_bearer import JwtBearer
from app.service.ai.docs.ai_docs_agent_service import AIDocsAgentService
from app.model.ai.docs.ai_docs_model import DocsSummaryAskInputs, DocsSummaryAskOutputs
from app.service.auth.auth_service import oauth2_scheme


router = APIRouter(
    prefix="/docs",
    tags=["ai"],
    dependencies=[],
    responses={404: {"description": "찾을 수 없습니다."}},
)


@router.post("/summary")
def docs_summary(
    request: Request,
    email: Annotated[UserModel, Depends(JwtBearer(only_email=True))],
    file: UploadFile,
    token: str = Depends(oauth2_scheme),
) -> bool:
    if file is None:
        return False
    AIDocsService(email).embed_file(
        email=email,
        file=file,
        ip=request.client.host,
        jwt=f"Bearer {request.cookies['accessToken']}",
    )
    return True


@router.post("/ask/{filename}")
async def docs_summary_ask(
    request: Request,
    email: Annotated[UserModel, Depends(JwtBearer(only_email=True))],
    filename: str,
    body: DocsSummaryAskInputs = Body(...),
) -> StreamingResponse:
    lastMessage = body.messages[-1]

    return StreamingResponse(
        AIDocsService(email).invoke_chain(
            email=email,
            filename=filename,
            message=lastMessage.content,
            ip=request.client.host,
        ),
    )


@router.post("/summary/agent")
async def docs_summary_agent(
    request: Request,
    email: Annotated[UserModel, Depends(JwtBearer(only_email=True))],
    file: UploadFile,
    token: str = Depends(oauth2_scheme),
) -> bool:
    if file is None:
        return False

    AIDocsAgentService(email).embed_file(
        email=email,
        file=file,
        ip=request.client.host,
        jwt=f"Bearer {request.cookies['accessToken']}",
    )
    return True


@router.post("/ask/agent/{filename}")
async def docs_summary_ask_agent(
    request: Request,
    email: Annotated[UserModel, Depends(JwtBearer(only_email=True))],
    filename: str,
    body: DocsSummaryAskInputs = Body(...),
) -> Response:
    lastMessage = body.messages[-1]

    result = await AIDocsAgentService(email).invoke_chain(
        email=email,
        filename=filename,
        message=lastMessage.content,
        ip=request.client.host,
    )

    return Response(content=result)
