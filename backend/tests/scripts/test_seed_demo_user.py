from __future__ import annotations

import unittest

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.models.orm import UserORM
from backend.scripts.seed_demo_user import seed_demo_user


class SeedDemoUserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def test_seed_demo_user_creates_hashed_user_once(self) -> None:
        session = self.SessionLocal()

        first = seed_demo_user(session=session, email="Demo@Example.com", password="password123")
        second = seed_demo_user(session=session, email="demo@example.com", password="password123")
        session.commit()

        user_count = session.scalar(select(func.count()).select_from(UserORM))

        self.assertEqual(first.id, "demo-user")
        self.assertEqual(second.id, "demo-user")
        self.assertEqual(first.email, "demo@example.com")
        self.assertNotEqual(first.password_hash, "password123")
        self.assertEqual(user_count, 1)


if __name__ == "__main__":
    unittest.main()
