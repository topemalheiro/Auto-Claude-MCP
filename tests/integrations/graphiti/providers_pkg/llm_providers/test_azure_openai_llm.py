"""Tests for azure_openai_llm"""

from unittest.mock import MagicMock, patch

import pytest

from integrations.graphiti.providers_pkg.llm_providers.azure_openai_llm import (
    create_azure_openai_llm_client,
)
from integrations.graphiti.providers_pkg.exceptions import ProviderNotInstalled


def test_create_azure_openai_llm_client():
    """Test create_azure_openai_llm_client"""

    # Arrange
    config = MagicMock()
    config.azure_openai_api_key = "test-api-key"
    config.azure_openai_endpoint = "https://test.openai.azure.com"
    config.azure_openai_llm_deployment = "test-deployment"
    config.azure_openai_llm_model = "gpt-4"

    # Act & Assert
    # The function requires graphiti-core which may not be installed
    with pytest.raises(ProviderNotInstalled) as exc_info:
        create_azure_openai_llm_client(config)
    assert "graphiti-core" in str(exc_info.value)
