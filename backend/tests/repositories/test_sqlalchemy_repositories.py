from __future__ import annotations

import unittest

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.domain.conflicts import DeterministicConflictDetector
from backend.app.domain.agents import AgentRun, AgentRunStatus, AgentTrace, ToolCall
from backend.app.domain.rag import RagChunk, RagDocument
from backend.app.domain.trips import UserPreference
from backend.app.agent.rag import ControlledKnowledgeRetriever
from backend.app.models.orm import ItineraryItemORM, TripDayORM, TripORM, TripVersionORM, UserORM
from backend.app.repositories.sqlalchemy import (
    SQLAlchemyAgentRunRepository,
    SQLAlchemyAgentTraceRepository,
    SQLAlchemyPreferenceRepository,
    SQLAlchemyRagRepository,
    SQLAlchemyToolCallRepository,
    SQLAlchemyTransactionManager,
    SQLAlchemyTripCandidateRepository,
    SQLAlchemyTripRepository,
)
from backend.app.services.trip_candidates import TripCandidateCreateInput, TripCandidateService
from backend.app.services.trips import TripCreateInput, TripService


class FailingPublishedCandidateRepository(SQLAlchemyTripCandidateRepository):
    def save(self, candidate):
        if candidate.status == "published":
            raise RuntimeError("candidate publish status write failed")
        return super().save(candidate)


class SQLAlchemyRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self._enable_foreign_keys(self.engine)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def test_publish_candidate_persists_version_and_current_projection(self) -> None:
        session = self.SessionLocal()
        self._seed_user(session, "user-1")
        trip_repository = SQLAlchemyTripRepository(session)
        candidate_repository = SQLAlchemyTripCandidateRepository(session)
        trip_service = TripService(trip_repository=trip_repository, id_generator=lambda: "trip-1")
        candidate_service = TripCandidateService(
            trip_repository=trip_repository,
            candidate_repository=candidate_repository,
            conflict_detector=DeterministicConflictDetector(),
            transaction_manager=SQLAlchemyTransactionManager(session),
            id_generator=lambda: "candidate-1",
        )

        trip_service.create_trip(
            user_id="user-1",
            data=TripCreateInput(title="Tokyo", destination="Tokyo", budget_total=5000),
        )
        candidate_service.create_candidate(
            user_id="user-1",
            trip_id="trip-1",
            data=TripCandidateCreateInput(
                source_type="agent",
                itinerary_snapshot={
                    "days": [
                        {
                            "date": "2026-07-01",
                            "items": [
                                {
                                    "temp_id": "item-1",
                                    "title": "Visit Senso-ji",
                                    "start_time": "09:00",
                                    "end_time": "11:00",
                                }
                            ],
                        }
                    ]
                },
                budget_snapshot={"total": 1200, "currency": "JPY"},
                preference_snapshot={"pace": "standard"},
            ),
        )
        session.commit()

        version = candidate_service.publish_candidate(
            user_id="user-1",
            candidate_id="candidate-1",
            publish_note="Initial publish",
        )
        session.commit()
        session.expire_all()

        stored_trip = trip_repository.get("trip-1")
        stored_candidate = candidate_repository.get("candidate-1")
        day_count = session.scalar(select(func.count()).select_from(TripDayORM).where(TripDayORM.trip_id == "trip-1"))
        item_count = session.scalar(select(func.count()).select_from(ItineraryItemORM))

        self.assertEqual(version.version_no, 1)
        self.assertEqual(stored_trip.active_version_id, "trip-1-v1")
        self.assertEqual(stored_trip.versions[0].publish_note, "Initial publish")
        self.assertEqual(stored_trip.days[0].items[0].title, "Visit Senso-ji")
        self.assertEqual(stored_candidate.status, "published")
        self.assertEqual(day_count, 1)
        self.assertEqual(item_count, 1)

    def test_publish_candidate_rolls_back_when_late_write_fails(self) -> None:
        session = self.SessionLocal()
        self._seed_user(session, "user-1")
        trip_repository = SQLAlchemyTripRepository(session)
        candidate_repository = SQLAlchemyTripCandidateRepository(session)
        trip_service = TripService(trip_repository=trip_repository, id_generator=lambda: "trip-1")
        candidate_service = TripCandidateService(
            trip_repository=trip_repository,
            candidate_repository=candidate_repository,
            conflict_detector=DeterministicConflictDetector(),
            transaction_manager=SQLAlchemyTransactionManager(session),
            id_generator=lambda: "candidate-1",
        )
        trip_service.create_trip(user_id="user-1", data=TripCreateInput(title="Tokyo", destination="Tokyo"))
        candidate_service.create_candidate(
            user_id="user-1",
            trip_id="trip-1",
            data=TripCandidateCreateInput(
                source_type="agent",
                itinerary_snapshot={"days": [{"date": "2026-07-01", "items": [{"temp_id": "item-1", "title": "Museum"}]}]},
            ),
        )
        session.commit()
        session.close()

        failing_session = self.SessionLocal()
        failing_service = TripCandidateService(
            trip_repository=SQLAlchemyTripRepository(failing_session),
            candidate_repository=FailingPublishedCandidateRepository(failing_session),
            conflict_detector=DeterministicConflictDetector(),
            transaction_manager=SQLAlchemyTransactionManager(failing_session),
            id_generator=lambda: "unused",
        )

        with self.assertRaisesRegex(RuntimeError, "candidate publish status write failed"):
            failing_service.publish_candidate(user_id="user-1", candidate_id="candidate-1")

        inspect_session = self.SessionLocal()
        self.assertEqual(inspect_session.scalar(select(func.count()).select_from(TripVersionORM)), 0)
        self.assertEqual(inspect_session.scalar(select(func.count()).select_from(TripDayORM)), 0)
        self.assertEqual(SQLAlchemyTripRepository(inspect_session).get("trip-1").active_version_id, None)
        self.assertEqual(SQLAlchemyTripCandidateRepository(inspect_session).get("candidate-1").status, "draft")

    def test_preference_repository_round_trips_user_preferences(self) -> None:
        session = self.SessionLocal()
        self._seed_user(session, "user-1")
        repository = SQLAlchemyPreferenceRepository(session)

        repository.save(
            UserPreference(
                user_id="user-1",
                default_pace="slow",
                interests=["food", "museum"],
                dietary_preferences=["vegetarian"],
                avoidances=["nightlife"],
            )
        )
        session.commit()
        session.expire_all()

        stored = repository.get_by_user("user-1")

        self.assertIsNotNone(stored)
        self.assertEqual(stored.default_pace, "slow")
        self.assertEqual(stored.interests, ["food", "museum"])
        self.assertEqual(stored.dietary_preferences, ["vegetarian"])
        self.assertEqual(stored.avoidances, ["nightlife"])

    def test_agent_run_tool_call_and_trace_repositories_round_trip_auditable_records(self) -> None:
        session = self.SessionLocal()
        self._seed_user(session, "user-1")
        self._seed_trip(session, "trip-1", "user-1")
        run_repository = SQLAlchemyAgentRunRepository(session)
        tool_call_repository = SQLAlchemyToolCallRepository(session)
        trace_repository = SQLAlchemyAgentTraceRepository(session)

        run = AgentRun(id="run-1", user_id="user-1", trip_id="trip-1", user_message="Plan Tokyo")
        run.status = AgentRunStatus.RUNNING
        run.add_event("intent_extracted", "Intent extracted", payload={"destination": "Tokyo"})
        run_repository.save(run)
        tool_call_repository.save(
            ToolCall(
                id=tool_call_repository.next_id("run-1"),
                agent_run_id="run-1",
                tool_name="create_trip_candidate",
                arguments={"trip_id": "trip-1"},
                status="success",
                result={"candidate_id": "candidate-1"},
            )
        )
        run.status = AgentRunStatus.COMPLETED
        run.candidate_id = "candidate-1"
        run.add_event("candidate_created", "Candidate created", payload={"candidate_id": "candidate-1"})
        run_repository.save(run)
        trace_repository.save(
            AgentTrace(
                id="run-1-trace",
                agent_run_id="run-1",
                user_id="user-1",
                trip_id="trip-1",
                user_intent="Plan Tokyo",
                status="completed",
                candidate_id="candidate-1",
                rag_chunk_ids=["chunk-1"],
                tool_call_ids=["run-1-tool-1"],
            )
        )
        session.commit()
        session.expire_all()

        stored_run = run_repository.get("run-1")
        stored_calls = tool_call_repository.list_by_run("run-1")
        stored_trace = trace_repository.get_by_run("run-1")

        self.assertEqual(stored_run.status, AgentRunStatus.COMPLETED)
        self.assertEqual(stored_run.candidate_id, "candidate-1")
        self.assertEqual([event.type for event in stored_run.events], ["intent_extracted", "candidate_created"])
        self.assertEqual(stored_calls[0].result, {"candidate_id": "candidate-1"})
        self.assertEqual(tool_call_repository.next_id("run-1"), "run-1-tool-2")
        self.assertEqual(stored_trace.rag_chunk_ids, ["chunk-1"])
        self.assertEqual(stored_trace.tool_call_ids, ["run-1-tool-1"])

    def test_rag_repository_supports_controlled_user_scoped_retrieval(self) -> None:
        session = self.SessionLocal()
        self._seed_user(session, "user-1")
        self._seed_user(session, "user-2")
        repository = SQLAlchemyRagRepository(session)
        repository.save_document(
            RagDocument(
                id="doc-public",
                owner_user_id=None,
                source_type="city_guide",
                title="Tokyo guide",
                city="Tokyo",
                content="Tokyo ramen and temples",
            )
        )
        repository.save_chunk(RagChunk(id="chunk-public", document_id="doc-public", chunk_index=0, content="Tokyo ramen"))
        repository.save_document(
            RagDocument(
                id="doc-user-1",
                owner_user_id="user-1",
                source_type="user_preference",
                title="User 1 food",
                city="Tokyo",
                content="Likes ramen",
            )
        )
        repository.save_chunk(RagChunk(id="chunk-user-1", document_id="doc-user-1", chunk_index=0, content="User likes ramen"))
        repository.save_document(
            RagDocument(
                id="doc-user-2",
                owner_user_id="user-2",
                source_type="user_preference",
                title="User 2 private",
                city="Tokyo",
                content="Private sushi preference",
            )
        )
        repository.save_chunk(RagChunk(id="chunk-user-2", document_id="doc-user-2", chunk_index=0, content="Private sushi preference"))
        session.commit()
        session.expire_all()

        hits = ControlledKnowledgeRetriever(repository=repository).retrieve(
            user_id="user-1",
            query="Tokyo ramen",
            city="Tokyo",
        )

        self.assertEqual({hit.chunk_id for hit in hits}, {"chunk-public", "chunk-user-1"})

    def _seed_user(self, session: Session, user_id: str) -> None:
        session.add(
            UserORM(
                id=user_id,
                email=f"{user_id}@example.com",
                password_hash="not-used",
                display_name=user_id,
            )
        )
        session.commit()

    def _seed_trip(self, session: Session, trip_id: str, user_id: str) -> None:
        session.add(
            TripORM(
                id=trip_id,
                user_id=user_id,
                title="Tokyo",
                destination="Tokyo",
                travelers_count=1,
                status="draft",
            )
        )
        session.commit()

    def _enable_foreign_keys(self, engine) -> None:
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()


if __name__ == "__main__":
    unittest.main()
