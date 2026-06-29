from __future__ import annotations

import unittest

from backend.app.domain.trips import Conflict, ConflictSeverity
from backend.app.repositories.memory import InMemoryTripCandidateRepository, InMemoryTripRepository
from backend.app.services.trip_candidates import (
    CandidateNotFoundError,
    TripCandidateCreateInput,
    TripCandidateService,
)
from backend.app.services.trips import TripCreateInput, TripService


class StubConflictDetector:
    def __init__(self, conflicts: list[Conflict] | None = None) -> None:
        self.conflicts = conflicts or []
        self.calls = 0

    def detect(self, *, itinerary_snapshot, budget_snapshot, preference_snapshot, trip):
        self.calls += 1
        return list(self.conflicts)


class TripCandidateServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.trips = InMemoryTripRepository()
        self.candidates = InMemoryTripCandidateRepository()
        self.trip_ids = iter(["trip-1"])
        self.candidate_ids = iter(["candidate-1", "candidate-2"])
        self.trip_service = TripService(trip_repository=self.trips, id_generator=lambda: next(self.trip_ids))
        self.trip = self.trip_service.create_trip(
            user_id="user-1",
            data=TripCreateInput(title="Tokyo", destination="Tokyo", budget_total=1000),
        )

    def test_create_candidate_is_scoped_to_trip_owner_and_does_not_publish(self) -> None:
        service = TripCandidateService(
            trip_repository=self.trips,
            candidate_repository=self.candidates,
            conflict_detector=StubConflictDetector(),
            id_generator=lambda: next(self.candidate_ids),
        )

        candidate = service.create_candidate(
            user_id="user-1",
            trip_id=self.trip.id,
            data=TripCandidateCreateInput(
                source_type="agent",
                source_agent_run_id="run-1",
                itinerary_snapshot={"days": []},
                budget_snapshot={"total": 0},
                preference_snapshot={"pace": "standard"},
            ),
        )

        self.assertEqual(candidate.id, "candidate-1")
        self.assertEqual(candidate.status, "draft")
        self.assertEqual(candidate.source_agent_run_id, "run-1")
        self.assertIsNone(self.trip.active_version_id)

    def test_validate_candidate_marks_blocked_when_detector_finds_blocking_conflict(self) -> None:
        conflict = Conflict(
            id="conflict-1",
            severity=ConflictSeverity.BLOCKING,
            conflict_type="time_overlap",
            message="Two itinerary items overlap.",
        )
        detector = StubConflictDetector([conflict])
        service = TripCandidateService(
            trip_repository=self.trips,
            candidate_repository=self.candidates,
            conflict_detector=detector,
            id_generator=lambda: next(self.candidate_ids),
        )
        candidate = service.create_candidate(
            user_id="user-1",
            trip_id=self.trip.id,
            data=TripCandidateCreateInput(source_type="user_edit", itinerary_snapshot={"days": []}),
        )

        validated = service.validate_candidate(user_id="user-1", candidate_id=candidate.id)

        self.assertEqual(validated.status, "blocked")
        self.assertEqual(validated.conflicts, [conflict])
        self.assertEqual(validated.validation_summary["blocking"], 1)

    def test_publish_candidate_revalidates_and_creates_current_projection(self) -> None:
        detector = StubConflictDetector()
        service = TripCandidateService(
            trip_repository=self.trips,
            candidate_repository=self.candidates,
            conflict_detector=detector,
            id_generator=lambda: next(self.candidate_ids),
        )
        candidate = service.create_candidate(
            user_id="user-1",
            trip_id=self.trip.id,
            data=TripCandidateCreateInput(
                source_type="agent",
                itinerary_snapshot={
                    "days": [
                        {
                            "date": "2026-07-01",
                            "items": [
                                {
                                    "temp_id": "item-1",
                                    "title": "Visit Senso-ji",
                                    "start_time": "09:00",
                                    "end_time": "11:00",
                                }
                            ],
                        }
                    ]
                },
            ),
        )

        version = service.publish_candidate(user_id="user-1", candidate_id=candidate.id, publish_note="Initial plan")

        self.assertEqual(detector.calls, 1)
        self.assertEqual(version.version_no, 1)
        self.assertEqual(version.publish_note, "Initial plan")
        self.assertEqual(self.trip.active_version_id, version.id)
        self.assertEqual(self.trip.days[0].items[0].title, "Visit Senso-ji")
        self.assertEqual(candidate.status, "published")

    def test_rollback_creates_new_version_without_mutating_history(self) -> None:
        service = TripCandidateService(
            trip_repository=self.trips,
            candidate_repository=self.candidates,
            conflict_detector=StubConflictDetector(),
            id_generator=lambda: next(self.candidate_ids),
        )
        first = service.create_candidate(
            user_id="user-1",
            trip_id=self.trip.id,
            data=TripCandidateCreateInput(
                source_type="agent",
                itinerary_snapshot={"days": [{"date": "2026-07-01", "items": [{"temp_id": "a", "title": "Old plan"}]}]},
            ),
        )
        first_version = service.publish_candidate(user_id="user-1", candidate_id=first.id)
        second = service.create_candidate(
            user_id="user-1",
            trip_id=self.trip.id,
            data=TripCandidateCreateInput(
                source_type="user_edit",
                itinerary_snapshot={"days": [{"date": "2026-07-01", "items": [{"temp_id": "b", "title": "New plan"}]}]},
            ),
        )
        service.publish_candidate(user_id="user-1", candidate_id=second.id)

        rollback_version = service.rollback_version(
            user_id="user-1",
            version_id=first_version.id,
            publish_note="Rollback to first version.",
        )

        self.assertEqual(rollback_version.version_no, 3)
        self.assertEqual(rollback_version.source_type, "rollback")
        self.assertEqual(rollback_version.rolled_back_from_version_id, first_version.id)
        self.assertEqual(self.trip.active_version_id, rollback_version.id)
        self.assertEqual(self.trip.days[0].items[0].title, "Old plan")
        self.assertEqual(first_version.itinerary_snapshot["days"][0]["items"][0]["title"], "Old plan")

    def test_cross_user_candidate_access_is_blocked(self) -> None:
        service = TripCandidateService(
            trip_repository=self.trips,
            candidate_repository=self.candidates,
            conflict_detector=StubConflictDetector(),
            id_generator=lambda: next(self.candidate_ids),
        )
        candidate = service.create_candidate(
            user_id="user-1",
            trip_id=self.trip.id,
            data=TripCandidateCreateInput(source_type="user_edit", itinerary_snapshot={"days": []}),
        )

        with self.assertRaises(CandidateNotFoundError):
            service.validate_candidate(user_id="user-2", candidate_id=candidate.id)


if __name__ == "__main__":
    unittest.main()
