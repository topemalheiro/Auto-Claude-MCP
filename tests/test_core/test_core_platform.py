"""
Tests for core.platform module
===============================

Comprehensive tests for platform abstraction utilities including:
- Platform detection (OS type, Windows/macOS/Linux)
- Path configuration (delimiters, extensions)
- Binary directories and tool detection
- Shell execution and command building
- Environment variable handling
- Platform validation and security
"""

import os
import platform
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.platform import (
    # Enums
    OS,
    ShellType,
    # Platform detection
    get_current_os,
    is_windows,
    is_macos,
    is_linux,
    is_unix,
    # Path configuration
    get_path_delimiter,
    get_executable_extension,
    with_executable_extension,
    # Binary directories
    get_binary_directories,
    get_homebrew_path,
    # Tool detection
    find_executable,
    get_claude_detection_paths,
    get_claude_detection_paths_structured,
    get_python_commands,
    validate_cli_path,
    # Shell execution
    requires_shell,
    get_comspec_path,
    build_windows_command,
    # Environment variables
    get_env_var,
    # Platform description
    get_platform_description,
)


# ============================================================================
# Platform Detection Tests
# ============================================================================


class TestPlatformDetection:
    """Tests for platform detection functions."""

    def test_get_current_os_windows(self):
        """Test get_current_os returns WINDOWS on Windows."""
        with patch("platform.system", return_value="Windows"):
            result = get_current_os()
            assert result == OS.WINDOWS

    def test_get_current_os_macos(self):
        """Test get_current_os returns MACOS on macOS."""
        with patch("platform.system", return_value="Darwin"):
            result = get_current_os()
            assert result == OS.MACOS

    def test_get_current_os_linux(self):
        """Test get_current_os returns LINUX on Linux."""
        with patch("platform.system", return_value="Linux"):
            result = get_current_os()
            assert result == OS.LINUX

    def test_get_current_os_freebsd_defaults_to_linux(self):
        """Test get_current_os defaults to Linux for other Unix systems."""
        with patch("platform.system", return_value="FreeBSD"):
            result = get_current_os()
            assert result == OS.LINUX

    def test_get_current_os_sunos_defaults_to_linux(self):
        """Test get_current_os defaults to Linux for SunOS."""
        with patch("platform.system", return_value="SunOS"):
            result = get_current_os()
            assert result == OS.LINUX

    def test_is_windows_true(self):
        """Test is_windows returns True on Windows."""
        with patch("platform.system", return_value="Windows"):
            assert is_windows() is True

    def test_is_windows_false(self):
        """Test is_windows returns False on non-Windows."""
        with patch("platform.system", return_value="Linux"):
            assert is_windows() is False

    def test_is_macos_true(self):
        """Test is_macos returns True on macOS."""
        with patch("platform.system", return_value="Darwin"):
            assert is_macos() is True

    def test_is_macos_false(self):
        """Test is_macos returns False on non-macOS."""
        with patch("platform.system", return_value="Linux"):
            assert is_macos() is False

    def test_is_linux_true(self):
        """Test is_linux returns True on Linux."""
        with patch("platform.system", return_value="Linux"):
            assert is_linux() is True

    def test_is_linux_false_on_windows(self):
        """Test is_linux returns False on Windows."""
        with patch("platform.system", return_value="Windows"):
            assert is_linux() is False

    def test_is_linux_false_on_macos(self):
        """Test is_linux returns False on macOS."""
        with patch("platform.system", return_value="Darwin"):
            assert is_linux() is False

    def test_is_unix_on_linux(self):
        """Test is_unix returns True on Linux."""
        with patch("platform.system", return_value="Linux"):
            assert is_unix() is True

    def test_is_unix_on_macos(self):
        """Test is_unix returns True on macOS."""
        with patch("platform.system", return_value="Darwin"):
            assert is_unix() is True

    def test_is_unix_false_on_windows(self):
        """Test is_unix returns False on Windows."""
        with patch("platform.system", return_value="Windows"):
            assert is_unix() is False


# ============================================================================
# Path Configuration Tests
# ============================================================================


class TestPathConfiguration:
    """Tests for path configuration functions."""

    def test_get_path_delimiter_windows(self):
        """Test get_path_delimiter returns semicolon on Windows."""
        with patch("core.platform.is_windows", return_value=True):
            assert get_path_delimiter() == ";"

    def test_get_path_delimiter_unix(self):
        """Test get_path_delimiter returns colon on Unix."""
        with patch("core.platform.is_windows", return_value=False):
            assert get_path_delimiter() == ":"

    def test_get_executable_extension_windows(self):
        """Test get_executable_extension returns .exe on Windows."""
        with patch("core.platform.is_windows", return_value=True):
            assert get_executable_extension() == ".exe"

    def test_get_executable_extension_unix(self):
        """Test get_executable_extension returns empty string on Unix."""
        with patch("core.platform.is_windows", return_value=False):
            assert get_executable_extension() == ""

    def test_with_executable_extension_windows(self):
        """Test with_executable_extension adds .exe on Windows."""
        with patch("core.platform.get_executable_extension", return_value=".exe"):
            result = with_executable_extension("program")
            assert result == "program.exe"

    def test_with_executable_extension_unix(self):
        """Test with_executable_extension does not add extension on Unix."""
        with patch("core.platform.get_executable_extension", return_value=""):
            result = with_executable_extension("program")
            assert result == "program"

    def test_with_executable_extension_already_has_extension(self):
        """Test with_executable_extension preserves existing extension."""
        with patch("core.platform.get_executable_extension", return_value=".exe"):
            result = with_executable_extension("program.exe")
            assert result == "program.exe"

    def test_with_executable_extension_empty_string(self):
        """Test with_executable_extension handles empty string."""
        with patch("core.platform.get_executable_extension", return_value=".exe"):
            result = with_executable_extension("")
            assert result == ""

    def test_with_executable_extension_none_extension_unix(self):
        """Test with_executable_extension when extension is None."""
        with patch("core.platform.get_executable_extension", return_value=""):
            result = with_executable_extension("program")
            assert result == "program"


# ============================================================================
# Binary Directories Tests
# ============================================================================


class TestBinaryDirectories:
    """Tests for binary directory functions."""

    @patch("core.platform.is_windows", return_value=True)
    @patch("pathlib.Path.home", return_value=Path("/home/user"))
    @patch.dict(os.environ, {"ProgramFiles": "C:\\Program Files", "ProgramFiles(x86)": "C:\\Program Files (x86)", "SystemRoot": "C:\\Windows"})
    def test_get_binary_directories_windows(self, mock_home, mock_is_windows):
        """Test get_binary_directories on Windows."""
        result = get_binary_directories()
        assert "user" in result
        assert "system" in result
        assert any("AppData" in p for p in result["user"])
        assert any("Program Files" in p for p in result["system"])

    @patch("core.platform.is_macos", return_value=True)
    @patch("core.platform.is_windows", return_value=False)
    @patch("pathlib.Path.home", return_value=Path("/home/user"))
    def test_get_binary_directories_macos(self, mock_is_windows, mock_is_macos, mock_home):
        """Test get_binary_directories on macOS."""
        result = get_binary_directories()
        assert "user" in result
        assert "system" in result
        assert "/opt/homebrew/bin" in result["system"]
        assert "/usr/local/bin" in result["system"]

    @patch("core.platform.is_linux", return_value=True)
    @patch("core.platform.is_windows", return_value=False)
    @patch("core.platform.is_macos", return_value=False)
    @patch("pathlib.Path.home", return_value=Path("/home/user"))
    def test_get_binary_directories_linux(self, mock_is_macos, mock_is_windows, mock_is_linux, mock_home):
        """Test get_binary_directories on Linux."""
        result = get_binary_directories()
        assert "user" in result
        assert "system" in result
        assert "/usr/bin" in result["system"]
        assert "/snap/bin" in result["system"]

    @patch("core.platform.is_macos", return_value=False)
    def test_get_homebrew_path_on_linux(self, mock_is_macos):
        """Test get_homebrew_path returns None on Linux."""
        result = get_homebrew_path()
        assert result is None

    @patch("core.platform.is_macos", return_value=True)
    @patch("os.path.exists")
    def test_get_homebrew_path_apple_silicon_exists(self, mock_exists, mock_is_macos):
        """Test get_homebrew_path returns Apple Silicon path when it exists."""
        mock_exists.side_effect = lambda p: p == "/opt/homebrew/bin"
        result = get_homebrew_path()
        assert result == "/opt/homebrew/bin"

    @patch("core.platform.is_macos", return_value=True)
    @patch("os.path.exists", return_value=False)
    def test_get_homebrew_path_defaults_to_apple_silicon(self, mock_exists, mock_is_macos):
        """Test get_homebrew_path defaults to Apple Silicon path."""
        result = get_homebrew_path()
        assert result == "/opt/homebrew/bin"


# ============================================================================
# Tool Detection Tests
# ============================================================================


class TestToolDetection:
    """Tests for tool detection functions."""

    @patch("shutil.which", return_value="/usr/bin/git")
    def test_find_executable_in_path(self, mock_which):
        """Test find_executable finds executable in system PATH."""
        result = find_executable("git")
        assert result == "/usr/bin/git"

    @pytest.mark.skipif(sys.platform == "win32", reason="Test uses Unix-specific paths and expects is_windows=False")
    @patch("shutil.which", return_value=None)
    @patch("core.platform.is_windows", return_value=False)
    @patch("os.path.isdir", return_value=True)
    @patch("os.path.isfile", side_effect=lambda p: p == "/usr/local/bin/git")
    @patch("core.platform.get_binary_directories")
    def test_find_executable_in_binary_dirs(self, mock_bins, mock_isfile, mock_isdir, mock_is_windows, mock_which):
        """Test find_executable finds executable in binary directories."""
        mock_bins.return_value = {"user": [], "system": ["/usr/local/bin"]}
        result = find_executable("git")
        assert result == "/usr/local/bin/git"

    @patch("shutil.which", return_value=None)
    @patch("core.platform.is_windows", return_value=False)
    @patch("core.platform.get_binary_directories")
    def test_find_executable_not_found(self, mock_bins, mock_is_windows, mock_which):
        """Test find_executable returns None when not found."""
        mock_bins.return_value = {"user": [], "system": []}
        result = find_executable("nonexistent")
        assert result is None

    @patch("shutil.which", side_effect=lambda x: "/usr/bin/python3" if x == "python3" else None)
    @patch("core.platform.is_windows", return_value=False)
    def test_find_executable_with_additional_paths(self, mock_is_windows, mock_which):
        """Test find_executable searches additional paths."""
        result = find_executable("python3", additional_paths=["/custom/path"])
        assert result == "/usr/bin/python3"

    @patch("core.platform.is_windows", return_value=True)
    @patch("shutil.which")
    def test_find_executable_windows_extensions(self, mock_which, mock_is_windows):
        """Test find_executable tries Windows extensions."""
        # First call (without extension) returns None, second (with .exe) returns path
        mock_which.side_effect = lambda x: "C:\\Program Files\\Git\\bin\\git.exe" if x.endswith(".exe") else None
        result = find_executable("git")
        assert result == "C:\\Program Files\\Git\\bin\\git.exe"

    @patch("core.platform.is_windows", return_value=False)
    @patch("core.platform.is_macos", return_value=False)
    @patch("pathlib.Path.home", return_value=Path("/home/user"))
    def test_get_claude_detection_paths_linux(self, mock_home, mock_is_macos, mock_is_windows):
        """Test get_claude_detection_paths on Linux."""
        result = get_claude_detection_paths()
        assert any("/home/user/.local/bin/claude" in p for p in result)

    @patch("core.platform.is_windows", return_value=True)
    @patch("pathlib.Path.home", return_value=Path("C:\\Users\\test"))
    def test_get_claude_detection_paths_windows(self, mock_home, mock_is_windows):
        """Test get_claude_detection_paths on Windows."""
        result = get_claude_detection_paths()
        assert any("claude.exe" in p for p in result)
        assert any("claude.cmd" in p for p in result)

    @patch("core.platform.is_windows", return_value=False)
    @patch("core.platform.is_macos", return_value=True)
    @patch("core.platform.is_windows", return_value=False)
    @patch("core.platform.get_homebrew_path", return_value="/opt/homebrew/bin")
    @patch("pathlib.Path.home", return_value=Path("/home/user"))
    def test_get_claude_detection_paths_macos_with_homebrew(self, mock_home, mock_get_homebrew, mock_is_windows2, mock_is_macos, mock_is_windows1):
        """Test get_claude_detection_paths includes Homebrew on macOS."""
        result = get_claude_detection_paths()
        assert any("homebrew" in p for p in result)

    @patch("core.platform.is_windows", return_value=False)
    @patch("core.platform.is_macos", return_value=False)
    @patch("pathlib.Path.home", return_value=Path("/home/user"))
    def test_get_claude_detection_paths_structured_linux(self, mock_home, mock_is_macos, mock_is_windows):
        """Test get_claude_detection_paths_structured on Linux."""
        result = get_claude_detection_paths_structured()
        assert "homebrew" in result
        assert "platform" in result
        assert "nvm_versions_dir" in result
        assert "/home/user/.nvm/versions/node" in result["nvm_versions_dir"]

    def test_get_python_commands_windows(self):
        """Test get_python_commands on Windows."""
        with patch("core.platform.is_windows", return_value=True):
            result = get_python_commands()
            assert ["py", "-3"] in result
            assert ["python"] in result
            assert ["python3"] in result

    def test_get_python_commands_unix(self):
        """Test get_python_commands on Unix systems."""
        with patch("core.platform.is_windows", return_value=False):
            result = get_python_commands()
            assert result == [["python3"], ["python"]]


# ============================================================================
# CLI Path Validation Tests
# ============================================================================


class TestValidateCliPath:
    """Tests for CLI path validation."""

    def test_validate_cli_path_empty_string(self):
        """Test validate_cli_path rejects empty string."""
        assert validate_cli_path("") is False
        assert validate_cli_path("   ") is False

    def test_validate_cli_path_none(self):
        """Test validate_cli_path rejects None."""
        assert validate_cli_path(None) is False

    def test_validate_cli_path_shell_metacharacters(self):
        """Test validate_cli_path rejects shell metacharacters."""
        assert validate_cli_path("test; rm -rf /") is False
        assert validate_cli_path("test && echo malicious") is False
        assert validate_cli_path("test`whoami`") is False
        assert validate_cli_path("test$(evil)") is False

    def test_validate_cli_path_directory_traversal(self):
        """Test validate_cli_path rejects directory traversal."""
        assert validate_cli_path("../../etc/passwd") is False
        assert validate_cli_path("..\\..\\system32\\config") is False

    def test_validate_cli_path_newlines(self):
        """Test validate_cli_path rejects newlines."""
        assert validate_cli_path("test\nmalicious") is False
        assert validate_cli_path("test\rmalicious") is False

    def test_validate_cli_path_windows_env_var(self):
        """Test validate_cli_path rejects Windows environment variables."""
        with patch("core.platform.is_windows", return_value=True):
            assert validate_cli_path("%TEMP%\\evil.exe") is False
            assert validate_cli_path("%PATH%") is False

    def test_validate_cli_path_valid_absolute_path(self):
        """Test validate_cli_path accepts valid absolute paths."""
        with patch("os.path.isabs", return_value=True):
            with patch("os.path.isfile", return_value=True):
                assert validate_cli_path("/usr/bin/claude") is True

    def test_validate_cli_path_nonexistent_absolute_path(self):
        """Test validate_cli_path rejects nonexistent absolute paths."""
        with patch("os.path.isabs", return_value=True):
            with patch("os.path.isfile", return_value=False):
                assert validate_cli_path("/nonexistent/path") is False

    def test_validate_cli_path_relative_path(self):
        """Test validate_cli_path accepts relative paths."""
        with patch("os.path.isabs", return_value=False):
            assert validate_cli_path("relative/path") is True

    @patch("core.platform.is_windows", return_value=True)
    def test_validate_cli_path_windows_invalid_name(self, mock_is_windows):
        """Test validate_cli_path rejects invalid Windows executable names."""
        assert validate_cli_path("C:\\Program Files\\evil*.exe") is False
        assert validate_cli_path("C:\\Program Files\\test|evil.exe") is False


# ============================================================================
# Shell Execution Tests
# ============================================================================


class TestShellExecution:
    """Tests for shell execution functions."""

    @patch("core.platform.is_windows", return_value=False)
    def test_requires_shell_unix(self, mock_is_windows):
        """Test requires_shell returns False on Unix."""
        assert requires_shell("program.exe") is False

    @patch("core.platform.is_windows", return_value=True)
    def test_requires_shell_windows_cmd(self, mock_is_windows):
        """Test requires_shell returns True for .cmd files on Windows."""
        assert requires_shell("script.cmd") is True

    @patch("core.platform.is_windows", return_value=True)
    def test_requires_shell_windows_bat(self, mock_is_windows):
        """Test requires_shell returns True for .bat files on Windows."""
        assert requires_shell("script.bat") is True

    @patch("core.platform.is_windows", return_value=True)
    def test_requires_shell_windows_ps1(self, mock_is_windows):
        """Test requires_shell returns True for .ps1 files on Windows."""
        assert requires_shell("script.ps1") is True

    @patch("core.platform.is_windows", return_value=True)
    def test_requires_shell_windows_exe(self, mock_is_windows):
        """Test requires_shell returns False for .exe files on Windows."""
        assert requires_shell("program.exe") is False

    @patch.dict(os.environ, {"ComSpec": "C:\\Windows\\System32\\cmd.exe"})
    @patch("core.platform.is_windows", return_value=True)
    def test_get_comspec_path_windows_custom(self, mock_is_windows):
        """Test get_comspec_path uses ComSpec environment variable."""
        result = get_comspec_path()
        assert result == "C:\\Windows\\System32\\cmd.exe"

    @patch.dict(os.environ, {}, clear=True)
    @patch("core.platform.is_windows", return_value=True)
    @patch.dict(os.environ, {"SystemRoot": "C:\\Windows"})
    def test_get_comspec_path_windows_default(self, mock_is_windows):
        """Test get_comspec_path uses default on Windows."""
        result = get_comspec_path()
        assert "cmd.exe" in result.lower()

    @patch("core.platform.is_windows", return_value=False)
    def test_get_comspec_path_unix(self, mock_is_windows):
        """Test get_comspec_path returns /bin/sh on Unix."""
        result = get_comspec_path()
        assert result == "/bin/sh"

    @patch("core.platform.is_windows", return_value=False)
    def test_build_windows_command_unix(self, mock_is_windows):
        """Test build_windows_command on Unix systems."""
        result = build_windows_command("/usr/bin/claude", ["--help"])
        assert result == ["/usr/bin/claude", "--help"]

    @patch("core.platform.is_windows", return_value=True)
    @patch("core.platform.get_comspec_path", return_value="C:\\Windows\\System32\\cmd.exe")
    def test_build_windows_command_cmd_file(self, mock_comspec, mock_is_windows):
        """Test build_windows_command for .cmd files on Windows."""
        result = build_windows_command("C:\\claude.cmd", ["--version"])
        assert len(result) == 5
        assert "cmd.exe" in result[0].lower()
        assert "/c" in result

    @patch("core.platform.is_windows", return_value=True)
    @patch("core.platform.get_comspec_path", return_value="C:\\Windows\\System32\\cmd.exe")
    def test_build_windows_command_exe_file(self, mock_comspec, mock_is_windows):
        """Test build_windows_command for .exe files on Windows."""
        result = build_windows_command("C:\\claude.exe", ["--version"])
        assert result == ["C:\\claude.exe", "--version"]


# ============================================================================
# Environment Variable Tests
# ============================================================================


class TestEnvironmentVariables:
    """Tests for environment variable handling."""

    @patch("core.platform.is_windows", return_value=False)
    def test_get_env_var_unix(self, mock_is_windows):
        """Test get_env_var on Unix (case-sensitive)."""
        with patch.dict(os.environ, {"PATH": "/usr/bin"}):
            result = get_env_var("PATH")
            assert result == "/usr/bin"
            # Case-sensitive on Unix
            result = get_env_var("path")
            assert result is None

    @patch("core.platform.is_windows", return_value=True)
    def test_get_env_var_windows_case_insensitive(self, mock_is_windows):
        """Test get_env_var on Windows (case-insensitive)."""
        with patch.dict(os.environ, {"PATH": "C:\\Windows"}):
            result = get_env_var("path")
            assert result == "C:\\Windows"
            result = get_env_var("PATH")
            assert result == "C:\\Windows"

    def test_get_env_var_default_value(self):
        """Test get_env_var returns default value when not found."""
        with patch("core.platform.is_windows", return_value=False):
            result = get_env_var("NONEXISTENT", "default_value")
            assert result == "default_value"


# ============================================================================
# Platform Description Tests
# ============================================================================


class TestPlatformDescription:
    """Tests for platform description functions."""

    @patch("platform.system", return_value="Linux")
    @patch("platform.machine", return_value="x86_64")
    @patch("core.platform.get_current_os")
    def test_get_platform_description_linux(self, mock_get_os, mock_machine, mock_system):
        """Test get_platform_description on Linux."""
        mock_get_os.return_value = OS.LINUX
        result = get_platform_description()
        assert "Linux" in result
        assert "x86_64" in result

    @patch("platform.system", return_value="Darwin")
    @patch("platform.machine", return_value="arm64")
    @patch("core.platform.get_current_os")
    def test_get_platform_description_macos(self, mock_get_os, mock_machine, mock_system):
        """Test get_platform_description on macOS."""
        mock_get_os.return_value = OS.MACOS
        result = get_platform_description()
        assert "macOS" in result
        assert "arm64" in result

    @patch("platform.system", return_value="Windows")
    @patch("platform.machine", return_value="AMD64")
    @patch("core.platform.get_current_os")
    def test_get_platform_description_windows(self, mock_get_os, mock_machine, mock_system):
        """Test get_platform_description on Windows."""
        mock_get_os.return_value = OS.WINDOWS
        result = get_platform_description()
        assert "Windows" in result
        assert "AMD64" in result
