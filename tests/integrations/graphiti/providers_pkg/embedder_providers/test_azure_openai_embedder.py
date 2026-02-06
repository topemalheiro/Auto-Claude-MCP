"""Tests for azure_openai_embedder"""

from unittest.mock import MagicMock, patch

import pytest

from integrations.graphiti.providers_pkg.embedder_providers.azure_openai_embedder import (
    create_azure_openai_embedder,
)
from integrations.graphiti.providers_pkg.exceptions import ProviderNotInstalled, ProviderError


def test_create_azure_openai_embedder():
    """Test create_azure_openai_embedder successfully creates embedder"""

    # Arrange
    config = MagicMock()
    config.azure_openai_api_key = "test-api-key"
    config.azure_openai_base_url = "https://test.openai.azure.com"
    config.azure_openai_embedding_deployment = "test-deployment"
    config.azure_openai_embedding_model = "text-embedding-ada-002"

    # Act
    result = create_azure_openai_embedder(config)

    # Assert
    assert result is not None
    # Check that it's an AzureOpenAIEmbedderClient
    assert result.__class__.__name__ == "AzureOpenAIEmbedderClient"


def test_create_azure_openai_embedder_missing_api_key():
    """Test create_azure_openai_embedder raises error when API key is missing"""

    # Arrange
    config = MagicMock()
    config.azure_openai_api_key = None

    # Act & Assert
    with pytest.raises(ProviderError, match="AZURE_OPENAI_API_KEY"):
        create_azure_openai_embedder(config)


def test_create_azure_openai_embedder_missing_base_url():
    """Test create_azure_openai_embedder raises error when base URL is missing"""

    # Arrange
    config = MagicMock()
    config.azure_openai_api_key = "test-api-key"
    config.azure_openai_base_url = None

    # Act & Assert
    with pytest.raises(ProviderError, match="AZURE_OPENAI_BASE_URL"):
        create_azure_openai_embedder(config)


def test_create_azure_openai_embedder_missing_deployment():
    """Test create_azure_openai_embedder raises error when deployment is missing"""

    # Arrange
    config = MagicMock()
    config.azure_openai_api_key = "test-api-key"
    config.azure_openai_base_url = "https://test.openai.azure.com"
    config.azure_openai_embedding_deployment = None

    # Act & Assert
    with pytest.raises(ProviderError, match="AZURE_OPENAI_EMBEDDING_DEPLOYMENT"):
        create_azure_openai_embedder(config)


def test_create_azure_openai_embedder_without_graphiti_core():
    """Test create_azure_openai_embedder raises ProviderNotInstalled when graphiti-core is missing"""

    # Arrange
    config = MagicMock()
    config.azure_openai_api_key = "test-api-key"
    config.azure_openai_base_url = "https://test.openai.azure.com"
    config.azure_openai_embedding_deployment = "test-deployment"

    # Act & Assert
    # Patch the import statement to simulate missing graphiti-core
    with patch("builtins.__import__", side_effect=ImportError("No module named 'graphiti_core'")):
        with pytest.raises(ProviderNotInstalled) as exc_info:
            create_azure_openai_embedder(config)
        assert "graphiti-core" in str(exc_info.value)
