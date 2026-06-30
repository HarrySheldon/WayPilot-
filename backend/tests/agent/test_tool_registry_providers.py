from __future__ import annotations

import unittest

from backend.app.agent.tools import ToolContext, ToolExecutionError, ToolRegistry
from backend.app.providers.seed import (
    MockOpeningHoursProvider,
    MockTransferTimeProvider,
    MockWeatherProvider,
    SeedPlaceProvider,
)
from backend.app.repositories.memory import InMemoryToolCallRepository


class ToolRegistryProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tool_calls = InMemoryToolCallRepository()
        self.registry = ToolRegistry(
            candidate_service=None,
            tool_call_repository=self.tool_calls,
            place_provider=SeedPlaceProvider(),
            weather_provider=MockWeatherProvider(),
            transfer_time_provider=MockTransferTimeProvider(),
            opening_hours_provider=MockOpeningHoursProvider(),
        )
        self.context = ToolContext(user_id="user-1", trip_id="trip-1", agent_run_id="run-1")

    def test_search_places_tool_records_successful_tool_call(self) -> None:
        result = self.registry.execute(
            "search_places",
            context=self.context,
            arguments={"query": "ramen", "city": "Tokyo", "limit": 1},
        )

        calls = self.tool_calls.list_by_run("run-1")
        self.assertEqual(result["places"][0]["place_id"], "place:tokyo:ramen-street")
        self.assertEqual(calls[0].tool_name, "search_places")
        self.assertEqual(calls[0].status, "success")
        self.assertEqual(calls[0].result, result)

    def test_weather_transfer_and_opening_tools_return_structured_results(self) -> None:
        weather = self.registry.execute(
            "get_weather",
            context=self.context,
            arguments={"city": "Tokyo", "date": "2026-07-01"},
        )
        transfer = self.registry.execute(
            "estimate_transfer_time",
            context=self.context,
            arguments={
                "origin_place_id": "place:tokyo:sensoji",
                "destination_place_id": "place:tokyo:ueno-park",
                "mode": "transit",
            },
        )
        opening = self.registry.execute(
            "check_opening_hours",
            context=self.context,
            arguments={
                "place_id": "place:tokyo:edo-tokyo-museum",
                "date": "2026-07-06",
                "start_time": "10:00",
                "end_time": "12:00",
            },
        )

        self.assertEqual(weather["weather"]["city"], "Tokyo")
        self.assertEqual(transfer["transfer_time"]["origin_place_id"], "place:tokyo:sensoji")
        self.assertEqual(opening["opening_hours"]["status"], "closed")
        self.assertEqual([call.tool_name for call in self.tool_calls.list_by_run("run-1")], [
            "get_weather",
            "estimate_transfer_time",
            "check_opening_hours",
        ])

    def test_calculate_budget_sums_estimated_costs(self) -> None:
        result = self.registry.execute(
            "calculate_budget",
            context=self.context,
            arguments={
                "itinerary_snapshot": {
                    "days": [
                        {
                            "items": [
                                {"title": "Museum", "estimated_cost": 1200},
                                {"title": "Lunch", "estimated_cost": 1800},
                                {"title": "Walk"},
                            ]
                        }
                    ]
                },
                "currency": "JPY",
            },
        )

        self.assertEqual(result, {"currency": "JPY", "total": 3000, "item_count": 2})

    def test_provider_tools_require_context(self) -> None:
        with self.assertRaisesRegex(ToolExecutionError, "tool context must include"):
            self.registry.execute(
                "search_places",
                context=ToolContext(user_id="", trip_id="trip-1", agent_run_id="run-1"),
                arguments={"query": "ramen", "city": "Tokyo"},
            )


if __name__ == "__main__":
    unittest.main()
