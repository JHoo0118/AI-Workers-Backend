from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.service.auth.auth_service import AuthService

from app.service.auth.jwt_service import JwtService


class JwtBearer(HTTPBearer):
    _jwtService: JwtService = None
    _authService: AuthService = None
    _verify_func = None
    _only_email: bool = True

    def __init__(self, only_email: bool = True, auto_error: bool = True):
        super(JwtBearer, self).__init__(auto_error=auto_error)
        self._jwtService = JwtService()
        self._authService = AuthService()
        self._only_email = only_email

        if only_email:
            self._verify_func = self._jwtService.verify_token
        else:
            self._verify_func = self._authService.get_current_user

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(
            JwtBearer, self
        ).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=403, detail="Invalid authentication scheme."
                )
            payload = await self.verify_jwt(credentials.credentials)
            if not payload:
                raise HTTPException(
                    status_code=409, detail="토큰이 유효하지 않거나 만기된 토큰입니다."
                )
            return payload
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")

    async def verify_jwt(self, token: str) -> bool:
        try:
            if self._only_email:
                payload = await self._jwtService.verify_token(
                    token, self._jwtService.access_token_key
                )
            else:
                payload = await self._authService.get_current_user(token)
        except:
            payload = None
        return payload
