from __future__ import annotations

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.api import dependencies
from backend.app.db.base import Base
from backend.app.db.session import get_db_session
from backend.app.domain.agents import AgentRun, AgentRunStatus, ToolCall
from backend.app.main import create_app
from backend.app.models.orm import UserORM, UserPreferenceORM
from backend.app.repositories.sqlalchemy import (
    SQLAlchemyAgentRunRepository,
    SQLAlchemyToolCallRepository,
    SQLAlchemyTripRepository,
)
from backend.app.services.trips import TripCreateInput, TripService


class SQLAlchemyDependencyWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self._enable_foreign_keys(self.engine)
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

    def test_preference_api_uses_sqlalchemy_repository_backend(self) -> None:
        upserted = self.client.put(
            "/api/v1/preferences",
            json={
                "default_pace": "slow",
                "interests": ["food", "museum"],
                "dietary_preferences": ["vegetarian"],
                "avoidances": ["crowds"],
            },
        )
        fetched = self.client.get("/api/v1/preferences")

        self.assertEqual(upserted.status_code, 200, upserted.text)
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["interests"], ["food", "museum"])
        session = self.SessionLocal()
        try:
            stored = session.get(UserPreferenceORM, "demo-user")
            self.assertIsNotNone(stored)
            self.assertEqual(stored.default_pace, "slow")
        finally:
            session.close()

    def test_agent_run_api_uses_sqlalchemy_repositories(self) -> None:
        session = self.SessionLocal()
        trip = TripService(
            trip_repository=SQLAlchemyTripRepository(session),
            id_generator=lambda: "trip-1",
        ).create_trip(user_id="demo-user", data=TripCreateInput(title="Tokyo", destination="Tokyo"))
        run = AgentRun(id="run-1", user_id="demo-user", trip_id=trip.id, user_message="Plan Tokyo")
        run.status = AgentRunStatus.COMPLETED
        run.candidate_id = "candidate-1"
        run.add_event("candidate_created", "Candidate created", payload={"candidate_id": "candidate-1"})
        SQLAlchemyAgentRunRepository(session).save(run)
        SQLAlchemyToolCallRepository(session).save(
            ToolCall(
                id="run-1-tool-1",
                agent_run_id="run-1",
                tool_name="create_trip_candidate",
                arguments={"trip_id": "trip-1"},
                status="success",
                result={"candidate_id": "candidate-1"},
            )
        )
        session.commit()
        session.close()

        fetched_run = self.client.get("/api/v1/agent-runs/run-1")
        fetched_events = self.client.get("/api/v1/agent-runs/run-1/events")
        fetched_tool_calls = self.client.get("/api/v1/agent-runs/run-1/tool-calls")

        self.assertEqual(fetched_run.status_code, 200, fetched_run.text)
        self.assertEqual(fetched_run.json()["candidate_id"], "candidate-1")
        self.assertEqual(fetched_events.status_code, 200, fetched_events.text)
        self.assertEqual(fetched_events.json()[0]["type"], "candidate_created")
        self.assertEqual(fetched_tool_calls.status_code, 200, fetched_tool_calls.text)
        self.assertEqual(fetched_tool_calls.json()[0]["result"], {"candidate_id": "candidate-1"})

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

    def _enable_foreign_keys(self, engine) -> None:
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()


if __name__ == "__main__":
    unittest.main()
