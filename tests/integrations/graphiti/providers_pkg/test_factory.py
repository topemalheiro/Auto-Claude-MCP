"""Tests for factory"""

from unittest.mock import MagicMock, patch

import pytest

from integrations.graphiti.providers_pkg.exceptions import ProviderNotInstalled
from integrations.graphiti.providers_pkg.factory import create_embedder, create_llm_client


def test_create_llm_client_anthropic():
    """Test create_llm_client with anthropic provider"""

    # Arrange
    config = MagicMock()
    config.llm_provider = "anthropic"
    config.anthropic_api_key = "test-api-key"
    config.anthropic_model = "claude-3-5-sonnet-20241022"

    # Act & Assert
    # This requires graphiti-core which may not be installed
    try:
        result = create_llm_client(config)
        assert result is not None
    except ProviderNotInstalled as e:
        # Expected if graphiti-core is not installed
        assert "graphiti-core" in str(e)


def test_create_llm_client_invalid_provider():
    """Test create_llm_client with invalid provider"""

    # Arrange
    config = MagicMock()
    config.llm_provider = "invalid_provider"

    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        create_llm_client(config)
    assert "Unknown" in str(exc_info.value) or "invalid" in str(exc_info.value).lower()


def test_create_embedder_ollama():
    """Test create_embedder with ollama provider"""

    # Arrange
    config = MagicMock()
    config.embedder_provider = "ollama"
    config.ollama_embedding_model = "nomic-embed-text"
    config.ollama_base_url = "http://localhost:11434"
    config.ollama_embedding_dim = 768

    # Act & Assert
    try:
        result = create_embedder(config)
        assert result is not None
    except Exception as e:
        # Expected if graphiti-core is not installed
        assert "graphiti" in str(e).lower() or "provider" in str(e).lower()


def test_create_embedder_invalid_provider():
    """Test create_embedder with invalid provider"""

    # Arrange
    config = MagicMock()
    config.embedder_provider = "invalid_provider"

    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        create_embedder(config)
    assert "Unknown" in str(exc_info.value) or "invalid" in str(exc_info.value).lower()
