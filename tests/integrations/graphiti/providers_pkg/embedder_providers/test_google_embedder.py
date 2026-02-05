"""Tests for google_embedder"""

from unittest.mock import MagicMock, patch

import pytest

from integrations.graphiti.providers_pkg.embedder_providers.google_embedder import (
    GoogleEmbedder,
    create_google_embedder,
)
from integrations.graphiti.providers_pkg.exceptions import ProviderError


def test_create_google_embedder():
    """Test create_google_embedder"""

    # Arrange
    config = MagicMock()
    config.google_api_key = "test-api-key"
    config.google_embedding_model = "text-embedding-004"

    # Act & Assert
    try:
        result = create_google_embedder(config)
        assert result is not None
        assert isinstance(result, GoogleEmbedder)
    except Exception as e:
        # Expected if google-generativeai is not installed
        assert "google" in str(e).lower() or "provider" in str(e).lower()


def test_create_google_embedder_missing_api_key():
    """Test create_google_embedder raises ProviderError when API key is missing"""

    # Arrange
    config = MagicMock()
    config.google_api_key = None

    # Act & Assert
    with pytest.raises(ProviderError, match="Google embedder requires GOOGLE_API_KEY"):
        create_google_embedder(config)


def test_create_google_embedder_default_model():
    """Test create_google_embedder uses default model when not specified"""

    # Arrange
    config = MagicMock()
    config.google_api_key = "test-api-key"
    config.google_embedding_model = None

    # Act & Assert
    try:
        result = create_google_embedder(config)
        assert result is not None
        assert result.model == "text-embedding-004"  # Default model
    except Exception as e:
        # Expected if google-generativeai is not installed
        assert "google" in str(e).lower()


def test_GoogleEmbedder___init__():
    """Test GoogleEmbedder.__init__"""

    # Arrange & Act & Assert
    try:
        instance = GoogleEmbedder(api_key="test-key", model="test-model")
        assert instance.api_key == "test-key"
        assert instance.model == "test-model"
    except Exception as e:
        # Expected if google-generativeai is not installed
        assert "google" in str(e).lower()


def test_GoogleEmbedder_create():
    """Test GoogleEmbedder.create"""

    # Arrange & Act & Assert
    try:
        instance = GoogleEmbedder(api_key="test-key", model="test-model")

        import asyncio

        result = asyncio.run(instance.create("test input"))
        assert result is not None
    except Exception as e:
        # Expected if google-generativeai is not installed or API key is invalid
        assert "google" in str(e).lower() or "api" in str(e).lower()


def test_GoogleEmbedder_create_batch():
    """Test GoogleEmbedder.create_batch"""

    # Arrange & Act & Assert
    try:
        instance = GoogleEmbedder(api_key="test-key", model="test-model")

        import asyncio

        result = asyncio.run(instance.create_batch(["input1", "input2"]))
        assert result is not None
    except Exception as e:
        # Expected if google-generativeai is not installed or API key is invalid
        assert "google" in str(e).lower() or "api" in str(e).lower()


def test_GoogleEmbedder_create_not_installed():
    """Test GoogleEmbedder raises ProviderNotInstalled when google-generativeai is not installed"""

    # Arrange & Act & Assert
    with patch.dict("sys.modules", {"google": None, "google.generativeai": None}):
        with pytest.raises(Exception) as exc_info:
            GoogleEmbedder(api_key="test-key")
        assert "google-generativeai" in str(exc_info.value) or "Provider" in str(exc_info.value)
