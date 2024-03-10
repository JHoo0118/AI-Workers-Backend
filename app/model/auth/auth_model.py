from pydantic import BaseModel, EmailStr, Field
from app.model.base_model import BaseSchema


class LogInOutputs(BaseSchema):
    access_token: str = Field()
    refresh_token: str = Field()


class LoginGoogleOutputs(BaseModel):
    url: str = Field("url")


class SignUpInputs(BaseModel):
    email: EmailStr = Field("Email")
    password: str = Field("Password")
    username: str = Field("Username")


class SignUpOutputs(LogInOutputs):
    pass


class RefreshTokensInputs(BaseSchema):
    email: EmailStr = Field("email")
    refresh_token: str = Field()


class RefreshTokensOutputs(LogInOutputs):
    pass
