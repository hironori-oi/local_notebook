"""
LLM Client - Abstraction layer for LLM providers (Ollama, vLLM, etc.)

Supports Ollama native API (/api/chat) and OpenAI-compatible API (/v1/chat/completions).
The provider can be switched via LLM_PROVIDER environment variable.
"""
from typing import List, Dict, Optional, AsyncGenerator
import httpx
import json

from app.core.config import settings


class LLMClient:
    """
    Unified LLM client supporting multiple providers.

    Supported providers:
    - ollama: Local Ollama server using native API (/api/chat)
    - vllm: vLLM server using OpenAI-compatible API (/v1/chat/completions)
    """

    def __init__(
        self,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        timeout: float = 120.0,
        max_tokens: Optional[int] = None,
    ):
        self.api_base = api_base or settings.LLM_API_BASE
        self.model = model or settings.LLM_MODEL
        self.provider = provider or settings.LLM_PROVIDER
        self.timeout = timeout
        self.max_tokens = max_tokens or settings.LLM_MAX_TOKENS

    async def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> str:
        """
        Send chat completion request and return the response content.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response (not yet implemented)

        Returns:
            The assistant's response content as a string
        """
        # Use provided max_tokens or fall back to instance default
        tokens_limit = max_tokens or self.max_tokens

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if self.provider == "ollama":
                # Ollama native API
                resp = await client.post(
                    f"{self.api_base}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": tokens_limit,
                        },
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["message"]["content"]
            else:
                # OpenAI-compatible API (vLLM, etc.)
                resp = await client.post(
                    f"{self.api_base}/v1/chat/completions",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": tokens_limit,
                        "stream": stream,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]

    async def chat_stream(
        self,
        messages: List[Dict],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Send chat completion request with streaming and yield response chunks.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens to generate

        Yields:
            Response content chunks as they arrive
        """
        # Use provided max_tokens or fall back to instance default
        tokens_limit = max_tokens or self.max_tokens

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if self.provider == "ollama":
                # Ollama native streaming API
                async with client.stream(
                    "POST",
                    f"{self.api_base}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": True,
                        "options": {
                            "temperature": temperature,
                            "num_predict": tokens_limit,
                        },
                    },
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                content = data.get("message", {}).get("content", "")
                                if content:
                                    yield content
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
            else:
                # OpenAI-compatible streaming API
                async with client.stream(
                    "POST",
                    f"{self.api_base}/v1/chat/completions",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": tokens_limit,
                        "stream": True,
                    },
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue

    async def health_check(self) -> Dict:
        """
        Check if the LLM server is reachable and responsive.

        Returns:
            Dict with 'status', 'provider', 'model', and optional 'error' keys
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if self.provider == "ollama":
                    # Ollama native API - check tags endpoint
                    resp = await client.get(f"{self.api_base}/api/tags")
                else:
                    # OpenAI-compatible API
                    resp = await client.get(f"{self.api_base}/v1/models")

                if resp.status_code == 200:
                    return {
                        "status": "healthy",
                        "provider": self.provider,
                        "model": self.model,
                        "api_base": self.api_base,
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "provider": self.provider,
                        "model": self.model,
                        "error": f"HTTP {resp.status_code}",
                    }
        except Exception as e:
            return {
                "status": "unreachable",
                "provider": self.provider,
                "model": self.model,
                "api_base": self.api_base,
                "error": str(e),
            }


# Default client instance
_default_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get the default LLM client instance (singleton)."""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client


async def call_llm(messages: List[Dict]) -> str:
    """
    Convenience function for simple chat completion.

    This maintains backward compatibility with existing code.
    """
    client = get_llm_client()
    return await client.chat(messages)


# =============================================================================
# Generation LLM Client (for infographic/slide generation)
# =============================================================================

_generation_client: Optional[LLMClient] = None


def get_generation_llm_client() -> LLMClient:
    """
    Get the generation-specific LLM client instance (singleton).

    Uses GENERATION_LLM_MODEL if set, otherwise falls back to LLM_MODEL.
    Uses GENERATION_LLM_MAX_TOKENS for longer outputs needed for structured generation.
    Uses a longer timeout (300s) for complex generation tasks.
    """
    global _generation_client
    if _generation_client is None:
        model = settings.GENERATION_LLM_MODEL or settings.LLM_MODEL
        _generation_client = LLMClient(
            model=model,
            max_tokens=settings.GENERATION_LLM_MAX_TOKENS,
            timeout=300.0,  # 5 minutes for large model generation
        )
    return _generation_client


async def call_generation_llm(messages: List[Dict], temperature: float = 0.3) -> str:
    """
    Call LLM for content generation tasks (infographics, slides, etc.).

    Uses a slightly higher temperature than the default chat for more
    creative structured output generation.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        temperature: Sampling temperature (default: 0.3 for balanced creativity)

    Returns:
        The assistant's response content as a string
    """
    client = get_generation_llm_client()
    return await client.chat(messages, temperature=temperature)
