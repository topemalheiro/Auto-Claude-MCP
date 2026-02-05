"""Tests for model_config"""

import os
from core.model_config import get_utility_model_config, DEFAULT_UTILITY_MODEL
import pytest


class TestGetUtilityModelConfig:
    """Tests for get_utility_model_config function"""

    def test_returns_default_model_when_env_not_set(self, monkeypatch):
        """Test returns default model when UTILITY_MODEL_ID not set"""
        monkeypatch.delenv("UTILITY_MODEL_ID", raising=False)
        monkeypatch.delenv("UTILITY_THINKING_BUDGET", raising=False)

        model, budget = get_utility_model_config()

        assert model == DEFAULT_UTILITY_MODEL
        assert budget is None

    def test_returns_custom_default_model(self, monkeypatch):
        """Test returns custom default model when provided"""
        monkeypatch.delenv("UTILITY_MODEL_ID", raising=False)
        monkeypatch.delenv("UTILITY_THINKING_BUDGET", raising=False)

        custom_default = "claude-sonnet-4-5-20250514"
        model, budget = get_utility_model_config(default_model=custom_default)

        assert model == custom_default
        assert budget is None

    def test_returns_env_model_id(self, monkeypatch):
        """Test returns model from UTILITY_MODEL_ID environment variable"""
        monkeypatch.setenv("UTILITY_MODEL_ID", "claude-opus-4-5-20250514")
        monkeypatch.delenv("UTILITY_THINKING_BUDGET", raising=False)

        model, budget = get_utility_model_config()

        assert model == "claude-opus-4-5-20250514"
        assert budget is None

    def test_thinking_budget_none_when_empty_string(self, monkeypatch):
        """Test thinking budget is None when UTILITY_THINKING_BUDGET is empty"""
        monkeypatch.delenv("UTILITY_MODEL_ID", raising=False)
        monkeypatch.setenv("UTILITY_THINKING_BUDGET", "")

        model, budget = get_utility_model_config()

        assert budget is None

    def test_thinking_budget_positive_int(self, monkeypatch):
        """Test positive thinking budget is returned as int"""
        monkeypatch.delenv("UTILITY_MODEL_ID", raising=False)
        monkeypatch.setenv("UTILITY_THINKING_BUDGET", "2048")

        model, budget = get_utility_model_config()

        assert budget == 2048
        assert isinstance(budget, int)

    def test_thinking_budget_zero_returns_none(self, monkeypatch):
        """Test zero thinking budget returns None (disabled)"""
        monkeypatch.delenv("UTILITY_MODEL_ID", raising=False)
        monkeypatch.setenv("UTILITY_THINKING_BUDGET", "0")

        model, budget = get_utility_model_config()

        assert budget is None

    def test_thinking_budget_negative_returns_default(self, monkeypatch, caplog):
        """Test negative thinking budget returns default 1024"""
        monkeypatch.delenv("UTILITY_MODEL_ID", raising=False)
        monkeypatch.setenv("UTILITY_THINKING_BUDGET", "-100")

        model, budget = get_utility_model_config()

        assert budget == 1024
        assert "Negative UTILITY_THINKING_BUDGET value" in caplog.text

    def test_thinking_budget_invalid_string_returns_default(self, monkeypatch, caplog):
        """Test invalid thinking budget string returns default 1024"""
        monkeypatch.delenv("UTILITY_MODEL_ID", raising=False)
        monkeypatch.setenv("UTILITY_THINKING_BUDGET", "invalid")

        model, budget = get_utility_model_config()

        assert budget == 1024
        assert "Invalid UTILITY_THINKING_BUDGET value" in caplog.text

    def test_thinking_budget_float_string_returns_default(self, monkeypatch, caplog):
        """Test float string thinking budget returns default 1024"""
        monkeypatch.delenv("UTILITY_MODEL_ID", raising=False)
        monkeypatch.setenv("UTILITY_THINKING_BUDGET", "1024.5")

        model, budget = get_utility_model_config()

        assert budget == 1024
        assert "Invalid UTILITY_THINKING_BUDGET value" in caplog.text

    def test_large_thinking_budget(self, monkeypatch):
        """Test large thinking budget value"""
        monkeypatch.delenv("UTILITY_MODEL_ID", raising=False)
        monkeypatch.setenv("UTILITY_THINKING_BUDGET", "200000")

        model, budget = get_utility_model_config()

        assert budget == 200000

    def test_both_env_vars_set(self, monkeypatch):
        """Test both model and thinking budget from environment"""
        monkeypatch.setenv("UTILITY_MODEL_ID", "custom-model-123")
        monkeypatch.setenv("UTILITY_THINKING_BUDGET", "4096")

        model, budget = get_utility_model_config()

        assert model == "custom-model-123"
        assert budget == 4096

    def test_thinking_budget_one(self, monkeypatch):
        """Test minimum positive thinking budget of 1"""
        monkeypatch.delenv("UTILITY_MODEL_ID", raising=False)
        monkeypatch.setenv("UTILITY_THINKING_BUDGET", "1")

        model, budget = get_utility_model_config()

        assert budget == 1

    def test_whitespace_thinking_budget_returns_default(self, monkeypatch, caplog):
        """Test whitespace-only thinking budget returns default"""
        monkeypatch.delenv("UTILITY_MODEL_ID", raising=False)
        monkeypatch.setenv("UTILITY_THINKING_BUDGET", "  ")

        model, budget = get_utility_model_config()

        # Empty/whitespace strings after strip are treated as empty
        # Actually looking at the code, it checks `if not thinking_budget_str:`
        # which will be False for "  " (non-empty string)
        # Then int("  ") will raise ValueError
        assert budget == 1024
        assert "Invalid UTILITY_THINKING_BUDGET value" in caplog.text

    def test_tuple_return_type(self, monkeypatch):
        """Test returns tuple of (model, thinking_budget)"""
        monkeypatch.delenv("UTILITY_MODEL_ID", raising=False)
        monkeypatch.setenv("UTILITY_THINKING_BUDGET", "512")

        result = get_utility_model_config()

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], int)

    def test_thinking_budget_can_be_none_type(self, monkeypatch):
        """Test thinking budget can be None type when disabled"""
        monkeypatch.delenv("UTILITY_MODEL_ID", raising=False)
        monkeypatch.setenv("UTILITY_THINKING_BUDGET", "")

        model, budget = get_utility_model_config()

        assert budget is None
        # Verify type annotation allows None
        assert budget is None or isinstance(budget, int)

    def test_model_id_can_be_any_string(self, monkeypatch):
        """Test model ID accepts arbitrary string values"""
        monkeypatch.setenv("UTILITY_MODEL_ID", "my-custom-model-v2")
        monkeypatch.delenv("UTILITY_THINKING_BUDGET", raising=False)

        model, budget = get_utility_model_config()

        assert model == "my-custom-model-v2"

    def test_default_utility_model_constant(self):
        """Test DEFAULT_UTILITY_MODEL is set correctly"""
        assert DEFAULT_UTILITY_MODEL == "claude-haiku-4-5-20251001"
