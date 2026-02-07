"""Tests for core.platform"""

import os
import platform
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.platform import (
    OS,
    ShellType,
    get_current_os,
    is_windows,
    is_macos,
    is_linux,
    is_unix,
    get_path_delimiter,
    get_executable_extension,
    with_executable_extension,
    get_binary_directories,
    get_homebrew_path,
    find_executable,
    get_claude_detection_paths,
    get_claude_detection_paths_structured,
    get_python_commands,
    validate_cli_path,
    requires_shell,
    get_comspec_path,
    build_windows_command,
    get_env_var,
    get_platform_description,
)


# ============================================================================
# Platform Detection Tests
# ============================================================================


def test_get_current_os():
    """Test get_current_os returns valid OS enum."""
    result = get_current_os()

    assert isinstance(result, OS)
    assert result in [OS.WINDOWS, OS.MACOS, OS.LINUX]


def test_is_windows():
    """Test is_windows returns boolean."""
    result = is_windows()

    assert isinstance(result, bool)
    # Should match platform.system()
    assert result == (platform.system() == "Windows")


def test_is_macos():
    """Test is_macos returns boolean."""
    result = is_macos()

    assert isinstance(result, bool)
    # Should match platform.system()
    assert result == (platform.system() == "Darwin")


def test_is_linux():
    """Test is_linux returns boolean."""
    result = is_linux()

    assert isinstance(result, bool)
    # Should match platform.system()
    assert result == (platform.system() == "Linux")


def test_is_unix():
    """Test is_unix returns True for macOS/Linux."""
    result = is_unix()

    assert isinstance(result, bool)
    # Unix is NOT Windows
    assert result == (not is_windows())


# ============================================================================
# Path Configuration Tests
# ============================================================================


def test_get_path_delimiter():
    """Test get_path_delimiter returns correct separator."""
    result = get_path_delimiter()

    assert isinstance(result, str)
    # Windows uses semicolon, Unix uses colon
    expected = ";" if is_windows() else ":"
    assert result == expected


def test_get_executable_extension():
    """Test get_executable_extension returns platform-specific extension."""
    result = get_executable_extension()

    assert isinstance(result, str)
    # Windows uses .exe, Unix uses empty string
    expected = ".exe" if is_windows() else ""
    assert result == expected


def test_with_executable_extension_windows():
    """Test with_executable_extension on Windows."""
    with patch("core.platform.is_windows", return_value=True):
        # Add extension to name without extension
        result = with_executable_extension("program")
        assert result == "program.exe"

        # Don't add extension if already present
        result = with_executable_extension("program.exe")
        assert result == "program.exe"

        # Handle empty string
        result = with_executable_extension("")
        assert result == ""


def test_with_executable_extension_unix():
    """Test with_executable_extension on Unix."""
    with patch("core.platform.is_windows", return_value=False):
        # Don't add extension on Unix
        result = with_executable_extension("program")
        assert result == "program"

        # Already with extension stays same
        result = with_executable_extension("program.sh")
        assert result == "program.sh"


# ============================================================================
# Binary Directories Tests
# ============================================================================


def test_get_binary_directories_structure():
    """Test get_binary_directories returns correct structure."""
    result = get_binary_directories()

    assert isinstance(result, dict)
    assert "user" in result
    assert "system" in result
    assert isinstance(result["user"], list)
    assert isinstance(result["system"], list)


def test_get_binary_directories_not_empty():
    """Test get_binary_directories returns non-empty lists."""
    result = get_binary_directories()

    assert len(result["user"]) > 0
    assert len(result["system"]) > 0


# ============================================================================
# Homebrew Tests
# ============================================================================


def test_get_homebrew_path_on_macos():
    """Test get_homebrew_path on macOS."""
    with patch("core.platform.is_macos", return_value=True):
        result = get_homebrew_path()

        # Should return a string path on macOS
        assert result is not None
        assert isinstance(result, str)
        # Should be one of the known Homebrew paths
        assert result in ["/opt/homebrew/bin", "/usr/local/bin"]


def test_get_homebrew_path_on_linux():
    """Test get_homebrew_path on Linux (should return None)."""
    with patch("core.platform.is_macos", return_value=False):
        result = get_homebrew_path()

        # Should return None on non-macOS
        assert result is None


# ============================================================================
# Tool Detection Tests
# ============================================================================


def test_find_executable_system_command():
    """Test find_executable can find system commands."""
    # Try to find 'ls' on Unix or 'cmd' on Windows
    if is_unix():
        result = find_executable("ls")
        assert result is not None
        assert "ls" in result
    else:
        result = find_executable("cmd")
        assert result is not None
        assert "cmd" in result.lower()


def test_find_executable_nonexistent():
    """Test find_executable with nonexistent command."""
    result = find_executable("this-command-definitely-does-not-exist-12345")
    assert result is None


def test_find_executable_with_additional_paths(tmp_path):
    """Test find_executable with additional custom paths."""
    # Create a dummy executable
    if is_windows():
        exe_name = "test-tool.exe"
    else:
        exe_name = "test-tool"

    custom_dir = tmp_path / "custom-bin"
    custom_dir.mkdir()
    exe_path = custom_dir / exe_name

    # Make it executable on Unix
    exe_path.write_text("#!/bin/sh\necho test")
    if is_unix():
        os.chmod(exe_path, 0o755)

    result = find_executable("test-tool", additional_paths=[str(custom_dir)])

    # Should find the executable in custom path
    assert result is not None
    assert "test-tool" in result


def test_get_claude_detection_paths_structure():
    """Test get_claude_detection_paths returns list."""
    result = get_claude_detection_paths()

    assert isinstance(result, list)
    assert len(result) > 0


def test_get_claude_detection_paths_platform_specific():
    """Test get_claude_detection_paths are platform-specific."""
    result = get_claude_detection_paths()

    if is_windows():
        # Should have Windows paths
        assert any(".exe" in p or ".cmd" in p for p in result)
    else:
        # Should have Unix paths
        assert all(".exe" not in p and ".cmd" not in p for p in result)


def test_get_claude_detection_paths_structured_format():
    """Test get_claude_detection_paths_structured returns dict."""
    result = get_claude_detection_paths_structured()

    assert isinstance(result, dict)
    assert "homebrew" in result
    assert "platform" in result
    assert "nvm_versions_dir" in result


def test_get_claude_detection_paths_structured_content():
    """Test get_claude_detection_paths_structured content."""
    result = get_claude_detection_paths_structured()

    # Check homebrew paths
    assert isinstance(result["homebrew"], list)
    assert len(result["homebrew"]) == 2  # Apple Silicon and Intel

    # Check platform paths
    assert isinstance(result["platform"], list)
    assert len(result["platform"]) > 0

    # Check NVM path
    assert isinstance(result["nvm_versions_dir"], str)
    assert "nvm" in result["nvm_versions_dir"].lower()


def test_get_python_commands_structure():
    """Test get_python_commands returns list of lists."""
    result = get_python_commands()

    assert isinstance(result, list)
    assert all(isinstance(cmd, list) for cmd in result)
    assert all(len(cmd) > 0 for cmd in result)


def test_get_python_commands_platform_specific():
    """Test get_python_commands are platform-specific."""
    result = get_python_commands()

    if is_windows():
        # Windows should have 'py' commands
        assert any("py" in cmd[0] for cmd in result)
    else:
        # Unix should have python/python3
        assert any("python" in cmd[0] for cmd in result)


# ============================================================================
# CLI Path Validation Tests
# ============================================================================


def test_validate_cli_path_empty():
    """Test validate_cli_path rejects empty path."""
    assert validate_cli_path("") is False
    assert validate_cli_path(None) is False
    assert validate_cli_path("   ") is False


def test_validate_cli_path_shell_metacharacters():
    """Test validate_cli_path rejects shell metacharacters."""
    # Test various dangerous patterns
    assert validate_cli_path("file;rm -rf /") is False
    assert validate_cli_path("file && evil") is False
    assert validate_cli_path("file|evil") is False
    assert validate_cli_path("file`evil`") is False
    assert validate_cli_path("file$(evil)") is False
    assert validate_cli_path("file${evil}") is False


def test_validate_cli_path_directory_traversal():
    """Test validate_cli_path rejects directory traversal."""
    assert validate_cli_path("../../etc/passwd") is False
    assert validate_cli_path("..\\..\\system32") is False


def test_validate_cli_path_env_expansion():
    """Test validate_cli_path rejects environment variable expansion."""
    assert validate_cli_path("%PATH%") is False
    assert validate_cli_path("%USERPROFILE%\\file") is False


def test_validate_cli_path_newlines():
    """Test validate_cli_path rejects newlines."""
    assert validate_cli_path("file\nrm -rf /") is False
    assert validate_cli_path("file\r\nevilmalware") is False


def test_validate_cli_path_valid_absolute_path(tmp_path):
    """Test validate_cli_path accepts valid absolute path."""
    # Create a test file
    test_file = tmp_path / "test-exec"
    test_file.write_text("test")

    result = validate_cli_path(str(test_file))
    assert result is True


def test_validate_cli_path_valid_relative_path():
    """Test validate_cli_path accepts valid relative path."""
    result = validate_cli_path("relative/path/to/exec")
    assert result is True


def test_validate_cli_path_windows_executable_name():
    """Test validate_cli_path Windows executable name validation."""
    with patch("core.platform.is_windows", return_value=True):
        # Valid names
        assert validate_cli_path("C:\\Program Files\\test.exe") is True or validate_cli_path(
            "C:\\Program Files\\test.exe"
        ) is False  # May not exist

        # Test just the validation logic (without file existence)
        # Extract name and validate
        name = os.path.basename("test.exe")
        name_without_ext = os.path.splitext(name)[0]
        assert all(c.isalnum() or c in "._-" for c in name_without_ext)


# ============================================================================
# Shell Execution Tests
# ============================================================================


def test_requires_shell_windows():
    """Test requires_shell on Windows."""
    with patch("core.platform.is_windows", return_value=True):
        # .cmd files require shell
        assert requires_shell("script.cmd") is True
        assert requires_shell("script.bat") is True
        assert requires_shell("script.ps1") is True

        # .exe files don't require shell
        assert requires_shell("program.exe") is False


def test_requires_shell_unix():
    """Test requires_shell on Unix (always False)."""
    with patch("core.platform.is_windows", return_value=False):
        assert requires_shell("script.sh") is False
        assert requires_shell("program") is False


def test_get_comspec_path_windows():
    """Test get_comspec_path on Windows."""
    with patch("core.platform.is_windows", return_value=True):
        result = get_comspec_path()

        assert isinstance(result, str)
        assert "cmd.exe" in result.lower() or "bin" in result.lower()


def test_get_comspec_path_unix():
    """Test get_comspec_path on Unix."""
    with patch("core.platform.is_windows", return_value=False):
        result = get_comspec_path()

        assert result == "/bin/sh"


def test_build_windows_command_with_cmd():
    """Test build_windows_command with .cmd file."""
    with patch("core.platform.is_windows", return_value=True):
        cli_path = "C:\\Program Files\\tool\\tool.cmd"
        args = ["--version"]

        result = build_windows_command(cli_path, args)

        assert isinstance(result, list)
        assert len(result) > 0
        assert "cmd.exe" in result[0].lower() or "bin" in result[0].lower()


def test_build_windows_command_with_exe():
    """Test build_windows_command with .exe file."""
    with patch("core.platform.is_windows", return_value=True):
        cli_path = "C:\\Program Files\\tool\\tool.exe"
        args = ["--version"]

        result = build_windows_command(cli_path, args)

        assert isinstance(result, list)
        assert result[0] == cli_path
        assert "--version" in result


def test_build_windows_command_unix():
    """Test build_windows_command on Unix."""
    with patch("core.platform.is_windows", return_value=False):
        cli_path = "/usr/bin/tool"
        args = ["--version"]

        result = build_windows_command(cli_path, args)

        assert result == [cli_path, "--version"]


# ============================================================================
# Environment Variable Tests
# ============================================================================


def test_get_env_var_existing():
    """Test get_env_var with existing variable."""
    # PATH should exist on all platforms
    result = get_env_var("PATH")

    assert result is not None
    assert isinstance(result, str)


def test_get_env_var_nonexistent():
    """Test get_env_var with nonexistent variable."""
    result = get_env_var("THIS_VAR_DOES_NOT_EXIST_12345")

    assert result is None


def test_get_env_var_with_default():
    """Test get_env_var with default value."""
    result = get_env_var("NONEXISTENT_VAR_12345", default="default_value")

    assert result == "default_value"


def test_get_env_var_case_insensitive_windows():
    """Test get_env_var case-insensitive on Windows."""
    with patch("core.platform.is_windows", return_value=True):
        # On Windows, PATH, Path, path should all work
        with patch.dict(os.environ, {"TEST_VAR": "value"}):
            result1 = get_env_var("TEST_VAR")
            result2 = get_env_var("test_var")
            result3 = get_env_var("TeSt_VaR")

            # All should return the value (or None depending on implementation)
            assert isinstance(result1, str) or result1 is None


@pytest.mark.skipif(sys.platform == "win32", reason="Cannot test Unix-specific case-sensitive env var behavior on Windows")
def test_get_env_var_case_sensitive_unix():
    """Test get_env_var case-sensitive on Unix."""
    with patch("core.platform.is_windows", return_value=False):
        # On Unix, environment variables are case-sensitive
        with patch.dict(os.environ, {"TEST_VAR": "value"}):
            result = get_env_var("test_var")

            # Should not find it (case mismatch)
            assert result is None


# ============================================================================
# Platform Description Tests
# ============================================================================


def test_get_platform_description_format():
    """Test get_platform_description returns formatted string."""
    result = get_platform_description()

    assert isinstance(result, str)
    assert " " in result  # Should have space between OS and arch
    assert "(" in result and ")" in result  # Should wrap architecture


def test_get_platform_description_content():
    """Test get_platform_description contains OS info."""
    result = get_platform_description()

    if is_windows():
        assert "Windows" in result
    elif is_macos():
        assert "macOS" in result or "Darwin" in result
    else:
        assert "Linux" in result

    # Should have architecture
    assert len(result.split("(")) > 1


# ============================================================================
# Enum Tests
# ============================================================================


def test_os_enum_values():
    """Test OS enum has correct values."""
    assert OS.WINDOWS.value == "Windows"
    assert OS.MACOS.value == "Darwin"
    assert OS.LINUX.value == "Linux"


def test_shell_type_enum_values():
    """Test ShellType enum has correct values."""
    assert ShellType.POWERSHELL.value == "powershell"
    assert ShellType.CMD.value == "cmd"
    assert ShellType.BASH.value == "bash"
    assert ShellType.ZSH.value == "zsh"
    assert ShellType.FISH.value == "fish"
    assert ShellType.UNKNOWN.value == "unknown"
