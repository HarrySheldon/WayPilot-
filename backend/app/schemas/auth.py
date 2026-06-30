from __future__ import annotations

from pydantic import BaseModel, Field

from ..domain.users import User
from ..services.auth import AuthResult


class LoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str


class CurrentUserResponse(BaseModel):
    id: str
    email: str
    display_name: str | None


def auth_result_to_response(result: AuthResult) -> AuthTokenResponse:
    return AuthTokenResponse(access_token=result.access_token, token_type=result.token_type)


def user_to_response(user: User) -> CurrentUserResponse:
    return CurrentUserResponse(id=user.id, email=user.email, display_name=user.display_name)
