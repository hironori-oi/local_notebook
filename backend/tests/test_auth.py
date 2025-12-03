"""
Tests for authentication endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.auth import get_password_hash


class TestRegister:
    """Tests for user registration endpoint."""

    def test_register_success(self, client: TestClient):
        """Test successful user registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "password": "SecurePass123!",
                "display_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "user" in data
        assert "token" in data
        assert data["user"]["username"] == "newuser"
        assert data["user"]["display_name"] == "New User"
        assert data["token"]["token_type"] == "bearer"

    def test_register_weak_password(self, client: TestClient):
        """Test registration with weak password."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "password": "weakpass",  # No uppercase, no special char, no digit
                "display_name": "New User",
            },
        )
        assert response.status_code == 422

    def test_register_short_password(self, client: TestClient):
        """Test registration with too short password."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "password": "Ab1!",  # Too short
                "display_name": "New User",
            },
        )
        assert response.status_code == 422

    def test_register_no_uppercase(self, client: TestClient):
        """Test registration with password missing uppercase."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "password": "password123!",  # No uppercase
                "display_name": "New User",
            },
        )
        assert response.status_code == 422

    def test_register_duplicate_username(self, client: TestClient, test_user: User):
        """Test registration with existing username."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": test_user.username,
                "password": "SecurePass123!",
                "display_name": "Another User",
            },
        )
        assert response.status_code == 400
        assert "既に使用されています" in response.json()["detail"]

    def test_register_invalid_username(self, client: TestClient):
        """Test registration with invalid username characters."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "user@name",  # Invalid character
                "password": "SecurePass123!",
                "display_name": "New User",
            },
        )
        assert response.status_code == 422


class TestLogin:
    """Tests for user login endpoint."""

    def test_login_success(self, client: TestClient, test_user: User):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": "TestPassword123!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "token" in data
        assert data["user"]["username"] == test_user.username

    def test_login_wrong_password(self, client: TestClient, test_user: User):
        """Test login with wrong password."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401
        assert "正しくありません" in response.json()["detail"]

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent username."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "Password123!",
            },
        )
        assert response.status_code == 401


class TestLogout:
    """Tests for logout endpoint."""

    def test_logout_success(self, authenticated_client: TestClient):
        """Test successful logout."""
        response = authenticated_client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        assert "ログアウト" in response.json()["message"]

    def test_logout_unauthenticated(self, client: TestClient):
        """Test logout without authentication."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 401
