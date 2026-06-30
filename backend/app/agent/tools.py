from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ..domain.agents import ToolCall
from ..providers.base import OpeningHoursProvider, PlaceProvider, TransferTimeProvider, WeatherProvider
from ..providers.seed import (
    MockOpeningHoursProvider,
    MockTransferTimeProvider,
    MockWeatherProvider,
    SeedPlaceProvider,
)
from ..services.trip_candidates import TripCandidateCreateInput, TripCandidateService


class ToolExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ToolContext:
    user_id: str
    trip_id: str
    agent_run_id: str


class ToolCallRepository(Protocol):
    def next_id(self, agent_run_id: str) -> str:
        ...

    def save(self, call: ToolCall) -> ToolCall:
        ...

    def list_by_run(self, agent_run_id: str) -> list[ToolCall]:
        ...


class ToolRegistry:
    def __init__(
        self,
        *,
        candidate_service: TripCandidateService | None,
        tool_call_repository: ToolCallRepository,
        place_provider: PlaceProvider | None = None,
        weather_provider: WeatherProvider | None = None,
        transfer_time_provider: TransferTimeProvider | None = None,
        opening_hours_provider: OpeningHoursProvider | None = None,
    ) -> None:
        self._candidate_service = candidate_service
        self._tool_call_repository = tool_call_repository
        self._place_provider = place_provider or SeedPlaceProvider()
        self._weather_provider = weather_provider or MockWeatherProvider()
        self._transfer_time_provider = transfer_time_provider or MockTransferTimeProvider()
        self._opening_hours_provider = opening_hours_provider or MockOpeningHoursProvider()

    def execute(self, tool_name: str, *, context: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        if not context.user_id or not context.trip_id or not context.agent_run_id:
            raise ToolExecutionError("tool context must include user_id, trip_id, and agent_run_id")

        call = ToolCall(
            id=self._tool_call_repository.next_id(context.agent_run_id),
            agent_run_id=context.agent_run_id,
            tool_name=tool_name,
            arguments=dict(arguments),
        )
        self._tool_call_repository.save(call)

        try:
            result = self._execute(tool_name=tool_name, context=context, arguments=arguments)
        except Exception as exc:
            call.status = "error"
            call.error = str(exc)
            self._tool_call_repository.save(call)
            raise ToolExecutionError(str(exc)) from exc

        call.status = "success"
        call.result = result
        self._tool_call_repository.save(call)
        return result

    def list_tool_calls(self, *, agent_run_id: str):
        return self._tool_call_repository.list_by_run(agent_run_id)

    def _execute(self, *, tool_name: str, context: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "search_places":
            places = self._place_provider.search_places(
                query=str(arguments["query"]),
                city=str(arguments["city"]) if arguments.get("city") is not None else None,
                limit=int(arguments.get("limit", 5)),
            )
            return {"places": [place.to_dict() for place in places]}

        if tool_name == "get_weather":
            weather = self._weather_provider.get_weather(
                city=str(arguments["city"]),
                date=str(arguments["date"]),
            )
            return {"weather": weather.to_dict()}

        if tool_name == "estimate_transfer_time":
            transfer = self._transfer_time_provider.estimate_transfer_time(
                origin_place_id=str(arguments["origin_place_id"]),
                destination_place_id=str(arguments["destination_place_id"]),
                mode=str(arguments.get("mode", "transit")),
            )
            return {"transfer_time": transfer.to_dict()}

        if tool_name == "check_opening_hours":
            opening_hours = self._opening_hours_provider.check_opening_hours(
                place_id=str(arguments["place_id"]),
                date=str(arguments["date"]),
                start_time=str(arguments["start_time"]),
                end_time=str(arguments["end_time"]),
            )
            return {"opening_hours": opening_hours.to_dict()}

        if tool_name == "calculate_budget":
            return _calculate_budget(arguments)

        if tool_name == "create_trip_candidate":
            if self._candidate_service is None:
                raise ToolExecutionError("candidate service is not configured")
            candidate = self._candidate_service.create_candidate(
                user_id=context.user_id,
                trip_id=context.trip_id,
                data=TripCandidateCreateInput(
                    source_type=str(arguments["source_type"]),
                    source_agent_run_id=context.agent_run_id,
                    itinerary_snapshot=dict(arguments["itinerary_snapshot"]),
                    budget_snapshot=dict(arguments.get("budget_snapshot", {})),
                    preference_snapshot=dict(arguments.get("preference_snapshot", {})),
                ),
            )
            return {"candidate_id": candidate.id, "status": candidate.status}

        if tool_name == "validate_itinerary":
            if self._candidate_service is None:
                raise ToolExecutionError("candidate service is not configured")
            candidate = self._candidate_service.validate_candidate(
                user_id=context.user_id,
                candidate_id=str(arguments["candidate_id"]),
            )
            return {
                "candidate_id": candidate.id,
                "status": candidate.status,
                "validation_summary": dict(candidate.validation_summary),
            }

        raise ToolExecutionError(f"unknown tool: {tool_name}")


def _calculate_budget(arguments: dict[str, Any]) -> dict[str, Any]:
    snapshot = dict(arguments.get("itinerary_snapshot", {}))
    currency = str(arguments.get("currency") or snapshot.get("currency") or "USD")
    total = 0
    item_count = 0
    for day in snapshot.get("days", []):
        if not isinstance(day, dict):
            continue
        for item in day.get("items", []):
            if not isinstance(item, dict):
                continue
            cost = item.get("estimated_cost")
            if isinstance(cost, int):
                total += cost
                item_count += 1
    return {"currency": currency, "total": total, "item_count": item_count}
