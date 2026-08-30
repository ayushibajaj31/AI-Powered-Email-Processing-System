"""JWT and login tests using mocked repositories; no real database is required."""

import os
import unittest
from dataclasses import dataclass

os.environ["JWT_SECRET_KEY"] = "test-only-secret-that-is-long-enough"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"

from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.dependencies import get_auth_repository
from src.auth.jwt_handler import create_access_token
from src.auth.security import hash_password


@dataclass
class MockCustomer:
    customer_id: str


@dataclass
class MockUser:
    id: int
    email: str
    password_hash: str
    role: str = "customer"
    is_active: bool = True
    customer: MockCustomer | None = None


class MockAuthRepository:
    def __init__(self):
        self.active = MockUser(1, "customer101@example.com", hash_password("TestPassword123!"), customer=MockCustomer("CUST0001"))
        self.inactive = MockUser(2, "inactive@example.com", hash_password("TestPassword123!"), is_active=False, customer=MockCustomer("CUST0002"))

    def get_user_by_email(self, email):
        return {self.active.email: self.active, self.inactive.email: self.inactive}.get(email.lower())

    def get_user_by_subject(self, subject):
        return self.active if subject == "CUST0001" else self.inactive if subject == "CUST0002" else None


class AuthenticationTestCase(unittest.TestCase):
    def setUp(self):
        self.repository = MockAuthRepository()
        app.dependency_overrides[get_auth_repository] = lambda: self.repository
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_successful_login(self):
        response = self.client.post("/api/v1/auth/login", json={"email": "customer101@example.com", "password": "TestPassword123!"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["token_type"], "bearer")

    def test_wrong_password_and_unknown_email(self):
        for email, password in [("customer101@example.com", "wrong"), ("unknown@example.com", "TestPassword123!")]:
            response = self.client.post("/api/v1/auth/login", json={"email": email, "password": password})
            self.assertEqual(response.status_code, 401)

    def test_inactive_user_cannot_login(self):
        response = self.client.post("/api/v1/auth/login", json={"email": "inactive@example.com", "password": "TestPassword123!"})
        self.assertEqual(response.status_code, 401)

    def test_missing_invalid_expired_and_tampered_tokens_are_rejected(self):
        cases = [
            {},
            {"Authorization": "Bearer invalid.token.value"},
            {"Authorization": f"Bearer {create_access_token('CUST0001', 'customer', expires_minutes=-1)}"},
            {"Authorization": f"Bearer {create_access_token('CUST0001', 'customer')}tampered"},
        ]
        for headers in cases:
            response = self.client.get("/api/v1/auth/me", headers=headers)
            self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
