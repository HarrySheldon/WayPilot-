from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..domain.agents import AgentRun, AgentRunEvent, AgentRunStatus, AgentTrace, ToolCall
from ..domain.rag import RagChunk, RagDocument
from ..domain.trips import (
    Conflict,
    ConflictSeverity,
    ItineraryItemProjection,
    Trip,
    TripCandidate,
    TripDayProjection,
    TripPreference,
    TripVersion,
    UserPreference,
)
from ..models.orm import (
    AgentRunEventORM,
    AgentRunORM,
    AgentTraceORM,
    ItineraryItemORM,
    RagChunkORM,
    RagDocumentORM,
    ToolCallORM,
    TripCandidateORM,
    TripDayORM,
    TripORM,
    TripPreferenceORM,
    TripVersionORM,
    UserPreferenceORM,
)


class SQLAlchemyTransactionManager:
    def __init__(self, session: Session) -> None:
        self._session = session

    def begin(self) -> AbstractContextManager[None]:
        if self._session.in_transaction():
            return nullcontext()
        return self._session.begin()


class SQLAlchemyTripRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, trip: Trip) -> Trip:
        orm = self._session.get(TripORM, trip.id)
        if orm is None:
            orm = TripORM(id=trip.id, user_id=trip.user_id, title=trip.title, destination=trip.destination)
            self._session.add(orm)

        orm.user_id = trip.user_id
        orm.title = trip.title
        orm.destination = trip.destination
        orm.start_date = trip.start_date
        orm.end_date = trip.end_date
        orm.travelers_count = trip.travelers_count
        orm.budget_total = trip.budget_total
        orm.status = trip.status
        orm.active_version_id = trip.active_version_id

        if trip.preference is not None:
            self._save_preference(trip.id, trip.preference)
        self._save_new_versions(trip)
        self._replace_projection(trip)
        self._session.flush()
        return trip

    def list_by_user(self, user_id: str) -> list[Trip]:
        rows = self._session.scalars(select(TripORM).where(TripORM.user_id == user_id).order_by(TripORM.id)).all()
        return [self._to_domain(row) for row in rows]

    def get(self, trip_id: str) -> Trip | None:
        orm = self._session.get(TripORM, trip_id)
        return self._to_domain(orm) if orm is not None else None

    def get_for_update(self, trip_id: str) -> Trip | None:
        orm = self._session.scalars(
            select(TripORM)
            .where(TripORM.id == trip_id)
            .with_for_update()
        ).one_or_none()
        return self._to_domain(orm) if orm is not None else None

    def find_by_version_id(self, version_id: str) -> Trip | None:
        version = self._session.get(TripVersionORM, version_id)
        if version is None:
            return None
        return self.get(version.trip_id)

    def _save_preference(self, trip_id: str, preference: TripPreference) -> None:
        orm = self._session.get(TripPreferenceORM, trip_id)
        if orm is None:
            orm = TripPreferenceORM(trip_id=trip_id, destination=preference.destination)
            self._session.add(orm)
        orm.destination = preference.destination
        orm.pace = preference.pace
        orm.interests = list(preference.interests)
        orm.dietary_preferences = list(preference.dietary_preferences)
        orm.must_visit_places = list(preference.must_visit_places)
        orm.avoidances = list(preference.avoidances)
        orm.natural_language_note = preference.natural_language_note

    def _save_new_versions(self, trip: Trip) -> None:
        for version in trip.versions:
            if self._session.get(TripVersionORM, version.id) is not None:
                continue
            self._session.add(
                TripVersionORM(
                    id=version.id,
                    trip_id=version.trip_id,
                    version_no=version.version_no,
                    source_candidate_id=version.source_candidate_id,
                    source_type=version.source_type,
                    source_agent_run_id=version.source_agent_run_id,
                    rolled_back_from_version_id=version.rolled_back_from_version_id,
                    itinerary_snapshot=_copy_dict(version.itinerary_snapshot),
                    budget_snapshot=_copy_dict(version.budget_snapshot),
                    preference_snapshot=_copy_dict(version.preference_snapshot),
                    conflict_snapshot=[_conflict_to_dict(conflict) for conflict in version.conflict_snapshot],
                    ignored_warning_conflict_ids=list(version.ignored_warning_conflict_ids),
                    publish_note=version.publish_note,
                    created_by=trip.user_id,
                )
            )

    def _replace_projection(self, trip: Trip) -> None:
        existing_days = self._session.scalars(select(TripDayORM).where(TripDayORM.trip_id == trip.id)).all()
        for day in existing_days:
            self._session.delete(day)
        self._session.flush()

        for day_index, day in enumerate(trip.days, start=1):
            day_orm = TripDayORM(
                id=f"{trip.id}-day-{day_index}",
                trip_id=trip.id,
                date=day.date,
                day_index=day_index,
            )
            self._session.add(day_orm)
            for item_index, item in enumerate(day.items, start=1):
                self._session.add(
                    ItineraryItemORM(
                        id=f"{day_orm.id}-item-{item_index}",
                        trip_day_id=day_orm.id,
                        temp_id=item.temp_id,
                        title=item.title,
                        item_type="note",
                        place_id=None,
                        place_name=None,
                        start_time=item.start_time,
                        end_time=item.end_time,
                        estimated_cost=None,
                        transport_to_next={},
                        notes="",
                        preference_tags=[],
                    )
                )

    def _to_domain(self, orm: TripORM) -> Trip:
        preference_orm = self._session.get(TripPreferenceORM, orm.id)
        versions = self._session.scalars(
            select(TripVersionORM).where(TripVersionORM.trip_id == orm.id).order_by(TripVersionORM.version_no)
        ).all()
        days = self._session.scalars(
            select(TripDayORM).where(TripDayORM.trip_id == orm.id).order_by(TripDayORM.day_index)
        ).all()
        return Trip(
            id=orm.id,
            user_id=orm.user_id,
            title=orm.title,
            destination=orm.destination,
            start_date=orm.start_date,
            end_date=orm.end_date,
            travelers_count=orm.travelers_count,
            budget_total=orm.budget_total,
            preference=_preference_to_domain(preference_orm) if preference_orm is not None else None,
            status=orm.status,
            active_version_id=orm.active_version_id,
            versions=[_version_to_domain(version) for version in versions],
            days=[self._day_to_domain(day) for day in days],
        )

    def _day_to_domain(self, day: TripDayORM) -> TripDayProjection:
        items = self._session.scalars(
            select(ItineraryItemORM).where(ItineraryItemORM.trip_day_id == day.id).order_by(ItineraryItemORM.id)
        ).all()
        return TripDayProjection(
            date=day.date,
            items=[
                ItineraryItemProjection(
                    temp_id=item.temp_id,
                    title=item.title,
                    start_time=item.start_time,
                    end_time=item.end_time,
                )
                for item in items
            ],
        )


class SQLAlchemyTripCandidateRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, candidate: TripCandidate) -> TripCandidate:
        orm = self._session.get(TripCandidateORM, candidate.id)
        if orm is None:
            orm = TripCandidateORM(
                id=candidate.id,
                trip_id=candidate.trip_id,
                source_type=candidate.source_type,
                status=candidate.status,
                itinerary_snapshot={},
                created_by=candidate.created_by,
            )
            self._session.add(orm)

        orm.trip_id = candidate.trip_id
        orm.source_type = candidate.source_type
        orm.source_agent_run_id = candidate.source_agent_run_id
        orm.base_version_id = candidate.base_version_id
        orm.status = candidate.status
        orm.itinerary_snapshot = _copy_dict(candidate.itinerary_snapshot)
        orm.budget_snapshot = _copy_dict(candidate.budget_snapshot)
        orm.preference_snapshot = _copy_dict(candidate.preference_snapshot)
        orm.validation_summary = dict(candidate.validation_summary)
        orm.conflict_snapshot = [_conflict_to_dict(conflict) for conflict in candidate.conflicts]
        orm.created_by = candidate.created_by
        self._session.flush()
        return candidate

    def get(self, candidate_id: str) -> TripCandidate | None:
        orm = self._session.get(TripCandidateORM, candidate_id)
        return _candidate_to_domain(orm) if orm is not None else None

    def list_by_trip(self, trip_id: str) -> list[TripCandidate]:
        rows = self._session.scalars(
            select(TripCandidateORM).where(TripCandidateORM.trip_id == trip_id).order_by(TripCandidateORM.id)
        ).all()
        return [_candidate_to_domain(row) for row in rows]


class SQLAlchemyPreferenceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, preference: UserPreference) -> UserPreference:
        orm = self._session.get(UserPreferenceORM, preference.user_id)
        if orm is None:
            orm = UserPreferenceORM(user_id=preference.user_id)
            self._session.add(orm)

        orm.default_pace = preference.default_pace
        orm.interests = list(preference.interests)
        orm.dietary_preferences = list(preference.dietary_preferences)
        orm.avoidances = list(preference.avoidances)
        self._session.flush()
        return preference

    def get_by_user(self, user_id: str) -> UserPreference | None:
        orm = self._session.get(UserPreferenceORM, user_id)
        if orm is None:
            return None
        return UserPreference(
            user_id=orm.user_id,
            default_pace=orm.default_pace,
            interests=list(orm.interests or []),
            dietary_preferences=list(orm.dietary_preferences or []),
            avoidances=list(orm.avoidances or []),
        )


class SQLAlchemyAgentRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, run: AgentRun) -> AgentRun:
        orm = self._session.get(AgentRunORM, run.id)
        if orm is None:
            orm = AgentRunORM(id=run.id, user_id=run.user_id, trip_id=run.trip_id, user_message=run.user_message)
            self._session.add(orm)

        orm.user_id = run.user_id
        orm.trip_id = run.trip_id
        orm.user_message = run.user_message
        orm.status = str(run.status)
        orm.candidate_id = run.candidate_id
        orm.error_message = run.error_message
        self._session.flush()
        self._replace_events(run)
        self._session.flush()
        return run

    def get(self, run_id: str) -> AgentRun | None:
        orm = self._session.get(AgentRunORM, run_id)
        return self._to_domain(orm) if orm is not None else None

    def list_by_trip(self, trip_id: str) -> list[AgentRun]:
        rows = self._session.scalars(
            select(AgentRunORM).where(AgentRunORM.trip_id == trip_id).order_by(AgentRunORM.created_at, AgentRunORM.id)
        ).all()
        return [self._to_domain(row) for row in rows]

    def _replace_events(self, run: AgentRun) -> None:
        self._session.execute(delete(AgentRunEventORM).where(AgentRunEventORM.agent_run_id == run.id))
        for event in run.events:
            self._session.add(
                AgentRunEventORM(
                    id=event.id,
                    agent_run_id=event.agent_run_id,
                    type=event.type,
                    title=event.title,
                    detail=event.detail,
                    payload=_copy_dict(event.payload),
                )
            )

    def _to_domain(self, orm: AgentRunORM) -> AgentRun:
        events = self._session.scalars(
            select(AgentRunEventORM).where(AgentRunEventORM.agent_run_id == orm.id).order_by(AgentRunEventORM.id)
        ).all()
        return AgentRun(
            id=orm.id,
            user_id=orm.user_id,
            trip_id=orm.trip_id,
            user_message=orm.user_message,
            status=AgentRunStatus(orm.status),
            candidate_id=orm.candidate_id,
            error_message=orm.error_message,
            events=[_agent_run_event_to_domain(event) for event in sorted(events, key=_agent_event_sort_key)],
        )


class SQLAlchemyToolCallRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def next_id(self, agent_run_id: str) -> str:
        count = self._session.scalar(
            select(func.count()).select_from(ToolCallORM).where(ToolCallORM.agent_run_id == agent_run_id)
        )
        return f"{agent_run_id}-tool-{int(count or 0) + 1}"

    def save(self, call: ToolCall) -> ToolCall:
        orm = self._session.get(ToolCallORM, call.id)
        if orm is None:
            orm = ToolCallORM(id=call.id, agent_run_id=call.agent_run_id, tool_name=call.tool_name)
            self._session.add(orm)

        orm.agent_run_id = call.agent_run_id
        orm.tool_name = call.tool_name
        orm.arguments = _copy_dict(call.arguments)
        orm.status = call.status
        orm.result = _copy_dict(call.result)
        orm.error = call.error
        self._session.flush()
        return call

    def list_by_run(self, agent_run_id: str) -> list[ToolCall]:
        rows = self._session.scalars(
            select(ToolCallORM).where(ToolCallORM.agent_run_id == agent_run_id).order_by(ToolCallORM.id)
        ).all()
        return [_tool_call_to_domain(row) for row in sorted(rows, key=_tool_call_sort_key)]


class SQLAlchemyRagRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_document(self, document: RagDocument) -> RagDocument:
        orm = self._session.get(RagDocumentORM, document.id)
        if orm is None:
            orm = RagDocumentORM(id=document.id, source_type=document.source_type, title=document.title, content=document.content)
            self._session.add(orm)

        orm.owner_user_id = document.owner_user_id
        orm.source_type = document.source_type
        orm.source_id = document.source_id
        orm.title = document.title
        orm.city = document.city
        orm.locale = document.locale
        orm.content = document.content
        orm.metadata_json = _copy_dict(document.metadata)
        self._session.flush()
        return document

    def save_chunk(self, chunk: RagChunk) -> RagChunk:
        if self._session.get(RagDocumentORM, chunk.document_id) is None:
            raise ValueError(f"document not found: {chunk.document_id}")

        orm = self._session.get(RagChunkORM, chunk.id)
        if orm is None:
            orm = RagChunkORM(id=chunk.id, document_id=chunk.document_id, chunk_index=chunk.chunk_index)
            self._session.add(orm)

        orm.document_id = chunk.document_id
        orm.chunk_index = chunk.chunk_index
        orm.content = chunk.content
        orm.embedding = _zero_embedding()
        orm.metadata_json = _copy_dict(chunk.metadata)
        self._session.flush()
        return chunk

    def get_document(self, document_id: str) -> RagDocument | None:
        orm = self._session.get(RagDocumentORM, document_id)
        return _rag_document_to_domain(orm) if orm is not None else None

    def list_chunks(self) -> list[RagChunk]:
        rows = self._session.scalars(
            select(RagChunkORM).order_by(RagChunkORM.document_id, RagChunkORM.chunk_index, RagChunkORM.id)
        ).all()
        return [_rag_chunk_to_domain(row) for row in rows]


class SQLAlchemyAgentTraceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, trace: AgentTrace) -> AgentTrace:
        orm = self._session.get(AgentTraceORM, trace.id)
        if orm is None:
            orm = self._session.scalars(
                select(AgentTraceORM).where(AgentTraceORM.agent_run_id == trace.agent_run_id)
            ).one_or_none()
        if orm is None:
            orm = AgentTraceORM(
                id=trace.id,
                agent_run_id=trace.agent_run_id,
                user_id=trace.user_id,
                trip_id=trace.trip_id,
                user_intent=trace.user_intent,
                status=trace.status,
            )
            self._session.add(orm)

        orm.agent_run_id = trace.agent_run_id
        orm.user_id = trace.user_id
        orm.trip_id = trace.trip_id
        orm.user_intent = trace.user_intent
        orm.status = trace.status
        orm.candidate_id = trace.candidate_id
        orm.rag_chunk_ids = list(trace.rag_chunk_ids)
        orm.tool_call_ids = list(trace.tool_call_ids)
        orm.error_message = trace.error_message
        self._session.flush()
        return trace

    def get_by_run(self, agent_run_id: str) -> AgentTrace | None:
        orm = self._session.scalars(select(AgentTraceORM).where(AgentTraceORM.agent_run_id == agent_run_id)).one_or_none()
        return _agent_trace_to_domain(orm) if orm is not None else None


def _preference_to_domain(orm: TripPreferenceORM) -> TripPreference:
    return TripPreference(
        destination=orm.destination,
        pace=orm.pace,
        interests=list(orm.interests or []),
        dietary_preferences=list(orm.dietary_preferences or []),
        must_visit_places=list(orm.must_visit_places or []),
        avoidances=list(orm.avoidances or []),
        natural_language_note=orm.natural_language_note,
    )


def _version_to_domain(orm: TripVersionORM) -> TripVersion:
    return TripVersion(
        id=orm.id,
        trip_id=orm.trip_id,
        version_no=orm.version_no,
        source_candidate_id=orm.source_candidate_id,
        itinerary_snapshot=_copy_dict(orm.itinerary_snapshot),
        budget_snapshot=_copy_dict(orm.budget_snapshot),
        preference_snapshot=_copy_dict(orm.preference_snapshot),
        conflict_snapshot=[_conflict_from_dict(conflict) for conflict in orm.conflict_snapshot or []],
        ignored_warning_conflict_ids=list(orm.ignored_warning_conflict_ids or []),
        source_type=orm.source_type,
        source_agent_run_id=orm.source_agent_run_id,
        rolled_back_from_version_id=orm.rolled_back_from_version_id,
        publish_note=orm.publish_note,
    )


def _candidate_to_domain(orm: TripCandidateORM) -> TripCandidate:
    return TripCandidate(
        id=orm.id,
        trip_id=orm.trip_id,
        itinerary_snapshot=_copy_dict(orm.itinerary_snapshot),
        budget_snapshot=_copy_dict(orm.budget_snapshot),
        preference_snapshot=_copy_dict(orm.preference_snapshot),
        conflicts=[_conflict_from_dict(conflict) for conflict in orm.conflict_snapshot or []],
        source_type=orm.source_type,
        source_agent_run_id=orm.source_agent_run_id,
        base_version_id=orm.base_version_id,
        created_by=orm.created_by,
        validation_summary=dict(orm.validation_summary or {}),
        status=orm.status,
    )


def _agent_run_event_to_domain(orm: AgentRunEventORM) -> AgentRunEvent:
    return AgentRunEvent(
        id=orm.id,
        agent_run_id=orm.agent_run_id,
        type=orm.type,
        title=orm.title,
        detail=orm.detail,
        payload=_copy_dict(orm.payload),
    )


def _tool_call_to_domain(orm: ToolCallORM) -> ToolCall:
    return ToolCall(
        id=orm.id,
        agent_run_id=orm.agent_run_id,
        tool_name=orm.tool_name,
        arguments=_copy_dict(orm.arguments),
        status=orm.status,
        result=_copy_dict(orm.result),
        error=orm.error,
    )


def _rag_document_to_domain(orm: RagDocumentORM) -> RagDocument:
    return RagDocument(
        id=orm.id,
        owner_user_id=orm.owner_user_id,
        source_type=orm.source_type,
        source_id=orm.source_id,
        title=orm.title,
        city=orm.city,
        locale=orm.locale,
        content=orm.content,
        metadata=_copy_dict(orm.metadata_json),
    )


def _rag_chunk_to_domain(orm: RagChunkORM) -> RagChunk:
    return RagChunk(
        id=orm.id,
        document_id=orm.document_id,
        chunk_index=orm.chunk_index,
        content=orm.content,
        metadata=_copy_dict(orm.metadata_json),
    )


def _agent_trace_to_domain(orm: AgentTraceORM) -> AgentTrace:
    return AgentTrace(
        id=orm.id,
        agent_run_id=orm.agent_run_id,
        user_id=orm.user_id,
        trip_id=orm.trip_id,
        user_intent=orm.user_intent,
        status=orm.status,
        candidate_id=orm.candidate_id,
        rag_chunk_ids=list(orm.rag_chunk_ids or []),
        tool_call_ids=list(orm.tool_call_ids or []),
        error_message=orm.error_message,
    )


def _conflict_to_dict(conflict: Conflict) -> dict[str, Any]:
    return {
        "id": conflict.id,
        "severity": str(conflict.severity),
        "conflict_type": conflict.conflict_type,
        "message": conflict.message,
    }


def _conflict_from_dict(data: dict[str, Any]) -> Conflict:
    return Conflict(
        id=str(data["id"]),
        severity=ConflictSeverity(str(data["severity"])),
        conflict_type=str(data["conflict_type"]),
        message=str(data["message"]),
    )


def _copy_dict(value: dict[str, Any] | None) -> dict[str, Any]:
    return dict(value or {})


def _zero_embedding() -> list[float]:
    return [0.0] * 1536


def _agent_event_sort_key(event: AgentRunEventORM) -> tuple[str, int, str]:
    marker = "-event-"
    if marker in event.id:
        prefix, _, suffix = event.id.rpartition(marker)
        if suffix.isdigit():
            return (prefix, int(suffix), event.id)
    return (event.agent_run_id, 0, event.id)


def _tool_call_sort_key(call: ToolCallORM) -> tuple[str, int, str]:
    marker = "-tool-"
    if marker in call.id:
        prefix, _, suffix = call.id.rpartition(marker)
        if suffix.isdigit():
            return (prefix, int(suffix), call.id)
    return (call.agent_run_id, 0, call.id)
