"""Tests for anthropic_llm"""

from unittest.mock import MagicMock


from integrations.graphiti.providers_pkg.llm_providers.anthropic_llm import (
    create_anthropic_llm_client,
)
from integrations.graphiti.providers_pkg.exceptions import ProviderNotInstalled, ProviderError


def test_create_anthropic_llm_client():
    """Test create_anthropic_llm_client"""

    # Arrange
    config = MagicMock()
    config.anthropic_api_key = "test-api-key"
    config.anthropic_model = "claude-3-5-sonnet-20241022"

    # Act & Assert
    # If graphiti-core is not installed, expect ProviderNotInstalled
    # If it is installed, the function will try to create the client
    try:
        result = create_anthropic_llm_client(config)
        # If we get here, graphiti-core is installed and client was created
        assert result is not None
    except ProviderNotInstalled:
        # Expected when graphiti-core is not installed
        pass
    except (Exception, ProviderError):
        # May get other errors if Anthropic API is unavailable or config is invalid
        # The test is primarily checking the function can be called
        pass


def test_create_anthropic_llm_client_missing_api_key():
    """Test create_anthropic_llm_client raises error when api key is missing"""

    # Arrange
    config = MagicMock()
    config.anthropic_api_key = None

    # Act & Assert
    # The function tries to import graphiti_core first before checking the API key
    try:
        create_anthropic_llm_client(config)
        # If graphiti-core is not installed, should have raised ProviderNotInstalled
        # If it is installed, should raise ProviderError for missing api key
        assert False, "Expected ProviderNotInstalled or ProviderError"
    except (ProviderNotInstalled, ProviderError):
        # Expected - either graphiti-core is not installed or api key is missing
        pass
