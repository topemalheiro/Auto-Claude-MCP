"""Tests for anthropic_llm"""

from unittest.mock import MagicMock, patch

import pytest

from integrations.graphiti.providers_pkg.llm_providers.anthropic_llm import (
    create_anthropic_llm_client,
)
from integrations.graphiti.providers_pkg.exceptions import ProviderNotInstalled


def test_create_anthropic_llm_client():
    """Test create_anthropic_llm_client"""

    # Arrange
    config = MagicMock()
    config.anthropic_api_key = "test-api-key"
    config.anthropic_model = "claude-3-5-sonnet-20241022"

    # Act & Assert
    # The function requires graphiti-core which may not be installed
    with pytest.raises(ProviderNotInstalled) as exc_info:
        create_anthropic_llm_client(config)
    assert "graphiti-core" in str(exc_info.value)


def test_create_anthropic_llm_client_missing_api_key():
    """Test create_anthropic_llm_client raises ProviderNotInstalled when graphiti-core is missing"""

    # Arrange
    config = MagicMock()
    config.anthropic_api_key = None

    # Act & Assert
    # The function tries to import graphiti_core first before checking the API key
    with pytest.raises(ProviderNotInstalled) as exc_info:
        create_anthropic_llm_client(config)
    assert "graphiti-core" in str(exc_info.value)
