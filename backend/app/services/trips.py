from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
from uuid import uuid4

from ..domain.trips import Trip, TripPreference, UserPreference
from ..repositories.memory import InMemoryPreferenceRepository, InMemoryTripRepository


class TripNotFoundError(LookupError):
    pass


class TripValidationError(ValueError):
    pass


@dataclass(frozen=True)
class TripCreateInput:
    title: str
    destination: str
    start_date: str | None = None
    end_date: str | None = None
    travelers_count: int = 1
    budget_total: int | None = None
    pace: str = "standard"
    interests: list[str] = field(default_factory=list)
    dietary_preferences: list[str] = field(default_factory=list)
    must_visit_places: list[str] = field(default_factory=list)
    avoidances: list[str] = field(default_factory=list)
    natural_language_note: str = ""


@dataclass(frozen=True)
class UserPreferenceInput:
    default_pace: str = "standard"
    interests: list[str] = field(default_factory=list)
    dietary_preferences: list[str] = field(default_factory=list)
    avoidances: list[str] = field(default_factory=list)


class TripService:
    def __init__(
        self,
        *,
        trip_repository: InMemoryTripRepository,
        id_generator: Callable[[], str] | None = None,
    ) -> None:
        self._trip_repository = trip_repository
        self._id_generator = id_generator or (lambda: str(uuid4()))

    def create_trip(self, *, user_id: str, data: TripCreateInput) -> Trip:
        normalized_title, normalized_destination = self._validate_create_input(data)
        trip = Trip(
            id=self._id_generator(),
            user_id=user_id,
            title=normalized_title,
            destination=normalized_destination,
            start_date=data.start_date,
            end_date=data.end_date,
            travelers_count=data.travelers_count,
            budget_total=data.budget_total,
            status="draft",
            preference=TripPreference(
                destination=normalized_destination,
                pace=data.pace,
                interests=list(data.interests),
                dietary_preferences=list(data.dietary_preferences),
                must_visit_places=list(data.must_visit_places),
                avoidances=list(data.avoidances),
                natural_language_note=data.natural_language_note,
            ),
        )
        return self._trip_repository.save(trip)

    def list_trips(self, *, user_id: str) -> list[Trip]:
        return self._trip_repository.list_by_user(user_id)

    def get_trip(self, *, user_id: str, trip_id: str) -> Trip:
        trip = self._trip_repository.get(trip_id)
        if trip is None or trip.user_id != user_id:
            raise TripNotFoundError(f"trip not found: {trip_id}")
        return trip

    def _validate_create_input(self, data: TripCreateInput) -> tuple[str, str]:
        title = data.title.strip()
        destination = data.destination.strip()
        if not title:
            raise TripValidationError("title is required")
        if not destination:
            raise TripValidationError("destination is required")
        if data.travelers_count < 1:
            raise TripValidationError("travelers_count must be at least 1")
        if data.budget_total is not None and data.budget_total < 0:
            raise TripValidationError("budget_total cannot be negative")
        return title, destination


class PreferenceService:
    def __init__(self, *, preference_repository: InMemoryPreferenceRepository) -> None:
        self._preference_repository = preference_repository

    def upsert_user_preference(self, *, user_id: str, data: UserPreferenceInput) -> UserPreference:
        preference = UserPreference(
            user_id=user_id,
            default_pace=data.default_pace,
            interests=list(data.interests),
            dietary_preferences=list(data.dietary_preferences),
            avoidances=list(data.avoidances),
        )
        return self._preference_repository.save(preference)

    def get_user_preference(self, *, user_id: str) -> UserPreference | None:
        return self._preference_repository.get_by_user(user_id)
