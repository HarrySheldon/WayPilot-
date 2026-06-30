from __future__ import annotations

import unittest

from backend.app.core.security import PasswordHasher, TokenService
from backend.app.domain.users import User
from backend.app.services.auth import (
    AuthConflictError,
    AuthInvalidCredentialsError,
    AuthService,
    LoginInput,
    RegisterUserInput,
)


class FakeUserRepository:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}

    def save(self, user: User) -> User:
        self.users[user.id] = user
        return user

    def get(self, user_id: str) -> User | None:
        return self.users.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        return next((user for user in self.users.values() if user.email == email), None)


class AuthServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.users = FakeUserRepository()
        self.hasher = PasswordHasher()
        self.token_service = TokenService(secret_key="test-secret")
        self.service = AuthService(
            user_repository=self.users,
            password_hasher=self.hasher,
            token_service=self.token_service,
            id_generator=lambda: "user-1",
        )

    def test_register_user_hashes_password_and_rejects_duplicate_email(self) -> None:
        user = self.service.register_user(
            data=RegisterUserInput(
                email=" Demo@Example.COM ",
                password="password123",
                display_name="Demo User",
            )
        )

        self.assertEqual(user.id, "user-1")
        self.assertEqual(user.email, "demo@example.com")
        self.assertEqual(user.display_name, "Demo User")
        self.assertNotEqual(user.password_hash, "password123")
        self.assertTrue(self.hasher.verify("password123", user.password_hash))

        with self.assertRaisesRegex(AuthConflictError, "email already registered"):
            self.service.register_user(
                data=RegisterUserInput(email="demo@example.com", password="password123")
            )

    def test_authenticate_user_returns_token_for_valid_password(self) -> None:
        self.service.register_user(
            data=RegisterUserInput(email="demo@example.com", password="password123")
        )

        result = self.service.authenticate_user(
            data=LoginInput(email="DEMO@example.com", password="password123")
        )

        self.assertEqual(result.token_type, "bearer")
        self.assertEqual(result.user.id, "user-1")
        self.assertEqual(self.token_service.verify_access_token(result.access_token).subject, "user-1")

    def test_authenticate_user_rejects_invalid_password(self) -> None:
        self.service.register_user(
            data=RegisterUserInput(email="demo@example.com", password="password123")
        )

        with self.assertRaisesRegex(AuthInvalidCredentialsError, "invalid email or password"):
            self.service.authenticate_user(
                data=LoginInput(email="demo@example.com", password="wrong-password")
            )

    def test_authenticate_user_rejects_unknown_email(self) -> None:
        with self.assertRaisesRegex(AuthInvalidCredentialsError, "invalid email or password"):
            self.service.authenticate_user(
                data=LoginInput(email="missing@example.com", password="password123")
            )


if __name__ == "__main__":
    unittest.main()
