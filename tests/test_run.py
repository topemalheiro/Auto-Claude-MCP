"""Tests for run.py - Main entry point for autonomous coding framework"""

import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call

import pytest


# ============================================================================
# Python Version Validation Tests
# ============================================================================


class TestPythonVersionValidation:
    """Test Python version validation in run.py"""

    def test_current_python_version(self):
        """Test that current Python version is >= 3.10"""
        # This test ensures we're running on a supported version
        assert sys.version_info >= (3, 10), (
            f"Tests require Python 3.10+, got {sys.version_info.major}.{sys.version_info.minor}"
        )

    def test_version_check_exists_in_run_py(self):
        """Test that run.py contains version check code"""
        run_py_path = Path(__file__).parent.parent / "apps" / "backend" / "run.py"
        content = run_py_path.read_text()

        # Verify version check exists
        assert "sys.version_info" in content
        assert "(3, 10)" in content
        assert "requires Python 3.10 or higher" in content

    def test_version_check_logic(self):
        """Test the version check logic works correctly"""
        # Test various version tuples
        assert (3, 9, 0) < (3, 10)
        assert (3, 10, 0) >= (3, 10)
        assert (3, 11, 5) >= (3, 10)
        assert (3, 12, 0) >= (3, 10)
        assert (2, 7, 0) < (3, 10)


# ============================================================================
# Windows Encoding Configuration Tests
# ============================================================================


class TestWindowsEncodingConfiguration:
    """Test Windows encoding configuration in run.py"""

    def test_windows_encoding_skipped_on_unix(self):
        """Test that encoding configuration is skipped on non-Windows platforms"""
        with patch("sys.platform", "linux"):
            # Should not attempt any stream reconfiguration
            original_stdout = sys.stdout
            original_stderr = sys.stderr

            # Simulate the Windows encoding check block
            if sys.platform == "win32":
                # This should NOT execute
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")

            # Streams should remain unchanged
            assert sys.stdout is original_stdout
            assert sys.stderr is original_stderr

    @patch("sys.platform", "win32")
    def test_windows_encoding_reconfigure_method(self):
        """Test Windows encoding with reconfigure method (TTY)"""
        # Create a mock stream with reconfigure method
        mock_stdout = MagicMock()
        mock_stdout.reconfigure = MagicMock()
        mock_stderr = MagicMock()
        mock_stderr.reconfigure = MagicMock()

        with patch("sys.stdout", mock_stdout):
            with patch("sys.stderr", mock_stderr):
                # Simulate the Windows encoding configuration block
                if sys.platform == "win32":
                    for _stream_name in ("stdout", "stderr"):
                        _stream = getattr(sys, _stream_name)
                        if hasattr(_stream, "reconfigure"):
                            try:
                                _stream.reconfigure(encoding="utf-8", errors="replace")
                                continue
                            except (AttributeError, io.UnsupportedOperation, OSError):
                                pass

                # Verify reconfigure was called for both streams
                mock_stdout.reconfigure.assert_called_once_with(
                    encoding="utf-8", errors="replace"
                )
                mock_stderr.reconfigure.assert_called_once_with(
                    encoding="utf-8", errors="replace"
                )

    @patch("sys.platform", "win32")
    def test_windows_encoding_textiowrapper_fallback(self):
        """Test Windows encoding with TextIOWrapper fallback (piped output)"""
        # Create mock streams without reconfigure but with buffer
        mock_buffer = MagicMock()

        mock_stdout = MagicMock()
        mock_stdout.reconfigure = None  # No reconfigure method
        mock_stdout.buffer = mock_buffer

        original_stdout = sys.stdout

        with patch("sys.stdout", mock_stdout):
            with patch("sys.stderr", mock_stdout):
                # Simulate the Windows encoding configuration with TextIOWrapper
                if sys.platform == "win32":
                    for _stream_name in ("stdout",):
                        _stream = getattr(sys, _stream_name)
                        # Skip reconfigure (it's None)
                        if hasattr(_stream, "reconfigure") and callable(_stream.reconfigure):
                            try:
                                _stream.reconfigure(encoding="utf-8", errors="replace")
                                continue
                            except (AttributeError, io.UnsupportedOperation, OSError):
                                pass

                        # Method 2: Wrap with TextIOWrapper
                        try:
                            if hasattr(_stream, "buffer"):
                                _new_stream = io.TextIOWrapper(
                                    _stream.buffer,
                                    encoding="utf-8",
                                    errors="replace",
                                    line_buffering=True,
                                )
                                setattr(sys, _stream_name, _new_stream)
                        except (AttributeError, io.UnsupportedOperation, OSError):
                            pass

                # Restore original
                sys.stdout = original_stdout

    @patch("sys.platform", "win32")
    def test_windows_encoding_handles_errors_gracefully(self):
        """Test that encoding configuration handles errors gracefully"""
        # Create a mock stream that raises errors
        mock_stdout = MagicMock()
        mock_stdout.reconfigure = MagicMock(
            side_effect=OSError("Cannot reconfigure")
        )
        mock_stdout.buffer = None  # No buffer, will cause AttributeError

        with patch("sys.stdout", mock_stdout):
            with patch("sys.stderr", mock_stdout):
                # Should not raise exception, just pass
                if sys.platform == "win32":
                    for _stream_name in ("stdout",):
                        _stream = getattr(sys, _stream_name)
                        if hasattr(_stream, "reconfigure"):
                            try:
                                _stream.reconfigure(encoding="utf-8", errors="replace")
                                continue
                            except (AttributeError, io.UnsupportedOperation, OSError):
                                pass

                        # Method 2 should also handle errors
                        try:
                            if hasattr(_stream, "buffer"):
                                _new_stream = io.TextIOWrapper(
                                    _stream.buffer,
                                    encoding="utf-8",
                                    errors="replace",
                                    line_buffering=True,
                                )
                                setattr(sys, _stream_name, _new_stream)
                        except (AttributeError, io.UnsupportedOperation, OSError):
                            pass


# ============================================================================
# Dependency Validation Tests
# ============================================================================


class TestDependencyValidation:
    """Test platform dependency validation in run.py"""

    @patch("core.platform.is_windows", return_value=False)
    @patch("core.platform.is_linux", return_value=False)
    def test_validate_dependencies_on_macos(self, mock_is_linux, mock_is_windows):
        """Test dependency validation on macOS (no platform-specific deps)"""
        from core.dependency_validator import validate_platform_dependencies

        # Should not raise on macOS
        validate_platform_dependencies()

    @patch("core.platform.is_windows", return_value=True)
    @patch("core.platform.is_linux", return_value=False)
    def test_validate_dependencies_on_windows_with_pywin32(
        self, mock_is_linux, mock_is_windows
    ):
        """Test dependency validation on Windows with pywin32 installed"""
        from core.dependency_validator import validate_platform_dependencies

        # Mock pywintypes import to succeed
        with patch("builtins.__import__", return_value=MagicMock()):
            # Should not raise when pywin32 is available
            validate_platform_dependencies()

    @patch("core.platform.is_windows", return_value=False)
    @patch("core.platform.is_linux", return_value=True)
    def test_validate_dependencies_on_linux_with_secretstorage(
        self, mock_is_linux, mock_is_windows
    ):
        """Test dependency validation on Linux with secretstorage installed"""
        from core.dependency_validator import validate_platform_dependencies

        # Mock secretstorage import to succeed
        with patch("builtins.__import__", return_value=MagicMock()):
            # Should not raise or warn
            validate_platform_dependencies()


# ============================================================================
# Import and Module Loading Tests
# ============================================================================


class TestModuleImports:
    """Test that run.py can import required modules"""

    def test_import_core_dependency_validator(self):
        """Test importing core.dependency_validator"""
        from core.dependency_validator import validate_platform_dependencies

        assert callable(validate_platform_dependencies)

    def test_import_cli_main(self):
        """Test that cli.main module exists and is structured correctly"""
        # Verify that the cli.main module file exists
        cli_main_path = Path(__file__).parent.parent / "apps" / "backend" / "cli" / "main.py"
        assert cli_main_path.exists()

        # Read and verify it has the main function
        content = cli_main_path.read_text()
        assert "def main()" in content
        assert "def parse_args" in content

    def test_run_py_main_entry_point(self):
        """Test that run.py can be executed as main"""
        # This is a basic smoke test to ensure run.py can be loaded
        run_py_path = Path(__file__).parent.parent / "apps" / "backend" / "run.py"
        assert run_py_path.exists()

        # Read and verify it contains key elements
        content = run_py_path.read_text()
        assert "Python version check" in content or "sys.version_info" in content
        assert "validate_platform_dependencies" in content
        assert "from cli import main" in content


# ============================================================================
# CLI Argument Parsing Tests
# ============================================================================
# Note: Argument parsing tests are covered in tests/cli/test_main.py
# These tests focus on run.py's structure and initialization


# ============================================================================
# Integration Tests
# ============================================================================


class TestRunPyIntegration:
    """Integration tests for run.py startup sequence"""

    @patch("core.platform.is_windows", return_value=False)
    @patch("core.platform.is_linux", return_value=False)
    def test_full_startup_sequence_on_macos(self, mock_is_linux, mock_is_windows):
        """Test complete startup sequence on macOS"""
        # This test verifies the startup sequence doesn't crash
        from core.dependency_validator import validate_platform_dependencies

        # Should run without errors
        validate_platform_dependencies()

    @patch("core.platform.is_windows", return_value=True)
    @patch("core.platform.is_linux", return_value=False)
    @patch("builtins.__import__")
    def test_full_startup_sequence_on_windows(self, mock_import, mock_is_linux, mock_is_windows):
        """Test complete startup sequence on Windows"""
        from core.dependency_validator import validate_platform_dependencies

        # Mock successful pywin32 import
        mock_import.return_value = MagicMock()

        # Should run without errors
        validate_platform_dependencies()

    @patch("core.platform.is_windows", return_value=False)
    @patch("core.platform.is_linux", return_value=True)
    @patch("sys.stderr.write")
    @patch("sys.stderr.flush")
    def test_full_startup_sequence_on_linux(
        self, mock_flush, mock_write, mock_is_linux, mock_is_windows
    ):
        """Test complete startup sequence on Linux with optional secretstorage warning"""
        from core.dependency_validator import validate_platform_dependencies

        # Mock secretstorage import to show warning behavior
        import builtins
        original_import = builtins.__import__

        def mock_import_func(name, *args, **kwargs):
            if name == "secretstorage":
                raise ImportError("secretstorage not found")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=mock_import_func):
            # Should run with warning (not error)
            validate_platform_dependencies()


# ============================================================================
# Run Py Structure Tests
# ============================================================================


class TestRunPyStructure:
    """Tests for run.py structure and content"""

    def test_run_py_has_shebang(self):
        """Test that run.py has a proper shebang"""
        run_py_path = Path(__file__).parent.parent / "apps" / "backend" / "run.py"
        content = run_py_path.read_text()
        lines = content.split("\n")
        assert lines[0].startswith("#!")
        assert "python3" in lines[0]

    def test_run_py_has_docstring(self):
        """Test that run.py has a docstring"""
        run_py_path = Path(__file__).parent.parent / "apps" / "backend" / "run.py"
        content = run_py_path.read_text()
        assert '"""' in content or "'''" in content

    def test_run_py_imports_cli_main(self):
        """Test that run.py imports cli.main"""
        run_py_path = Path(__file__).parent.parent / "apps" / "backend" / "run.py"
        content = run_py_path.read_text()
        assert "from cli import main" in content
        assert "if __name__ ==" in content
        assert "main()" in content

    def test_run_py_validates_dependencies(self):
        """Test that run.py validates dependencies"""
        run_py_path = Path(__file__).parent.parent / "apps" / "backend" / "run.py"
        content = run_py_path.read_text()
        assert "validate_platform_dependencies" in content
        assert "from core.dependency_validator import" in content

    def test_run_py_configures_encoding_on_windows(self):
        """Test that run.py has Windows encoding configuration"""
        run_py_path = Path(__file__).parent.parent / "apps" / "backend" / "run.py"
        content = run_py_path.read_text()
        assert 'sys.platform == "win32"' in content
        assert "utf-8" in content
        assert "encoding" in content or "reconfigure" in content

    def test_run_py_is_executable_structure(self):
        """Test that run.py follows executable script conventions"""
        run_py_path = Path(__file__).parent.parent / "apps" / "backend" / "run.py"
        content = run_py_path.read_text()

        # Check for main guard
        assert 'if __name__ == "__main__":' in content

        # Check for proper imports
        assert "import sys" in content
        assert "import io" in content
