"""Tests for voyage_embedder"""

from unittest.mock import MagicMock, patch

import pytest

from integrations.graphiti.providers_pkg.embedder_providers.voyage_embedder import (
    create_voyage_embedder,
)
from integrations.graphiti.providers_pkg.exceptions import ProviderNotInstalled


def test_create_voyage_embedder():
    """Test create_voyage_embedder"""

    # Arrange
    config = MagicMock()
    config.voyage_api_key = "test-api-key"
    config.voyage_embedding_model = "voyage-3"
    config.voyage_embedding_dim = 1024

    # Act & Assert
    # The function requires graphiti-core which may not be installed
    # We test the error handling path
    with pytest.raises(ProviderNotInstalled) as exc_info:
        create_voyage_embedder(config)
    assert "graphiti-core" in str(exc_info.value)


def test_create_voyage_embedder_missing_api_key():
    """Test create_voyage_embedder raises error when API key is missing"""

    # Arrange
    config = MagicMock()
    config.voyage_api_key = None

    # Act & Assert
    with pytest.raises(Exception):
        create_voyage_embedder(config)
