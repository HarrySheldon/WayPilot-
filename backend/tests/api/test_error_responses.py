from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from backend.app.api import dependencies
from backend.app.main import create_app


class ErrorResponseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_http_errors_use_error_envelope_with_request_id(self) -> None:
        response = self.client.get("/api/v1/trips")

        body = response.json()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(body["error"]["code"], "not_authenticated")
        self.assertEqual(body["error"]["message"], "Not authenticated")
        self.assertTrue(body["error"]["request_id"])
        self.assertEqual(response.headers["x-request-id"], body["error"]["request_id"])

    def test_validation_errors_use_error_envelope(self) -> None:
        self.app.dependency_overrides[dependencies.get_current_user_id] = lambda: "user-1"

        response = self.client.post("/api/v1/trips", json={})

        body = response.json()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(body["error"]["code"], "validation_error")
        self.assertEqual(body["error"]["message"], "Request validation failed")
        self.assertTrue(body["error"]["request_id"])

    def test_unhandled_errors_do_not_leak_internal_message(self) -> None:
        @self.app.get("/explode")
        def explode():
            raise RuntimeError("provider api key sk-secret leaked")

        response = self.client.get("/explode")

        body = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertEqual(body["error"]["message"], "Internal server error")
        self.assertNotIn("sk-secret", response.text)


if __name__ == "__main__":
    unittest.main()
