from __future__ import annotations

from typing import Protocol

from ..domain.agents import AgentRun, AgentRunStatus, UnifiedMessage
from .error_recovery import ErrorRecoveryPolicy
from .provider_openai_compatible import ProviderError
from .structured_output import StructuredOutputValidationError, StructuredOutputValidator
from .tools import ToolContext, ToolExecutionError, ToolRegistry
from .trace import TraceRecorder


class ProviderAdapter(Protocol):
    def generate_itinerary(self, *, messages: list[UnifiedMessage], rag_hits: list) -> dict:
        ...


class RagRetriever(Protocol):
    def retrieve(self, *, user_id: str, query: str, city: str | None = None, limit: int = 5) -> list:
        ...


class AgentRunRepository(Protocol):
    def get(self, run_id: str) -> AgentRun | None:
        ...

    def save(self, run: AgentRun) -> AgentRun:
        ...


class AgentRuntime:
    def __init__(
        self,
        *,
        agent_run_repository: AgentRunRepository,
        provider: ProviderAdapter,
        rag_retriever: RagRetriever,
        tool_registry: ToolRegistry,
        output_validator: StructuredOutputValidator,
        id_generator,
        trace_recorder: TraceRecorder | None = None,
        error_recovery_policy: ErrorRecoveryPolicy | None = None,
    ) -> None:
        self._agent_run_repository = agent_run_repository
        self._provider = provider
        self._rag_retriever = rag_retriever
        self._tool_registry = tool_registry
        self._output_validator = output_validator
        self._id_generator = id_generator
        self._trace_recorder = trace_recorder
        self._error_recovery_policy = error_recovery_policy or ErrorRecoveryPolicy()

    def generate_trip_candidate(self, *, user_id: str, trip_id: str, user_message: str) -> AgentRun:
        run_id = self._id_generator()
        run = self._agent_run_repository.get(run_id)
        if run is None:
            run = AgentRun(id=run_id, user_id=user_id, trip_id=trip_id, user_message=user_message)
        run.status = AgentRunStatus.RUNNING
        run.add_event("intent_extracted", "User request captured", payload={"message": user_message})
        self._agent_run_repository.save(run)
        rag_hits = []

        try:
            rag_hits = self._rag_retriever.retrieve(user_id=user_id, query=user_message)
            run.add_event("rag_retrieved", "RAG context retrieved", payload={"hit_count": len(rag_hits)})
            messages = [UnifiedMessage(role="user", content=user_message)]
            allowed_rag_chunk_ids = {str(getattr(hit, "chunk_id")) for hit in rag_hits if getattr(hit, "chunk_id", None)}
            validated_output = self._generate_validated_output(
                run=run,
                messages=messages,
                rag_hits=rag_hits,
                allowed_rag_chunk_ids=allowed_rag_chunk_ids,
            )

            run.status = AgentRunStatus.TOOL_CALLING
            context = ToolContext(user_id=user_id, trip_id=trip_id, agent_run_id=run.id)
            created = self._tool_registry.execute(
                "create_trip_candidate",
                context=context,
                arguments={
                    "source_type": "agent",
                    "itinerary_snapshot": validated_output,
                    "budget_snapshot": validated_output.get("budget_summary", {}),
                    "preference_snapshot": {"rag_citations": validated_output.get("rag_citations", [])},
                },
            )
            candidate_id = str(created["candidate_id"])
            self._tool_registry.execute(
                "validate_itinerary",
                context=context,
                arguments={"candidate_id": candidate_id},
            )
            run.candidate_id = candidate_id
            run.status = AgentRunStatus.COMPLETED
            run.add_event("candidate_created", "Candidate itinerary created", payload={"candidate_id": candidate_id})
        except (ProviderError, StructuredOutputValidationError, ToolExecutionError, ValueError) as exc:
            run.status = AgentRunStatus.FAILED
            run.error_message = str(exc)
            run.add_event("run_failed", "Agent run failed", detail=str(exc))

        self._agent_run_repository.save(run)
        if self._trace_recorder is not None:
            self._trace_recorder.record_run(run=run, rag_hits=rag_hits)
        return run

    def _generate_validated_output(
        self,
        *,
        run: AgentRun,
        messages: list[UnifiedMessage],
        rag_hits: list,
        allowed_rag_chunk_ids: set[str],
    ) -> dict:
        last_error: StructuredOutputValidationError | None = None
        for attempt in range(1, self._error_recovery_policy.max_model_attempts + 1):
            output = self._provider.generate_itinerary(messages=messages, rag_hits=rag_hits)
            try:
                return self._output_validator.validate(output, allowed_rag_chunk_ids=allowed_rag_chunk_ids)
            except StructuredOutputValidationError as exc:
                last_error = exc
                if attempt < self._error_recovery_policy.max_model_attempts:
                    run.add_event(
                        "structured_output_retry",
                        "Structured output invalid; retrying",
                        detail=str(exc),
                        payload={"attempt": attempt},
                    )
        raise last_error or StructuredOutputValidationError("structured output validation failed")
