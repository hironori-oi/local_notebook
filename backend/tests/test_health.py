"""
Tests for health check endpoints.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


class TestHealthCheck:
    """Tests for basic health check endpoint."""

    def test_health_check_success(self, client: TestClient):
        """Test basic health check returns OK."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data


class TestLLMHealthCheck:
    """Tests for LLM health check endpoint."""

    def test_llm_health_check_healthy(self, client: TestClient):
        """Test LLM health check when service is healthy."""
        with patch("app.api.v1.health.get_llm_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.health_check.return_value = {
                "status": "healthy",
                "provider": "openai",
                "model": "gpt-4",
            }
            mock_get_client.return_value = mock_client

            response = client.get("/api/v1/health/llm")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    def test_llm_health_check_unhealthy(self, client: TestClient):
        """Test LLM health check when service is unhealthy."""
        with patch("app.api.v1.health.get_llm_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.health_check.return_value = {
                "status": "unhealthy",
                "error": "Connection refused",
            }
            mock_get_client.return_value = mock_client

            response = client.get("/api/v1/health/llm")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"


class TestEmbeddingHealthCheck:
    """Tests for embedding health check endpoint."""

    def test_embedding_health_check_healthy(self, client: TestClient):
        """Test embedding health check when service is healthy."""
        with patch("app.api.v1.health.get_embedding_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.health_check.return_value = {
                "status": "healthy",
                "model": "text-embedding-3-small",
                "dimension": 1536,
            }
            mock_get_client.return_value = mock_client

            response = client.get("/api/v1/health/embedding")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"


class TestFullHealthCheck:
    """Tests for comprehensive health check endpoint."""

    def test_full_health_check_all_healthy(self, client: TestClient):
        """Test full health check when all services are healthy."""
        with (
            patch("app.api.v1.health.get_llm_client") as mock_llm,
            patch("app.api.v1.health.get_embedding_client") as mock_embed,
        ):
            mock_llm_client = AsyncMock()
            mock_llm_client.health_check.return_value = {"status": "healthy"}
            mock_llm.return_value = mock_llm_client

            mock_embed_client = AsyncMock()
            mock_embed_client.health_check.return_value = {"status": "healthy"}
            mock_embed.return_value = mock_embed_client

            response = client.get("/api/v1/health/full")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "services" in data
            assert "config" in data

    def test_full_health_check_degraded(self, client: TestClient):
        """Test full health check when some services are unhealthy."""
        with (
            patch("app.api.v1.health.get_llm_client") as mock_llm,
            patch("app.api.v1.health.get_embedding_client") as mock_embed,
        ):
            mock_llm_client = AsyncMock()
            mock_llm_client.health_check.return_value = {"status": "unhealthy"}
            mock_llm.return_value = mock_llm_client

            mock_embed_client = AsyncMock()
            mock_embed_client.health_check.return_value = {"status": "healthy"}
            mock_embed.return_value = mock_embed_client

            response = client.get("/api/v1/health/full")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
