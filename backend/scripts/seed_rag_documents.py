from __future__ import annotations

from sqlalchemy.orm import Session

try:
    from backend.app.db.session import SessionLocal
    from backend.app.rag.embeddings import DeterministicEmbeddingProvider
    from backend.app.rag.ingest import RagIngestor
    from backend.app.repositories.sqlalchemy import SQLAlchemyRagRepository
except ModuleNotFoundError:
    from app.db.session import SessionLocal
    from app.rag.embeddings import DeterministicEmbeddingProvider
    from app.rag.ingest import RagIngestor
    from app.repositories.sqlalchemy import SQLAlchemyRagRepository


SEED_DOCUMENTS = [
    {
        "owner_user_id": None,
        "source_type": "city_guide",
        "source_id": "tokyo-guide",
        "title": "Tokyo guide",
        "city": "Tokyo",
        "content": "Tokyo is strong for ramen, temples, museums, parks, and rail-based day trips.",
        "metadata": {"seed": True},
    },
    {
        "owner_user_id": None,
        "source_type": "restaurant_note",
        "source_id": "tokyo-ramen",
        "title": "Tokyo ramen notes",
        "city": "Tokyo",
        "content": "Tokyo Ramen Street is convenient for station-based dining and short itinerary gaps.",
        "metadata": {"seed": True},
    },
]


def seed_rag_documents(*, session: Session) -> int:
    ingestor = RagIngestor(
        repository=SQLAlchemyRagRepository(session),
        embedding_provider=DeterministicEmbeddingProvider(),
    )
    for document in SEED_DOCUMENTS:
        ingestor.ingest_document(**document)
    return len(SEED_DOCUMENTS)


def main() -> None:
    session = SessionLocal()
    try:
        count = seed_rag_documents(session=session)
        session.commit()
        print(f"seeded rag documents: {count}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
