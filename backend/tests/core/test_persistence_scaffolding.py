from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]


class PersistenceScaffoldingTests(unittest.TestCase):
    def test_orm_models_and_initial_migration_cover_core_tables(self) -> None:
        orm_models = ROOT / "backend" / "app" / "models" / "orm.py"
        migration = ROOT / "backend" / "alembic" / "versions" / "0001_initial_schema.py"
        requirements = ROOT / "backend" / "requirements.txt"

        self.assertTrue(orm_models.exists(), "SQLAlchemy ORM models are required")
        self.assertTrue(migration.exists(), "initial Alembic migration is required")
        self.assertIn("pgvector", requirements.read_text(encoding="utf-8"))

        model_text = orm_models.read_text(encoding="utf-8")
        migration_text = migration.read_text(encoding="utf-8")
        for table_name in [
            "users",
            "user_preferences",
            "trips",
            "trip_candidates",
            "trip_versions",
            "trip_days",
            "itinerary_items",
            "budget_items",
            "agent_runs",
            "agent_run_events",
            "tool_calls",
            "agent_traces",
            "rag_documents",
            "rag_chunks",
        ]:
            self.assertIn(table_name, model_text)
            self.assertIn(table_name, migration_text)
        self.assertIn("CREATE EXTENSION IF NOT EXISTS vector", migration_text)


if __name__ == "__main__":
    unittest.main()
