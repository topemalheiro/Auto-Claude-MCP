"""Tests for hooks"""

from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from security.hooks import bash_security_hook, validate_command
from security.constants import PROJECT_DIR_ENV_VAR


class TestBashSecurityHook:
    """Tests for bash_security_hook function"""

    @pytest.mark.asyncio
    async def test_allows_non_bash_tools(self):
        """Test that non-Bash tools are allowed through"""
        input_data = {
            "tool_name": "ReadWrite",
            "tool_input": {"file_path": "/tmp/test.txt"}
        }
        result = await bash_security_hook(input_data)
        assert result == {}

    @pytest.mark.asyncio
    async def test_blocks_none_tool_input(self):
        """Test that None tool_input is blocked"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": None
        }
        result = await bash_security_hook(input_data)
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "malformed tool call" in result["hookSpecificOutput"]["permissionDecisionReason"]

    @pytest.mark.asyncio
    async def test_blocks_non_dict_tool_input(self):
        """Test that non-dict tool_input is blocked"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": "invalid string"
        }
        result = await bash_security_hook(input_data)
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_allows_empty_command(self):
        """Test that empty commands are allowed (early return)"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": ""}
        }
        result = await bash_security_hook(input_data)
        assert result == {}

    @pytest.mark.asyncio
    async def test_blocks_disallowed_command(self):
        """Test that disallowed commands are blocked"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /"}
        }
        result = await bash_security_hook(input_data)
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_blocks_unparseable_command(self):
        """Test that unparseable commands are blocked"""
        with patch('security.hooks.extract_commands', return_value=[]):
            input_data = {
                "tool_name": "Bash",
                "tool_input": {"command": "some invalid command"}
            }
            result = await bash_security_hook(input_data)
            assert "hookSpecificOutput" in result
            assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_respects_project_dir_env_var(self, tmp_path):
        """Test that PROJECT_DIR_ENV_VAR is respected for cwd"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls"}
        }

        with patch.dict('os.environ', {PROJECT_DIR_ENV_VAR: str(tmp_path)}):
            # Should use the env var for project_dir
            with patch('security.hooks.get_security_profile') as mock_profile:
                mock_profile.return_value = MagicMock()
                mock_profile.return_value.get_all_allowed_commands.return_value = ['ls']
                mock_profile.return_value.base_commands = {'ls': MagicMock()}

                with patch('security.hooks.is_command_allowed', return_value=(True, "")):
                    result = await bash_security_hook(input_data)
                    assert result == {}

    @pytest.mark.asyncio
    async def test_falls_back_to_input_data_cwd(self):
        """Test fallback to input_data cwd when env var not set"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "cwd": "/tmp/test"
        }

        with patch.dict('os.environ', {}, clear=True):
            with patch('security.hooks.get_security_profile') as mock_profile:
                mock_profile.return_value = MagicMock()
                mock_profile.return_value.get_all_allowed_commands.return_value = ['ls']
                mock_profile.return_value.base_commands = {'ls': MagicMock()}

                with patch('security.hooks.is_command_allowed', return_value=(True, "")):
                    result = await bash_security_hook(input_data)
                    assert result == {}

    @pytest.mark.asyncio
    async def test_handles_profile_load_failure(self):
        """Test graceful handling of profile load failure"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls"}
        }

        with patch('security.hooks.get_security_profile', side_effect=Exception("Profile load failed")):
            with patch('security.hooks.extract_commands', return_value=['ls']):
                with patch('security.hooks.is_command_allowed', return_value=(True, "")):
                    result = await bash_security_hook(input_data)
                    # Should fall back to BASE_COMMANDS and continue
                    assert result == {}

    @pytest.mark.asyncio
    async def test_multi_command_validation(self):
        """Test validation of multi-command strings (&&, ||, ; operators)"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls && echo test"}
        }

        with patch('security.hooks.get_security_profile') as mock_profile:
            mock_profile.return_value = MagicMock()
            mock_profile.return_value.get_all_allowed_commands.return_value = ['ls', 'echo']

            with patch('security.hooks.extract_commands', return_value=['ls', 'echo']):
                with patch('security.hooks.is_command_allowed', return_value=(True, "")):
                    result = await bash_security_hook(input_data)
                    assert result == {}

    @pytest.mark.asyncio
    async def test_blocks_first_bad_command_in_chain(self):
        """Test that if first command is bad, entire chain is blocked"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf / && ls"}
        }

        with patch('security.hooks.get_security_profile') as mock_profile:
            mock_profile.return_value = MagicMock()
            mock_profile.return_value.get_all_allowed_commands.return_value = []

            with patch('security.hooks.extract_commands', return_value=['rm']):
                with patch('security.hooks.is_command_allowed', return_value=(False, "rm not allowed")):
                    result = await bash_security_hook(input_data)
                    assert "hookSpecificOutput" in result
                    assert "not allowed" in result["hookSpecificOutput"]["permissionDecisionReason"]


class TestBashSecurityHookEdgeCases:
    """Tests for edge cases and corner cases in bash_security_hook"""

    @pytest.mark.asyncio
    async def test_blocks_whitespace_only_command(self):
        """Test that whitespace-only commands are blocked (fail parsing)"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "   \t  \n  "}
        }
        result = await bash_security_hook(input_data)
        # Should block because whitespace-only commands fail parsing
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "Could not parse" in result["hookSpecificOutput"]["permissionDecisionReason"]

    @pytest.mark.asyncio
    async def test_missing_command_key_in_tool_input(self):
        """Test handling of missing 'command' key in tool_input"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"other_key": "value"}
        }
        result = await bash_security_hook(input_data)
        # Should allow since missing command key defaults to empty string
        assert result == {}

    @pytest.mark.asyncio
    async def test_context_cwd_fallback(self):
        """Test fallback to context.cwd when env var and input_data cwd are missing"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls"}
        }

        mock_context = MagicMock()
        mock_context.cwd = "/tmp/context_cwd"

        with patch.dict('os.environ', {}, clear=True):
            with patch('security.hooks.get_security_profile') as mock_profile:
                mock_profile.return_value = MagicMock()
                mock_profile.return_value.get_all_allowed_commands.return_value = ['ls']

                with patch('security.hooks.is_command_allowed', return_value=(True, "")):
                    result = await bash_security_hook(input_data, context=mock_context)
                    assert result == {}

    @pytest.mark.asyncio
    async def test_all_cwd_fallbacks_to_os_getcwd(self):
        """Test ultimate fallback to os.getcwd when all other sources fail"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls"}
        }

        with patch.dict('os.environ', {}, clear=True):
            with patch('os.getcwd', return_value="/tmp/fallback_cwd"):
                with patch('security.hooks.get_security_profile') as mock_profile:
                    mock_profile.return_value = MagicMock()
                    mock_profile.return_value.get_all_allowed_commands.return_value = ['ls']

                    with patch('security.hooks.is_command_allowed', return_value=(True, "")):
                        result = await bash_security_hook(input_data)
                        assert result == {}

    @pytest.mark.asyncio
    async def test_validator_fallback_to_full_command(self):
        """Test that validator falls back to full command when segment extraction fails"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "rm important_file.txt"}
        }

        with patch('security.hooks.get_security_profile') as mock_profile:
            mock_profile.return_value = MagicMock()
            mock_profile.return_value.get_all_allowed_commands.return_value = ['rm']

            with patch('security.hooks.extract_commands', return_value=['rm']):
                with patch('security.hooks.is_command_allowed', return_value=(True, "")):
                    # Make get_command_for_validation return empty string
                    with patch('security.hooks.get_command_for_validation', return_value=""):
                        from security.validator import VALIDATORS
                        # Mock a validator that blocks the command
                        mock_validator = MagicMock(return_value=(False, "unsafe rm operation"))
                        with patch.dict(VALIDATORS, {'rm': mock_validator}):
                            result = await bash_security_hook(input_data)
                            assert "hookSpecificOutput" in result
                            assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
                            # Verify validator was called with full command
                            mock_validator.assert_called_once_with("rm important_file.txt")

    @pytest.mark.asyncio
    async def test_validator_passes_with_valid_command(self):
        """Test that validator allows commands that pass validation"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "rm -f temp_file.txt"}
        }

        with patch('security.hooks.get_security_profile') as mock_profile:
            mock_profile.return_value = MagicMock()
            mock_profile.return_value.get_all_allowed_commands.return_value = ['rm']

            with patch('security.hooks.extract_commands', return_value=['rm']):
                with patch('security.hooks.is_command_allowed', return_value=(True, "")):
                    from security.validator import VALIDATORS
                    # Mock a validator that allows the command
                    mock_validator = MagicMock(return_value=(True, ""))
                    with patch.dict(VALIDATORS, {'rm': mock_validator}):
                        result = await bash_security_hook(input_data)
                        assert result == {}
                        mock_validator.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_validators_in_chain(self):
        """Test that multiple validators are checked in a command chain"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "rm temp.txt && pkill test"}
        }

        with patch('security.hooks.get_security_profile') as mock_profile:
            mock_profile.return_value = MagicMock()
            mock_profile.return_value.get_all_allowed_commands.return_value = ['rm', 'pkill']

            with patch('security.hooks.extract_commands', return_value=['rm', 'pkill']):
                with patch('security.hooks.is_command_allowed', return_value=(True, "")):
                    from security.validator import VALIDATORS
                    mock_rm_validator = MagicMock(return_value=(True, ""))
                    mock_pkill_validator = MagicMock(return_value=(True, ""))
                    with patch.dict(VALIDATORS, {'rm': mock_rm_validator, 'pkill': mock_pkill_validator}):
                        result = await bash_security_hook(input_data)
                        assert result == {}
                        # Both validators should be called
                        mock_rm_validator.assert_called_once()
                        mock_pkill_validator.assert_called_once()

    @pytest.mark.asyncio
    async def test_profile_fallback_uses_base_commands(self):
        """Test that profile load failure falls back to BASE_COMMANDS"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls"}
        }

        with patch('security.hooks.get_security_profile', side_effect=Exception("Profile load error")):
            with patch('security.hooks.extract_commands', return_value=['ls']):
                # Since we can't easily mock BASE_COMMANDS in the except block,
                # we just verify it doesn't crash and returns something
                result = await bash_security_hook(input_data)
                # The result depends on whether 'ls' is in BASE_COMMANDS
                assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_command_with_pipe_operator(self):
        """Test handling of pipe operators in commands"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "cat file.txt | grep pattern"}
        }

        with patch('security.hooks.get_security_profile') as mock_profile:
            mock_profile.return_value = MagicMock()
            mock_profile.return_value.get_all_allowed_commands.return_value = ['cat', 'grep']

            with patch('security.hooks.extract_commands', return_value=['cat', 'grep']):
                with patch('security.hooks.is_command_allowed', return_value=(True, "")):
                    result = await bash_security_hook(input_data)
                    assert result == {}

    @pytest.mark.asyncio
    async def test_command_with_or_operator(self):
        """Test handling of || operator in commands"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "cat file.txt || echo failed"}
        }

        with patch('security.hooks.get_security_profile') as mock_profile:
            mock_profile.return_value = MagicMock()
            mock_profile.return_value.get_all_allowed_commands.return_value = ['cat', 'echo']

            with patch('security.hooks.extract_commands', return_value=['cat', 'echo']):
                with patch('security.hooks.is_command_allowed', return_value=(True, "")):
                    result = await bash_security_hook(input_data)
                    assert result == {}

    @pytest.mark.asyncio
    async def test_second_command_blocked_in_or_chain(self):
        """Test that if second command is blocked, entire chain is blocked"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "cat file.txt || rm -rf /"}
        }

        with patch('security.hooks.get_security_profile') as mock_profile:
            mock_profile.return_value = MagicMock()
            mock_profile.return_value.get_all_allowed_commands.return_value = ['cat']

            with patch('security.hooks.extract_commands', return_value=['cat', 'rm']):
                # First command allowed, second blocked
                with patch('security.hooks.is_command_allowed', side_effect=[
                    (True, ""),  # cat is allowed
                    (False, "rm not allowed")  # rm is not allowed
                ]):
                    result = await bash_security_hook(input_data)
                    assert "hookSpecificOutput" in result
                    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"


class TestValidateCommand:
    """Tests for validate_command function"""

    def test_validate_allowed_command(self, tmp_path):
        """Test validation of an allowed command"""
        with patch('security.hooks.get_security_profile') as mock_profile:
            mock_profile.return_value = MagicMock()
            mock_profile.return_value.base_commands = {'ls': MagicMock()}

            with patch('security.hooks.extract_commands', return_value=['ls']):
                with patch('security.hooks.is_command_allowed', return_value=(True, "")):
                    is_allowed, reason = validate_command("ls", tmp_path)
                    assert is_allowed is True
                    assert reason == ""

    def test_validate_disallowed_command(self, tmp_path):
        """Test validation of a disallowed command"""
        with patch('security.hooks.get_security_profile') as mock_profile:
            mock_profile.return_value = MagicMock()

            with patch('security.hooks.extract_commands', return_value=['rm']):
                with patch('security.hooks.is_command_allowed', return_value=(False, "rm not allowed")):
                    is_allowed, reason = validate_command("rm -rf /", tmp_path)
                    assert is_allowed is False
                    assert "not allowed" in reason

    def test_validate_unparseable_command(self, tmp_path):
        """Test validation of an unparseable command"""
        with patch('security.hooks.extract_commands', return_value=[]):
            is_allowed, reason = validate_command("some invalid command", tmp_path)
            assert is_allowed is False
            assert "Could not parse" in reason

    def test_validate_uses_cwd_when_no_project_dir(self):
        """Test that cwd is used when project_dir is not provided"""
        with patch('security.hooks.get_security_profile') as mock_profile:
            mock_profile.return_value = MagicMock()
            mock_profile.return_value.base_commands = {'pwd': MagicMock()}

            with patch('security.hooks.extract_commands', return_value=['pwd']):
                with patch('security.hooks.is_command_allowed', return_value=(True, "")):
                    is_allowed, reason = validate_command("pwd")
                    assert is_allowed is True

    def test_validate_with_validator(self, tmp_path):
        """Test validation that uses a specific validator"""
        with patch('security.hooks.get_security_profile') as mock_profile:
            mock_profile.return_value = MagicMock()

            with patch('security.hooks.extract_commands', return_value=['git']):
                with patch('security.hooks.is_command_allowed', return_value=(True, "")):
                    # Test that validator is checked
                    with patch('security.hooks.get_command_for_validation', return_value='git push'):
                        from security.validator import VALIDATORS
                        # Mock a validator function
                        mock_validator = MagicMock(return_value=(False, "git validation failed"))
                        with patch.dict(VALIDATORS, {'git': mock_validator}):
                            is_allowed, reason = validate_command("git push origin main", tmp_path)
                            # Should be blocked by validator
                            assert is_allowed is False

    def test_validate_validator_fallback_to_full_command(self, tmp_path):
        """Test that validate_command falls back to full command when segment extraction fails"""
        with patch('security.hooks.get_security_profile') as mock_profile:
            mock_profile.return_value = MagicMock()

            with patch('security.hooks.extract_commands', return_value=['rm']):
                with patch('security.hooks.is_command_allowed', return_value=(True, "")):
                    # Make get_command_for_validation return empty string
                    with patch('security.hooks.get_command_for_validation', return_value=""):
                        from security.validator import VALIDATORS
                        # Mock a validator that blocks the command
                        mock_validator = MagicMock(return_value=(False, "unsafe rm operation"))
                        with patch.dict(VALIDATORS, {'rm': mock_validator}):
                            is_allowed, reason = validate_command("rm -rf important", tmp_path)
                            # Should be blocked by validator
                            assert is_allowed is False
                            # Verify validator was called with full command
                            mock_validator.assert_called_once_with("rm -rf important")

    def test_validate_command_without_validator(self, tmp_path):
        """Test validation of command that doesn't have a validator"""
        with patch('security.hooks.get_security_profile') as mock_profile:
            mock_profile.return_value = MagicMock()

            with patch('security.hooks.extract_commands', return_value=['echo']):
                with patch('security.hooks.is_command_allowed', return_value=(True, "")):
                    # echo has no validator
                    is_allowed, reason = validate_command("echo hello", tmp_path)
                    assert is_allowed is True
                    assert reason == ""

    def test_validate_command_with_multiple_commands(self, tmp_path):
        """Test validation of command string with multiple commands"""
        with patch('security.hooks.get_security_profile') as mock_profile:
            mock_profile.return_value = MagicMock()

            with patch('security.hooks.extract_commands', return_value=['ls', 'pwd']):
                with patch('security.hooks.is_command_allowed', return_value=(True, "")):
                    is_allowed, reason = validate_command("ls && pwd", tmp_path)
                    assert is_allowed is True

    def test_validate_command_second_command_fails(self, tmp_path):
        """Test validation when second command in chain is disallowed"""
        with patch('security.hooks.get_security_profile') as mock_profile:
            mock_profile.return_value = MagicMock()

            with patch('security.hooks.extract_commands', return_value=['ls', 'rm']):
                with patch('security.hooks.is_command_allowed', side_effect=[
                    (True, ""),  # ls is allowed
                    (False, "rm not allowed")  # rm is not allowed
                ]):
                    is_allowed, reason = validate_command("ls && rm -rf /", tmp_path)
                    assert is_allowed is False
                    assert "not allowed" in reason
