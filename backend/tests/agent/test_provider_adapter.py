from __future__ import annotations

import unittest

from backend.app.agent.provider_openai_compatible import (
    OpenAICompatibleProviderAdapter,
    ProviderError,
)
from backend.app.domain.agents import UnifiedMessage
from backend.app.domain.rag import RagHit


class FakeHttpClient:
    def __init__(self, response: dict | None = None, status_code: int = 200) -> None:
        self.response = response or {
            "choices": [{"message": {"content": '{"trip_summary":"Tokyo","days":[]}'}}]
        }
        self.status_code = status_code
        self.requests: list[dict] = []

    def post_json(self, *, url: str, headers: dict[str, str], payload: dict, timeout_seconds: float) -> dict:
        self.requests.append(
            {
                "url": url,
                "headers": headers,
                "payload": payload,
                "timeout_seconds": timeout_seconds,
            }
        )
        if self.status_code >= 400:
            raise ProviderError(f"provider returned {self.status_code}")
        return self.response


class OpenAICompatibleProviderAdapterTests(unittest.TestCase):
    def test_generate_itinerary_sends_chat_completion_request_and_parses_json_content(self) -> None:
        http = FakeHttpClient()
        adapter = OpenAICompatibleProviderAdapter(
            base_url="https://api.example.com/v1",
            api_key="test-key",
            model="travel-model",
            http_client=http,
            timeout_seconds=12,
        )

        result = adapter.generate_itinerary(
            messages=[UnifiedMessage(role="user", content="Plan Tokyo")],
            rag_hits=[
                RagHit(
                    document_id="doc-1",
                    chunk_id="chunk-1",
                    source_type="city_guide",
                    title="Tokyo guide",
                    city="Tokyo",
                    score=1.0,
                    snippet="Tokyo ramen",
                )
            ],
        )

        request = http.requests[0]
        self.assertEqual(result, {"trip_summary": "Tokyo", "days": []})
        self.assertEqual(request["url"], "https://api.example.com/v1/chat/completions")
        self.assertEqual(request["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(request["payload"]["model"], "travel-model")
        self.assertEqual(request["payload"]["response_format"], {"type": "json_object"})
        self.assertEqual(request["payload"]["messages"][0]["role"], "system")
        self.assertIn("chunk-1", request["payload"]["messages"][0]["content"])
        self.assertEqual(request["payload"]["messages"][1], {"role": "user", "content": "Plan Tokyo"})
        self.assertEqual(request["timeout_seconds"], 12)

    def test_generate_itinerary_raises_provider_error_for_invalid_json_content(self) -> None:
        adapter = OpenAICompatibleProviderAdapter(
            base_url="https://api.example.com/v1",
            api_key="test-key",
            model="travel-model",
            http_client=FakeHttpClient(response={"choices": [{"message": {"content": "not json"}}]}),
        )

        with self.assertRaisesRegex(ProviderError, "valid JSON"):
            adapter.generate_itinerary(messages=[UnifiedMessage(role="user", content="Plan")], rag_hits=[])

    def test_generate_itinerary_raises_provider_error_for_missing_message_content(self) -> None:
        adapter = OpenAICompatibleProviderAdapter(
            base_url="https://api.example.com/v1",
            api_key="test-key",
            model="travel-model",
            http_client=FakeHttpClient(response={"choices": [{"message": {}}]}),
        )

        with self.assertRaisesRegex(ProviderError, "message content"):
            adapter.generate_itinerary(messages=[UnifiedMessage(role="user", content="Plan")], rag_hits=[])


if __name__ == "__main__":
    unittest.main()
