"""Tests for openai_llm"""

from unittest.mock import MagicMock, patch

import pytest

from integrations.graphiti.providers_pkg.llm_providers.openai_llm import (
    create_openai_llm_client,
)
from integrations.graphiti.providers_pkg.exceptions import ProviderNotInstalled


def test_create_openai_llm_client():
    """Test create_openai_llm_client"""

    # Arrange
    config = MagicMock()
    config.openai_api_key = "test-api-key"
    config.openai_llm_model = "gpt-4o"

    # Act & Assert
    # The function requires graphiti-core which may not be installed
    with pytest.raises(ProviderNotInstalled) as exc_info:
        create_openai_llm_client(config)
    assert "graphiti-core" in str(exc_info.value)
