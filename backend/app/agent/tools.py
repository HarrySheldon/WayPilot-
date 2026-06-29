from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ..domain.agents import ToolCall
from ..services.trip_candidates import TripCandidateCreateInput, TripCandidateService


class ToolExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ToolContext:
    user_id: str
    trip_id: str
    agent_run_id: str


class ToolCallRepository(Protocol):
    def next_id(self, agent_run_id: str) -> str:
        ...

    def save(self, call: ToolCall) -> ToolCall:
        ...

    def list_by_run(self, agent_run_id: str) -> list[ToolCall]:
        ...


class ToolRegistry:
    def __init__(
        self,
        *,
        candidate_service: TripCandidateService,
        tool_call_repository: ToolCallRepository,
    ) -> None:
        self._candidate_service = candidate_service
        self._tool_call_repository = tool_call_repository

    def execute(self, tool_name: str, *, context: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        if not context.user_id or not context.trip_id or not context.agent_run_id:
            raise ToolExecutionError("tool context must include user_id, trip_id, and agent_run_id")

        call = ToolCall(
            id=self._tool_call_repository.next_id(context.agent_run_id),
            agent_run_id=context.agent_run_id,
            tool_name=tool_name,
            arguments=dict(arguments),
        )
        self._tool_call_repository.save(call)

        try:
            result = self._execute(tool_name=tool_name, context=context, arguments=arguments)
        except Exception as exc:
            call.status = "error"
            call.error = str(exc)
            self._tool_call_repository.save(call)
            raise ToolExecutionError(str(exc)) from exc

        call.status = "success"
        call.result = result
        self._tool_call_repository.save(call)
        return result

    def list_tool_calls(self, *, agent_run_id: str):
        return self._tool_call_repository.list_by_run(agent_run_id)

    def _execute(self, *, tool_name: str, context: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "create_trip_candidate":
            candidate = self._candidate_service.create_candidate(
                user_id=context.user_id,
                trip_id=context.trip_id,
                data=TripCandidateCreateInput(
                    source_type=str(arguments["source_type"]),
                    source_agent_run_id=context.agent_run_id,
                    itinerary_snapshot=dict(arguments["itinerary_snapshot"]),
                    budget_snapshot=dict(arguments.get("budget_snapshot", {})),
                    preference_snapshot=dict(arguments.get("preference_snapshot", {})),
                ),
            )
            return {"candidate_id": candidate.id, "status": candidate.status}

        if tool_name == "validate_itinerary":
            candidate = self._candidate_service.validate_candidate(
                user_id=context.user_id,
                candidate_id=str(arguments["candidate_id"]),
            )
            return {
                "candidate_id": candidate.id,
                "status": candidate.status,
                "validation_summary": dict(candidate.validation_summary),
            }

        raise ToolExecutionError(f"unknown tool: {tool_name}")
