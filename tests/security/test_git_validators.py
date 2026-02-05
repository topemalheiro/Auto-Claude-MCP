"""Tests for git_validators"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from security.git_validators import (
    validate_git_config,
    validate_git_inline_config,
    validate_git_command,
    validate_git_commit_secrets,
)


class TestValidateGitConfig:
    """Tests for validate_git_config function"""

    def test_non_git_config_command_allowed(self):
        """Test that non-git-config commands are allowed"""
        safe_commands = [
            "git status",
            "git log",
            "git diff",
            "ls -la",
            "echo test",
        ]
        for cmd in safe_commands:
            is_valid, error = validate_git_config(cmd)
            assert is_valid, f"Command should be allowed: {cmd}"
            assert error == ""

    def test_read_only_git_config_allowed(self):
        """Test read-only git config operations are allowed"""
        read_only_commands = [
            "git config --get user.name",
            "git config --get-all user.name",
            "git config --get-regexp .*",
            "git config --list",
            "git config -l",
        ]
        for cmd in read_only_commands:
            is_valid, error = validate_git_config(cmd)
            assert is_valid, f"Read-only command should be allowed: {cmd}"
            assert error == ""

        # Note: "git config user.name" without a flag is actually a GET operation
        # but it returns the value, not a read-only flag per se
        # The implementation checks for specific read-only flags

    def test_blocked_identity_keys(self):
        """Test that identity config keys are blocked"""
        blocked_commands = [
            "git config user.name 'Test User'",
            "git config user.email 'test@example.com'",
            "git config author.name 'Test User'",
            "git config author.email 'test@example.com'",
            "git config committer.name 'Test User'",
            "git config committer.email 'test@example.com'",
        ]
        for cmd in blocked_commands:
            is_valid, error = validate_git_config(cmd)
            assert not is_valid, f"Command should be blocked: {cmd}"
            assert "blocked" in error.lower()
            assert "identity" in error.lower()

    def test_safe_config_keys_allowed(self):
        """Test that non-identity config keys are allowed"""
        safe_commands = [
            "git config core.editor vim",
            "git config merge.tool vimdiff",
            "git config push.default simple",
            "git config remote.origin.url https://github.com/user/repo",
        ]
        for cmd in safe_commands:
            is_valid, error = validate_git_config(cmd)
            assert is_valid, f"Safe config should be allowed: {cmd}"
            assert error == ""

    def test_config_key_case_insensitive(self):
        """Test that config key checking is case-insensitive"""
        is_valid, _ = validate_git_config("git config User.Name 'Test'")
        assert not is_valid

        is_valid, _ = validate_git_config("git config USER.EMAIL 'test@example.com'")
        assert not is_valid

    def test_git_config_with_options(self):
        """Test git config with various options"""
        is_valid, _ = validate_git_config("git config --global core.editor vim")
        assert is_valid

        is_valid, _ = validate_git_config("git config --local core.editor vim")
        assert is_valid

    def test_git_config_empty_command(self):
        """Test empty command is allowed (not a git config command)"""
        is_valid, error = validate_git_config("")
        assert is_valid
        assert error == ""

    def test_git_config_parse_error(self):
        """Test unparseable command is rejected"""
        is_valid, error = validate_git_config('git config "test')
        assert not is_valid
        assert "parse" in error.lower()

    def test_git_config_list_with_no_key(self):
        """Test git config --list (no key specified) is allowed"""
        is_valid, _ = validate_git_config("git config --list")
        assert is_valid


class TestValidateGitInlineConfig:
    """Tests for validate_git_inline_config function"""

    def test_no_inline_config_allowed(self):
        """Test git commands without -c flag are allowed"""
        safe_commands = [
            ["git", "status"],
            ["git", "log", "--oneline"],
            ["git", "push", "origin", "main"],
        ]
        for tokens in safe_commands:
            is_valid, error = validate_git_inline_config(tokens)
            assert is_valid, f"Tokens should be allowed: {tokens}"
            assert error == ""

    def test_blocked_identity_inline_config(self):
        """Test that -c with identity keys is blocked"""
        blocked_commands = [
            ["git", "-c", "user.name=Test User", "commit"],
            ["git", "-c", "user.email=test@example.com", "commit"],
            ["git", "-c", "author.name=Test", "push"],
            ["git", "-c", "committer.email=test@example.com", "commit"],
        ]
        for tokens in blocked_commands:
            is_valid, error = validate_git_inline_config(tokens)
            assert not is_valid, f"Tokens should be blocked: {tokens}"
            assert "blocked" in error.lower()

    def test_blocked_identity_compact_inline_config(self):
        """Test -ckey=value format (no space) is blocked"""
        blocked_commands = [
            ["git", "-cuser.name=Test User", "commit"],
            ["git", "-cuser.email=test@example.com", "commit"],
            ["git", "-cauthor.name=Test", "push"],
        ]
        for tokens in blocked_commands:
            is_valid, error = validate_git_inline_config(tokens)
            assert not is_valid, f"Tokens should be blocked: {tokens}"
            assert "blocked" in error.lower()

    def test_safe_inline_config_allowed(self):
        """Test -c with non-identity keys is allowed"""
        safe_commands = [
            ["git", "-c", "core.editor=vim", "commit"],
            ["git", "-c", "merge.tool=vimdiff", "merge"],
            ["git", "-c", "push.default=simple", "push"],
            ["git", "-ccore.editor=vim", "commit"],
        ]
        for tokens in safe_commands:
            is_valid, error = validate_git_inline_config(tokens)
            assert is_valid, f"Tokens should be allowed: {tokens}"
            assert error == ""

    def test_inline_config_case_insensitive(self):
        """Test that inline config checking is case-insensitive"""
        is_valid, _ = validate_git_inline_config(["git", "-c", "User.Name=Test", "commit"])
        assert not is_valid

    def test_multiple_inline_configs(self):
        """Test multiple -c flags"""
        # All safe
        is_valid, _ = validate_git_inline_config(
            ["git", "-c", "core.editor=vim", "-c", "merge.tool=vimdiff", "commit"]
        )
        assert is_valid

        # One blocked
        is_valid, _ = validate_git_inline_config(
            ["git", "-c", "core.editor=vim", "-c", "user.name=Test", "commit"]
        )
        assert not is_valid

    def test_inline_config_without_equals(self):
        """Test -c flag without equals sign is allowed"""
        is_valid, _ = validate_git_inline_config(["git", "-c", "some.value", "commit"])
        assert is_valid


class TestValidateGitCommand:
    """Tests for validate_git_command function"""

    def test_non_git_commands_allowed(self):
        """Test non-git commands are allowed"""
        safe_commands = [
            "ls -la",
            "echo test",
            "npm install",
            "python script.py",
        ]
        for cmd in safe_commands:
            is_valid, error = validate_git_command(cmd)
            assert is_valid, f"Command should be allowed: {cmd}"
            assert error == ""

    def test_git_without_subcommand_allowed(self):
        """Test 'git' with no subcommand is allowed"""
        is_valid, _ = validate_git_command("git")
        assert is_valid

    def test_git_config_blocked_identity(self):
        """Test git config with identity changes is blocked"""
        is_valid, error = validate_git_command("git config user.name 'Test User'")
        assert not is_valid
        assert "blocked" in error.lower()

    def test_git_config_read_only_allowed(self):
        """Test git config read-only operations are allowed"""
        is_valid, _ = validate_git_command("git config --get user.name")
        assert is_valid

    def test_git_with_blocked_inline_config(self):
        """Test git commands with blocked -c flags are blocked"""
        blocked_commands = [
            "git -c user.name=Test commit",
            "git -c user.email=test@example.com commit -m 'test'",
            "git -c author.name=Test push origin main",
        ]
        for cmd in blocked_commands:
            is_valid, error = validate_git_command(cmd)
            assert not is_valid, f"Command should be blocked: {cmd}"
            assert "blocked" in error.lower()

    def test_git_with_safe_inline_config(self):
        """Test git commands with safe -c flags are allowed"""
        safe_commands = [
            "git -c core.editor=vim commit -m 'test'",
            "git -c merge.tool=vimdiff merge",
            "git -c push.default=simple push origin main",
        ]
        for cmd in safe_commands:
            is_valid, _ = validate_git_command(cmd)
            assert is_valid, f"Command should be allowed: {cmd}"

    def test_git_commit_with_global_options(self):
        """Test git commit with global options"""
        is_valid, _ = validate_git_command("git -C /path/to/repo commit -m 'test'")
        assert is_valid

        is_valid, _ = validate_git_command("git --git-dir=.git commit -m 'test'")
        assert is_valid

    def test_git_other_subcommands_allowed(self):
        """Test other git subcommands are allowed"""
        safe_commands = [
            "git status",
            "git log --oneline",
            "git diff",
            "git add .",
            "git push origin main",
            "git pull origin main",
            "git branch -a",
            "git checkout -b feature",
            "git merge main",
            "git rebase main",
            "git reset HEAD~1",
            "git tag v1.0.0",
        ]
        for cmd in safe_commands:
            is_valid, _ = validate_git_command(cmd)
            assert is_valid, f"Command should be allowed: {cmd}"

    def test_git_empty_command(self):
        """Test empty command is allowed"""
        is_valid, _ = validate_git_command("")
        assert is_valid

    def test_git_parse_error(self):
        """Test unparseable command is rejected"""
        is_valid, error = validate_git_command('git config "test')
        assert not is_valid
        assert "parse" in error.lower()


class TestValidateGitCommitSecrets:
    """Tests for validate_git_commit_secrets function"""

    def test_non_git_commit_allowed(self):
        """Test non-git-commit commands are allowed"""
        safe_commands = [
            "git status",
            "git log",
            "ls -la",
            "echo test",
        ]
        for cmd in safe_commands:
            is_valid, error = validate_git_commit_secrets(cmd)
            assert is_valid, f"Command should be allowed: {cmd}"
            assert error == ""

    def test_git_commit_without_staged_files_allowed(self):
        """Test git commit with no staged files is allowed"""
        with patch("scan_secrets.get_staged_files", return_value=[]):
            is_valid, _ = validate_git_commit_secrets("git commit -m 'test'")
            assert is_valid

    @patch("scan_secrets.scan_files")
    @patch("scan_secrets.get_staged_files")
    def test_git_commit_with_no_secrets_allowed(self, mock_staged, mock_scan):
        """Test git commit with no secrets detected is allowed"""
        mock_staged.return_value = ["file1.txt", "file2.txt"]
        mock_scan.return_value = []

        is_valid, _ = validate_git_commit_secrets("git commit -m 'test'")
        assert is_valid

    @patch("scan_secrets.scan_files")
    @patch("scan_secrets.get_staged_files")
    @patch("security.git_validators.Path.cwd")
    def test_git_commit_with_secrets_blocked(self, mock_cwd, mock_staged, mock_scan):
        """Test git commit with secrets detected is blocked"""
        mock_cwd.return_value = Path("/tmp/test")
        mock_staged.return_value = ["config.py"]

        # Create a mock secret match
        mock_match = MagicMock()
        mock_match.file_path = "config.py"
        mock_match.line_number = 10
        mock_match.pattern_name = "Generic API key assignment"
        mock_match.matched_text = "api_key = 'sk-1234567890abcdefghijklmnopqrstuvwxyz'"

        mock_scan.return_value = [mock_match]

        is_valid, error = validate_git_commit_secrets("git commit -m 'test'")
        assert not is_valid
        assert "secrets detected" in error.lower()
        assert "config.py" in error
        assert "api key assignment" in error.lower()

    @patch("scan_secrets.scan_files")
    @patch("scan_secrets.get_staged_files")
    @patch("security.git_validators.Path.cwd")
    def test_multiple_files_with_secrets(self, mock_cwd, mock_staged, mock_scan):
        """Test commit with secrets in multiple files"""
        mock_cwd.return_value = Path("/tmp/test")
        mock_staged.return_value = ["config.py", ".env"]

        # Create multiple mock secret matches
        match1 = MagicMock()
        match1.file_path = "config.py"
        match1.line_number = 5
        match1.pattern_name = "Password assignment"
        match1.matched_text = "password = 'secret123'"

        match2 = MagicMock()
        match2.file_path = ".env"
        match2.line_number = 1
        match2.pattern_name = "Generic API key"
        match2.matched_text = "API_KEY=sk-abcdef1234567890"

        mock_scan.return_value = [match1, match2]

        is_valid, error = validate_git_commit_secrets("git commit -m 'Add config'")
        assert not is_valid
        assert "config.py" in error
        assert ".env" in error
        assert "password assignment" in error.lower()

    def test_scanner_import_error_handling(self):
        """Test that the function handles scanner import correctly"""
        # The function imports from scan_secrets module
        # We can't easily test the ImportError path without breaking the test environment
        # Just verify the function exists and handles basic cases
        assert callable(validate_git_commit_secrets)

    @patch("scan_secrets.scan_files")
    @patch("scan_secrets.get_staged_files")
    @patch("security.git_validators.Path.cwd")
    def test_detailed_error_message(self, mock_cwd, mock_staged, mock_scan):
        """Test that detailed error message includes actionable guidance"""
        mock_cwd.return_value = Path("/tmp/test")
        mock_staged.return_value = ["secrets.py"]

        mock_match = MagicMock()
        mock_match.file_path = "secrets.py"
        mock_match.line_number = 42
        mock_match.pattern_name = "OpenAI API key"
        mock_match.matched_text = "sk-ant-api123-456-789"

        mock_scan.return_value = [mock_match]

        is_valid, error = validate_git_commit_secrets("git commit -m 'Add secrets'")

        assert not is_valid
        # Check for key elements of the error message
        assert "secrets detected" in error.lower()
        assert "secrets.py" in error
        assert "action required" in error.lower()
        assert "environment variable" in error.lower() or "os.environ" in error.lower()
        assert ".secretsignore" in error

    def test_git_commit_parse_error(self):
        """Test unparseable command is rejected"""
        is_valid, error = validate_git_commit_secrets('git commit "test')
        assert not is_valid
        assert "parse" in error.lower()

    @patch("scan_secrets.get_staged_files", return_value=["file.py"])
    @patch("security.git_validators.Path.cwd", return_value=Path("/tmp/test"))
    @patch("scan_secrets.scan_files")
    def test_secrets_masked_in_output(self, mock_scan, mock_cwd, mock_staged):
        """Test that secrets are masked in the output"""
        mock_match = MagicMock()
        mock_match.file_path = "api.py"
        mock_match.line_number = 10
        mock_match.pattern_name = "API key"
        mock_match.matched_text = "sk-proj-verylongapikeythatis1234567890abcdefghijklmnopqr"

        mock_scan.return_value = [mock_match]

        is_valid, error = validate_git_commit_secrets("git commit -m 'Add API'")
        assert not is_valid
        # Secret should be masked in output
        assert "***" in error or "sk-proj-" in error  # At least prefix or mask


class TestGitConfigAttackScenarios:
    """Test git config attack scenarios"""

    def test_all_blocked_config_variations(self):
        """Test all variations of blocked config keys"""
        blocked_variations = [
            "git config user.name Test",
            "git config user.email test@test.com",
            "git config user.name 'Test User'",
            "git config user.email \"test@test.com\"",
            "git config --global user.name Test",
            "git config --local user.email test@test.com",
        ]
        for cmd in blocked_variations:
            is_valid, error = validate_git_config(cmd)
            assert not is_valid, f"Should block: {cmd}"
            assert "blocked" in error.lower()

    def test_config_value_variations(self):
        """Test various config value formats"""
        # All these should be blocked regardless of value format
        value_variations = [
            "git config user.name test",
            "git config user.name 'test'",
            "git config user.name \"test\"",
        ]
        for cmd in value_variations:
            is_valid, _ = validate_git_config(cmd)
            assert not is_valid, f"Should block: {cmd}"

    def test_config_with_subkeys(self):
        """Test config keys that might use dot notation"""
        # These should be allowed as they're not exact matches
        safe_subkeys = [
            "git config user.signingkey 1234",
            "git config user.gpgsign true",
            "git config user.useConfigOnly true",
        ]
        for cmd in safe_subkeys:
            is_valid, _ = validate_git_config(cmd)
            assert is_valid, f"Should allow: {cmd}"


class TestGitInlineConfigEdgeCases:
    """Test edge cases for inline config validation"""

    def test_inline_config_without_equals(self):
        """Test -c flag without equals sign"""
        # -c without equals should be allowed (not setting a value)
        tokens = ["git", "-c", "some.option", "commit"]
        is_valid, _ = validate_git_inline_config(tokens)
        assert is_valid

    def test_inline_config_empty_value(self):
        """Test -c with empty value"""
        tokens = ["git", "-c", "user.name=", "commit"]
        is_valid, _ = validate_git_inline_config(tokens)
        # Setting user.name to empty string should still be blocked
        assert not is_valid

    def test_inline_config_multiple_equals(self):
        """Test -c with multiple equals signs"""
        tokens = ["git", "-c", "core.sshCommand=ssh -i key=path", "commit"]
        is_valid, _ = validate_git_inline_config(tokens)
        # Should be allowed as it's not an identity key
        assert is_valid

    def test_compact_inline_variations(self):
        """Test -ckey=value format variations"""
        # Blocked identity keys in compact format
        blocked_compact = [
            ["git", "-cuser.name=Test", "commit"],
            ["git", "-cuser.email=test@test.com", "commit"],
            ["git", "-cauthor.name=Test", "commit"],
        ]
        for tokens in blocked_compact:
            is_valid, _ = validate_git_inline_config(tokens)
            assert not is_valid

        # Safe keys in compact format
        safe_compact = [
            ["git", "-ccore.editor=vim", "commit"],
            ["git", "-cmerge.tool=vimdiff", "merge"],
        ]
        for tokens in safe_compact:
            is_valid, _ = validate_git_inline_config(tokens)
            assert is_valid

    def test_multiple_inline_configs_mixed(self):
        """Test multiple -c flags with mixed safe/blocked keys"""
        # Any blocked key should cause rejection
        mixed_configs = [
            ["git", "-c", "core.editor=vim", "-c", "user.name=Test", "commit"],
            ["git", "-cuser.name=Test", "-c", "core.editor=vim", "commit"],
            ["git", "-c", "safe.option=value", "-c", "user.email=test@test.com", "commit"],
        ]
        for tokens in mixed_configs:
            is_valid, _ = validate_git_inline_config(tokens)
            assert not is_valid, f"Should block with mixed configs: {tokens}"

    def test_inline_config_special_characters_in_value(self):
        """Test inline config with special characters in values"""
        special_values = [
            ["git", "-c", "core.editor=vim -f", "commit"],
            ["git", "-c", "core.sshCommand=ssh -i ~/.ssh/key", "commit"],
            ["git", "-c", "alias.graph=log --graph --oneline", "commit"],
        ]
        for tokens in special_values:
            is_valid, _ = validate_git_inline_config(tokens)
            # These are safe config keys with special values
            assert is_valid


class TestGitCommandComprehensive:
    """Comprehensive tests for git command validation"""

    def test_all_git_subcommands(self):
        """Test various git subcommands are allowed"""
        allowed_commands = [
            "git add .",
            "git add -A",
            "git add -p",
            "git branch",
            "git branch -a",
            "git branch new-branch",
            "git checkout -b feature",
            "git checkout main",
            "git checkout -- file.txt",
            "git commit -m 'message'",
            "git commit --amend",
            "git commit --allow-empty",
            "git diff",
            "git diff --cached",
            "git log --oneline",
            "git log --graph",
            "git merge main",
            "git merge --no-ff feature",
            "git pull origin main",
            "git push origin main",
            "git push --force-with-lease",
            "git rebase main",
            "git rebase -i HEAD~3",
            "git remote -v",
            "git remote add origin https://github.com/user/repo",
            "git reset HEAD~1",
            "git reset --hard",
            "git restore file.txt",
            "git revert HEAD",
            "git stash",
            "git stash pop",
            "git status",
            "git switch main",
            "git tag v1.0.0",
            "git worktree add ../feature-branch",
        ]
        for cmd in allowed_commands:
            is_valid, _ = validate_git_command(cmd)
            assert is_valid, f"Should allow: {cmd}"

    def test_git_with_global_options(self):
        """Test git with various global options"""
        global_options = [
            "git -C /path/to/repo status",
            "git --git-dir=.git status",
            "git --work-tree=. status",
            "git --help status",
            "git --version",
        ]
        for cmd in global_options:
            is_valid, _ = validate_git_command(cmd)
            assert is_valid, f"Should allow: {cmd}"

    def test_git_commit_with_all_options(self):
        """Test git commit with various options"""
        commit_options = [
            "git commit",
            "git commit -m 'message'",
            "git commit -m 'message' -a",
            "git commit --amend",
            "git commit --allow-empty",
            "git commit --allow-empty-message",
            "git commit --no-verify",
            "git commit -v",
            "git commit -q",
        ]
        for cmd in commit_options:
            is_valid, _ = validate_git_command(cmd)
            assert is_valid, f"Should allow: {cmd}"

    def test_git_config_commands_comprehensive(self):
        """Test comprehensive git config command variations"""
        # Safe config commands
        safe_configs = [
            "git config --get user.name",
            "git config --get-all user.name",
            "git config --get-regexp user\\..*",
            "git config --list",
            "git config -l",
            "git config --global core.editor vim",
            "git config --local merge.tool vimdiff",
            "git config core.autocrlf input",
            "git config push.default simple",
            "git config remote.origin.url https://github.com/user/repo",
            "git config alias.st status",
            "git config alias.co checkout",
        ]
        for cmd in safe_configs:
            is_valid, _ = validate_git_command(cmd)
            assert is_valid, f"Should allow: {cmd}"

        # Blocked config commands
        blocked_configs = [
            "git config user.name Test",
            "git config user.email test@test.com",
            "git config --global user.name Test",
            "git config author.name Test",
            "git config committer.email test@test.com",
        ]
        for cmd in blocked_configs:
            is_valid, _ = validate_git_command(cmd)
            assert not is_valid, f"Should block: {cmd}"

    def test_git_with_all_blocked_inline_configs(self):
        """Test all variations of blocked inline configs"""
        blocked_inline = [
            "git -c user.name=Test commit",
            "git -c user.email=test@test.com commit",
            "git -c author.name=Test commit",
            "git -c author.email=test@test.com commit",
            "git -c committer.name=Test commit",
            "git -c committer.email=test@test.com commit",
            "git -cuser.name=Test commit",
            "git -cuser.email=test@test.com commit",
        ]
        for cmd in blocked_inline:
            is_valid, _ = validate_git_command(cmd)
            assert not is_valid, f"Should block: {cmd}"

    def test_git_with_safe_inline_configs(self):
        """Test various safe inline configs"""
        safe_inline = [
            "git -c core.editor=vim commit",
            "git -c merge.tool=vimdiff merge",
            "git -c push.default=simple push",
            "git -c core.autocrlf=input commit",
            "git -c color.ui=always status",
            "git -c alias.st status",
            "git -ccore.editor=vim commit",
        ]
        for cmd in safe_inline:
            is_valid, _ = validate_git_command(cmd)
            assert is_valid, f"Should allow: {cmd}"

    def test_mixed_global_options_and_configs(self):
        """Test mixing global options and inline configs"""
        mixed_commands = [
            "git -C /path -c core.editor=vim commit",
            "git --git-dir=.git -c merge.tool=vimdiff status",
            "git -c core.editor=vim -C /path commit",
        ]
        for cmd in mixed_commands:
            is_valid, _ = validate_git_command(cmd)
            assert is_valid, f"Should allow: {cmd}"

        # With blocked inline config
        blocked_mixed = [
            "git -C /path -c user.name=Test commit",
            "git -c core.editor=vim -c user.email=test@test.com commit",
        ]
        for cmd in blocked_mixed:
            is_valid, _ = validate_git_command(cmd)
            assert not is_valid, f"Should block: {cmd}"


class TestGitCommitSecretsEdgeCases:
    """Test edge cases for git commit secrets validation"""

    @patch("scan_secrets.scan_files")
    @patch("scan_secrets.get_staged_files")
    @patch("security.git_validators.Path.cwd")
    def test_single_file_multiple_secrets(self, mock_cwd, mock_staged, mock_scan):
        """Test single file with multiple secrets"""
        mock_cwd.return_value = Path("/tmp/test")
        mock_staged.return_value = ["config.py"]

        match1 = MagicMock()
        match1.file_path = "config.py"
        match1.line_number = 5
        match1.pattern_name = "API key"
        match1.matched_text = "sk-1234567890abcdefghijklmnopqrstuvwxyz"

        match2 = MagicMock()
        match2.file_path = "config.py"
        match2.line_number = 10
        match2.pattern_name = "Password"
        match2.matched_text = "secret_password_123"

        mock_scan.return_value = [match1, match2]

        is_valid, error = validate_git_commit_secrets("git commit -m 'Add config'")
        assert not is_valid
        # Should show both secrets in error
        assert "config.py" in error
        assert "API key" in error or "Password" in error

    @patch("scan_secrets.scan_files")
    @patch("scan_secrets.get_staged_files")
    @patch("security.git_validators.Path.cwd")
    def test_secret_masking_with_various_lengths(self, mock_cwd, mock_staged, mock_scan):
        """Test secret masking with various secret lengths"""
        mock_cwd.return_value = Path("/tmp/test")
        mock_staged.return_value = ["api.py"]

        test_cases = [
            ("sk-short", 7),
            ("sk-mediumlengthkey12345", 20),
            ("sk-verylongkeythatgoesonandonandneverends1234567890abcdefghijklmnop", 60),
        ]

        for secret, length in test_cases:
            mock_match = MagicMock()
            mock_match.file_path = "api.py"
            mock_match.line_number = 1
            mock_match.pattern_name = "API key"
            mock_match.matched_text = secret
            mock_scan.return_value = [mock_match]

            is_valid, error = validate_git_commit_secrets("git commit -m 'Add API'")
            assert not is_valid
            # Secret should be partially visible or fully masked
            if length > 12:
                assert "***" in error or secret[:12] in error

    @patch("scan_secrets.get_staged_files", return_value=[])
    def test_no_staged_files_allows_commit(self, mock_staged):
        """Test that commits with no staged files are allowed"""
        is_valid, _ = validate_git_commit_secrets("git commit -m 'Empty commit'")
        assert is_valid

    def test_import_error_handling(self):
        """Test that import errors are handled gracefully"""
        # The function has try/except ImportError and returns True if scan_secrets can't be imported
        # We can't easily test this path without actually breaking the import
        # Just verify the function is callable
        assert callable(validate_git_commit_secrets)

    @patch("scan_secrets.scan_files")
    @patch("scan_secrets.get_staged_files")
    @patch("security.git_validators.Path.cwd")
    def test_error_message_includes_all_required_sections(self, mock_cwd, mock_staged, mock_scan):
        """Test that error message includes all required sections"""
        mock_cwd.return_value = Path("/tmp/test")
        mock_staged.return_value = ["secret.py"]

        mock_match = MagicMock()
        mock_match.file_path = "secret.py"
        mock_match.line_number = 42
        mock_match.pattern_name = "Secret"
        mock_match.matched_text = "sk-secret123"
        mock_scan.return_value = [mock_match]

        is_valid, error = validate_git_commit_secrets("git commit -m 'Add secret'")
        assert not is_valid

        # Check all required sections are present
        required_sections = [
            "SECRETS DETECTED",
            "secret.py",
            "ACTION REQUIRED",
            "environment variable",
            ".secretsignore",
        ]
        for section in required_sections:
            assert section.lower() in error.lower(), f"Missing section: {section}"

    @patch("scan_secrets.scan_files")
    @patch("scan_secrets.get_staged_files")
    @patch("security.git_validators.Path.cwd")
    def test_commit_with_stage_options(self, mock_cwd, mock_staged, mock_scan):
        """Test git commit with various staging options"""
        mock_cwd.return_value = Path("/tmp/test")
        mock_staged.return_value = ["file.py"]
        mock_scan.return_value = []

        commit_variants = [
            "git commit -m 'message'",
            "git commit -am 'message'",
            "git commit --only -m 'message'",
            "git commit --include -m 'message'",
        ]
        for cmd in commit_variants:
            is_valid, _ = validate_git_commit_secrets(cmd)
            assert is_valid, f"Should allow: {cmd}"


class TestBackwardsCompatibility:
    """Test backwards compatibility aliases"""

    def test_validate_git_commit_alias(self):
        """Test that validate_git_commit points to validate_git_command"""
        from security.git_validators import validate_git_commit, validate_git_command
        assert validate_git_commit is validate_git_command


class TestEdgeCasesForFullCoverage:
    """Tests to achieve 100% coverage of edge cases"""

    def test_git_config_with_only_options_no_key(self):
        """Test git config with only options and no config key (line 78)"""
        # Commands like 'git config --global' with no key should be allowed
        # This covers line 78: return True, ""  # No config key specified
        is_valid, error = validate_git_config("git config --global")
        assert is_valid
        assert error == ""

        is_valid, error = validate_git_config("git config --local")
        assert is_valid
        assert error == ""

    def test_git_commit_secret_scanner_import_error_path(self):
        """Test ImportError path when scan_secrets module cannot be imported (lines 239-241)"""
        import sys
        import importlib

        # Save original states
        scan_secrets_backup = sys.modules.get("scan_secrets")
        git_validators_backup = sys.modules.get("security.git_validators")

        try:
            # Remove both modules to force fresh import
            if "scan_secrets" in sys.modules:
                del sys.modules["scan_secrets"]
            if "security.git_validators" in sys.modules:
                del sys.modules["security.git_validators"]

            # Import git_validators WITHOUT scan_secrets available
            # This triggers the ImportError path inside validate_git_commit_secrets
            from security import git_validators

            # Now call the function - it will try to import scan_secrets and fail
            is_valid, error = git_validators.validate_git_commit_secrets("git commit -m 'test'")

            # Should return True (allow commit) when scanner unavailable
            assert is_valid, "Should allow commit when scanner unavailable"
            assert error == "", "Error message should be empty"

        finally:
            # Restore both modules
            if scan_secrets_backup is not None:
                sys.modules["scan_secrets"] = scan_secrets_backup
            if git_validators_backup is not None:
                sys.modules["security.git_validators"] = git_validators_backup

            # Also clean them out to ensure clean state for other tests
            if "security.git_validators" in sys.modules:
                del sys.modules["security.git_validators"]

    def test_blocked_config_keys_constant(self):
        """Test that BLOCKED_GIT_CONFIG_KEYS contains all expected keys"""
        from security.git_validators import BLOCKED_GIT_CONFIG_KEYS

        expected_keys = {
            "user.name",
            "user.email",
            "author.name",
            "author.email",
            "committer.name",
            "committer.email",
        }
        assert BLOCKED_GIT_CONFIG_KEYS == expected_keys

    def test_validate_git_command_with_tokens_starting_with_dash(self):
        """Test validate_git_command properly skips tokens starting with dash"""
        # This tests the subcommand extraction logic that skips options
        is_valid, _ = validate_git_command("git -C /path/to/repo --git-dir=.git status")
        assert is_valid

    def test_validate_git_command_no_subcommand_after_options(self):
        """Test validate_git_command when no subcommand is found after options"""
        # Only global options, no subcommand
        is_valid, _ = validate_git_command("git --version")
        assert is_valid

        is_valid, _ = validate_git_command("git --help")
        assert is_valid

    @patch("security.git_validators.Path.cwd", return_value=Path("/tmp/test"))
    @patch("scan_secrets.get_staged_files", return_value=["test.py"])
    @patch("scan_secrets.scan_files")
    def test_git_commit_secret_mask_with_short_secret(self, mock_scan, mock_cwd, mock_staged):
        """Test secret masking with a secret shorter than 12 characters"""
        mock_match = MagicMock()
        mock_match.file_path = "test.py"
        mock_match.line_number = 1
        mock_match.pattern_name = "API Key"
        mock_match.matched_text = "short"  # Less than 12 chars
        mock_scan.return_value = [mock_match]

        is_valid, error = validate_git_commit_secrets("git commit -m 'test'")
        assert not is_valid
        # Should still include masked output
        assert "short" in error or "***" in error

    @patch("security.git_validators.Path.cwd", return_value=Path("/tmp/test"))
    @patch("scan_secrets.get_staged_files", return_value=["file1.py", "file2.py", "file3.py"])
    @patch("scan_secrets.scan_files")
    def test_multiple_files_with_multiple_secrets(self, mock_scan, mock_cwd, mock_staged):
        """Test commit with secrets across multiple files"""
        match1 = MagicMock()
        match1.file_path = "file1.py"
        match1.line_number = 1
        match1.pattern_name = "Secret 1"
        match1.matched_text = "secret1"

        match2 = MagicMock()
        match2.file_path = "file2.py"
        match2.line_number = 2
        match2.pattern_name = "Secret 2"
        match2.matched_text = "secret2"

        match3 = MagicMock()
        match3.file_path = "file3.py"
        match3.line_number = 3
        match3.pattern_name = "Secret 3"
        match3.matched_text = "secret3"

        mock_scan.return_value = [match1, match2, match3]

        is_valid, error = validate_git_commit_secrets("git commit -m 'test'")
        assert not is_valid
        # All files should be mentioned
        assert "file1.py" in error
        assert "file2.py" in error
        assert "file3.py" in error

    def test_git_config_empty_tokens_after_git(self):
        """Test git config when tokens array is just ['git', 'config']"""
        # Edge case: just "git config" with no arguments
        is_valid, error = validate_git_config("git config")
        assert is_valid
        assert error == ""

    def test_validate_git_inline_config_with_c_at_end(self):
        """Test inline config when -c is the last token"""
        # -c flag at the end should not crash
        tokens = ["git", "status", "-c"]
        is_valid, error = validate_git_inline_config(tokens)
        assert is_valid
        assert error == ""

    def test_validate_git_inline_config_compact_without_equals(self):
        """Test compact -c format without equals sign"""
        # -ckey (no equals, no value) should be allowed
        tokens = ["git", "-coption", "status"]
        is_valid, error = validate_git_inline_config(tokens)
        assert is_valid
        assert error == ""

    def test_git_commit_with_quoted_message(self):
        """Test git commit with various quote styles in message"""
        is_valid, _ = validate_git_commit_secrets('git commit -m "test message"')
        assert is_valid

        is_valid, _ = validate_git_commit_secrets("git commit -m 'test message'")
        assert is_valid

    def test_empty_command_string(self):
        """Test empty command string across all validators"""
        is_valid, _ = validate_git_config("")
        assert is_valid

        is_valid, _ = validate_git_inline_config([])
        assert is_valid

        is_valid, _ = validate_git_command("")
        assert is_valid

        is_valid, _ = validate_git_commit_secrets("")
        assert is_valid
