"""Tests for azure_openai_embedder"""

from unittest.mock import MagicMock, patch
from types import SimpleNamespace

import pytest

from integrations.graphiti.providers_pkg.embedder_providers.azure_openai_embedder import (
    create_azure_openai_embedder,
)
from integrations.graphiti.providers_pkg.exceptions import ProviderNotInstalled, ProviderError


def test_create_azure_openai_embedder():
    """Test create_azure_openai_embedder successfully creates embedder"""

    # Arrange - use SimpleNamespace to create config with actual values
    config = SimpleNamespace(
        azure_openai_api_key="test-api-key",
        azure_openai_base_url="https://test.openai.azure.com",
        azure_openai_embedding_deployment="test-deployment",
        azure_openai_embedding_model="text-embedding-ada-002",
    )

    # Create a proper mock for AzureOpenAIEmbedderClient
    mock_embedder_instance = MagicMock()
    mock_embedder_instance.__class__.__name__ = "AzureOpenAIEmbedderClient"

    mock_azure_client_class = MagicMock(return_value=mock_embedder_instance)
    mock_async_openai_instance = MagicMock()

    with patch.dict("sys.modules", {
        "graphiti_core": MagicMock(),
        "graphiti_core.embedder": MagicMock(),
        "graphiti_core.embedder.azure_openai": MagicMock(AzureOpenAIEmbedderClient=mock_azure_client_class),
        "openai": MagicMock(),
        "openai.AsyncOpenAI": MagicMock(return_value=mock_async_openai_instance)
    }):
        # Act
        result = create_azure_openai_embedder(config)

        # Assert
        assert result is not None
        # Check that it's an AzureOpenAIEmbedderClient
        assert result.__class__.__name__ == "AzureOpenAIEmbedderClient"


def test_create_azure_openai_embedder_missing_api_key():
    """Test create_azure_openai_embedder raises error when API key is missing"""

    # Arrange - SimpleNamespace with None value
    config = SimpleNamespace(
        azure_openai_api_key=None,
        azure_openai_base_url=None,
        azure_openai_embedding_deployment=None,
    )

    # Mock graphiti_core and openai so we get past the import checks
    mock_azure_client_class = MagicMock()

    with patch.dict("sys.modules", {
        "graphiti_core": MagicMock(),
        "graphiti_core.embedder": MagicMock(),
        "graphiti_core.embedder.azure_openai": MagicMock(AzureOpenAIEmbedderClient=mock_azure_client_class),
        "openai": MagicMock(),
        "openai.AsyncOpenAI": MagicMock()
    }):
        # Act & Assert
        with pytest.raises(ProviderError, match="AZURE_OPENAI_API_KEY"):
            create_azure_openai_embedder(config)


def test_create_azure_openai_embedder_missing_base_url():
    """Test create_azure_openai_embedder raises error when base URL is missing"""

    # Arrange - SimpleNamespace with None for base_url
    config = SimpleNamespace(
        azure_openai_api_key="test-api-key",
        azure_openai_base_url=None,
        azure_openai_embedding_deployment=None,
    )

    # Mock graphiti_core and openai so we get past the import checks
    mock_azure_client_class = MagicMock()

    with patch.dict("sys.modules", {
        "graphiti_core": MagicMock(),
        "graphiti_core.embedder": MagicMock(),
        "graphiti_core.embedder.azure_openai": MagicMock(AzureOpenAIEmbedderClient=mock_azure_client_class),
        "openai": MagicMock(),
        "openai.AsyncOpenAI": MagicMock()
    }):
        # Act & Assert
        with pytest.raises(ProviderError, match="AZURE_OPENAI_BASE_URL"):
            create_azure_openai_embedder(config)


def test_create_azure_openai_embedder_missing_deployment():
    """Test create_azure_openai_embedder raises error when deployment is missing"""

    # Arrange - SimpleNamespace with None for deployment
    config = SimpleNamespace(
        azure_openai_api_key="test-api-key",
        azure_openai_base_url="https://test.openai.azure.com",
        azure_openai_embedding_deployment=None,
    )

    # Mock graphiti_core and openai so we get past the import checks
    mock_azure_client_class = MagicMock()

    with patch.dict("sys.modules", {
        "graphiti_core": MagicMock(),
        "graphiti_core.embedder": MagicMock(),
        "graphiti_core.embedder.azure_openai": MagicMock(AzureOpenAIEmbedderClient=mock_azure_client_class),
        "openai": MagicMock(),
        "openai.AsyncOpenAI": MagicMock()
    }):
        # Act & Assert
        with pytest.raises(ProviderError, match="AZURE_OPENAI_EMBEDDING_DEPLOYMENT"):
            create_azure_openai_embedder(config)


def test_create_azure_openai_embedder_without_graphiti_core():
    """Test create_azure_openai_embedder raises ProviderNotInstalled when graphiti-core is missing"""

    # Arrange
    config = SimpleNamespace(
        azure_openai_api_key="test-api-key",
        azure_openai_base_url="https://test.openai.azure.com",
        azure_openai_embedding_deployment="test-deployment",
    )

    # Act & Assert
    # Patch the import statement to simulate missing graphiti-core
    with patch("builtins.__import__", side_effect=ImportError("No module named 'graphiti_core'")):
        with pytest.raises(ProviderNotInstalled) as exc_info:
            create_azure_openai_embedder(config)
        assert "graphiti-core" in str(exc_info.value)
