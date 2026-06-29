from __future__ import annotations

from ..domain.conflicts import DeterministicConflictDetector
from ..repositories.memory import (
    InMemoryAgentRunRepository,
    InMemoryPreferenceRepository,
    InMemoryToolCallRepository,
    InMemoryTripCandidateRepository,
    InMemoryTripRepository,
)
from ..services.trip_candidates import TripCandidateService
from ..services.trips import PreferenceService, TripService

trip_repository = InMemoryTripRepository()
preference_repository = InMemoryPreferenceRepository()
candidate_repository = InMemoryTripCandidateRepository()
agent_run_repository = InMemoryAgentRunRepository()
tool_call_repository = InMemoryToolCallRepository()

trip_service = TripService(trip_repository=trip_repository)
preference_service = PreferenceService(preference_repository=preference_repository)
trip_candidate_service = TripCandidateService(
    trip_repository=trip_repository,
    candidate_repository=candidate_repository,
    conflict_detector=DeterministicConflictDetector(),
)


def get_current_user_id() -> str:
    return "demo-user"


def get_trip_service() -> TripService:
    return trip_service


def get_preference_service() -> PreferenceService:
    return preference_service


def get_trip_candidate_service() -> TripCandidateService:
    return trip_candidate_service


def get_agent_run_repository() -> InMemoryAgentRunRepository:
    return agent_run_repository


def get_tool_call_repository() -> InMemoryToolCallRepository:
    return tool_call_repository
