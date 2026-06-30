from __future__ import annotations

import hashlib
import re
from typing import Protocol

from ..domain.rag import RagChunk, RagDocument
from .embeddings import EmbeddingProvider


class RagIngestRepository(Protocol):
    def save_document(self, document: RagDocument) -> RagDocument:
        ...

    def save_chunk(self, chunk: RagChunk) -> RagChunk:
        ...

    def find_document_by_source(
        self,
        *,
        owner_user_id: str | None,
        source_type: str,
        source_id: str | None,
    ) -> RagDocument | None:
        ...

    def delete_chunks_by_document(self, document_id: str) -> None:
        ...


class RagIngestor:
    def __init__(
        self,
        *,
        repository: RagIngestRepository,
        embedding_provider: EmbeddingProvider,
        max_chunk_chars: int = 800,
    ) -> None:
        self._repository = repository
        self._embedding_provider = embedding_provider
        self._max_chunk_chars = max_chunk_chars

    def ingest_document(
        self,
        *,
        owner_user_id: str | None,
        source_type: str,
        source_id: str | None,
        title: str,
        city: str | None,
        content: str,
        locale: str = "en",
        metadata: dict | None = None,
    ) -> RagDocument:
        existing = self._repository.find_document_by_source(
            owner_user_id=owner_user_id,
            source_type=source_type,
            source_id=source_id,
        )
        document_id = existing.id if existing is not None else _document_id(
            owner_user_id=owner_user_id,
            source_type=source_type,
            source_id=source_id,
            title=title,
        )
        document = RagDocument(
            id=document_id,
            owner_user_id=owner_user_id,
            source_type=source_type,
            source_id=source_id,
            title=title.strip(),
            city=city.strip() if city else None,
            locale=locale,
            content=content.strip(),
            metadata=dict(metadata or {}),
        )
        saved = self._repository.save_document(document)
        self._repository.delete_chunks_by_document(saved.id)
        for index, chunk_content in enumerate(chunk_text(saved.content, max_chars=self._max_chunk_chars)):
            self._repository.save_chunk(
                RagChunk(
                    id=f"{saved.id}-c{index}",
                    document_id=saved.id,
                    chunk_index=index,
                    content=chunk_content,
                    embedding=self._embedding_provider.embed(chunk_content),
                )
            )
        return saved


def chunk_text(content: str, *, max_chars: int = 800) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", content.strip()) if part.strip()]
    chunks: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
            continue
        chunks.extend(_split_long_paragraph(paragraph, max_chars=max_chars))
    return chunks


def _split_long_paragraph(paragraph: str, *, max_chars: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0
    for word in paragraph.split():
        separator = 1 if current else 0
        if current and current_length + separator + len(word) > max_chars:
            chunks.append(" ".join(current))
            current = [word]
            current_length = len(word)
            continue
        current.append(word)
        current_length += separator + len(word)
    if current:
        chunks.append(" ".join(current))
    return chunks


def _document_id(*, owner_user_id: str | None, source_type: str, source_id: str | None, title: str) -> str:
    owner_key = owner_user_id or "public"
    source_key = source_id or title
    digest = hashlib.sha256(f"{owner_key}:{source_type}:{source_key}".encode("utf-8")).hexdigest()
    return f"ragdoc-{digest[:24]}"
