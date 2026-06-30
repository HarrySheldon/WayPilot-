from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ....api.dependencies import get_auth_service
from ....schemas.auth import AuthTokenResponse, LoginRequest, auth_result_to_response
from ....services.auth import AuthInvalidCredentialsError, AuthService, LoginInput

router = APIRouter()


@router.post("/login", response_model=AuthTokenResponse)
def login(
    request: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> AuthTokenResponse:
    try:
        result = service.authenticate_user(
            data=LoginInput(email=request.email, password=request.password)
        )
    except AuthInvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return auth_result_to_response(result)
