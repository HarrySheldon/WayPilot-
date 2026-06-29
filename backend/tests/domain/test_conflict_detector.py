from __future__ import annotations

import unittest

from backend.app.domain.conflicts import DeterministicConflictDetector
from backend.app.domain.trips import ConflictSeverity, Trip, TripPreference


class DeterministicConflictDetectorTests(unittest.TestCase):
    def test_detects_time_overlap_as_blocking_conflict(self) -> None:
        detector = DeterministicConflictDetector()
        trip = Trip(id="trip-1", budget_total=1000)
        itinerary = {
            "days": [
                {
                    "date": "2026-07-01",
                    "items": [
                        {"temp_id": "a", "title": "Museum", "start_time": "09:00", "end_time": "11:00"},
                        {"temp_id": "b", "title": "Temple", "start_time": "10:30", "end_time": "12:00"},
                    ],
                }
            ]
        }

        conflicts = detector.detect(
            itinerary_snapshot=itinerary,
            budget_snapshot={},
            preference_snapshot={},
            trip=trip,
        )

        self.assertEqual(conflicts[0].conflict_type, "time_overlap")
        self.assertEqual(conflicts[0].severity, ConflictSeverity.BLOCKING)

    def test_detects_budget_overrun_against_trip_budget(self) -> None:
        detector = DeterministicConflictDetector()
        trip = Trip(id="trip-1", budget_total=1000)

        conflicts = detector.detect(
            itinerary_snapshot={"days": []},
            budget_snapshot={"total": 1200},
            preference_snapshot={},
            trip=trip,
        )

        self.assertEqual([conflict.conflict_type for conflict in conflicts], ["budget_exceeded"])
        self.assertEqual(conflicts[0].severity, ConflictSeverity.WARNING)

    def test_detects_closed_places_and_insufficient_transfer(self) -> None:
        detector = DeterministicConflictDetector()
        trip = Trip(id="trip-1")
        itinerary = {
            "days": [
                {
                    "date": "2026-07-01",
                    "items": [
                        {
                            "temp_id": "a",
                            "title": "Closed museum",
                            "opening_status": "closed",
                            "transport_to_next": {"estimated_minutes": 10, "required_minutes": 25},
                        },
                        {"temp_id": "b", "title": "Lunch"},
                    ],
                }
            ]
        }

        conflicts = detector.detect(
            itinerary_snapshot=itinerary,
            budget_snapshot={},
            preference_snapshot={},
            trip=trip,
        )

        self.assertEqual(
            {conflict.conflict_type: conflict.severity for conflict in conflicts},
            {
                "closed_place": ConflictSeverity.BLOCKING,
                "insufficient_transfer": ConflictSeverity.WARNING,
            },
        )

    def test_detects_weather_risk_and_pace_overload(self) -> None:
        detector = DeterministicConflictDetector()
        trip = Trip(id="trip-1", preference=TripPreference(destination="Tokyo", pace="relaxed"))
        itinerary = {
            "days": [
                {
                    "date": "2026-07-01",
                    "items": [
                        {"temp_id": "a", "title": "Park", "start_time": "08:00", "end_time": "09:00", "weather_risk": True},
                        {"temp_id": "b", "title": "Museum", "start_time": "09:30", "end_time": "10:30"},
                        {"temp_id": "c", "title": "Cafe", "start_time": "11:00", "end_time": "12:00"},
                        {"temp_id": "d", "title": "Market", "start_time": "13:00", "end_time": "14:00"},
                        {"temp_id": "e", "title": "Gallery", "start_time": "15:00", "end_time": "16:00"},
                    ],
                }
            ]
        }

        conflicts = detector.detect(
            itinerary_snapshot=itinerary,
            budget_snapshot={},
            preference_snapshot={},
            trip=trip,
        )

        self.assertEqual(
            {conflict.conflict_type for conflict in conflicts},
            {"weather_risk", "pace_overload"},
        )

    def test_detects_missing_required_places_and_avoidance_violations(self) -> None:
        detector = DeterministicConflictDetector()
        trip = Trip(
            id="trip-1",
            preference=TripPreference(
                destination="Tokyo",
                must_visit_places=["Senso-ji"],
                avoidances=["nightclub"],
            ),
        )
        itinerary = {
            "days": [
                {
                    "date": "2026-07-01",
                    "items": [{"temp_id": "a", "title": "Late nightclub", "place_name": "Shibuya nightclub"}],
                }
            ]
        }

        conflicts = detector.detect(
            itinerary_snapshot=itinerary,
            budget_snapshot={},
            preference_snapshot={},
            trip=trip,
        )

        self.assertEqual(
            {conflict.conflict_type for conflict in conflicts},
            {"missing_required_place", "avoidance_violation"},
        )
        self.assertTrue(all(conflict.severity == ConflictSeverity.BLOCKING for conflict in conflicts))


if __name__ == "__main__":
    unittest.main()
