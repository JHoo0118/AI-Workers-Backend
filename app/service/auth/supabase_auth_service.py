import os
import requests
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Annotated
from prisma.models import User
from prisma.errors import UniqueViolationError

from app.db.prisma import prisma
from app.model.auth.auth_model import (
    LogInOutputs,
    RefreshTokensOutputs,
    SignUpInputs,
    SignUpOutputs,
)
from app.model.user.user_model import UserModel
from app.service.auth.jwt_service import JwtService
from app.service.user.user_service import UserService

from app.const.const import SIGNUP_TYPE_GOOGLE
from app.db.supabase import SupabaseService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")


class SupabaseAuthService(object):
    _instance = None

    _jwtService: JwtService = None
    _userService: UserService = None
    _supabaseService: SupabaseService = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)

        return class_._instance

    def __init__(self) -> None:
        self._jwtService = JwtService()
        self._userService = UserService()
        self._supabaseService = SupabaseService()

    async def authenticate_user(self, email: str, password: str) -> UserModel:
        user = await self._userService.get_user(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="존재하지 않는 이메일이거나 비밀번호가 틀렸습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif not self._userService.verify_hash(password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비밀번호가 틀렸습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    def hash_refresh_token(self, encoded_jwt: str) -> str:
        return self._userService.get_hash(encoded_jwt)

    async def logout(self, email: str) -> bool:
        try:
            # prisma.refreshtoken.delete(where={"userEmail": email})
            self._supabaseService.supabase.auth.sign_out()
            return True
        except:
            return False

    async def get_current_user(
        self, token: Annotated[str, Depends(oauth2_scheme)]
    ) -> UserModel:
        email = await self._jwtService.verify_token(
            token=token, token_key=self._jwtService.access_token_key
        )

        user = await self._userService.get_user(email=email)
        if user is None:
            raise self._jwtService.credentials_exception
        return user

    async def get_current_active_user(
        current_user: Annotated[UserModel, Depends(get_current_user)]
    ):
        if current_user.disabled:
            raise HTTPException(status_code=400, detail="Inactive user")
        return current_user

    async def login(self, data: OAuth2PasswordRequestForm = Depends()):
        email = data.username
        password = data.password

        try:
            res = self._supabaseService.supabase.auth.sign_in_with_password(
                {
                    "email": email,
                    "password": password,
                }
            )

            # user = await self.authenticate_user(email=email, password=password)

            # access_token, refresh_token = self._jwtService.get_tokens(
            #     data={"sub": user.email},
            # )

            # await self.update_rt_hash(email=user.email, rt=refresh_token)

            return LogInOutputs(
                access_token=res.session.access_token,
                refresh_token=res.session.refresh_token,
            )
        except Exception as e:
            print(e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="아이디 또는 비밀번호를 확인해 주세요.",
            )

    def login_google(self) -> str:
        # return f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope=openid%20profile%20email&access_type=offline"
        res = self._supabaseService.supabase.auth.sign_in_with_oauth(
            credentials={
                "provider": "google",
                "options": {
                    "redirect_to": GOOGLE_REDIRECT_URI,
                },
            }
        )
        return res.url

    async def callback_google(self, code: str) -> LogInOutputs:
        forbbiden_exception = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="인증에 실패했습니다.",
        )
        try:
            token_url = "https://accounts.google.com/o/oauth2/token"
            data = {
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
                "scope": [
                    # "https://www.googleapis.com/auth/userinfo.profile",
                    "https://www.googleapis.com/auth/userinfo.email",
                    "openid",
                ],
            }
            response = requests.post(token_url, data=data)
            access_token = response.json().get("access_token")
            if access_token is None:
                raise forbbiden_exception
            user_info = requests.get(
                "https://www.googleapis.com/oauth2/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_info_json: dict = user_info.json()
            email = user_info_json.get("email")
            with prisma.tx() as transaction:
                user: User = transaction.user.find_unique(where={"email": email})
                if user is None:
                    transaction.user.create(
                        data={
                            "email": email,
                            "username": email,
                            "type": SIGNUP_TYPE_GOOGLE,
                        }
                    )
                # access_token, refresh_token = self._jwtService.get_tokens(
                #     data={"sub": email},
                # )

            # await self.update_rt_hash(email=user.email, rt=refresh_token)

            return LogInOutputs(
                access_token=access_token,
                # refresh_token=refresh_token,
            )

        except Exception as e:
            raise forbbiden_exception

    async def sign_up(self, sign_up_inputs: SignUpInputs) -> SignUpOutputs:
        try:
            email = sign_up_inputs.email
            password = sign_up_inputs.password
            with prisma.tx() as transaction:
                sign_up_inputs.password = self._userService.get_hash(
                    sign_up_inputs.password
                )
                data = sign_up_inputs.model_dump()
                data.pop("password")
                transaction.user.create(data)

            res = self._supabaseService.supabase.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                }
            )
            return SignUpOutputs(
                access_token=res.session.access_token,
                refresh_token=res.session.refresh_token,
            )
        except UniqueViolationError as e:
            errTarget = (
                "이메일" if str(e.data["error"]).find("email") != -1 else "사용자명"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"이미 존재하는 {errTarget}입니다.",
            )

    async def refresh_tokens(self, email: str, rt: str) -> RefreshTokensOutputs:

        try:
            res = self._supabaseService.supabase.auth.refresh_session(refresh_token=rt)
            return RefreshTokensOutputs(
                access_token=res.session.access_token,
                refresh_token=res.session.refresh_token,
            )
        except Exception as e:
            res = self._supabaseService.supabase.auth.get_session()
            return RefreshTokensOutputs(
                access_token=res.access_token,
                refresh_token=res.refresh_token,
            )
