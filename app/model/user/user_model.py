from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from prisma.models import User


class UserModel(User):
    email: EmailStr = Field("Email")


class CreateUserInputs(BaseModel):
    email: EmailStr = Field("Email")
    password: str = Field("Password")
    username: str = Field("Username")


class CreateUserOutputs(UserModel):
    pass


class UpdateUserInputs(BaseModel):
    email: EmailStr = Field("Email")
    username: Optional[str] = Field("Username")


class UpdateUserOutputs(UserModel):
    pass
