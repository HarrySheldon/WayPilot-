import unittest

from backend.app.repositories.memory import InMemoryPreferenceRepository, InMemoryTripRepository
from backend.app.services.trips import (
    PreferenceService,
    TripCreateInput,
    TripNotFoundError,
    TripService,
    TripValidationError,
    UserPreferenceInput,
)


class TripServiceTests(unittest.TestCase):
    def test_create_trip_saves_draft_trip_with_preferences(self) -> None:
        trips = InMemoryTripRepository()
        service = TripService(trip_repository=trips, id_generator=lambda: "trip-1")

        trip = service.create_trip(
            user_id="user-1",
            data=TripCreateInput(
                title="Tokyo family trip",
                destination="Tokyo",
                start_date="2026-07-01",
                end_date="2026-07-05",
                travelers_count=3,
                budget_total=3000,
                pace="relaxed",
                interests=["food", "history"],
                dietary_preferences=["no beef"],
                must_visit_places=["Senso-ji"],
                avoidances=["late-night transfers"],
                natural_language_note="Traveling with parents, keep the schedule relaxed.",
            ),
        )

        self.assertEqual(trip.id, "trip-1")
        self.assertEqual(trip.user_id, "user-1")
        self.assertEqual(trip.status, "draft")
        self.assertEqual(trip.preference.destination, "Tokyo")
        self.assertEqual(trip.preference.pace, "relaxed")
        self.assertEqual(trip.preference.interests, ["food", "history"])
        self.assertEqual(trip.preference.natural_language_note, "Traveling with parents, keep the schedule relaxed.")

    def test_list_trips_returns_only_the_requesting_users_trips(self) -> None:
        trips = InMemoryTripRepository()
        ids = iter(["trip-1", "trip-2"])
        service = TripService(trip_repository=trips, id_generator=lambda: next(ids))

        service.create_trip(user_id="user-1", data=TripCreateInput(title="Tokyo", destination="Tokyo"))
        service.create_trip(user_id="user-2", data=TripCreateInput(title="Paris", destination="Paris"))

        result = service.list_trips(user_id="user-1")

        self.assertEqual([trip.title for trip in result], ["Tokyo"])

    def test_get_trip_raises_not_found_for_another_users_trip(self) -> None:
        trips = InMemoryTripRepository()
        service = TripService(trip_repository=trips, id_generator=lambda: "trip-1")
        service.create_trip(user_id="user-1", data=TripCreateInput(title="Tokyo", destination="Tokyo"))

        with self.assertRaises(TripNotFoundError):
            service.get_trip(user_id="user-2", trip_id="trip-1")

    def test_create_trip_rejects_blank_title(self) -> None:
        trips = InMemoryTripRepository()
        service = TripService(trip_repository=trips)

        with self.assertRaisesRegex(TripValidationError, "title is required"):
            service.create_trip(user_id="user-1", data=TripCreateInput(title="  ", destination="Tokyo"))

    def test_create_trip_rejects_blank_destination(self) -> None:
        trips = InMemoryTripRepository()
        service = TripService(trip_repository=trips)

        with self.assertRaisesRegex(TripValidationError, "destination is required"):
            service.create_trip(user_id="user-1", data=TripCreateInput(title="Summer trip", destination=""))

    def test_create_trip_rejects_invalid_traveler_count(self) -> None:
        trips = InMemoryTripRepository()
        service = TripService(trip_repository=trips)

        with self.assertRaisesRegex(TripValidationError, "travelers_count must be at least 1"):
            service.create_trip(user_id="user-1", data=TripCreateInput(title="Tokyo", destination="Tokyo", travelers_count=0))

    def test_create_trip_rejects_negative_budget(self) -> None:
        trips = InMemoryTripRepository()
        service = TripService(trip_repository=trips)

        with self.assertRaisesRegex(TripValidationError, "budget_total cannot be negative"):
            service.create_trip(user_id="user-1", data=TripCreateInput(title="Tokyo", destination="Tokyo", budget_total=-1))


class PreferenceServiceTests(unittest.TestCase):
    def test_upsert_user_preference_is_scoped_to_user(self) -> None:
        preferences = InMemoryPreferenceRepository()
        service = PreferenceService(preference_repository=preferences)

        preference = service.upsert_user_preference(
            user_id="user-1",
            data=UserPreferenceInput(
                default_pace="relaxed",
                interests=["food", "nature"],
                dietary_preferences=["vegetarian"],
                avoidances=["crowded attractions"],
            ),
        )

        self.assertEqual(preference.user_id, "user-1")
        self.assertEqual(preference.default_pace, "relaxed")
        self.assertEqual(preference.interests, ["food", "nature"])
        self.assertIsNone(service.get_user_preference(user_id="user-2"))


if __name__ == "__main__":
    unittest.main()
