from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol
from uuid import uuid4

from ..core.security import PasswordHasher, TokenService
from ..domain.users import User


class AuthValidationError(ValueError):
    pass


class AuthConflictError(ValueError):
    pass


class AuthInvalidCredentialsError(ValueError):
    pass


class UserRepository(Protocol):
    def save(self, user: User) -> User:
        ...

    def get(self, user_id: str) -> User | None:
        ...

    def get_by_email(self, email: str) -> User | None:
        ...


@dataclass(frozen=True)
class RegisterUserInput:
    email: str
    password: str
    display_name: str | None = None


@dataclass(frozen=True)
class LoginInput:
    email: str
    password: str


@dataclass(frozen=True)
class AuthResult:
    access_token: str
    token_type: str
    user: User


class AuthService:
    def __init__(
        self,
        *,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
        id_generator: Callable[[], str] | None = None,
    ) -> None:
        self._user_repository = user_repository
        self._password_hasher = password_hasher
        self._token_service = token_service
        self._id_generator = id_generator or (lambda: str(uuid4()))

    def register_user(self, *, data: RegisterUserInput) -> User:
        email = _normalize_email(data.email)
        _validate_password(data.password)
        if self._user_repository.get_by_email(email) is not None:
            raise AuthConflictError("email already registered")

        user = User(
            id=self._id_generator(),
            email=email,
            password_hash=self._password_hasher.hash(data.password),
            display_name=_normalize_optional_text(data.display_name),
        )
        return self._user_repository.save(user)

    def authenticate_user(self, *, data: LoginInput) -> AuthResult:
        email = _normalize_email(data.email)
        user = self._user_repository.get_by_email(email)
        if user is None or not self._password_hasher.verify(data.password, user.password_hash):
            raise AuthInvalidCredentialsError("invalid email or password")

        return AuthResult(
            access_token=self._token_service.create_access_token(user_id=user.id),
            token_type="bearer",
            user=user,
        )


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not normalized or "@" not in normalized:
        raise AuthValidationError("valid email is required")
    return normalized


def _validate_password(password: str) -> None:
    if len(password) < 8:
        raise AuthValidationError("password must be at least 8 characters")


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
