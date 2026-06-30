from __future__ import annotations

import json
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..domain.agents import UnifiedMessage
from ..domain.rag import RagHit


class ProviderError(RuntimeError):
    pass


class JSONHttpClient(Protocol):
    def post_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        ...


class UrllibJSONHttpClient:
    def post_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={**headers, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            raise ProviderError(f"provider returned {exc.code}") from exc
        except URLError as exc:
            raise ProviderError(f"provider request failed: {exc.reason}") from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderError("provider response must be valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ProviderError("provider response must be a JSON object")
        return parsed


class OpenAICompatibleProviderAdapter:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        http_client: JSONHttpClient | None = None,
        timeout_seconds: float = 30,
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        if not model:
            raise ValueError("model is required")
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._http_client = http_client or UrllibJSONHttpClient()
        self._timeout_seconds = timeout_seconds

    def generate_itinerary(self, *, messages: list[UnifiedMessage], rag_hits: list[RagHit]) -> dict:
        response = self._http_client.post_json(
            url=f"{self._base_url}/chat/completions",
            headers=self._headers(),
            payload={
                "model": self._model,
                "messages": _to_openai_messages(messages=messages, rag_hits=rag_hits),
                "response_format": {"type": "json_object"},
            },
            timeout_seconds=self._timeout_seconds,
        )
        return _parse_json_content(response)

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers


def _to_openai_messages(*, messages: list[UnifiedMessage], rag_hits: list[RagHit]) -> list[dict[str, str]]:
    converted: list[dict[str, str]] = []
    if rag_hits:
        converted.append({"role": "system", "content": _format_rag_context(rag_hits)})
    converted.extend({"role": message.role, "content": message.content} for message in messages)
    return converted


def _format_rag_context(rag_hits: list[RagHit]) -> str:
    lines = ["Use only the following retrieved context when it is relevant:"]
    for hit in rag_hits:
        lines.append(f"- [{hit.chunk_id}] {hit.title}: {hit.snippet}")
    return "\n".join(lines)


def _parse_json_content(response: dict[str, Any]) -> dict:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError("provider response is missing message content") from exc
    if not isinstance(content, str) or not content.strip():
        raise ProviderError("provider response is missing message content")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ProviderError("provider message content must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ProviderError("provider message content must be a JSON object")
    return parsed
