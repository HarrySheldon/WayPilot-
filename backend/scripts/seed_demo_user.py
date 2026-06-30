from __future__ import annotations

from sqlalchemy.orm import Session

try:
    from backend.app.core.config import settings
    from backend.app.core.security import PasswordHasher, TokenService
    from backend.app.db.session import SessionLocal
    from backend.app.domain.users import User
    from backend.app.repositories.users import SQLAlchemyUserRepository
    from backend.app.services.auth import AuthService, RegisterUserInput
except ModuleNotFoundError:
    from app.core.config import settings
    from app.core.security import PasswordHasher, TokenService
    from app.db.session import SessionLocal
    from app.domain.users import User
    from app.repositories.users import SQLAlchemyUserRepository
    from app.services.auth import AuthService, RegisterUserInput


def seed_demo_user(
    *,
    session: Session,
    email: str = "demo@example.com",
    password: str = "password123",
    user_id: str = "demo-user",
    display_name: str = "Demo User",
) -> User:
    repository = SQLAlchemyUserRepository(session)
    normalized_email = email.strip().lower()
    existing = repository.get_by_email(normalized_email)
    if existing is not None:
        return existing

    return AuthService(
        user_repository=repository,
        password_hasher=PasswordHasher(),
        token_service=TokenService(secret_key=settings.jwt_secret_key),
        id_generator=lambda: user_id,
    ).register_user(
        data=RegisterUserInput(
            email=normalized_email,
            password=password,
            display_name=display_name,
        )
    )


def main() -> None:
    session = SessionLocal()
    try:
        user = seed_demo_user(session=session)
        session.commit()
        print(f"seeded demo user: {user.email} ({user.id})")
    finally:
        session.close()


if __name__ == "__main__":
    main()
