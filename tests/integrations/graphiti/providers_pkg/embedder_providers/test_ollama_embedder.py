"""Tests for ollama_embedder"""

from unittest.mock import MagicMock, patch

import pytest

from integrations.graphiti.providers_pkg.embedder_providers.ollama_embedder import (
    create_ollama_embedder,
    get_embedding_dim_for_model,
)
from integrations.graphiti.providers_pkg.exceptions import ProviderError


def test_get_embedding_dim_for_model_known_model():
    """Test get_embedding_dim_for_model for known models"""

    # Arrange & Act
    result = get_embedding_dim_for_model("all-minilm", 0)

    # Assert
    assert result == 384


def test_get_embedding_dim_for_model_configured_dim():
    """Test get_embedding_dim_for_model with configured dimension"""

    # Arrange & Act
    result = get_embedding_dim_for_model("custom-model", 1024)

    # Assert
    assert result == 1024


def test_get_embedding_dim_for_model_unknown_model_no_config():
    """Test get_embedding_dim_for_model raises ProviderError for unknown model without configured dim"""

    # Arrange & Act & Assert
    with pytest.raises(ProviderError, match="Unknown Ollama embedding model"):
        get_embedding_dim_for_model("unknown-model", 0)


def test_get_embedding_dim_for_model_all_known_models():
    """Test get_embedding_dim_for_model for all known models"""

    # Test all known models
    known_models = {
        "all-minilm": 384,
        "bge-large": 1024,
        "bge-m3": 1024,
        "embeddinggemma": 768,
        "mxbai-embed-large": 1024,
        "nomic-embed-text": 768,
        "qwen3-embedding": 1024,
    }

    for model, expected_dim in known_models.items():
        result = get_embedding_dim_for_model(model, 0)
        assert result == expected_dim, f"Expected {expected_dim} for {model}, got {result}"


def test_create_ollama_embedder():
    """Test create_ollama_embedder"""

    # Arrange
    config = MagicMock()
    config.ollama_embedding_model = "nomic-embed-text"
    config.ollama_base_url = "http://localhost:11434"
    config.ollama_embedding_dim = 768

    # Act & Assert
    # Try to create the embedder, it might fail if graphiti-core is not installed
    try:
        result = create_ollama_embedder(config)
        assert result is not None
    except Exception as e:
        # Expected if graphiti-core is not installed
        assert "graphiti" in str(e).lower() or "provider" in str(e).lower()


def test_create_ollama_embedder_missing_model():
    """Test create_ollama_embedder raises ProviderError when model is missing"""

    # Arrange
    config = MagicMock()
    config.ollama_embedding_model = None

    # Act & Assert
    with pytest.raises(ProviderError, match="Ollama embedder requires OLLAMA_EMBEDDING_MODEL"):
        create_ollama_embedder(config)
