"""Tests for shell_validators"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from security.shell_validators import (
    SHELL_INTERPRETERS,
    _extract_c_argument,
    validate_bash_command,
    validate_sh_command,
    validate_shell_c_command,
    validate_zsh_command,
)


class TestExtractCArgument:
    """Tests for _extract_c_argument function"""

    def test_valid_bash_c_single_quote(self):
        """Test extracting command from bash -c 'command'"""
        result = _extract_c_argument("bash -c 'npm test'")
        assert result == "npm test"

    def test_valid_bash_c_double_quote(self):
        """Test extracting command from bash -c "command\""""
        result = _extract_c_argument('bash -c "npm test"')
        assert result == "npm test"

    def test_valid_sh_c_single_quote(self):
        """Test extracting command from sh -c 'cmd1 && cmd2'"""
        result = _extract_c_argument("sh -c 'ls && echo test'")
        assert result == "ls && echo test"

    def test_valid_zsh_c_double_quote(self):
        """Test extracting command from zsh -c "complex command\""""
        result = _extract_c_argument('zsh -c "git status && git log"')
        assert result == "git status && git log"

    def test_combined_flags_xc(self):
        """Test extracting command with -xc flag (combined flags)"""
        result = _extract_c_argument("bash -xc 'echo test'")
        assert result == "echo test"

    def test_combined_flags_ec(self):
        """Test extracting command with -ec flag (combined flags)"""
        result = _extract_c_argument("bash -ec 'npm install'")
        assert result == "npm install"

    def test_combined_flags_ic(self):
        """Test extracting command with -ic flag (combined flags)"""
        result = _extract_c_argument("bash -ic 'ls -la'")
        assert result == "ls -la"

    def test_combined_flags_exc(self):
        """Test extracting command with -exc flag (combined flags)"""
        result = _extract_c_argument("bash -exc 'echo test'")
        assert result == "echo test"

    def test_c_flag_with_path(self):
        """Test extracting command with full path to bash"""
        result = _extract_c_argument("/bin/bash -c 'ls'")
        assert result == "ls"

    def test_windows_path_bash(self):
        """Test extracting command with Windows-style bash path"""
        result = _extract_c_argument('C:\\Windows\\System32\\bash.exe -c "ls"')
        assert result == "ls"

    def test_non_c_invocation_script(self):
        """Test non -c invocation (e.g., bash script.sh)"""
        result = _extract_c_argument("bash script.sh")
        assert result is None

    def test_non_c_invocation_interactive(self):
        """Test non -c invocation (e.g., bash -i)"""
        result = _extract_c_argument("bash -i")
        assert result is None

    def test_non_c_invocation_login(self):
        """Test non -c invocation (e.g., bash -l)"""
        result = _extract_c_argument("bash -l")
        assert result is None

    def test_empty_command(self):
        """Test extracting empty command"""
        result = _extract_c_argument("bash -c ''")
        assert result == ""

    def test_c_without_command(self):
        """Test -c flag without following command"""
        result = _extract_c_argument("bash -c")
        assert result is None

    def test_too_short_command(self):
        """Test command string that's too short"""
        result = _extract_c_argument("bash")
        assert result is None

    def test_malformed_unclosed_single_quote(self):
        """Test malformed command with unclosed single quote"""
        result = _extract_c_argument("bash -c 'unclosed")
        assert result is None

    def test_malformed_unclosed_double_quote(self):
        """Test malformed command with unclosed double quote"""
        result = _extract_c_argument('bash -c "unclosed')
        assert result is None

    def test_c_after_other_flags(self):
        """Test -c flag appearing after other flags"""
        result = _extract_c_argument("bash -l -c 'ls'")
        assert result == "ls"

    def test_multiple_commands_in_quotes(self):
        """Test multiple commands in -c string"""
        result = _extract_c_argument("bash -c 'cd /tmp && ls && pwd'")
        assert result == "cd /tmp && ls && pwd"

    def test_command_with_pipes(self):
        """Test command with pipes"""
        result = _extract_c_argument('bash -c "cat file | grep test"')
        assert result == "cat file | grep test"

    def test_command_with_redirection(self):
        """Test command with redirection"""
        result = _extract_c_argument('bash -c "echo test > file.txt"')
        assert result == "echo test > file.txt"


class TestValidateShellCCommand:
    """Tests for validate_shell_c_command function"""

    def test_non_c_invocation_simple_script(self, tmp_path):
        """Test non -c invocation (bash script.sh) is allowed"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                result = validate_shell_c_command("bash script.sh")
                assert result == (True, "")

    def test_non_c_invocation_with_flags(self, tmp_path):
        """Test non -c invocation with flags (bash -l script.sh)"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                result = validate_shell_c_command("bash -l script.sh")
                assert result == (True, "")

    def test_process_substitution_input_blocked(self, tmp_path):
        """Test process substitution <(...) is blocked"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            result = validate_shell_c_command("bash script.sh <(cmd)")
            assert result[0] is False
            assert "Process substitution" in result[1]

    def test_process_substitution_output_blocked(self, tmp_path):
        """Test process substitution >(...) is blocked"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            result = validate_shell_c_command("bash script.sh >(cmd)")
            assert result[0] is False
            assert "Process substitution" in result[1]

    def test_command_substitution_allowed_in_non_c(self, tmp_path):
        """Test command substitution in non -c is allowed (not process substitution)"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                # $(...) is command substitution, not process substitution
                # Process substitution is <(...) or >(...)
                result = validate_shell_c_command("bash script.sh $(cmd)")
                assert result == (True, "")

    def test_empty_c_command_allowed(self, tmp_path):
        """Test empty -c command is allowed"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                result = validate_shell_c_command("bash -c ''")
                assert result == (True, "")

    def test_whitespace_only_c_command_allowed(self, tmp_path):
        """Test whitespace-only -c command is allowed"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                result = validate_shell_c_command("bash -c '   '")
                assert result == (True, "")

    def test_c_command_with_allowed_commands(self, tmp_path):
        """Test -c command with allowed commands"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                with patch("security.shell_validators.is_command_allowed", return_value=(True, "")):
                    result = validate_shell_c_command("bash -c 'npm test'")
                    assert result == (True, "")

    def test_c_command_with_disallowed_command(self, tmp_path):
        """Test -c command with disallowed command"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                with patch(
                    "security.shell_validators.is_command_allowed",
                    return_value=(False, "rm not allowed"),
                ):
                    result = validate_shell_c_command("bash -c 'rm -rf /'")
                    assert result[0] is False
                    assert "not allowed" in result[1]

    def test_c_command_multiple_commands_one_disallowed(self, tmp_path):
        """Test -c command with multiple commands where one is disallowed"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()

                def mock_is_allowed(cmd, profile):
                    return (cmd == "ls", f"{cmd} not allowed" if cmd != "ls" else "")

                with patch("security.shell_validators.is_command_allowed", side_effect=mock_is_allowed):
                    result = validate_shell_c_command("bash -c 'ls && rm file'")
                    assert result[0] is False
                    assert "rm" in result[1]

    def test_profile_load_failure_fails_safe(self, tmp_path):
        """Test that profile load failure fails safe (blocks)"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile", side_effect=Exception("Load failed")):
                result = validate_shell_c_command("bash -c 'npm test'")
                assert result[0] is False
                assert "Could not load security profile" in result[1]

    def test_nested_shell_bash_in_bash(self, tmp_path):
        """Test nested bash invocation in -c command"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                with patch("security.shell_validators.is_command_allowed", return_value=(True, "")):
                    result = validate_shell_c_command("bash -c 'bash -c \"echo test\"'")
                    assert result == (True, "")

    def test_nested_shell_disallowed_inner_command(self, tmp_path):
        """Test nested shell where inner command is disallowed"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()

                def mock_is_allowed(cmd, profile):
                    # Outer bash and sh are allowed, but inner rm is not
                    if cmd in ("bash", "sh"):
                        return (True, "")
                    return (False, f"{cmd} not allowed")

                with patch("security.shell_validators.is_command_allowed", side_effect=mock_is_allowed):
                    result = validate_shell_c_command('bash -c \'sh -c "rm -rf /"\'')
                    assert result[0] is False
                    assert "Nested shell command not allowed" in result[1]

    def test_nested_sh_in_bash(self, tmp_path):
        """Test nested sh in bash -c"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                with patch("security.shell_validators.is_command_allowed", return_value=(True, "")):
                    result = validate_shell_c_command('bash -c "sh -c \'echo test\'"')
                    assert result == (True, "")

    def test_nested_zsh_in_bash(self, tmp_path):
        """Test nested zsh in bash -c"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                with patch("security.shell_validators.is_command_allowed", return_value=(True, "")):
                    result = validate_shell_c_command('bash -c "zsh -c \'echo test\'"')
                    assert result == (True, "")

    def test_cross_platform_windows_path_in_c(self, tmp_path):
        """Test Windows path in -c command"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                with patch("security.shell_validators.is_command_allowed", return_value=(True, "")):
                    result = validate_shell_c_command('bash -c "C:\\\\Python312\\\\python.exe script.py"')
                    assert result == (True, "")

    def test_cross_platform_unix_path_in_c(self, tmp_path):
        """Test Unix path in -c command"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                with patch("security.shell_validators.is_command_allowed", return_value=(True, "")):
                    result = validate_shell_c_command('bash -c "/usr/bin/python3 script.py"')
                    assert result == (True, "")

    def test_non_c_with_full_path_shell(self, tmp_path):
        """Test non -c invocation with full path to shell"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                result = validate_shell_c_command("/bin/bash script.sh")
                assert result == (True, "")

    def test_non_c_with_windows_path_shell(self, tmp_path):
        """Test non -c invocation with Windows path to shell"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                result = validate_shell_c_command("C:\\Windows\\System32\\bash.exe script.sh")
                assert result == (True, "")

    def test_c_command_with_chaining_operators(self, tmp_path):
        """Test -c command with chaining operators (&&, ||, ;)"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                with patch("security.shell_validators.is_command_allowed", return_value=(True, "")):
                    result = validate_shell_c_command("bash -c 'npm install && npm test || echo failed'")
                    assert result == (True, "")

    def test_c_command_with_pipes(self, tmp_path):
        """Test -c command with pipes"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                with patch("security.shell_validators.is_command_allowed", return_value=(True, "")):
                    result = validate_shell_c_command('bash -c "cat file.txt | grep test | wc -l"')
                    assert result == (True, "")

    def test_c_command_with_background_job(self, tmp_path):
        """Test -c command with background job (&)"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                with patch("security.shell_validators.is_command_allowed", return_value=(True, "")):
                    result = validate_shell_c_command('bash -c "long_command &"')
                    assert result == (True, "")

    def test_unparseable_c_command_blocked(self, tmp_path):
        """Test unparseable -c command is blocked"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                with patch("security.shell_validators.extract_commands", return_value=[]):
                    result = validate_shell_c_command('bash -c "complex command"')
                    assert result[0] is False
                    assert "Could not parse commands" in result[1]

    def test_no_project_dir_env_var_uses_cwd(self, tmp_path):
        """Test that PROJECT_DIR env var is respected"""
        with patch.dict(os.environ, {}, clear=False):
            # Remove PROJECT_DIR if set
            os.environ.pop("PROJECT_DIR", None)
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                with patch("security.shell_validators.is_command_allowed", return_value=(True, "")):
                    result = validate_shell_c_command("bash -c 'ls'")
                    assert result == (True, "")


class TestShellInterpreterAliases:
    """Tests for shell interpreter alias functions"""

    def test_validate_bash_command_alias(self, tmp_path):
        """Test validate_bash_command is an alias for validate_shell_c_command"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                with patch("security.shell_validators.is_command_allowed", return_value=(True, "")):
                    result1 = validate_bash_command("bash -c 'ls'")
                    result2 = validate_shell_c_command("bash -c 'ls'")
                    assert result1 == result2

    def test_validate_sh_command_alias(self, tmp_path):
        """Test validate_sh_command is an alias for validate_shell_c_command"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                with patch("security.shell_validators.is_command_allowed", return_value=(True, "")):
                    result1 = validate_sh_command("sh -c 'ls'")
                    result2 = validate_shell_c_command("sh -c 'ls'")
                    assert result1 == result2

    def test_validate_zsh_command_alias(self, tmp_path):
        """Test validate_zsh_command is an alias for validate_shell_c_command"""
        with patch.dict(os.environ, {"PROJECT_DIR": str(tmp_path)}):
            with patch("security.shell_validators.get_security_profile") as mock_profile:
                mock_profile.return_value = MagicMock()
                with patch("security.shell_validators.is_command_allowed", return_value=(True, "")):
                    result1 = validate_zsh_command("zsh -c 'ls'")
                    result2 = validate_shell_c_command("zsh -c 'ls'")
                    assert result1 == result2


class TestShellInterpretersConstant:
    """Tests for SHELL_INTERPRETERS constant"""

    def test_shell_interpreters_contains_expected_shells(self):
        """Test that SHELL_INTERPRETERS contains expected shells"""
        assert "bash" in SHELL_INTERPRETERS
        assert "sh" in SHELL_INTERPRETERS
        assert "zsh" in SHELL_INTERPRETERS

    def test_shell_interpreters_is_set(self):
        """Test that SHELL_INTERPRETERS is a set"""
        assert isinstance(SHELL_INTERPRETERS, set)

    def test_shell_interpreters_has_correct_count(self):
        """Test that SHELL_INTERPRETERS has expected number of shells"""
        assert len(SHELL_INTERPRETERS) == 3
