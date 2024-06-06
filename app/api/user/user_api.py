from typing import Annotated
from fastapi import APIRouter, Depends


from app.model.user.user_model import (
    UpdateUserInputs,
    UpdateUserOutputs,
    UserModel,
    CreateUserInputs,
    CreateUserOutputs,
)
from app.service.auth.jwt_bearer import JwtBearer
from app.service.user.user_service import UserService


router = APIRouter(
    prefix="/user",
    tags=["user"],
    dependencies=[],
    responses={404: {"description": "찾을 수 없습니다."}},
)


@router.post("/create", response_model=CreateUserOutputs)
async def create_user(create_user_inputs: CreateUserInputs):
    user = await UserService().create_user(create_user_inputs)

    return CreateUserOutputs(**user.model_dump())


@router.post("/update", response_model=UpdateUserOutputs)
async def create_user(update_user_inputs: UpdateUserInputs):
    user = await UserService().update_user(update_user_inputs)

    return CreateUserOutputs(**user.model_dump())


@router.get("/me", response_model=UserModel)
async def read_users_me(
    current_user: Annotated[UserModel, Depends(JwtBearer(only_email=False))]
):
    return current_user


@router.post("remain", response_model=UserModel)
async def recalculate_remain_count(
    email: Annotated[UserModel, Depends(JwtBearer(only_email=True))]
):
    return await UserService().recalculate_remain_count(email=email)
