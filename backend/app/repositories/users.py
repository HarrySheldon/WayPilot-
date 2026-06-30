from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.users import User
from ..models.orm import UserORM


class SQLAlchemyUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, user: User) -> User:
        orm = self._session.get(UserORM, user.id)
        if orm is None:
            orm = UserORM(id=user.id, email=user.email, password_hash=user.password_hash)
            self._session.add(orm)

        orm.email = user.email
        orm.password_hash = user.password_hash
        orm.display_name = user.display_name
        self._session.flush()
        return user

    def get(self, user_id: str) -> User | None:
        orm = self._session.get(UserORM, user_id)
        return _user_to_domain(orm) if orm is not None else None

    def get_by_email(self, email: str) -> User | None:
        orm = self._session.scalars(select(UserORM).where(UserORM.email == email)).one_or_none()
        return _user_to_domain(orm) if orm is not None else None


def _user_to_domain(orm: UserORM) -> User:
    return User(
        id=orm.id,
        email=orm.email,
        password_hash=orm.password_hash,
        display_name=orm.display_name,
    )
