from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.session import get_db_session
from ..domain.conflicts import DeterministicConflictDetector
from ..repositories.memory import (
    InMemoryAgentRunRepository,
    InMemoryAgentTraceRepository,
    InMemoryPreferenceRepository,
    InMemoryRagRepository,
    InMemoryToolCallRepository,
    InMemoryTripCandidateRepository,
    InMemoryTripRepository,
)
from ..repositories.sqlalchemy import (
    SQLAlchemyAgentRunRepository,
    SQLAlchemyAgentTraceRepository,
    SQLAlchemyPreferenceRepository,
    SQLAlchemyRagRepository,
    SQLAlchemyToolCallRepository,
    SQLAlchemyTransactionManager,
    SQLAlchemyTripCandidateRepository,
    SQLAlchemyTripRepository,
)
from ..services.trip_candidates import TripCandidateService
from ..services.trips import PreferenceService, TripService

trip_repository = InMemoryTripRepository()
preference_repository = InMemoryPreferenceRepository()
candidate_repository = InMemoryTripCandidateRepository()
agent_run_repository = InMemoryAgentRunRepository()
tool_call_repository = InMemoryToolCallRepository()
rag_repository = InMemoryRagRepository()
agent_trace_repository = InMemoryAgentTraceRepository()

trip_service = TripService(trip_repository=trip_repository)
preference_service = PreferenceService(preference_repository=preference_repository)
trip_candidate_service = TripCandidateService(
    trip_repository=trip_repository,
    candidate_repository=candidate_repository,
    conflict_detector=DeterministicConflictDetector(),
)


def get_current_user_id() -> str:
    return "demo-user"


def get_repository_backend() -> str:
    return settings.repository_backend


def get_trip_service(
    db_session: Session = Depends(get_db_session),
    repository_backend: str = Depends(get_repository_backend),
) -> TripService:
    if repository_backend == "sqlalchemy":
        return TripService(trip_repository=SQLAlchemyTripRepository(db_session))
    return trip_service


def get_preference_service(
    db_session: Session = Depends(get_db_session),
    repository_backend: str = Depends(get_repository_backend),
) -> PreferenceService:
    if repository_backend == "sqlalchemy":
        return PreferenceService(preference_repository=SQLAlchemyPreferenceRepository(db_session))
    return preference_service


def get_trip_candidate_service(
    db_session: Session = Depends(get_db_session),
    repository_backend: str = Depends(get_repository_backend),
) -> TripCandidateService:
    if repository_backend == "sqlalchemy":
        return TripCandidateService(
            trip_repository=SQLAlchemyTripRepository(db_session),
            candidate_repository=SQLAlchemyTripCandidateRepository(db_session),
            conflict_detector=DeterministicConflictDetector(),
            transaction_manager=SQLAlchemyTransactionManager(db_session),
        )
    return trip_candidate_service


def get_agent_run_repository(
    db_session: Session = Depends(get_db_session),
    repository_backend: str = Depends(get_repository_backend),
):
    if repository_backend == "sqlalchemy":
        return SQLAlchemyAgentRunRepository(db_session)
    return agent_run_repository


def get_tool_call_repository(
    db_session: Session = Depends(get_db_session),
    repository_backend: str = Depends(get_repository_backend),
):
    if repository_backend == "sqlalchemy":
        return SQLAlchemyToolCallRepository(db_session)
    return tool_call_repository


def get_rag_repository(
    db_session: Session = Depends(get_db_session),
    repository_backend: str = Depends(get_repository_backend),
):
    if repository_backend == "sqlalchemy":
        return SQLAlchemyRagRepository(db_session)
    return rag_repository


def get_agent_trace_repository(
    db_session: Session = Depends(get_db_session),
    repository_backend: str = Depends(get_repository_backend),
):
    if repository_backend == "sqlalchemy":
        return SQLAlchemyAgentTraceRepository(db_session)
    return agent_trace_repository
