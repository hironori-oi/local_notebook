"""
Tests for notes endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.note import Note
from app.models.notebook import Notebook
from app.models.message import Message


class TestListNotes:
    """Tests for listing notes."""

    def test_list_notes_empty(
        self, authenticated_client: TestClient, test_notebook: Notebook
    ):
        """Test listing notes when none exist."""
        response = authenticated_client.get(
            f"/api/v1/notes/notebook/{test_notebook.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_notes_with_data(
        self,
        authenticated_client: TestClient,
        test_notebook: Notebook,
        test_note: Note,
    ):
        """Test listing notes with existing data."""
        response = authenticated_client.get(
            f"/api/v1/notes/notebook/{test_notebook.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == test_note.title
        assert data["total"] == 1

    def test_list_notes_unauthenticated(
        self, client: TestClient, test_notebook: Notebook
    ):
        """Test that unauthenticated users cannot list notes."""
        response = client.get(f"/api/v1/notes/notebook/{test_notebook.id}")
        assert response.status_code == 401

    def test_list_notes_invalid_notebook_id(self, authenticated_client: TestClient):
        """Test listing notes with invalid notebook ID."""
        response = authenticated_client.get("/api/v1/notes/notebook/invalid-id")
        assert response.status_code == 400

    def test_list_notes_pagination(
        self,
        authenticated_client: TestClient,
        test_notebook: Notebook,
        test_note: Note,
    ):
        """Test notes list pagination parameters."""
        response = authenticated_client.get(
            f"/api/v1/notes/notebook/{test_notebook.id}?offset=0&limit=10"
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data


class TestCreateNote:
    """Tests for creating notes."""

    def test_create_note_success(
        self,
        authenticated_client: TestClient,
        test_notebook: Notebook,
        test_assistant_message: Message,
        db: Session,
    ):
        """Test successful note creation."""
        # First delete any existing note for this message
        db.query(Note).filter(Note.message_id == test_assistant_message.id).delete()
        db.commit()

        response = authenticated_client.post(
            f"/api/v1/notes/{test_notebook.id}",
            json={
                "message_id": str(test_assistant_message.id),
                "title": "New Note",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Note"
        assert "id" in data

    def test_create_note_duplicate_message(
        self,
        authenticated_client: TestClient,
        test_notebook: Notebook,
        test_note: Note,
        test_assistant_message: Message,
    ):
        """Test that duplicate note for same message is rejected."""
        response = authenticated_client.post(
            f"/api/v1/notes/{test_notebook.id}",
            json={
                "message_id": str(test_assistant_message.id),
                "title": "Duplicate Note",
            },
        )
        assert response.status_code == 400

    def test_create_note_invalid_message(
        self, authenticated_client: TestClient, test_notebook: Notebook
    ):
        """Test creating note with non-existent message."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_client.post(
            f"/api/v1/notes/{test_notebook.id}",
            json={
                "message_id": fake_id,
                "title": "Test Note",
            },
        )
        assert response.status_code == 404

    def test_create_note_unauthenticated(
        self, client: TestClient, test_notebook: Notebook
    ):
        """Test that unauthenticated users cannot create notes."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(
            f"/api/v1/notes/{test_notebook.id}",
            json={
                "message_id": fake_id,
                "title": "Test Note",
            },
        )
        assert response.status_code == 401


class TestGetNote:
    """Tests for getting a single note."""

    def test_get_note_success(
        self, authenticated_client: TestClient, test_note: Note
    ):
        """Test getting an existing note."""
        response = authenticated_client.get(f"/api/v1/notes/{test_note.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_note.id)
        assert data["title"] == test_note.title

    def test_get_note_not_found(self, authenticated_client: TestClient):
        """Test getting a non-existent note."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_client.get(f"/api/v1/notes/{fake_id}")
        assert response.status_code == 404

    def test_get_note_invalid_id(self, authenticated_client: TestClient):
        """Test getting note with invalid ID format."""
        response = authenticated_client.get("/api/v1/notes/invalid-id")
        assert response.status_code == 400


class TestUpdateNote:
    """Tests for updating notes."""

    def test_update_note_title(
        self, authenticated_client: TestClient, test_note: Note
    ):
        """Test updating note title."""
        response = authenticated_client.patch(
            f"/api/v1/notes/{test_note.id}",
            json={"title": "Updated Title"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    def test_update_note_content(
        self, authenticated_client: TestClient, test_note: Note
    ):
        """Test updating note content."""
        response = authenticated_client.patch(
            f"/api/v1/notes/{test_note.id}",
            json={"content": "Updated content here"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Updated content here"

    def test_update_note_not_found(self, authenticated_client: TestClient):
        """Test updating non-existent note."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_client.patch(
            f"/api/v1/notes/{fake_id}",
            json={"title": "Updated"},
        )
        assert response.status_code == 404


class TestDeleteNote:
    """Tests for deleting notes."""

    def test_delete_note_success(
        self, authenticated_client: TestClient, test_note: Note
    ):
        """Test successful note deletion."""
        response = authenticated_client.delete(f"/api/v1/notes/{test_note.id}")
        assert response.status_code == 204

        # Verify it's deleted
        response = authenticated_client.get(f"/api/v1/notes/{test_note.id}")
        assert response.status_code == 404

    def test_delete_note_not_found(self, authenticated_client: TestClient):
        """Test deleting non-existent note."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_client.delete(f"/api/v1/notes/{fake_id}")
        assert response.status_code == 404

    def test_delete_note_invalid_id(self, authenticated_client: TestClient):
        """Test deleting note with invalid ID format."""
        response = authenticated_client.delete("/api/v1/notes/invalid-id")
        assert response.status_code == 400
