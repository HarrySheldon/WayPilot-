from __future__ import annotations

from sqlalchemy.orm import Session

from ..agent.provider_openai_compatible import OpenAICompatibleProviderAdapter
from ..agent.seed_provider import SeedItineraryProvider
from ..core.config import settings
from ..db.session import SessionLocal
from ..domain.conflicts import DeterministicConflictDetector
from ..repositories.sqlalchemy import (
    SQLAlchemyAgentRunRepository,
    SQLAlchemyAgentTraceRepository,
    SQLAlchemyRagRepository,
    SQLAlchemyToolCallRepository,
    SQLAlchemyTransactionManager,
    SQLAlchemyTripCandidateRepository,
    SQLAlchemyTripRepository,
)
from ..services.agent_runs import AgentRunService, build_agent_executor
from ..services.trip_candidates import TripCandidateService
from ..services.trips import TripService
from .celery_app import celery_app


@celery_app.task(name="waypilot.run_agent")
def run_agent_task(agent_run_id: str) -> None:
    if settings.repository_backend != "sqlalchemy":
        raise RuntimeError("Celery agent execution requires the sqlalchemy repository backend")

    session = SessionLocal()
    try:
        service = _build_agent_run_service(session)
        service.run_pending_agent_run(agent_run_id)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@celery_app.task(name="waypilot.archive_agent_run")
def archive_agent_run_task(agent_run_id: str) -> None:
    return None


def _build_agent_run_service(session: Session) -> AgentRunService:
    trip_repository = SQLAlchemyTripRepository(session)
    candidate_service = TripCandidateService(
        trip_repository=trip_repository,
        candidate_repository=SQLAlchemyTripCandidateRepository(session),
        conflict_detector=DeterministicConflictDetector(),
        transaction_manager=SQLAlchemyTransactionManager(session),
    )
    run_repository = SQLAlchemyAgentRunRepository(session)
    tool_call_repository = SQLAlchemyToolCallRepository(session)
    executor = build_agent_executor(
        agent_run_repository=run_repository,
        candidate_service=candidate_service,
        tool_call_repository=tool_call_repository,
        rag_repository=SQLAlchemyRagRepository(session),
        trace_repository=SQLAlchemyAgentTraceRepository(session),
        provider=_build_agent_provider(),
    )
    return AgentRunService(
        trip_service=TripService(trip_repository=trip_repository),
        agent_run_repository=run_repository,
        agent_executor=executor,
    )


def _build_agent_provider():
    if settings.openai_compatible_base_url and settings.openai_compatible_model:
        return OpenAICompatibleProviderAdapter(
            base_url=settings.openai_compatible_base_url,
            api_key=settings.openai_compatible_api_key,
            model=settings.openai_compatible_model,
            timeout_seconds=settings.openai_compatible_timeout_seconds,
        )
    return SeedItineraryProvider()
