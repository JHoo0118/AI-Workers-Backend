import json
import asyncio
from typing import Any, Callable, Optional
from fastapi import Request
from sse_starlette import EventSourceResponse
from app.const.const import TASK_AI_API_GEN, TASK_AI_DOCS_SUMMARY_SERVE
from app.model.ai.code.api_gen.ai_api_gen_model import ApiGenerateInputs
from app.model.ai.docs.ai_docs_model import DocsSummaryServeInputs
from app.model.common.event_model import (
    EventModel,
    SSEEmitInputs,
    SSEEmitOutputs,
    SSEEvent,
)
from app.service.ai.code.api_gen.ai_api_gen_service import AICodeApiGenService
from app.service.ai.docs.ai_docs_serve_ver2_service import AIDocsServeVer2Service
from app.utils.datetime_utils import getNow


class SSEService(object):
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)

        return class_._instance

    def sse_emit(
        self,
        email: str,
        inputs: SSEEmitInputs,
    ) -> SSEEmitOutputs:
        event_model = EventModel(
            task_id=inputs.task_id,
            task_type=inputs.task_type,
            result=inputs.result,
            completed=inputs.completed,
            completed_at=inputs.completed_at,
            created_at=inputs.created_at,
            error=inputs.error,
            message=inputs.message,
            request_body=inputs.request_body,
        )
        SSEEvent.add_event(event_model)

        return SSEEmitOutputs(
            task_id=inputs.task_id,
            task_type=inputs.task_type,
            created_at=inputs.created_at,
            completed=inputs.completed,
            message="작업이 시작되었습니다.",
        )

    async def stream_events(
        self, email: str, request: Request, task_id: str
    ) -> EventSourceResponse:
        return EventSourceResponse(
            self.__stream_generator(email=email, request=request, task_id=task_id)
        )

    async def __stream_generator(self, email: str, request: Request, task_id: str):
        while True:
            if await request.is_disconnected():
                print("SSE Disconnected")
                break
            sse_event = SSEEvent.get_event(task_id=task_id)
            if sse_event:
                if sse_event.completed is not True:
                    yield sse_event.model_dump_json(by_alias=True)
                    result = await self.__do_task(
                        request=request,
                        email=email,
                        task_type=sse_event.task_type,
                        request_body=sse_event.request_body,
                    )
                    sse_event.result = result
                sse_event.completed = True
                sse_event.request_body = None
                sse_event.completed_at = getNow()
                yield sse_event.model_dump_json(by_alias=True)

            await asyncio.sleep(1)

    async def __do_task(
        self, request: Request, email: str, task_type: str, request_body: Any
    ):
        if task_type == TASK_AI_API_GEN and request_body is not None:
            request_body_json = json.loads(request_body)
            api_generate_inputs = ApiGenerateInputs(**request_body_json)
            return await AICodeApiGenService().invoke(
                email=email,
                inputs=api_generate_inputs,
            )
        elif task_type == TASK_AI_DOCS_SUMMARY_SERVE and request_body is not None:
            request_body_json = json.loads(request_body)
            docs_summary_serve_inputs = DocsSummaryServeInputs(**request_body_json)
            result = await AIDocsServeVer2Service(
                email
            ).summarize_text_by_page_for_stream(
                email=email,
                path=docs_summary_serve_inputs.path,
                ip=request.client.host,
            )
            return json.dumps(result, indent=4)
