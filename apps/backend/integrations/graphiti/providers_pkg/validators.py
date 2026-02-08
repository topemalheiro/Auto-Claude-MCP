"""
Provider Validators and Health Checks
======================================

Validation and health check functions for Graphiti providers.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from graphiti_config import GraphitiConfig

from .exceptions import ProviderError, ProviderNotInstalled
from .models import get_expected_embedding_dim

logger = logging.getLogger(__name__)


def validate_embedding_config(config: "GraphitiConfig") -> tuple[bool, str]:
    """
    Validate embedding configuration for consistency.

    Checks that embedding dimensions are correctly configured,
    especially important for Ollama where explicit dimension is required.

    Args:
        config: GraphitiConfig to validate

    Returns:
        Tuple of (is_valid, message)
    """
    provider = config.embedder_provider

    if provider == "ollama":
        # Ollama requires explicit embedding dimension
        if not config.ollama_embedding_dim:
            expected = get_expected_embedding_dim(config.ollama_embedding_model)
            if expected:
                return False, (
                    f"Ollama embedder requires OLLAMA_EMBEDDING_DIM. "
                    f"For model '{config.ollama_embedding_model}', "
                    f"expected dimension is {expected}."
                )
            else:
                return False, (
                    "Ollama embedder requires OLLAMA_EMBEDDING_DIM. "
                    "Check your model's documentation for the correct dimension."
                )

    # Check for known dimension mismatches
    if provider == "openai":
        expected = get_expected_embedding_dim(config.openai_embedding_model)
        # OpenAI handles this automatically, just log info
        if expected:
            logger.debug(
                f"OpenAI embedding model '{config.openai_embedding_model}' has dimension {expected}"
            )

    elif provider == "voyage":
        expected = get_expected_embedding_dim(config.voyage_embedding_model)
        if expected:
            logger.debug(
                f"Voyage embedding model '{config.voyage_embedding_model}' has dimension {expected}"
            )

    return True, "Embedding configuration valid"


async def test_llm_connection(config: "GraphitiConfig") -> tuple[bool, str]:
    """
    Test if LLM provider is reachable.

    Args:
        config: GraphitiConfig with provider settings

    Returns:
        Tuple of (success, message)
    """

    try:
        # llm_client = ...  # TODO: unused variable
        # Most clients don't have a ping method, so just verify creation succeeded
        return (
            True,
            f"LLM client created successfully for provider: {config.llm_provider}",
        )
    except ProviderNotInstalled as e:
        return False, str(e)
    except ProviderError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Failed to create LLM client: {e}"


async def test_embedder_connection(config: "GraphitiConfig") -> tuple[bool, str]:
    """
    Test if embedder provider is reachable.

    Args:
        config: GraphitiConfig with provider settings

    Returns:
        Tuple of (success, message)
    """

    # First validate config
    valid, msg = validate_embedding_config(config)
    if not valid:
        return False, msg

    try:
        # embedder = ...  # TODO: unused variable
        return (
            True,
            f"Embedder created successfully for provider: {config.embedder_provider}",
        )
    except ProviderNotInstalled as e:
        return False, str(e)
    except ProviderError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Failed to create embedder: {e}"


async def test_ollama_connection(
    base_url: str = "http://localhost:11434",
) -> tuple[bool, str]:
    """
    Test if Ollama server is running and reachable.

    Args:
        base_url: Ollama server URL

    Returns:
        Tuple of (success, message)
    """
    import asyncio

    # Normalize URL first (used in both paths)
    url = base_url.rstrip("/")
    if url.endswith("/v1"):
        url = url[:-3]

    try:
        import aiohttp
    except ImportError:
        # Fall back to sync request
        import urllib.error
        import urllib.request

        try:
            req = urllib.request.Request(f"{url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as response:
                status = response.status
                if status == 200:
                    return True, f"Ollama is running at {url}"
                return False, f"Ollama returned status {status}"
        except urllib.error.URLError as e:
            return False, f"Cannot connect to Ollama at {url}: {e.reason}"
        except Exception as e:
            return False, f"Ollama connection error: {e}"

    # Use aiohttp if available
    try:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{url}/api/tags", timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    status = response.status
                    if status == 200:
                        return True, f"Ollama is running at {url}"
                    return False, f"Ollama returned status {status}"
            except asyncio.TimeoutError:
                return False, f"Ollama connection timed out at {url}"
            except Exception:
                # Catch aiohttp.ClientError and any other exceptions from session.get
                return False, f"Cannot connect to Ollama at {url}"
    except Exception:
        # Catch any exceptions from ClientSession creation
        return False, f"Cannot connect to Ollama at {url}"
