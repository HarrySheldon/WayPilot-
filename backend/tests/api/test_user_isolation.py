from __future__ import annotations

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.api import dependencies
from backend.app.core.security import PasswordHasher, TokenService
from backend.app.db.base import Base
from backend.app.db.session import get_db_session
from backend.app.main import create_app
from backend.app.repositories.sqlalchemy import SQLAlchemyTripRepository
from backend.app.repositories.users import SQLAlchemyUserRepository
from backend.app.services.auth import AuthService, RegisterUserInput
from backend.app.services.trips import TripCreateInput, TripService


class UserIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.token_service = TokenService(secret_key="test-secret")
        self._seed_user(email="owner@example.com", password="password123", user_id="user-owner")
        self._seed_user(email="other@example.com", password="password123", user_id="user-other")
        self._seed_trip(user_id="user-owner", trip_id="trip-1")

        self.app = create_app()
        self.app.dependency_overrides[dependencies.get_repository_backend] = lambda: "sqlalchemy"
        self.app.dependency_overrides[dependencies.get_token_service] = lambda: self.token_service
        self.app.dependency_overrides[get_db_session] = self._override_session
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_owner_can_read_trip_and_other_user_gets_not_found(self) -> None:
        owner_token = self.token_service.create_access_token(user_id="user-owner")
        other_token = self.token_service.create_access_token(user_id="user-other")

        owner_response = self.client.get(
            "/api/v1/trips/trip-1",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        other_response = self.client.get(
            "/api/v1/trips/trip-1",
            headers={"Authorization": f"Bearer {other_token}"},
        )

        self.assertEqual(owner_response.status_code, 200, owner_response.text)
        self.assertEqual(owner_response.json()["id"], "trip-1")
        self.assertEqual(other_response.status_code, 404, other_response.text)

    def _seed_user(self, *, email: str, password: str, user_id: str) -> None:
        session = self.SessionLocal()
        AuthService(
            user_repository=SQLAlchemyUserRepository(session),
            password_hasher=PasswordHasher(),
            token_service=self.token_service,
            id_generator=lambda: user_id,
        ).register_user(data=RegisterUserInput(email=email, password=password))
        session.commit()
        session.close()

    def _seed_trip(self, *, user_id: str, trip_id: str) -> None:
        session = self.SessionLocal()
        TripService(
            trip_repository=SQLAlchemyTripRepository(session),
            id_generator=lambda: trip_id,
        ).create_trip(user_id=user_id, data=TripCreateInput(title="Tokyo", destination="Tokyo"))
        session.commit()
        session.close()

    def _override_session(self):
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
