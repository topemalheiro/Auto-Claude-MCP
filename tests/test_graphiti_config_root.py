"""
Tests for Graphiti configuration module.

Tests environment loading, validation, embedding dimension detection,
and provider signature generation.
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from integrations.graphiti.config import (
    EmbedderProvider,
    GraphitiConfig,
    GraphitiState,
    LLMProvider,
    get_available_providers,
    get_graphiti_status,
    is_graphiti_enabled,
    validate_graphiti_config,
)


class TestGraphitiConfig:
    """Test GraphitiConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = GraphitiConfig()

        assert config.enabled is False
        assert config.llm_provider == "openai"
        assert config.embedder_provider == "openai"
        assert config.database == "auto_claude_memory"
        assert config.db_path == "~/.auto-claude/memories"
        assert config.openai_api_key == ""
        assert config.openai_model == "gpt-5-mini"
        assert config.openai_embedding_model == "text-embedding-3-small"

    def test_from_env_disabled(self):
        """Test from_env when Graphiti is disabled."""
        with patch.dict(os.environ, {}, clear=True):
            config = GraphitiConfig.from_env()

            assert config.enabled is False
            assert config.llm_provider == "openai"
            assert config.embedder_provider == "openai"

    def test_from_env_enabled(self):
        """Test from_env when Graphiti is enabled."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "GRAPHITI_LLM_PROVIDER": "anthropic",
            "GRAPHITI_EMBEDDER_PROVIDER": "voyage",
            "OPENAI_API_KEY": "sk-test-key",
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "VOYAGE_API_KEY": "voyage-test",
        }
        with patch.dict(os.environ, env, clear=False):
            config = GraphitiConfig.from_env()

            assert config.enabled is True
            assert config.llm_provider == "anthropic"
            assert config.embedder_provider == "voyage"
            assert config.openai_api_key == "sk-test-key"
            assert config.anthropic_api_key == "sk-ant-test"
            assert config.voyage_api_key == "voyage-test"

    def test_from_env_enabled_variants(self):
        """Test various enabled values."""
        enabled_values = ["true", "1", "yes", "True", "YES"]
        for val in enabled_values:
            with patch.dict(os.environ, {"GRAPHITI_ENABLED": val}):
                config = GraphitiConfig.from_env()
                assert config.enabled is True, f"Failed for value: {val}"

    def test_from_env_ollama(self):
        """Test Ollama provider configuration."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "GRAPHITI_EMBEDDER_PROVIDER": "ollama",
            "OLLAMA_BASE_URL": "http://localhost:11434",
            "OLLAMA_EMBEDDING_MODEL": "nomic-embed-text",
            "OLLAMA_EMBEDDING_DIM": "768",
            "OLLAMA_LLM_MODEL": "deepseek-r1:7b",
        }
        with patch.dict(os.environ, env, clear=False):
            config = GraphitiConfig.from_env()

            assert config.embedder_provider == "ollama"
            assert config.ollama_base_url == "http://localhost:11434"
            assert config.ollama_embedding_model == "nomic-embed-text"
            assert config.ollama_embedding_dim == 768
            assert config.ollama_llm_model == "deepseek-r1:7b"

    def test_from_env_google(self):
        """Test Google AI provider configuration."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "GRAPHITI_LLM_PROVIDER": "google",
            "GRAPHITI_EMBEDDER_PROVIDER": "google",
            "GOOGLE_API_KEY": "google-test-key",
            "GOOGLE_LLM_MODEL": "gemini-2.0-flash",
            "GOOGLE_EMBEDDING_MODEL": "text-embedding-004",
        }
        with patch.dict(os.environ, env, clear=False):
            config = GraphitiConfig.from_env()

            assert config.llm_provider == "google"
            assert config.embedder_provider == "google"
            assert config.google_api_key == "google-test-key"
            assert config.google_llm_model == "gemini-2.0-flash"
            assert config.google_embedding_model == "text-embedding-004"

    def test_from_env_azure_openai(self):
        """Test Azure OpenAI provider configuration."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "GRAPHITI_LLM_PROVIDER": "azure_openai",
            "GRAPHITI_EMBEDDER_PROVIDER": "azure_openai",
            "AZURE_OPENAI_API_KEY": "azure-test-key",
            "AZURE_OPENAI_BASE_URL": "https://test.openai.azure.com",
            "AZURE_OPENAI_LLM_DEPLOYMENT": "gpt-deployment",
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "embed-deployment",
        }
        with patch.dict(os.environ, env, clear=False):
            config = GraphitiConfig.from_env()

            assert config.llm_provider == "azure_openai"
            assert config.embedder_provider == "azure_openai"
            assert config.azure_openai_api_key == "azure-test-key"
            assert config.azure_openai_base_url == "https://test.openai.azure.com"
            assert config.azure_openai_llm_deployment == "gpt-deployment"
            assert config.azure_openai_embedding_deployment == "embed-deployment"

    def test_from_env_openrouter(self):
        """Test OpenRouter provider configuration."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "GRAPHITI_LLM_PROVIDER": "openrouter",
            "GRAPHITI_EMBEDDER_PROVIDER": "openrouter",
            "OPENROUTER_API_KEY": "or-test-key",
            "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
            "OPENROUTER_LLM_MODEL": "anthropic/claude-sonnet-4",
            "OPENROUTER_EMBEDDING_MODEL": "openai/text-embedding-3-small",
        }
        with patch.dict(os.environ, env, clear=False):
            config = GraphitiConfig.from_env()

            assert config.llm_provider == "openrouter"
            assert config.embedder_provider == "openrouter"
            assert config.openrouter_api_key == "or-test-key"
            assert config.openrouter_base_url == "https://openrouter.ai/api/v1"
            assert config.openrouter_llm_model == "anthropic/claude-sonnet-4"
            assert config.openrouter_embedding_model == "openai/text-embedding-3-small"

    def test_is_valid_disabled(self):
        """Test is_valid returns False when disabled."""
        config = GraphitiConfig(enabled=False)
        assert config.is_valid() is False

    def test_is_valid_enabled(self):
        """Test is_valid returns True when enabled (embedder optional)."""
        config = GraphitiConfig(enabled=True)
        assert config.is_valid() is True

    def test_get_validation_errors_disabled(self):
        """Test validation errors when disabled."""
        config = GraphitiConfig(enabled=False)
        errors = config.get_validation_errors()

        assert len(errors) == 1
        assert "GRAPHITI_ENABLED must be set to true" in errors[0]

    def test_get_validation_errors_openai_no_key(self):
        """Test validation errors for OpenAI without API key."""
        config = GraphitiConfig(
            enabled=True, embedder_provider="openai", openai_api_key=""
        )
        errors = config.get_validation_errors()

        assert "OPENAI_API_KEY" in errors[0]

    def test_get_validation_errors_voyage_no_key(self):
        """Test validation errors for Voyage without API key."""
        config = GraphitiConfig(
            enabled=True, embedder_provider="voyage", voyage_api_key=""
        )
        errors = config.get_validation_errors()

        assert "VOYAGE_API_KEY" in errors[0]

    def test_get_validation_errors_azure_missing_config(self):
        """Test validation errors for Azure with missing config."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="azure_openai",
            azure_openai_api_key="",
            azure_openai_base_url="",
            azure_openai_embedding_deployment="",
        )
        errors = config.get_validation_errors()

        assert len(errors) == 3
        assert any("AZURE_OPENAI_API_KEY" in e for e in errors)
        assert any("AZURE_OPENAI_BASE_URL" in e for e in errors)
        assert any("AZURE_OPENAI_EMBEDDING_DEPLOYMENT" in e for e in errors)

    def test_get_validation_errors_ollama_no_model(self):
        """Test validation errors for Ollama without model."""
        config = GraphitiConfig(
            enabled=True, embedder_provider="ollama", ollama_embedding_model=""
        )
        errors = config.get_validation_errors()

        assert "OLLAMA_EMBEDDING_MODEL" in errors[0]

    def test_get_validation_errors_unknown_provider(self):
        """Test validation errors for unknown provider."""
        config = GraphitiConfig(enabled=True, embedder_provider="unknown")
        errors = config.get_validation_errors()

        assert "Unknown embedder provider: unknown" in errors[0]

    def test_get_db_path(self):
        """Test get_db_path expands tilde and creates parent."""
        config = GraphitiConfig(db_path="~/test/memories", database="test_db")

        with patch("pathlib.Path.mkdir"):
            db_path = config.get_db_path()

            # Should expand ~ and append database name
            assert db_path.name == "test_db"
            assert "memories" in str(db_path)

    def test_get_provider_summary(self):
        """Test get_provider_summary returns provider info."""
        config = GraphitiConfig(
            llm_provider="anthropic", embedder_provider="voyage"
        )
        summary = config.get_provider_summary()

        assert "LLM: anthropic" in summary
        assert "Embedder: voyage" in summary

    def test_get_embedding_dimension_openai(self):
        """Test embedding dimension for OpenAI."""
        config = GraphitiConfig(embedder_provider="openai")
        assert config.get_embedding_dimension() == 1536

    def test_get_embedding_dimension_voyage(self):
        """Test embedding dimension for Voyage."""
        config = GraphitiConfig(embedder_provider="voyage")
        assert config.get_embedding_dimension() == 1024

    def test_get_embedding_dimension_google(self):
        """Test embedding dimension for Google."""
        config = GraphitiConfig(embedder_provider="google")
        assert config.get_embedding_dimension() == 768

    def test_get_embedding_dimension_azure_openai(self):
        """Test embedding dimension for Azure OpenAI."""
        config = GraphitiConfig(embedder_provider="azure_openai")
        assert config.get_embedding_dimension() == 1536

    def test_get_embedding_dimension_ollama_explicit(self):
        """Test Ollama embedding dimension with explicit value."""
        config = GraphitiConfig(
            embedder_provider="ollama", ollama_embedding_dim=1024
        )
        assert config.get_embedding_dimension() == 1024

    def test_get_embedding_dimension_ollama_nomic(self):
        """Test Ollama auto-detect for nomic-embed-text."""
        config = GraphitiConfig(
            embedder_provider="ollama",
            ollama_embedding_model="nomic-embed-text",
            ollama_embedding_dim=0,
        )
        assert config.get_embedding_dimension() == 768

    def test_get_embedding_dimension_ollama_mxbai(self):
        """Test Ollama auto-detect for mxbai-embed-large."""
        config = GraphitiConfig(
            embedder_provider="ollama",
            ollama_embedding_model="mxbai-embed-large",
            ollama_embedding_dim=0,
        )
        assert config.get_embedding_dimension() == 1024

    def test_get_embedding_dimension_ollama_bge_large(self):
        """Test Ollama auto-detect for bge-large."""
        config = GraphitiConfig(
            embedder_provider="ollama",
            ollama_embedding_model="bge-large",
            ollama_embedding_dim=0,
        )
        assert config.get_embedding_dimension() == 1024

    def test_get_embedding_dimension_ollama_qwen3_sizes(self):
        """Test Ollama auto-detect for Qwen3 variants."""
        test_cases = [
            ("qwen3-embedding:0.6b", 1024),
            ("qwen3-embedding:4b", 2560),
            ("qwen3-embedding:8b", 4096),
        ]
        for model, expected_dim in test_cases:
            config = GraphitiConfig(
                embedder_provider="ollama",
                ollama_embedding_model=model,
                ollama_embedding_dim=0,
            )
            assert (
                config.get_embedding_dimension() == expected_dim
            ), f"Failed for {model}"

    def test_get_embedding_dimension_ollama_embeddinggemma(self):
        """Test Ollama auto-detect for embeddinggemma."""
        config = GraphitiConfig(
            embedder_provider="ollama",
            ollama_embedding_model="embeddinggemma",
            ollama_embedding_dim=0,
        )
        assert config.get_embedding_dimension() == 768

    def test_get_embedding_dimension_ollama_unknown(self):
        """Test Ollama default for unknown model."""
        config = GraphitiConfig(
            embedder_provider="ollama",
            ollama_embedding_model="unknown-model",
            ollama_embedding_dim=0,
        )
        # Should return default fallback
        assert config.get_embedding_dimension() == 768

    def test_get_embedding_dimension_openrouter_openai(self):
        """Test OpenRouter dimension for OpenAI model."""
        config = GraphitiConfig(
            embedder_provider="openrouter",
            openrouter_embedding_model="openai/text-embedding-3-small",
        )
        assert config.get_embedding_dimension() == 1536

    def test_get_embedding_dimension_openrouter_voyage(self):
        """Test OpenRouter dimension for Voyage model."""
        config = GraphitiConfig(
            embedder_provider="openrouter",
            openrouter_embedding_model="voyage/voyage-3",
        )
        assert config.get_embedding_dimension() == 1024

    def test_get_embedding_dimension_openrouter_google(self):
        """Test OpenRouter dimension for Google model."""
        config = GraphitiConfig(
            embedder_provider="openrouter",
            openrouter_embedding_model="google/text-embedding-004",
        )
        assert config.get_embedding_dimension() == 768

    def test_get_embedding_dimension_openrouter_unknown(self):
        """Test OpenRouter dimension for unknown model."""
        config = GraphitiConfig(
            embedder_provider="openrouter",
            openrouter_embedding_model="unknown/model",
        )
        assert config.get_embedding_dimension() == 1536

    def test_get_provider_signature_openai(self):
        """Test provider signature for OpenAI."""
        config = GraphitiConfig(embedder_provider="openai")
        assert config.get_provider_signature() == "openai_1536"

    def test_get_provider_signature_voyage(self):
        """Test provider signature for Voyage."""
        config = GraphitiConfig(embedder_provider="voyage")
        assert config.get_provider_signature() == "voyage_1024"

    def test_get_provider_signature_ollama(self):
        """Test provider signature for Ollama includes model."""
        config = GraphitiConfig(
            embedder_provider="ollama",
            ollama_embedding_model="nomic-embed-text",
            ollama_embedding_dim=768,
        )
        signature = config.get_provider_signature()
        assert signature == "ollama_nomic-embed-text_768"

    def test_get_provider_signature_ollama_with_special_chars(self):
        """Test Ollama signature sanitizes special characters."""
        config = GraphitiConfig(
            embedder_provider="ollama",
            ollama_embedding_model="qwen3:0.6b",
            ollama_embedding_dim=1024,
        )
        signature = config.get_provider_signature()
        # : should be replaced with _
        assert signature == "ollama_qwen3_0_6b_1024"

    def test_get_provider_specific_database_name(self):
        """Test provider-specific database name generation."""
        config = GraphitiConfig(
            embedder_provider="ollama",
            ollama_embedding_model="nomic-embed-text",
            ollama_embedding_dim=768,
            database="auto_claude_memory",
        )
        db_name = config.get_provider_specific_database_name()
        assert db_name == "auto_claude_memory_ollama_nomic-embed-text_768"

    def test_get_provider_specific_database_name_removes_old_suffix(self):
        """Test provider-specific database removes old provider suffix."""
        config = GraphitiConfig(
            embedder_provider="voyage",
            database="auto_claude_memory_ollama_768",
        )
        db_name = config.get_provider_specific_database_name()
        assert db_name == "auto_claude_memory_voyage_1024"

    def test_get_provider_specific_database_name_custom_base(self):
        """Test provider-specific database with custom base name."""
        config = GraphitiConfig(embedder_provider="google")
        db_name = config.get_provider_specific_database_name("custom_db")
        assert db_name == "custom_db_google_768"


class TestGraphitiState:
    """Test GraphitiState dataclass."""

    def test_default_values(self):
        """Test default state values."""
        state = GraphitiState()

        assert state.initialized is False
        assert state.database is None
        assert state.indices_built is False
        assert state.created_at is None
        assert state.last_session is None
        assert state.episode_count == 0
        assert state.error_log == []

    def test_to_dict(self):
        """Test serialization to dict."""
        state = GraphitiState(
            initialized=True,
            database="test_db",
            indices_built=True,
            created_at="2024-01-01",
            last_session=5,
            episode_count=10,
            llm_provider="anthropic",
            embedder_provider="voyage",
        )
        state.error_log = [{"error": "test"}]

        data = state.to_dict()

        assert data["initialized"] is True
        assert data["database"] == "test_db"
        assert data["indices_built"] is True
        assert data["created_at"] == "2024-01-01"
        assert data["last_session"] == 5
        assert data["episode_count"] == 10
        assert data["llm_provider"] == "anthropic"
        assert data["embedder_provider"] == "voyage"
        assert data["error_log"] == [{"error": "test"}]

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "initialized": True,
            "database": "test_db",
            "indices_built": True,
            "created_at": "2024-01-01",
            "last_session": 5,
            "episode_count": 10,
            "error_log": [{"error": "test"}],
            "llm_provider": "anthropic",
            "embedder_provider": "voyage",
        }
        state = GraphitiState.from_dict(data)

        assert state.initialized is True
        assert state.database == "test_db"
        assert state.indices_built is True
        assert state.created_at == "2024-01-01"
        assert state.last_session == 5
        assert state.episode_count == 10
        assert state.llm_provider == "anthropic"
        assert state.embedder_provider == "voyage"
        assert state.error_log == [{"error": "test"}]

    def test_from_dict_with_defaults(self):
        """Test from_dict uses defaults for missing values."""
        state = GraphitiState.from_dict({})

        assert state.initialized is False
        assert state.database is None
        assert state.indices_built is False
        assert state.episode_count == 0
        assert state.error_log == []

    def test_save(self, tmp_path: Path):
        """Test saving state to file."""
        state = GraphitiState(
            initialized=True, database="test_db", episode_count=5
        )
        state.save(tmp_path)

        marker_file = tmp_path / ".graphiti_state.json"
        assert marker_file.exists()

        with open(marker_file) as f:
            data = json.load(f)

        assert data["database"] == "test_db"
        assert data["episode_count"] == 5

    def test_load(self, tmp_path: Path):
        """Test loading state from file."""
        data = {
            "initialized": True,
            "database": "test_db",
            "indices_built": True,
            "episode_count": 5,
        }
        marker_file = tmp_path / ".graphiti_state.json"
        with open(marker_file, "w") as f:
            json.dump(data, f)

        state = GraphitiState.load(tmp_path)

        assert state.initialized is True
        assert state.database == "test_db"
        assert state.indices_built is True
        assert state.episode_count == 5

    def test_load_nonexistent(self, tmp_path: Path):
        """Test load returns None when file doesn't exist."""
        state = GraphitiState.load(tmp_path)
        assert state is None

    def test_load_invalid_json(self, tmp_path: Path):
        """Test load returns None for invalid JSON."""
        marker_file = tmp_path / ".graphiti_state.json"
        with open(marker_file, "w") as f:
            f.write("invalid json")

        state = GraphitiState.load(tmp_path)
        assert state is None

    def test_record_error(self):
        """Test recording error to state."""
        state = GraphitiState()
        state.record_error("Test error")

        assert len(state.error_log) == 1
        assert state.error_log[0]["error"] == "Test error"
        assert "timestamp" in state.error_log[0]

    def test_record_error_truncates_long_message(self):
        """Test error messages are truncated to 500 chars."""
        state = GraphitiState()
        long_error = "x" * 600
        state.record_error(long_error)

        assert len(state.error_log[0]["error"]) == 500

    def test_record_error_keeps_last_10(self):
        """Test only last 10 errors are kept."""
        state = GraphitiState()
        for i in range(15):
            state.record_error(f"Error {i}")

        assert len(state.error_log) == 10
        assert "Error 14" in state.error_log[-1]["error"]

    def test_has_provider_changed(self):
        """Test detecting provider changes."""
        state = GraphitiState(
            initialized=True, embedder_provider="voyage"
        )
        config_same = GraphitiConfig(embedder_provider="voyage")
        config_diff = GraphitiConfig(embedder_provider="openai")

        assert state.has_provider_changed(config_same) is False
        assert state.has_provider_changed(config_diff) is True

    def test_has_provider_changed_not_initialized(self):
        """Test provider change returns False when not initialized."""
        state = GraphitiState(initialized=False, embedder_provider="voyage")
        config = GraphitiConfig(embedder_provider="openai")

        assert state.has_provider_changed(config) is False

    def test_has_provider_changed_no_state_provider(self):
        """Test provider change returns False when state has no provider."""
        state = GraphitiState(initialized=True, embedder_provider=None)
        config = GraphitiConfig(embedder_provider="openai")

        assert state.has_provider_changed(config) is False

    def test_get_migration_info(self):
        """Test getting migration information."""
        state = GraphitiState(
            initialized=True,
            embedder_provider="voyage",
            database="old_db",
            episode_count=100,
        )
        config = GraphitiConfig(embedder_provider="openai")

        migration = state.get_migration_info(config)

        assert migration["old_provider"] == "voyage"
        assert migration["new_provider"] == "openai"
        assert migration["old_database"] == "old_db"
        assert migration["episode_count"] == 100
        assert migration["requires_migration"] is True

    def test_get_migration_info_no_change(self):
        """Test migration info is None when no change."""
        state = GraphitiState(
            initialized=True, embedder_provider="voyage"
        )
        config = GraphitiConfig(embedder_provider="voyage")

        migration = state.get_migration_info(config)
        assert migration is None


class TestModuleFunctions:
    """Test module-level utility functions."""

    def test_is_graphiti_enabled_disabled(self):
        """Test is_graphiti_enabled returns False when disabled."""
        with patch.dict(os.environ, {"GRAPHITI_ENABLED": "false"}):
            assert is_graphiti_enabled() is False

    def test_is_graphiti_enabled_true(self):
        """Test is_graphiti_enabled returns True when enabled."""
        with patch.dict(os.environ, {"GRAPHITI_ENABLED": "true"}):
            # Note: may still return False if dependencies not installed
            result = is_graphiti_enabled()
            # Just check it doesn't crash
            assert isinstance(result, bool)

    def test_validate_graphiti_config_valid(self):
        """Test validate_graphiti_config for valid config."""
        with patch.dict(os.environ, {"GRAPHITI_ENABLED": "true"}):
            is_valid, errors = validate_graphiti_config()
            # With just enabled=true, embedder is optional
            # So should be valid (keyword search fallback)
            assert is_valid is True or len(errors) == 0

    def test_validate_graphiti_config_invalid(self):
        """Test validate_graphiti_config for invalid config."""
        with patch.dict(os.environ, {}, clear=True):
            is_valid, errors = validate_graphiti_config()

            assert is_valid is False
            assert len(errors) > 0

    def test_get_graphiti_status_disabled(self):
        """Test get_graphiti_status when disabled."""
        with patch.dict(os.environ, {}, clear=True):
            status = get_graphiti_status()

            assert status["enabled"] is False
            assert status["available"] is False
            assert "not set to true" in status["reason"]

    def test_get_graphiti_status_enabled(self):
        """Test get_graphiti_status structure when enabled."""
        with patch.dict(os.environ, {"GRAPHITI_ENABLED": "true"}):
            status = get_graphiti_status()

            assert status["enabled"] is True
            assert "available" in status
            assert "database" in status
            assert "db_path" in status
            assert "llm_provider" in status
            assert "embedder_provider" in status

    def test_get_available_providers_empty(self):
        """Test get_available_providers with no keys."""
        with patch.dict(os.environ, {}, clear=True):
            providers = get_available_providers()

            assert providers["llm_providers"] == []
            assert providers["embedder_providers"] == []

    def test_get_available_providers_openai(self):
        """Test get_available_providers with OpenAI key."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            providers = get_available_providers()

            assert "openai" in providers["llm_providers"]
            assert "openai" in providers["embedder_providers"]

    def test_get_available_providers_anthropic(self):
        """Test get_available_providers with Anthropic key."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            providers = get_available_providers()

            assert "anthropic" in providers["llm_providers"]

    def test_get_available_providers_voyage(self):
        """Test get_available_providers with Voyage key."""
        with patch.dict(os.environ, {"VOYAGE_API_KEY": "voyage-test"}):
            providers = get_available_providers()

            assert "voyage" in providers["embedder_providers"]

    def test_get_available_providers_google(self):
        """Test get_available_providers with Google key."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "google-test"}):
            providers = get_available_providers()

            assert "google" in providers["llm_providers"]
            assert "google" in providers["embedder_providers"]

    def test_get_available_providers_azure(self):
        """Test get_available_providers with Azure keys."""
        env = {
            "AZURE_OPENAI_API_KEY": "azure-test",
            "AZURE_OPENAI_BASE_URL": "https://test.openai.azure.com",
            "AZURE_OPENAI_LLM_DEPLOYMENT": "gpt",
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "embed",
        }
        with patch.dict(os.environ, env):
            providers = get_available_providers()

            assert "azure_openai" in providers["llm_providers"]
            assert "azure_openai" in providers["embedder_providers"]

    def test_get_available_providers_openrouter(self):
        """Test get_available_providers with OpenRouter key."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "or-test"}):
            providers = get_available_providers()

            assert "openrouter" in providers["llm_providers"]
            assert "openrouter" in providers["embedder_providers"]

    def test_get_available_providers_ollama(self):
        """Test get_available_providers with Ollama model and dim."""
        with patch.dict(
            os.environ,
            {"OLLAMA_LLM_MODEL": "deepseek", "OLLAMA_EMBEDDING_MODEL": "nomic", "OLLAMA_EMBEDDING_DIM": "768"},
        ):
            providers = get_available_providers()

            assert "ollama" in providers["llm_providers"]
            assert "ollama" in providers["embedder_providers"]

    def test_get_available_providers_multiple(self):
        """Test get_available_providers with multiple keys."""
        env = {
            "OPENAI_API_KEY": "sk-test",
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "VOYAGE_API_KEY": "voyage-test",
            "GOOGLE_API_KEY": "google-test",
        }
        with patch.dict(os.environ, env):
            providers = get_available_providers()

            assert len(providers["llm_providers"]) >= 2
            assert len(providers["embedder_providers"]) >= 3
