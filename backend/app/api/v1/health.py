"""
Health check endpoints for system status and LLM/Embedding connectivity.
"""
from fastapi import APIRouter

from app.core.config import settings
from app.services.llm_client import get_llm_client
from app.services.embedding import get_embedding_client

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """
    Basic health check endpoint.

    Returns:
        Simple status message indicating the API is running
    """
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
    }


@router.get("/llm")
async def llm_health_check():
    """
    Check LLM server connectivity.

    Returns:
        LLM connection status including provider, model, and any errors
    """
    client = get_llm_client()
    result = await client.health_check()
    return result


@router.get("/embedding")
async def embedding_health_check():
    """
    Check embedding server connectivity.

    Returns:
        Embedding connection status including model, dimension, and any errors
    """
    client = get_embedding_client()
    result = await client.health_check()
    return result


@router.get("/full")
async def full_health_check():
    """
    Comprehensive health check for all services.

    Returns:
        Status of API, LLM, and embedding services
    """
    llm_client = get_llm_client()
    embedding_client = get_embedding_client()

    llm_status = await llm_client.health_check()
    embedding_status = await embedding_client.health_check()

    all_healthy = (
        llm_status.get("status") == "healthy"
        and embedding_status.get("status") == "healthy"
    )

    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": {
            "api": {"status": "healthy"},
            "llm": llm_status,
            "embedding": embedding_status,
        },
        "config": {
            "llm_provider": settings.LLM_PROVIDER,
            "llm_model": settings.LLM_MODEL,
            "embedding_model": settings.EMBEDDING_MODEL,
            "embedding_dim": settings.EMBEDDING_DIM,
        },
    }
