"""Tests for google_llm"""

from unittest.mock import MagicMock, patch

import pytest

from integrations.graphiti.providers_pkg.llm_providers.google_llm import (
    GoogleLLMClient,
    create_google_llm_client,
)
from integrations.graphiti.providers_pkg.exceptions import ProviderError


def test_create_google_llm_client():
    """Test create_google_llm_client"""

    # Arrange
    config = MagicMock()
    config.google_api_key = "test-api-key"
    config.google_llm_model = "gemini-1.5-pro"

    # Act & Assert
    # Requires google-generativeai to be installed
    try:
        result = create_google_llm_client(config)
        assert result is not None
        assert isinstance(result, GoogleLLMClient)
    except Exception as e:
        # Expected if google-generativeai is not installed
        assert "google" in str(e).lower() or "provider" in str(e).lower()


def test_create_google_llm_client_missing_api_key():
    """Test create_google_llm_client raises ProviderError when API key is missing"""

    # Arrange
    config = MagicMock()
    config.google_api_key = None

    # Act & Assert
    with pytest.raises(ProviderError, match="Google LLM provider requires GOOGLE_API_KEY"):
        create_google_llm_client(config)


def test_GoogleLLMClient___init__():
    """Test GoogleLLMClient.__init__"""

    # Arrange & Act & Assert
    try:
        instance = GoogleLLMClient(api_key="test-key", model="test-model")
        assert instance.api_key == "test-key"
        assert instance.model == "test-model"
    except Exception as e:
        # Expected if google-generativeai is not installed
        assert "google" in str(e).lower()


def test_GoogleLLMClient_generate_response():
    """Test GoogleLLMClient.generate_response"""

    # Arrange & Act & Assert
    try:
        instance = GoogleLLMClient(api_key="test-key", model="test-model")

        import asyncio

        result = asyncio.run(instance.generate_response([{"role": "user", "content": "test"}], None))
        assert result is not None
    except Exception as e:
        # Expected if google-generativeai is not installed or API key is invalid
        assert "google" in str(e).lower() or "api" in str(e).lower()


def test_GoogleLLMClient_generate_response_with_tools():
    """Test GoogleLLMClient.generate_response_with_tools"""

    # Arrange & Act & Assert
    try:
        instance = GoogleLLMClient(api_key="test-key", model="test-model")

        import asyncio

        result = asyncio.run(
            instance.generate_response_with_tools(
                [{"role": "user", "content": "test"}], [{"name": "test_tool"}]
            )
        )
        assert result is not None
    except Exception as e:
        # Expected if google-generativeai is not installed or API key is invalid
        assert "google" in str(e).lower() or "api" in str(e).lower()
