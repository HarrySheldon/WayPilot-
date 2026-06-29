from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AgentRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    TOOL_CALLING = "tool_calling"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class UnifiedToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class UnifiedMessage:
    role: str
    content: str
    tool_calls: list[UnifiedToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRunEvent:
    id: str
    agent_run_id: str
    type: str
    title: str
    detail: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    id: str
    agent_run_id: str
    tool_name: str
    arguments: dict[str, Any]
    status: str = "pending"
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class AgentRun:
    id: str
    user_id: str
    trip_id: str
    user_message: str
    status: AgentRunStatus = AgentRunStatus.PENDING
    candidate_id: str | None = None
    error_message: str | None = None
    events: list[AgentRunEvent] = field(default_factory=list)

    def add_event(self, event_type: str, title: str, detail: str = "", payload: dict[str, Any] | None = None) -> None:
        self.events.append(
            AgentRunEvent(
                id=f"{self.id}-event-{len(self.events) + 1}",
                agent_run_id=self.id,
                type=event_type,
                title=title,
                detail=detail,
                payload=payload or {},
            )
        )


@dataclass
class AgentTrace:
    id: str
    agent_run_id: str
    user_id: str
    trip_id: str
    user_intent: str
    status: str
    candidate_id: str | None
    rag_chunk_ids: list[str] = field(default_factory=list)
    tool_call_ids: list[str] = field(default_factory=list)
    error_message: str | None = None
