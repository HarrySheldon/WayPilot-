from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from typing import Any, Callable


class InvalidTokenError(ValueError):
    pass


class ExpiredTokenError(InvalidTokenError):
    pass


@dataclass(frozen=True)
class TokenPayload:
    subject: str
    issuer: str


class TokenService:
    def __init__(
        self,
        *,
        secret_key: str,
        issuer: str = "waypilot",
        access_token_ttl: timedelta = timedelta(minutes=60),
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if not secret_key:
            raise ValueError("secret_key is required")
        self._secret_key = secret_key.encode("utf-8")
        self._issuer = issuer
        self._access_token_ttl = access_token_ttl
        self._now = now or (lambda: datetime.now(timezone.utc))

    def create_access_token(self, *, user_id: str) -> str:
        if not user_id:
            raise ValueError("user_id is required")
        issued_at = self._now()
        payload = {
            "sub": user_id,
            "iss": self._issuer,
            "iat": int(issued_at.timestamp()),
            "exp": int((issued_at + self._access_token_ttl).timestamp()),
        }
        header = {"alg": "HS256", "typ": "JWT"}
        signing_input = f"{_json_b64(header)}.{_json_b64(payload)}"
        signature = _b64encode(
            hmac.new(self._secret_key, signing_input.encode("ascii"), hashlib.sha256).digest()
        )
        return f"{signing_input}.{signature}"

    def verify_access_token(self, token: str) -> TokenPayload:
        header, payload, signature, signing_input = self._decode_parts(token)
        if header.get("alg") != "HS256" or header.get("typ") != "JWT":
            raise InvalidTokenError("unsupported token header")

        expected_signature = _b64encode(
            hmac.new(self._secret_key, signing_input.encode("ascii"), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(signature, expected_signature):
            raise InvalidTokenError("invalid token signature")

        subject = payload.get("sub")
        issuer = payload.get("iss")
        expires_at = payload.get("exp")
        if not isinstance(subject, str) or not subject:
            raise InvalidTokenError("token subject is missing")
        if issuer != self._issuer:
            raise InvalidTokenError("token issuer is invalid")
        if not isinstance(expires_at, int):
            raise InvalidTokenError("token expiration is missing")
        if expires_at <= int(self._now().timestamp()):
            raise ExpiredTokenError("token has expired")

        return TokenPayload(subject=subject, issuer=issuer)

    def _decode_parts(self, token: str) -> tuple[dict[str, Any], dict[str, Any], str, str]:
        parts = token.split(".")
        if len(parts) != 3:
            raise InvalidTokenError("token must contain three parts")

        signing_input = f"{parts[0]}.{parts[1]}"
        try:
            header = json.loads(_b64decode(parts[0]))
            payload = json.loads(_b64decode(parts[1]))
        except (ValueError, json.JSONDecodeError) as exc:
            raise InvalidTokenError("token payload is invalid") from exc

        if not isinstance(header, dict) or not isinstance(payload, dict):
            raise InvalidTokenError("token payload must be a JSON object")
        return header, payload, parts[2], signing_input


def _json_b64(data: dict[str, Any]) -> str:
    return _b64encode(json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(data: str) -> str:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}").decode("utf-8")
