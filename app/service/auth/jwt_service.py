import os

from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from jose import JWTError, jwt


class JwtService(object):
    access_token_expire_minutes = 1  # 30
    refresh_token_expire_minutes = 60 * 24 * 30

    access_token_key = os.getenv("ACCESS_TOKEN_KEY")
    refresh_token_key = os.getenv("REFRESH_TOKEN_KEY")
    algorithm = os.getenv("ALGORITHM")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="토큰이 유효하지 않거나 만기된 토큰입니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)

        return class_._instance

    def create_access_token(self, data: dict) -> str:
        to_encode = self.__get_to_encode(data.copy(), self.access_token_expire_minutes)
        encoded_jwt = jwt.encode(
            to_encode, self.access_token_key, algorithm=self.algorithm
        )
        return encoded_jwt

    def create_refresh_token(self, data: dict) -> str:
        to_encode = self.__get_to_encode(data.copy(), self.refresh_token_expire_minutes)
        encoded_jwt = jwt.encode(
            to_encode, self.refresh_token_key, algorithm=self.algorithm
        )
        return encoded_jwt

    def get_tokens(self, data: dict):
        return self.create_access_token(data), self.create_refresh_token(data)

    async def verify_token(self, token: str, token_key: str) -> str:
        try:
            # print(token, token_key, self.algorithm)
            payload = jwt.decode(
                token,
                key=token_key,
                algorithms=[self.algorithm],
                audience="authenticated",
            )
            # email: str = payload.get("sub")
            # supabase
            # user_metadata = payload.get("user_metadata", {})
            # app_metadata = payload.get("app_metadata", {})
            email = payload.get("email")
            # super_id = payload.get("sub")
            # provider = app_metadata.get("provider")
            # username = user_metadata.get("username")
            email: str = payload.get("email")
            if email is None:
                raise self.credentials_exception
            return email
        except JWTError:
            raise self.credentials_exception

    def __get_to_encode(self, data: dict, expire_minutes: int) -> dict:
        expires_delta = timedelta(minutes=expire_minutes)

        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        return to_encode
