from __future__ import annotations

from uuid import uuid4

from backend.app.agent.rag import ControlledKnowledgeRetriever
from backend.app.agent.runtime import AgentRuntime
from backend.app.agent.structured_output import StructuredOutputValidator
from backend.app.agent.tools import ToolRegistry
from backend.app.agent.trace import TraceRecorder
from backend.app.db.session import SessionLocal
from backend.app.domain.rag import RagChunk, RagDocument
from backend.app.models.orm import UserORM
from backend.app.repositories.sqlalchemy import (
    SQLAlchemyAgentRunRepository,
    SQLAlchemyAgentTraceRepository,
    SQLAlchemyRagRepository,
    SQLAlchemyToolCallRepository,
    SQLAlchemyTransactionManager,
    SQLAlchemyTripCandidateRepository,
    SQLAlchemyTripRepository,
)
from backend.app.services.trip_candidates import TripCandidateService
from backend.app.services.trips import TripCreateInput, TripService


class NoopConflictDetector:
    def detect(self, *, itinerary_snapshot, budget_snapshot, preference_snapshot, trip):
        return []


class ScriptedProvider:
    def __init__(self, output: dict) -> None:
        self.output = output

    def generate_itinerary(self, *, messages, rag_hits) -> dict:
        return self.output


def main() -> None:
    suffix = uuid4().hex[:8]
    user_id = f"smoke-user-{suffix}"
    trip_id = f"smoke-trip-{suffix}"
    run_id = f"smoke-run-{suffix}"
    candidate_id = f"smoke-candidate-{suffix}"
    doc_id = f"smoke-doc-{suffix}"
    chunk_id = f"smoke-chunk-{suffix}"

    session = SessionLocal()
    try:
        session.add(
            UserORM(
                id=user_id,
                email=f"{user_id}@example.com",
                password_hash="not-used",
                display_name="Smoke User",
            )
        )
        session.commit()

        trip_repository = SQLAlchemyTripRepository(session)
        candidate_repository = SQLAlchemyTripCandidateRepository(session)
        agent_runs = SQLAlchemyAgentRunRepository(session)
        tool_calls = SQLAlchemyToolCallRepository(session)
        traces = SQLAlchemyAgentTraceRepository(session)
        rag_repository = SQLAlchemyRagRepository(session)

        trip = TripService(trip_repository=trip_repository, id_generator=lambda: trip_id).create_trip(
            user_id=user_id,
            data=TripCreateInput(title="Tokyo smoke", destination="Tokyo"),
        )
        rag_repository.save_document(
            RagDocument(
                id=doc_id,
                owner_user_id=None,
                source_type="city_guide",
                title="Tokyo guide",
                city="Tokyo",
                content="Tokyo ramen",
            )
        )
        rag_repository.save_chunk(
            RagChunk(id=chunk_id, document_id=doc_id, chunk_index=0, content="Tokyo ramen")
        )

        runtime = AgentRuntime(
            agent_run_repository=agent_runs,
            provider=ScriptedProvider(
                {
                    "trip_summary": "Tokyo ramen trip",
                    "days": [{"date": "2026-07-01", "items": []}],
                    "budget_summary": {"total": 0},
                    "rag_citations": [{"chunk_id": chunk_id}],
                }
            ),
            rag_retriever=ControlledKnowledgeRetriever(repository=rag_repository),
            tool_registry=ToolRegistry(
                candidate_service=TripCandidateService(
                    trip_repository=trip_repository,
                    candidate_repository=candidate_repository,
                    conflict_detector=NoopConflictDetector(),
                    transaction_manager=SQLAlchemyTransactionManager(session),
                    id_generator=lambda: candidate_id,
                ),
                tool_call_repository=tool_calls,
            ),
            output_validator=StructuredOutputValidator(),
            trace_recorder=TraceRecorder(trace_repository=traces, tool_call_repository=tool_calls),
            id_generator=lambda: run_id,
        )

        run = runtime.generate_trip_candidate(
            user_id=user_id,
            trip_id=trip.id,
            user_message="Plan Tokyo ramen",
        )
        session.commit()
        session.expire_all()

        stored_candidate = candidate_repository.get(candidate_id)
        stored_trace = traces.get_by_run(run_id)
        stored_calls = tool_calls.list_by_run(run_id)

        print("run", str(run.status), run.candidate_id)
        print("candidate", stored_candidate.status)
        print("tool_calls", [call.tool_name for call in stored_calls])
        print("trace", stored_trace.rag_chunk_ids, stored_trace.tool_call_ids)
    finally:
        session.close()


if __name__ == "__main__":
    main()
