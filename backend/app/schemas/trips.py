from pydantic import BaseModel, Field

from typing import Any

from ..domain.agents import AgentRun, AgentRunEvent, ToolCall
from ..domain.trips import Conflict, Trip, TripCandidate, TripVersion, UserPreference


class TripPreferenceResponse(BaseModel):
    destination: str
    pace: str
    interests: list[str]
    dietary_preferences: list[str]
    must_visit_places: list[str]
    avoidances: list[str]
    natural_language_note: str


class TripCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    start_date: str | None = None
    end_date: str | None = None
    travelers_count: int = Field(default=1, ge=1)
    budget_total: int | None = Field(default=None, ge=0)
    pace: str = "standard"
    interests: list[str] = Field(default_factory=list)
    dietary_preferences: list[str] = Field(default_factory=list)
    must_visit_places: list[str] = Field(default_factory=list)
    avoidances: list[str] = Field(default_factory=list)
    natural_language_note: str = ""


class AgentRunRequest(BaseModel):
    message: str = Field(min_length=1)


class AgentRunAcceptedResponse(BaseModel):
    agent_run_id: str


class TripResponse(BaseModel):
    id: str
    user_id: str
    title: str
    destination: str
    start_date: str | None
    end_date: str | None
    travelers_count: int
    budget_total: int | None
    status: str
    active_version_id: str | None
    preference: TripPreferenceResponse | None


class UserPreferenceRequest(BaseModel):
    default_pace: str = "standard"
    interests: list[str] = Field(default_factory=list)
    dietary_preferences: list[str] = Field(default_factory=list)
    avoidances: list[str] = Field(default_factory=list)


class UserPreferenceResponse(BaseModel):
    user_id: str
    default_pace: str
    interests: list[str]
    dietary_preferences: list[str]
    avoidances: list[str]


class ConflictResponse(BaseModel):
    id: str
    severity: str
    conflict_type: str
    message: str


class TripCandidateResponse(BaseModel):
    id: str
    trip_id: str
    source_type: str
    source_agent_run_id: str | None
    base_version_id: str | None
    status: str
    itinerary_snapshot: dict[str, Any]
    budget_snapshot: dict[str, Any]
    preference_snapshot: dict[str, Any]
    validation_summary: dict[str, int]
    conflicts: list[ConflictResponse]


class PublishCandidateRequest(BaseModel):
    ignored_warning_conflict_ids: list[str] = Field(default_factory=list)
    publish_note: str | None = None


class TripVersionResponse(BaseModel):
    id: str
    trip_id: str
    version_no: int
    source_candidate_id: str
    source_type: str
    source_agent_run_id: str | None
    rolled_back_from_version_id: str | None
    itinerary_snapshot: dict[str, Any]
    budget_snapshot: dict[str, Any]
    preference_snapshot: dict[str, Any]
    conflict_snapshot: list[ConflictResponse]
    ignored_warning_conflict_ids: list[str]
    publish_note: str | None


class RollbackVersionRequest(BaseModel):
    publish_note: str | None = None


class AgentRunEventResponse(BaseModel):
    id: str
    agent_run_id: str
    type: str
    title: str
    detail: str
    payload: dict[str, Any]


class AgentRunResponse(BaseModel):
    id: str
    user_id: str
    trip_id: str
    user_message: str
    status: str
    candidate_id: str | None
    error_message: str | None
    events: list[AgentRunEventResponse]


class ToolCallResponse(BaseModel):
    id: str
    agent_run_id: str
    tool_name: str
    arguments: dict[str, Any]
    status: str
    result: dict[str, Any]
    error: str | None


def trip_to_response(trip: Trip) -> TripResponse:
    preference = None
    if trip.preference is not None:
        preference = TripPreferenceResponse(
            destination=trip.preference.destination,
            pace=trip.preference.pace,
            interests=trip.preference.interests,
            dietary_preferences=trip.preference.dietary_preferences,
            must_visit_places=trip.preference.must_visit_places,
            avoidances=trip.preference.avoidances,
            natural_language_note=trip.preference.natural_language_note,
        )
    return TripResponse(
        id=trip.id,
        user_id=trip.user_id,
        title=trip.title,
        destination=trip.destination,
        start_date=trip.start_date,
        end_date=trip.end_date,
        travelers_count=trip.travelers_count,
        budget_total=trip.budget_total,
        status=trip.status,
        active_version_id=trip.active_version_id,
        preference=preference,
    )


def user_preference_to_response(preference: UserPreference) -> UserPreferenceResponse:
    return UserPreferenceResponse(
        user_id=preference.user_id,
        default_pace=preference.default_pace,
        interests=preference.interests,
        dietary_preferences=preference.dietary_preferences,
        avoidances=preference.avoidances,
    )


def conflict_to_response(conflict: Conflict) -> ConflictResponse:
    return ConflictResponse(
        id=conflict.id,
        severity=str(conflict.severity),
        conflict_type=conflict.conflict_type,
        message=conflict.message,
    )


def candidate_to_response(candidate: TripCandidate) -> TripCandidateResponse:
    return TripCandidateResponse(
        id=candidate.id,
        trip_id=candidate.trip_id,
        source_type=candidate.source_type,
        source_agent_run_id=candidate.source_agent_run_id,
        base_version_id=candidate.base_version_id,
        status=candidate.status,
        itinerary_snapshot=candidate.itinerary_snapshot,
        budget_snapshot=candidate.budget_snapshot,
        preference_snapshot=candidate.preference_snapshot,
        validation_summary=candidate.validation_summary,
        conflicts=[conflict_to_response(conflict) for conflict in candidate.conflicts],
    )


def version_to_response(version: TripVersion) -> TripVersionResponse:
    return TripVersionResponse(
        id=version.id,
        trip_id=version.trip_id,
        version_no=version.version_no,
        source_candidate_id=version.source_candidate_id,
        source_type=version.source_type,
        source_agent_run_id=version.source_agent_run_id,
        rolled_back_from_version_id=version.rolled_back_from_version_id,
        itinerary_snapshot=version.itinerary_snapshot,
        budget_snapshot=version.budget_snapshot,
        preference_snapshot=version.preference_snapshot,
        conflict_snapshot=[conflict_to_response(conflict) for conflict in version.conflict_snapshot],
        ignored_warning_conflict_ids=version.ignored_warning_conflict_ids,
        publish_note=version.publish_note,
    )


def agent_run_event_to_response(event: AgentRunEvent) -> AgentRunEventResponse:
    return AgentRunEventResponse(
        id=event.id,
        agent_run_id=event.agent_run_id,
        type=event.type,
        title=event.title,
        detail=event.detail,
        payload=event.payload,
    )


def agent_run_to_response(run: AgentRun) -> AgentRunResponse:
    return AgentRunResponse(
        id=run.id,
        user_id=run.user_id,
        trip_id=run.trip_id,
        user_message=run.user_message,
        status=str(run.status),
        candidate_id=run.candidate_id,
        error_message=run.error_message,
        events=[agent_run_event_to_response(event) for event in run.events],
    )


def tool_call_to_response(call: ToolCall) -> ToolCallResponse:
    return ToolCallResponse(
        id=call.id,
        agent_run_id=call.agent_run_id,
        tool_name=call.tool_name,
        arguments=call.arguments,
        status=call.status,
        result=call.result,
        error=call.error,
    )
