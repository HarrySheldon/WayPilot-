from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ....api.dependencies import get_agent_run_repository, get_current_user_id, get_tool_call_repository
from ....repositories.memory import InMemoryAgentRunRepository, InMemoryToolCallRepository
from ....schemas.trips import (
    AgentRunEventResponse,
    AgentRunResponse,
    ToolCallResponse,
    agent_run_event_to_response,
    agent_run_to_response,
    tool_call_to_response,
)

router = APIRouter()


@router.get("/{run_id}", response_model=AgentRunResponse)
def get_agent_run(
    run_id: str,
    user_id: str = Depends(get_current_user_id),
    repository: InMemoryAgentRunRepository = Depends(get_agent_run_repository),
) -> AgentRunResponse:
    run = repository.get(run_id)
    if run is None or run.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    return agent_run_to_response(run)


@router.get("/{run_id}/events", response_model=list[AgentRunEventResponse])
def list_agent_run_events(
    run_id: str,
    user_id: str = Depends(get_current_user_id),
    repository: InMemoryAgentRunRepository = Depends(get_agent_run_repository),
) -> list[AgentRunEventResponse]:
    run = repository.get(run_id)
    if run is None or run.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    return [agent_run_event_to_response(event) for event in run.events]


@router.get("/{run_id}/tool-calls", response_model=list[ToolCallResponse])
def list_agent_run_tool_calls(
    run_id: str,
    user_id: str = Depends(get_current_user_id),
    run_repository: InMemoryAgentRunRepository = Depends(get_agent_run_repository),
    tool_call_repository: InMemoryToolCallRepository = Depends(get_tool_call_repository),
) -> list[ToolCallResponse]:
    run = run_repository.get(run_id)
    if run is None or run.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    return [tool_call_to_response(call) for call in tool_call_repository.list_by_run(run_id)]
