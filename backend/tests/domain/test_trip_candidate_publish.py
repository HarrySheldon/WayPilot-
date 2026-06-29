import unittest

from backend.app.domain.trips import (
    Conflict,
    ConflictSeverity,
    PublishBlockedError,
    Trip,
    TripCandidate,
    TripCandidatePublisher,
)


class TripCandidatePublisherTests(unittest.TestCase):
    def test_blocking_conflict_prevents_publish(self) -> None:
        trip = Trip(id="trip-1")
        candidate = TripCandidate(
            id="candidate-1",
            trip_id=trip.id,
            itinerary_snapshot={"days": []},
            conflicts=[
                Conflict(
                    id="conflict-1",
                    severity=ConflictSeverity.BLOCKING,
                    conflict_type="time_overlap",
                    message="Two itinerary items overlap.",
                )
            ],
        )

        with self.assertRaisesRegex(PublishBlockedError, "blocking conflicts"):
            TripCandidatePublisher().publish(trip=trip, candidate=candidate)

        self.assertIsNone(trip.active_version_id)
        self.assertEqual(candidate.status, "ready")

    def test_warning_conflict_requires_explicit_confirmation(self) -> None:
        trip = Trip(id="trip-1")
        candidate = TripCandidate(
            id="candidate-1",
            trip_id=trip.id,
            itinerary_snapshot={"days": []},
            conflicts=[
                Conflict(
                    id="conflict-1",
                    severity=ConflictSeverity.WARNING,
                    conflict_type="weather_risk",
                    message="Outdoor activity may be affected by rain.",
                )
            ],
        )

        with self.assertRaisesRegex(PublishBlockedError, "unconfirmed warnings"):
            TripCandidatePublisher().publish(trip=trip, candidate=candidate)

        self.assertIsNone(trip.active_version_id)
        self.assertEqual(candidate.status, "ready")

    def test_confirmed_warning_publishes_version_and_rebuilds_projection(self) -> None:
        trip = Trip(id="trip-1")
        candidate = TripCandidate(
            id="candidate-1",
            trip_id=trip.id,
            itinerary_snapshot={
                "days": [
                    {
                        "date": "2026-07-01",
                        "items": [
                            {
                                "temp_id": "item-1",
                                "title": "Visit museum",
                                "start_time": "10:00",
                                "end_time": "12:00",
                            }
                        ],
                    }
                ]
            },
            budget_snapshot={"currency": "USD", "total": 120},
            preference_snapshot={"pace": "relaxed"},
            conflicts=[
                Conflict(
                    id="conflict-1",
                    severity=ConflictSeverity.WARNING,
                    conflict_type="weather_risk",
                    message="Outdoor activity may be affected by rain.",
                )
            ],
        )

        version = TripCandidatePublisher().publish(
            trip=trip,
            candidate=candidate,
            ignored_warning_conflict_ids={"conflict-1"},
            publish_note="User accepted weather risk.",
        )

        self.assertEqual(version.version_no, 1)
        self.assertEqual(version.source_candidate_id, candidate.id)
        self.assertEqual(version.ignored_warning_conflict_ids, ["conflict-1"])
        self.assertEqual(version.itinerary_snapshot, candidate.itinerary_snapshot)
        self.assertEqual(version.budget_snapshot, candidate.budget_snapshot)
        self.assertEqual(version.preference_snapshot, candidate.preference_snapshot)
        self.assertEqual(version.publish_note, "User accepted weather risk.")
        self.assertEqual(trip.active_version_id, version.id)
        self.assertEqual(trip.status, "active")
        self.assertEqual(candidate.status, "published")
        self.assertEqual(len(trip.days), 1)
        self.assertEqual(trip.days[0].items[0].title, "Visit museum")


if __name__ == "__main__":
    unittest.main()
