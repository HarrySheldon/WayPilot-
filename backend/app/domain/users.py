from __future__ import annotations

from dataclasses import dataclass


@dataclass
class User:
    id: str
    email: str
    password_hash: str
    display_name: str | None = None
