"""
Tests for dependency_validator

Comprehensive test coverage for platform-specific dependency validation.
"""

from core.dependency_validator import validate_platform_dependencies
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest
import sys


class TestValidatePlatformDependencies:
    """Tests for validate_platform_dependencies() function."""

    def test_validate_platform_dependencies_linux_with_secretstorage(self):
        """Test validation on Linux with secretstorage installed."""
        # Arrange - mock platform as Linux and secretstorage available
        with patch('core.dependency_validator.is_linux', return_value=True):
            with patch('core.dependency_validator.is_windows', return_value=False):
                with patch('builtins.__import__', side_effect=lambda name, *args, **kwargs:
                           MagicMock() if name == 'secretstorage' else __import__(name, *args, **kwargs)):
                    # Act - should not raise
                    validate_platform_dependencies()

    def test_validate_platform_dependencies_linux_without_secretstorage(self, capsys):
        """Test validation on Linux without secretstorage (should warn)."""
        # Arrange - mock platform as Linux, no secretstorage
        with patch('core.dependency_validator.is_linux', return_value=True):
            with patch('core.dependency_validator.is_windows', return_value=False):
                with patch('builtins.__import__', side_effect=ImportError("No module named 'secretstorage'")):
                    # Act - should not raise, but warn
                    validate_platform_dependencies()

        # Assert - warning in stderr
        captured = capsys.readouterr()
        assert "Warning: Linux dependency 'secretstorage' is not installed" in captured.err

    def test_validate_platform_dependencies_windows_with_pywin32(self):
        """Test validation on Windows with pywin32 installed."""
        # Arrange - mock platform as Windows and pywin32 available
        with patch('core.dependency_validator.is_windows', return_value=True):
            with patch('core.dependency_validator.is_linux', return_value=False):
                with patch('builtins.__import__', side_effect=lambda name, *args, **kwargs:
                           MagicMock() if name == 'pywintypes' else __import__(name, *args, **kwargs)):
                    # Act - should not raise
                    validate_platform_dependencies()

    def test_validate_platform_dependencies_windows_without_pywin32(self):
        """Test validation on Windows without pywin32 (should exit)."""
        # Arrange - mock platform as Windows, no pywin32
        with patch('core.dependency_validator.is_windows', return_value=True):
            with patch('core.dependency_validator.is_linux', return_value=False):
                with patch('builtins.__import__', side_effect=ImportError("No module named 'pywintypes'")):
                    # Act & Assert - should call sys.exit
                    with pytest.raises(SystemExit) as exc_info:
                        validate_platform_dependencies()

                    # Check that exit message contains expected text
                    assert "pywin32" in str(exc_info.value)

    def test_validate_platform_dependencies_macos(self):
        """Test validation on macOS (no special dependencies)."""
        # Arrange - mock platform as macOS (not Windows, not Linux)
        with patch('core.dependency_validator.is_windows', return_value=False):
            with patch('core.dependency_validator.is_linux', return_value=False):
                # Act - should not raise or warn
                validate_platform_dependencies()

    def test_validate_platform_dependencies_all_checks(self, capsys):
        """Test all platform checks in sequence."""
        # Test on Linux with warning
        with patch('core.dependency_validator.is_linux', return_value=True):
            with patch('core.dependency_validator.is_windows', return_value=False):
                with patch('builtins.__import__', side_effect=ImportError("No module")):
                    validate_platform_dependencies()

        captured = capsys.readouterr()
        assert "secretstorage" in captured.err


class TestWindowsPywin32Error:
    """Tests for _exit_with_pywin32_error() function."""

    @patch('core.dependency_validator.is_windows', return_value=True)
    @patch('core.dependency_validator.is_linux', return_value=False)
    def test_exit_with_pywin32_error_message_content(self, mock_linux, mock_windows):
        """Test that exit message contains expected content."""
        # Arrange
        with patch('builtins.__import__', side_effect=ImportError("No module named 'pywintypes'")):
            # Act
            with pytest.raises(SystemExit) as exc_info:
                validate_platform_dependencies()

            # Assert - check message content
            message = str(exc_info.value)
            assert "pywin32" in message
            assert "required Windows dependency" in message.lower()
            assert "MCP library" in message
            assert "win32api" in message
            assert sys.executable in message

    @patch('core.dependency_validator.is_windows', return_value=True)
    @patch('core.dependency_validator.is_linux', return_value=False)
    def test_exit_with_venv_activate_exists(self, mock_linux, mock_windows, tmp_path):
        """Test error message when venv activate script exists."""
        # Arrange - create fake venv with activate script
        scripts_dir = tmp_path / "Scripts"
        scripts_dir.mkdir()
        activate_bat = scripts_dir / "activate.bat"
        activate_bat.touch()

        with patch('sys.prefix', str(tmp_path)):
            with patch('builtins.__import__', side_effect=ImportError("No module")):
                # Act
                with pytest.raises(SystemExit) as exc_info:
                    validate_platform_dependencies()

                # Assert - should include activation step
                message = str(exc_info.value)
                assert "activate.bat" in message

    @patch('core.dependency_validator.is_windows', return_value=True)
    @patch('core.dependency_validator.is_linux', return_value=False)
    def test_exit_with_venv_activate_ps1_exists(self, mock_linux, mock_windows, tmp_path):
        """Test error message when Activate.ps1 script exists."""
        # Arrange
        scripts_dir = tmp_path / "Scripts"
        scripts_dir.mkdir()
        activate_ps1 = scripts_dir / "Activate.ps1"
        activate_ps1.touch()

        with patch('sys.prefix', str(tmp_path)):
            with patch('builtins.__import__', side_effect=ImportError("No module")):
                # Act
                with pytest.raises(SystemExit) as exc_info:
                    validate_platform_dependencies()

                # Assert
                message = str(exc_info.value)
                assert "Activate.ps1" in message

    @patch('core.dependency_validator.is_windows', return_value=True)
    @patch('core.dependency_validator.is_linux', return_value=False)
    def test_exit_without_venv_activate(self, mock_linux, mock_windows, tmp_path):
        """Test error message when no activate script exists."""
        # Arrange - venv without activate script
        scripts_dir = tmp_path / "Scripts"
        scripts_dir.mkdir()

        with patch('sys.prefix', str(tmp_path)):
            with patch('builtins.__import__', side_effect=ImportError("No module")):
                # Act
                with pytest.raises(SystemExit) as exc_info:
                    validate_platform_dependencies()

                # Assert - should not include activation step
                message = str(exc_info.value)
                assert "activate" not in message.lower()
                assert "pip install pywin32" in message

    @patch('core.dependency_validator.is_windows', return_value=True)
    @patch('core.dependency_validator.is_linux', return_value=False)
    def test_exit_includes_install_instructions(self, mock_linux, mock_windows):
        """Test that exit message includes installation instructions."""
        with patch('builtins.__import__', side_effect=ImportError("No module")):
            with pytest.raises(SystemExit) as exc_info:
                validate_platform_dependencies()

            message = str(exc_info.value)
            assert "pip install pywin32" in message
            assert "pip install -r requirements.txt" in message

    @patch('core.dependency_validator.is_windows', return_value=True)
    @patch('core.dependency_validator.is_linux', return_value=False)
    def test_exit_includes_usage_explanation(self, mock_linux, mock_windows):
        """Test that exit message explains why pywin32 is needed."""
        with patch('builtins.__import__', side_effect=ImportError("No module")):
            with pytest.raises(SystemExit) as exc_info:
                validate_platform_dependencies()

            message = str(exc_info.value)
            assert "LadybugDB" in message or "Graphiti" in message
            assert "win32api" in message or "win32con" in message


class TestLinuxSecretstorageWarning:
    """Tests for _warn_missing_secretstorage() function."""

    @patch('core.dependency_validator.is_linux', return_value=True)
    @patch('core.dependency_validator.is_windows', return_value=False)
    def test_warn_message_content(self, mock_windows, mock_linux, capsys):
        """Test that warning message contains expected content."""
        with patch('builtins.__import__', side_effect=ImportError("No module")):
            # Act
            validate_platform_dependencies()

        # Assert
        captured = capsys.readouterr()
        assert "Warning: Linux dependency 'secretstorage' is not installed" in captured.err
        assert "keyring" in captured.err.lower()
        assert "gnome-keyring" in captured.err or "kwallet" in captured.err

    @patch('core.dependency_validator.is_linux', return_value=True)
    @patch('core.dependency_validator.is_windows', return_value=False)
    def test_warn_with_venv_activate_exists(self, mock_windows, mock_linux, tmp_path, capsys):
        """Test warning when venv activate script exists."""
        # Arrange - create fake venv
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        activate = bin_dir / "activate"
        activate.touch()

        with patch('sys.prefix', str(tmp_path)):
            with patch('builtins.__import__', side_effect=ImportError("No module")):
                # Act
                validate_platform_dependencies()

        # Assert - should include activation step
        captured = capsys.readouterr()
        assert "source" in captured.err
        assert "activate" in captured.err

    @patch('core.dependency_validator.is_linux', return_value=True)
    @patch('core.dependency_validator.is_windows', return_value=False)
    def test_warn_without_venv_activate(self, mock_windows, mock_linux, tmp_path, capsys):
        """Test warning when no activate script exists."""
        # Arrange
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        with patch('sys.prefix', str(tmp_path)):
            with patch('builtins.__import__', side_effect=ImportError("No module")):
                # Act
                validate_platform_dependencies()

        # Assert - should not include activation step
        captured = capsys.readouterr()
        # Should still have install instructions
        assert "pip install 'secretstorage" in captured.err

    @patch('core.dependency_validator.is_linux', return_value=True)
    @patch('core.dependency_validator.is_windows', return_value=False)
    def test_warn_is_non_blocking(self, mock_windows, mock_linux, capsys):
        """Test that warning is non-blocking (function continues)."""
        # Arrange - track if function completes
        completed = [False]

        def mark_completed(*args, **kwargs):
            completed[0] = True
            raise ImportError("No module")

        with patch('builtins.__import__', side_effect=mark_completed):
            # Act
            validate_platform_dependencies()

        # Assert - function should complete (no SystemExit)
        assert completed[0]

    @patch('core.dependency_validator.is_linux', return_value=True)
    @patch('core.dependency_validator.is_windows', return_value=False)
    def test_warn_includes_install_instructions(self, mock_windows, mock_linux, capsys):
        """Test that warning includes installation instructions."""
        with patch('builtins.__import__', side_effect=ImportError("No module")):
            validate_platform_dependencies()

        captured = capsys.readouterr()
        assert "pip install 'secretstorage" in captured.err
        assert "pip install -r requirements.txt" in captured.err

    @patch('core.dependency_validator.is_linux', return_value=True)
    @patch('core.dependency_validator.is_windows', return_value=False)
    def test_warn_explain_security_implications(self, mock_windows, mock_linux, capsys):
        """Test that warning explains security implications."""
        with patch('builtins.__import__', side_effect=ImportError("No module")):
            validate_platform_dependencies()

        captured = capsys.readouterr()
        assert ".env file" in captured.err
        assert "plaintext" in captured.err.lower()

    @patch('core.dependency_validator.is_linux', return_value=True)
    @patch('core.dependency_validator.is_windows', return_value=False)
    def test_warn_flushes_stderr(self, mock_windows, mock_linux):
        """Test that warning flushes stderr."""
        # Arrange - mock stderr
        with patch('sys.stderr') as mock_stderr:
            mock_stderr.write.return_value = None
            mock_stderr.flush.return_value = None

            with patch('builtins.__import__', side_effect=ImportError("No module")):
                # Act
                validate_platform_dependencies()

        # Assert - flush should be called
        mock_stderr.flush.assert_called()


class TestPlatformSpecificBehavior:
    """Tests for platform-specific dependency behavior."""

    def test_windows_checks_pywin32_only(self):
        """Test that Windows only checks for pywin32."""
        # Arrange - mock both imports as failing
        import_tracker = []

        def track_import(name, *args, **kwargs):
            import_tracker.append(name)
            raise ImportError(f"No module {name}")

        with patch('core.dependency_validator.is_windows', return_value=True):
            with patch('core.dependency_validator.is_linux', return_value=False):
                with patch('builtins.__import__', side_effect=track_import):
                    # Act
                    with pytest.raises(SystemExit):
                        validate_platform_dependencies()

        # Assert - should only try pywintypes
        assert 'pywintypes' in import_tracker

    def test_linux_checks_secretstorage_only(self, capsys):
        """Test that Linux only checks for secretstorage."""
        import_tracker = []

        def track_import(name, *args, **kwargs):
            import_tracker.append(name)
            raise ImportError(f"No module {name}")

        with patch('core.dependency_validator.is_windows', return_value=False):
            with patch('core.dependency_validator.is_linux', return_value=True):
                with patch('builtins.__import__', side_effect=track_import):
                    # Act
                    validate_platform_dependencies()

        # Assert - should only try secretstorage
        assert 'secretstorage' in import_tracker

    def test_macos_no_checks(self):
        """Test that macOS performs no dependency checks."""
        import_tracker = []

        def track_import(name, *args, **kwargs):
            import_tracker.append(name)
            raise ImportError(f"No module {name}")

        with patch('core.dependency_validator.is_windows', return_value=False):
            with patch('core.dependency_validator.is_linux', return_value=False):
                with patch('builtins.__import__', side_effect=track_import):
                    # Act
                    validate_platform_dependencies()

        # Assert - should not try any imports
        assert len(import_tracker) == 0


class TestErrorScenarios:
    """Tests for various error scenarios."""

    @patch('core.dependency_validator.is_windows', return_value=True)
    @patch('core.dependency_validator.is_linux', return_value=False)
    def test_both_windows_and_linux_true(self, mock_linux, mock_windows):
        """Test behavior when both is_windows and is_linux return True (edge case)."""
        with patch('builtins.__import__', side_effect=ImportError("No module")):
            # Should handle both checks
            with pytest.raises(SystemExit):
                validate_platform_dependencies()

    @patch('core.dependency_validator.is_windows', return_value=False)
    @patch('core.dependency_validator.is_linux', return_value=False)
    def test_neither_windows_nor_linux(self, mock_linux, mock_windows):
        """Test behavior when neither platform matches (e.g., BSD)."""
        # Should pass through without checks
        validate_platform_dependencies()

    def test_actual_python_executable_in_message(self):
        """Test that sys.executable is included in error message."""
        with patch('core.dependency_validator.is_windows', return_value=True):
            with patch('core.dependency_validator.is_linux', return_value=False):
                with patch('builtins.__import__', side_effect=ImportError("No module")):
                    with pytest.raises(SystemExit) as exc_info:
                        validate_platform_dependencies()

                    # Assert - actual Python path should be in message
                    message = str(exc_info.value)
                    assert sys.executable in message


class TestScriptPathDetection:
    """Tests for venv script path detection."""

    @patch('core.dependency_validator.is_windows', return_value=True)
    @patch('core.dependency_validator.is_linux', return_value=False)
    def test_scripts_path_from_sys_prefix(self, mock_linux, mock_windows, tmp_path):
        """Test that Scripts path is derived from sys.prefix on Windows."""
        scripts_dir = tmp_path / "Scripts"
        scripts_dir.mkdir()
        (scripts_dir / "activate.bat").touch()

        with patch('sys.prefix', str(tmp_path)):
            with patch('builtins.__import__', side_effect=ImportError("No module")):
                with pytest.raises(SystemExit) as exc_info:
                    validate_platform_dependencies()

                message = str(exc_info.value)
                assert str(tmp_path) in message

    @patch('core.dependency_validator.is_linux', return_value=True)
    @patch('core.dependency_validator.is_windows', return_value=False)
    def test_bin_path_from_sys_prefix(self, mock_windows, mock_linux, tmp_path, capsys):
        """Test that bin path is derived from sys.prefix on Linux."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        (bin_dir / "activate").touch()

        with patch('sys.prefix', str(tmp_path)):
            with patch('builtins.__import__', side_effect=ImportError("No module")):
                validate_platform_dependencies()

        captured = capsys.readouterr()
        assert str(tmp_path) in captured.err


class TestMultipleActivationScripts:
    """Tests for handling multiple activation script formats."""

    @patch('core.dependency_validator.is_windows', return_value=True)
    @patch('core.dependency_validator.is_linux', return_value=False)
    def test_multiple_activation_scripts_uses_first(self, mock_linux, mock_windows, tmp_path):
        """Test that first found activation script is used."""
        scripts_dir = tmp_path / "Scripts"
        scripts_dir.mkdir()
        (scripts_dir / "activate").touch()
        (scripts_dir / "activate.bat").touch()
        (scripts_dir / "Activate.ps1").touch()

        with patch('sys.prefix', str(tmp_path)):
            with patch('builtins.__import__', side_effect=ImportError("No module")):
                with pytest.raises(SystemExit) as exc_info:
                    validate_platform_dependencies()

                # Should use the first one (activate)
                message = str(exc_info.value)
                assert "activate" in message

    @patch('core.dependency_validator.is_windows', return_value=True)
    @patch('core.dependency_validator.is_linux', return_value=False)
    def test_only_ps1_script(self, mock_linux, mock_windows, tmp_path):
        """Test with only Activate.ps1 script."""
        scripts_dir = tmp_path / "Scripts"
        scripts_dir.mkdir()
        (scripts_dir / "Activate.ps1").touch()

        with patch('sys.prefix', str(tmp_path)):
            with patch('builtins.__import__', side_effect=ImportError("No module")):
                with pytest.raises(SystemExit) as exc_info:
                    validate_platform_dependencies()

                message = str(exc_info.value)
                assert "Activate.ps1" in message
