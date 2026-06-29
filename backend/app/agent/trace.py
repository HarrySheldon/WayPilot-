from __future__ import annotations

from typing import Protocol

from ..domain.agents import AgentRun, AgentTrace
from ..domain.rag import RagHit


class AgentTraceRepository(Protocol):
    def save(self, trace: AgentTrace) -> AgentTrace:
        ...


class ToolCallReader(Protocol):
    def list_by_run(self, agent_run_id: str) -> list:
        ...


class TraceRecorder:
    def __init__(
        self,
        *,
        trace_repository: AgentTraceRepository,
        tool_call_repository: ToolCallReader,
    ) -> None:
        self._trace_repository = trace_repository
        self._tool_call_repository = tool_call_repository

    def record_run(self, *, run: AgentRun, rag_hits: list[RagHit]) -> AgentTrace:
        trace = AgentTrace(
            id=f"{run.id}-trace",
            agent_run_id=run.id,
            user_id=run.user_id,
            trip_id=run.trip_id,
            user_intent=run.user_message,
            status=str(run.status),
            candidate_id=run.candidate_id,
            rag_chunk_ids=[hit.chunk_id for hit in rag_hits],
            tool_call_ids=[call.id for call in self._tool_call_repository.list_by_run(run.id)],
            error_message=run.error_message,
        )
        return self._trace_repository.save(trace)
