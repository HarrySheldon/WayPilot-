from __future__ import annotations

import unittest

from backend.app.agent.runtime import AgentRuntime
from backend.app.agent.structured_output import StructuredOutputValidator
from backend.app.agent.tools import ToolRegistry
from backend.app.domain.agents import AgentRun, AgentRunStatus
from backend.app.repositories.memory import (
    InMemoryAgentRunRepository,
    InMemoryToolCallRepository,
    InMemoryTripCandidateRepository,
    InMemoryTripRepository,
)
from backend.app.services.agent_runs import AgentRunInvalidStateError, AgentRunService
from backend.app.services.trip_candidates import TripCandidateService
from backend.app.services.trips import TripCreateInput, TripService


class NoopConflictDetector:
    def detect(self, *, itinerary_snapshot, budget_snapshot, preference_snapshot, trip):
        return []


class NoopRagRetriever:
    def retrieve(self, *, user_id: str, query: str, city: str | None = None, limit: int = 5):
        return []


class ScriptedProvider:
    def generate_itinerary(self, *, messages, rag_hits):
        return {
            "trip_summary": "Tokyo food and culture trip",
            "timezone": "Asia/Tokyo",
            "currency": "JPY",
            "assumptions": [],
            "days": [{"date": "2026-07-01", "city": "Tokyo", "items": []}],
            "budget_summary": {"total": 0},
            "rag_citations": [],
        }


class AgentRunServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.trips = InMemoryTripRepository()
        self.candidates = InMemoryTripCandidateRepository()
        self.agent_runs = InMemoryAgentRunRepository()
        self.tool_calls = InMemoryToolCallRepository()
        self.trip_service = TripService(trip_repository=self.trips, id_generator=lambda: "trip-1")
        self.trip = self.trip_service.create_trip(
            user_id="user-1",
            data=TripCreateInput(title="Tokyo", destination="Tokyo"),
        )
        self.candidate_service = TripCandidateService(
            trip_repository=self.trips,
            candidate_repository=self.candidates,
            conflict_detector=NoopConflictDetector(),
            id_generator=lambda: "candidate-1",
        )

    def test_request_generation_creates_pending_run_without_candidate(self) -> None:
        service = self._service(agent_executor=lambda run: run)

        run = service.request_generation(
            user_id="user-1",
            trip_id=self.trip.id,
            message="Plan a relaxed Tokyo trip.",
        )

        stored = self.agent_runs.get("run-1")
        self.assertEqual(run.status, AgentRunStatus.PENDING)
        self.assertIs(stored, run)
        self.assertEqual(run.user_id, "user-1")
        self.assertEqual(run.trip_id, self.trip.id)
        self.assertEqual(run.user_message, "Plan a relaxed Tokyo trip.")
        self.assertIn("run_queued", [event.type for event in run.events])
        self.assertEqual(self.candidates.list_by_trip(self.trip.id), [])

    def test_run_pending_agent_run_creates_candidate_but_does_not_publish(self) -> None:
        service = self._service(agent_executor=self._runtime_executor)
        requested = service.request_generation(
            user_id="user-1",
            trip_id=self.trip.id,
            message="Plan a relaxed Tokyo trip.",
        )

        completed = service.run_pending_agent_run(requested.id)

        candidate = self.candidates.get("candidate-1")
        self.assertEqual(completed.status, AgentRunStatus.COMPLETED)
        self.assertEqual(completed.candidate_id, "candidate-1")
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.status, "ready")
        self.assertIsNone(self.trip.active_version_id)
        self.assertEqual(self.trip.versions, [])
        self.assertEqual(
            [call.tool_name for call in self.tool_calls.list_by_run("run-1")],
            ["create_trip_candidate", "validate_itinerary"],
        )
        event_types = [event.type for event in completed.events]
        self.assertIn("run_queued", event_types)
        self.assertIn("run_started", event_types)
        self.assertIn("candidate_created", event_types)

    def test_cancel_allows_pending_and_running_but_rejects_completed(self) -> None:
        service = self._service(agent_executor=lambda run: run)
        pending = service.request_generation(user_id="user-1", trip_id=self.trip.id, message="Plan Tokyo")
        running = AgentRun(id="run-running", user_id="user-1", trip_id=self.trip.id, user_message="Plan Tokyo")
        running.status = AgentRunStatus.RUNNING
        completed = AgentRun(id="run-completed", user_id="user-1", trip_id=self.trip.id, user_message="Plan Tokyo")
        completed.status = AgentRunStatus.COMPLETED
        self.agent_runs.save(running)
        self.agent_runs.save(completed)

        self.assertEqual(service.cancel_run(user_id="user-1", run_id=pending.id).status, AgentRunStatus.CANCELLED)
        self.assertEqual(service.cancel_run(user_id="user-1", run_id=running.id).status, AgentRunStatus.CANCELLED)
        with self.assertRaises(AgentRunInvalidStateError):
            service.cancel_run(user_id="user-1", run_id=completed.id)

    def _service(self, *, agent_executor) -> AgentRunService:
        return AgentRunService(
            trip_service=self.trip_service,
            agent_run_repository=self.agent_runs,
            agent_executor=agent_executor,
            id_generator=lambda: "run-1",
        )

    def _runtime_executor(self, run: AgentRun) -> AgentRun:
        runtime = AgentRuntime(
            agent_run_repository=self.agent_runs,
            provider=ScriptedProvider(),
            rag_retriever=NoopRagRetriever(),
            tool_registry=ToolRegistry(
                candidate_service=self.candidate_service,
                tool_call_repository=self.tool_calls,
            ),
            output_validator=StructuredOutputValidator(),
            id_generator=lambda: run.id,
        )
        return runtime.generate_trip_candidate(
            user_id=run.user_id,
            trip_id=run.trip_id,
            user_message=run.user_message,
        )


if __name__ == "__main__":
    unittest.main()
