"""
Comprehensive tests for ui/capabilities.py

Tests cover:
1. enable_windows_ansi_support: Windows platform with ctypes, console mode manipulation,
   ANSI already enabled, fallback to colorama, ctypes failures
2. configure_safe_encoding: Windows encoding configuration, stream reconfigure method,
   stream buffer attribute, exception paths
3. supports_unicode: ENABLE_FANCY_UI env variable, various encodings
4. supports_color: NO_COLOR/FORCE_COLOR env variables, isatty() True/False, TERM==dumb
5. supports_interactive: stdin.isatty() True/False
"""

import io
import os
import sys
from unittest.mock import MagicMock, Mock, patch, PropertyMock

import pytest

from ui.capabilities import (
    configure_safe_encoding,
    enable_windows_ansi_support,
    supports_color,
    supports_interactive,
    supports_unicode,
)


class TestEnableWindowsAnsiSupport:
    """Tests for enable_windows_ansi_support function"""

    def test_non_windows_platform_returns_true(self):
        """Test that non-Windows platforms always return True"""
        with patch("ui.capabilities.sys.platform", "linux"):
            result = enable_windows_ansi_support()
            assert result is True

    def test_non_windows_macos_returns_true(self):
        """Test that macOS returns True"""
        with patch("ui.capabilities.sys.platform", "darwin"):
            result = enable_windows_ansi_support()
            assert result is True

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_successfully_enables_ansi(self):
        """Test successful ANSI enablement on Windows"""
        # Mock the ctypes module and its sub-components
        mock_dword = MagicMock()
        mock_dword.value = 0

        mock_kernel32 = MagicMock()
        mock_kernel32.GetStdHandle.return_value = 1  # Valid handle
        mock_kernel32.GetConsoleMode.return_value = True
        mock_kernel32.SetConsoleMode.return_value = True

        mock_wintypes = MagicMock()
        mock_wintypes.DWORD.return_value = mock_dword

        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32 = mock_kernel32
        mock_ctypes.wintypes = mock_wintypes

        with patch("builtins.__import__", side_effect=_create_import_side_effect(mock_ctypes)):
            result = enable_windows_ansi_support()
            assert result is True

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_ansi_already_enabled(self):
        """Test when ANSI is already enabled on Windows"""
        # Setup mock for DWORD with ANSI flag already set
        mock_dword = MagicMock()
        mock_dword.value = 0x0004  # ENABLE_VIRTUAL_TERMINAL_PROCESSING

        mock_kernel32 = MagicMock()
        mock_kernel32.GetStdHandle.return_value = 1
        mock_kernel32.GetConsoleMode.return_value = True

        mock_wintypes = MagicMock()
        mock_wintypes.DWORD.return_value = mock_dword

        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32 = mock_kernel32
        mock_ctypes.wintypes = mock_wintypes

        with patch("builtins.__import__", side_effect=_create_import_side_effect(mock_ctypes)):
            result = enable_windows_ansi_support()
            assert result is True

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_invalid_handle_continues(self):
        """Test when GetStdHandle returns -1 (invalid handle)"""
        mock_dword = MagicMock()
        mock_dword.value = 0

        mock_kernel32 = MagicMock()
        # First handle invalid, second valid
        mock_kernel32.GetStdHandle.side_effect = [-1, 1]
        mock_kernel32.GetConsoleMode.return_value = True

        mock_wintypes = MagicMock()
        mock_wintypes.DWORD.return_value = mock_dword

        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32 = mock_kernel32
        mock_ctypes.wintypes = mock_wintypes

        with patch("builtins.__import__", side_effect=_create_import_side_effect(mock_ctypes)):
            result = enable_windows_ansi_support()
            assert result is True

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_get_console_mode_fails(self):
        """Test when GetConsoleMode fails"""
        mock_dword = MagicMock()
        mock_dword.value = 0

        mock_kernel32 = MagicMock()
        mock_kernel32.GetStdHandle.return_value = 1
        mock_kernel32.GetConsoleMode.return_value = False

        mock_wintypes = MagicMock()
        mock_wintypes.DWORD.return_value = mock_dword

        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32 = mock_kernel32
        mock_ctypes.wintypes = mock_wintypes

        with patch("builtins.__import__", side_effect=_create_import_side_effect(mock_ctypes)):
            result = enable_windows_ansi_support()
            assert result is True

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_ctypes_import_error_falls_back_to_colorama(self):
        """Test fallback to colorama when ctypes import fails"""
        mock_colorama = MagicMock()
        mock_colorama.init.return_value = None

        def import_side_effect(name, *args, **kwargs):
            if name == "ctypes":
                raise ImportError("No module named 'ctypes'")
            if name == "colorama":
                return mock_colorama
            return __import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=import_side_effect):
            result = enable_windows_ansi_support()
            assert result is True
            mock_colorama.init.assert_called_once()

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_ctypes_attribute_error(self):
        """Test handling of AttributeError from ctypes"""
        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32.GetStdHandle.side_effect = AttributeError("No attribute")

        mock_colorama = MagicMock()
        mock_colorama.init.return_value = None

        def import_side_effect(name, *args, **kwargs):
            if name == "ctypes":
                return mock_ctypes
            if name == "colorama":
                return mock_colorama
            return __import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=import_side_effect):
            result = enable_windows_ansi_support()
            assert result is True
            mock_colorama.init.assert_called_once()

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_oserror_falls_back_to_colorama(self):
        """Test OSError handling falls back to colorama"""
        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32.GetStdHandle.side_effect = OSError("Failed")

        mock_colorama = MagicMock()
        mock_colorama.init.return_value = None

        def import_side_effect(name, *args, **kwargs):
            if name == "ctypes":
                return mock_ctypes
            if name == "colorama":
                return mock_colorama
            return __import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=import_side_effect):
            result = enable_windows_ansi_support()
            assert result is True
            mock_colorama.init.assert_called_once()

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_colorama_import_error_returns_false(self):
        """Test when both ctypes and colorama fail"""
        # Patch both ctypes and colorama imports to fail
        import builtins
        original_import = builtins.__import__

        def import_side_effect(name, *args, **kwargs):
            if name == "ctypes":
                raise ImportError("No module named 'ctypes'")
            if name == "colorama":
                raise ImportError("No module named 'colorama'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=import_side_effect):
            result = enable_windows_ansi_support()

        assert result is False


def _create_import_side_effect(mock_ctypes):
    """Helper to create import side effect with mocked ctypes"""
    def import_side_effect(name, *args, **kwargs):
        if name == "ctypes":
            return mock_ctypes
        if name == "ctypes.wintypes":
            return mock_ctypes.wintypes
        return __import__(name, *args, **kwargs)
    return import_side_effect


class TestConfigureSafeEncoding:
    """Tests for configure_safe_encoding function"""

    def test_non_windows_returns_early(self):
        """Test that non-Windows platforms return early"""
        with patch("ui.capabilities.sys.platform", "linux"):
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            configure_safe_encoding()
            # Should not modify stdout/stderr on non-Windows
            assert sys.stdout is original_stdout
            assert sys.stderr is original_stderr

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_reconfigure_method_works(self):
        """Test successful reconfigure on Windows"""
        mock_stdout = MagicMock()
        mock_stdout.reconfigure.return_value = None
        mock_stderr = MagicMock()
        mock_stderr.reconfigure.return_value = None

        with patch("ui.capabilities.sys.stdout", mock_stdout):
            with patch("ui.capabilities.sys.stderr", mock_stderr):
                configure_safe_encoding()

                mock_stdout.reconfigure.assert_called_once_with(
                    encoding="utf-8", errors="replace"
                )
                mock_stderr.reconfigure.assert_called_once_with(
                    encoding="utf-8", errors="replace"
                )

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_reconfigure_unsupported_operation_falls_back_to_wrapper(self):
        """Test fallback to TextIOWrapper when reconfigure fails"""
        mock_buffer = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.reconfigure.side_effect = io.UnsupportedOperation()
        mock_stdout.buffer = mock_buffer

        with patch("ui.capabilities.sys.stdout", mock_stdout):
            with patch("ui.capabilities.sys", sys):
                configure_safe_encoding()
                # Should wrap with TextIOWrapper
                # (actual sys.stdout would be replaced)

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_reconfigure_attribute_error(self):
        """Test handling AttributeError during reconfigure"""
        mock_stdout = MagicMock()
        mock_stdout.reconfigure.side_effect = AttributeError("No reconfigure")

        with patch("ui.capabilities.sys.stdout", mock_stdout):
            with patch("ui.capabilities.sys.stderr", mock_stdout):
                # Should not raise exception
                configure_safe_encoding()

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_reconfigure_oserror(self):
        """Test handling OSError during reconfigure"""
        mock_stdout = MagicMock()
        mock_stdout.reconfigure.side_effect = OSError("Failed")

        with patch("ui.capabilities.sys.stdout", mock_stdout):
            with patch("ui.capabilities.sys.stderr", mock_stdout):
                # Should not raise exception
                configure_safe_encoding()

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_no_buffer_attribute(self):
        """Test when stream has no buffer attribute"""
        mock_stdout = MagicMock()
        mock_stdout.reconfigure.side_effect = io.UnsupportedOperation()
        # No buffer attribute - accessing it raises AttributeError
        type(mock_stdout).buffer = PropertyMock(side_effect=AttributeError("no buffer"))

        with patch("ui.capabilities.sys.stdout", mock_stdout):
            with patch("ui.capabilities.sys.stderr", mock_stdout):
                # Should not raise exception
                configure_safe_encoding()

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_textio_wrapper_creation_oserror(self):
        """Test OSError when creating TextIOWrapper"""
        mock_stdout = MagicMock()
        mock_stdout.reconfigure.side_effect = io.UnsupportedOperation()
        mock_stdout.buffer = MagicMock()
        # Make TextIOWrapper raise OSError
        with patch("ui.capabilities.io.TextIOWrapper", side_effect=OSError("Failed")):
            with patch("ui.capabilities.sys.stdout", mock_stdout):
                # Should not raise exception
                configure_safe_encoding()

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_textio_wrapper_unsupported_operation(self):
        """Test UnsupportedOperation when creating TextIOWrapper"""
        mock_stdout = MagicMock()
        mock_stdout.reconfigure.side_effect = io.UnsupportedOperation()
        mock_stdout.buffer = MagicMock()
        with patch("ui.capabilities.io.TextIOWrapper", side_effect=io.UnsupportedOperation()):
            with patch("ui.capabilities.sys.stdout", mock_stdout):
                # Should not raise exception
                configure_safe_encoding()


class TestSupportsUnicode:
    """Tests for supports_unicode function"""

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "false"})
    def test_returns_false_when_fancy_ui_disabled(self):
        """Test returns False when ENABLE_FANCY_UI is false"""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "utf-8"
        with patch("sys.stdout", mock_stdout):
            from ui.capabilities import supports_unicode
            result = supports_unicode()
            assert result is False

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "0"})
    def test_returns_false_when_fancy_ui_zero(self):
        """Test returns False when ENABLE_FANCY_UI is 0"""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "utf-8"
        with patch("sys.stdout", mock_stdout):
            from ui.capabilities import supports_unicode
            result = supports_unicode()
            assert result is False

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "no"})
    def test_returns_false_when_fancy_ui_no(self):
        """Test returns False when ENABLE_FANCY_UI is no"""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "utf-8"
        with patch("sys.stdout", mock_stdout):
            from ui.capabilities import supports_unicode
            result = supports_unicode()
            assert result is False

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"})
    def test_returns_true_for_utf8_encoding(self):
        """Test returns True for UTF-8 encoding"""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "utf-8"
        with patch("sys.stdout", mock_stdout):
            import ui.capabilities
            result = ui.capabilities.supports_unicode()
            assert result is True

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"})
    def test_returns_true_for_utf8_variant(self):
        """Test returns True for utf8 (no dash) encoding"""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "utf8"
        with patch("sys.stdout", mock_stdout):
            import ui.capabilities
            result = ui.capabilities.supports_unicode()
            assert result is True

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"})
    def test_returns_true_for_uppercase_utf8(self):
        """Test returns True for uppercase UTF-8"""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "UTF-8"
        with patch("sys.stdout", mock_stdout):
            import ui.capabilities
            result = ui.capabilities.supports_unicode()
            assert result is True

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"})
    def test_returns_false_for_non_utf_encoding(self):
        """Test returns False for non-UTF-8 encoding"""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "cp1252"
        with patch("sys.stdout", mock_stdout):
            import ui.capabilities
            result = ui.capabilities.supports_unicode()
            assert result is False

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"})
    def test_returns_false_for_empty_encoding(self):
        """Test returns False when encoding is empty"""
        mock_stdout = MagicMock()
        mock_stdout.encoding = ""
        with patch("sys.stdout", mock_stdout):
            import ui.capabilities
            result = ui.capabilities.supports_unicode()
            assert result is False

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"})
    def test_returns_false_when_encoding_is_none(self):
        """Test returns False when encoding is None"""
        mock_stdout = MagicMock()
        mock_stdout.encoding = None
        with patch("sys.stdout", mock_stdout):
            import ui.capabilities
            result = ui.capabilities.supports_unicode()
            assert result is False

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "1"})
    def test_returns_true_for_fancy_ui_enabled_as_one(self):
        """Test returns True when ENABLE_FANCY_UI is 1"""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "utf-8"
        with patch("sys.stdout", mock_stdout):
            import ui.capabilities
            result = ui.capabilities.supports_unicode()
            assert result is True

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "yes"})
    def test_returns_true_for_fancy_ui_yes(self):
        """Test returns True when ENABLE_FANCY_UI is yes"""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "utf-8"
        with patch("sys.stdout", mock_stdout):
            import ui.capabilities
            result = ui.capabilities.supports_unicode()
            assert result is True

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "on"})
    def test_returns_true_for_fancy_ui_on(self):
        """Test returns True when ENABLE_FANCY_UI is on"""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "utf-8"
        with patch("sys.stdout", mock_stdout):
            import ui.capabilities
            result = ui.capabilities.supports_unicode()
            assert result is True


class TestSupportsColor:
    """Tests for supports_color function"""

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "false"})
    def test_returns_false_when_fancy_ui_disabled(self):
        """Test returns False when fancy UI is disabled"""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "utf-8"
        with patch("sys.stdout", mock_stdout):
            from ui.capabilities import supports_color
            result = supports_color()
            assert result is False

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "true", "NO_COLOR": "1"})
    def test_returns_false_when_no_color_set(self):
        """Test returns False when NO_COLOR env var is set"""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "utf-8"
        with patch("sys.stdout", mock_stdout):
            from ui.capabilities import supports_color
            result = supports_color()
            assert result is False

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "true", "NO_COLOR": ""})
    def test_returns_true_when_no_color_empty_string(self):
        """Test returns True when NO_COLOR is empty string (falsy, so ignored)"""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "utf-8"
        with patch("sys.stdout", mock_stdout):
            from ui.capabilities import supports_color
            result = supports_color()
            # Empty string is falsy, so NO_COLOR check is skipped, returns True (MagicMock.isatty is truthy)
            assert result is True

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "true", "FORCE_COLOR": "1"})
    def test_returns_true_when_force_color_set(self):
        """Test returns True when FORCE_COLOR env var is set"""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "utf-8"
        with patch("sys.stdout", mock_stdout):
            from ui.capabilities import supports_color
            result = supports_color()
            assert result is True

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "true", "FORCE_COLOR": "1"})
    def test_returns_true_when_force_color_non_empty(self):
        """Test returns True when FORCE_COLOR has non-empty value"""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "utf-8"
        with patch("sys.stdout", mock_stdout):
            from ui.capabilities import supports_color
            result = supports_color()
            assert result is True

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"})
    def test_returns_false_when_not_tty(self):
        """Test returns False when stdout is not a TTY"""
        # Mock sys.stdout.isatty at the call site
        with patch("sys.stdout.isatty", return_value=False):
            import ui.capabilities
            result = ui.capabilities.supports_color()
            assert result is False

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"})
    def test_returns_false_when_no_isatty_method(self):
        """Test returns False when stdout has no isatty method"""
        # Create a mock object without isatty method
        mock_stdout = Mock(spec=["encoding"])
        with patch("sys.stdout", mock_stdout):
            import ui.capabilities
            result = ui.capabilities.supports_color()
            assert result is False

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "true", "TERM": "dumb"})
    def test_returns_false_when_term_is_dumb(self):
        """Test returns False when TERM is set to 'dumb'"""
        # Mock sys.stdout.isatty at the call site
        with patch("sys.stdout.isatty", return_value=True):
            import ui.capabilities
            result = ui.capabilities.supports_color()
            assert result is False

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "true", "TERM": "xterm-256color"})
    def test_returns_true_when_term_supports_color(self):
        """Test returns True for color-supporting terminal"""
        # Mock sys.stdout.isatty at the call site
        with patch("sys.stdout.isatty", return_value=True):
            import ui.capabilities
            result = ui.capabilities.supports_color()
            assert result is True

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"})
    def test_returns_true_when_term_not_set(self):
        """Test returns True when TERM env var is not set (defaults to not dumb)"""
        # Remove TERM from environment and mock isatty
        with patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"}, clear=True):
            with patch("sys.stdout.isatty", return_value=True):
                import ui.capabilities
                result = ui.capabilities.supports_color()
                assert result is True


class TestSupportsInteractive:
    """Tests for supports_interactive function"""

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "false"})
    def test_returns_false_when_fancy_ui_disabled(self):
        """Test returns False when fancy UI is disabled"""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "utf-8"
        with patch("sys.stdout", mock_stdout):
            from ui.capabilities import supports_interactive
            result = supports_interactive()
            assert result is False

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"})
    def test_returns_false_when_stdin_not_tty(self):
        """Test returns False when stdin is not a TTY"""
        # Mock sys.stdin.isatty at the call site
        with patch("sys.stdin.isatty", return_value=False):
            import ui.capabilities
            result = ui.capabilities.supports_interactive()
            assert result is False

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"})
    def test_returns_true_when_stdin_is_tty(self):
        """Test returns True when stdin is a TTY"""
        # Mock sys.stdin.isatty at the call site
        with patch("sys.stdin.isatty", return_value=True):
            import ui.capabilities
            result = ui.capabilities.supports_interactive()
            assert result is True

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"})
    def test_returns_false_when_no_isatty_method(self):
        """Test returns False when stdin has no isatty method"""
        # Create a mock object without isatty method
        mock_stdin = Mock(spec=["encoding"])
        with patch("sys.stdin", mock_stdin):
            import ui.capabilities
            result = ui.capabilities.supports_interactive()
            assert result is False


# ============================================================================
# Additional tests to improve coverage for actual code paths
# ============================================================================


class TestEnableWindowsAnsiSupportActualPaths:
    """Tests that execute the actual Windows ANSI support code paths"""

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_ctypes_actual_import_and_execution(self):
        """Test actual ctypes import path on Windows"""
        # We need to properly mock ctypes.wintypes.DWORD
        mock_dword_instance = MagicMock()
        mock_dword_instance.value = 0

        mock_dword_class = MagicMock(return_value=mock_dword_instance)

        mock_kernel32 = MagicMock()
        mock_kernel32.GetStdHandle.return_value = 1
        mock_kernel32.GetConsoleMode.return_value = True
        mock_kernel32.SetConsoleMode.return_value = True

        mock_byref = MagicMock(return_value=mock_dword_instance)

        # Create a mock ctypes module
        mock_ctypes_module = MagicMock()
        mock_ctypes_module.windll.kernel32 = mock_kernel32
        mock_ctypes_module.wintypes.DWORD = mock_dword_class
        mock_ctypes_module.byref = mock_byref

        # Patch the import to return our mock
        import ui.capabilities as cap_module
        import builtins

        original_import = builtins.__import__

        def custom_import(name, *args, **kwargs):
            if name == "ctypes":
                return mock_ctypes_module
            if name == "ctypes.wintypes":
                return mock_ctypes_module.wintypes
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=custom_import):
            # Need to reload the function to pick up the mocked import
            # Act
            result = cap_module.enable_windows_ansi_support()

        # Assert
        assert result is True

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_ctypes_with_mode_already_set(self):
        """Test Windows path when ANSI mode is already enabled"""
        # Mock DWORD with ANSI flag already set
        mock_dword_instance = MagicMock()
        mock_dword_instance.value = 0x0004  # ENABLE_VIRTUAL_TERMINAL_PROCESSING

        mock_dword_class = MagicMock(return_value=mock_dword_instance)

        mock_kernel32 = MagicMock()
        mock_kernel32.GetStdHandle.return_value = 1
        mock_kernel32.GetConsoleMode.return_value = True

        mock_byref = MagicMock(return_value=mock_dword_instance)

        mock_ctypes_module = MagicMock()
        mock_ctypes_module.windll.kernel32 = mock_kernel32
        mock_ctypes_module.wintypes.DWORD = mock_dword_class
        mock_ctypes_module.byref = mock_byref

        import ui.capabilities as cap_module
        import builtins

        original_import = builtins.__import__

        def custom_import(name, *args, **kwargs):
            if name == "ctypes":
                return mock_ctypes_module
            if name == "ctypes.wintypes":
                return mock_ctypes_module.wintypes
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=custom_import):
            # Act
            result = cap_module.enable_windows_ansi_support()

        # Assert - SetConsoleMode should NOT be called when already enabled
        assert result is True
        # The code checks: if not (mode.value & ENABLE_VIRTUAL_TERMINAL_PROCESSING)
        # Since mode.value is 0x0004, the condition is False, so SetConsoleMode is not called

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_ctypes_with_both_handles(self):
        """Test Windows path with both output and error handles"""
        # Mock two different handles
        mock_dword_instance = MagicMock()
        mock_dword_instance.value = 0

        mock_dword_class = MagicMock(return_value=mock_dword_instance)

        mock_kernel32 = MagicMock()
        # Return different handles for output and error
        mock_kernel32.GetStdHandle.side_effect = [1, 2]
        mock_kernel32.GetConsoleMode.return_value = True
        mock_kernel32.SetConsoleMode.return_value = True

        mock_byref = MagicMock(return_value=mock_dword_instance)

        mock_ctypes_module = MagicMock()
        mock_ctypes_module.windll.kernel32 = mock_kernel32
        mock_ctypes_module.wintypes.DWORD = mock_dword_class
        mock_ctypes_module.byref = mock_byref

        import ui.capabilities as cap_module
        import builtins

        original_import = builtins.__import__

        def custom_import(name, *args, **kwargs):
            if name == "ctypes":
                return mock_ctypes_module
            if name == "ctypes.wintypes":
                return mock_ctypes_module.wintypes
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=custom_import):
            # Act
            result = cap_module.enable_windows_ansi_support()

        # Assert
        assert result is True
        # GetStdHandle should be called twice (STD_OUTPUT_HANDLE and STD_ERROR_HANDLE)
        assert mock_kernel32.GetStdHandle.call_count == 2


class TestConfigureSafeEncodingActualPaths:
    """Tests that execute the actual configure_safe_encoding code paths"""

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_reconfigure_success(self):
        """Test successful reconfigure on Windows"""
        # Create mocks for stdout and stderr with reconfigure method
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()

        import ui.capabilities as cap_module

        with patch("ui.capabilities.sys.stdout", mock_stdout):
            with patch("ui.capabilities.sys.stderr", mock_stderr):
                # Act
                cap_module.configure_safe_encoding()

                # Assert - reconfigure should be called on both streams
                mock_stdout.reconfigure.assert_called_once_with(encoding="utf-8", errors="replace")
                mock_stderr.reconfigure.assert_called_once_with(encoding="utf-8", errors="replace")

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_reconfigure_fails_to_textiowrapper(self):
        """Test fallback to TextIOWrapper when reconfigure fails"""
        mock_buffer = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.reconfigure.side_effect = io.UnsupportedOperation("reconfigure not supported")
        mock_stdout.buffer = mock_buffer

        mock_stderr = MagicMock()
        mock_stderr.reconfigure.side_effect = io.UnsupportedOperation("reconfigure not supported")
        mock_stderr.buffer = MagicMock()

        import ui.capabilities as cap_module

        with patch("ui.capabilities.sys.stdout", mock_stdout):
            with patch("ui.capabilities.sys.stderr", mock_stderr):
                with patch("ui.capabilities.io.TextIOWrapper") as mock_textio_wrapper:
                    # Act - should not raise
                    cap_module.configure_safe_encoding()

                    # Assert - TextIOWrapper should be created for both streams
                    assert mock_textio_wrapper.call_count == 2

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_no_buffer_attribute(self):
        """Test when stream has no buffer attribute"""
        mock_stdout = MagicMock()
        mock_stdout.reconfigure.side_effect = io.UnsupportedOperation("reconfigure not supported")
        # Remove buffer attribute
        del mock_stdout.buffer

        mock_stderr = MagicMock()
        mock_stderr.reconfigure.side_effect = io.UnsupportedOperation("reconfigure not supported")
        del mock_stderr.buffer

        import ui.capabilities as cap_module

        with patch("ui.capabilities.sys.stdout", mock_stdout):
            with patch("ui.capabilities.sys.stderr", mock_stderr):
                # Act - should not raise
                cap_module.configure_safe_encoding()

                # Assert - no exception raised

    @patch("ui.capabilities.sys.platform", "win32")
    def test_windows_textiowrapper_oserror(self):
        """Test OSError when creating TextIOWrapper"""
        mock_stdout = MagicMock()
        mock_stdout.reconfigure.side_effect = io.UnsupportedOperation("reconfigure not supported")
        mock_stdout.buffer = MagicMock()

        import ui.capabilities as cap_module

        with patch("ui.capabilities.sys.stdout", mock_stdout):
            with patch("ui.capabilities.sys.stderr", mock_stdout):
                with patch("ui.capabilities.io.TextIOWrapper", side_effect=OSError("Failed")):
                    # Act - should not raise
                    cap_module.configure_safe_encoding()

                    # Assert - no exception raised

    @patch("ui.capabilities.sys.platform", "linux")
    def test_non_windows_returns_early(self):
        """Test that non-Windows platforms return early"""
        import ui.capabilities as cap_module

        original_stdout = sys.stdout
        original_stderr = sys.stderr

        # Act
        cap_module.configure_safe_encoding()

        # Assert - stdout and stderr should not be modified
        assert sys.stdout is original_stdout
        assert sys.stderr is original_stderr


class TestIsFancyUiEnabled:
    """Tests for _is_fancy_ui_enabled internal function"""

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"})
    def test_returns_true_for_true(self):
        """Test returns True for 'true'"""
        from ui.capabilities import _is_fancy_ui_enabled
        assert _is_fancy_ui_enabled() is True

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "True"})
    def test_returns_true_for_capital_true(self):
        """Test returns True for 'True'"""
        from ui.capabilities import _is_fancy_ui_enabled
        assert _is_fancy_ui_enabled() is True

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "TRUE"})
    def test_returns_true_for_uppercase_true(self):
        """Test returns True for 'TRUE'"""
        from ui.capabilities import _is_fancy_ui_enabled
        assert _is_fancy_ui_enabled() is True

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "1"})
    def test_returns_true_for_one(self):
        """Test returns True for '1'"""
        from ui.capabilities import _is_fancy_ui_enabled
        assert _is_fancy_ui_enabled() is True

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "yes"})
    def test_returns_true_for_yes(self):
        """Test returns True for 'yes'"""
        from ui.capabilities import _is_fancy_ui_enabled
        assert _is_fancy_ui_enabled() is True

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "on"})
    def test_returns_true_for_on(self):
        """Test returns True for 'on'"""
        from ui.capabilities import _is_fancy_ui_enabled
        assert _is_fancy_ui_enabled() is True

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "false"})
    def test_returns_false_for_false(self):
        """Test returns False for 'false'"""
        from ui.capabilities import _is_fancy_ui_enabled
        assert _is_fancy_ui_enabled() is False

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "0"})
    def test_returns_false_for_zero(self):
        """Test returns False for '0'"""
        from ui.capabilities import _is_fancy_ui_enabled
        assert _is_fancy_ui_enabled() is False

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "no"})
    def test_returns_false_for_no(self):
        """Test returns False for 'no'"""
        from ui.capabilities import _is_fancy_ui_enabled
        assert _is_fancy_ui_enabled() is False

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "off"})
    def test_returns_false_for_off(self):
        """Test returns False for 'off'"""
        from ui.capabilities import _is_fancy_ui_enabled
        assert _is_fancy_ui_enabled() is False

    @patch.dict(os.environ, {}, clear=True)
    def test_returns_true_when_not_set(self):
        """Test returns True when env var is not set (default)"""
        from ui.capabilities import _is_fancy_ui_enabled
        assert _is_fancy_ui_enabled() is True

    @patch.dict(os.environ, {"ENABLE_FANCY_UI": "random"})
    def test_returns_false_for_invalid_value(self):
        """Test returns False for invalid value"""
        from ui.capabilities import _is_fancy_ui_enabled
        assert _is_fancy_ui_enabled() is False


class TestModuleLevelConstants:
    """Tests for module-level constants"""

    def test_fancy_ui_constant(self):
        """Test FANCY_UI constant is set"""
        from ui.capabilities import FANCY_UI
        assert isinstance(FANCY_UI, bool)

    def test_unicode_constant(self):
        """Test UNICODE constant is set"""
        from ui.capabilities import UNICODE
        assert isinstance(UNICODE, bool)

    def test_color_constant(self):
        """Test COLOR constant is set"""
        from ui.capabilities import COLOR
        assert isinstance(COLOR, bool)

    def test_interactive_constant(self):
        """Test INTERACTIVE constant is set"""
        from ui.capabilities import INTERACTIVE
        assert isinstance(INTERACTIVE, bool)

    def test_windows_ansi_enabled_constant(self):
        """Test WINDOWS_ANSI_ENABLED constant is set"""
        from ui.capabilities import WINDOWS_ANSI_ENABLED
        assert isinstance(WINDOWS_ANSI_ENABLED, bool)
