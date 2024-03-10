import json
import logging
import time

from typing import Callable
from uuid import uuid4
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.helper.async_interator_wrapper import AsyncIteratorWrapper


class RouterLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, *, logger: logging.Logger) -> None:
        self._logger = logger
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id: str = str(uuid4())
        logging_dict = {"X-API-REQUEST-ID": request_id}
        response, response_dict = await self.__log_response(
            call_next, request, request_id
        )
        request_dict = await self.__log_request(request)
        logging_dict["request"] = request_dict
        logging_dict["response"] = response_dict

        self._logger.info(logging_dict)

        return response

    async def __log_request(self, request: Request) -> str:
        path = request.url.path
        if request.query_params:
            path += f"?{request.query_params}"

        request_logging = {
            "method": request.method,
            "path": path,
            "ip": request.client.host,
        }

        try:
            body = await request.json()
            request_logging["body"] = body
        except:
            body = None

        return request_logging

    async def __log_response(
        self, call_next: Callable, request: Request, request_id: str
    ) -> Response:
        start_time = time.perf_counter()
        response = await self.__execute_request(call_next, request, request_id)
        finish_time = time.perf_counter()

        if response == None:
            return response, {"status": "failed", "status_code": 500}

        overall_status = "successful" if response.status_code < 400 else "failed"
        execution_time = finish_time - start_time

        response_logging = {
            "status": overall_status,
            "status_code": response.status_code,
            "time_taken": f"{execution_time:0.4f}s",
        }

        resp_body = [section async for section in response.__dict__["body_iterator"]]
        response.__setattr__("body_iterator", AsyncIteratorWrapper(resp_body))

        try:
            resp_body = json.loads(resp_body[0].decode())
        except:
            resp_body = str(resp_body)

        response_logging["body"] = resp_body

        return response, response_logging

    async def __execute_request(
        self, call_next: Callable, request: Request, request_id: str
    ) -> Response:
        try:
            response: Response = await call_next(request)

            # Kickback X-Request-ID
            response.headers["X-API-Request-ID"] = request_id
            return response

        except Exception as e:
            self._logger.exception(
                {"path": request.url.path, "method": request.method, "reason": e}
            )
