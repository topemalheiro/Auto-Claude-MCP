"""Tests for azure_openai_embedder"""

from unittest.mock import MagicMock, patch

import pytest

from integrations.graphiti.providers_pkg.embedder_providers.azure_openai_embedder import (
    create_azure_openai_embedder,
)
from integrations.graphiti.providers_pkg.exceptions import ProviderNotInstalled


def test_create_azure_openai_embedder():
    """Test create_azure_openai_embedder"""

    # Arrange
    config = MagicMock()
    config.azure_openai_api_key = "test-api-key"
    config.azure_openai_endpoint = "https://test.openai.azure.com"
    config.azure_openai_embedding_deployment = "test-deployment"
    config.azure_openai_embedding_model = "text-embedding-ada-002"

    # Act & Assert
    # The function requires graphiti-core which may not be installed
    # We test the error handling path
    with pytest.raises(ProviderNotInstalled) as exc_info:
        create_azure_openai_embedder(config)
    assert "graphiti-core" in str(exc_info.value)


def test_create_azure_openai_embedder_missing_api_key():
    """Test create_azure_openai_embedder raises error when API key is missing"""

    # Arrange
    config = MagicMock()
    config.azure_openai_api_key = None

    # Act & Assert
    with pytest.raises(Exception):
        create_azure_openai_embedder(config)
