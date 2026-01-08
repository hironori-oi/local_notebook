"""
Tests for source endpoints.
"""

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.notebook import Notebook
from app.models.source import Source


class TestListSources:
    """Tests for listing sources."""

    def test_list_sources_empty(
        self, authenticated_client: TestClient, test_notebook: Notebook
    ):
        """Test listing sources when none exist."""
        response = authenticated_client.get(
            f"/api/v1/notebooks/{test_notebook.id}/sources"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_sources_with_data(
        self,
        authenticated_client: TestClient,
        test_notebook: Notebook,
        test_source: Source,
    ):
        """Test listing sources with existing data."""
        response = authenticated_client.get(
            f"/api/v1/notebooks/{test_notebook.id}/sources"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["filename"] == test_source.filename
        assert data["total"] == 1

    def test_list_sources_unauthenticated(
        self, client: TestClient, test_notebook: Notebook
    ):
        """Test that unauthenticated users cannot list sources."""
        response = client.get(f"/api/v1/notebooks/{test_notebook.id}/sources")
        assert response.status_code == 401

    def test_list_sources_other_user_notebook(
        self, authenticated_client: TestClient, other_user_notebook: Notebook
    ):
        """Test that users cannot list sources from other users' notebooks."""
        response = authenticated_client.get(
            f"/api/v1/notebooks/{other_user_notebook.id}/sources"
        )
        assert response.status_code == 404


class TestUploadSource:
    """Tests for uploading sources."""

    def test_upload_text_file_success(
        self, authenticated_client: TestClient, test_notebook: Notebook
    ):
        """Test successful text file upload."""
        file_content = b"This is test content for the uploaded file."
        files = {"file": ("test_upload.txt", io.BytesIO(file_content), "text/plain")}
        response = authenticated_client.post(
            f"/api/v1/notebooks/{test_notebook.id}/sources",
            files=files,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "test_upload.txt"
        assert data["file_type"] == "txt"
        assert "id" in data

    def test_upload_empty_file(
        self, authenticated_client: TestClient, test_notebook: Notebook
    ):
        """Test that empty files are rejected."""
        files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
        response = authenticated_client.post(
            f"/api/v1/notebooks/{test_notebook.id}/sources",
            files=files,
        )
        assert response.status_code == 400

    def test_upload_unsupported_file_type(
        self, authenticated_client: TestClient, test_notebook: Notebook
    ):
        """Test that unsupported file types are rejected."""
        file_content = b"#!/bin/bash\necho 'hello'"
        files = {"file": ("script.sh", io.BytesIO(file_content), "application/x-sh")}
        response = authenticated_client.post(
            f"/api/v1/notebooks/{test_notebook.id}/sources",
            files=files,
        )
        assert response.status_code == 400

    def test_upload_to_other_user_notebook(
        self, authenticated_client: TestClient, other_user_notebook: Notebook
    ):
        """Test that users cannot upload to other users' notebooks."""
        file_content = b"Test content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        response = authenticated_client.post(
            f"/api/v1/notebooks/{other_user_notebook.id}/sources",
            files=files,
        )
        assert response.status_code == 404


class TestGetSource:
    """Tests for getting a single source."""

    def test_get_source_success(
        self,
        authenticated_client: TestClient,
        test_notebook: Notebook,
        test_source: Source,
    ):
        """Test getting an existing source."""
        response = authenticated_client.get(
            f"/api/v1/notebooks/{test_notebook.id}/sources/{test_source.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_source.id)
        assert data["filename"] == test_source.filename

    def test_get_source_not_found(
        self, authenticated_client: TestClient, test_notebook: Notebook
    ):
        """Test getting a non-existent source."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_client.get(
            f"/api/v1/notebooks/{test_notebook.id}/sources/{fake_id}"
        )
        assert response.status_code == 404


class TestDeleteSource:
    """Tests for deleting sources."""

    def test_delete_source_success(
        self,
        authenticated_client: TestClient,
        test_notebook: Notebook,
        test_source: Source,
    ):
        """Test successful source deletion."""
        response = authenticated_client.delete(
            f"/api/v1/notebooks/{test_notebook.id}/sources/{test_source.id}"
        )
        assert response.status_code == 200

        # Verify it's deleted
        response = authenticated_client.get(
            f"/api/v1/notebooks/{test_notebook.id}/sources/{test_source.id}"
        )
        assert response.status_code == 404

    def test_delete_source_not_found(
        self, authenticated_client: TestClient, test_notebook: Notebook
    ):
        """Test deleting non-existent source."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_client.delete(
            f"/api/v1/notebooks/{test_notebook.id}/sources/{fake_id}"
        )
        assert response.status_code == 404

    def test_delete_source_from_other_user_notebook(
        self,
        authenticated_client: TestClient,
        other_user_notebook: Notebook,
        db: Session,
    ):
        """Test that users cannot delete sources from other users' notebooks."""
        # Create a source in the other user's notebook
        from app.models.source import Source as SourceModel

        other_source = SourceModel(
            notebook_id=other_user_notebook.id,
            filename="other_user_file.txt",
            file_type="txt",
            file_size=50,
            content="Other user's content",
        )
        db.add(other_source)
        db.commit()
        db.refresh(other_source)

        response = authenticated_client.delete(
            f"/api/v1/notebooks/{other_user_notebook.id}/sources/{other_source.id}"
        )
        assert response.status_code == 404
