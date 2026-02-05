"""Tests for phase_config module"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from phase_config import (
    DEFAULT_PHASE_MODELS,
    DEFAULT_PHASE_THINKING,
    MODEL_ID_MAP,
    SPEC_PHASE_THINKING_LEVELS,
    THINKING_BUDGET_MAP,
    get_phase_config,
    get_phase_model,
    get_phase_thinking,
    get_phase_thinking_budget,
    get_spec_phase_thinking_budget,
    get_thinking_budget,
    load_task_metadata,
    resolve_model_id,
)


class TestResolveModelId:
    """Tests for resolve_model_id function"""

    @patch.dict("os.environ", {}, clear=True)
    def test_resolve_haiku_shorthand(self):
        """Test resolving haiku shorthand to full model ID"""
        result = resolve_model_id("haiku")
        assert result == "claude-haiku-4-5-20251001"

    @patch.dict("os.environ", {}, clear=True)
    def test_resolve_sonnet_shorthand(self):
        """Test resolving sonnet shorthand to full model ID"""
        result = resolve_model_id("sonnet")
        assert result == "claude-sonnet-4-5-20250929"

    @patch.dict("os.environ", {}, clear=True)
    def test_resolve_opus_shorthand(self):
        """Test resolving opus shorthand to full model ID"""
        result = resolve_model_id("opus")
        assert result == "claude-opus-4-5-20251101"

    @patch.dict("os.environ", {}, clear=True)
    def test_resolve_full_model_id_passthrough(self):
        """Test that full model IDs are passed through unchanged"""
        full_id = "claude-sonnet-4-5-20250929"
        result = resolve_model_id(full_id)
        assert result == full_id

    @patch.dict("os.environ", {}, clear=True)
    def test_resolve_unknown_shorthand_passthrough(self):
        """Test that unknown model shorthands are passed through unchanged"""
        unknown = "unknown-model"
        result = resolve_model_id(unknown)
        assert result == unknown

    def test_resolve_with_env_override_haiku(self):
        """Test environment variable override for haiku"""
        custom_model = "custom-haiku-model"
        with patch.dict("os.environ", {"ANTHROPIC_DEFAULT_HAIKU_MODEL": custom_model}, clear=True):
            result = resolve_model_id("haiku")
            assert result == custom_model

    def test_resolve_with_env_override_sonnet(self):
        """Test environment variable override for sonnet"""
        custom_model = "custom-sonnet-model"
        with patch.dict("os.environ", {"ANTHROPIC_DEFAULT_SONNET_MODEL": custom_model}, clear=True):
            result = resolve_model_id("sonnet")
            assert result == custom_model

    def test_resolve_with_env_override_opus(self):
        """Test environment variable override for opus"""
        custom_model = "custom-opus-model"
        with patch.dict("os.environ", {"ANTHROPIC_DEFAULT_OPUS_MODEL": custom_model}, clear=True):
            result = resolve_model_id("opus")
            assert result == custom_model

    def test_resolve_env_override_empty_value(self):
        """Test that empty env override falls back to default"""
        with patch.dict("os.environ", {"ANTHROPIC_DEFAULT_SONNET_MODEL": ""}, clear=True):
            result = resolve_model_id("sonnet")
            assert result == MODEL_ID_MAP["sonnet"]


class TestGetThinkingBudget:
    """Tests for get_thinking_budget function"""

    def test_thinking_budget_none(self):
        """Test 'none' thinking level returns None"""
        result = get_thinking_budget("none")
        assert result is None

    def test_thinking_budget_low(self):
        """Test 'low' thinking level"""
        result = get_thinking_budget("low")
        assert result == 1024

    def test_thinking_budget_medium(self):
        """Test 'medium' thinking level"""
        result = get_thinking_budget("medium")
        assert result == 4096

    def test_thinking_budget_high(self):
        """Test 'high' thinking level"""
        result = get_thinking_budget("high")
        assert result == 16384

    def test_thinking_budget_ultrathink(self):
        """Test 'ultrathink' thinking level"""
        result = get_thinking_budget("ultrathink")
        assert result == 63999

    def test_thinking_budget_invalid_defaults_to_medium(self, caplog):
        """Test invalid thinking level defaults to medium with warning"""
        result = get_thinking_budget("invalid")
        assert result == THINKING_BUDGET_MAP["medium"]
        assert "Invalid thinking_level" in caplog.text
        assert "defaulting to 'medium'" in caplog.text.lower()


class TestLoadTaskMetadata:
    """Tests for load_task_metadata function"""

    def test_load_metadata_not_exists(self, tmp_path):
        """Test loading metadata when file doesn't exist"""
        result = load_task_metadata(tmp_path)
        assert result is None

    def test_load_metadata_valid_json(self, tmp_path):
        """Test loading valid metadata JSON"""
        metadata = {
            "isAutoProfile": True,
            "phaseModels": {"planning": "opus", "coding": "sonnet"},
            "phaseThinking": {"planning": "high", "coding": "medium"},
        }
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        result = load_task_metadata(tmp_path)
        assert result == metadata

    def test_load_metadata_invalid_json(self, tmp_path):
        """Test loading invalid JSON returns None"""
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text("{ invalid json }")

        result = load_task_metadata(tmp_path)
        assert result is None

    def test_load_metadata_empty_file(self, tmp_path):
        """Test loading empty JSON file"""
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text("{}")

        result = load_task_metadata(tmp_path)
        assert result == {}

    def test_load_metadata_with_os_error(self, tmp_path):
        """Test handling of OS errors during file read"""
        # Create a directory instead of a file
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.mkdir()

        result = load_task_metadata(tmp_path)
        assert result is None


class TestGetPhaseModel:
    """Tests for get_phase_model function"""

    @patch.dict("os.environ", {}, clear=True)
    def test_get_phase_model_cli_override(self, tmp_path):
        """Test CLI argument takes precedence"""
        result = get_phase_model(tmp_path, "coding", cli_model="opus")
        assert result == MODEL_ID_MAP["opus"]

    @patch.dict("os.environ", {}, clear=True)
    def test_get_phase_model_default_fallback(self, tmp_path):
        """Test default fallback when no metadata exists"""
        result = get_phase_model(tmp_path, "coding")
        assert result == MODEL_ID_MAP[DEFAULT_PHASE_MODELS["coding"]]

    @patch.dict("os.environ", {}, clear=True)
    def test_get_phase_model_auto_profile_phase_specific(self, tmp_path):
        """Test auto profile with phase-specific models"""
        metadata = {
            "isAutoProfile": True,
            "phaseModels": {"planning": "opus", "coding": "haiku"},
        }
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        result = get_phase_model(tmp_path, "coding")
        assert result == MODEL_ID_MAP["haiku"]

    @patch.dict("os.environ", {}, clear=True)
    def test_get_phase_model_auto_profile_missing_phase_uses_default(self, tmp_path):
        """Test auto profile missing specific phase uses default"""
        metadata = {
            "isAutoProfile": True,
            "phaseModels": {"planning": "opus"},  # No 'coding' key
        }
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        result = get_phase_model(tmp_path, "coding")
        assert result == MODEL_ID_MAP[DEFAULT_PHASE_MODELS["coding"]]

    @patch.dict("os.environ", {}, clear=True)
    def test_get_phase_model_non_auto_profile_single_model(self, tmp_path):
        """Test non-auto profile uses single model"""
        metadata = {"isAutoProfile": False, "model": "opus"}
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        result = get_phase_model(tmp_path, "coding")
        assert result == MODEL_ID_MAP["opus"]

    @patch.dict("os.environ", {}, clear=True)
    def test_get_phase_model_no_is_auto_profile_key_uses_single_model(self, tmp_path):
        """Test metadata without isAutoProfile uses single model"""
        metadata = {"model": "haiku"}
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        result = get_phase_model(tmp_path, "planning")
        assert result == MODEL_ID_MAP["haiku"]

    @patch.dict("os.environ", {}, clear=True)
    def test_get_phase_model_all_phases(self, tmp_path):
        """Test model resolution for all phases"""
        metadata = {
            "isAutoProfile": True,
            "phaseModels": {
                "spec": "opus",
                "planning": "opus",
                "coding": "sonnet",
                "qa": "sonnet",
            },
        }
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        assert get_phase_model(tmp_path, "spec") == MODEL_ID_MAP["opus"]
        assert get_phase_model(tmp_path, "planning") == MODEL_ID_MAP["opus"]
        assert get_phase_model(tmp_path, "coding") == MODEL_ID_MAP["sonnet"]
        assert get_phase_model(tmp_path, "qa") == MODEL_ID_MAP["sonnet"]

    def test_get_phase_model_with_custom_full_model_id(self, tmp_path):
        """Test with custom full model ID in metadata"""
        custom_model = "custom-model-id-123"
        metadata = {"isAutoProfile": False, "model": custom_model}
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        result = get_phase_model(tmp_path, "coding")
        assert result == custom_model


class TestGetPhaseThinking:
    """Tests for get_phase_thinking function"""

    def test_get_phase_thinking_cli_override(self, tmp_path):
        """Test CLI argument takes precedence"""
        result = get_phase_thinking(tmp_path, "coding", cli_thinking="high")
        assert result == "high"

    def test_get_phase_thinking_default_fallback(self, tmp_path):
        """Test default fallback when no metadata exists"""
        result = get_phase_thinking(tmp_path, "coding")
        assert result == DEFAULT_PHASE_THINKING["coding"]

    def test_get_phase_thinking_auto_profile_phase_specific(self, tmp_path):
        """Test auto profile with phase-specific thinking levels"""
        metadata = {
            "isAutoProfile": True,
            "phaseThinking": {"planning": "ultrathink", "coding": "low"},
        }
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        result = get_phase_thinking(tmp_path, "coding")
        assert result == "low"

    def test_get_phase_thinking_auto_profile_missing_phase_uses_default(self, tmp_path):
        """Test auto profile missing specific phase uses default"""
        metadata = {
            "isAutoProfile": True,
            "phaseThinking": {"planning": "high"},  # No 'coding' key
        }
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        result = get_phase_thinking(tmp_path, "coding")
        assert result == DEFAULT_PHASE_THINKING["coding"]

    def test_get_phase_thinking_non_auto_profile_single_level(self, tmp_path):
        """Test non-auto profile uses single thinking level"""
        metadata = {"isAutoProfile": False, "thinkingLevel": "none"}
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        result = get_phase_thinking(tmp_path, "coding")
        assert result == "none"

    def test_get_phase_thinking_no_is_auto_profile_key_uses_single_level(self, tmp_path):
        """Test metadata without isAutoProfile uses single thinking level"""
        metadata = {"thinkingLevel": "low"}
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        result = get_phase_thinking(tmp_path, "planning")
        assert result == "low"

    def test_get_phase_thinking_all_phases(self, tmp_path):
        """Test thinking resolution for all phases"""
        metadata = {
            "isAutoProfile": True,
            "phaseThinking": {
                "spec": "high",
                "planning": "ultrathink",
                "coding": "medium",
                "qa": "high",
            },
        }
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        assert get_phase_thinking(tmp_path, "spec") == "high"
        assert get_phase_thinking(tmp_path, "planning") == "ultrathink"
        assert get_phase_thinking(tmp_path, "coding") == "medium"
        assert get_phase_thinking(tmp_path, "qa") == "high"


class TestGetPhaseThinkingBudget:
    """Tests for get_phase_thinking_budget function"""

    def test_get_phase_thinking_budget_default(self, tmp_path):
        """Test getting thinking budget with defaults"""
        result = get_phase_thinking_budget(tmp_path, "coding")
        expected = THINKING_BUDGET_MAP[DEFAULT_PHASE_THINKING["coding"]]
        assert result == expected

    def test_get_phase_thinking_budget_cli_override(self, tmp_path):
        """Test CLI override for thinking budget"""
        result = get_phase_thinking_budget(tmp_path, "coding", cli_thinking="high")
        assert result == THINKING_BUDGET_MAP["high"]

    def test_get_phase_thinking_budget_from_metadata(self, tmp_path):
        """Test thinking budget from metadata"""
        metadata = {
            "isAutoProfile": True,
            "phaseThinking": {"coding": "ultrathink"},
        }
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        result = get_phase_thinking_budget(tmp_path, "coding")
        assert result == THINKING_BUDGET_MAP["ultrathink"]

    def test_get_phase_thinking_budget_none(self, tmp_path):
        """Test thinking budget of None"""
        metadata = {
            "isAutoProfile": False,
            "thinkingLevel": "none",
        }
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        result = get_phase_thinking_budget(tmp_path, "coding")
        assert result is None


class TestGetPhaseConfig:
    """Tests for get_phase_config function"""

    @patch.dict("os.environ", {}, clear=True)
    def test_get_phase_config_all_defaults(self, tmp_path):
        """Test getting full config with all defaults"""
        model_id, thinking_level, thinking_budget = get_phase_config(
            tmp_path, "coding"
        )

        expected_model = MODEL_ID_MAP[DEFAULT_PHASE_MODELS["coding"]]
        expected_thinking = DEFAULT_PHASE_THINKING["coding"]
        expected_budget = THINKING_BUDGET_MAP[expected_thinking]

        assert model_id == expected_model
        assert thinking_level == expected_thinking
        assert thinking_budget == expected_budget

    @patch.dict("os.environ", {}, clear=True)
    def test_get_phase_config_with_metadata(self, tmp_path):
        """Test getting full config from metadata"""
        metadata = {
            "isAutoProfile": True,
            "phaseModels": {"coding": "opus"},
            "phaseThinking": {"coding": "high"},
        }
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        model_id, thinking_level, thinking_budget = get_phase_config(
            tmp_path, "coding"
        )

        assert model_id == MODEL_ID_MAP["opus"]
        assert thinking_level == "high"
        assert thinking_budget == THINKING_BUDGET_MAP["high"]

    @patch.dict("os.environ", {}, clear=True)
    def test_get_phase_config_cli_overrides(self, tmp_path):
        """Test CLI overrides for both model and thinking"""
        model_id, thinking_level, thinking_budget = get_phase_config(
            tmp_path, "coding", cli_model="haiku", cli_thinking="low"
        )

        assert model_id == MODEL_ID_MAP["haiku"]
        assert thinking_level == "low"
        assert thinking_budget == THINKING_BUDGET_MAP["low"]

    @patch.dict("os.environ", {}, clear=True)
    def test_get_phase_config_all_phases(self, tmp_path):
        """Test getting config for all phases"""
        for phase in ["spec", "planning", "coding", "qa"]:
            model_id, thinking_level, thinking_budget = get_phase_config(
                tmp_path, phase
            )

            expected_model = MODEL_ID_MAP[DEFAULT_PHASE_MODELS[phase]]
            expected_thinking = DEFAULT_PHASE_THINKING[phase]
            expected_budget = THINKING_BUDGET_MAP[expected_thinking]

            assert model_id == expected_model
            assert thinking_level == expected_thinking
            assert thinking_budget == expected_budget


class TestGetSpecPhaseThinkingBudget:
    """Tests for get_spec_phase_thinking_budget function"""

    def test_spec_phase_discovery(self):
        """Test discovery phase gets ultrathink budget"""
        result = get_spec_phase_thinking_budget("discovery")
        assert result == THINKING_BUDGET_MAP["ultrathink"]

    def test_spec_phase_spec_writing(self):
        """Test spec_writing phase gets ultrathink budget"""
        result = get_spec_phase_thinking_budget("spec_writing")
        assert result == THINKING_BUDGET_MAP["ultrathink"]

    def test_spec_phase_self_critique(self):
        """Test self_critique phase gets ultrathink budget"""
        result = get_spec_phase_thinking_budget("self_critique")
        assert result == THINKING_BUDGET_MAP["ultrathink"]

    def test_spec_phase_requirements(self):
        """Test requirements phase gets medium budget"""
        result = get_spec_phase_thinking_budget("requirements")
        assert result == THINKING_BUDGET_MAP["medium"]

    def test_spec_phase_research(self):
        """Test research phase gets medium budget"""
        result = get_spec_phase_thinking_budget("research")
        assert result == THINKING_BUDGET_MAP["medium"]

    def test_spec_phase_context(self):
        """Test context phase gets medium budget"""
        result = get_spec_phase_thinking_budget("context")
        assert result == THINKING_BUDGET_MAP["medium"]

    def test_spec_phase_planning(self):
        """Test planning phase gets medium budget"""
        result = get_spec_phase_thinking_budget("planning")
        assert result == THINKING_BUDGET_MAP["medium"]

    def test_spec_phase_validation(self):
        """Test validation phase gets medium budget"""
        result = get_spec_phase_thinking_budget("validation")
        assert result == THINKING_BUDGET_MAP["medium"]

    def test_spec_phase_quick_spec(self):
        """Test quick_spec phase gets medium budget"""
        result = get_spec_phase_thinking_budget("quick_spec")
        assert result == THINKING_BUDGET_MAP["medium"]

    def test_spec_phase_historical_context(self):
        """Test historical_context phase gets medium budget"""
        result = get_spec_phase_thinking_budget("historical_context")
        assert result == THINKING_BUDGET_MAP["medium"]

    def test_spec_phase_complexity_assessment(self):
        """Test complexity_assessment phase gets medium budget"""
        result = get_spec_phase_thinking_budget("complexity_assessment")
        assert result == THINKING_BUDGET_MAP["medium"]

    def test_spec_phase_unknown_defaults_to_medium(self):
        """Test unknown spec phase defaults to medium budget"""
        result = get_spec_phase_thinking_budget("unknown_phase")
        assert result == THINKING_BUDGET_MAP["medium"]

    def test_all_spec_phases_have_defined_budgets(self):
        """Test that all defined spec phases return valid budgets"""
        for phase_name, thinking_level in SPEC_PHASE_THINKING_LEVELS.items():
            result = get_spec_phase_thinking_budget(phase_name)
            expected = THINKING_BUDGET_MAP[thinking_level]
            assert result == expected, f"Phase {phase_name} should have budget {expected}"


class TestEdgeCases:
    """Tests for edge cases and error conditions"""

    @patch.dict("os.environ", {}, clear=True)
    def test_empty_metadata_file(self, tmp_path):
        """Test with empty metadata file"""
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text("{}")

        model = get_phase_model(tmp_path, "coding")
        thinking = get_phase_thinking(tmp_path, "coding")

        assert model == MODEL_ID_MAP[DEFAULT_PHASE_MODELS["coding"]]
        assert thinking == DEFAULT_PHASE_THINKING["coding"]

    @patch.dict("os.environ", {}, clear=True)
    def test_metadata_with_null_values(self, tmp_path):
        """Test metadata with null values"""
        metadata = {
            "isAutoProfile": True,
            "phaseModels": None,
            "phaseThinking": None,
        }
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        model = get_phase_model(tmp_path, "coding")
        thinking = get_phase_thinking(tmp_path, "coding")

        # Should fall back to defaults
        assert model == MODEL_ID_MAP[DEFAULT_PHASE_MODELS["coding"]]
        assert thinking == DEFAULT_PHASE_THINKING["coding"]

    @patch.dict("os.environ", {}, clear=True)
    def test_corrupted_json_file(self, tmp_path):
        """Test with corrupted JSON file"""
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text("{corrupted json content")

        model = get_phase_model(tmp_path, "coding")
        thinking = get_phase_thinking(tmp_path, "coding")

        # Should fall back to defaults
        assert model == MODEL_ID_MAP[DEFAULT_PHASE_MODELS["coding"]]
        assert thinking == DEFAULT_PHASE_THINKING["coding"]

    @patch.dict("os.environ", {}, clear=True)
    def test_mixed_valid_and_invalid_phases_in_metadata(self, tmp_path):
        """Test metadata with some valid and some invalid phase entries"""
        metadata = {
            "isAutoProfile": True,
            "phaseModels": {
                "coding": "sonnet",
                "invalid_phase": "opus",  # Should be ignored
            },
            "phaseThinking": {
                "coding": "medium",
                "invalid_phase": "high",  # Should be ignored
            },
        }
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        model = get_phase_model(tmp_path, "coding")
        thinking = get_phase_thinking(tmp_path, "coding")

        assert model == MODEL_ID_MAP["sonnet"]
        assert thinking == "medium"

    @patch.dict("os.environ", {}, clear=True)
    def test_phase_models_without_is_auto_profile(self, tmp_path):
        """Test phaseModels without isAutoProfile key"""
        metadata = {
            "phaseModels": {"coding": "opus"},
            "model": "haiku",
        }
        metadata_path = tmp_path / "task_metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        # Should use the single model, not phaseModels
        model = get_phase_model(tmp_path, "coding")
        assert model == MODEL_ID_MAP["haiku"]

    @patch.dict("os.environ", {}, clear=True)
    def test_nonexistent_spec_dir(self, tmp_path):
        """Test with nonexistent spec directory (using tmp_path as base)"""
        # Create a subdirectory that doesn't have task_metadata.json
        nonexistent_spec = tmp_path / "nonexistent_spec"

        model = get_phase_model(nonexistent_spec, "coding")
        thinking = get_phase_thinking(nonexistent_spec, "coding")

        # Should use defaults
        assert model == MODEL_ID_MAP[DEFAULT_PHASE_MODELS["coding"]]
        assert thinking == DEFAULT_PHASE_THINKING["coding"]
