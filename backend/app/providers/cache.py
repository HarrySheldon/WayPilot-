from __future__ import annotations

import json
from typing import Any, Protocol

from redis.exceptions import RedisError

from .base import OpeningHoursResult, PlaceResult, TransferTimeResult, WeatherResult


class RedisCacheClient(Protocol):
    def get(self, key: str):
        ...

    def setex(self, key: str, ttl_seconds: int, value: str):
        ...


class CachedPlaceProvider:
    def __init__(self, *, provider, redis_client: RedisCacheClient, ttl_seconds: int) -> None:
        self._provider = provider
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds

    def search_places(self, *, query: str, city: str | None, limit: int = 5) -> list[PlaceResult]:
        key = f"provider:places:{_normalize(query)}:{_normalize(city or '')}:{limit}"
        cached = _safe_get_json(self._redis, key)
        if isinstance(cached, list):
            return [PlaceResult(**item) for item in cached]

        results = self._provider.search_places(query=query, city=city, limit=limit)
        _safe_set_json(self._redis, key, [result.to_dict() for result in results], self._ttl_seconds)
        return results


class CachedWeatherProvider:
    def __init__(self, *, provider, redis_client: RedisCacheClient, ttl_seconds: int) -> None:
        self._provider = provider
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds

    def get_weather(self, *, city: str, date: str) -> WeatherResult:
        key = f"provider:weather:{_normalize(city)}:{date}"
        cached = _safe_get_json(self._redis, key)
        if isinstance(cached, dict):
            return WeatherResult(**cached)

        result = self._provider.get_weather(city=city, date=date)
        _safe_set_json(self._redis, key, result.to_dict(), self._ttl_seconds)
        return result


class CachedTransferTimeProvider:
    def __init__(self, *, provider, redis_client: RedisCacheClient, ttl_seconds: int) -> None:
        self._provider = provider
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds

    def estimate_transfer_time(
        self,
        *,
        origin_place_id: str,
        destination_place_id: str,
        mode: str,
    ) -> TransferTimeResult:
        key = f"provider:transfer:{origin_place_id}:{destination_place_id}:{_normalize(mode)}"
        cached = _safe_get_json(self._redis, key)
        if isinstance(cached, dict):
            return TransferTimeResult(**cached)

        result = self._provider.estimate_transfer_time(
            origin_place_id=origin_place_id,
            destination_place_id=destination_place_id,
            mode=mode,
        )
        _safe_set_json(self._redis, key, result.to_dict(), self._ttl_seconds)
        return result


class CachedOpeningHoursProvider:
    def __init__(self, *, provider, redis_client: RedisCacheClient, ttl_seconds: int) -> None:
        self._provider = provider
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds

    def check_opening_hours(
        self,
        *,
        place_id: str,
        date: str,
        start_time: str,
        end_time: str,
    ) -> OpeningHoursResult:
        key = f"provider:opening:{place_id}:{date}:{start_time}:{end_time}"
        cached = _safe_get_json(self._redis, key)
        if isinstance(cached, dict):
            return OpeningHoursResult(**cached)

        result = self._provider.check_opening_hours(
            place_id=place_id,
            date=date,
            start_time=start_time,
            end_time=end_time,
        )
        _safe_set_json(self._redis, key, result.to_dict(), self._ttl_seconds)
        return result


def _safe_get_json(redis_client: RedisCacheClient, key: str) -> Any | None:
    try:
        raw = redis_client.get(key)
    except RedisError:
        return None
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def _safe_set_json(redis_client: RedisCacheClient, key: str, value: Any, ttl_seconds: int) -> None:
    try:
        redis_client.setex(key, ttl_seconds, json.dumps(value, sort_keys=True))
    except RedisError:
        return


def _normalize(value: str) -> str:
    return value.strip().lower()
