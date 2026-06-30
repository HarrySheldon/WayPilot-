from __future__ import annotations

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.api import dependencies
from backend.app.core.security import PasswordHasher, TokenService
from backend.app.db.base import Base
from backend.app.db.session import get_db_session
from backend.app.domain.agents import AgentRunStatus
from backend.app.main import create_app
from backend.app.repositories.sqlalchemy import SQLAlchemyAgentRunRepository, SQLAlchemyTripRepository
from backend.app.repositories.users import SQLAlchemyUserRepository
from backend.app.services.auth import AuthService, RegisterUserInput
from backend.app.services.trips import TripCreateInput, TripService


class AgentGenerateApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.token_service = TokenService(secret_key="test-secret")
        self.dispatched_run_ids: list[str] = []
        self._seed_user(email="demo@example.com", password="password123", user_id="user-1")
        self._seed_trip(user_id="user-1", trip_id="trip-1")

        self.app = create_app()
        self.app.dependency_overrides[dependencies.get_repository_backend] = lambda: "sqlalchemy"
        self.app.dependency_overrides[dependencies.get_token_service] = lambda: self.token_service
        self.app.dependency_overrides[dependencies.get_agent_run_dispatcher] = lambda: self.dispatched_run_ids.append
        self.app.dependency_overrides[get_db_session] = self._override_session
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_generate_creates_pending_agent_run_and_dispatches_task(self) -> None:
        response = self.client.post(
            "/api/v1/trips/trip-1/generate",
            headers=self._auth_headers(),
            json={"message": "Plan a relaxed Tokyo food trip."},
        )

        self.assertEqual(response.status_code, 202, response.text)
        run_id = response.json()["agent_run_id"]
        self.assertEqual(self.dispatched_run_ids, [run_id])
        stored = self._get_run(run_id)
        self.assertIsNotNone(stored)
        self.assertEqual(stored.status, AgentRunStatus.PENDING)
        self.assertEqual(stored.user_message, "Plan a relaxed Tokyo food trip.")

        fetched = self.client.get(f"/api/v1/agent-runs/{run_id}", headers=self._auth_headers())
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["status"], "pending")

    def test_adjust_creates_pending_agent_run(self) -> None:
        response = self.client.post(
            "/api/v1/trips/trip-1/adjust",
            headers=self._auth_headers(),
            json={"message": "Make day two cheaper."},
        )

        self.assertEqual(response.status_code, 202, response.text)
        self.assertEqual(len(self.dispatched_run_ids), 1)
        self.assertEqual(self._get_run(response.json()["agent_run_id"]).status, AgentRunStatus.PENDING)

    def test_generate_requires_auth_token(self) -> None:
        response = self.client.post(
            "/api/v1/trips/trip-1/generate",
            json={"message": "Plan Tokyo"},
        )

        self.assertEqual(response.status_code, 401)

    def _seed_user(self, *, email: str, password: str, user_id: str) -> None:
        session = self.SessionLocal()
        AuthService(
            user_repository=SQLAlchemyUserRepository(session),
            password_hasher=PasswordHasher(),
            token_service=self.token_service,
            id_generator=lambda: user_id,
        ).register_user(data=RegisterUserInput(email=email, password=password))
        session.commit()
        session.close()

    def _seed_trip(self, *, user_id: str, trip_id: str) -> None:
        session = self.SessionLocal()
        TripService(
            trip_repository=SQLAlchemyTripRepository(session),
            id_generator=lambda: trip_id,
        ).create_trip(user_id=user_id, data=TripCreateInput(title="Tokyo", destination="Tokyo"))
        session.commit()
        session.close()

    def _get_run(self, run_id: str):
        session = self.SessionLocal()
        try:
            return SQLAlchemyAgentRunRepository(session).get(run_id)
        finally:
            session.close()

    def _auth_headers(self) -> dict[str, str]:
        token = self.token_service.create_access_token(user_id="user-1")
        return {"Authorization": f"Bearer {token}"}

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


if __name__ == "__main__":
    unittest.main()
