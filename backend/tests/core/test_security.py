from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from backend.app.core.security import ExpiredTokenError, InvalidTokenError, TokenService


class TokenServiceTests(unittest.TestCase):
    def test_access_token_round_trip_returns_subject(self) -> None:
        now = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)
        service = TokenService(secret_key="test-secret", now=lambda: now)

        token = service.create_access_token(user_id="user-1")
        payload = service.verify_access_token(token)

        self.assertEqual(payload.subject, "user-1")
        self.assertEqual(payload.issuer, "waypilot")

    def test_tampered_access_token_is_rejected(self) -> None:
        now = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)
        service = TokenService(secret_key="test-secret", now=lambda: now)
        token = service.create_access_token(user_id="user-1")
        tampered = token[:-1] + ("a" if token[-1] != "a" else "b")

        with self.assertRaises(InvalidTokenError):
            service.verify_access_token(tampered)

    def test_expired_access_token_is_rejected(self) -> None:
        issued_at = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)
        checked_at = issued_at + timedelta(minutes=61)
        service = TokenService(
            secret_key="test-secret",
            now=lambda: issued_at,
            access_token_ttl=timedelta(minutes=60),
        )
        token = service.create_access_token(user_id="user-1")
        verifier = TokenService(secret_key="test-secret", now=lambda: checked_at)

        with self.assertRaises(ExpiredTokenError):
            verifier.verify_access_token(token)


if __name__ == "__main__":
    unittest.main()
