"""
Tests for Graphiti provider factory functions.

Tests creation of LLM clients and embedders for all supported providers.
Uses sys.modules mocking to prevent graphiti-core import errors.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock graphiti_core before any imports
mock_graphiti_core = MagicMock()
sys.modules["graphiti_core"] = mock_graphiti_core
sys.modules["graphiti_core.embedder"] = MagicMock()
sys.modules["graphiti_core.embedder.openai"] = MagicMock()
sys.modules["graphiti_core.llm"] = MagicMock()
sys.modules["graphiti_core.llm_client"] = MagicMock()
sys.modules["graphiti_core.llm_client.config"] = MagicMock()
sys.modules["graphiti_core.utils"] = MagicMock()
sys.modules["graphiti_core.utils.errors"] = MagicMock()

from integrations.graphiti.providers_pkg.exceptions import (
    ProviderError,
    ProviderNotInstalled,
)
from integrations.graphiti.providers_pkg import factory


class TestCreateLLMClient:
    """Test create_llm_client factory function."""

    def test_create_llm_client_openai(self):
        """Test creating OpenAI LLM client."""
        from integrations.graphiti.config import GraphitiConfig

        config = GraphitiConfig(
            enabled=True,
            llm_provider="openai",
            openai_api_key="sk-test-key",
            openai_model="gpt-4",
        )

        # Patch the function in the factory module namespace
        with patch("integrations.graphiti.providers_pkg.factory.create_openai_llm_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            result = factory.create_llm_client(config)

            assert result == mock_client
            mock_create.assert_called_once_with(config)

    def test_create_llm_client_anthropic(self):
        """Test creating Anthropic LLM client."""
        from integrations.graphiti.config import GraphitiConfig

        config = GraphitiConfig(
            enabled=True,
            llm_provider="anthropic",
            anthropic_api_key="sk-ant-test",
        )

        with patch("integrations.graphiti.providers_pkg.factory.create_anthropic_llm_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            result = factory.create_llm_client(config)

            assert result == mock_client
            mock_create.assert_called_once_with(config)

    def test_create_llm_client_azure_openai(self):
        """Test creating Azure OpenAI LLM client."""
        from integrations.graphiti.config import GraphitiConfig

        config = GraphitiConfig(
            enabled=True,
            llm_provider="azure_openai",
            azure_openai_api_key="azure-test",
            azure_openai_base_url="https://test.openai.azure.com",
            azure_openai_llm_deployment="gpt-deployment",
        )

        with patch("integrations.graphiti.providers_pkg.factory.create_azure_openai_llm_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            result = factory.create_llm_client(config)

            assert result == mock_client
            mock_create.assert_called_once_with(config)

    def test_create_llm_client_ollama(self):
        """Test creating Ollama LLM client."""
        from integrations.graphiti.config import GraphitiConfig

        config = GraphitiConfig(
            enabled=True,
            llm_provider="ollama",
            ollama_base_url="http://localhost:11434",
            ollama_llm_model="deepseek-r1:7b",
        )

        with patch("integrations.graphiti.providers_pkg.factory.create_ollama_llm_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            result = factory.create_llm_client(config)

            assert result == mock_client
            mock_create.assert_called_once_with(config)

    def test_create_llm_client_google(self):
        """Test creating Google AI LLM client."""
        from integrations.graphiti.config import GraphitiConfig

        config = GraphitiConfig(
            enabled=True,
            llm_provider="google",
            google_api_key="google-test",
            google_llm_model="gemini-2.0-flash",
        )

        with patch("integrations.graphiti.providers_pkg.factory.create_google_llm_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            result = factory.create_llm_client(config)

            assert result == mock_client
            mock_create.assert_called_once_with(config)

    def test_create_llm_client_openrouter(self):
        """Test creating OpenRouter LLM client."""
        from integrations.graphiti.config import GraphitiConfig

        config = GraphitiConfig(
            enabled=True,
            llm_provider="openrouter",
            openrouter_api_key="or-test",
            openrouter_llm_model="anthropic/claude-sonnet-4",
        )

        with patch("integrations.graphiti.providers_pkg.factory.create_openrouter_llm_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            result = factory.create_llm_client(config)

            assert result == mock_client
            mock_create.assert_called_once_with(config)

    def test_create_llm_client_unknown_provider(self):
        """Test creating LLM client for unknown provider raises error."""
        from integrations.graphiti.config import GraphitiConfig

        config = GraphitiConfig(
            enabled=True,
            llm_provider="unknown_provider",
        )

        with pytest.raises(ProviderError) as exc_info:
            factory.create_llm_client(config)

        assert "Unknown LLM provider: unknown_provider" in str(exc_info.value)

    def test_create_llm_client_propagates_provider_not_installed(self):
        """Test ProviderNotInstalled is propagated from provider factory."""
        from integrations.graphiti.config import GraphitiConfig

        config = GraphitiConfig(
            enabled=True,
            llm_provider="openai",
            openai_api_key="sk-test",
        )

        with patch("integrations.graphiti.providers_pkg.factory.create_openai_llm_client") as mock_create:
            mock_create.side_effect = ProviderNotInstalled("Missing openai package")

            with pytest.raises(ProviderNotInstalled) as exc_info:
                factory.create_llm_client(config)

            assert "Missing openai package" in str(exc_info.value)

    def test_create_llm_client_propagates_provider_error(self):
        """Test ProviderError is propagated from provider factory."""
        from integrations.graphiti.config import GraphitiConfig

        config = GraphitiConfig(
            enabled=True,
            llm_provider="openai",
            openai_api_key="",  # Missing API key
        )

        with patch("integrations.graphiti.providers_pkg.factory.create_openai_llm_client") as mock_create:
            mock_create.side_effect = ProviderError("Missing API key")

            with pytest.raises(ProviderError) as exc_info:
                factory.create_llm_client(config)

            assert "Missing API key" in str(exc_info.value)


class TestCreateEmbedder:
    """Test create_embedder factory function."""

    def test_create_embedder_openai(self):
        """Test creating OpenAI embedder."""
        from integrations.graphiti.config import GraphitiConfig

        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openai",
            openai_api_key="sk-test",
            openai_embedding_model="text-embedding-3-small",
        )

        with patch("integrations.graphiti.providers_pkg.factory.create_openai_embedder") as mock_create:
            mock_embedder = MagicMock()
            mock_create.return_value = mock_embedder

            result = factory.create_embedder(config)

            assert result == mock_embedder
            mock_create.assert_called_once_with(config)

    def test_create_embedder_voyage(self):
        """Test creating Voyage embedder."""
        from integrations.graphiti.config import GraphitiConfig

        config = GraphitiConfig(
            enabled=True,
            embedder_provider="voyage",
            voyage_api_key="voyage-test",
        )

        with patch("integrations.graphiti.providers_pkg.factory.create_voyage_embedder") as mock_create:
            mock_embedder = MagicMock()
            mock_create.return_value = mock_embedder

            result = factory.create_embedder(config)

            assert result == mock_embedder
            mock_create.assert_called_once_with(config)

    def test_create_embedder_azure_openai(self):
        """Test creating Azure OpenAI embedder."""
        from integrations.graphiti.config import GraphitiConfig

        config = GraphitiConfig(
            enabled=True,
            embedder_provider="azure_openai",
            azure_openai_api_key="azure-test",
            azure_openai_base_url="https://test.openai.azure.com",
            azure_openai_embedding_deployment="embed-deployment",
        )

        with patch("integrations.graphiti.providers_pkg.factory.create_azure_openai_embedder") as mock_create:
            mock_embedder = MagicMock()
            mock_create.return_value = mock_embedder

            result = factory.create_embedder(config)

            assert result == mock_embedder
            mock_create.assert_called_once_with(config)

    def test_create_embedder_ollama(self):
        """Test creating Ollama embedder."""
        from integrations.graphiti.config import GraphitiConfig

        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_base_url="http://localhost:11434",
            ollama_embedding_model="nomic-embed-text",
            ollama_embedding_dim=768,
        )

        with patch("integrations.graphiti.providers_pkg.factory.create_ollama_embedder") as mock_create:
            mock_embedder = MagicMock()
            mock_create.return_value = mock_embedder

            result = factory.create_embedder(config)

            assert result == mock_embedder
            mock_create.assert_called_once_with(config)

    def test_create_embedder_google(self):
        """Test creating Google AI embedder."""
        from integrations.graphiti.config import GraphitiConfig

        config = GraphitiConfig(
            enabled=True,
            embedder_provider="google",
            google_api_key="google-test",
            google_embedding_model="text-embedding-004",
        )

        with patch("integrations.graphiti.providers_pkg.factory.create_google_embedder") as mock_create:
            mock_embedder = MagicMock()
            mock_create.return_value = mock_embedder

            result = factory.create_embedder(config)

            assert result == mock_embedder
            mock_create.assert_called_once_with(config)

    def test_create_embedder_openrouter(self):
        """Test creating OpenRouter embedder."""
        from integrations.graphiti.config import GraphitiConfig

        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openrouter",
            openrouter_api_key="or-test",
            openrouter_embedding_model="openai/text-embedding-3-small",
        )

        with patch("integrations.graphiti.providers_pkg.factory.create_openrouter_embedder") as mock_create:
            mock_embedder = MagicMock()
            mock_create.return_value = mock_embedder

            result = factory.create_embedder(config)

            assert result == mock_embedder
            mock_create.assert_called_once_with(config)

    def test_create_embedder_unknown_provider(self):
        """Test creating embedder for unknown provider raises error."""
        from integrations.graphiti.config import GraphitiConfig

        config = GraphitiConfig(
            enabled=True,
            embedder_provider="unknown_provider",
        )

        with pytest.raises(ProviderError) as exc_info:
            factory.create_embedder(config)

        assert "Unknown embedder provider: unknown_provider" in str(
            exc_info.value
        )

    def test_create_embedder_propagates_provider_not_installed(self):
        """Test ProviderNotInstalled is propagated from provider factory."""
        from integrations.graphiti.config import GraphitiConfig

        config = GraphitiConfig(
            enabled=True,
            embedder_provider="voyage",
            voyage_api_key="voyage-test",
        )

        with patch("integrations.graphiti.providers_pkg.factory.create_voyage_embedder") as mock_create:
            mock_create.side_effect = ProviderNotInstalled("Missing voyageai package")

            with pytest.raises(ProviderNotInstalled) as exc_info:
                factory.create_embedder(config)

            assert "Missing voyageai package" in str(exc_info.value)

    def test_create_embedder_propagates_provider_error(self):
        """Test ProviderError is propagated from provider factory."""
        from integrations.graphiti.config import GraphitiConfig

        config = GraphitiConfig(
            enabled=True,
            embedder_provider="voyage",
            voyage_api_key="",  # Missing API key
        )

        with patch("integrations.graphiti.providers_pkg.factory.create_voyage_embedder") as mock_create:
            mock_create.side_effect = ProviderError("Missing API key")

            with pytest.raises(ProviderError) as exc_info:
                factory.create_embedder(config)

            assert "Missing API key" in str(exc_info.value)


class TestAllProviderCombinations:
    """Test all supported LLM and embedder provider combinations."""

    def test_all_llm_providers_supported(self):
        """Test all LLM providers are routed correctly."""
        from integrations.graphiti.config import GraphitiConfig

        llm_providers = [
            "openai",
            "anthropic",
            "azure_openai",
            "ollama",
            "google",
            "openrouter",
        ]

        for provider in llm_providers:
            config = GraphitiConfig(enabled=True, llm_provider=provider)
            mock_func = f"create_{provider}_llm_client"

            with patch(f"integrations.graphiti.providers_pkg.factory.{mock_func}") as mock_create:
                mock_client = MagicMock()
                mock_create.return_value = mock_client

                result = factory.create_llm_client(config)

                assert result == mock_client, f"Failed for {provider}"
                mock_create.assert_called_once_with(config)

    def test_all_embedder_providers_supported(self):
        """Test all embedder providers are routed correctly."""
        from integrations.graphiti.config import GraphitiConfig

        embedder_providers = [
            "openai",
            "voyage",
            "azure_openai",
            "ollama",
            "google",
            "openrouter",
        ]

        for provider in embedder_providers:
            config = GraphitiConfig(enabled=True, embedder_provider=provider)
            mock_func = f"create_{provider}_embedder"

            with patch(f"integrations.graphiti.providers_pkg.factory.{mock_func}") as mock_create:
                mock_embedder = MagicMock()
                mock_create.return_value = mock_embedder

                result = factory.create_embedder(config)

                assert result == mock_embedder, f"Failed for {provider}"
                mock_create.assert_called_once_with(config)
