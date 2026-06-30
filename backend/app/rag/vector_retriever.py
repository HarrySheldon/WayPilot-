from __future__ import annotations

import math
from typing import Protocol

from ..domain.rag import RagChunk, RagDocument, RagHit
from .embeddings import EmbeddingProvider


class RagVectorRepository(Protocol):
    def list_chunks(self) -> list[RagChunk]:
        ...

    def get_document(self, document_id: str) -> RagDocument | None:
        ...


class VectorRagRetriever:
    def __init__(self, *, repository: RagVectorRepository, embedding_provider: EmbeddingProvider) -> None:
        self._repository = repository
        self._embedding_provider = embedding_provider

    def retrieve(self, *, user_id: str, query: str, city: str | None = None, limit: int = 5) -> list[RagHit]:
        if limit <= 0:
            return []
        query_embedding = self._embedding_provider.embed(query)
        hits: list[RagHit] = []
        for chunk in self._repository.list_chunks():
            document = self._repository.get_document(chunk.document_id)
            if document is None:
                continue
            if document.owner_user_id is not None and document.owner_user_id != user_id:
                continue
            if city is not None and document.city != city:
                continue
            score = _cosine_similarity(query_embedding, chunk.embedding)
            if score <= 0:
                continue
            hits.append(
                RagHit(
                    document_id=document.id,
                    chunk_id=chunk.id,
                    source_type=document.source_type,
                    title=document.title,
                    city=document.city,
                    score=score,
                    snippet=chunk.content[:240],
                )
            )

        hits.sort(key=lambda hit: (-hit.score, hit.chunk_id))
        return hits[:limit]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(left_value * right_value for left_value, right_value in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
