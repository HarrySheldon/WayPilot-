from __future__ import annotations

import unittest

from backend.app.domain.rag import RagChunk, RagDocument
from backend.app.rag.embeddings import DeterministicEmbeddingProvider
from backend.app.rag.vector_retriever import VectorRagRetriever
from backend.app.repositories.memory import InMemoryRagRepository


class VectorRetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryRagRepository()
        self.embedding_provider = DeterministicEmbeddingProvider()
        self._add_document(
            document=RagDocument(
                id="doc-public-tokyo",
                owner_user_id=None,
                source_type="city_guide",
                title="Tokyo food guide",
                city="Tokyo",
                content="Tokyo ramen and markets",
            ),
            chunk_id="chunk-public-tokyo",
            chunk_content="Tokyo ramen and markets",
        )
        self._add_document(
            document=RagDocument(
                id="doc-user-1",
                owner_user_id="user-1",
                source_type="user_preference",
                title="User 1 dining notes",
                city="Tokyo",
                content="ramen breakfast preference",
            ),
            chunk_id="chunk-user-1",
            chunk_content="ramen breakfast preference",
        )
        self._add_document(
            document=RagDocument(
                id="doc-user-2",
                owner_user_id="user-2",
                source_type="user_preference",
                title="User 2 private notes",
                city="Tokyo",
                content="ramen private notes",
            ),
            chunk_id="chunk-user-2",
            chunk_content="ramen private notes",
        )
        self._add_document(
            document=RagDocument(
                id="doc-public-paris",
                owner_user_id=None,
                source_type="city_guide",
                title="Paris food guide",
                city="Paris",
                content="Paris ramen listing",
            ),
            chunk_id="chunk-public-paris",
            chunk_content="Paris ramen listing",
        )

    def test_retriever_returns_public_and_current_user_hits_only(self) -> None:
        hits = self._retriever().retrieve(user_id="user-1", query="ramen", city="Tokyo", limit=10)

        self.assertEqual({hit.chunk_id for hit in hits}, {"chunk-public-tokyo", "chunk-user-1"})
        self.assertNotIn("chunk-user-2", {hit.chunk_id for hit in hits})

    def test_retriever_respects_city_filter_and_top_k(self) -> None:
        tokyo_hits = self._retriever().retrieve(user_id="user-1", query="ramen", city="Tokyo", limit=1)
        paris_hits = self._retriever().retrieve(user_id="user-1", query="ramen", city="Paris", limit=10)

        self.assertEqual(len(tokyo_hits), 1)
        self.assertEqual({hit.city for hit in paris_hits}, {"Paris"})
        self.assertEqual({hit.chunk_id for hit in paris_hits}, {"chunk-public-paris"})

    def test_retriever_returns_rag_hit_shape(self) -> None:
        hit = self._retriever().retrieve(user_id="user-1", query="ramen", city="Tokyo", limit=1)[0]

        self.assertTrue(hit.document_id)
        self.assertTrue(hit.chunk_id)
        self.assertIn(hit.source_type, {"city_guide", "user_preference"})
        self.assertTrue(hit.title)
        self.assertEqual(hit.city, "Tokyo")
        self.assertGreater(hit.score, 0)
        self.assertTrue(hit.snippet)

    def _retriever(self) -> VectorRagRetriever:
        return VectorRagRetriever(repository=self.repository, embedding_provider=self.embedding_provider)

    def _add_document(self, *, document: RagDocument, chunk_id: str, chunk_content: str) -> None:
        self.repository.save_document(document)
        self.repository.save_chunk(
            RagChunk(
                id=chunk_id,
                document_id=document.id,
                chunk_index=0,
                content=chunk_content,
                embedding=self.embedding_provider.embed(chunk_content),
            )
        )


if __name__ == "__main__":
    unittest.main()
