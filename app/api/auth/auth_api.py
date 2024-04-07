import os
from typing import Annotated
from fastapi import APIRouter, Body, Depends, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from app.model.auth.auth_model import (
    LogInOutputs,
    LoginGoogleOutputs,
    RefreshTokensInputs,
    RefreshTokensOutputs,
    SignUpInputs,
    SignUpOutputs,
)
from app.model.user.user_model import UserModel
from app.service.auth import AuthService, SupabaseAuthService
from app.service.auth.jwt_bearer import JwtBearer
from app.service.auth.auth_service import oauth2_scheme

ACCESS_TOKEN_MAX_AGE = 60 * 60 * 24 * 7
REFRESH_TOKEN_MAX_AGE = 60 * 60 * 24 * 7

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    dependencies=[],
    responses={404: {"description": "찾을 수 없습니다."}},
)


@router.post("/login")
async def login(
    response: Response, data: OAuth2PasswordRequestForm = Depends()
) -> LogInOutputs:
    # login_outputs: LogInOutputs = await AuthService().login(data)
    login_outputs: SignUpOutputs = await SupabaseAuthService().login(data)
    response.set_cookie(
        key="accessToken",
        value=login_outputs.access_token,
        # max_age=ACCESS_TOKEN_MAX_AGE,
    )
    response.set_cookie(
        key="refreshToken",
        value=login_outputs.refresh_token,
        # httponly=True,
        # max_age=REFRESH_TOKEN_MAX_AGE,
    )
    return login_outputs


@router.get("/login/google")
async def login_google() -> LoginGoogleOutputs:
    url: str = AuthService().login_google()
    # url: str = SupabaseAuthService().login_google()
    return LoginGoogleOutputs(url=url)


@router.get("/callback/google")
async def callback_google(response: RedirectResponse, code: str) -> Response:
    login_outputs = await AuthService().callback_google(code)
    # login_outputs = await SupabaseAuthService().callback_google(code)

    redirect_url = os.getenv("GOOGLE_REDIRECT_SUCCESS_URI")
    response = RedirectResponse(
        url=redirect_url,
        status_code=status.HTTP_302_FOUND,
    )
    response.set_cookie(
        key="accessToken",
        value=login_outputs.access_token,
        # max_age=ACCESS_TOKEN_MAX_AGE,
    )
    response.set_cookie(
        key="refreshToken",
        value=login_outputs.refresh_token,
        # max_age=REFRESH_TOKEN_MAX_AGE,
    )
    return response


@router.post("/signup")
async def sign_up(
    response: Response, sign_up_inputs: SignUpInputs = Body(...)
) -> SignUpOutputs:
    # sign_up_outputs: SignUpOutputs = await AuthService().sign_up(sign_up_inputs)
    sign_up_outputs: SignUpOutputs = await SupabaseAuthService().sign_up(sign_up_inputs)
    response.set_cookie(
        key="accessToken",
        value=sign_up_outputs.access_token,
        # max_age=ACCESS_TOKEN_MAX_AGE,
    )
    response.set_cookie(
        key="refreshToken",
        value=sign_up_outputs.refresh_token,
        # max_age=REFRESH_TOKEN_MAX_AGE,
    )
    return sign_up_outputs


@router.post("/logout")
async def logout(
    response: Response, email: Annotated[str, Depends(JwtBearer())]
) -> bool:
    response.delete_cookie(key="accessToken")
    response.delete_cookie(key="refreshToken")
    # return await AuthService().logout(email)
    return await SupabaseAuthService().logout(email)


# @router.post('/refresh-tokens', dependencies=[Depends(JwtBearer())])
@router.post("/refresh-tokens")
async def refresh_tokens(
    response: Response,
    refresh_token_inputs: RefreshTokensInputs,
) -> RefreshTokensOutputs:
    refresh_tokens_outputs: (
        RefreshTokensOutputs
    ) = await SupabaseAuthService().refresh_tokens(
        email=refresh_token_inputs.email, rt=refresh_token_inputs.refresh_token
    )
    response.set_cookie(
        key="accessToken",
        value=refresh_tokens_outputs.access_token,
        # max_age=ACCESS_TOKEN_MAX_AGE,
    )
    response.set_cookie(
        key="refreshToken",
        value=refresh_tokens_outputs.refresh_token,
        # max_age=REFRESH_TOKEN_MAX_AGE,
    )
    return refresh_tokens_outputs


@router.delete("/leave")
async def refresh_tokens(
    token: Annotated[str, Depends(oauth2_scheme)],
    email: Annotated[UserModel, Depends(JwtBearer(only_email=True))],
) -> bool:
    return await SupabaseAuthService().delete_account(token=token, email=email)
