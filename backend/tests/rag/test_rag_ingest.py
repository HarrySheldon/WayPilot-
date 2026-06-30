from __future__ import annotations

import unittest

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.models.orm import UserORM
from backend.app.rag.embeddings import DeterministicEmbeddingProvider
from backend.app.rag.ingest import RagIngestor
from backend.app.repositories.sqlalchemy import SQLAlchemyRagRepository


class RagIngestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self._enable_foreign_keys(self.engine)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def test_ingest_chunks_content_and_writes_1536_dimensional_embeddings(self) -> None:
        session = self.SessionLocal()
        self._seed_user(session, "user-1")
        repository = SQLAlchemyRagRepository(session)
        ingestor = RagIngestor(
            repository=repository,
            embedding_provider=DeterministicEmbeddingProvider(),
            max_chunk_chars=48,
        )

        document = ingestor.ingest_document(
            owner_user_id="user-1",
            source_type="city_guide",
            source_id="tokyo-food",
            title="Tokyo Food",
            city="Tokyo",
            content="Tokyo ramen temples.\n\nSecond paragraph parks.",
            metadata={"source": "seed"},
        )
        session.commit()
        session.expire_all()

        stored_document = repository.get_document(document.id)
        chunks = repository.list_chunks_by_document(document.id)

        self.assertEqual(stored_document.owner_user_id, "user-1")
        self.assertEqual(stored_document.source_id, "tokyo-food")
        self.assertEqual(stored_document.metadata["source"], "seed")
        self.assertEqual([chunk.content for chunk in chunks], ["Tokyo ramen temples.", "Second paragraph parks."])
        self.assertEqual(len(chunks[0].embedding), 1536)
        self.assertTrue(any(value != 0 for value in chunks[0].embedding))

    def test_reingesting_same_source_updates_document_and_chunks(self) -> None:
        session = self.SessionLocal()
        repository = SQLAlchemyRagRepository(session)
        ingestor = RagIngestor(
            repository=repository,
            embedding_provider=DeterministicEmbeddingProvider(),
            max_chunk_chars=80,
        )

        first = ingestor.ingest_document(
            owner_user_id=None,
            source_type="city_guide",
            source_id="tokyo",
            title="Tokyo Guide",
            city="Tokyo",
            content="Old ramen paragraph.",
        )
        second = ingestor.ingest_document(
            owner_user_id=None,
            source_type="city_guide",
            source_id="tokyo",
            title="Updated Tokyo Guide",
            city="Tokyo",
            content="Updated museum paragraph.",
        )
        session.commit()
        session.expire_all()

        stored_document = repository.get_document(first.id)
        chunks = repository.list_chunks_by_document(first.id)

        self.assertEqual(first.id, second.id)
        self.assertEqual(stored_document.title, "Updated Tokyo Guide")
        self.assertEqual(stored_document.content, "Updated museum paragraph.")
        self.assertEqual([chunk.content for chunk in chunks], ["Updated museum paragraph."])

    def test_embedding_provider_is_deterministic_and_1536_dimensional(self) -> None:
        provider = DeterministicEmbeddingProvider()

        first = provider.embed("Tokyo ramen")
        second = provider.embed("Tokyo ramen")
        different = provider.embed("Kyoto temples")

        self.assertEqual(len(first), 1536)
        self.assertEqual(first, second)
        self.assertNotEqual(first, different)

    def _seed_user(self, session: Session, user_id: str) -> None:
        session.add(UserORM(id=user_id, email=f"{user_id}@example.com", password_hash="not-used"))
        session.commit()

    def _enable_foreign_keys(self, engine) -> None:
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()


if __name__ == "__main__":
    unittest.main()
