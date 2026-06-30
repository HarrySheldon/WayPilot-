from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]:
        ...


class DeterministicEmbeddingProvider:
    def __init__(self, *, dimensions: int = 1536) -> None:
        self._dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        tokens = _tokens(text)
        if not tokens:
            return vector

        for token in tokens:
            index = _stable_index(token, self._dimensions)
            vector[index] += 1.0

        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return vector
        return [value / magnitude for value in vector]


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _stable_index(value: str, dimensions: int) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % dimensions
