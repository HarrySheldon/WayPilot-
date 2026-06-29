from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]


class ProjectScaffoldingTests(unittest.TestCase):
    def test_alembic_and_sqlalchemy_scaffolding_are_present(self) -> None:
        alembic_ini = ROOT / "backend" / "alembic.ini"
        env_py = ROOT / "backend" / "alembic" / "env.py"
        db_base = ROOT / "backend" / "app" / "db" / "base.py"
        db_session = ROOT / "backend" / "app" / "db" / "session.py"

        self.assertTrue(alembic_ini.exists(), "backend/alembic.ini is required")
        self.assertTrue(env_py.exists(), "backend/alembic/env.py is required")
        self.assertTrue(db_base.exists(), "backend/app/db/base.py is required")
        self.assertTrue(db_session.exists(), "backend/app/db/session.py is required")
        self.assertIn("Base.metadata", env_py.read_text(encoding="utf-8"))
        self.assertIn("settings.database_url", env_py.read_text(encoding="utf-8"))
        self.assertIn("DeclarativeBase", db_base.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
