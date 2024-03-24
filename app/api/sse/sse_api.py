import asyncio
from typing import Annotated, Any
from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import StreamingResponse
from sse_starlette import EventSourceResponse

from app.model.common.event_model import (
    EventModel,
    SSEEmitInputs,
    SSEEmitOutputs,
    SSEEvent,
)
from app.model.user.user_model import UserModel
from app.service.auth.jwt_bearer import JwtBearer
from app.service.sse.sse_service import SSEService


router = APIRouter(
    prefix="/sse",
    tags=["sse"],
    dependencies=[],
    responses={404: {"description": "찾을 수 없습니다."}},
)


@router.post("/emit", response_model=SSEEmitOutputs)
def sse_emit(
    email: Annotated[UserModel, Depends(JwtBearer(only_email=True))],
    body: SSEEmitInputs = Body(...),
) -> SSEEmitOutputs:
    return SSEService().sse_emit(email, body)


@router.get("/stream/{task_id}", response_class=StreamingResponse)
async def stream_events(
    email: Annotated[UserModel, Depends(JwtBearer(only_email=True))],
    request: Request,
    task_id: str,
) -> EventSourceResponse:
    return await SSEService().stream_events(
        email=email, request=request, task_id=task_id
    )
