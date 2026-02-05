"""Comprehensive tests for validators.py module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from integrations.graphiti.config import GraphitiConfig
from integrations.graphiti.providers_pkg.exceptions import (
    ProviderError,
    ProviderNotInstalled,
)
from integrations.graphiti.providers_pkg import validators as validators_module
from integrations.graphiti.providers_pkg.validators import (
    validate_embedding_config,
)


class TestValidateEmbeddingConfig:
    """Tests for validate_embedding_config function."""

    def test_validate_ollama_with_dim_set(self):
        """Test Ollama config with dimension set is valid."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_model="nomic-embed-text",
            ollama_embedding_dim=768,
        )

        valid, msg = validate_embedding_config(config)

        assert valid is True
        assert "valid" in msg.lower()

    def test_validate_ollama_without_dim_known_model(self):
        """Test Ollama config without dimension for known model."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_model="nomic-embed-text",
            ollama_embedding_dim=0,
        )

        valid, msg = validate_embedding_config(config)

        assert valid is False
        assert "OLLAMA_EMBEDDING_DIM" in msg
        assert "768" in msg  # Expected dimension for nomic-embed-text

    def test_validate_ollama_without_dim_unknown_model(self):
        """Test Ollama config without dimension for unknown model."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_model="unknown-model",
            ollama_embedding_dim=0,
        )

        valid, msg = validate_embedding_config(config)

        assert valid is False
        assert "OLLAMA_EMBEDDING_DIM" in msg
        assert "documentation" in msg.lower()

    @patch("integrations.graphiti.providers_pkg.validators.logger")
    def test_validate_openai_logs_dimension(self, mock_logger):
        """Test OpenAI config logs expected dimension."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openai",
            openai_embedding_model="text-embedding-3-small",
        )

        valid, msg = validate_embedding_config(config)

        assert valid is True
        # Should log debug info about dimension
        assert mock_logger.debug.called

    @patch("integrations.graphiti.providers_pkg.validators.logger")
    def test_validate_voyage_logs_dimension(self, mock_logger):
        """Test Voyage config logs expected dimension."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="voyage",
            voyage_embedding_model="voyage-3",
        )

        valid, msg = validate_embedding_config(config)

        assert valid is True
        # Should log debug info about dimension
        assert mock_logger.debug.called

    def test_validate_google_provider(self):
        """Test Google provider passes validation."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="google",
            google_embedding_model="text-embedding-004",
        )

        valid, msg = validate_embedding_config(config)

        assert valid is True

    def test_validate_azure_openai_provider(self):
        """Test Azure OpenAI provider passes validation."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="azure_openai",
            azure_openai_embedding_deployment="embedding",
        )

        valid, msg = validate_embedding_config(config)

        assert valid is True

    def test_validate_openrouter_provider(self):
        """Test OpenRouter provider passes validation."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openrouter",
            openrouter_embedding_model="openai/text-embedding-3-small",
        )

        valid, msg = validate_embedding_config(config)

        assert valid is True


class TestTestLlmConnection:
    """Tests for test_llm_connection function."""

    @pytest.mark.asyncio
    async def test_test_llm_connection_success(self):
        """Test LLM connection with successful client creation."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="openai",
            openai_api_key="test-key",
        )

        with patch(
            "integrations.graphiti.providers_pkg.factory.create_llm_client",
            return_value=MagicMock(),
        ):
            success, msg = await validators_module.test_llm_connection(config)

            assert success is True
            assert "successfully" in msg.lower()
            assert "openai" in msg.lower()

    @pytest.mark.asyncio
    async def test_test_llm_connection_not_installed(self):
        """Test LLM connection with ProviderNotInstalled error."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="openai",
        )

        with patch(
            "integrations.graphiti.providers_pkg.factory.create_llm_client",
            side_effect=ProviderNotInstalled("openai package not installed"),
        ):
            success, msg = await validators_module.test_llm_connection(config)

            assert success is False
            assert "not installed" in msg.lower()

    @pytest.mark.asyncio
    async def test_test_llm_connection_provider_error(self):
        """Test LLM connection with ProviderError."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="openai",
        )

        with patch(
            "integrations.graphiti.providers_pkg.factory.create_llm_client",
            side_effect=ProviderError("Invalid API key"),
        ):
            success, msg = await validators_module.test_llm_connection(config)

            assert success is False
            assert "invalid" in msg.lower()

    @pytest.mark.asyncio
    async def test_test_llm_connection_generic_error(self):
        """Test LLM connection with generic exception."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="openai",
        )

        with patch(
            "integrations.graphiti.providers_pkg.factory.create_llm_client",
            side_effect=RuntimeError("Connection failed"),
        ):
            success, msg = await validators_module.test_llm_connection(config)

            assert success is False
            assert "failed to create" in msg.lower()


class TestTestEmbedderConnection:
    """Tests for test_embedder_connection function."""

    @pytest.mark.asyncio
    async def test_test_embedder_connection_success(self):
        """Test embedder connection with successful creation."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openai",
            openai_api_key="test-key",
            ollama_embedding_dim=768,
        )

        with patch(
            "integrations.graphiti.providers_pkg.validators.validate_embedding_config",
            return_value=(True, "Valid"),
        ):
            with patch(
                "integrations.graphiti.providers_pkg.factory.create_embedder",
                return_value=MagicMock(),
            ):
                success, msg = await validators_module.test_embedder_connection(config)

                assert success is True
                assert "successfully" in msg.lower()

    @pytest.mark.asyncio
    async def test_test_embedder_connection_invalid_config(self):
        """Test embedder connection with invalid config."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_dim=0,
        )

        with patch(
            "integrations.graphiti.providers_pkg.validators.validate_embedding_config",
            return_value=(False, "Missing dimension"),
        ):
            success, msg = await validators_module.test_embedder_connection(config)

            assert success is False
            assert "missing" in msg.lower()

    @pytest.mark.asyncio
    async def test_test_embedder_connection_not_installed(self):
        """Test embedder connection with ProviderNotInstalled."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="voyage",
        )

        with patch(
            "integrations.graphiti.providers_pkg.validators.validate_embedding_config",
            return_value=(True, "Valid"),
        ):
            with patch(
                "integrations.graphiti.providers_pkg.factory.create_embedder",
                side_effect=ProviderNotInstalled("voyage package not installed"),
            ):
                success, msg = await validators_module.test_embedder_connection(config)

                assert success is False

    @pytest.mark.asyncio
    async def test_test_embedder_connection_provider_error(self):
        """Test embedder connection with ProviderError."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openai",
        )

        with patch(
            "integrations.graphiti.providers_pkg.validators.validate_embedding_config",
            return_value=(True, "Valid"),
        ):
            with patch(
                "integrations.graphiti.providers_pkg.factory.create_embedder",
                side_effect=ProviderError("Invalid configuration"),
            ):
                success, msg = await validators_module.test_embedder_connection(config)

                assert success is False

    @pytest.mark.asyncio
    async def test_test_embedder_connection_generic_error(self):
        """Test embedder connection with generic exception."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="google",
        )

        with patch(
            "integrations.graphiti.providers_pkg.validators.validate_embedding_config",
            return_value=(True, "Valid"),
        ):
            with patch(
                "integrations.graphiti.providers_pkg.factory.create_embedder",
                side_effect=ValueError("Invalid API key format"),
            ):
                success, msg = await validators_module.test_embedder_connection(config)

                assert success is False
                assert "failed to create" in msg.lower()


class TestTestOllamaConnection:
    """Tests for test_ollama_connection function."""

    @pytest.mark.asyncio
    async def test_test_ollama_connection_success_aiohttp(self):
        """Test Ollama connection successful with aiohttp."""
        mock_response = MagicMock()
        mock_response.status = 200

        with patch.dict(
            "sys.modules",
            {"aiohttp": MagicMock()},
        ):
            mock_session = MagicMock()
            mock_get_result = MagicMock()
            mock_get_result.__aenter__ = AsyncMock(return_value=mock_response)
            mock_get_result.__aexit__ = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_get_result)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            with patch(
                "aiohttp.ClientSession",
                return_value=mock_session,
            ):
                success, msg = await validators_module.test_ollama_connection("http://localhost:11434")

                assert success is True
                assert "running" in msg.lower()

    @pytest.mark.asyncio
    async def test_test_ollama_connection_success_urllib(self):
        """Test Ollama connection successful with urllib fallback."""
        # Simulate aiohttp not available
        with patch.dict(
            "sys.modules",
            {"aiohttp": None},
        ):
            mock_response = MagicMock()
            mock_response.status = 200

            with patch(
                "urllib.request.urlopen",
                return_value=mock_response,
            ):
                success, msg = await validators_module.test_ollama_connection("http://localhost:11434")

                assert success is True
                assert "running" in msg.lower()

    @pytest.mark.asyncio
    async def test_test_ollama_connection_non_200_status(self):
        """Test Ollama connection with non-200 status."""
        mock_response = MagicMock()
        mock_response.status = 503

        with patch.dict(
            "sys.modules",
            {"aiohttp": MagicMock()},
        ):
            mock_session = MagicMock()
            mock_get_result = MagicMock()
            mock_get_result.__aenter__ = AsyncMock(return_value=mock_response)
            mock_get_result.__aexit__ = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_get_result)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            with patch(
                "aiohttp.ClientSession",
                return_value=mock_session,
            ):
                success, msg = await validators_module.test_ollama_connection("http://localhost:11434")

                assert success is False
                assert "503" in msg

    @pytest.mark.asyncio
    async def test_test_ollama_connection_timeout(self):
        """Test Ollama connection with timeout."""
        import asyncio

        with patch.dict(
            "sys.modules",
            {"aiohttp": MagicMock()},
        ):
            mock_session = MagicMock()
            mock_get_result = MagicMock()
            mock_get_result.__aenter__ = AsyncMock(
                side_effect=asyncio.TimeoutError()
            )
            mock_get_result.__aexit__ = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_get_result)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            with patch(
                "aiohttp.ClientSession",
                return_value=mock_session,
            ):
                success, msg = await validators_module.test_ollama_connection("http://localhost:11434")

                assert success is False
                assert "timed out" in msg.lower()

    @pytest.mark.asyncio
    async def test_test_ollama_connection_url_error(self):
        """Test Ollama connection with URL error."""
        import aiohttp

        with patch.dict(
            "sys.modules",
            {"aiohttp": MagicMock()},
        ):
            mock_session = MagicMock()
            mock_get_result = MagicMock()
            mock_get_result.__aenter__ = AsyncMock(
                side_effect=aiohttp.ClientError("Connection refused")
            )
            mock_get_result.__aexit__ = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_get_result)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            with patch(
                "aiohttp.ClientSession",
                return_value=mock_session,
            ):
                success, msg = await validators_module.test_ollama_connection("http://localhost:11434")

                assert success is False
                assert "cannot connect" in msg.lower()

    @pytest.mark.asyncio
    async def test_test_ollama_connection_url_normalization_v1_suffix(self):
        """Test Ollama connection URL normalization removes /v1 suffix."""
        mock_response = MagicMock()
        mock_response.status = 200

        with patch.dict(
            "sys.modules",
            {"aiohttp": MagicMock()},
        ):
            mock_session = MagicMock()
            mock_get_result = MagicMock()
            mock_get_result.__aenter__ = AsyncMock(return_value=mock_response)
            mock_get_result.__aexit__ = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_get_result)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            with patch(
                "aiohttp.ClientSession",
                return_value=mock_session,
            ):
                success, msg = await validators_module.test_ollama_connection("http://localhost:11434/v1")

                assert success is True
                # Verify /v1 was stripped from URL
                call_args = mock_session.get.call_args
                assert "/api/tags" in call_args[0][0]
                assert "/v1" not in call_args[0][0]

    @pytest.mark.asyncio
    async def test_test_ollama_connection_url_normalization_trailing_slash(self):
        """Test Ollama connection URL normalization handles trailing slash."""
        mock_response = MagicMock()
        mock_response.status = 200

        with patch.dict(
            "sys.modules",
            {"aiohttp": MagicMock()},
        ):
            mock_session = MagicMock()
            mock_get_result = MagicMock()
            mock_get_result.__aenter__ = AsyncMock(return_value=mock_response)
            mock_get_result.__aexit__ = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_get_result)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            with patch(
                "aiohttp.ClientSession",
                return_value=mock_session,
            ):
                success, msg = await validators_module.test_ollama_connection("http://localhost:11434/")

                assert success is True

    @pytest.mark.asyncio
    async def test_test_ollama_connection_default_url(self):
        """Test Ollama connection with default URL."""
        mock_response = MagicMock()
        mock_response.status = 200

        with patch.dict(
            "sys.modules",
            {"aiohttp": MagicMock()},
        ):
            mock_session = MagicMock()
            mock_get_result = MagicMock()
            mock_get_result.__aenter__ = AsyncMock(return_value=mock_response)
            mock_get_result.__aexit__ = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_get_result)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            with patch(
                "aiohttp.ClientSession",
                return_value=mock_session,
            ):
                success, msg = await validators_module.test_ollama_connection()

                assert success is True
                assert "localhost:11434" in msg

    @pytest.mark.asyncio
    async def test_test_ollama_connection_urllib_url_error(self):
        """Test Ollama connection with urllib URL error."""
        import urllib.error

        # Simulate aiohttp not available
        with patch.dict(
            "sys.modules",
            {"aiohttp": None},
        ):
            with patch(
                "urllib.request.urlopen",
                side_effect=urllib.error.URLError("Connection refused"),
            ):
                success, msg = await validators_module.test_ollama_connection("http://localhost:11434")

                assert success is False
                assert "cannot connect" in msg.lower()

    @pytest.mark.asyncio
    async def test_test_ollama_connection_urllib_generic_error(self):
        """Test Ollama connection with urllib generic error."""
        # Simulate aiohttp not available
        with patch.dict(
            "sys.modules",
            {"aiohttp": None},
        ):
            with patch(
                "urllib.request.urlopen",
                side_effect=ValueError("Some error"),
            ):
                success, msg = await validators_module.test_ollama_connection("http://localhost:11434")

                assert success is False
                assert "error" in msg.lower()

    @pytest.mark.asyncio
    async def test_test_ollama_connection_urllib_non_200_status(self):
        """Test Ollama connection with urllib returning non-200."""
        mock_response = MagicMock()
        mock_response.status = 404

        # Simulate aiohttp not available
        with patch.dict(
            "sys.modules",
            {"aiohttp": None},
        ):
            with patch(
                "urllib.request.urlopen",
                return_value=mock_response,
            ):
                success, msg = await validators_module.test_ollama_connection("http://localhost:11434")

                assert success is False
                assert "404" in msg
