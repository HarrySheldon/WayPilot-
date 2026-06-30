from __future__ import annotations

import unittest

from redis.exceptions import RedisError

from backend.app.providers.base import PlaceResult, WeatherResult
from backend.app.providers.cache import CachedPlaceProvider, CachedWeatherProvider


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def get(self, key: str):
        return self.values.get(key)

    def setex(self, key: str, ttl_seconds: int, value: str):
        self.values[key] = value
        self.ttls[key] = ttl_seconds
        return True


class FailingRedis:
    def get(self, key: str):
        raise RedisError("redis unavailable")

    def setex(self, key: str, ttl_seconds: int, value: str):
        raise RedisError("redis unavailable")


class CountingWeatherProvider:
    def __init__(self) -> None:
        self.calls = 0

    def get_weather(self, *, city: str, date: str) -> WeatherResult:
        self.calls += 1
        return WeatherResult(
            city=city,
            date=date,
            condition="clear",
            severity="clear",
            summary=f"call {self.calls}",
        )


class CountingPlaceProvider:
    def __init__(self) -> None:
        self.calls = 0

    def search_places(self, *, query: str, city: str | None, limit: int = 5) -> list[PlaceResult]:
        self.calls += 1
        return [
            PlaceResult(
                place_id=f"place:{self.calls}",
                name=query,
                city=city or "",
                category="test",
                address="seed",
            )
        ][:limit]


class ProviderCacheTests(unittest.TestCase):
    def test_weather_cache_hits_for_same_city_and_date(self) -> None:
        redis_client = FakeRedis()
        provider = CountingWeatherProvider()
        cached = CachedWeatherProvider(provider=provider, redis_client=redis_client, ttl_seconds=300)

        first = cached.get_weather(city="Tokyo", date="2026-07-01")
        second = cached.get_weather(city="Tokyo", date="2026-07-01")

        self.assertEqual(provider.calls, 1)
        self.assertEqual(first, second)
        self.assertEqual(redis_client.ttls["provider:weather:tokyo:2026-07-01"], 300)

    def test_weather_cache_key_includes_city_and_date(self) -> None:
        redis_client = FakeRedis()
        provider = CountingWeatherProvider()
        cached = CachedWeatherProvider(provider=provider, redis_client=redis_client, ttl_seconds=300)

        cached.get_weather(city="Tokyo", date="2026-07-01")
        cached.get_weather(city="Tokyo", date="2026-07-02")

        self.assertEqual(provider.calls, 2)

    def test_place_cache_stores_internal_dto_list(self) -> None:
        redis_client = FakeRedis()
        provider = CountingPlaceProvider()
        cached = CachedPlaceProvider(provider=provider, redis_client=redis_client, ttl_seconds=300)

        first = cached.search_places(query="ramen", city="Tokyo", limit=1)
        second = cached.search_places(query="ramen", city="Tokyo", limit=1)

        self.assertEqual(provider.calls, 1)
        self.assertEqual(first, second)
        cached_value = redis_client.values["provider:places:ramen:tokyo:1"]
        self.assertIn('"place_id"', cached_value)
        self.assertNotIn("raw_response", cached_value)

    def test_redis_outage_falls_back_to_provider(self) -> None:
        provider = CountingWeatherProvider()
        cached = CachedWeatherProvider(provider=provider, redis_client=FailingRedis(), ttl_seconds=300)

        result = cached.get_weather(city="Tokyo", date="2026-07-01")

        self.assertEqual(provider.calls, 1)
        self.assertEqual(result.city, "Tokyo")


if __name__ == "__main__":
    unittest.main()
