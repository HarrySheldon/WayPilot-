from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..agent.provider_openai_compatible import OpenAICompatibleProviderAdapter
from ..agent.seed_provider import SeedItineraryProvider
from ..core.config import settings
from ..core.security import InvalidTokenError, PasswordHasher, TokenService
from ..db.session import get_db_session
from ..domain.conflicts import DeterministicConflictDetector
from ..domain.users import User
from ..repositories.memory import (
    InMemoryAgentRunRepository,
    InMemoryAgentTraceRepository,
    InMemoryPreferenceRepository,
    InMemoryRagRepository,
    InMemoryToolCallRepository,
    InMemoryTripCandidateRepository,
    InMemoryTripRepository,
    InMemoryUserRepository,
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
from ..repositories.users import SQLAlchemyUserRepository
from ..rag.embeddings import DeterministicEmbeddingProvider
from ..rag.vector_retriever import VectorRagRetriever
from ..services.agent_runs import AgentRunService, build_agent_executor
from ..services.auth import AuthService
from ..services.trip_candidates import TripCandidateService
from ..services.trips import PreferenceService, TripService

bearer_scheme = HTTPBearer(auto_error=False)

user_repository = InMemoryUserRepository()
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


def get_repository_backend() -> str:
    return settings.repository_backend


def get_token_service() -> TokenService:
    return TokenService(secret_key=settings.jwt_secret_key)


def get_password_hasher() -> PasswordHasher:
    return PasswordHasher()


def get_user_repository(
    db_session: Session = Depends(get_db_session),
    repository_backend: str = Depends(get_repository_backend),
):
    if repository_backend == "sqlalchemy":
        return SQLAlchemyUserRepository(db_session)
    return user_repository


def get_auth_service(
    user_repo=Depends(get_user_repository),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    token_service: TokenService = Depends(get_token_service),
) -> AuthService:
    return AuthService(
        user_repository=user_repo,
        password_hasher=password_hasher,
        token_service=token_service,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    token_service: TokenService = Depends(get_token_service),
    user_repo=Depends(get_user_repository),
) -> User:
    if credentials is None:
        raise _unauthorized()
    try:
        payload = token_service.verify_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise _unauthorized() from exc

    user = user_repo.get(payload.subject)
    if user is None:
        raise _unauthorized()
    return user


def get_current_user_id(current_user: User = Depends(get_current_user)) -> str:
    return current_user.id


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


def get_agent_provider():
    if settings.openai_compatible_base_url and settings.openai_compatible_model:
        return OpenAICompatibleProviderAdapter(
            base_url=settings.openai_compatible_base_url,
            api_key=settings.openai_compatible_api_key,
            model=settings.openai_compatible_model,
            timeout_seconds=settings.openai_compatible_timeout_seconds,
        )
    return SeedItineraryProvider()


def get_embedding_provider():
    return DeterministicEmbeddingProvider()


def get_rag_retriever(
    rag_repo=Depends(get_rag_repository),
    embedding_provider=Depends(get_embedding_provider),
):
    return VectorRagRetriever(repository=rag_repo, embedding_provider=embedding_provider)


def get_agent_executor(
    candidate_service: TripCandidateService = Depends(get_trip_candidate_service),
    run_repo=Depends(get_agent_run_repository),
    tool_call_repo=Depends(get_tool_call_repository),
    rag_repo=Depends(get_rag_repository),
    trace_repo=Depends(get_agent_trace_repository),
    provider=Depends(get_agent_provider),
    rag_retriever=Depends(get_rag_retriever),
):
    return build_agent_executor(
        agent_run_repository=run_repo,
        candidate_service=candidate_service,
        tool_call_repository=tool_call_repo,
        rag_repository=rag_repo,
        trace_repository=trace_repo,
        provider=provider,
        rag_retriever=rag_retriever,
    )


def get_agent_run_service(
    trip_service: TripService = Depends(get_trip_service),
    run_repo=Depends(get_agent_run_repository),
    agent_executor=Depends(get_agent_executor),
) -> AgentRunService:
    return AgentRunService(
        trip_service=trip_service,
        agent_run_repository=run_repo,
        agent_executor=agent_executor,
    )


def get_agent_run_dispatcher():
    from ..worker.tasks import run_agent_task

    def dispatch(agent_run_id: str) -> None:
        run_agent_task.apply_async((agent_run_id,))

    return dispatch


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
