from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.domain.users import User
from backend.app.repositories.users import SQLAlchemyUserRepository


class SQLAlchemyUserRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def test_save_and_get_user_by_id_and_email(self) -> None:
        session = self.SessionLocal()
        repository = SQLAlchemyUserRepository(session)

        repository.save(
            User(
                id="user-1",
                email="demo@example.com",
                password_hash="hashed-password",
                display_name="Demo User",
            )
        )
        session.commit()
        session.expire_all()

        by_id = repository.get("user-1")
        by_email = repository.get_by_email("demo@example.com")

        self.assertEqual(by_id.email, "demo@example.com")
        self.assertEqual(by_id.display_name, "Demo User")
        self.assertEqual(by_email.id, "user-1")
        self.assertEqual(by_email.password_hash, "hashed-password")

    def test_save_updates_existing_user_without_changing_id(self) -> None:
        session = self.SessionLocal()
        repository = SQLAlchemyUserRepository(session)
        repository.save(
            User(
                id="user-1",
                email="demo@example.com",
                password_hash="hashed-password",
                display_name="Demo User",
            )
        )
        session.commit()

        repository.save(
            User(
                id="user-1",
                email="updated@example.com",
                password_hash="new-hash",
                display_name="Updated",
            )
        )
        session.commit()
        session.expire_all()

        stored = repository.get("user-1")

        self.assertEqual(stored.email, "updated@example.com")
        self.assertEqual(stored.password_hash, "new-hash")
        self.assertEqual(stored.display_name, "Updated")

    def test_get_by_email_returns_none_for_missing_user(self) -> None:
        session = self.SessionLocal()
        repository = SQLAlchemyUserRepository(session)

        self.assertIsNone(repository.get_by_email("missing@example.com"))


if __name__ == "__main__":
    unittest.main()
