from __future__ import annotations

from typing import Callable, Protocol
from uuid import uuid4

from ..agent.runtime import AgentRuntime
from ..agent.seed_provider import SeedItineraryProvider
from ..agent.structured_output import StructuredOutputValidator
from ..agent.tools import ToolRegistry
from ..agent.trace import TraceRecorder
from ..domain.agents import AgentRun, AgentRunStatus
from ..rag.embeddings import DeterministicEmbeddingProvider
from ..rag.vector_retriever import VectorRagRetriever
from ..services.trips import TripService
from .trip_candidates import TripCandidateService


class AgentRunNotFoundError(LookupError):
    pass


class AgentRunInvalidStateError(RuntimeError):
    pass


class AgentRunRepository(Protocol):
    def save(self, run: AgentRun) -> AgentRun:
        ...

    def get(self, run_id: str) -> AgentRun | None:
        ...


class ToolCallRepository(Protocol):
    def next_id(self, agent_run_id: str) -> str:
        ...

    def save(self, call) -> object:
        ...

    def list_by_run(self, agent_run_id: str) -> list:
        ...


class RagRepository(Protocol):
    def list_chunks(self) -> list:
        ...

    def get_document(self, document_id: str):
        ...


class AgentTraceRepository(Protocol):
    def save(self, trace) -> object:
        ...


class AgentProvider(Protocol):
    def generate_itinerary(self, *, messages: list, rag_hits: list) -> dict:
        ...


class RagRetriever(Protocol):
    def retrieve(self, *, user_id: str, query: str, city: str | None = None, limit: int = 5) -> list:
        ...


AgentExecutor = Callable[[AgentRun], AgentRun]


class AgentRunService:
    def __init__(
        self,
        *,
        trip_service: TripService,
        agent_run_repository: AgentRunRepository,
        agent_executor: AgentExecutor,
        id_generator: Callable[[], str] | None = None,
    ) -> None:
        self._trip_service = trip_service
        self._agent_run_repository = agent_run_repository
        self._agent_executor = agent_executor
        self._id_generator = id_generator or (lambda: str(uuid4()))

    def request_generation(self, *, user_id: str, trip_id: str, message: str) -> AgentRun:
        return self._request_run(user_id=user_id, trip_id=trip_id, message=message, request_type="generate")

    def request_adjustment(self, *, user_id: str, trip_id: str, message: str) -> AgentRun:
        return self._request_run(user_id=user_id, trip_id=trip_id, message=message, request_type="adjust")

    def get_run(self, *, user_id: str, run_id: str) -> AgentRun:
        run = self._agent_run_repository.get(run_id)
        if run is None or run.user_id != user_id:
            raise AgentRunNotFoundError(f"agent run not found: {run_id}")
        return run

    def cancel_run(self, *, user_id: str, run_id: str) -> AgentRun:
        run = self.get_run(user_id=user_id, run_id=run_id)
        if run.status in {AgentRunStatus.COMPLETED, AgentRunStatus.FAILED}:
            raise AgentRunInvalidStateError(f"agent run cannot be cancelled from status: {run.status}")
        if run.status == AgentRunStatus.CANCELLED:
            return run
        run.status = AgentRunStatus.CANCELLED
        run.add_event("run_cancelled", "Agent run cancelled")
        return self._agent_run_repository.save(run)

    def run_pending_agent_run(self, run_id: str) -> AgentRun:
        run = self._agent_run_repository.get(run_id)
        if run is None:
            raise AgentRunNotFoundError(f"agent run not found: {run_id}")
        if run.status == AgentRunStatus.CANCELLED:
            return run
        if run.status != AgentRunStatus.PENDING:
            raise AgentRunInvalidStateError(f"agent run must be pending, got: {run.status}")

        run.status = AgentRunStatus.RUNNING
        run.add_event("run_started", "Agent run started")
        self._agent_run_repository.save(run)
        try:
            completed = self._agent_executor(run)
        except Exception as exc:
            latest = self._agent_run_repository.get(run.id) or run
            latest.status = AgentRunStatus.FAILED
            latest.error_message = str(exc)
            latest.add_event("run_failed", "Agent run failed", detail=str(exc))
            return self._agent_run_repository.save(latest)

        return self._agent_run_repository.save(completed)

    def _request_run(self, *, user_id: str, trip_id: str, message: str, request_type: str) -> AgentRun:
        normalized_message = message.strip()
        if not normalized_message:
            raise ValueError("message is required")
        self._trip_service.get_trip(user_id=user_id, trip_id=trip_id)
        run = AgentRun(
            id=self._id_generator(),
            user_id=user_id,
            trip_id=trip_id,
            user_message=normalized_message,
        )
        run.add_event("run_queued", "Agent run queued", payload={"request_type": request_type})
        return self._agent_run_repository.save(run)


def build_agent_executor(
    *,
    agent_run_repository: AgentRunRepository,
    candidate_service: TripCandidateService,
    tool_call_repository: ToolCallRepository,
    rag_repository: RagRepository,
    trace_repository: AgentTraceRepository,
    provider: AgentProvider | None = None,
    rag_retriever: RagRetriever | None = None,
) -> AgentExecutor:
    selected_provider = provider or SeedItineraryProvider()
    selected_retriever = rag_retriever or VectorRagRetriever(
        repository=rag_repository,
        embedding_provider=DeterministicEmbeddingProvider(),
    )

    def execute(run: AgentRun) -> AgentRun:
        runtime = AgentRuntime(
            agent_run_repository=agent_run_repository,
            provider=selected_provider,
            rag_retriever=selected_retriever,
            tool_registry=ToolRegistry(
                candidate_service=candidate_service,
                tool_call_repository=tool_call_repository,
            ),
            output_validator=StructuredOutputValidator(),
            id_generator=lambda: run.id,
            trace_recorder=TraceRecorder(
                trace_repository=trace_repository,
                tool_call_repository=tool_call_repository,
            ),
        )
        return runtime.generate_trip_candidate(
            user_id=run.user_id,
            trip_id=run.trip_id,
            user_message=run.user_message,
        )

    return execute
