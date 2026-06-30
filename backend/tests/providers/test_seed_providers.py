from __future__ import annotations

import unittest

from backend.app.providers.seed import (
    MockOpeningHoursProvider,
    MockTransferTimeProvider,
    MockWeatherProvider,
    SeedPlaceProvider,
)


class SeedProviderTests(unittest.TestCase):
    def test_place_provider_returns_stable_internal_place_ids(self) -> None:
        provider = SeedPlaceProvider()

        results = provider.search_places(query="Sensoji", city="tokyo", limit=3)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].place_id, "place:tokyo:sensoji")
        self.assertEqual(results[0].name, "Senso-ji")
        self.assertEqual(results[0].city, "Tokyo")
        self.assertEqual(results[0].category, "attraction")

    def test_place_provider_respects_limit_and_city_filter(self) -> None:
        provider = SeedPlaceProvider()

        results = provider.search_places(query="tokyo", city="Tokyo", limit=2)

        self.assertEqual(len(results), 2)
        self.assertTrue(all(result.city == "Tokyo" for result in results))

    def test_weather_provider_returns_deterministic_result(self) -> None:
        weather = MockWeatherProvider().get_weather(city="Tokyo", date="2026-07-01")

        self.assertEqual(weather.city, "Tokyo")
        self.assertEqual(weather.date, "2026-07-01")
        self.assertIn(weather.severity, {"clear", "warning", "severe"})
        self.assertIsInstance(weather.summary, str)

    def test_transfer_provider_returns_required_buffer(self) -> None:
        transfer = MockTransferTimeProvider().estimate_transfer_time(
            origin_place_id="place:tokyo:sensoji",
            destination_place_id="place:tokyo:ueno-park",
            mode="transit",
        )

        self.assertEqual(transfer.origin_place_id, "place:tokyo:sensoji")
        self.assertEqual(transfer.destination_place_id, "place:tokyo:ueno-park")
        self.assertEqual(transfer.mode, "transit")
        self.assertGreaterEqual(transfer.required_minutes, transfer.estimated_minutes)

    def test_opening_hours_provider_marks_known_closed_slots(self) -> None:
        result = MockOpeningHoursProvider().check_opening_hours(
            place_id="place:tokyo:edo-tokyo-museum",
            date="2026-07-06",
            start_time="10:00",
            end_time="12:00",
        )

        self.assertEqual(result.place_id, "place:tokyo:edo-tokyo-museum")
        self.assertEqual(result.status, "closed")
        self.assertFalse(result.is_open)


if __name__ == "__main__":
    unittest.main()
