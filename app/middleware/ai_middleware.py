from fastapi import FastAPI, Request
from fastapi import security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

from app.service.auth.auth_service import AuthService
from app.service.auth.jwt_bearer import JwtBearer
from app.service.user.user_service import UserService


class AIMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.jwt_bearer = JwtBearer()
        self.userService = UserService()

    async def dispatch(self, request: Request, call_next):
        try:
            if (
                request.url.path.startswith("/api/ai")
                and not request.url.path.startswith("/api/ai/docs/summary")
            ) or request.url.path.startswith("/api/sse"):
                email: str = await self.jwt_bearer(request)
                await self.userService.recalculate_remain_count(email)
            response = await call_next(request)
            return response
        except Exception as e:
            return JSONResponse(
                status_code=400, content={"detail": str(e.detail if e.detail else e)}
            )
