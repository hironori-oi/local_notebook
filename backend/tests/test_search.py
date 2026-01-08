"""
Tests for search endpoints.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.notebook import Notebook
from app.models.user import User


class TestGlobalSearch:
    """Tests for global search endpoint."""

    def test_search_unauthenticated(self, client: TestClient):
        """Test that unauthenticated users cannot search."""
        response = client.get("/api/v1/search/global?q=test")
        assert response.status_code == 401

    def test_search_empty_query(self, authenticated_client: TestClient):
        """Test search with empty query is rejected."""
        response = authenticated_client.get("/api/v1/search/global?q=")
        assert response.status_code == 422

    def test_search_query_too_long(self, authenticated_client: TestClient):
        """Test search with query exceeding max length."""
        long_query = "a" * 201
        response = authenticated_client.get(f"/api/v1/search/global?q={long_query}")
        assert response.status_code == 422

    def test_search_success(
        self, authenticated_client: TestClient, test_notebook: Notebook
    ):
        """Test successful search."""
        # Mock the search service
        with patch("app.api.v1.search.SearchService") as MockSearchService:
            mock_instance = MagicMock()
            mock_result = MagicMock()
            mock_result.type = "notebook"
            mock_result.id = str(test_notebook.id)
            mock_result.title = test_notebook.title
            mock_result.snippet = "Test snippet"
            mock_result.notebook_id = str(test_notebook.id)
            mock_result.notebook_title = test_notebook.title
            mock_result.relevance_score = 0.95
            mock_result.created_at = datetime.now()

            # Mock async method
            async def mock_search_all(*args, **kwargs):
                return ([mock_result], 1, 10.5)

            mock_instance.search_all = mock_search_all
            MockSearchService.return_value = mock_instance

            response = authenticated_client.get("/api/v1/search/global?q=test")
            assert response.status_code == 200
            data = response.json()
            assert "query" in data
            assert "results" in data
            assert "total" in data
            assert "search_time_ms" in data

    def test_search_with_type_filter(self, authenticated_client: TestClient):
        """Test search with type filter."""
        with patch("app.api.v1.search.SearchService") as MockSearchService:
            mock_instance = MagicMock()

            async def mock_search_all(*args, **kwargs):
                return ([], 0, 5.0)

            mock_instance.search_all = mock_search_all
            MockSearchService.return_value = mock_instance

            response = authenticated_client.get(
                "/api/v1/search/global?q=test&types=notebook,source"
            )
            assert response.status_code == 200

    def test_search_pagination(self, authenticated_client: TestClient):
        """Test search with pagination parameters."""
        with patch("app.api.v1.search.SearchService") as MockSearchService:
            mock_instance = MagicMock()

            async def mock_search_all(*args, **kwargs):
                return ([], 0, 5.0)

            mock_instance.search_all = mock_search_all
            MockSearchService.return_value = mock_instance

            response = authenticated_client.get(
                "/api/v1/search/global?q=test&limit=10&offset=5"
            )
            assert response.status_code == 200


class TestRecentItems:
    """Tests for recent items endpoint."""

    def test_recent_items_unauthenticated(self, client: TestClient):
        """Test that unauthenticated users cannot get recent items."""
        response = client.get("/api/v1/search/recent")
        assert response.status_code == 401

    def test_recent_items_success(self, authenticated_client: TestClient):
        """Test getting recent items."""
        with patch("app.api.v1.search.SearchService") as MockSearchService:
            mock_instance = MagicMock()
            mock_instance.get_recent_items.return_value = []
            MockSearchService.return_value = mock_instance

            response = authenticated_client.get("/api/v1/search/recent")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_recent_items_with_limit(self, authenticated_client: TestClient):
        """Test recent items with custom limit."""
        with patch("app.api.v1.search.SearchService") as MockSearchService:
            mock_instance = MagicMock()
            mock_instance.get_recent_items.return_value = []
            MockSearchService.return_value = mock_instance

            response = authenticated_client.get("/api/v1/search/recent?limit=5")
            assert response.status_code == 200
