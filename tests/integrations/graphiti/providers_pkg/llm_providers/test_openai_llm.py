"""Tests for openai_llm"""

from unittest.mock import MagicMock, patch

import pytest

from integrations.graphiti.providers_pkg.llm_providers.openai_llm import (
    create_openai_llm_client,
)
from integrations.graphiti.providers_pkg.exceptions import ProviderNotInstalled


def test_create_openai_llm_client():
    """Test create_openai_llm_client"""

    # Arrange - use a simple object with the required attributes
    from types import SimpleNamespace

    config = SimpleNamespace(
        openai_api_key="test-api-key",
        openai_model="gpt-4o",
    )

    # Mock graphiti_core modules for testing
    mock_llm_config = MagicMock()
    mock_openai_client = MagicMock()

    with patch.dict("sys.modules", {
        "graphiti_core": MagicMock(),
        "graphiti_core.llm_client": MagicMock(),
        "graphiti_core.llm_client.config": MagicMock(LLMConfig=mock_llm_config),
        "graphiti_core.llm_client.openai_client": MagicMock(OpenAIClient=mock_openai_client)
    }):
        # Act & Assert
        # When graphiti-core IS installed, this should work
        result = create_openai_llm_client(config)
        assert result is not None
