"""
Tests for notebook endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.notebook import Notebook
from app.models.user import User


class TestListNotebooks:
    """Tests for listing notebooks."""

    def test_list_notebooks_empty(self, authenticated_client: TestClient):
        """Test listing notebooks when none exist."""
        response = authenticated_client.get("/api/v1/notebooks")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_notebooks_with_data(
        self, authenticated_client: TestClient, test_notebook: Notebook
    ):
        """Test listing notebooks with existing data."""
        response = authenticated_client.get("/api/v1/notebooks")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == test_notebook.title
        assert data["total"] == 1

    def test_list_notebooks_unauthenticated(self, client: TestClient):
        """Test that unauthenticated users cannot list notebooks."""
        response = client.get("/api/v1/notebooks")
        assert response.status_code == 401


class TestCreateNotebook:
    """Tests for creating notebooks."""

    def test_create_notebook_success(self, authenticated_client: TestClient):
        """Test successful notebook creation."""
        response = authenticated_client.post(
            "/api/v1/notebooks",
            json={
                "title": "Test Notebook",
                "description": "A test notebook",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Notebook"
        assert data["description"] == "A test notebook"
        assert "id" in data

    def test_create_notebook_minimal(self, authenticated_client: TestClient):
        """Test creating notebook with minimal data."""
        response = authenticated_client.post(
            "/api/v1/notebooks",
            json={"title": "Minimal Notebook"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Minimal Notebook"
        assert data["description"] is None or data["description"] == ""

    def test_create_notebook_empty_title(self, authenticated_client: TestClient):
        """Test that empty title is rejected."""
        response = authenticated_client.post(
            "/api/v1/notebooks",
            json={"title": ""},
        )
        assert response.status_code == 422

    def test_create_notebook_unauthenticated(self, client: TestClient):
        """Test that unauthenticated users cannot create notebooks."""
        response = client.post(
            "/api/v1/notebooks",
            json={"title": "Test Notebook"},
        )
        assert response.status_code == 401


class TestGetNotebook:
    """Tests for getting a single notebook."""

    def test_get_notebook_success(
        self, authenticated_client: TestClient, test_notebook: Notebook
    ):
        """Test getting an existing notebook."""
        response = authenticated_client.get(f"/api/v1/notebooks/{test_notebook.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_notebook.id)
        assert data["title"] == test_notebook.title

    def test_get_notebook_not_found(self, authenticated_client: TestClient):
        """Test getting a non-existent notebook."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_client.get(f"/api/v1/notebooks/{fake_id}")
        assert response.status_code == 404

    def test_get_notebook_invalid_id(self, authenticated_client: TestClient):
        """Test getting notebook with invalid ID format."""
        response = authenticated_client.get("/api/v1/notebooks/invalid-id")
        assert response.status_code == 422

    def test_get_other_user_notebook(
        self,
        authenticated_client: TestClient,
        other_user_notebook: Notebook,
    ):
        """Test that users cannot access other users' notebooks."""
        response = authenticated_client.get(
            f"/api/v1/notebooks/{other_user_notebook.id}"
        )
        assert response.status_code == 404


class TestUpdateNotebook:
    """Tests for updating notebooks."""

    def test_update_notebook_success(
        self, authenticated_client: TestClient, test_notebook: Notebook
    ):
        """Test successful notebook update."""
        response = authenticated_client.put(
            f"/api/v1/notebooks/{test_notebook.id}",
            json={
                "title": "Updated Title",
                "description": "Updated description",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["description"] == "Updated description"

    def test_update_notebook_partial(
        self, authenticated_client: TestClient, test_notebook: Notebook
    ):
        """Test partial notebook update."""
        response = authenticated_client.put(
            f"/api/v1/notebooks/{test_notebook.id}",
            json={"title": "Only Title Updated"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Only Title Updated"

    def test_update_notebook_not_found(self, authenticated_client: TestClient):
        """Test updating non-existent notebook."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_client.put(
            f"/api/v1/notebooks/{fake_id}",
            json={"title": "Updated"},
        )
        assert response.status_code == 404


class TestDeleteNotebook:
    """Tests for deleting notebooks."""

    def test_delete_notebook_success(
        self, authenticated_client: TestClient, test_notebook: Notebook
    ):
        """Test successful notebook deletion."""
        response = authenticated_client.delete(f"/api/v1/notebooks/{test_notebook.id}")
        assert response.status_code == 200

        # Verify it's deleted
        response = authenticated_client.get(f"/api/v1/notebooks/{test_notebook.id}")
        assert response.status_code == 404

    def test_delete_notebook_not_found(self, authenticated_client: TestClient):
        """Test deleting non-existent notebook."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_client.delete(f"/api/v1/notebooks/{fake_id}")
        assert response.status_code == 404

    def test_delete_other_user_notebook(
        self,
        authenticated_client: TestClient,
        other_user_notebook: Notebook,
    ):
        """Test that users cannot delete other users' notebooks."""
        response = authenticated_client.delete(
            f"/api/v1/notebooks/{other_user_notebook.id}"
        )
        assert response.status_code == 404
