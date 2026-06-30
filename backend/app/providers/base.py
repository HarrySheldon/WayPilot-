from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol


@dataclass(frozen=True)
class PlaceResult:
    place_id: str
    name: str
    city: str
    category: str
    address: str
    estimated_cost: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class WeatherResult:
    city: str
    date: str
    condition: str
    severity: str
    summary: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TransferTimeResult:
    origin_place_id: str
    destination_place_id: str
    mode: str
    estimated_minutes: int
    required_minutes: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class OpeningHoursResult:
    place_id: str
    date: str
    start_time: str
    end_time: str
    status: str
    is_open: bool
    reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class PlaceProvider(Protocol):
    def search_places(self, *, query: str, city: str | None, limit: int = 5) -> list[PlaceResult]:
        ...


class WeatherProvider(Protocol):
    def get_weather(self, *, city: str, date: str) -> WeatherResult:
        ...


class TransferTimeProvider(Protocol):
    def estimate_transfer_time(
        self,
        *,
        origin_place_id: str,
        destination_place_id: str,
        mode: str,
    ) -> TransferTimeResult:
        ...


class OpeningHoursProvider(Protocol):
    def check_opening_hours(
        self,
        *,
        place_id: str,
        date: str,
        start_time: str,
        end_time: str,
    ) -> OpeningHoursResult:
        ...
