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
from backend.app.repositories.users import SQLAlchemyUserRepository
from backend.app.services.auth import AuthService, RegisterUserInput


class AuthApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.token_service = TokenService(secret_key="test-secret")
        self._seed_user(email="demo@example.com", password="password123", user_id="user-1")

        self.app = create_app()
        self.app.dependency_overrides[dependencies.get_repository_backend] = lambda: "sqlalchemy"
        self.app.dependency_overrides[dependencies.get_token_service] = lambda: self.token_service
        self.app.dependency_overrides[get_db_session] = self._override_session
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_login_returns_bearer_token_and_users_me_returns_current_user(self) -> None:
        login = self.client.post(
            "/api/v1/auth/login",
            json={"email": "demo@example.com", "password": "password123"},
        )

        self.assertEqual(login.status_code, 200, login.text)
        body = login.json()
        self.assertEqual(body["token_type"], "bearer")
        self.assertEqual(self.token_service.verify_access_token(body["access_token"]).subject, "user-1")

        me = self.client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )

        self.assertEqual(me.status_code, 200, me.text)
        self.assertEqual(me.json()["id"], "user-1")
        self.assertEqual(me.json()["email"], "demo@example.com")

    def test_login_rejects_invalid_password(self) -> None:
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "demo@example.com", "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 401)

    def test_protected_endpoint_requires_bearer_token(self) -> None:
        response = self.client.get("/api/v1/trips")

        self.assertEqual(response.status_code, 401)

    def test_invalid_token_is_rejected(self) -> None:
        response = self.client.get(
            "/api/v1/trips",
            headers={"Authorization": "Bearer invalid-token"},
        )

        self.assertEqual(response.status_code, 401)

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
