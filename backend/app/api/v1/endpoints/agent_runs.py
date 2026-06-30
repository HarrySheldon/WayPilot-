from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ....api.dependencies import get_agent_run_service, get_current_user_id, get_tool_call_repository
from ....schemas.trips import (
    AgentRunEventResponse,
    AgentRunResponse,
    ToolCallResponse,
    agent_run_event_to_response,
    agent_run_to_response,
    tool_call_to_response,
)
from ....services.agent_runs import AgentRunInvalidStateError, AgentRunNotFoundError, AgentRunService

router = APIRouter()


@router.get("/{run_id}", response_model=AgentRunResponse)
def get_agent_run(
    run_id: str,
    user_id: str = Depends(get_current_user_id),
    service: AgentRunService = Depends(get_agent_run_service),
) -> AgentRunResponse:
    try:
        run = service.get_run(user_id=user_id, run_id=run_id)
    except AgentRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found") from exc
    return agent_run_to_response(run)


@router.get("/{run_id}/events", response_model=list[AgentRunEventResponse])
def list_agent_run_events(
    run_id: str,
    user_id: str = Depends(get_current_user_id),
    service: AgentRunService = Depends(get_agent_run_service),
) -> list[AgentRunEventResponse]:
    try:
        run = service.get_run(user_id=user_id, run_id=run_id)
    except AgentRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found") from exc
    return [agent_run_event_to_response(event) for event in run.events]


@router.get("/{run_id}/tool-calls", response_model=list[ToolCallResponse])
def list_agent_run_tool_calls(
    run_id: str,
    user_id: str = Depends(get_current_user_id),
    service: AgentRunService = Depends(get_agent_run_service),
    tool_call_repository=Depends(get_tool_call_repository),
) -> list[ToolCallResponse]:
    try:
        service.get_run(user_id=user_id, run_id=run_id)
    except AgentRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found") from exc
    return [tool_call_to_response(call) for call in tool_call_repository.list_by_run(run_id)]


@router.post("/{run_id}/cancel", response_model=AgentRunResponse)
def cancel_agent_run(
    run_id: str,
    user_id: str = Depends(get_current_user_id),
    service: AgentRunService = Depends(get_agent_run_service),
) -> AgentRunResponse:
    try:
        return agent_run_to_response(service.cancel_run(user_id=user_id, run_id=run_id))
    except AgentRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found") from exc
    except AgentRunInvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
