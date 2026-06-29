from __future__ import annotations

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.api import dependencies
from backend.app.db.base import Base
from backend.app.db.session import get_db_session
from backend.app.main import create_app
from backend.app.models.orm import UserORM


class SQLAlchemyDependencyWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self._seed_user("demo-user")

        self.app = create_app()
        self.app.dependency_overrides[dependencies.get_repository_backend] = lambda: "sqlalchemy"
        self.app.dependency_overrides[dependencies.get_current_user_id] = lambda: "demo-user"
        self.app.dependency_overrides[get_db_session] = self._override_session
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_trip_api_uses_sqlalchemy_repository_backend_across_requests(self) -> None:
        created = self.client.post(
            "/api/v1/trips",
            json={
                "title": "Tokyo spring",
                "destination": "Tokyo",
                "travelers_count": 2,
                "budget_total": 3000,
                "pace": "standard",
                "interests": ["food"],
                "dietary_preferences": [],
                "must_visit_places": [],
                "avoidances": [],
                "natural_language_note": "",
            },
        )

        self.assertEqual(created.status_code, 201, created.text)
        trip_id = created.json()["id"]
        listed = self.client.get("/api/v1/trips")
        fetched = self.client.get(f"/api/v1/trips/{trip_id}")

        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual([trip["id"] for trip in listed.json()], [trip_id])
        self.assertEqual(fetched.json()["destination"], "Tokyo")

    def _override_session(self):
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _seed_user(self, user_id: str) -> None:
        session = self.SessionLocal()
        session.add(UserORM(id=user_id, email="demo@example.com", password_hash="not-used"))
        session.commit()
        session.close()


if __name__ == "__main__":
    unittest.main()
