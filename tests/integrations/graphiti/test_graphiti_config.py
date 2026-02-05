"""Tests for graphiti config module."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from integrations.graphiti.config import (
    GraphitiConfig,
    GraphitiState,
    LLMProvider,
    EmbedderProvider,
    get_available_providers,
    get_graphiti_status,
    is_graphiti_enabled,
    validate_graphiti_config,
    DEFAULT_DATABASE,
    DEFAULT_DB_PATH,
    GRAPHITI_STATE_MARKER,
)


class TestGraphitiConfig:
    """Tests for GraphitiConfig class."""

    def test_default_values(self):
        """Test GraphitiConfig default values."""
        config = GraphitiConfig()

        assert config.enabled is False
        assert config.llm_provider == "openai"
        assert config.embedder_provider == "openai"
        assert config.database == DEFAULT_DATABASE
        assert config.db_path == DEFAULT_DB_PATH

    def test_from_env_disabled(self):
        """Test from_env when GRAPHITI_ENABLED is not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = GraphitiConfig.from_env()
            assert config.enabled is False

    def test_from_env_enabled_true(self):
        """Test from_env with GRAPHITI_ENABLED=true."""
        with patch.dict(os.environ, {"GRAPHITI_ENABLED": "true"}):
            config = GraphitiConfig.from_env()
            assert config.enabled is True

    def test_from_env_enabled_variants(self):
        """Test from_env with various enabled values."""
        for value in ["true", "TRUE", "1", "yes", "YES"]:
            with patch.dict(os.environ, {"GRAPHITI_ENABLED": value}):
                config = GraphitiConfig.from_env()
                assert config.enabled is True, f"Failed for value: {value}"

        for value in ["false", "FALSE", "0", "no", "NO", ""]:
            with patch.dict(os.environ, {"GRAPHITI_ENABLED": value}):
                config = GraphitiConfig.from_env()
                assert config.enabled is False, f"Failed for value: {value}"

    def test_from_env_provider_defaults(self):
        """Test from_env provider defaults."""
        with patch.dict(os.environ, {"GRAPHITI_ENABLED": "true"}):
            config = GraphitiConfig.from_env()
            assert config.llm_provider == "openai"
            assert config.embedder_provider == "openai"

    def test_from_env_custom_providers(self):
        """Test from_env with custom providers."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "GRAPHITI_LLM_PROVIDER": "anthropic",
            "GRAPHITI_EMBEDDER_PROVIDER": "ollama",
        }
        with patch.dict(os.environ, env):
            config = GraphitiConfig.from_env()
            assert config.llm_provider == "anthropic"
            assert config.embedder_provider == "ollama"

    def test_from_env_openai_settings(self):
        """Test from_env with OpenAI settings."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "OPENAI_API_KEY": "sk-test-key",
            "OPENAI_MODEL": "gpt-4",
            "OPENAI_EMBEDDING_MODEL": "text-embedding-3-large",
        }
        with patch.dict(os.environ, env):
            config = GraphitiConfig.from_env()
            assert config.openai_api_key == "sk-test-key"
            assert config.openai_model == "gpt-4"
            assert config.openai_embedding_model == "text-embedding-3-large"

    def test_from_env_anthropic_settings(self):
        """Test from_env with Anthropic settings."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "GRAPHITI_ANTHROPIC_MODEL": "claude-3-5-sonnet-20241022",
        }
        with patch.dict(os.environ, env):
            config = GraphitiConfig.from_env()
            assert config.anthropic_api_key == "sk-ant-test"
            assert config.anthropic_model == "claude-3-5-sonnet-20241022"

    def test_from_env_azure_settings(self):
        """Test from_env with Azure OpenAI settings."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "AZURE_OPENAI_API_KEY": "azure-key",
            "AZURE_OPENAI_BASE_URL": "https://test.openai.azure.com",
            "AZURE_OPENAI_LLM_DEPLOYMENT": "gpt-35-turbo",
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "text-embedding-ada-002",
        }
        with patch.dict(os.environ, env):
            config = GraphitiConfig.from_env()
            assert config.azure_openai_api_key == "azure-key"
            assert config.azure_openai_base_url == "https://test.openai.azure.com"
            assert config.azure_openai_llm_deployment == "gpt-35-turbo"
            assert config.azure_openai_embedding_deployment == "text-embedding-ada-002"

    def test_from_env_voyage_settings(self):
        """Test from_env with Voyage settings."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "VOYAGE_API_KEY": "voyage-key",
            "VOYAGE_EMBEDDING_MODEL": "voyage-2",
        }
        with patch.dict(os.environ, env):
            config = GraphitiConfig.from_env()
            assert config.voyage_api_key == "voyage-key"
            assert config.voyage_embedding_model == "voyage-2"

    def test_from_env_google_settings(self):
        """Test from_env with Google settings."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "GOOGLE_API_KEY": "google-key",
            "GOOGLE_LLM_MODEL": "gemini-pro",
            "GOOGLE_EMBEDDING_MODEL": "embedding-001",
        }
        with patch.dict(os.environ, env):
            config = GraphitiConfig.from_env()
            assert config.google_api_key == "google-key"
            assert config.google_llm_model == "gemini-pro"
            assert config.google_embedding_model == "embedding-001"

    def test_from_env_ollama_settings(self):
        """Test from_env with Ollama settings."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "OLLAMA_BASE_URL": "http://localhost:11434",
            "OLLAMA_LLM_MODEL": "llama3.2",
            "OLLAMA_EMBEDDING_MODEL": "nomic-embed-text",
            "OLLAMA_EMBEDDING_DIM": "768",
        }
        with patch.dict(os.environ, env):
            config = GraphitiConfig.from_env()
            assert config.ollama_base_url == "http://localhost:11434"
            assert config.ollama_llm_model == "llama3.2"
            assert config.ollama_embedding_model == "nomic-embed-text"
            assert config.ollama_embedding_dim == 768

    def test_from_env_openrouter_settings(self):
        """Test from_env with OpenRouter settings."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "OPENROUTER_API_KEY": "or-key",
            "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
            "OPENROUTER_LLM_MODEL": "anthropic/claude-3-5-sonnet",
            "OPENROUTER_EMBEDDING_MODEL": "openai/text-embedding-3-small",
        }
        with patch.dict(os.environ, env):
            config = GraphitiConfig.from_env()
            assert config.openrouter_api_key == "or-key"
            assert config.openrouter_base_url == "https://openrouter.ai/api/v1"
            assert config.openrouter_llm_model == "anthropic/claude-3-5-sonnet"
            assert config.openrouter_embedding_model == "openai/text-embedding-3-small"

    def test_from_env_database_settings(self):
        """Test from_env with database settings."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "GRAPHITI_DATABASE": "test_db",
            "GRAPHITI_DB_PATH": "/tmp/test",
        }
        with patch.dict(os.environ, env):
            config = GraphitiConfig.from_env()
            assert config.database == "test_db"
            assert config.db_path == "/tmp/test"

    def test_from_env_invalid_embedding_dim(self):
        """Test from_env with invalid embedding dimension."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "OLLAMA_EMBEDDING_DIM": "invalid",
        }
        with patch.dict(os.environ, env):
            config = GraphitiConfig.from_env()
            assert config.ollama_embedding_dim == 0

    def test_is_valid_disabled(self):
        """Test is_valid returns False when disabled."""
        config = GraphitiConfig(enabled=False)
        assert config.is_valid() is False

    def test_is_valid_enabled(self):
        """Test is_valid returns True when enabled."""
        config = GraphitiConfig(enabled=True)
        assert config.is_valid() is True

    def test_get_db_path(self, tmp_path: Path):
        """Test get_db_path expands tilde and creates parent."""
        config = GraphitiConfig(
            enabled=True,
            db_path="~/test_memories",
            database="test_db",
        )

        db_path = config.get_db_path()

        # Check path is expanded and includes database name
        assert db_path.name == "test_db"
        assert "test_memories" in str(db_path)

    def test_get_provider_summary(self):
        """Test get_provider_summary."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="openai",
            embedder_provider="voyage",
        )
        summary = config.get_provider_summary()
        assert summary == "LLM: openai, Embedder: voyage"

    def test_get_embedding_dimension_openai(self):
        """Test get_embedding_dimension for OpenAI."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openai",
        )
        assert config.get_embedding_dimension() == 1536

    def test_get_embedding_dimension_voyage(self):
        """Test get_embedding_dimension for Voyage."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="voyage",
        )
        assert config.get_embedding_dimension() == 1024

    def test_get_embedding_dimension_google(self):
        """Test get_embedding_dimension for Google."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="google",
        )
        assert config.get_embedding_dimension() == 768

    def test_get_embedding_dimension_azure_openai(self):
        """Test get_embedding_dimension for Azure OpenAI."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="azure_openai",
        )
        assert config.get_embedding_dimension() == 1536

    def test_get_embedding_dimension_ollama_custom(self):
        """Test get_embedding_dimension for Ollama with custom dimension."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_dim=1024,
        )
        assert config.get_embedding_dimension() == 1024

    def test_get_embedding_dimension_ollama_embeddinggemma(self):
        """Test get_embedding_dimension for Ollama embeddinggemma."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_model="embeddinggemma",
            ollama_embedding_dim=0,
        )
        assert config.get_embedding_dimension() == 768

    def test_get_embedding_dimension_ollama_nomic(self):
        """Test get_embedding_dimension for Ollama nomic-embed-text."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_model="nomic-embed-text",
            ollama_embedding_dim=0,
        )
        assert config.get_embedding_dimension() == 768

    def test_get_embedding_dimension_ollama_mxbai(self):
        """Test get_embedding_dimension for Ollama mxbai."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_model="mxbai-embed-large",
            ollama_embedding_dim=0,
        )
        assert config.get_embedding_dimension() == 1024

    def test_get_embedding_dimension_ollama_qwen3(self):
        """Test get_embedding_dimension for Ollama qwen3 variants."""
        # 0.6b
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_model="qwen3-embedding:0.6b",
            ollama_embedding_dim=0,
        )
        assert config.get_embedding_dimension() == 1024

        # 4b
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_model="qwen3-embedding:4b",
            ollama_embedding_dim=0,
        )
        assert config.get_embedding_dimension() == 2560

        # 8b
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_model="qwen3-embedding:8b",
            ollama_embedding_dim=0,
        )
        assert config.get_embedding_dimension() == 4096

    def test_get_embedding_dimension_openrouter(self):
        """Test get_embedding_dimension for OpenRouter."""
        # OpenAI via OpenRouter
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openrouter",
            openrouter_embedding_model="openai/text-embedding-3-small",
        )
        assert config.get_embedding_dimension() == 1536

        # Voyage via OpenRouter
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openrouter",
            openrouter_embedding_model="voyage/voyage-3",
        )
        assert config.get_embedding_dimension() == 1024

        # Google via OpenRouter
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openrouter",
            openrouter_embedding_model="google/text-embedding-004",
        )
        assert config.get_embedding_dimension() == 768

    def test_get_embedding_dimension_default(self):
        """Test get_embedding_dimension default fallback."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="unknown",
        )
        assert config.get_embedding_dimension() == 768

    def test_get_provider_signature_openai(self):
        """Test get_provider_signature for OpenAI."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openai",
        )
        assert config.get_provider_signature() == "openai_1536"

    def test_get_provider_signature_ollama(self):
        """Test get_provider_signature for Ollama."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_model="nomic-embed-text",
            ollama_embedding_dim=768,
        )
        signature = config.get_provider_signature()
        assert signature == "ollama_nomic-embed-text_768"

    def test_get_provider_signature_ollama_with_special_chars(self):
        """Test get_provider_signature for Ollama with special characters."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_model="llama3:2",
            ollama_embedding_dim=768,
        )
        signature = config.get_provider_signature()
        assert signature == "ollama_llama3_2_768"

    def test_get_provider_specific_database_name(self):
        """Test get_provider_specific_database_name."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openai",
            database="auto_claude_memory",
        )
        assert config.get_provider_specific_database_name() == "auto_claude_memory_openai_1536"

    def test_get_provider_specific_database_name_removes_old_suffix(self):
        """Test get_provider_specific_database_name removes old provider suffix."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="voyage",
            database="auto_claude_memory_openai_1536",
        )
        assert config.get_provider_specific_database_name() == "auto_claude_memory_voyage_1024"

    def test_get_provider_specific_database_name_custom_base(self):
        """Test get_provider_specific_database_name with custom base."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_model="test",
            ollama_embedding_dim=768,
        )
        assert config.get_provider_specific_database_name("my_db") == "my_db_ollama_test_768"

    def test_get_validation_errors_disabled(self):
        """Test get_validation_errors when disabled."""
        config = GraphitiConfig(enabled=False)
        errors = config.get_validation_errors()
        assert "GRAPHITI_ENABLED must be set to true" in errors

    def test_get_validation_errors_openai_no_key(self):
        """Test get_validation_errors for OpenAI without key."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openai",
            openai_api_key="",
        )
        errors = config.get_validation_errors()
        assert any("OPENAI_API_KEY" in e for e in errors)

    def test_get_validation_errors_voyage_no_key(self):
        """Test get_validation_errors for Voyage without key."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="voyage",
            voyage_api_key="",
        )
        errors = config.get_validation_errors()
        assert any("VOYAGE_API_KEY" in e for e in errors)

    def test_get_validation_errors_azure_missing_config(self):
        """Test get_validation_errors for Azure with missing config."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="azure_openai",
            azure_openai_api_key="",
            azure_openai_base_url="",
            azure_openai_embedding_deployment="",
        )
        errors = config.get_validation_errors()
        assert len(errors) >= 3
        assert any("AZURE_OPENAI_API_KEY" in e for e in errors)
        assert any("AZURE_OPENAI_BASE_URL" in e for e in errors)
        assert any("AZURE_OPENAI_EMBEDDING_DEPLOYMENT" in e for e in errors)

    def test_get_validation_errors_ollama_no_model(self):
        """Test get_validation_errors for Ollama without model."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_model="",
        )
        errors = config.get_validation_errors()
        assert any("OLLAMA_EMBEDDING_MODEL" in e for e in errors)

    def test_get_validation_errors_google_no_key(self):
        """Test get_validation_errors for Google without key."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="google",
            google_api_key="",
        )
        errors = config.get_validation_errors()
        assert any("GOOGLE_API_KEY" in e for e in errors)

    def test_get_validation_errors_openrouter_no_key(self):
        """Test get_validation_errors for OpenRouter without key."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openrouter",
            openrouter_api_key="",
        )
        errors = config.get_validation_errors()
        assert any("OPENROUTER_API_KEY" in e for e in errors)

    def test_get_validation_errors_unknown_provider(self):
        """Test get_validation_errors for unknown provider."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="unknown_provider",
        )
        errors = config.get_validation_errors()
        assert any("Unknown embedder provider" in e for e in errors)


class TestGraphitiState:
    """Tests for GraphitiState class."""

    def test_default_values(self):
        """Test GraphitiState default values."""
        state = GraphitiState()
        assert state.initialized is False
        assert state.database is None
        assert state.indices_built is False
        assert state.created_at is None
        assert state.last_session is None
        assert state.episode_count == 0
        assert state.error_log == []
        assert state.llm_provider is None
        assert state.embedder_provider is None

    def test_to_dict(self):
        """Test to_dict method."""
        state = GraphitiState(
            initialized=True,
            database="test_db",
            indices_built=True,
            created_at="2024-01-01T00:00:00",
            last_session=5,
            episode_count=10,
            error_log=[{"timestamp": "2024-01-01T00:00:00", "error": "test error"}],
            llm_provider="openai",
            embedder_provider="voyage",
        )
        data = state.to_dict()
        assert data["initialized"] is True
        assert data["database"] == "test_db"
        assert data["indices_built"] is True
        assert data["created_at"] == "2024-01-01T00:00:00"
        assert data["last_session"] == 5
        assert data["episode_count"] == 10
        assert len(data["error_log"]) == 1
        assert data["llm_provider"] == "openai"
        assert data["embedder_provider"] == "voyage"

    def test_to_dict_limits_error_log(self):
        """Test to_dict limits error log to 10 entries."""
        state = GraphitiState(
            error_log=[{"timestamp": f"2024-01-01T00:00:0{i}", "error": f"error {i}"} for i in range(15)]
        )
        data = state.to_dict()
        assert len(data["error_log"]) == 10

    def test_from_dict(self):
        """Test from_dict class method."""
        data = {
            "initialized": True,
            "database": "test_db",
            "indices_built": True,
            "created_at": "2024-01-01T00:00:00",
            "last_session": 5,
            "episode_count": 10,
            "error_log": [{"timestamp": "2024-01-01T00:00:00", "error": "test"}],
            "llm_provider": "openai",
            "embedder_provider": "voyage",
        }
        state = GraphitiState.from_dict(data)
        assert state.initialized is True
        assert state.database == "test_db"
        assert state.indices_built is True
        assert state.created_at == "2024-01-01T00:00:00"
        assert state.last_session == 5
        assert state.episode_count == 10
        assert len(state.error_log) == 1
        assert state.llm_provider == "openai"
        assert state.embedder_provider == "voyage"

    def test_from_dict_defaults(self):
        """Test from_dict with missing values uses defaults."""
        data = {}
        state = GraphitiState.from_dict(data)
        assert state.initialized is False
        assert state.database is None
        assert state.indices_built is False
        assert state.created_at is None
        assert state.last_session is None
        assert state.episode_count == 0
        assert state.error_log == []
        assert state.llm_provider is None
        assert state.embedder_provider is None

    def test_save(self, tmp_path: Path):
        """Test save method writes state file."""
        state = GraphitiState(
            initialized=True,
            database="test_db",
            llm_provider="openai",
            embedder_provider="voyage",
        )
        state.save(tmp_path)

        marker_file = tmp_path / GRAPHITI_STATE_MARKER
        assert marker_file.exists()

        with open(marker_file) as f:
            data = json.load(f)
            assert data["initialized"] is True
            assert data["database"] == "test_db"

    def test_load(self, tmp_path: Path):
        """Test load class method reads state file."""
        data = {
            "initialized": True,
            "database": "test_db",
            "indices_built": True,
            "created_at": "2024-01-01T00:00:00",
            "last_session": 5,
            "episode_count": 10,
            "error_log": [],
            "llm_provider": "openai",
            "embedder_provider": "voyage",
        }
        marker_file = tmp_path / GRAPHITI_STATE_MARKER
        with open(marker_file, "w") as f:
            json.dump(data, f)

        state = GraphitiState.load(tmp_path)
        assert state.initialized is True
        assert state.database == "test_db"
        assert state.llm_provider == "openai"
        assert state.embedder_provider == "voyage"

    def test_load_nonexistent(self, tmp_path: Path):
        """Test load returns None when file doesn't exist."""
        state = GraphitiState.load(tmp_path)
        assert state is None

    def test_load_invalid_json(self, tmp_path: Path):
        """Test load returns None with invalid JSON."""
        marker_file = tmp_path / GRAPHITI_STATE_MARKER
        with open(marker_file, "w") as f:
            f.write("invalid json")

        state = GraphitiState.load(tmp_path)
        assert state is None

    def test_record_error(self):
        """Test record_error method."""
        state = GraphitiState()
        state.record_error("Test error message")

        assert len(state.error_log) == 1
        assert state.error_log[0]["error"] == "Test error message"
        assert "timestamp" in state.error_log[0]

    def test_record_error_limits_length(self):
        """Test record_error limits error message length."""
        state = GraphitiState()
        long_error = "x" * 600
        state.record_error(long_error)

        assert len(state.error_log[0]["error"]) == 500

    def test_record_error_keeps_last_10(self):
        """Test record_error keeps only last 10 errors."""
        state = GraphitiState()
        for i in range(15):
            state.record_error(f"Error {i}")

        assert len(state.error_log) == 10
        assert state.error_log[0]["error"] == "Error 5"
        assert state.error_log[-1]["error"] == "Error 14"

    def test_has_provider_changed_not_initialized(self):
        """Test has_provider_changed when not initialized."""
        state = GraphitiState(initialized=False)
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="voyage",
        )
        assert state.has_provider_changed(config) is False

    def test_has_provider_changed_no_provider(self):
        """Test has_provider_changed when no provider set."""
        state = GraphitiState(
            initialized=True,
            embedder_provider=None,
        )
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="voyage",
        )
        assert state.has_provider_changed(config) is False

    def test_has_provider_changed_same(self):
        """Test has_provider_changed when same provider."""
        state = GraphitiState(
            initialized=True,
            embedder_provider="openai",
        )
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openai",
        )
        assert state.has_provider_changed(config) is False

    def test_has_provider_changed_different(self):
        """Test has_provider_changed when different provider."""
        state = GraphitiState(
            initialized=True,
            embedder_provider="openai",
        )
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="voyage",
        )
        assert state.has_provider_changed(config) is True

    def test_get_migration_info_no_change(self):
        """Test get_migration_info when no change."""
        state = GraphitiState(
            initialized=True,
            embedder_provider="openai",
            database="db",
            episode_count=5,
        )
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openai",
            database="db",
        )
        assert state.get_migration_info(config) is None

    def test_get_migration_info_with_change(self):
        """Test get_migration_info with provider change."""
        state = GraphitiState(
            initialized=True,
            embedder_provider="openai",
            database="db_openai",
            episode_count=10,
        )
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="voyage",
            database="db",
        )
        info = state.get_migration_info(config)
        assert info is not None
        assert info["old_provider"] == "openai"
        assert info["new_provider"] == "voyage"
        assert info["old_database"] == "db_openai"
        assert info["episode_count"] == 10
        assert info["requires_migration"] is True


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_is_graphiti_enabled_false(self):
        """Test is_graphiti_enabled returns False when not enabled."""
        with patch.dict(os.environ, {}, clear=True):
            assert is_graphiti_enabled() is False

    def test_is_graphiti_enabled_true(self):
        """Test is_graphiti_enabled returns True when enabled."""
        with patch.dict(os.environ, {"GRAPHITI_ENABLED": "true"}):
            assert is_graphiti_enabled() is True

    @patch("integrations.graphiti.config.GraphitiConfig.from_env")
    def test_get_graphiti_status_disabled(self, mock_from_env):
        """Test get_graphiti_status when disabled."""
        mock_from_env.return_value = GraphitiConfig(enabled=False)
        status = get_graphiti_status()
        assert status["enabled"] is False
        assert status["available"] is False
        assert "not set to true" in status["reason"]

    @patch("integrations.graphiti.config.GraphitiConfig.from_env")
    def test_get_graphiti_status_enabled_no_deps(self, mock_from_env):
        """Test get_graphiti_status when enabled but packages not available."""
        mock_from_env.return_value = GraphitiConfig(
            enabled=True,
            llm_provider="openai",
            embedder_provider="openai",
        )
        status = get_graphiti_status()
        assert status["enabled"] is True
        assert status["available"] is False
        assert "not installed" in status["reason"]

    @patch("integrations.graphiti.config.GraphitiConfig.from_env")
    def test_get_graphiti_status_fields(self, mock_from_env):
        """Test get_graphiti_status returns all expected fields."""
        mock_from_env.return_value = GraphitiConfig(
            enabled=True,
            database="test_db",
            db_path="/tmp/test",
            llm_provider="openai",
            embedder_provider="voyage",
        )
        status = get_graphiti_status()
        expected_keys = {
            "enabled",
            "available",
            "database",
            "db_path",
            "llm_provider",
            "embedder_provider",
            "reason",
            "errors",
        }
        assert set(status.keys()) == expected_keys

    def test_get_available_providers_empty(self):
        """Test get_available_providers with no configured providers."""
        with patch.dict(os.environ, {"GRAPHITI_ENABLED": "true"}):
            providers = get_available_providers()
            assert providers["llm_providers"] == []
            assert providers["embedder_providers"] == []

    def test_get_available_providers_openai(self):
        """Test get_available_providers detects OpenAI."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "OPENAI_API_KEY": "sk-test",
        }
        with patch.dict(os.environ, env):
            providers = get_available_providers()
            assert "openai" in providers["llm_providers"]
            assert "openai" in providers["embedder_providers"]

    def test_get_available_providers_anthropic(self):
        """Test get_available_providers detects Anthropic."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "ANTHROPIC_API_KEY": "sk-ant-test",
        }
        with patch.dict(os.environ, env):
            providers = get_available_providers()
            assert "anthropic" in providers["llm_providers"]

    def test_get_available_providers_azure(self):
        """Test get_available_providers detects Azure OpenAI."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "AZURE_OPENAI_API_KEY": "key",
            "AZURE_OPENAI_BASE_URL": "https://test",
            "AZURE_OPENAI_LLM_DEPLOYMENT": "llm",
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "embed",
        }
        with patch.dict(os.environ, env):
            providers = get_available_providers()
            assert "azure_openai" in providers["llm_providers"]
            assert "azure_openai" in providers["embedder_providers"]

    def test_get_available_providers_voyage(self):
        """Test get_available_providers detects Voyage."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "VOYAGE_API_KEY": "key",
        }
        with patch.dict(os.environ, env):
            providers = get_available_providers()
            assert "voyage" in providers["embedder_providers"]

    def test_get_available_providers_google(self):
        """Test get_available_providers detects Google."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "GOOGLE_API_KEY": "key",
        }
        with patch.dict(os.environ, env):
            providers = get_available_providers()
            assert "google" in providers["llm_providers"]
            assert "google" in providers["embedder_providers"]

    def test_get_available_providers_openrouter(self):
        """Test get_available_providers detects OpenRouter."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "OPENROUTER_API_KEY": "key",
        }
        with patch.dict(os.environ, env):
            providers = get_available_providers()
            assert "openrouter" in providers["llm_providers"]
            assert "openrouter" in providers["embedder_providers"]

    def test_get_available_providers_ollama(self):
        """Test get_available_providers detects Ollama."""
        env = {
            "GRAPHITI_ENABLED": "true",
            "OLLAMA_LLM_MODEL": "llama3",
            "OLLAMA_EMBEDDING_MODEL": "nomic",
            "OLLAMA_EMBEDDING_DIM": "768",
        }
        with patch.dict(os.environ, env):
            providers = get_available_providers()
            assert "ollama" in providers["llm_providers"]
            assert "ollama" in providers["embedder_providers"]

    def test_validate_graphiti_config_valid(self):
        """Test validate_graphiti_config returns valid."""
        with patch.dict(os.environ, {"GRAPHITI_ENABLED": "true"}):
            is_valid, errors = validate_graphiti_config()
            assert is_valid is True
            assert errors == []

    def test_validate_graphiti_config_invalid(self):
        """Test validate_graphiti_config returns invalid."""
        with patch.dict(os.environ, {}, clear=True):
            is_valid, errors = validate_graphiti_config()
            assert is_valid is False
            assert len(errors) > 0
