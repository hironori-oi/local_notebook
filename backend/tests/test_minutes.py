"""
Tests for minutes endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, AsyncMock

from app.models.notebook import Notebook
from app.models.user import User


@pytest.fixture
def test_minute(db: Session, test_notebook, test_user):
    """Create a test minute."""
    from app.models.minute import Minute

    minute = Minute(
        notebook_id=test_notebook.id,
        created_by=test_user.id,
        title="Test Minute",
        content="This is the content of the test minute.",
        processing_status="completed",
    )
    db.add(minute)
    db.commit()
    db.refresh(minute)
    return minute


class TestListMinutes:
    """Tests for listing minutes."""

    def test_list_minutes_empty(
        self, authenticated_client: TestClient, test_notebook: Notebook
    ):
        """Test listing minutes when none exist."""
        response = authenticated_client.get(
            f"/api/v1/minutes/notebook/{test_notebook.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_minutes_with_data(
        self,
        authenticated_client: TestClient,
        test_notebook: Notebook,
        test_minute,
    ):
        """Test listing minutes with existing data."""
        response = authenticated_client.get(
            f"/api/v1/minutes/notebook/{test_notebook.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == test_minute.title

    def test_list_minutes_unauthenticated(
        self, client: TestClient, test_notebook: Notebook
    ):
        """Test that unauthenticated users cannot list minutes."""
        response = client.get(f"/api/v1/minutes/notebook/{test_notebook.id}")
        assert response.status_code == 401

    def test_list_minutes_invalid_notebook_id(self, authenticated_client: TestClient):
        """Test listing minutes with invalid notebook ID."""
        response = authenticated_client.get("/api/v1/minutes/notebook/invalid-id")
        assert response.status_code == 400


class TestCreateMinute:
    """Tests for creating minutes."""

    def test_create_minute_success(
        self,
        authenticated_client: TestClient,
        test_notebook: Notebook,
    ):
        """Test successful minute creation."""
        # Mock the embedding function
        with patch("app.api.v1.minutes.embed_texts", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [[0.1] * 384]  # Return mock embedding

            response = authenticated_client.post(
                f"/api/v1/minutes/notebook/{test_notebook.id}",
                json={
                    "title": "New Minute",
                    "content": "This is the content.",
                    "document_ids": [],
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["title"] == "New Minute"
            assert "id" in data

    def test_create_minute_unauthenticated(
        self, client: TestClient, test_notebook: Notebook
    ):
        """Test that unauthenticated users cannot create minutes."""
        response = client.post(
            f"/api/v1/minutes/notebook/{test_notebook.id}",
            json={
                "title": "Test Minute",
                "content": "Content here",
                "document_ids": [],
            },
        )
        assert response.status_code == 401

    def test_create_minute_invalid_document_id(
        self,
        authenticated_client: TestClient,
        test_notebook: Notebook,
    ):
        """Test creating minute with invalid document ID."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_client.post(
            f"/api/v1/minutes/notebook/{test_notebook.id}",
            json={
                "title": "Test Minute",
                "content": "Content here",
                "document_ids": [fake_id],
            },
        )
        assert response.status_code == 400


class TestGetMinute:
    """Tests for getting a single minute."""

    def test_get_minute_success(
        self, authenticated_client: TestClient, test_minute
    ):
        """Test getting an existing minute."""
        response = authenticated_client.get(f"/api/v1/minutes/{test_minute.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_minute.id)
        assert data["title"] == test_minute.title

    def test_get_minute_not_found(self, authenticated_client: TestClient):
        """Test getting a non-existent minute."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_client.get(f"/api/v1/minutes/{fake_id}")
        assert response.status_code == 404

    def test_get_minute_invalid_id(self, authenticated_client: TestClient):
        """Test getting minute with invalid ID format."""
        response = authenticated_client.get("/api/v1/minutes/invalid-id")
        assert response.status_code == 400


class TestUpdateMinute:
    """Tests for updating minutes."""

    def test_update_minute_title(
        self, authenticated_client: TestClient, test_minute
    ):
        """Test updating minute title."""
        response = authenticated_client.patch(
            f"/api/v1/minutes/{test_minute.id}",
            json={"title": "Updated Title"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    def test_update_minute_content(
        self, authenticated_client: TestClient, test_minute
    ):
        """Test updating minute content."""
        with patch("app.api.v1.minutes.embed_texts", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [[0.1] * 384]

            response = authenticated_client.patch(
                f"/api/v1/minutes/{test_minute.id}",
                json={"content": "Updated content here"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "id" in data

    def test_update_minute_not_found(self, authenticated_client: TestClient):
        """Test updating non-existent minute."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_client.patch(
            f"/api/v1/minutes/{fake_id}",
            json={"title": "Updated"},
        )
        assert response.status_code == 404


class TestDeleteMinute:
    """Tests for deleting minutes."""

    def test_delete_minute_success(
        self, authenticated_client: TestClient, test_minute
    ):
        """Test successful minute deletion."""
        response = authenticated_client.delete(f"/api/v1/minutes/{test_minute.id}")
        assert response.status_code == 204

        # Verify it's deleted
        response = authenticated_client.get(f"/api/v1/minutes/{test_minute.id}")
        assert response.status_code == 404

    def test_delete_minute_not_found(self, authenticated_client: TestClient):
        """Test deleting non-existent minute."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_client.delete(f"/api/v1/minutes/{fake_id}")
        assert response.status_code == 404


class TestGetMinuteDetail:
    """Tests for getting minute detail."""

    def test_get_minute_detail_success(
        self, authenticated_client: TestClient, test_minute
    ):
        """Test getting minute detail."""
        response = authenticated_client.get(f"/api/v1/minutes/{test_minute.id}/detail")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_minute.id)
        assert "content" in data
        assert "processing_status" in data


class TestUpdateMinuteSummary:
    """Tests for updating minute summary."""

    def test_update_minute_summary(
        self, authenticated_client: TestClient, test_minute
    ):
        """Test updating minute summary."""
        response = authenticated_client.patch(
            f"/api/v1/minutes/{test_minute.id}/summary",
            json={
                "summary": "This is a summary",
                "formatted_content": "# Formatted\n\nContent here",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "This is a summary"
        assert data["formatted_content"] == "# Formatted\n\nContent here"
