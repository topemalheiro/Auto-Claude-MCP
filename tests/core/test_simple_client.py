"""
Tests for simple_client

Comprehensive test coverage for simple Claude SDK client factory.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from core.simple_client import create_simple_client
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions


class TestCreateSimpleClientBasic:
    """Tests for basic create_simple_client() functionality."""

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    def test_create_simple_client_default_params(
        self, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test create_simple_client with default parameters."""
        # Arrange
        mock_env.return_value = {"ANTHROPIC_API_KEY": "test-key"}
        mock_config.return_value = {"tools": [], "thinking_default": "low"}
        mock_thinking.return_value = "low"
        mock_budget.return_value = 1024

        # Act
        client = create_simple_client()

        # Assert
        assert isinstance(client, ClaudeSDKClient)
        mock_auth.assert_called_once()

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    def test_create_simple_client_returns_sdk_client(
        self, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test that create_simple_client returns ClaudeSDKClient instance."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "none"}
        mock_thinking.return_value = "none"
        mock_budget.return_value = None

        client = create_simple_client()

        assert isinstance(client, ClaudeSDKClient)


class TestAgentTypeParameter:
    """Tests for agent_type parameter variations."""

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    def test_agent_type_merge_resolver(
        self, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test agent_type='merge_resolver'."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "low"}
        mock_thinking.return_value = "low"
        mock_budget.return_value = 1024

        client = create_simple_client(agent_type="merge_resolver")

        assert isinstance(client, ClaudeSDKClient)
        mock_config.assert_called_with("merge_resolver")

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    def test_agent_type_commit_message(
        self, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test agent_type='commit_message'."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "low"}
        mock_thinking.return_value = "low"
        mock_budget.return_value = 1024

        client = create_simple_client(agent_type="commit_message")

        assert isinstance(client, ClaudeSDKClient)

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    def test_agent_type_insights(
        self, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test agent_type='insights'."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": ["Read", "Glob"], "thinking_default": "none"}
        mock_thinking.return_value = "none"
        mock_budget.return_value = None

        client = create_simple_client(agent_type="insights")

        assert isinstance(client, ClaudeSDKClient)

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    def test_agent_type_batch_analysis(
        self, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test agent_type='batch_analysis'."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": ["Read"], "thinking_default": "low"}
        mock_thinking.return_value = "low"
        mock_budget.return_value = 1024

        client = create_simple_client(agent_type="batch_analysis")

        assert isinstance(client, ClaudeSDKClient)

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    def test_agent_type_batch_validation(
        self, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test agent_type='batch_validation'."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": ["Read"], "thinking_default": "low"}
        mock_thinking.return_value = "low"
        mock_budget.return_value = 1024

        client = create_simple_client(agent_type="batch_validation")

        assert isinstance(client, ClaudeSDKClient)

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    def test_agent_type_pr_reviewer(
        self, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test agent_type='pr_reviewer'."""
        mock_env.return_value = {}
        mock_config.return_value = {
            "tools": ["Read", "WebSearch"],
            "thinking_default": "high"
        }
        mock_thinking.return_value = "high"
        mock_budget.return_value = 16384

        client = create_simple_client(agent_type="pr_reviewer")

        assert isinstance(client, ClaudeSDKClient)


class TestModelParameter:
    """Tests for model parameter variations."""

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_model_default_haiku(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test default model is haiku."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "none"}
        mock_thinking.return_value = "none"
        mock_budget.return_value = None
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        create_simple_client()  # Use default model

        # Verify ClaudeAgentOptions was created with default model
        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        assert options.model == "claude-haiku-4-5-20251001"

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_model_custom_sonnet(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test custom model selection."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "medium"}
        mock_thinking.return_value = "medium"
        mock_budget.return_value = 4096
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        create_simple_client(model="claude-sonnet-4-5-20250929")

        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        assert options.model == "claude-sonnet-4-5-20250929"

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_model_shorthand_opus(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test model shorthand 'opus' is passed through."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "ultrathink"}
        mock_thinking.return_value = "ultrathink"
        mock_budget.return_value = 63999
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        create_simple_client(model="opus")

        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        # The factory doesn't resolve shorthand - passes through to SDK
        assert options.model == "opus"

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_model_full_id_passed_through(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test that full model IDs are passed through unchanged."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "medium"}
        mock_thinking.return_value = "medium"
        mock_budget.return_value = 4096
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        full_id = "claude-opus-4-5-20251101"
        create_simple_client(model=full_id)

        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        assert options.model == full_id


class TestThinkingBudgetConfiguration:
    """Tests for max_thinking_tokens parameter handling."""

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_thinking_budget_from_agent_default(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test thinking budget from agent default."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "high"}
        mock_thinking.return_value = "high"
        mock_budget.return_value = 16384
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        create_simple_client()

        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        assert options.max_thinking_tokens == 16384

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_thinking_budget_override(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test max_thinking_tokens override."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "medium"}
        mock_thinking.return_value = "medium"
        mock_budget.return_value = 4096
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        create_simple_client(max_thinking_tokens=32000)

        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        assert options.max_thinking_tokens == 32000

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_thinking_budget_none_for_haiku(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test that None thinking budget is not added for Haiku (no thinking support)."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "none"}
        mock_thinking.return_value = "none"
        mock_budget.return_value = None
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        create_simple_client()

        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        # When None, max_thinking_tokens is not added to options_kwargs
        assert not hasattr(options, 'max_thinking_tokens') or options.max_thinking_tokens is None

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_thinking_all_levels(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test all thinking level budgets."""
        mock_env.return_value = {}

        thinking_budgets = {
            "none": None,
            "low": 1024,
            "medium": 4096,
            "high": 16384,
            "ultrathink": 63999,
        }

        for level, expected_budget in thinking_budgets.items():
            mock_config.reset_mock()
            mock_thinking.reset_mock()
            mock_budget.reset_mock()

            mock_config.return_value = {"tools": [], "thinking_default": level}
            mock_thinking.return_value = level
            mock_budget.return_value = expected_budget
            mock_instance = MagicMock()
            mock_client_class.return_value = mock_instance

            create_simple_client(agent_type="merge_resolver")

            call_args = mock_client_class.call_args
            options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]

            if expected_budget is None:
                # When None, max_thinking_tokens is not added
                assert not hasattr(options, 'max_thinking_tokens') or options.max_thinking_tokens is None
            else:
                assert options.max_thinking_tokens == expected_budget


class TestOptionalParameters:
    """Tests for optional parameters: system_prompt, cwd, max_turns."""

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_system_prompt_custom(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test custom system_prompt."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "medium"}
        mock_thinking.return_value = "medium"
        mock_budget.return_value = 4096
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        custom_prompt = "You are a helpful code reviewer."
        create_simple_client(system_prompt=custom_prompt)

        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        assert options.system_prompt == custom_prompt

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_system_prompt_none(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test system_prompt=None."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "medium"}
        mock_thinking.return_value = "medium"
        mock_budget.return_value = 4096
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        create_simple_client(system_prompt=None)

        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        assert options.system_prompt is None

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_cwd_with_path(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test cwd parameter with Path object."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": ["Read"], "thinking_default": "low"}
        mock_thinking.return_value = "low"
        mock_budget.return_value = 1024
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        test_path = Path("/test/project")
        create_simple_client(cwd=test_path)

        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        assert options.cwd == str(test_path.resolve())

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_cwd_none(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test cwd=None."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "low"}
        mock_thinking.return_value = "low"
        mock_budget.return_value = 1024
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        create_simple_client(cwd=None)

        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        assert options.cwd is None

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_max_turns_default_one(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test default max_turns is 1."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "low"}
        mock_thinking.return_value = "low"
        mock_budget.return_value = 1024
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        create_simple_client()

        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        assert options.max_turns == 1

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_max_turns_custom(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test custom max_turns."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "low"}
        mock_thinking.return_value = "low"
        mock_budget.return_value = 1024
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        create_simple_client(max_turns=5)

        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        assert options.max_turns == 5


class TestToolsConfiguration:
    """Tests for tools configuration from agent config."""

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_tools_empty_list(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test agent config with empty tools list."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "none"}
        mock_thinking.return_value = "none"
        mock_budget.return_value = None
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        create_simple_client()

        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        assert options.allowed_tools == []

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_tools_from_agent_config(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test tools are populated from agent config."""
        mock_env.return_value = {}
        mock_config.return_value = {
            "tools": ["Read", "Glob", "Grep", "Write", "Edit", "Bash"],
            "thinking_default": "medium"
        }
        mock_thinking.return_value = "medium"
        mock_budget.return_value = 4096
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        create_simple_client()

        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        assert "Read" in options.allowed_tools
        assert "Write" in options.allowed_tools
        assert "Bash" in options.allowed_tools

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_tools_read_only(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test read-only tools configuration."""
        mock_env.return_value = {}
        mock_config.return_value = {
            "tools": ["Read", "Glob", "Grep"],
            "thinking_default": "low"
        }
        mock_thinking.return_value = "low"
        mock_budget.return_value = 1024
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        create_simple_client(agent_type="batch_analysis")

        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        assert "Read" in options.allowed_tools
        assert "Glob" in options.allowed_tools
        assert "Grep" in options.allowed_tools
        assert "Write" not in options.allowed_tools


class TestEnvironmentVariables:
    """Tests for environment variable handling."""

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_sdk_env_vars_passed_to_options(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test SDK env vars are passed to client options."""
        env_vars = {
            "ANTHROPIC_API_KEY": "test-key",
            "CLAUDE_CONFIG_DIR": "/test/config"
        }
        mock_env.return_value = env_vars
        mock_config.return_value = {"tools": [], "thinking_default": "low"}
        mock_thinking.return_value = "low"
        mock_budget.return_value = 1024
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        create_simple_client()

        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        assert options.env == env_vars

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_config_dir_passed_to_auth(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test CLAUDE_CONFIG_DIR is passed to configure_sdk_authentication."""
        config_dir = "/test/config"
        mock_env.return_value = {"CLAUDE_CONFIG_DIR": config_dir}
        mock_config.return_value = {"tools": [], "thinking_default": "low"}
        mock_thinking.return_value = "low"
        mock_budget.return_value = 1024
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        create_simple_client()

        mock_auth.assert_called_with(config_dir)


class TestCliPathOverride:
    """Tests for CLAUDE_CLI_PATH environment variable override."""

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    @patch('core.simple_client.validate_cli_path')
    def test_cli_path_override_valid(
        self, mock_validate, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test CLAUDE_CLI_PATH override with valid path."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "low"}
        mock_thinking.return_value = "low"
        mock_budget.return_value = 1024
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance
        mock_validate.return_value = True

        cli_path = "/custom/path/to/claude"

        # Set and restore original env var
        original = os.environ.get('CLAUDE_CLI_PATH')
        try:
            os.environ['CLAUDE_CLI_PATH'] = cli_path
            create_simple_client()
        finally:
            if original is None:
                os.environ.pop('CLAUDE_CLI_PATH', None)
            else:
                os.environ['CLAUDE_CLI_PATH'] = original

        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        assert options.cli_path == cli_path
        mock_validate.assert_called_with(cli_path)

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    @patch('core.simple_client.validate_cli_path')
    def test_cli_path_override_invalid(
        self, mock_validate, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test CLAUDE_CLI_PATH override with invalid path."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "low"}
        mock_thinking.return_value = "low"
        mock_budget.return_value = 1024
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance
        mock_validate.return_value = False

        # Set and restore original env var
        original = os.environ.get('CLAUDE_CLI_PATH')
        try:
            os.environ['CLAUDE_CLI_PATH'] = '/invalid/path'
            create_simple_client()
        finally:
            if original is None:
                os.environ.pop('CLAUDE_CLI_PATH', None)
            else:
                os.environ['CLAUDE_CLI_PATH'] = original

        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        assert not hasattr(options, 'cli_path') or options.cli_path is None

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_no_cli_path_override(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test no CLAUDE_CLI_PATH override."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "low"}
        mock_thinking.return_value = "low"
        mock_budget.return_value = 1024
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        # Remove and restore original env var
        original = os.environ.get('CLAUDE_CLI_PATH')
        try:
            os.environ.pop('CLAUDE_CLI_PATH', None)
            create_simple_client()
        finally:
            if original is not None:
                os.environ['CLAUDE_CLI_PATH'] = original

        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        assert not hasattr(options, 'cli_path') or options.cli_path is None


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    def test_unknown_agent_type_raises_value_error(
        self, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test that unknown agent type raises ValueError."""
        mock_env.return_value = {}
        mock_config.side_effect = ValueError(
            "Unknown agent type: 'unknown_type'. "
            "Valid types: ['batch_analysis', 'batch_validation', ...]"
        )

        with pytest.raises(ValueError, match="Unknown agent type"):
            create_simple_client(agent_type="unknown_type")

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_agent_config_missing_tools_empty_list(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test agent config with missing tools key defaults to empty list."""
        mock_env.return_value = {}
        mock_config.return_value = {"thinking_default": "low"}
        mock_thinking.return_value = "low"
        mock_budget.return_value = 1024
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        create_simple_client()

        call_args = mock_client_class.call_args
        options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
        assert options.allowed_tools == []


class TestReturnValueValidation:
    """Tests for return value validation."""

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    def test_return_value_is_claude_sdk_client(
        self, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test that return value is ClaudeSDKClient instance."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "low"}
        mock_thinking.return_value = "low"
        mock_budget.return_value = 1024

        client = create_simple_client()

        # Check instance type
        assert isinstance(client, ClaudeSDKClient)

    @patch('core.simple_client.configure_sdk_authentication')
    @patch('core.simple_client.get_agent_config')
    @patch('core.simple_client.get_default_thinking_level')
    @patch('core.simple_client.get_thinking_budget')
    @patch('core.simple_client.get_sdk_env_vars')
    @patch('core.simple_client.ClaudeSDKClient')
    def test_client_created_with_options(
        self, mock_client_class, mock_env, mock_budget, mock_thinking, mock_config, mock_auth
    ):
        """Test that ClaudeSDKClient is created with ClaudeAgentOptions."""
        mock_env.return_value = {}
        mock_config.return_value = {"tools": [], "thinking_default": "low"}
        mock_thinking.return_value = "low"
        mock_budget.return_value = 1024
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        create_simple_client()

        # Verify ClaudeSDKClient was called
        mock_client_class.assert_called_once()

        # Verify options parameter
        call_args = mock_client_class.call_args
        assert 'options' in call_args[1]
        assert isinstance(call_args[1]['options'], ClaudeAgentOptions)
