from __future__ import annotations

from ..domain.agents import AgentRun, AgentTrace, ToolCall
from ..domain.rag import RagChunk, RagDocument
from ..domain.trips import Trip, TripCandidate, UserPreference
from ..domain.users import User


class InMemoryUserRepository:
    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    def save(self, user: User) -> User:
        self._users[user.id] = user
        return user

    def get(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        return next((user for user in self._users.values() if user.email == email), None)


class InMemoryTripRepository:
    def __init__(self) -> None:
        self._trips: dict[str, Trip] = {}

    def save(self, trip: Trip) -> Trip:
        self._trips[trip.id] = trip
        return trip

    def list_by_user(self, user_id: str) -> list[Trip]:
        return [trip for trip in self._trips.values() if trip.user_id == user_id]

    def get(self, trip_id: str) -> Trip | None:
        return self._trips.get(trip_id)

    def find_by_version_id(self, version_id: str) -> Trip | None:
        for trip in self._trips.values():
            if any(version.id == version_id for version in trip.versions):
                return trip
        return None


class InMemoryTripCandidateRepository:
    def __init__(self) -> None:
        self._candidates: dict[str, TripCandidate] = {}

    def save(self, candidate: TripCandidate) -> TripCandidate:
        self._candidates[candidate.id] = candidate
        return candidate

    def get(self, candidate_id: str) -> TripCandidate | None:
        return self._candidates.get(candidate_id)

    def list_by_trip(self, trip_id: str) -> list[TripCandidate]:
        return [candidate for candidate in self._candidates.values() if candidate.trip_id == trip_id]


class InMemoryPreferenceRepository:
    def __init__(self) -> None:
        self._preferences: dict[str, UserPreference] = {}

    def save(self, preference: UserPreference) -> UserPreference:
        self._preferences[preference.user_id] = preference
        return preference

    def get_by_user(self, user_id: str) -> UserPreference | None:
        return self._preferences.get(user_id)


class InMemoryAgentRunRepository:
    def __init__(self) -> None:
        self._runs: dict[str, AgentRun] = {}

    def save(self, run: AgentRun) -> AgentRun:
        self._runs[run.id] = run
        return run

    def get(self, run_id: str) -> AgentRun | None:
        return self._runs.get(run_id)

    def list_by_trip(self, trip_id: str) -> list[AgentRun]:
        return [run for run in self._runs.values() if run.trip_id == trip_id]


class InMemoryToolCallRepository:
    def __init__(self) -> None:
        self._calls: dict[str, ToolCall] = {}

    def next_id(self, agent_run_id: str) -> str:
        return f"{agent_run_id}-tool-{len(self.list_by_run(agent_run_id)) + 1}"

    def save(self, call: ToolCall) -> ToolCall:
        self._calls[call.id] = call
        return call

    def list_by_run(self, agent_run_id: str) -> list[ToolCall]:
        return [call for call in self._calls.values() if call.agent_run_id == agent_run_id]


class InMemoryRagRepository:
    def __init__(self) -> None:
        self._documents: dict[str, RagDocument] = {}
        self._chunks: dict[str, RagChunk] = {}

    def save_document(self, document: RagDocument) -> RagDocument:
        self._documents[document.id] = document
        return document

    def save_chunk(self, chunk: RagChunk) -> RagChunk:
        if chunk.document_id not in self._documents:
            raise ValueError(f"document not found: {chunk.document_id}")
        self._chunks[chunk.id] = chunk
        return chunk

    def find_document_by_source(
        self,
        *,
        owner_user_id: str | None,
        source_type: str,
        source_id: str | None,
    ) -> RagDocument | None:
        return next(
            (
                document
                for document in self._documents.values()
                if document.owner_user_id == owner_user_id
                and document.source_type == source_type
                and document.source_id == source_id
            ),
            None,
        )

    def get_document(self, document_id: str) -> RagDocument | None:
        return self._documents.get(document_id)

    def list_chunks_by_document(self, document_id: str) -> list[RagChunk]:
        return sorted(
            [chunk for chunk in self._chunks.values() if chunk.document_id == document_id],
            key=lambda chunk: (chunk.chunk_index, chunk.id),
        )

    def list_chunks(self) -> list[RagChunk]:
        return list(self._chunks.values())

    def delete_chunks_by_document(self, document_id: str) -> None:
        for chunk_id in [chunk.id for chunk in self._chunks.values() if chunk.document_id == document_id]:
            del self._chunks[chunk_id]


class InMemoryAgentTraceRepository:
    def __init__(self) -> None:
        self._traces_by_run: dict[str, AgentTrace] = {}

    def save(self, trace: AgentTrace) -> AgentTrace:
        self._traces_by_run[trace.agent_run_id] = trace
        return trace

    def get_by_run(self, agent_run_id: str) -> AgentTrace | None:
        return self._traces_by_run.get(agent_run_id)
