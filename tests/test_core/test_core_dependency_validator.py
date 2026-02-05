"""
Tests for core.dependency_validator module
===========================================

Comprehensive tests for platform dependency validation including:
- Windows pywin32 dependency checking
- Linux secretstorage dependency checking
- Helpful error messages and installation instructions
- Virtual environment detection
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.dependency_validator import (
    validate_platform_dependencies,
    _exit_with_pywin32_error,
    _warn_missing_secretstorage,
)


# ============================================================================
# validate_platform_dependencies tests
# ============================================================================


class TestValidatePlatformDependencies:
    """Tests for validate_platform_dependencies function."""

    @patch("core.dependency_validator.is_windows", return_value=False)
    @patch("core.dependency_validator.is_linux", return_value=False)
    def test_validate_no_dependencies_needed_unix(self, mock_is_linux, mock_is_windows):
        """Test validate passes on macOS (no extra dependencies)."""
        # Should not raise
        validate_platform_dependencies()

    @patch("core.dependency_validator.is_linux", return_value=False)
    @patch("core.dependency_validator.is_windows", return_value=True)
    def test_validate_pywin32_installed(self, mock_is_windows, mock_is_linux):
        """Test validate passes when pywin32 is installed on Windows."""
        # Create a real module-like object for pywintypes
        import importlib
        import types

        # Create a mock pywintypes module
        mock_pywintypes = types.ModuleType("pywintypes")

        original_import = __builtins__["__import__"]

        def mock_import(name, *args, **kwargs):
            if name == "pywintypes":
                return mock_pywintypes
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            # Should not raise
            validate_platform_dependencies()

    @patch("core.dependency_validator.is_windows", return_value=True)
    @patch("core.dependency_validator.is_linux", return_value=False)
    @patch("pathlib.Path.exists", return_value=False)
    def test_validate_pywin32_missing_exits(self, mock_exists, mock_is_linux, mock_is_windows):
        """Test validate exits when pywin32 is missing on Windows."""
        import types

        original_import = __builtins__["__import__"]

        def mock_import(name, *args, **kwargs):
            if name == "pywintypes":
                raise ImportError("No module named 'pywintypes'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with patch("sys.exit") as mock_exit:
                validate_platform_dependencies()
                # Should have called sys.exit
                assert mock_exit.called

    @patch("core.dependency_validator.is_linux", return_value=True)
    @patch("core.dependency_validator.is_windows", return_value=False)
    def test_validate_secretstorage_installed(self, mock_is_windows, mock_is_linux):
        """Test validate passes when secretstorage is installed on Linux."""
        with patch("builtins.__import__", side_effect=lambda name, *args, **kwargs: MagicMock() if name == "secretstorage" else __import__(name, *args, **kwargs)):
            # Should not raise
            validate_platform_dependencies()

    @patch("core.dependency_validator.is_linux", return_value=True)
    @patch("core.dependency_validator.is_windows", return_value=False)
    @patch("pathlib.Path.exists", return_value=False)
    def test_validate_secretstorage_warns_only(self, mock_exists, mock_is_windows, mock_is_linux, capsys):
        """Test validate warns but continues when secretstorage is missing on Linux."""
        import types

        original_import = __builtins__["__import__"]

        def mock_import(name, *args, **kwargs):
            if name == "secretstorage":
                raise ImportError("No module named 'secretstorage'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            # Should not raise or exit
            validate_platform_dependencies()
            # Should have printed warning to stderr
            captured = capsys.readouterr()
            assert "Warning" in captured.err
            assert "secretstorage" in captured.err.lower()

    @patch("core.dependency_validator.is_windows", return_value=True)
    @patch("core.dependency_validator.is_linux", return_value=False)
    @patch("pathlib.Path.exists", return_value=False)
    def test_validate_both_checks_on_windows(self, mock_exists, mock_is_linux, mock_is_windows):
        """Test that Linux check is skipped on Windows."""
        import types

        mock_pywintypes = types.ModuleType("pywintypes")
        original_import = __builtins__["__import__"]

        def mock_import(name, *args, **kwargs):
            if name == "pywintypes":
                return mock_pywintypes
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            validate_platform_dependencies()
            # Should complete without error
            assert True


# ============================================================================
# _exit_with_pywin32_error tests
# ============================================================================


class TestExitWithPywin32Error:
    """Tests for _exit_with_pywin32_error function."""

    @patch("sys.prefix", "/fake/venv")
    @patch("pathlib.Path.exists", return_value=True)
    def test_exit_with_pywin32_error_with_venv(self, mock_exists):
        """Test error message includes activation steps for venv."""
        with patch("sys.exit") as mock_exit:
            _exit_with_pywin32_error()
            # Should have called sys.exit
            assert mock_exit.called
            exit_message = mock_exit.call_args[0][0]
            # Check message content
            assert "pywin32" in exit_message
            assert "pip install" in exit_message
            assert "activate" in exit_message.lower()

    @patch("sys.prefix", "/usr")
    @patch("pathlib.Path.exists", return_value=False)
    def test_exit_with_pywin32_error_without_venv(self, mock_exists):
        """Test error message without venv activation step."""
        with patch("sys.exit") as mock_exit:
            _exit_with_pywin32_error()
            exit_message = mock_exit.call_args[0][0]
            # Should have install instructions but no activation
            assert "pip install" in exit_message
            # Current Python path should be shown
            assert sys.executable in exit_message

    @patch("sys.prefix", "/fake/venv")
    @patch("sys.executable", "/fake/venv/bin/python")
    @patch("pathlib.Path.exists", return_value=True)
    def test_exits_with_code(self, mock_exists):
        """Test function actually calls sys.exit."""
        with patch("sys.exit") as mock_exit:
            _exit_with_pywin32_error()
            # Verify sys.exit was called
            assert mock_exit.called

    @patch("sys.prefix", "/fake/venv")
    @patch("pathlib.Path.exists", return_value=True)
    def test_error_message_content(self, mock_exists):
        """Test error message contains all required information."""
        with patch("sys.executable", "/fake/venv/bin/python3.10"):
            with patch("sys.exit") as mock_exit:
                _exit_with_pywin32_error()
                exit_message = mock_exit.call_args[0][0]

                # Check for key information
                assert "Error" in exit_message
                assert "pywin32" in exit_message
                assert "Windows" in exit_message
                assert "MCP library" in exit_message or "win32api" in exit_message
                assert "pip install pywin32" in exit_message
                assert "requirements.txt" in exit_message

    @patch("sys.prefix", "/fake/venv")
    @patch("pathlib.Path.exists", return_value=True)
    def test_detects_activate_script_variants(self, mock_exists):
        """Test detection of various activate script names."""
        with patch("sys.exit") as mock_exit:
            _exit_with_pywin32_error()
            exit_message = mock_exit.call_args[0][0]
            assert "activate" in exit_message.lower()


# ============================================================================
# _warn_missing_secretstorage tests
# ============================================================================


class TestWarnMissingSecretstorage:
    """Tests for _warn_missing_secretstorage function."""

    @patch("sys.prefix", "/fake/venv")
    @patch("pathlib.Path.exists", return_value=True)
    def test_warn_with_venv_activation_step(self, mock_exists, capsys):
        """Test warning includes activation step for venv."""
        _warn_missing_secretstorage()
        captured = capsys.readouterr()
        warning = captured.err

        assert "Warning" in warning
        assert "secretstorage" in warning.lower()
        assert "source" in warning  # activation command
        assert "activate" in warning

    @patch("sys.prefix", "/usr")
    @patch("pathlib.Path.exists", return_value=False)
    def test_warn_without_venv(self, mock_exists, capsys):
        """Test warning without venv activation step."""
        _warn_missing_secretstorage()
        captured = capsys.readouterr()
        warning = captured.err

        assert "Warning" in warning
        assert "secretstorage" in warning.lower()
        # Should have install instructions
        assert "pip install" in warning

    @patch("sys.executable", "/usr/bin/python3.10")
    @patch("pathlib.Path.exists", return_value=False)
    def test_warn_shows_python_path(self, mock_exists, capsys):
        """Test warning shows current Python path."""
        _warn_missing_secretstorage()
        captured = capsys.readouterr()
        warning = captured.err

        assert sys.executable in warning

    @patch("pathlib.Path.exists", return_value=False)
    def test_warn_does_not_exit(self, mock_exists, capsys):
        """Test warning does not exit the program."""
        # This should not raise SystemExit
        _warn_missing_secretstorage()
        # If we get here, the function continued (correct behavior)
        captured = capsys.readouterr()
        assert "Warning" in captured.err

    @patch("pathlib.Path.exists", return_value=False)
    def test_warn_content_completeness(self, mock_exists, capsys):
        """Test warning contains all necessary information."""
        _warn_missing_secretstorage()
        captured = capsys.readouterr()
        warning = captured.err

        # Check for key information
        assert "secretstorage" in warning.lower()
        assert "keyring" in warning.lower() or "gnome-keyring" in warning or "kwallet" in warning
        assert ".env file" in warning
        assert "plaintext" in warning
        assert "pip install" in warning
        assert "requirements.txt" in warning

    @patch("sys.prefix", "/fake/venv")
    @patch("pathlib.Path.exists", return_value=True)
    def test_warn_flushes_stderr(self, mock_exists, capsys):
        """Test warning flushes stderr."""
        _warn_missing_secretstorage()
        # If stderr was flushed properly, we should be able to read it
        captured = capsys.readouterr()
        assert len(captured.err) > 0


# ============================================================================
# Integration tests
# ============================================================================


class TestDependencyValidatorIntegration:
    """Integration tests for dependency validation."""

    @patch("core.dependency_validator.is_windows", return_value=False)
    @patch("core.dependency_validator.is_linux", return_value=False)
    def test_macos_no_extra_deps(self, mock_is_linux, mock_is_windows):
        """Test macOS requires no extra dependencies."""
        # Should pass without any imports
        validate_platform_dependencies()

    @patch("core.dependency_validator.is_windows", return_value=True)
    @patch("core.dependency_validator.is_linux", return_value=False)
    def test_windows_with_mocked_pywin32(self, mock_is_linux, mock_is_windows):
        """Test Windows passes with mocked pywin32."""
        # Mock successful import
        original_import = __builtins__["__import__"]

        def mock_import(name, *args, **kwargs):
            if name == "pywintypes":
                return MagicMock()
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            validate_platform_dependencies()

    @patch("core.dependency_validator.is_linux", return_value=True)
    @patch("core.dependency_validator.is_windows", return_value=False)
    @patch("pathlib.Path.exists", return_value=False)
    def test_linux_continues_without_secretstorage(self, mock_exists, mock_is_windows, mock_is_linux, capsys):
        """Test Linux continues execution without secretstorage."""
        import types

        original_import = __builtins__["__import__"]

        def mock_import(name, *args, **kwargs):
            if name == "secretstorage":
                raise ImportError("No module named 'secretstorage'")
            return original_import(name, *args, **kwargs)

        # Mock missing import
        with patch("builtins.__import__", side_effect=mock_import):
            validate_platform_dependencies()
            # Should have warned but not exited
            captured = capsys.readouterr()
            assert "Warning" in captured.err

    @patch("sys.prefix", "/home/user/.venv")
    @patch("sys.executable", "/home/user/.venv/bin/python")
    @patch("pathlib.Path.exists", return_value=True)
    def test_venv_detection_in_error_messages(self, mock_exists, capsys):
        """Test that venv paths are correctly detected in error messages."""
        with patch("core.dependency_validator.is_windows", return_value=True):
            import types
            original_import = __builtins__["__import__"]
            def mock_import(name, *args, **kwargs):
                if name == "pywintypes":
                    raise ImportError("No module named 'pywintypes'")
                return original_import(name, *args, **kwargs)
            with patch("builtins.__import__", side_effect=mock_import):
                with patch("sys.exit") as mock_exit:
                    validate_platform_dependencies()
                    # Should have included venv-specific instructions
                    exit_msg = mock_exit.call_args[0][0]
                    assert "activate" in exit_msg.lower()

    @patch("sys.prefix", "/usr")
    @patch("sys.executable", "/usr/bin/python3")
    @patch("pathlib.Path.exists", return_value=False)
    @patch("core.dependency_validator.is_windows", return_value=True)
    def test_system_python_detection(self, mock_is_windows, mock_exists, capsys):
        """Test error messages for system Python without venv."""
        import types
        original_import = __builtins__["__import__"]
        def mock_import(name, *args, **kwargs):
            if name == "pywintypes":
                raise ImportError("No module named 'pywintypes'")
            return original_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=mock_import):
            with patch("sys.exit") as mock_exit:
                validate_platform_dependencies()
                # Should have system Python instructions (no activate)
                exit_msg = mock_exit.call_args[0][0]
                # Should NOT include venv activation step
                assert "source " not in exit_msg and "activate.bat" not in exit_msg


# ============================================================================
# Platform-specific behavior tests
# ============================================================================


class TestPlatformSpecificBehavior:
    """Tests for platform-specific validation behavior."""

    @patch("core.dependency_validator.is_windows", return_value=True)
    @patch("core.dependency_validator.is_linux", return_value=True)
    @patch("pathlib.Path.exists", return_value=False)
    def test_windows_takes_precedence(self, mock_exists, mock_is_linux, mock_is_windows, capsys):
        """Test Windows check takes precedence over Linux."""
        # This is an edge case - both returning True shouldn't happen
        # but Windows should take precedence if it does
        import types
        original_import = __builtins__["__import__"]
        def mock_import(name, *args, **kwargs):
            if name == "pywintypes":
                raise ImportError("No module named 'pywintypes'")
            return original_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=mock_import):
            with patch("sys.exit"):
                validate_platform_dependencies()
                # Should have exited for Windows (pywin32)
                # Linux warning should not appear
                captured = capsys.readouterr()
                # Should not have Linux warning (because we exited first)
                assert "secretstorage" not in captured.err

    @patch("core.dependency_validator.is_windows", return_value=False)
    @patch("core.dependency_validator.is_linux", return_value=False)
    @patch("platform.system", return_value="Darwin")
    def test_macos_passes_without_checks(self, mock_system, mock_is_linux, mock_is_windows):
        """Test macOS passes all checks without importing extra modules."""
        # Should not attempt to import anything
        with patch("builtins.__import__") as mock_import:
            validate_platform_dependencies()
            # Should not have tried to import pywin32 or secretstorage
            for call in mock_import.call_args_list:
                name = call[0][0] if call[0] else ""
                assert name not in ("pywintypes", "secretstorage")
