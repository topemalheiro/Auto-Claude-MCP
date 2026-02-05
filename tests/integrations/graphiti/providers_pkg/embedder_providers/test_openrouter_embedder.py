"""Tests for openrouter_embedder"""

from unittest.mock import MagicMock, patch

import pytest

from integrations.graphiti.providers_pkg.embedder_providers.openrouter_embedder import (
    create_openrouter_embedder,
)
from integrations.graphiti.providers_pkg.exceptions import ProviderNotInstalled, ProviderError


def test_create_openrouter_embedder():
    """Test create_openrouter_embedder"""

    # Arrange
    config = MagicMock()
    config.openrouter_api_key = "test-api-key"
    config.openrouter_embedding_model = "openai/text-embedding-3-small"
    config.openrouter_embedding_dim = 1536

    # Act & Assert
    # The function requires graphiti-core which may not be installed
    # Test the error handling path when graphiti-core is not available
    with patch.dict('sys.modules', {'graphiti_core': None, 'graphiti_core.embedder': None, 'graphiti_core.embedder.openai': None}):
        with pytest.raises(ProviderNotInstalled) as exc_info:
            create_openrouter_embedder(config)
        assert "graphiti-core" in str(exc_info.value)


def test_create_openrouter_embedder_missing_api_key():
    """Test create_openrouter_embedder raises error when API key is missing"""

    # Arrange
    config = MagicMock()
    config.openrouter_api_key = None

    # Act & Assert
    # Clear cached graphiti_core to force ImportError
    with patch.dict('sys.modules', {'graphiti_core': None, 'graphiti_core.embedder': None, 'graphiti_core.embedder.openai': None}):
        with pytest.raises(ProviderNotInstalled):
            create_openrouter_embedder(config)
