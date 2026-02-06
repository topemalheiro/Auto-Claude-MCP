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

    # Act & Assert
    # When graphiti-core IS installed, this should work
    result = create_openai_llm_client(config)
    assert result is not None
