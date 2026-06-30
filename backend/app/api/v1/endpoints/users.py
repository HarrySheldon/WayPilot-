from __future__ import annotations

from fastapi import APIRouter, Depends

from ....api.dependencies import get_current_user
from ....domain.users import User
from ....schemas.auth import CurrentUserResponse, user_to_response

router = APIRouter()


@router.get("/me", response_model=CurrentUserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return user_to_response(current_user)
