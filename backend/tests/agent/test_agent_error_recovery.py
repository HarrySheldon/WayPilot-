from __future__ import annotations

import unittest

from backend.app.agent.error_recovery import ErrorRecoveryPolicy
from backend.app.agent.provider_openai_compatible import ProviderError
from backend.app.agent.runtime import AgentRuntime
from backend.app.agent.structured_output import StructuredOutputValidator
from backend.app.agent.tools import ToolRegistry
from backend.app.domain.agents import AgentRunStatus
from backend.app.repositories.memory import (
    InMemoryAgentRunRepository,
    InMemoryToolCallRepository,
    InMemoryTripCandidateRepository,
    InMemoryTripRepository,
)
from backend.app.services.trip_candidates import TripCandidateService
from backend.app.services.trips import TripCreateInput, TripService


class NoopConflictDetector:
    def detect(self, *, itinerary_snapshot, budget_snapshot, preference_snapshot, trip):
        return []


class NoopRagRetriever:
    def retrieve(self, *, user_id: str, query: str, city: str | None = None, limit: int = 5):
        return []


class SequenceProvider:
    def __init__(self, outputs: list[dict]) -> None:
        self.outputs = list(outputs)
        self.calls = 0

    def generate_itinerary(self, *, messages, rag_hits):
        self.calls += 1
        return self.outputs.pop(0)


class FailingProvider:
    def generate_itinerary(self, *, messages, rag_hits):
        raise ProviderError("model unavailable")


class AgentErrorRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.trips = InMemoryTripRepository()
        self.candidates = InMemoryTripCandidateRepository()
        self.agent_runs = InMemoryAgentRunRepository()
        self.tool_calls = InMemoryToolCallRepository()
        self.trip = TripService(trip_repository=self.trips, id_generator=lambda: "trip-1").create_trip(
            user_id="user-1",
            data=TripCreateInput(title="Tokyo", destination="Tokyo"),
        )
        self.candidate_service = TripCandidateService(
            trip_repository=self.trips,
            candidate_repository=self.candidates,
            conflict_detector=NoopConflictDetector(),
            id_generator=lambda: "candidate-1",
        )

    def test_runtime_retries_once_after_invalid_structured_output(self) -> None:
        provider = SequenceProvider(
            [
                {"trip_summary": "Missing days"},
                {
                    "trip_summary": "Tokyo",
                    "days": [{"date": "2026-07-01", "items": []}],
                    "rag_citations": [],
                },
            ]
        )
        runtime = self._runtime(provider)

        run = runtime.generate_trip_candidate(
            user_id="user-1",
            trip_id=self.trip.id,
            user_message="Plan Tokyo",
        )

        self.assertEqual(provider.calls, 2)
        self.assertEqual(run.status, AgentRunStatus.COMPLETED)
        self.assertEqual(run.candidate_id, "candidate-1")
        self.assertIn("structured_output_retry", [event.type for event in run.events])

    def test_runtime_fails_after_persistent_invalid_structured_output(self) -> None:
        provider = SequenceProvider(
            [
                {"trip_summary": "Missing days"},
                {"trip_summary": "Still missing days"},
            ]
        )
        runtime = self._runtime(provider)

        run = runtime.generate_trip_candidate(
            user_id="user-1",
            trip_id=self.trip.id,
            user_message="Plan Tokyo",
        )

        self.assertEqual(provider.calls, 2)
        self.assertEqual(run.status, AgentRunStatus.FAILED)
        self.assertIsNone(run.candidate_id)
        self.assertEqual(self.candidates.list_by_trip(self.trip.id), [])
        self.assertIn("run_failed", [event.type for event in run.events])

    def test_runtime_marks_run_failed_when_provider_raises_model_error(self) -> None:
        runtime = self._runtime(FailingProvider())

        run = runtime.generate_trip_candidate(
            user_id="user-1",
            trip_id=self.trip.id,
            user_message="Plan Tokyo",
        )

        self.assertEqual(run.status, AgentRunStatus.FAILED)
        self.assertEqual(run.error_message, "model unavailable")
        self.assertIn("run_failed", [event.type for event in run.events])

    def _runtime(self, provider) -> AgentRuntime:
        return AgentRuntime(
            agent_run_repository=self.agent_runs,
            provider=provider,
            rag_retriever=NoopRagRetriever(),
            tool_registry=ToolRegistry(
                candidate_service=self.candidate_service,
                tool_call_repository=self.tool_calls,
            ),
            output_validator=StructuredOutputValidator(),
            error_recovery_policy=ErrorRecoveryPolicy(max_model_attempts=2),
            id_generator=lambda: "run-1",
        )


if __name__ == "__main__":
    unittest.main()
