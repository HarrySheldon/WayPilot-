from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .trips import Conflict, ConflictSeverity, Trip


@dataclass(frozen=True)
class PaceLimit:
    scheduled_items_per_day: int


PACE_LIMITS = {
    "relaxed": PaceLimit(scheduled_items_per_day=4),
    "standard": PaceLimit(scheduled_items_per_day=6),
    "packed": PaceLimit(scheduled_items_per_day=8),
}


class DeterministicConflictDetector:
    def detect(
        self,
        *,
        itinerary_snapshot: dict[str, Any],
        budget_snapshot: dict[str, Any],
        preference_snapshot: dict[str, Any],
        trip: Trip,
    ) -> list[Conflict]:
        conflicts: list[Conflict] = []
        days = itinerary_snapshot.get("days", [])
        conflicts.extend(self._detect_time_overlaps(days))
        conflicts.extend(self._detect_item_level_conflicts(days))
        conflicts.extend(self._detect_budget_overrun(budget_snapshot=budget_snapshot, trip=trip))
        conflicts.extend(self._detect_pace_overload(days=days, preference_snapshot=preference_snapshot, trip=trip))
        conflicts.extend(self._detect_required_and_avoidance_conflicts(days=days, preference_snapshot=preference_snapshot, trip=trip))
        return conflicts

    def _detect_time_overlaps(self, days: list[dict[str, Any]]) -> list[Conflict]:
        conflicts: list[Conflict] = []
        for day in days:
            intervals: list[tuple[int, int, dict[str, Any]]] = []
            for item in day.get("items", []):
                start = _parse_minutes(item.get("start_time"))
                end = _parse_minutes(item.get("end_time"))
                if start is None or end is None or end <= start:
                    continue
                intervals.append((start, end, item))
            intervals.sort(key=lambda interval: interval[0])
            previous_end: int | None = None
            previous_item: dict[str, Any] | None = None
            for start, end, item in intervals:
                if previous_end is not None and previous_item is not None and start < previous_end:
                    conflicts.append(
                        Conflict(
                            id=f"time_overlap:{day.get('date')}:{_item_id(item)}",
                            severity=ConflictSeverity.BLOCKING,
                            conflict_type="time_overlap",
                            message=f"{item.get('title', 'Itinerary item')} overlaps with {previous_item.get('title', 'previous item')}.",
                        )
                    )
                if previous_end is None or end > previous_end:
                    previous_end = end
                    previous_item = item
        return conflicts

    def _detect_item_level_conflicts(self, days: list[dict[str, Any]]) -> list[Conflict]:
        conflicts: list[Conflict] = []
        for day in days:
            for item in day.get("items", []):
                item_id = _item_id(item)
                if item.get("opening_status") == "closed" or item.get("is_open") is False:
                    conflicts.append(
                        Conflict(
                            id=f"closed_place:{day.get('date')}:{item_id}",
                            severity=ConflictSeverity.BLOCKING,
                            conflict_type="closed_place",
                            message=f"{item.get('title', 'Place')} is closed at the scheduled time.",
                        )
                    )

                transfer = item.get("transport_to_next")
                if isinstance(transfer, dict):
                    estimated = _as_int(transfer.get("estimated_minutes"))
                    required = _as_int(transfer.get("required_minutes"))
                    if estimated is not None and required is not None and estimated < required:
                        conflicts.append(
                            Conflict(
                                id=f"insufficient_transfer:{day.get('date')}:{item_id}",
                                severity=ConflictSeverity.WARNING,
                                conflict_type="insufficient_transfer",
                                message="Estimated transfer time is shorter than the required transfer buffer.",
                            )
                        )

                weather = item.get("weather")
                weather_severity = weather.get("severity") if isinstance(weather, dict) else None
                if item.get("weather_risk") is True or weather_severity in {"risk", "warning", "severe"}:
                    conflicts.append(
                        Conflict(
                            id=f"weather_risk:{day.get('date')}:{item_id}",
                            severity=ConflictSeverity.WARNING,
                            conflict_type="weather_risk",
                            message=f"{item.get('title', 'Itinerary item')} may be affected by weather.",
                        )
                    )
        return conflicts

    def _detect_budget_overrun(self, *, budget_snapshot: dict[str, Any], trip: Trip) -> list[Conflict]:
        if trip.budget_total is None:
            return []
        total = _first_int(
            budget_snapshot.get("total"),
            budget_snapshot.get("total_estimated"),
            budget_snapshot.get("estimated_total"),
        )
        if total is None or total <= trip.budget_total:
            return []
        return [
            Conflict(
                id=f"budget_exceeded:{trip.id}",
                severity=ConflictSeverity.WARNING,
                conflict_type="budget_exceeded",
                message="Estimated budget exceeds the trip budget.",
            )
        ]

    def _detect_pace_overload(
        self,
        *,
        days: list[dict[str, Any]],
        preference_snapshot: dict[str, Any],
        trip: Trip,
    ) -> list[Conflict]:
        pace = str(preference_snapshot.get("pace") or (trip.preference.pace if trip.preference else "standard"))
        limit = PACE_LIMITS.get(pace, PACE_LIMITS["standard"]).scheduled_items_per_day
        conflicts: list[Conflict] = []
        for day in days:
            scheduled_count = sum(1 for item in day.get("items", []) if item.get("start_time") and item.get("end_time"))
            if scheduled_count > limit:
                conflicts.append(
                    Conflict(
                        id=f"pace_overload:{day.get('date')}",
                        severity=ConflictSeverity.WARNING,
                        conflict_type="pace_overload",
                        message=f"{day.get('date', 'This day')} has {scheduled_count} scheduled items, above the {pace} pace limit.",
                    )
                )
        return conflicts

    def _detect_required_and_avoidance_conflicts(
        self,
        *,
        days: list[dict[str, Any]],
        preference_snapshot: dict[str, Any],
        trip: Trip,
    ) -> list[Conflict]:
        must_visit_places = _preference_terms("must_visit_places", preference_snapshot, trip)
        avoidances = _preference_terms("avoidances", preference_snapshot, trip)
        itinerary_text = " ".join(_item_text(item) for day in days for item in day.get("items", [])).lower()

        conflicts: list[Conflict] = []
        for required in must_visit_places:
            if required.lower() not in itinerary_text:
                conflicts.append(
                    Conflict(
                        id=f"missing_required_place:{_slug(required)}",
                        severity=ConflictSeverity.BLOCKING,
                        conflict_type="missing_required_place",
                        message=f"Required place is missing: {required}.",
                    )
                )

        for avoidance in avoidances:
            if avoidance.lower() in itinerary_text:
                conflicts.append(
                    Conflict(
                        id=f"avoidance_violation:{_slug(avoidance)}",
                        severity=ConflictSeverity.BLOCKING,
                        conflict_type="avoidance_violation",
                        message=f"Itinerary includes an avoided item: {avoidance}.",
                    )
                )
        return conflicts


def _parse_minutes(value: Any) -> int | None:
    if not isinstance(value, str) or ":" not in value:
        return None
    hour, minute = value.split(":", 1)
    if not hour.isdigit() or not minute.isdigit():
        return None
    return int(hour) * 60 + int(minute)


def _as_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _first_int(*values: Any) -> int | None:
    for value in values:
        result = _as_int(value)
        if result is not None:
            return result
    return None


def _item_id(item: dict[str, Any]) -> str:
    return str(item.get("temp_id") or item.get("id") or item.get("title") or "item")


def _item_text(item: dict[str, Any]) -> str:
    return " ".join(
        str(value)
        for value in [item.get("title"), item.get("place_name"), item.get("notes")]
        if value
    )


def _preference_terms(key: str, preference_snapshot: dict[str, Any], trip: Trip) -> list[str]:
    raw_terms = preference_snapshot.get(key)
    if raw_terms is None and trip.preference is not None:
        raw_terms = getattr(trip.preference, key)
    if not isinstance(raw_terms, list):
        return []
    return [str(term) for term in raw_terms if str(term).strip()]


def _slug(value: str) -> str:
    return "-".join(value.lower().split())
