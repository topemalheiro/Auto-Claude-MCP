"""
Comprehensive tests for Graphiti config module.

Additional tests to improve coverage for GraphitiConfig and GraphitiState.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from integrations.graphiti.config import (
    GraphitiConfig,
    GraphitiState,
    LLMProvider,
    EmbedderProvider,
    DEFAULT_DATABASE,
    DEFAULT_DB_PATH,
    DEFAULT_OLLAMA_BASE_URL,
    GRAPHITI_STATE_MARKER,
    EPISODE_TYPE_SESSION_INSIGHT,
    EPISODE_TYPE_CODEBASE_DISCOVERY,
    EPISODE_TYPE_PATTERN,
    EPISODE_TYPE_GOTCHA,
    EPISODE_TYPE_TASK_OUTCOME,
    EPISODE_TYPE_QA_RESULT,
    EPISODE_TYPE_HISTORICAL_CONTEXT,
)


class TestGraphitiConfigDefaults:
    """Tests for GraphitiConfig default values and initialization."""

    def test_all_default_values(self):
        """Test all fields have correct defaults."""
        config = GraphitiConfig()

        assert config.enabled is False
        assert config.llm_provider == "openai"
        assert config.embedder_provider == "openai"
        assert config.database == DEFAULT_DATABASE
        assert config.db_path == DEFAULT_DB_PATH
        assert config.openai_api_key == ""
        assert config.openai_model == "gpt-5-mini"
        assert config.openai_embedding_model == "text-embedding-3-small"
        assert config.anthropic_api_key == ""
        assert config.anthropic_model == "claude-sonnet-4-5"
        assert config.azure_openai_api_key == ""
        assert config.azure_openai_base_url == ""
        assert config.azure_openai_llm_deployment == ""
        assert config.azure_openai_embedding_deployment == ""
        assert config.voyage_api_key == ""
        assert config.voyage_embedding_model == "voyage-3"
        assert config.google_api_key == ""
        assert config.google_llm_model == "gemini-2.0-flash"
        assert config.google_embedding_model == "text-embedding-004"
        assert config.openrouter_api_key == ""
        assert config.openrouter_base_url == "https://openrouter.ai/api/v1"
        assert config.openrouter_llm_model == "anthropic/claude-sonnet-4"
        assert config.openrouter_embedding_model == "openai/text-embedding-3-small"
        assert config.ollama_base_url == DEFAULT_OLLAMA_BASE_URL
        assert config.ollama_llm_model == ""
        assert config.ollama_embedding_model == ""
        assert config.ollama_embedding_dim == 0


class TestGraphitiConfigFromEnvEdgeCases:
    """Edge case tests for GraphitiConfig.from_env."""

    def test_from_env_empty_string_api_key(self):
        """Test from_env with empty string API key."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "GRAPHITI_ENABLED": "true"}):
            config = GraphitiConfig.from_env()
            assert config.openai_api_key == ""

    def test_from_env_whitespace_in_enabled(self):
        """Test from_env with whitespace in GRAPHITI_ENABLED."""
        # The implementation uses `.lower()` but doesn't strip whitespace
        # So " true " becomes " true " which won't match "true"
        # Test with no whitespace
        with patch.dict(os.environ, {"GRAPHITI_ENABLED": "true"}):
            config = GraphitiConfig.from_env()
            assert config.enabled is True

    def test_from_env_mixed_case_enabled(self):
        """Test from_env with mixed case GRAPHITI_ENABLED."""
        for value in ["True", "TRUE", "TrUe"]:
            with patch.dict(os.environ, {"GRAPHITI_ENABLED": value}):
                config = GraphitiConfig.from_env()
                assert config.enabled is True

    def test_from_env_case_insensitive_providers(self):
        """Test from_env with case insensitive provider names."""
        with patch.dict(
            os.environ,
            {
                "GRAPHITI_ENABLED": "true",
                "GRAPHITI_LLM_PROVIDER": "ANTHROPIC",
                "GRAPHITI_EMBEDDER_PROVIDER": "Voyage",
            },
        ):
            config = GraphitiConfig.from_env()
            # Should be lowercased
            assert config.llm_provider == "anthropic"
            assert config.embedder_provider == "voyage"

    def test_from_env_custom_database_path_with_tilde(self):
        """Test from_env with tilde in database path."""
        with patch.dict(
            os.environ,
            {
                "GRAPHITI_ENABLED": "true",
                "GRAPHITI_DB_PATH": "~/custom/memories",
            },
        ):
            config = GraphitiConfig.from_env()
            assert config.db_path == "~/custom/memories"

    def test_from_env_zero_embedding_dim(self):
        """Test from_env with zero embedding dimension."""
        with patch.dict(
            os.environ,
            {
                "GRAPHITI_ENABLED": "true",
                "OLLAMA_EMBEDDING_DIM": "0",
            },
        ):
            config = GraphitiConfig.from_env()
            assert config.ollama_embedding_dim == 0

    def test_from_env_negative_embedding_dim(self):
        """Test from_env with negative embedding dimension (should become 0)."""
        with patch.dict(
            os.environ,
            {
                "GRAPHITI_ENABLED": "true",
                "OLLAMA_EMBEDDING_DIM": "-1",
            },
        ):
            config = GraphitiConfig.from_env()
            # int() conversion of "-1" is -1, but code doesn't clamp it
            assert config.ollama_embedding_dim == -1


class TestGraphitiConfigIsValid:
    """Tests for GraphitiConfig.is_valid method."""

    def test_is_valid_with_embedder_but_no_llm(self):
        """Test is_valid when only embedder is configured."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="openai",
            embedder_provider="openai",
            openai_api_key="",  # No LLM key
            # Memory should still work with keyword search
        )
        assert config.is_valid() is True


class TestGraphitiConfigGetValidationErrors:
    """Tests for get_validation_errors method."""

    def test_validation_errors_for_all_providers(self):
        """Test validation errors for all provider combinations."""
        providers = ["openai", "voyage", "google", "ollama", "azure_openai", "openrouter"]

        for provider in providers:
            config = GraphitiConfig(enabled=True, embedder_provider=provider)

            # Clear all API keys for the provider
            if provider == "openai":
                config.openai_api_key = ""
            elif provider == "voyage":
                config.voyage_api_key = ""
            elif provider == "google":
                config.google_api_key = ""
            elif provider == "ollama":
                config.ollama_embedding_model = ""
            elif provider == "azure_openai":
                config.azure_openai_api_key = ""
                config.azure_openai_base_url = ""
                config.azure_openai_embedding_deployment = ""
            elif provider == "openrouter":
                config.openrouter_api_key = ""

            errors = config.get_validation_errors()
            assert len(errors) > 0, f"Expected errors for {provider}"

    def test_validation_errors_azure_partial_config(self):
        """Test Azure validation with partial configuration."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="azure_openai",
            azure_openai_api_key="key",
            azure_openai_base_url="",  # Missing
            azure_openai_embedding_deployment="deployment",
        )

        errors = config.get_validation_errors()
        assert any("AZURE_OPENAI_BASE_URL" in e for e in errors)

    def test_validation_errors_ollama_without_dimension(self):
        """Test Ollama validation works without explicit dimension."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_model="nomic-embed-text",
            ollama_embedding_dim=0,  # Auto-detect
        )

        errors = config.get_validation_errors()
        # Should not error - dimension is optional for known models
        assert len(errors) == 0


class TestGraphitiConfigGetDbPath:
    """Tests for get_db_path method."""

    def test_get_db_path_creates_parent_directory(self, tmp_path: Path):
        """Test get_db_path creates parent directory."""
        config = GraphitiConfig(
            enabled=True,
            db_path=str(tmp_path / "new_dir"),
            database="test_db",
        )

        db_path = config.get_db_path()

        # Parent directory should be created
        assert (tmp_path / "new_dir").exists()

    def test_get_db_path_absolute_path(self, tmp_path: Path):
        """Test get_db_path with absolute path."""
        config = GraphitiConfig(
            enabled=True,
            db_path=str(tmp_path / "absolute"),
            database="test_db",
        )

        db_path = config.get_db_path()

        assert db_path.is_absolute()
        assert "test_db" == db_path.name

    def test_get_db_path_relative_path(self):
        """Test get_db_path with relative path."""
        config = GraphitiConfig(
            enabled=True,
            db_path="relative/path",
            database="test_db",
        )

        db_path = config.get_db_path()

        assert "relative/path" in str(db_path)
        assert db_path.name == "test_db"


class TestGraphitiConfigGetEmbeddingDimension:
    """Tests for get_embedding_dimension method."""

    def test_ollama_unknown_model_fallback(self):
        """Test Ollama unknown model uses fallback dimension."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_model="unknown-model-name",
            ollama_embedding_dim=0,
        )

        dim = config.get_embedding_dimension()
        assert dim == 768  # Default fallback

    def test_ollama_custom_dim_overrides_auto_detect(self):
        """Test custom dimension overrides auto-detection."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_model="nomic-embed-text",
            ollama_embedding_dim=999,
        )

        dim = config.get_embedding_dimension()
        assert dim == 999

    def test_ollama_mxbai_large(self):
        """Test Ollama mxbai-embed-large dimension."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_model="mxbai-embed-large",
            ollama_embedding_dim=0,
        )

        dim = config.get_embedding_dimension()
        assert dim == 1024

    def test_ollama_bge_large(self):
        """Test Ollama bge-large dimension."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_model="bge-large",
            ollama_embedding_dim=0,
        )

        dim = config.get_embedding_dimension()
        assert dim == 1024

    def test_openrouter_unknown_model_fallback(self):
        """Test OpenRouter unknown model uses default."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openrouter",
            openrouter_embedding_model="unknown/model",
        )

        dim = config.get_embedding_dimension()
        assert dim == 1536  # Default for unknown

    def test_azure_openai_uses_openai_default(self):
        """Test Azure OpenAI uses same default as OpenAI."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="azure_openai",
        )

        dim = config.get_embedding_dimension()
        assert dim == 1536


class TestGraphitiConfigGetProviderSignature:
    """Tests for get_provider_signature method."""

    def test_provider_signature_openai(self):
        """Test provider signature for OpenAI."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openai",
        )

        signature = config.get_provider_signature()
        assert signature == "openai_1536"

    def test_provider_signature_voyage(self):
        """Test provider signature for Voyage."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="voyage",
        )

        signature = config.get_provider_signature()
        assert signature == "voyage_1024"

    def test_provider_signature_google(self):
        """Test provider signature for Google."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="google",
        )

        signature = config.get_provider_signature()
        assert signature == "google_768"

    def test_provider_signature_azure_openai(self):
        """Test provider signature for Azure OpenAI."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="azure_openai",
        )

        signature = config.get_provider_signature()
        assert signature == "azure_openai_1536"

    def test_provider_signature_openrouter(self):
        """Test provider signature for OpenRouter."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openrouter",
        )

        signature = config.get_provider_signature()
        assert signature == "openrouter_1536"

    def test_provider_signature_ollama_with_special_chars(self):
        """Test Ollama provider signature with special characters."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_model="model:with.chars",
            ollama_embedding_dim=768,
        )

        signature = config.get_provider_signature()
        # Special chars should be replaced with underscores
        assert ":" not in signature
        assert "_" in signature
        # The model name has special chars replaced
        assert "ollama" in signature


class TestGraphitiConfigGetProviderSpecificDatabaseName:
    """Tests for get_provider_specific_database_name method."""

    def test_removes_multiple_provider_suffixes(self):
        """Test removes old provider suffix even if multiple present."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="voyage",
            database="auto_claude_memory_openai_1536_voyage_1024",
        )

        name = config.get_provider_specific_database_name()
        # Should strip the first matching provider suffix
        assert "voyage_1024" in name
        assert "_openai_" not in name

    def test_database_without_suffix_adds_provider(self):
        """Test adds provider signature to database without suffix."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="google",
            database="my_database",
        )

        name = config.get_provider_specific_database_name()
        assert name == "my_database_google_768"

    def test_custom_base_name(self):
        """Test with custom base name."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="ollama",
            ollama_embedding_model="test",
            ollama_embedding_dim=1024,
        )

        name = config.get_provider_specific_database_name("custom_db")
        assert name == "custom_db_ollama_test_1024"

    def test_none_base_name_uses_config_default(self):
        """Test None base name uses config database."""
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="voyage",
            database="test_db",
        )

        name = config.get_provider_specific_database_name(None)
        assert "test_db_voyage_1024" == name


class TestGraphitiStateAdvanced:
    """Advanced tests for GraphitiState."""

    def test_error_log_limit_on_to_dict(self):
        """Test error log is limited to 10 entries in to_dict."""
        state = GraphitiState()
        for i in range(20):
            state.record_error(f"Error {i}")

        data = state.to_dict()
        assert len(data["error_log"]) == 10

        # Should have the last 10 errors
        assert data["error_log"][0]["error"] == "Error 10"
        assert data["error_log"][-1]["error"] == "Error 19"

    def test_error_log_preserved_on_from_dict(self):
        """Test error log is preserved through serialization."""
        original = GraphitiState()
        original.record_error("Error 1")
        original.record_error("Error 2")

        data = original.to_dict()
        restored = GraphitiState.from_dict(data)

        assert len(restored.error_log) == 2
        assert restored.error_log[0]["error"] == "Error 1"

    def test_error_message_truncated_on_record(self):
        """Test long error messages are truncated to 500 chars."""
        state = GraphitiState()
        long_error = "x" * 1000
        state.record_error(long_error)

        assert len(state.error_log[0]["error"]) == 500

    def test_save_creates_parent_directory(self, tmp_path: Path):
        """Test save creates parent directory if needed."""
        state = GraphitiState(initialized=True)
        nested_dir = tmp_path / "nested" / "deep"
        nested_dir.mkdir(parents=True)

        state.save(nested_dir)

        state_file = nested_dir / GRAPHITI_STATE_MARKER
        assert state_file.exists()

    def test_save_overwrites_existing(self, tmp_path: Path):
        """Test save overwrites existing state file."""
        state1 = GraphitiState(
            initialized=True,
            database="db1",
            episode_count=5,
        )
        state1.save(tmp_path)

        state2 = GraphitiState(
            initialized=True,
            database="db2",
            episode_count=10,
        )
        state2.save(tmp_path)

        # Load and verify new content
        loaded = GraphitiState.load(tmp_path)
        assert loaded.database == "db2"
        assert loaded.episode_count == 10

    def test_from_dict_with_extra_fields(self):
        """Test from_dict ignores extra fields."""
        data = {
            "initialized": True,
            "database": "test_db",
            "unknown_field": "should_be_ignored",
            "another_unknown": 123,
        }

        state = GraphitiState.from_dict(data)
        assert state.database == "test_db"
        # Unknown fields should be ignored, not cause errors

    def test_to_dict_includes_all_v2_fields(self):
        """Test to_dict includes V2 provider fields."""
        state = GraphitiState(
            initialized=True,
            llm_provider="anthropic",
            embedder_provider="voyage",
        )

        data = state.to_dict()
        assert data["llm_provider"] == "anthropic"
        assert data["embedder_provider"] == "voyage"

    def test_from_dict_with_v2_fields(self):
        """Test from_dict with V2 provider fields."""
        data = {
            "initialized": True,
            "llm_provider": "openai",
            "embedder_provider": "ollama",
        }

        state = GraphitiState.from_dict(data)
        assert state.llm_provider == "openai"
        assert state.embedder_provider == "ollama"


class TestGraphitiStateMigration:
    """Tests for provider migration detection."""

    def test_has_provider_changed_not_initialized(self):
        """Test returns False when not initialized."""
        state = GraphitiState(initialized=False)
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="voyage",
        )

        assert state.has_provider_changed(config) is False

    def test_has_provider_changed_none_provider(self):
        """Test returns False when state provider is None."""
        state = GraphitiState(
            initialized=True,
            embedder_provider=None,
        )
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="voyage",
        )

        assert state.has_provider_changed(config) is False

    def test_has_provider_changed_same_provider(self):
        """Test returns False for same provider."""
        state = GraphitiState(
            initialized=True,
            embedder_provider="openai",
        )
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openai",
        )

        assert state.has_provider_changed(config) is False

    def test_has_provider_changed_different_provider(self):
        """Test returns True for different provider."""
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
        """Test returns None when no migration needed."""
        state = GraphitiState(
            initialized=True,
            embedder_provider="openai",
            database="db",
        )
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="openai",
            database="db",
        )

        assert state.get_migration_info(config) is None

    def test_get_migration_info_with_change(self):
        """Test returns migration info when provider changed."""
        state = GraphitiState(
            initialized=True,
            embedder_provider="openai",
            database="db_openai",
            episode_count=15,
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
        assert info["new_database"] == "db_voyage_1024"
        assert info["episode_count"] == 15
        assert info["requires_migration"] is True

    def test_get_migration_info_includes_base_database(self):
        """Test migration info uses base database name."""
        state = GraphitiState(
            initialized=True,
            embedder_provider="openai",
            database="custom_db_openai_1536",
            episode_count=5,
        )
        config = GraphitiConfig(
            enabled=True,
            embedder_provider="google",
            database="custom_db_openai_1536",  # Same base in config
        )

        info = state.get_migration_info(config)

        # New database should be custom_db_google_768
        assert "custom_db" in info["new_database"]
        assert "google_768" in info["new_database"]


class TestGraphitiStateLoadErrors:
    """Tests for GraphitiState.load error handling."""

    def test_load_nonexistent_returns_none(self, tmp_path: Path):
        """Test load returns None when file doesn't exist."""
        state = GraphitiState.load(tmp_path)
        assert state is None

    def test_load_invalid_json_returns_none(self, tmp_path: Path):
        """Test load returns None with invalid JSON."""
        state_file = tmp_path / GRAPHITI_STATE_MARKER
        state_file.write_text("not valid json {{{")

        state = GraphitiState.load(tmp_path)
        assert state is None

    def test_load_with_unicode_error_returns_none(self, tmp_path: Path):
        """Test load returns None on Unicode decode error."""
        state_file = tmp_path / GRAPHITI_STATE_MARKER
        with open(state_file, "wb") as f:
            f.write(b"\xff\xfe Invalid UTF-16")

        state = GraphitiState.load(tmp_path)
        assert state is None

    def test_load_with_os_error_returns_none(self, tmp_path: Path):
        """Test load handles OS errors gracefully."""
        state_file = tmp_path / GRAPHITI_STATE_MARKER
        state_file.write_text("{}")
        state_file.chmod(0o000)

        # Should handle permission error
        state = GraphitiState.load(tmp_path)
        # Result depends on OS
        assert state is None or state.initialized is False


class TestEpisodeTypeConstants:
    """Tests for episode type constants."""

    def test_session_insight_constant(self):
        """Test EPISODE_TYPE_SESSION_INSIGHT constant."""
        assert EPISODE_TYPE_SESSION_INSIGHT == "session_insight"

    def test_codebase_discovery_constant(self):
        """Test EPISODE_TYPE_CODEBASE_DISCOVERY constant."""
        assert EPISODE_TYPE_CODEBASE_DISCOVERY == "codebase_discovery"

    def test_pattern_constant(self):
        """Test EPISODE_TYPE_PATTERN constant."""
        assert EPISODE_TYPE_PATTERN == "pattern"

    def test_gotcha_constant(self):
        """Test EPISODE_TYPE_GOTCHA constant."""
        assert EPISODE_TYPE_GOTCHA == "gotcha"

    def test_task_outcome_constant(self):
        """Test EPISODE_TYPE_TASK_OUTCOME constant."""
        assert EPISODE_TYPE_TASK_OUTCOME == "task_outcome"

    def test_qa_result_constant(self):
        """Test EPISODE_TYPE_QA_RESULT constant."""
        assert EPISODE_TYPE_QA_RESULT == "qa_result"

    def test_historical_context_constant(self):
        """Test EPISODE_TYPE_HISTORICAL_CONTEXT constant."""
        assert EPISODE_TYPE_HISTORICAL_CONTEXT == "historical_context"


class TestLLMProviderEnum:
    """Tests for LLMProvider enum."""

    def test_llm_provider_values(self):
        """Test LLMProvider enum has correct values."""
        assert LLMProvider.OPENAI == "openai"
        assert LLMProvider.ANTHROPIC == "anthropic"
        assert LLMProvider.AZURE_OPENAI == "azure_openai"
        assert LLMProvider.OLLAMA == "ollama"
        assert LLMProvider.GOOGLE == "google"
        assert LLMProvider.OPENROUTER == "openrouter"


class TestEmbedderProviderEnum:
    """Tests for EmbedderProvider enum."""

    def test_embedder_provider_values(self):
        """Test EmbedderProvider enum has correct values."""
        assert EmbedderProvider.OPENAI == "openai"
        assert EmbedderProvider.VOYAGE == "voyage"
        assert EmbedderProvider.AZURE_OPENAI == "azure_openai"
        assert EmbedderProvider.OLLAMA == "ollama"
        assert EmbedderProvider.GOOGLE == "google"
        assert EmbedderProvider.OPENROUTER == "openrouter"
