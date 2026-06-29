from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from copy import deepcopy


class ConflictSeverity(StrEnum):
    BLOCKING = "blocking"
    WARNING = "warning"
    INFO = "info"


class PublishBlockedError(RuntimeError):
    pass


@dataclass(frozen=True)
class Conflict:
    id: str
    severity: ConflictSeverity
    conflict_type: str
    message: str


@dataclass
class ItineraryItemProjection:
    temp_id: str
    title: str
    start_time: str | None = None
    end_time: str | None = None


@dataclass
class TripDayProjection:
    date: str
    items: list[ItineraryItemProjection] = field(default_factory=list)


@dataclass
class TripVersion:
    id: str
    trip_id: str
    version_no: int
    source_candidate_id: str
    itinerary_snapshot: dict[str, Any]
    budget_snapshot: dict[str, Any]
    preference_snapshot: dict[str, Any]
    conflict_snapshot: list[Conflict]
    ignored_warning_conflict_ids: list[str]
    source_type: str = "agent"
    source_agent_run_id: str | None = None
    rolled_back_from_version_id: str | None = None
    publish_note: str | None = None


@dataclass
class TripCandidate:
    id: str
    trip_id: str
    itinerary_snapshot: dict[str, Any]
    budget_snapshot: dict[str, Any] = field(default_factory=dict)
    preference_snapshot: dict[str, Any] = field(default_factory=dict)
    conflicts: list[Conflict] = field(default_factory=list)
    source_type: str = "user_edit"
    source_agent_run_id: str | None = None
    base_version_id: str | None = None
    created_by: str = ""
    validation_summary: dict[str, int] = field(default_factory=dict)
    status: str = "ready"


@dataclass
class Trip:
    id: str
    user_id: str = ""
    title: str = ""
    destination: str = ""
    start_date: str | None = None
    end_date: str | None = None
    travelers_count: int = 1
    budget_total: int | None = None
    preference: TripPreference | None = None
    status: str = "draft"
    active_version_id: str | None = None
    versions: list[TripVersion] = field(default_factory=list)
    days: list[TripDayProjection] = field(default_factory=list)


@dataclass
class TripPreference:
    destination: str
    pace: str = "standard"
    interests: list[str] = field(default_factory=list)
    dietary_preferences: list[str] = field(default_factory=list)
    must_visit_places: list[str] = field(default_factory=list)
    avoidances: list[str] = field(default_factory=list)
    natural_language_note: str = ""


@dataclass
class UserPreference:
    user_id: str
    default_pace: str = "standard"
    interests: list[str] = field(default_factory=list)
    dietary_preferences: list[str] = field(default_factory=list)
    avoidances: list[str] = field(default_factory=list)


class TripCandidatePublisher:
    def publish(
        self,
        *,
        trip: Trip,
        candidate: TripCandidate,
        ignored_warning_conflict_ids: set[str] | None = None,
        publish_note: str | None = None,
    ) -> TripVersion:
        ignored_warning_conflict_ids = ignored_warning_conflict_ids or set()
        self._ensure_candidate_can_publish(trip, candidate, ignored_warning_conflict_ids)

        version_no = len(trip.versions) + 1
        version = TripVersion(
            id=f"{trip.id}-v{version_no}",
            trip_id=trip.id,
            version_no=version_no,
            source_candidate_id=candidate.id,
            itinerary_snapshot=deepcopy(candidate.itinerary_snapshot),
            budget_snapshot=deepcopy(candidate.budget_snapshot),
            preference_snapshot=deepcopy(candidate.preference_snapshot),
            conflict_snapshot=list(candidate.conflicts),
            ignored_warning_conflict_ids=sorted(ignored_warning_conflict_ids),
            source_type=candidate.source_type,
            source_agent_run_id=candidate.source_agent_run_id,
            publish_note=publish_note,
        )

        trip.versions.append(version)
        trip.days = self._build_projection(version.itinerary_snapshot)
        trip.active_version_id = version.id
        trip.status = "active"
        candidate.status = "published"
        return version

    def _ensure_candidate_can_publish(
        self,
        trip: Trip,
        candidate: TripCandidate,
        ignored_warning_conflict_ids: set[str],
    ) -> None:
        if candidate.trip_id != trip.id:
            raise PublishBlockedError("candidate does not belong to trip")

        if any(conflict.severity == ConflictSeverity.BLOCKING for conflict in candidate.conflicts):
            raise PublishBlockedError("candidate has blocking conflicts")

        if candidate.status != "ready":
            raise PublishBlockedError("candidate is not ready to publish")

        warning_ids = {
            conflict.id
            for conflict in candidate.conflicts
            if conflict.severity == ConflictSeverity.WARNING
        }
        unconfirmed_warning_ids = warning_ids - ignored_warning_conflict_ids
        if unconfirmed_warning_ids:
            raise PublishBlockedError("candidate has unconfirmed warnings")

    def _build_projection(self, itinerary_snapshot: dict[str, Any]) -> list[TripDayProjection]:
        return self.build_projection(itinerary_snapshot)

    def build_projection(self, itinerary_snapshot: dict[str, Any]) -> list[TripDayProjection]:
        days: list[TripDayProjection] = []
        for raw_day in itinerary_snapshot.get("days", []):
            items = [
                ItineraryItemProjection(
                    temp_id=str(raw_item["temp_id"]),
                    title=str(raw_item["title"]),
                    start_time=raw_item.get("start_time"),
                    end_time=raw_item.get("end_time"),
                )
                for raw_item in raw_day.get("items", [])
            ]
            days.append(TripDayProjection(date=str(raw_day["date"]), items=items))
        return days
