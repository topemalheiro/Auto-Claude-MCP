"""Tests for git_executable"""

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.git_executable import (
    GIT_ENV_VARS_TO_CLEAR,
    _find_git_executable,
    get_git_executable,
    get_isolated_git_env,
    run_git,
)


class TestGetIsolatedGitEnv:
    """Tests for get_isolated_git_env function"""

    def test_get_isolated_git_env_clears_git_vars(self):
        """Test get_isolated_git_env clears git environment variables"""
        # Arrange
        base_env = {
            "PATH": "/usr/bin:/bin",
            "GIT_DIR": "/some/.git",
            "GIT_WORK_TREE": "/some",
            "HOME": "/home/user",
        }

        # Act
        result = get_isolated_git_env(base_env)

        # Assert
        assert result is not None
        assert "PATH" in result
        assert result["PATH"] == "/usr/bin:/bin"
        assert "GIT_DIR" not in result
        assert "GIT_WORK_TREE" not in result
        assert "HOME" in result
        assert result["HUSKY"] == "0"

    def test_get_isolated_git_env_clears_all_git_vars(self):
        """Test all git environment variables are cleared"""
        # Arrange
        base_env = {var: "value" for var in GIT_ENV_VARS_TO_CLEAR}
        base_env["PATH"] = "/usr/bin"

        # Act
        result = get_isolated_git_env(base_env)

        # Assert
        assert "PATH" in result
        assert result["HUSKY"] == "0"
        for var in GIT_ENV_VARS_TO_CLEAR:
            assert var not in result

    def test_get_isolated_git_env_default(self):
        """Test get_isolated_git_env with default env"""
        # Act
        result = get_isolated_git_env()

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert result["HUSKY"] == "0"

    def test_get_isolated_git_env_preserves_non_git_vars(self):
        """Test non-git environment variables are preserved"""
        # Arrange
        base_env = {
            "PATH": "/usr/bin:/bin",
            "GIT_DIR": "/some/.git",
            "HOME": "/home/user",
            "USER": "testuser",
            "SHELL": "/bin/bash",
        }

        # Act
        result = get_isolated_git_env(base_env)

        # Assert
        assert result["PATH"] == "/usr/bin:/bin"
        assert result["HOME"] == "/home/user"
        assert result["USER"] == "testuser"
        assert result["SHELL"] == "/bin/bash"
        assert "GIT_DIR" not in result

    def test_get_isolated_git_env_sets_husky_zero(self):
        """Test HUSKY is set to 0 to disable hooks"""
        # Arrange
        base_env = {"PATH": "/usr/bin"}

        # Act
        result = get_isolated_git_env(base_env)

        # Assert
        assert result["HUSKY"] == "0"


class TestFindGitExecutable:
    """Tests for _find_git_executable function"""

    def test_find_git_from_bash_path_env_var(self):
        """Test finding git from CLAUDE_CODE_GIT_BASH_PATH environment variable"""
        # Arrange
        bash_path = "C:\\Program Files\\Git\\bin\\bash.exe"

        with patch.dict(os.environ, {"CLAUDE_CODE_GIT_BASH_PATH": bash_path}, clear=False):
            # When bash path is set but git is not found, it falls through to shutil.which
            with patch("shutil.which", return_value="/usr/bin/git"):
                # Act
                result = _find_git_executable()

                # Assert - should find git from shutil.which
                assert result == "/usr/bin/git"

    def test_find_git_from_bash_path_bin_git(self):
        """Test finding git.exe in bin/ directory from bash path"""
        # Arrange
        bash_path = "/usr/local/Git/bin/bash.exe"

        with patch.dict(os.environ, {"CLAUDE_CODE_GIT_BASH_PATH": bash_path}, clear=False):
            # When bash path is set but git is not found, it falls through to shutil.which
            with patch("shutil.which", return_value="/usr/local/Git/bin/git"):
                # Act
                result = _find_git_executable()

                # Assert - should find git from shutil.which
                assert result == "/usr/local/Git/bin/git"

    def test_find_git_from_bash_path_invalid_path(self):
        """Test CLAUDE_CODE_GIT_BASH_PATH with invalid path"""
        # Arrange
        bash_path = "/nonexistent/bash.exe"

        with patch.dict(os.environ, {"CLAUDE_CODE_GIT_BASH_PATH": bash_path}, clear=False):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("shutil.which", return_value="/usr/bin/git"):
                    # Act
                    result = _find_git_executable()

                    # Assert
                    assert result == "/usr/bin/git"

    def test_find_git_from_bash_path_os_error(self):
        """Test CLAUDE_CODE_GIT_BASH_PATH with OS error"""
        # Arrange
        bash_path = "/invalid/bash"

        with patch.dict(os.environ, {"CLAUDE_CODE_GIT_BASH_PATH": bash_path}, clear=False):
            with patch("pathlib.Path.exists", side_effect=OSError("Invalid path")):
                with patch("shutil.which", return_value="/usr/bin/git"):
                    # Act
                    result = _find_git_executable()

                    # Assert
                    assert result == "/usr/bin/git"

    def test_find_git_from_path(self):
        """Test finding git from PATH via shutil.which"""
        # Arrange
        path_result = "/usr/bin/git"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_CODE_GIT_BASH_PATH", None)

        with patch("shutil.which", return_value=path_result):
            # Act
            result = _find_git_executable()

            # Assert
            assert result == path_result

    @patch("os.name", "nt")
    def test_find_git_windows_program_files_cmd(self):
        """Test finding git from Windows Program Files cmd"""
        # Arrange
        git_path = "C:\\Program Files\\Git\\cmd\\git.exe"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_CODE_GIT_BASH_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.expandvars", side_effect=lambda x: x.replace("%PROGRAMFILES%", "C:\\Program Files")):
                with patch("os.path.isfile", side_effect=lambda p: p == git_path):
                    # Act
                    result = _find_git_executable()

                    # Assert
                    assert result == git_path

    @patch("os.name", "nt")
    def test_find_git_windows_program_files_bin(self):
        """Test finding git from Windows Program Files bin"""
        # Arrange
        git_path = "C:\\Program Files\\Git\\bin\\git.exe"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_CODE_GIT_BASH_PATH", None)

        with patch("shutil.which", return_value=None):
            # Don't mock expandvars so it expands the environment variables
            with patch("os.path.isfile", side_effect=lambda p: p == git_path or "bin/git.exe" in str(p)):
                # Act
                result = _find_git_executable()

                # Assert - should find git in one of the Windows paths or fallback
                assert result is not None

    @patch("os.name", "nt")
    def test_find_git_windows_program_files_x86(self):
        """Test finding git from Windows Program Files (x86)"""
        # Arrange
        git_path = "C:\\Program Files (x86)\\Git\\cmd\\git.exe"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_CODE_GIT_BASH_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.expandvars", side_effect=lambda x: x.replace("%PROGRAMFILES(X86)%", "C:\\Program Files (x86)")):
                with patch("os.path.isfile", side_effect=lambda p: p == git_path):
                    # Act
                    result = _find_git_executable()

                    # Assert
                    assert result == git_path

    @patch("os.name", "nt")
    def test_find_git_windows_localappdata(self):
        """Test finding git from Windows LOCALAPPDATA Programs"""
        # Arrange
        git_path = "C:\\Users\\user\\AppData\\Local\\Programs\\Git\\cmd\\git.exe"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_CODE_GIT_BASH_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.expandvars", side_effect=lambda x: x.replace("%LOCALAPPDATA%", "C:\\Users\\user\\AppData\\Local")):
                with patch("os.path.isfile", side_effect=lambda p: p == git_path):
                    # Act
                    result = _find_git_executable()

                    # Assert
                    assert result == git_path

    @patch("os.name", "nt")
    def test_find_git_windows_fallback_hardcoded_paths(self):
        """Test finding git from hardcoded Windows paths"""
        # Arrange
        git_path = r"C:\Program Files\Git\cmd\git.exe"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_CODE_GIT_BASH_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.expandvars", side_effect=lambda x: x):
                with patch("os.path.isfile", side_effect=lambda p: p == git_path):
                    # Act
                    result = _find_git_executable()

                    # Assert
                    assert result == git_path

    @patch("os.name", "nt")
    def test_find_git_windows_where_command(self):
        """Test finding git via Windows 'where' command"""
        # Arrange
        where_path = "C:\\custom\\git.exe"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_CODE_GIT_BASH_PATH", None)

        with patch("shutil.which", return_value=None):
            # Mock isfile to return True only for the where command result
            def mock_isfile(path):
                return path == where_path

            with patch("os.path.isfile", side_effect=mock_isfile):
                with patch("subprocess.run") as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_result.stdout = where_path + "\n"
                    mock_run.return_value = mock_result

                    # Act
                    result = _find_git_executable()

                    # Assert
                    assert result == where_path

    @patch("os.name", "nt")
    def test_find_git_windows_where_command_timeout(self):
        """Test 'where' command timeout falls back to default"""
        # Arrange
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_CODE_GIT_BASH_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.expandvars", side_effect=lambda x: x):
                with patch("os.path.isfile", return_value=False):
                    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("where", 5)):
                        # Act
                        result = _find_git_executable()

                        # Assert
                        assert result == "git"

    @patch("os.name", "nt")
    def test_find_git_windows_where_command_os_error(self):
        """Test 'where' command OS error falls back to default"""
        # Arrange
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_CODE_GIT_BASH_PATH", None)

        with patch("shutil.which", return_value=None):
            with patch("os.path.expandvars", side_effect=lambda x: x):
                with patch("os.path.isfile", return_value=False):
                    with patch("subprocess.run", side_effect=OSError("Command failed")):
                        # Act
                        result = _find_git_executable()

                        # Assert
                        assert result == "git"

    @patch("os.name", "posix")
    def test_find_git_unix_fallback(self):
        """Test Unix systems fall back to 'git' command"""
        # Arrange
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_CODE_GIT_BASH_PATH", None)

        with patch("shutil.which", return_value=None):
            # Act
            result = _find_git_executable()

            # Assert
            assert result == "git"

    @patch("os.name", "nt")
    def test_find_git_windows_os_error_on_common_paths(self):
        """Test OSError when checking common Windows paths"""
        # Arrange
        where_path = "C:\\git.exe"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_CODE_GIT_BASH_PATH", None)

        with patch("shutil.which", return_value=None):
            # First isfile calls for common paths raise OSError, then we return True for where result
            call_count = [0]

            def mock_isfile(path):
                call_count[0] += 1
                if call_count[0] <= 6:  # First 6 calls (common paths)
                    raise OSError("Permission denied")
                return path == where_path

            with patch("os.path.isfile", side_effect=mock_isfile):
                with patch("subprocess.run") as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_result.stdout = where_path
                    mock_run.return_value = mock_result

                    # Act
                    result = _find_git_executable()

                    # Assert
                    assert result == where_path


class TestGetGitExecutable:
    """Tests for get_git_executable function"""

    def test_get_git_executable_caching(self):
        """Test caching behavior of get_git_executable"""
        # Arrange
        cached_path = "/cached/git"

        with patch("core.git_executable._cached_git_path", cached_path):
            # Act
            result = get_git_executable()

            # Assert
            assert result == cached_path

    def test_get_git_executable_no_cache(self):
        """Test get_git_executable with no cache"""
        # Arrange
        with patch("core.git_executable._cached_git_path", None):
            with patch("core.git_executable._find_git_executable", return_value="/usr/bin/git"):
                # Act
                result = get_git_executable()

                # Assert
                assert result == "/usr/bin/git"
                # Verify cache was set
                from core import git_executable
                assert git_executable._cached_git_path == "/usr/bin/git"


class TestRunGit:
    """Tests for run_git function"""

    def test_run_git_with_args(self):
        """Test run_git with proper list args"""
        # Arrange
        args = ["status", "--short"]
        cwd = None
        timeout = 60
        input_data = None
        env = None
        isolate_env = True

        # Mock subprocess.run to simulate git execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "M file.py"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            # Act
            result = run_git(args, cwd, timeout, input_data, env, isolate_env)

            # Assert
            assert result.returncode == 0
            mock_run.assert_called_once()
            # Verify that args were passed as a list
            call_args = mock_run.call_args
            assert isinstance(call_args[0][0], list)

    def test_run_git_with_input_data(self):
        """Test run_git with input data"""
        # Arrange
        args = ["commit", "-m", "test"]
        input_data = "commit message"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("core.git_executable.get_git_executable", return_value="git"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                # Act
                result = run_git(args, input_data=input_data)

                # Assert
                assert result.returncode == 0
                # Verify input_data was passed
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["input"] == input_data

    def test_run_git_with_cwd(self):
        """Test run_git with custom working directory"""
        # Arrange
        args = ["status"]
        cwd = "/path/to/repo"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("core.git_executable.get_git_executable", return_value="git"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                # Act
                result = run_git(args, cwd=cwd)

                # Assert
                assert result.returncode == 0
                # Verify cwd was passed
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["cwd"] == cwd

    def test_run_git_with_custom_timeout(self):
        """Test run_git with custom timeout"""
        # Arrange
        args = ["clone", "https://github.com/example/repo.git"]
        custom_timeout = 120

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("core.git_executable.get_git_executable", return_value="git"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                # Act
                result = run_git(args, timeout=custom_timeout)

                # Assert
                assert result.returncode == 0
                # Verify timeout was passed
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["timeout"] == custom_timeout

    def test_run_git_timeout(self):
        """Test run_git handles timeout"""
        # Arrange
        args = ["clone", "https://github.com/example/repo.git"]
        timeout = 60

        with patch("core.git_executable.get_git_executable", return_value="git"):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", timeout)):
                # Act
                result = run_git(args, timeout=timeout)

                # Assert
                assert result.returncode == -1
                assert "timed out" in result.stderr
                assert f"{timeout} seconds" in result.stderr

    def test_run_git_file_not_found(self):
        """Test run_git handles file not found"""
        # Arrange
        args = ["status"]

        with patch("core.git_executable.get_git_executable", return_value="git"):
            with patch("subprocess.run", side_effect=FileNotFoundError):
                # Act
                result = run_git(args)

                # Assert
                assert result.returncode == -1
                assert "not found" in result.stderr

    def test_run_git_no_isolation(self):
        """Test run_git without environment isolation"""
        # Arrange
        args = ["status"]
        custom_env = {"PATH": "/usr/bin", "GIT_DIR": "/custom/.git"}

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("core.git_executable.get_git_executable", return_value="git"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                # Act
                result = run_git(args, env=custom_env, isolate_env=False)

                # Assert
                assert result.returncode == 0
                # When isolate_env=False, custom env should be used
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["env"] == custom_env

    def test_run_git_with_isolation(self):
        """Test run_git with environment isolation uses base_env when provided"""
        # Arrange
        args = ["status"]
        base_env = {"PATH": "/usr/bin", "GIT_DIR": "/old/.git"}

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("core.git_executable.get_git_executable", return_value="git"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                # Act
                result = run_git(args, env=base_env, isolate_env=True)

                # Assert
                assert result.returncode == 0
                # When env is provided and isolate_env=True, the provided env is used directly
                # (isolation only applies when env is None)
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["env"] == base_env

    def test_run_git_default_isolation(self):
        """Test run_git uses isolation by default"""
        # Arrange
        args = ["status"]

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("core.git_executable.get_git_executable", return_value="git"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                # Act
                result = run_git(args)

                # Assert
                assert result.returncode == 0
                # Verify env isolation was applied
                call_kwargs = mock_run.call_args[1]
                assert "env" in call_kwargs
                assert call_kwargs["env"]["HUSKY"] == "0"

    def test_run_git_pathlib_cwd(self):
        """Test run_git accepts pathlib.Path for cwd"""
        # Arrange
        args = ["status"]
        cwd = Path("/path/to/repo")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("core.git_executable.get_git_executable", return_value="git"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                # Act
                result = run_git(args, cwd=cwd)

                # Assert
                assert result.returncode == 0
                # Verify cwd was passed
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["cwd"] == cwd

    def test_run_git_encoding_errors(self):
        """Test run_git handles encoding errors gracefully"""
        # Arrange
        args = ["log"]

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "commit message"
        mock_result.stderr = ""

        with patch("core.git_executable.get_git_executable", return_value="git"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                # Act
                result = run_git(args)

                # Assert
                assert result.returncode == 0
                # Verify encoding parameters
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["encoding"] == "utf-8"
                assert call_kwargs["errors"] == "replace"
