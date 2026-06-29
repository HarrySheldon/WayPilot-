from __future__ import annotations

from copy import deepcopy
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass, field
from typing import Callable, Protocol
from uuid import uuid4

from ..domain.trips import Conflict, ConflictSeverity, Trip, TripCandidate, TripCandidatePublisher, TripVersion
from ..repositories.memory import InMemoryTripCandidateRepository, InMemoryTripRepository
from .trips import TripNotFoundError


class CandidateNotFoundError(LookupError):
    pass


class TripVersionNotFoundError(LookupError):
    pass


class ConflictDetector(Protocol):
    def detect(
        self,
        *,
        itinerary_snapshot: dict,
        budget_snapshot: dict,
        preference_snapshot: dict,
        trip: Trip,
    ) -> list[Conflict]:
        ...


class TransactionManager(Protocol):
    def begin(self) -> AbstractContextManager[None]:
        ...


@dataclass(frozen=True)
class TripCandidateCreateInput:
    source_type: str
    itinerary_snapshot: dict
    budget_snapshot: dict = field(default_factory=dict)
    preference_snapshot: dict = field(default_factory=dict)
    source_agent_run_id: str | None = None
    base_version_id: str | None = None


class TripCandidateService:
    def __init__(
        self,
        *,
        trip_repository: InMemoryTripRepository,
        candidate_repository: InMemoryTripCandidateRepository,
        conflict_detector: ConflictDetector,
        id_generator: Callable[[], str] | None = None,
        transaction_manager: TransactionManager | None = None,
    ) -> None:
        self._trip_repository = trip_repository
        self._candidate_repository = candidate_repository
        self._conflict_detector = conflict_detector
        self._id_generator = id_generator or (lambda: str(uuid4()))
        self._publisher = TripCandidatePublisher()
        self._transaction_manager = transaction_manager

    def create_candidate(self, *, user_id: str, trip_id: str, data: TripCandidateCreateInput) -> TripCandidate:
        trip = self._get_trip_for_user(user_id=user_id, trip_id=trip_id)
        candidate = TripCandidate(
            id=self._id_generator(),
            trip_id=trip.id,
            itinerary_snapshot=deepcopy(data.itinerary_snapshot),
            budget_snapshot=deepcopy(data.budget_snapshot),
            preference_snapshot=deepcopy(data.preference_snapshot),
            source_type=data.source_type,
            source_agent_run_id=data.source_agent_run_id,
            base_version_id=data.base_version_id or trip.active_version_id,
            created_by=user_id,
            status="draft",
        )
        return self._candidate_repository.save(candidate)

    def list_candidates(self, *, user_id: str, trip_id: str) -> list[TripCandidate]:
        self._get_trip_for_user(user_id=user_id, trip_id=trip_id)
        return self._candidate_repository.list_by_trip(trip_id)

    def get_candidate(self, *, user_id: str, candidate_id: str) -> TripCandidate:
        return self._get_candidate_for_user(user_id=user_id, candidate_id=candidate_id)

    def validate_candidate(self, *, user_id: str, candidate_id: str) -> TripCandidate:
        candidate = self._get_candidate_for_user(user_id=user_id, candidate_id=candidate_id)
        trip = self._get_trip_for_user(user_id=user_id, trip_id=candidate.trip_id)
        return self._validate_candidate_against_trip(candidate=candidate, trip=trip)

    def _validate_candidate_against_trip(self, *, candidate: TripCandidate, trip: Trip) -> TripCandidate:
        conflicts = self._conflict_detector.detect(
            itinerary_snapshot=candidate.itinerary_snapshot,
            budget_snapshot=candidate.budget_snapshot,
            preference_snapshot=candidate.preference_snapshot,
            trip=trip,
        )
        candidate.conflicts = conflicts
        candidate.validation_summary = _summarize_conflicts(conflicts)
        candidate.status = "blocked" if candidate.validation_summary["blocking"] else "ready"
        return self._candidate_repository.save(candidate)

    def publish_candidate(
        self,
        *,
        user_id: str,
        candidate_id: str,
        ignored_warning_conflict_ids: set[str] | None = None,
        publish_note: str | None = None,
    ) -> TripVersion:
        with self._begin_transaction():
            candidate = self._get_candidate_for_user(user_id=user_id, candidate_id=candidate_id)
            trip = self._get_trip_for_user(user_id=user_id, trip_id=candidate.trip_id, lock=True)
            candidate = self._validate_candidate_against_trip(candidate=candidate, trip=trip)
            version = self._publisher.publish(
                trip=trip,
                candidate=candidate,
                ignored_warning_conflict_ids=ignored_warning_conflict_ids,
                publish_note=publish_note,
            )
            self._trip_repository.save(trip)
            self._candidate_repository.save(candidate)
            return version

    def discard_candidate(self, *, user_id: str, candidate_id: str) -> TripCandidate:
        candidate = self._get_candidate_for_user(user_id=user_id, candidate_id=candidate_id)
        candidate.status = "discarded"
        return self._candidate_repository.save(candidate)

    def list_versions(self, *, user_id: str, trip_id: str) -> list[TripVersion]:
        trip = self._get_trip_for_user(user_id=user_id, trip_id=trip_id)
        return list(trip.versions)

    def get_version(self, *, user_id: str, version_id: str) -> TripVersion:
        trip = self._trip_repository.find_by_version_id(version_id)
        if trip is None or trip.user_id != user_id:
            raise TripVersionNotFoundError(f"version not found: {version_id}")
        return next(version for version in trip.versions if version.id == version_id)

    def rollback_version(self, *, user_id: str, version_id: str, publish_note: str | None = None) -> TripVersion:
        with self._begin_transaction():
            trip = self._trip_repository.find_by_version_id(version_id)
            if trip is None or trip.user_id != user_id:
                raise TripVersionNotFoundError(f"version not found: {version_id}")
            source_version = next(version for version in trip.versions if version.id == version_id)
            next_version_no = len(trip.versions) + 1
            rollback_version = TripVersion(
                id=f"{trip.id}-v{next_version_no}",
                trip_id=trip.id,
                version_no=next_version_no,
                source_candidate_id=f"rollback:{source_version.id}",
                source_type="rollback",
                rolled_back_from_version_id=source_version.id,
                itinerary_snapshot=deepcopy(source_version.itinerary_snapshot),
                budget_snapshot=deepcopy(source_version.budget_snapshot),
                preference_snapshot=deepcopy(source_version.preference_snapshot),
                conflict_snapshot=list(source_version.conflict_snapshot),
                ignored_warning_conflict_ids=list(source_version.ignored_warning_conflict_ids),
                publish_note=publish_note,
            )
            trip.versions.append(rollback_version)
            trip.days = self._publisher.build_projection(rollback_version.itinerary_snapshot)
            trip.active_version_id = rollback_version.id
            trip.status = "active"
            self._trip_repository.save(trip)
            return rollback_version

    def _get_candidate_for_user(self, *, user_id: str, candidate_id: str) -> TripCandidate:
        candidate = self._candidate_repository.get(candidate_id)
        if candidate is None:
            raise CandidateNotFoundError(f"candidate not found: {candidate_id}")
        try:
            self._get_trip_for_user(user_id=user_id, trip_id=candidate.trip_id)
        except TripNotFoundError as exc:
            raise CandidateNotFoundError(f"candidate not found: {candidate_id}") from exc
        return candidate

    def _get_trip_for_user(self, *, user_id: str, trip_id: str, lock: bool = False) -> Trip:
        if lock and hasattr(self._trip_repository, "get_for_update"):
            trip = self._trip_repository.get_for_update(trip_id)
        else:
            trip = self._trip_repository.get(trip_id)
        if trip is None or trip.user_id != user_id:
            raise TripNotFoundError(f"trip not found: {trip_id}")
        return trip

    def _begin_transaction(self) -> AbstractContextManager[None]:
        if self._transaction_manager is None:
            return nullcontext()
        return self._transaction_manager.begin()


def _summarize_conflicts(conflicts: list[Conflict]) -> dict[str, int]:
    return {
        "blocking": sum(1 for conflict in conflicts if conflict.severity == ConflictSeverity.BLOCKING),
        "warning": sum(1 for conflict in conflicts if conflict.severity == ConflictSeverity.WARNING),
        "info": sum(1 for conflict in conflicts if conflict.severity == ConflictSeverity.INFO),
    }
