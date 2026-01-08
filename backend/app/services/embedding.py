"""
Embedding Client - Abstraction layer for embedding providers (Ollama, vLLM, etc.)

Supports Ollama native API (/api/embeddings) and OpenAI-compatible API (/v1/embeddings).
Embedding dimension is configured via EMBEDDING_DIM environment variable.
- embeddinggemma:300m outputs 768 dimensions
- PLaMo-Embedding-1B outputs 2048 dimensions
"""
import asyncio
from typing import List, Dict, Optional
import httpx

from app.core.config import settings

# Maximum concurrent embedding requests for Ollama (prevents server overload)
EMBEDDING_CONCURRENCY_LIMIT = 5


class EmbeddingClient:
    """
    Unified embedding client supporting multiple providers.

    Supported providers:
    - ollama: Local Ollama server using native API (/api/embeddings)
    - vllm: vLLM server using OpenAI-compatible API (/v1/embeddings)

    Embedding dimension is configured via EMBEDDING_DIM environment variable.
    """

    def __init__(
        self,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.api_base = api_base or settings.EMBEDDING_API_BASE
        self.model = model or settings.EMBEDDING_MODEL
        self.provider = provider or settings.LLM_PROVIDER  # Use same provider as LLM
        self.timeout = timeout

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        For Ollama: Uses parallel processing with semaphore-limited concurrency
        For vLLM/OpenAI: Uses batch API which handles multiple texts natively

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (each is a list of floats)
        """
        if not texts:
            return []

        if self.provider == "ollama":
            # Ollama native API - parallel processing with concurrency limit
            semaphore = asyncio.Semaphore(EMBEDDING_CONCURRENCY_LIMIT)

            async def embed_single(text: str, index: int) -> tuple[int, List[float]]:
                """Embed a single text with semaphore-limited concurrency."""
                async with semaphore:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        resp = await client.post(
                            f"{self.api_base}/api/embeddings",
                            json={
                                "model": self.model,
                                "prompt": text,
                            },
                        )
                        resp.raise_for_status()
                        data = resp.json()
                        return (index, data["embedding"])

            # Process all texts in parallel (semaphore limits actual concurrency)
            results = await asyncio.gather(
                *[embed_single(text, i) for i, text in enumerate(texts)]
            )

            # Sort by index to maintain original order
            sorted_results = sorted(results, key=lambda x: x[0])
            return [emb for _, emb in sorted_results]
        else:
            # OpenAI-compatible API (vLLM, etc.) - native batch support
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.api_base}/v1/embeddings",
                    json={
                        "model": self.model,
                        "input": texts,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                vectors = [item["embedding"] for item in data["data"]]
                return vectors

    async def embed_single(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector as a list of floats
        """
        vectors = await self.embed([text])
        return vectors[0] if vectors else []

    async def health_check(self) -> Dict:
        """
        Check if the embedding server is reachable and responsive.

        Returns:
            Dict with 'status', 'model', and optional 'error' keys
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if self.provider == "ollama":
                    # Ollama native API
                    resp = await client.post(
                        f"{self.api_base}/api/embeddings",
                        json={
                            "model": self.model,
                            "prompt": "test",
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        dim = len(data.get("embedding", []))
                        return {
                            "status": "healthy",
                            "model": self.model,
                            "api_base": self.api_base,
                            "dimension": dim,
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "model": self.model,
                            "error": f"HTTP {resp.status_code}",
                        }
                else:
                    # OpenAI-compatible API
                    resp = await client.post(
                        f"{self.api_base}/v1/embeddings",
                        json={
                            "model": self.model,
                            "input": ["test"],
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        dim = len(data["data"][0]["embedding"]) if data["data"] else 0
                        return {
                            "status": "healthy",
                            "model": self.model,
                            "api_base": self.api_base,
                            "dimension": dim,
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "model": self.model,
                            "error": f"HTTP {resp.status_code}",
                        }
        except Exception as e:
            return {
                "status": "unreachable",
                "model": self.model,
                "api_base": self.api_base,
                "error": str(e),
            }


# Default client instance
_default_client: Optional[EmbeddingClient] = None


def get_embedding_client() -> EmbeddingClient:
    """Get the default embedding client instance (singleton)."""
    global _default_client
    if _default_client is None:
        _default_client = EmbeddingClient()
    return _default_client


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Convenience function for embedding texts.

    This maintains backward compatibility with existing code.

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors
    """
    client = get_embedding_client()
    return await client.embed(texts)
