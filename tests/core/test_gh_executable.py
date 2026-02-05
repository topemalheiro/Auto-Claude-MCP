"""Tests for gh_executable"""

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.gh_executable import (
    _find_gh_executable,
    _run_where_command,
    _verify_gh_executable,
    get_gh_executable,
    invalidate_gh_cache,
    run_gh,
)


class TestVerifyGhExecutable:
    """Tests for _verify_gh_executable function"""

    def test_verify_gh_executable_valid(self):
        """Test verification with valid gh executable"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            # Act
            result = _verify_gh_executable("/usr/bin/gh")

            # Assert
            assert result is True

    def test_verify_gh_executable_invalid(self):
        """Test verification with invalid gh executable"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("subprocess.run", return_value=mock_result):
            # Act
            result = _verify_gh_executable("/usr/bin/gh")

            # Assert
            assert result is False

    def test_verify_gh_executable_timeout(self):
        """Test verification handles timeout"""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("gh", 5)):
            # Act
            result = _verify_gh_executable("/usr/bin/gh")

            # Assert
            assert result is False

    def test_verify_gh_executable_os_error(self):
        """Test verification handles OS error"""
        with patch("subprocess.run", side_effect=OSError("Command failed")):
            # Act
            result = _verify_gh_executable("/usr/bin/gh")

            # Assert
            assert result is False


class TestRunWhereCommand:
    """Tests for _run_where_command function"""

    @patch("os.name", "nt")
    def test_run_where_command_success(self):
        """Test successful 'where' command on Windows"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "C:\\Program Files\\GitHub CLI\\gh.exe\nC:\\other\\gh.exe"

        with patch("subprocess.run", return_value=mock_result):
            with patch("os.path.isfile", return_value=True):
                with patch("core.gh_executable._verify_gh_executable", return_value=True):
                    # Act
                    result = _run_where_command()

                    # Assert
                    assert result == "C:\\Program Files\\GitHub CLI\\gh.exe"

    @patch("os.name", "nt")
    def test_run_where_command_no_output(self):
        """Test 'where' command with no output"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            # Act
            result = _run_where_command()

            # Assert
            assert result is None

    @patch("os.name", "nt")
    def test_run_where_command_failure(self):
        """Test 'where' command failure"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("subprocess.run", return_value=mock_result):
            # Act
            result = _run_where_command()

            # Assert
            assert result is None

    @patch("os.name", "nt")
    def test_run_where_command_timeout(self):
        """Test 'where' command timeout"""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("where", 5)):
            # Act
            result = _run_where_command()

            # Assert
            assert result is None

    @patch("os.name", "nt")
    def test_run_where_command_os_error(self):
        """Test 'where' command OS error"""
        with patch("subprocess.run", side_effect=OSError("Command failed")):
            # Act
            result = _run_where_command()

            # Assert
            assert result is None

    @patch("os.name", "nt")
    def test_run_where_command_file_not_exists(self):
        """Test 'where' command when file doesn't exist"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "C:\\Program Files\\GitHub CLI\\gh.exe"

        with patch("subprocess.run", return_value=mock_result):
            with patch("os.path.isfile", return_value=False):
                # Act
                result = _run_where_command()

                # Assert
                assert result is None

    @patch("os.name", "nt")
    def test_run_where_command_invalid_executable(self):
        """Test 'where' command when executable is invalid"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "C:\\Program Files\\GitHub CLI\\gh.exe"

        with patch("subprocess.run", return_value=mock_result):
            with patch("os.path.isfile", return_value=True):
                with patch("core.gh_executable._verify_gh_executable", return_value=False):
                    # Act
                    result = _run_where_command()

                    # Assert
                    assert result is None


class TestFindGhExecutable:
    """Tests for _find_gh_executable function"""

    def test_find_gh_from_env_var(self):
        """Test finding gh from GITHUB_CLI_PATH environment variable"""
        # Arrange
        env_path = "/custom/path/to/gh"

        with patch.dict(os.environ, {"GITHUB_CLI_PATH": env_path}):
            with patch("os.path.isfile", return_value=True):
                with patch("core.gh_executable._verify_gh_executable", return_value=True):
                    # Act
                    result = _find_gh_executable()

                    # Assert
                    assert result == env_path

    def test_find_gh_from_env_var_not_file(self):
        """Test GITHUB_CLI_PATH when path is not a file"""
        # Arrange
        env_path = "/custom/path/to/gh"

        with patch.dict(os.environ, {"GITHUB_CLI_PATH": env_path}):
            with patch("os.path.isfile", return_value=False):
                with patch("shutil.which", return_value=None):
                    # Act
                    result = _find_gh_executable()

                    # Assert
                    assert result is None

    def test_find_gh_from_env_var_invalid(self):
        """Test GITHUB_CLI_PATH when executable is invalid"""
        # Arrange
        env_path = "/custom/path/to/gh"

        with patch.dict(os.environ, {"GITHUB_CLI_PATH": env_path}):
            with patch("os.path.isfile", return_value=True):
                with patch("core.gh_executable._verify_gh_executable", return_value=False):
                    with patch("shutil.which", return_value=None):
                        # Act
                        result = _find_gh_executable()

                        # Assert
                        assert result is None

    def test_find_gh_from_path(self):
        """Test finding gh from PATH via shutil.which"""
        # Arrange
        path_result = "/usr/bin/gh"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_CLI_PATH", None)

        with patch("shutil.which", return_value=path_result):
            with patch("core.gh_executable._verify_gh_executable", return_value=True):
                # Act
                result = _find_gh_executable()

                # Assert
                assert result == path_result

    def test_find_gh_from_path_invalid(self):
        """Test shutil.which returns invalid executable"""
        # Arrange
        path_result = "/usr/bin/gh"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_CLI_PATH", None)

        with patch("shutil.which", return_value=path_result):
            with patch("core.gh_executable._verify_gh_executable", return_value=False):
                # Act
                result = _find_gh_executable()

                # Assert
                assert result is None

    @patch("os.name", "posix")
    def test_find_gh_homebrew_apple_silicon(self):
        """Test finding gh from Homebrew on Apple Silicon"""
        # Arrange
        homebrew_path = "/opt/homebrew/bin/gh"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_CLI_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.isfile", side_effect=lambda p: p == homebrew_path):
                with patch("core.gh_executable._verify_gh_executable", return_value=True):
                    # Act
                    result = _find_gh_executable()

                    # Assert
                    assert result == homebrew_path

    @patch("os.name", "posix")
    def test_find_gh_homebrew_intel(self):
        """Test finding gh from Homebrew on Intel Mac"""
        # Arrange
        homebrew_path = "/usr/local/bin/gh"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_CLI_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.isfile", side_effect=lambda p: p == homebrew_path):
                with patch("core.gh_executable._verify_gh_executable", return_value=True):
                    # Act
                    result = _find_gh_executable()

                    # Assert
                    assert result == homebrew_path

    @patch("os.name", "posix")
    def test_find_gh_linuxbrew(self):
        """Test finding gh from Linuxbrew"""
        # Arrange
        linuxbrew_path = "/home/linuxbrew/.linuxbrew/bin/gh"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_CLI_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.isfile", side_effect=lambda p: p == linuxbrew_path):
                with patch("core.gh_executable._verify_gh_executable", return_value=True):
                    # Act
                    result = _find_gh_executable()

                    # Assert
                    assert result == linuxbrew_path

    @patch("os.name", "nt")
    def test_find_gh_windows_program_files(self):
        """Test finding gh from Windows Program Files"""
        # Arrange
        windows_path = "C:\\Program Files\\GitHub CLI\\gh.exe"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_CLI_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.expandvars", side_effect=lambda x: x.replace("%PROGRAMFILES%", "C:\\Program Files")):
                with patch("os.path.isfile", side_effect=lambda p: p == windows_path):
                    with patch("core.gh_executable._verify_gh_executable", return_value=True):
                        # Act
                        result = _find_gh_executable()

                        # Assert
                        assert result == windows_path

    @patch("os.name", "nt")
    def test_find_gh_windows_program_files_x86(self):
        """Test finding gh from Windows Program Files (x86)"""
        # Arrange
        windows_path = "C:\\Program Files (x86)\\GitHub CLI\\gh.exe"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_CLI_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.expandvars", side_effect=lambda x: x.replace("%PROGRAMFILES(X86)%", "C:\\Program Files (x86)")):
                with patch("os.path.isfile", side_effect=lambda p: p == windows_path):
                    with patch("core.gh_executable._verify_gh_executable", return_value=True):
                        # Act
                        result = _find_gh_executable()

                        # Assert
                        assert result == windows_path

    @patch("os.name", "nt")
    def test_find_gh_windows_localappdata(self):
        """Test finding gh from Windows LOCALAPPDATA Programs"""
        # Arrange
        windows_path = "C:\\Users\\user\\AppData\\Local\\Programs\\GitHub CLI\\gh.exe"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_CLI_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.expandvars", side_effect=lambda x: x.replace("%LOCALAPPDATA%", "C:\\Users\\user\\AppData\\Local")):
                with patch("os.path.isfile", side_effect=lambda p: p == windows_path):
                    with patch("core.gh_executable._verify_gh_executable", return_value=True):
                        # Act
                        result = _find_gh_executable()

                        # Assert
                        assert result == windows_path

    @patch("os.name", "nt")
    def test_find_gh_windows_fallback_to_where(self):
        """Test finding gh falls back to 'where' command on Windows"""
        # Arrange
        where_path = "C:\\custom\\gh.exe"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_CLI_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.isfile", return_value=False):
                with patch("core.gh_executable._run_where_command", return_value=where_path):
                    # Act
                    result = _find_gh_executable()

                    # Assert
                    assert result == where_path

    def test_find_gh_not_found(self):
        """Test when gh cannot be found"""
        # Arrange
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_CLI_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.isfile", return_value=False):
                # Act
                result = _find_gh_executable()

                # Assert
                assert result is None


class TestGetGhExecutable:
    """Tests for get_gh_executable function"""

    def test_get_gh_executable_caching(self):
        """Test caching behavior of get_gh_executable"""
        # Arrange
        cached_path = "/cached/gh"

        with patch("core.gh_executable._cached_gh_path", cached_path):
            with patch("os.path.isfile", return_value=True):
                # Act
                result = get_gh_executable()

                # Assert
                assert result == cached_path

    def test_get_gh_executable_cache_invalidated(self):
        """Test cache is invalidated when file doesn't exist"""
        # Arrange
        cached_path = "/cached/gh"

        with patch("core.gh_executable._cached_gh_path", cached_path):
            with patch("os.path.isfile", return_value=False):
                with patch("core.gh_executable._find_gh_executable", return_value="/new/gh"):
                    # Act
                    result = get_gh_executable()

                    # Assert
                    assert result == "/new/gh"

    def test_get_gh_executable_no_cache(self):
        """Test get_gh_executable with no cache"""
        # Arrange
        with patch("core.gh_executable._cached_gh_path", None):
            with patch("core.gh_executable._find_gh_executable", return_value=None):
                # Act
                result = get_gh_executable()

                # Assert
                assert result is None


class TestInvalidateGhCache:
    """Tests for invalidate_gh_cache function"""

    def test_invalidate_gh_cache(self):
        """Test invalidate_gh_cache"""
        # Arrange
        with patch("core.gh_executable._cached_gh_path", "/some/path"):
            # Act
            invalidate_gh_cache()

            # Assert - cache should be cleared
            from core import gh_executable
            assert gh_executable._cached_gh_path is None


class TestRunGh:
    """Tests for run_gh function"""

    def test_run_gh_with_valid_gh(self):
        """Test run_gh when gh is available"""
        # Arrange
        args = ["--version"]
        cwd = None
        timeout = 5
        input_data = None

        # Mock subprocess.run to simulate gh execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "gh version 2.0.0"
        mock_result.stderr = ""

        with patch("core.gh_executable.get_gh_executable", return_value="/usr/bin/gh"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                # Act
                result = run_gh(args, cwd, timeout, input_data)

                # Assert
                assert result.returncode == 0
                mock_run.assert_called_once()

    def test_run_gh_with_input_data(self):
        """Test run_gh with input data"""
        # Arrange
        args = ["pr", "create"]
        input_data = "PR title\nBody"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "PR created"
        mock_result.stderr = ""

        with patch("core.gh_executable.get_gh_executable", return_value="/usr/bin/gh"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                # Act
                result = run_gh(args, input_data=input_data)

                # Assert
                assert result.returncode == 0
                # Verify input_data was passed
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["input"] == input_data

    def test_run_gh_with_cwd(self):
        """Test run_gh with custom working directory"""
        # Arrange
        args = ["pr", "list"]
        cwd = "/path/to/repo"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("core.gh_executable.get_gh_executable", return_value="/usr/bin/gh"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                # Act
                result = run_gh(args, cwd=cwd)

                # Assert
                assert result.returncode == 0
                # Verify cwd was passed
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["cwd"] == cwd

    def test_run_gh_with_custom_timeout(self):
        """Test run_gh with custom timeout"""
        # Arrange
        args = ["pr", "create"]
        custom_timeout = 120

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("core.gh_executable.get_gh_executable", return_value="/usr/bin/gh"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                # Act
                result = run_gh(args, timeout=custom_timeout)

                # Assert
                assert result.returncode == 0
                # Verify timeout was passed
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["timeout"] == custom_timeout

    def test_run_gh_without_gh(self):
        """Test run_gh when gh is not available"""
        # Arrange
        args = ["pr", "list"]
        with patch("core.gh_executable.get_gh_executable", return_value=None):
            # Act
            result = run_gh(args)

            # Assert
            assert result.returncode == -1
            assert "not found" in result.stderr
            assert "https://cli.github.com/" in result.stderr

    def test_run_gh_timeout(self):
        """Test run_gh handles timeout"""
        # Arrange
        args = ["pr", "create"]
        timeout = 60

        with patch("core.gh_executable.get_gh_executable", return_value="/usr/bin/gh"):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("gh", timeout)):
                # Act
                result = run_gh(args, timeout=timeout)

                # Assert
                assert result.returncode == -1
                assert "timed out" in result.stderr
                assert f"{timeout} seconds" in result.stderr

    def test_run_gh_file_not_found(self):
        """Test run_gh handles file not found"""
        # Arrange
        args = ["pr", "list"]
        gh_path = "/nonexistent/gh"

        with patch("core.gh_executable.get_gh_executable", return_value=gh_path):
            with patch("subprocess.run", side_effect=FileNotFoundError):
                # Act
                result = run_gh(args)

                # Assert
                assert result.returncode == -1
                assert "not found" in result.stderr
                assert "https://cli.github.com/" in result.stderr

    def test_run_gh_default_timeout(self):
        """Test run_gh uses default timeout"""
        # Arrange
        args = ["status"]

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("core.gh_executable.get_gh_executable", return_value="/usr/bin/gh"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                # Act
                result = run_gh(args)

                # Assert
                assert result.returncode == 0
                # Verify default timeout
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["timeout"] == 60

    def test_run_gh_encoding_errors(self):
        """Test run_gh handles encoding errors gracefully"""
        # Arrange
        args = ["pr", "list"]

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Success"
        mock_result.stderr = ""

        with patch("core.gh_executable.get_gh_executable", return_value="/usr/bin/gh"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                # Act
                result = run_gh(args)

                # Assert
                assert result.returncode == 0
                # Verify encoding parameters
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["encoding"] == "utf-8"
                assert call_kwargs["errors"] == "replace"
