from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RagDocument:
    id: str
    owner_user_id: str | None
    source_type: str
    title: str
    city: str | None
    content: str
    source_id: str | None = None
    locale: str = "en"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RagChunk:
    id: str
    document_id: str
    chunk_index: int
    content: str
    embedding: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RagHit:
    document_id: str
    chunk_id: str
    source_type: str
    title: str
    city: str | None
    score: float
    snippet: str
