from __future__ import annotations

from ..domain.rag import RagHit
from ..repositories.memory import InMemoryRagRepository


class ControlledKnowledgeRetriever:
    def __init__(self, *, repository: InMemoryRagRepository) -> None:
        self._repository = repository

    def retrieve(self, *, user_id: str, query: str, city: str | None = None, limit: int = 5) -> list[RagHit]:
        terms = [term for term in query.lower().split() if term]
        hits: list[RagHit] = []
        for chunk in self._repository.list_chunks():
            document = self._repository.get_document(chunk.document_id)
            if document is None:
                continue
            if document.owner_user_id is not None and document.owner_user_id != user_id:
                continue
            if city is not None and document.city != city:
                continue

            searchable = f"{document.title} {document.content} {chunk.content}".lower()
            score = sum(searchable.count(term) for term in terms)
            if score <= 0:
                continue
            hits.append(
                RagHit(
                    document_id=document.id,
                    chunk_id=chunk.id,
                    source_type=document.source_type,
                    title=document.title,
                    city=document.city,
                    score=float(score),
                    snippet=chunk.content[:240],
                )
            )

        hits.sort(key=lambda hit: (-hit.score, hit.chunk_id))
        return hits[:limit]
