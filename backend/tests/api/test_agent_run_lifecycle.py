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
from backend.app.domain.agents import AgentRun, AgentRunStatus
from backend.app.main import create_app
from backend.app.repositories.sqlalchemy import SQLAlchemyAgentRunRepository, SQLAlchemyTripRepository
from backend.app.repositories.users import SQLAlchemyUserRepository
from backend.app.services.auth import AuthService, RegisterUserInput
from backend.app.services.trips import TripCreateInput, TripService


class AgentRunLifecycleApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.token_service = TokenService(secret_key="test-secret")
        self._seed_user(email="demo@example.com", password="password123", user_id="user-1")
        self._seed_trip(user_id="user-1", trip_id="trip-1")
        self._seed_run(run_id="pending-run", status=AgentRunStatus.PENDING)
        self._seed_run(run_id="running-run", status=AgentRunStatus.RUNNING)
        self._seed_run(run_id="completed-run", status=AgentRunStatus.COMPLETED)

        self.app = create_app()
        self.app.dependency_overrides[dependencies.get_repository_backend] = lambda: "sqlalchemy"
        self.app.dependency_overrides[dependencies.get_token_service] = lambda: self.token_service
        self.app.dependency_overrides[get_db_session] = self._override_session
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_cancel_marks_pending_and_running_runs_cancelled(self) -> None:
        pending = self.client.post("/api/v1/agent-runs/pending-run/cancel", headers=self._auth_headers())
        running = self.client.post("/api/v1/agent-runs/running-run/cancel", headers=self._auth_headers())

        self.assertEqual(pending.status_code, 200, pending.text)
        self.assertEqual(running.status_code, 200, running.text)
        self.assertEqual(pending.json()["status"], "cancelled")
        self.assertEqual(running.json()["status"], "cancelled")

    def test_cancel_rejects_completed_run(self) -> None:
        response = self.client.post("/api/v1/agent-runs/completed-run/cancel", headers=self._auth_headers())

        self.assertEqual(response.status_code, 409, response.text)

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

    def _seed_run(self, *, run_id: str, status: AgentRunStatus) -> None:
        session = self.SessionLocal()
        run = AgentRun(id=run_id, user_id="user-1", trip_id="trip-1", user_message="Plan Tokyo")
        run.status = status
        SQLAlchemyAgentRunRepository(session).save(run)
        session.commit()
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
