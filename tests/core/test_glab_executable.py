"""Tests for glab_executable"""

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.glab_executable import (
    _find_glab_executable,
    _run_where_command,
    _verify_glab_executable,
    get_glab_executable,
    invalidate_glab_cache,
    run_glab,
)


class TestVerifyGlabExecutable:
    """Tests for _verify_glab_executable function"""

    def test_verify_glab_executable_valid(self):
        """Test verification with valid glab executable"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            # Act
            result = _verify_glab_executable("/usr/bin/glab")

            # Assert
            assert result is True

    def test_verify_glab_executable_invalid(self):
        """Test verification with invalid glab executable"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("subprocess.run", return_value=mock_result):
            # Act
            result = _verify_glab_executable("/usr/bin/glab")

            # Assert
            assert result is False

    def test_verify_glab_executable_timeout(self):
        """Test verification handles timeout"""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("glab", 5)):
            # Act
            result = _verify_glab_executable("/usr/bin/glab")

            # Assert
            assert result is False

    def test_verify_glab_executable_os_error(self):
        """Test verification handles OS error"""
        with patch("subprocess.run", side_effect=OSError("Command failed")):
            # Act
            result = _verify_glab_executable("/usr/bin/glab")

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
        mock_result.stdout = "C:\\Program Files\\glab\\bin\\glab.exe\nC:\\other\\glab.exe"

        with patch("subprocess.run", return_value=mock_result):
            with patch("os.path.isfile", return_value=True):
                with patch("core.glab_executable._verify_glab_executable", return_value=True):
                    # Act
                    result = _run_where_command()

                    # Assert
                    assert result == "C:\\Program Files\\glab\\bin\\glab.exe"

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
        mock_result.stdout = "C:\\Program Files\\glab\\glab.exe"

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
        mock_result.stdout = "C:\\Program Files\\glab\\glab.exe"

        with patch("subprocess.run", return_value=mock_result):
            with patch("os.path.isfile", return_value=True):
                with patch("core.glab_executable._verify_glab_executable", return_value=False):
                    # Act
                    result = _run_where_command()

                    # Assert
                    assert result is None


class TestFindGlabExecutable:
    """Tests for _find_glab_executable function"""

    def test_find_glab_from_env_var(self):
        """Test finding glab from GITLAB_CLI_PATH environment variable"""
        # Arrange
        env_path = "/custom/path/to/glab"

        with patch.dict(os.environ, {"GITLAB_CLI_PATH": env_path}):
            with patch("os.path.isfile", return_value=True):
                with patch("core.glab_executable._verify_glab_executable", return_value=True):
                    # Act
                    result = _find_glab_executable()

                    # Assert
                    assert result == env_path

    def test_find_glab_from_env_var_not_file(self):
        """Test GITLAB_CLI_PATH when path is not a file"""
        # Arrange
        env_path = "/custom/path/to/glab"

        with patch.dict(os.environ, {"GITLAB_CLI_PATH": env_path}):
            with patch("os.path.isfile", return_value=False):
                with patch("shutil.which", return_value=None):
                    # Act
                    result = _find_glab_executable()

                    # Assert
                    assert result is None

    def test_find_glab_from_env_var_invalid(self):
        """Test GITLAB_CLI_PATH when executable is invalid"""
        # Arrange
        env_path = "/custom/path/to/glab"

        with patch.dict(os.environ, {"GITLAB_CLI_PATH": env_path}):
            with patch("os.path.isfile", return_value=True):
                with patch("core.glab_executable._verify_glab_executable", return_value=False):
                    with patch("shutil.which", return_value=None):
                        # Act
                        result = _find_glab_executable()

                        # Assert
                        assert result is None

    def test_find_glab_from_path(self):
        """Test finding glab from PATH via shutil.which"""
        # Arrange
        path_result = "/usr/bin/glab"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITLAB_CLI_PATH", None)

        with patch("shutil.which", return_value=path_result):
            with patch("core.glab_executable._verify_glab_executable", return_value=True):
                # Act
                result = _find_glab_executable()

                # Assert
                assert result == path_result

    def test_find_glab_from_path_invalid(self):
        """Test shutil.which returns invalid executable"""
        # Arrange
        path_result = "/usr/bin/glab"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITLAB_CLI_PATH", None)

        with patch("shutil.which", return_value=path_result):
            with patch("core.glab_executable._verify_glab_executable", return_value=False):
                # Act
                result = _find_glab_executable()

                # Assert
                assert result is None

    @patch("os.name", "posix")
    def test_find_glab_homebrew_apple_silicon(self):
        """Test finding glab from Homebrew on Apple Silicon"""
        # Arrange
        homebrew_path = "/opt/homebrew/bin/glab"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITLAB_CLI_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.isfile", side_effect=lambda p: p == homebrew_path):
                with patch("core.glab_executable._verify_glab_executable", return_value=True):
                    # Act
                    result = _find_glab_executable()

                    # Assert
                    assert result == homebrew_path

    @patch("os.name", "posix")
    def test_find_glab_homebrew_intel(self):
        """Test finding glab from Homebrew on Intel Mac"""
        # Arrange
        homebrew_path = "/usr/local/bin/glab"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITLAB_CLI_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.isfile", side_effect=lambda p: p == homebrew_path):
                with patch("core.glab_executable._verify_glab_executable", return_value=True):
                    # Act
                    result = _find_glab_executable()

                    # Assert
                    assert result == homebrew_path

    @patch("os.name", "posix")
    def test_find_glab_linuxbrew(self):
        """Test finding glab from Linuxbrew"""
        # Arrange
        linuxbrew_path = "/home/linuxbrew/.linuxbrew/bin/glab"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITLAB_CLI_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.isfile", side_effect=lambda p: p == linuxbrew_path):
                with patch("core.glab_executable._verify_glab_executable", return_value=True):
                    # Act
                    result = _find_glab_executable()

                    # Assert
                    assert result == linuxbrew_path

    @patch("os.name", "nt")
    def test_find_glab_windows_program_files(self):
        """Test finding glab from Windows Program Files"""
        # Arrange
        windows_path = "C:\\Program Files\\glab\\glab.exe"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITLAB_CLI_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.expandvars", side_effect=lambda x: x.replace("%PROGRAMFILES%", "C:\\Program Files")):
                with patch("os.path.isfile", side_effect=lambda p: p == windows_path):
                    with patch("core.glab_executable._verify_glab_executable", return_value=True):
                        # Act
                        result = _find_glab_executable()

                        # Assert
                        assert result == windows_path

    @patch("os.name", "nt")
    def test_find_glab_windows_program_files_x86(self):
        """Test finding glab from Windows Program Files (x86)"""
        # Arrange
        windows_path = "C:\\Program Files (x86)\\glab\\glab.exe"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITLAB_CLI_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.expandvars", side_effect=lambda x: x.replace("%PROGRAMFILES(X86)%", "C:\\Program Files (x86)")):
                with patch("os.path.isfile", side_effect=lambda p: p == windows_path):
                    with patch("core.glab_executable._verify_glab_executable", return_value=True):
                        # Act
                        result = _find_glab_executable()

                        # Assert
                        assert result == windows_path

    @patch("os.name", "nt")
    def test_find_glab_windows_localappdata(self):
        """Test finding glab from Windows LOCALAPPDATA Programs"""
        # Arrange
        windows_path = "C:\\Users\\user\\AppData\\Local\\Programs\\glab\\glab.exe"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITLAB_CLI_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.expandvars", side_effect=lambda x: x.replace("%LOCALAPPDATA%", "C:\\Users\\user\\AppData\\Local")):
                with patch("os.path.isfile", side_effect=lambda p: p == windows_path):
                    with patch("core.glab_executable._verify_glab_executable", return_value=True):
                        # Act
                        result = _find_glab_executable()

                        # Assert
                        assert result == windows_path

    @patch("os.name", "nt")
    def test_find_glab_windows_fallback_to_where(self):
        """Test finding glab falls back to 'where' command on Windows"""
        # Arrange
        where_path = "C:\\custom\\glab.exe"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITLAB_CLI_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.isfile", return_value=False):
                with patch("core.glab_executable._run_where_command", return_value=where_path):
                    # Act
                    result = _find_glab_executable()

                    # Assert
                    assert result == where_path

    def test_find_glab_not_found(self):
        """Test when glab cannot be found"""
        # Arrange
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITLAB_CLI_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.isfile", return_value=False):
                # Act
                result = _find_glab_executable()

                # Assert
                assert result is None


class TestGetGlabExecutable:
    """Tests for get_glab_executable function"""

    def test_get_glab_executable_caching(self):
        """Test caching behavior of get_glab_executable"""
        # Arrange
        cached_path = "/cached/glab"

        with patch("core.glab_executable._cached_glab_path", cached_path):
            with patch("os.path.isfile", return_value=True):
                # Act
                result = get_glab_executable()

                # Assert
                assert result == cached_path

    def test_get_glab_executable_cache_invalidated(self):
        """Test cache is invalidated when file doesn't exist"""
        # Arrange
        cached_path = "/cached/glab"

        with patch("core.glab_executable._cached_glab_path", cached_path):
            with patch("os.path.isfile", return_value=False):
                with patch("core.glab_executable._find_glab_executable", return_value="/new/glab"):
                    # Act
                    result = get_glab_executable()

                    # Assert
                    assert result == "/new/glab"

    def test_get_glab_executable_no_cache(self):
        """Test get_glab_executable with no cache"""
        # Arrange
        with patch("core.glab_executable._cached_glab_path", None):
            with patch("core.glab_executable._find_glab_executable", return_value=None):
                # Act
                result = get_glab_executable()

                # Assert
                assert result is None


class TestInvalidateGlabCache:
    """Tests for invalidate_glab_cache function"""

    def test_invalidate_glab_cache(self):
        """Test invalidate_glab_cache"""
        # Arrange
        with patch("core.glab_executable._cached_glab_path", "/some/path"):
            # Act
            invalidate_glab_cache()

            # Assert - cache should be cleared
            from core import glab_executable
            assert glab_executable._cached_glab_path is None


class TestRunGlab:
    """Tests for run_glab function"""

    def test_run_glab_with_valid_glab(self):
        """Test run_glab when glab is available"""
        # Arrange
        args = ["--version"]
        cwd = None
        timeout = 5
        input_data = None

        # Mock subprocess.run to simulate glab execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "glab version 1.0.0"
        mock_result.stderr = ""

        with patch("core.glab_executable.get_glab_executable", return_value="/usr/bin/glab"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                # Act
                result = run_glab(args, cwd, timeout, input_data)

                # Assert
                assert result.returncode == 0
                mock_run.assert_called_once()

    def test_run_glab_with_input_data(self):
        """Test run_glab with input data"""
        # Arrange
        args = ["mr", "create"]
        input_data = "MR title\nBody"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "MR created"
        mock_result.stderr = ""

        with patch("core.glab_executable.get_glab_executable", return_value="/usr/bin/glab"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                # Act
                result = run_glab(args, input_data=input_data)

                # Assert
                assert result.returncode == 0
                # Verify input_data was passed
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["input"] == input_data

    def test_run_glab_with_cwd(self):
        """Test run_glab with custom working directory"""
        # Arrange
        args = ["mr", "list"]
        cwd = "/path/to/repo"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("core.glab_executable.get_glab_executable", return_value="/usr/bin/glab"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                # Act
                result = run_glab(args, cwd=cwd)

                # Assert
                assert result.returncode == 0
                # Verify cwd was passed
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["cwd"] == cwd

    def test_run_glab_with_custom_timeout(self):
        """Test run_glab with custom timeout"""
        # Arrange
        args = ["mr", "create"]
        custom_timeout = 120

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("core.glab_executable.get_glab_executable", return_value="/usr/bin/glab"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                # Act
                result = run_glab(args, timeout=custom_timeout)

                # Assert
                assert result.returncode == 0
                # Verify timeout was passed
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["timeout"] == custom_timeout

    def test_run_glab_without_glab(self):
        """Test run_glab when glab is not available"""
        # Arrange
        args = ["mr", "list"]
        with patch("core.glab_executable.get_glab_executable", return_value=None):
            # Act
            result = run_glab(args)

            # Assert
            assert result.returncode == -1
            assert "not found" in result.stderr
            assert "https://gitlab.com/gitlab-org/cli" in result.stderr

    def test_run_glab_timeout(self):
        """Test run_glab handles timeout"""
        # Arrange
        args = ["mr", "create"]
        timeout = 60

        with patch("core.glab_executable.get_glab_executable", return_value="/usr/bin/glab"):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("glab", timeout)):
                # Act
                result = run_glab(args, timeout=timeout)

                # Assert
                assert result.returncode == -1
                assert "timed out" in result.stderr
                assert f"{timeout} seconds" in result.stderr

    def test_run_glab_file_not_found(self):
        """Test run_glab handles file not found"""
        # Arrange
        args = ["mr", "list"]
        glab_path = "/nonexistent/glab"

        with patch("core.glab_executable.get_glab_executable", return_value=glab_path):
            with patch("subprocess.run", side_effect=FileNotFoundError):
                # Act
                result = run_glab(args)

                # Assert
                assert result.returncode == -1
                assert "not found" in result.stderr
                assert "https://gitlab.com/gitlab-org/cli" in result.stderr

    def test_run_glab_default_timeout(self):
        """Test run_glab uses default timeout"""
        # Arrange
        args = ["status"]

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("core.glab_executable.get_glab_executable", return_value="/usr/bin/glab"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                # Act
                result = run_glab(args)

                # Assert
                assert result.returncode == 0
                # Verify default timeout
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["timeout"] == 60

    def test_run_glab_encoding_errors(self):
        """Test run_glab handles encoding errors gracefully"""
        # Arrange
        args = ["mr", "list"]

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Success"
        mock_result.stderr = ""

        with patch("core.glab_executable.get_glab_executable", return_value="/usr/bin/glab"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                # Act
                result = run_glab(args)

                # Assert
                assert result.returncode == 0
                # Verify encoding parameters
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["encoding"] == "utf-8"
                assert call_kwargs["errors"] == "replace"
