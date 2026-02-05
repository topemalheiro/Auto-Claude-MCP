"""Tests for openrouter_llm"""

from unittest.mock import MagicMock, patch

import pytest

from integrations.graphiti.providers_pkg.llm_providers.openrouter_llm import (
    create_openrouter_llm_client,
)
from integrations.graphiti.providers_pkg.exceptions import ProviderNotInstalled


def test_create_openrouter_llm_client():
    """Test create_openrouter_llm_client"""

    # Arrange
    config = MagicMock()
    config.openrouter_api_key = "test-api-key"
    config.openrouter_llm_model = "anthropic/claude-3.5-sonnet"

    # Act & Assert
    # The function requires graphiti-core which may not be installed
    with pytest.raises(ProviderNotInstalled) as exc_info:
        create_openrouter_llm_client(config)
    assert "graphiti-core" in str(exc_info.value)
