from __future__ import annotations

import unittest

from backend.app.agent.runtime import AgentRuntime
from backend.app.agent.structured_output import StructuredOutputValidator
from backend.app.agent.tools import ToolContext, ToolExecutionError, ToolRegistry
from backend.app.domain.agents import AgentRunStatus
from backend.app.repositories.memory import (
    InMemoryAgentRunRepository,
    InMemoryToolCallRepository,
    InMemoryTripCandidateRepository,
    InMemoryTripRepository,
)
from backend.app.services.trip_candidates import TripCandidateCreateInput, TripCandidateService
from backend.app.services.trips import TripCreateInput, TripService


class NoopConflictDetector:
    def detect(self, *, itinerary_snapshot, budget_snapshot, preference_snapshot, trip):
        return []


class ScriptedProvider:
    def __init__(self, output) -> None:
        self.output = output

    def generate_itinerary(self, *, messages, rag_hits):
        return self.output


class NoopRagRetriever:
    def retrieve(self, *, user_id: str, query: str, city: str | None = None, limit: int = 5):
        return []


class AgentRuntimeTests(unittest.TestCase):
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

    def test_runtime_creates_candidate_and_records_tool_calls_without_publishing(self) -> None:
        provider = ScriptedProvider(
            {
                "trip_summary": "Tokyo food and culture trip",
                "timezone": "Asia/Tokyo",
                "currency": "JPY",
                "assumptions": [],
                "days": [{"date": "2026-07-01", "city": "Tokyo", "items": []}],
                "budget_summary": {"total": 0},
                "rag_citations": [],
            }
        )
        runtime = AgentRuntime(
            agent_run_repository=self.agent_runs,
            provider=provider,
            rag_retriever=NoopRagRetriever(),
            tool_registry=ToolRegistry(
                candidate_service=self.candidate_service,
                tool_call_repository=self.tool_calls,
            ),
            output_validator=StructuredOutputValidator(),
            id_generator=lambda: "run-1",
        )

        run = runtime.generate_trip_candidate(
            user_id="user-1",
            trip_id=self.trip.id,
            user_message="Plan a relaxed Tokyo trip.",
        )

        candidate = self.candidates.get("candidate-1")
        self.assertEqual(run.status, AgentRunStatus.COMPLETED)
        self.assertEqual(run.candidate_id, "candidate-1")
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.status, "ready")
        self.assertIsNone(self.trip.active_version_id)
        self.assertEqual([call.tool_name for call in self.tool_calls.list_by_run("run-1")], ["create_trip_candidate", "validate_itinerary"])
        self.assertIn("candidate_created", [event.type for event in run.events])

    def test_runtime_fails_when_structured_output_is_invalid(self) -> None:
        runtime = AgentRuntime(
            agent_run_repository=self.agent_runs,
            provider=ScriptedProvider({"trip_summary": "Missing days"}),
            rag_retriever=NoopRagRetriever(),
            tool_registry=ToolRegistry(
                candidate_service=self.candidate_service,
                tool_call_repository=self.tool_calls,
            ),
            output_validator=StructuredOutputValidator(),
            id_generator=lambda: "run-1",
        )

        run = runtime.generate_trip_candidate(
            user_id="user-1",
            trip_id=self.trip.id,
            user_message="Plan a relaxed Tokyo trip.",
        )

        self.assertEqual(run.status, AgentRunStatus.FAILED)
        self.assertIsNone(run.candidate_id)
        self.assertEqual(self.candidates.list_by_trip(self.trip.id), [])
        self.assertIn("run_failed", [event.type for event in run.events])

    def test_tool_registry_enforces_trip_permissions_and_records_error(self) -> None:
        registry = ToolRegistry(candidate_service=self.candidate_service, tool_call_repository=self.tool_calls)

        with self.assertRaises(ToolExecutionError):
            registry.execute(
                "create_trip_candidate",
                context=ToolContext(user_id="user-2", trip_id=self.trip.id, agent_run_id="run-1"),
                arguments={
                    "source_type": "agent",
                    "itinerary_snapshot": {"days": []},
                    "budget_snapshot": {},
                    "preference_snapshot": {},
                },
            )

        calls = self.tool_calls.list_by_run("run-1")
        self.assertEqual(calls[0].status, "error")
        self.assertEqual(calls[0].tool_name, "create_trip_candidate")


if __name__ == "__main__":
    unittest.main()
