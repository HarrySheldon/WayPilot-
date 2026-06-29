from __future__ import annotations

import unittest

from backend.app.agent.rag import ControlledKnowledgeRetriever
from backend.app.agent.runtime import AgentRuntime
from backend.app.agent.structured_output import StructuredOutputValidationError, StructuredOutputValidator
from backend.app.agent.tools import ToolRegistry
from backend.app.agent.trace import TraceRecorder
from backend.app.domain.rag import RagChunk, RagDocument
from backend.app.repositories.memory import (
    InMemoryAgentRunRepository,
    InMemoryAgentTraceRepository,
    InMemoryRagRepository,
    InMemoryToolCallRepository,
    InMemoryTripCandidateRepository,
    InMemoryTripRepository,
)
from backend.app.services.trip_candidates import TripCandidateService
from backend.app.services.trips import TripCreateInput, TripService


class NoopConflictDetector:
    def detect(self, *, itinerary_snapshot, budget_snapshot, preference_snapshot, trip):
        return []


class ScriptedProvider:
    def __init__(self, output) -> None:
        self.output = output

    def generate_itinerary(self, *, messages, rag_hits):
        return self.output


class RagAndTraceTests(unittest.TestCase):
    def test_retriever_returns_public_and_current_user_hits_only(self) -> None:
        repository = InMemoryRagRepository()
        repository.save_document(RagDocument(id="doc-public", owner_user_id=None, source_type="city_guide", title="Tokyo guide", city="Tokyo", content="Tokyo ramen and temples"))
        repository.save_chunk(RagChunk(id="chunk-public", document_id="doc-public", chunk_index=0, content="Tokyo ramen and temples"))
        repository.save_document(RagDocument(id="doc-user-1", owner_user_id="user-1", source_type="user_preference", title="User 1 food", city="Tokyo", content="Likes ramen"))
        repository.save_chunk(RagChunk(id="chunk-user-1", document_id="doc-user-1", chunk_index=0, content="User likes ramen"))
        repository.save_document(RagDocument(id="doc-user-2", owner_user_id="user-2", source_type="user_preference", title="User 2 private", city="Tokyo", content="Private sushi preference"))
        repository.save_chunk(RagChunk(id="chunk-user-2", document_id="doc-user-2", chunk_index=0, content="Private sushi preference"))

        hits = ControlledKnowledgeRetriever(repository=repository).retrieve(
            user_id="user-1",
            query="Tokyo ramen",
            city="Tokyo",
        )

        self.assertEqual({hit.chunk_id for hit in hits}, {"chunk-public", "chunk-user-1"})

    def test_structured_output_rejects_rag_citation_not_retrieved(self) -> None:
        output = {
            "trip_summary": "Tokyo",
            "days": [{"date": "2026-07-01", "items": []}],
            "rag_citations": [{"chunk_id": "chunk-other"}],
        }

        with self.assertRaises(StructuredOutputValidationError):
            StructuredOutputValidator().validate(output, allowed_rag_chunk_ids={"chunk-1"})

    def test_runtime_records_trace_with_rag_hits_and_candidate_id(self) -> None:
        trips = InMemoryTripRepository()
        candidates = InMemoryTripCandidateRepository()
        agent_runs = InMemoryAgentRunRepository()
        tool_calls = InMemoryToolCallRepository()
        traces = InMemoryAgentTraceRepository()
        rag_repository = InMemoryRagRepository()
        rag_repository.save_document(RagDocument(id="doc-public", owner_user_id=None, source_type="city_guide", title="Tokyo guide", city="Tokyo", content="Tokyo ramen"))
        rag_repository.save_chunk(RagChunk(id="chunk-public", document_id="doc-public", chunk_index=0, content="Tokyo ramen"))
        trip = TripService(trip_repository=trips, id_generator=lambda: "trip-1").create_trip(
            user_id="user-1",
            data=TripCreateInput(title="Tokyo", destination="Tokyo"),
        )
        candidate_service = TripCandidateService(
            trip_repository=trips,
            candidate_repository=candidates,
            conflict_detector=NoopConflictDetector(),
            id_generator=lambda: "candidate-1",
        )
        runtime = AgentRuntime(
            agent_run_repository=agent_runs,
            provider=ScriptedProvider(
                {
                    "trip_summary": "Tokyo ramen trip",
                    "days": [{"date": "2026-07-01", "items": []}],
                    "budget_summary": {"total": 0},
                    "rag_citations": [{"chunk_id": "chunk-public"}],
                }
            ),
            rag_retriever=ControlledKnowledgeRetriever(repository=rag_repository),
            tool_registry=ToolRegistry(candidate_service=candidate_service, tool_call_repository=tool_calls),
            output_validator=StructuredOutputValidator(),
            trace_recorder=TraceRecorder(trace_repository=traces, tool_call_repository=tool_calls),
            id_generator=lambda: "run-1",
        )

        runtime.generate_trip_candidate(
            user_id="user-1",
            trip_id=trip.id,
            user_message="Plan Tokyo ramen",
        )

        trace = traces.get_by_run("run-1")
        self.assertIsNotNone(trace)
        self.assertEqual(trace.candidate_id, "candidate-1")
        self.assertEqual(trace.rag_chunk_ids, ["chunk-public"])
        self.assertEqual(trace.tool_call_ids, ["run-1-tool-1", "run-1-tool-2"])


if __name__ == "__main__":
    unittest.main()
