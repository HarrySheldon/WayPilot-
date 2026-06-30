from __future__ import annotations

import hashlib

from .base import OpeningHoursResult, PlaceResult, TransferTimeResult, WeatherResult


SEED_PLACES = [
    PlaceResult(
        place_id="place:tokyo:sensoji",
        name="Senso-ji",
        city="Tokyo",
        category="attraction",
        address="2 Chome-3-1 Asakusa, Taito City, Tokyo",
        estimated_cost=0,
    ),
    PlaceResult(
        place_id="place:tokyo:ueno-park",
        name="Ueno Park",
        city="Tokyo",
        category="attraction",
        address="Uenokoen, Taito City, Tokyo",
        estimated_cost=0,
    ),
    PlaceResult(
        place_id="place:tokyo:ramen-street",
        name="Tokyo Ramen Street",
        city="Tokyo",
        category="restaurant",
        address="Tokyo Station First Avenue, Chiyoda City, Tokyo",
        estimated_cost=1800,
    ),
    PlaceResult(
        place_id="place:tokyo:edo-tokyo-museum",
        name="Edo-Tokyo Museum",
        city="Tokyo",
        category="museum",
        address="1 Chome-4-1 Yokoami, Sumida City, Tokyo",
        estimated_cost=600,
    ),
    PlaceResult(
        place_id="place:paris:louvre",
        name="Louvre Museum",
        city="Paris",
        category="museum",
        address="Rue de Rivoli, Paris",
        estimated_cost=2200,
    ),
]


class SeedPlaceProvider:
    def search_places(self, *, query: str, city: str | None, limit: int = 5) -> list[PlaceResult]:
        normalized_query = query.strip().lower()
        normalized_city = city.strip().lower() if city else None
        if not normalized_query:
            return []

        results: list[PlaceResult] = []
        for place in SEED_PLACES:
            if normalized_city is not None and place.city.lower() != normalized_city:
                continue
            searchable = " ".join(
                [place.place_id, place.name, place.city, place.category, place.address]
            ).lower()
            if normalized_query in searchable:
                results.append(place)
        return results[: max(limit, 0)]


class MockWeatherProvider:
    def get_weather(self, *, city: str, date: str) -> WeatherResult:
        bucket = _stable_bucket(f"weather:{city.lower()}:{date}", modulo=6)
        if bucket == 0:
            return WeatherResult(
                city=_title_city(city),
                date=date,
                condition="heavy_rain",
                severity="severe",
                summary="Heavy rain may affect outdoor activities.",
            )
        if bucket in {1, 2}:
            return WeatherResult(
                city=_title_city(city),
                date=date,
                condition="rain",
                severity="warning",
                summary="Rain is possible; keep flexible indoor alternatives.",
            )
        return WeatherResult(
            city=_title_city(city),
            date=date,
            condition="clear",
            severity="clear",
            summary="No material weather risk in the seed forecast.",
        )


class MockTransferTimeProvider:
    def estimate_transfer_time(
        self,
        *,
        origin_place_id: str,
        destination_place_id: str,
        mode: str,
    ) -> TransferTimeResult:
        bucket = _stable_bucket(
            f"transfer:{origin_place_id}:{destination_place_id}:{mode}",
            modulo=25,
        )
        estimated_minutes = 10 + bucket
        return TransferTimeResult(
            origin_place_id=origin_place_id,
            destination_place_id=destination_place_id,
            mode=mode,
            estimated_minutes=estimated_minutes,
            required_minutes=estimated_minutes + 10,
        )


class MockOpeningHoursProvider:
    def check_opening_hours(
        self,
        *,
        place_id: str,
        date: str,
        start_time: str,
        end_time: str,
    ) -> OpeningHoursResult:
        if place_id == "place:tokyo:edo-tokyo-museum" and date == "2026-07-06":
            return OpeningHoursResult(
                place_id=place_id,
                date=date,
                start_time=start_time,
                end_time=end_time,
                status="closed",
                is_open=False,
                reason="Seed data marks this museum closed on the requested date.",
            )
        return OpeningHoursResult(
            place_id=place_id,
            date=date,
            start_time=start_time,
            end_time=end_time,
            status="open",
            is_open=True,
        )


def _stable_bucket(value: str, *, modulo: int) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % modulo


def _title_city(city: str) -> str:
    return city.strip().title()
