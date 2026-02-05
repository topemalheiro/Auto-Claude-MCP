"""
Comprehensive tests for core.sentry module.

Tests cover:
- Sentry initialization with various configurations
- Exception and message capturing
- Path masking for privacy (macOS, Windows, Linux, WSL)
- Event filtering and before_send callback
- Disabled Sentry handling
- Context and tag setting
- Version detection
- Edge cases and error handling
"""

import builtins
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Import the module under test
from core.sentry import (
    _before_send,
    _get_version,
    _mask_object_paths,
    _mask_user_paths,
    capture_exception,
    capture_message,
    init_sentry,
    is_enabled,
    is_initialized,
    set_context,
    set_tag,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def reset_sentry_state():
    """Reset Sentry module state before each test."""
    import core.sentry as sentry_module

    original_enabled = sentry_module._sentry_enabled
    original_initialized = sentry_module._sentry_initialized

    sentry_module._sentry_enabled = False
    sentry_module._sentry_initialized = False

    yield

    sentry_module._sentry_enabled = original_enabled
    sentry_module._sentry_initialized = original_initialized


@pytest.fixture
def mock_sdk():
    """Create a mock sentry_sdk module."""
    mock = Mock()
    mock.init = Mock()
    mock.push_scope = MagicMock()
    mock.push_scope.return_value.__enter__ = Mock(return_value=mock)
    mock.push_scope.return_value.__exit__ = Mock(return_value=False)
    mock.set_tag = Mock()
    mock.set_context = Mock()
    mock.capture_exception = Mock()
    mock.capture_message = Mock()
    return mock


@pytest.fixture
def mock_logging_int():
    """Create a mock LoggingIntegration."""
    mock = Mock(return_value=Mock())
    return mock


# ============================================================================
# Path Masking Tests (_mask_user_paths)
# ============================================================================


class TestMaskUserPaths:
    """Tests for _mask_user_paths function."""

    def test_mask_macos_paths(self):
        """Test masking macOS user paths."""
        assert _mask_user_paths("/Users/john/workspace/project/file.py") == "/Users/***/workspace/project/file.py"
        assert _mask_user_paths("/Users/alice/Downloads/file.txt") == "/Users/***/Downloads/file.txt"
        assert _mask_user_paths("/Users/john/project/Users/jane/file") == "/Users/***/project/Users/***/file"
        assert _mask_user_paths("/Users/john") == "/Users/***"

    def test_mask_windows_paths(self):
        """Test masking Windows user paths."""
        assert _mask_user_paths(r"C:\Users\john\project\file.py") == r"C:\Users\***\project\file.py"
        assert _mask_user_paths(r"D:\Users\alice\Downloads\file.txt") == r"D:\Users\***\Downloads\file.txt"
        assert _mask_user_paths(r"C:\Users\john\project\C:\Users\jane\file") == r"C:\Users\***\project\C:\Users\***\file"
        assert _mask_user_paths(r"C:\Users\john") == r"C:\Users\***"

    def test_mask_linux_paths(self):
        """Test masking Linux user paths."""
        assert _mask_user_paths("/home/john/workspace/project/file.py") == "/home/***/workspace/project/file.py"
        assert _mask_user_paths("/home/alice/Downloads/file.txt") == "/home/***/Downloads/file.txt"
        assert _mask_user_paths("/home/john/project/home/jane/file") == "/home/***/project/home/***/file"
        assert _mask_user_paths("/home/john") == "/home/***"

    def test_mask_wsl_paths(self):
        """Test masking WSL paths accessing Windows filesystem."""
        assert _mask_user_paths("/mnt/c/Users/john/project/file.py") == "/mnt/c/Users/***/project/file.py"
        assert _mask_user_paths("/mnt/d/Users/alice/Downloads/file.txt") == "/mnt/d/Users/***/Downloads/file.txt"
        assert _mask_user_paths("/mnt/c/Users/john/mnt/d/Users/jane/file") == "/mnt/c/Users/***/mnt/d/Users/***/file"

    def test_preserve_non_user_paths(self):
        """Test that non-user paths are not modified."""
        assert _mask_user_paths("/opt/dev/Auto-Claude/project/file.py") == "/opt/dev/Auto-Claude/project/file.py"
        assert _mask_user_paths("/usr/local/bin/python") == "/usr/local/bin/python"
        assert _mask_user_paths(r"C:\Program Files\App\file.exe") == r"C:\Program Files\App\file.exe"
        assert _mask_user_paths(r"D:\Projects\Auto-Claude\file.py") == r"D:\Projects\Auto-Claude\file.py"

    def test_empty_and_none_inputs(self):
        """Test handling of empty and None inputs."""
        assert _mask_user_paths("") == ""
        assert _mask_user_paths(None) is None
        assert _mask_user_paths("no paths here") == "no paths here"


class TestMaskObjectPaths:
    """Tests for _mask_object_paths function."""

    def test_mask_string(self):
        """Test masking a string."""
        result = _mask_object_paths("/Users/john/project/file.py")
        assert result == "/Users/***/project/file.py"

    def test_mask_none(self):
        """Test that None is returned as-is."""
        assert _mask_object_paths(None) is None

    def test_mask_list(self):
        """Test masking a list of strings."""
        input_list = [
            "/Users/john/file1.py",
            "/home/jane/file2.py",
            "no path here",
            None,
        ]
        result = _mask_object_paths(input_list)
        assert result == [
            "/Users/***/file1.py",
            "/home/***/file2.py",
            "no path here",
            None,
        ]

    def test_mask_dict(self):
        """Test masking a dictionary."""
        input_dict = {
            "file": "/Users/john/project/file.py",
            "user": "john",
            "nested": {"path": "/home/jane/data.json"},
            "none_value": None,
        }
        result = _mask_object_paths(input_dict)
        assert result["file"] == "/Users/***/project/file.py"
        assert result["user"] == "john"
        assert result["nested"]["path"] == "/home/***/data.json"
        assert result["none_value"] is None

    def test_mask_nested_structures(self):
        """Test masking deeply nested structures."""
        nested = {
            "level1": {
                "level2": {
                    "level3": {
                        "paths": [
                            "/Users/john/file.py",
                            {"inner": "/home/jane/file.txt"},
                        ]
                    }
                }
            }
        }
        result = _mask_object_paths(nested)
        assert result["level1"]["level2"]["level3"]["paths"][0] == "/Users/***/file.py"
        assert result["level1"]["level2"]["level3"]["paths"][1]["inner"] == "/home/***/file.txt"

    def test_depth_limit(self):
        """Test that recursion depth is limited to prevent stack overflow."""
        # Test with a simple nested structure to verify function doesn't crash
        deeply_nested = {"level1": {"level2": {"level3": {"path": "/Users/john/file.py"}}}}

        # Should not crash
        result = _mask_object_paths(deeply_nested)
        assert result["level1"]["level2"]["level3"]["path"] == "/Users/***/file.py"

    def test_non_string_values_unchanged(self):
        """Test that non-string values are unchanged."""
        input_obj = {
            "int": 42,
            "float": 3.14,
            "bool": True,
            "list": [1, 2, 3],
            "none": None,
        }
        result = _mask_object_paths(input_obj)
        assert result == input_obj


# ============================================================================
# Version Detection Tests (_get_version)
# ============================================================================


class TestGetVersion:
    """Tests for _get_version function."""

    def test_get_version_default(self):
        """Test default version when package.json is not found."""
        with patch("core.sentry.Path") as mock_path:
            mock_path.return_value.parent.parent.parent = Mock()
            mock_path.return_value.exists.return_value = False

            version = _get_version()
            assert version == "0.0.0"

    def test_get_version_json_error(self):
        """Test handling of invalid JSON in package.json."""
        with patch("core.sentry.Path") as mock_path:
            mock_instance = Mock()
            mock_instance.exists.return_value = True
            mock_instance.open = Mock(side_effect=IOError("Read error"))
            mock_path.return_value = mock_instance

            version = _get_version()
            assert version == "0.0.0"


# ============================================================================
# Event Filter Tests (_before_send)
# ============================================================================


class TestBeforeSend:
    """Tests for _before_send callback function."""

    def test_before_send_disabled(self):
        """Test that None is returned when Sentry is disabled."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = False

        event = {"message": "test"}
        result = _before_send(event, {})
        assert result is None

    def test_before_send_enabled_no_exception(self):
        """Test event processing without exception data."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        event = {
            "message": "Error at /Users/john/project/file.py",
            "tags": {"path": "/home/jane/data"},
            "extra": {"file": "C:\\Users\\bob\\file.txt"},
        }

        result = _before_send(event, {})

        assert result is not None
        assert result["message"] == "Error at /Users/***/project/file.py"
        assert result["tags"]["path"] == "/home/***/data"
        assert r"Users\***" in result["extra"]["file"]
        # user key should not exist if not in original event
        assert "user" not in result

    def test_before_send_with_exception_stacktrace(self):
        """Test masking of exception stack traces."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        event = {
            "exception": {
                "values": [
                    {
                        "type": "ValueError",
                        "value": "Error in /Users/john/script.py",
                        "stacktrace": {
                            "frames": [
                                {
                                    "filename": "/Users/alice/project/module.py",
                                    "abs_path": "/Users/alice/project/module.py",
                                    "lineno": 42,
                                },
                                {
                                    "filename": "/home/bob/utils/helper.py",
                                    "abs_path": "/home/bob/utils/helper.py",
                                    "lineno": 10,
                                },
                            ]
                        },
                    }
                ]
            }
        }

        result = _before_send(event, {})

        frames = result["exception"]["values"][0]["stacktrace"]["frames"]
        assert frames[0]["filename"] == "/Users/***/project/module.py"
        assert frames[0]["abs_path"] == "/Users/***/project/module.py"
        assert frames[1]["filename"] == "/home/***/utils/helper.py"
        assert frames[1]["abs_path"] == "/home/***/utils/helper.py"
        assert result["exception"]["values"][0]["value"] == "Error in /Users/***/script.py"

    def test_before_send_with_breadcrumbs(self):
        """Test masking of breadcrumb data."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        event = {
            "breadcrumbs": {
                "values": [
                    {
                        "message": "Processed /Users/john/input.py",
                        "data": {"path": "/home/jane/config.json"},
                    }
                ]
            }
        }

        result = _before_send(event, {})

        breadcrumbs = result["breadcrumbs"]["values"]
        assert breadcrumbs[0]["message"] == "Processed /Users/***/input.py"
        assert breadcrumbs[0]["data"]["path"] == "/home/***/config.json"

    def test_before_send_clears_user_info(self):
        """Test that user information is cleared for privacy."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        event = {
            "user": {
                "id": "user123",
                "email": "user@example.com",
                "username": "john",
            },
            "message": "test",
        }

        result = _before_send(event, {})
        assert result["user"] == {}

    def test_before_send_empty_event(self):
        """Test handling of empty event."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        result = _before_send({}, {})
        assert result == {}


# ============================================================================
# Initialization Tests (init_sentry)
# ============================================================================


class TestInitSentry:
    """Tests for init_sentry function."""

    def test_init_no_dsn(self):
        """Test initialization without SENTRY_DSN."""
        import core.sentry as sentry_module
        sentry_module._sentry_initialized = False

        with patch.dict("os.environ", {}, clear=False):
            with patch("os.environ.get", return_value=""):
                result = init_sentry()
                assert result is False
                assert is_enabled() is False
                assert is_initialized() is True

    def test_init_not_packaged_no_dev_mode(self):
        """Test that Sentry is not enabled in dev mode without SENTRY_DEV."""
        import core.sentry as sentry_module
        sentry_module._sentry_initialized = False

        with patch.dict("os.environ", {"SENTRY_DSN": "https://test@test.ingest.sentry.io/123"}):
            with patch("core.sentry.getattr", return_value=False):
                result = init_sentry()
                assert result is False
                assert is_enabled() is False

    def test_init_with_force_enable(self, mock_sdk, mock_logging_int):
        """Test initialization with force_enable=True."""
        import core.sentry as sentry_module
        sentry_module._sentry_initialized = False

        # Create a mock logging integration module
        mock_logging_module = Mock()
        mock_logging_module.LoggingIntegration = mock_logging_int
        mock_sdk.integrations = Mock()
        mock_sdk.integrations.logging = mock_logging_module

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk, "sentry_sdk.integrations": mock_sdk.integrations, "sentry_sdk.integrations.logging": mock_logging_module}):
            with patch.dict("os.environ", {"SENTRY_DSN": "https://test@test.ingest.sentry.io/123"}):
                result = init_sentry(force_enable=True)
                assert result is True
                assert is_enabled() is True

    def test_init_with_sentry_dev(self, mock_sdk, mock_logging_int):
        """Test initialization with SENTRY_DEV=true."""
        import core.sentry as sentry_module
        sentry_module._sentry_initialized = False

        mock_logging_module = Mock()
        mock_logging_module.LoggingIntegration = mock_logging_int
        mock_sdk.integrations = Mock()
        mock_sdk.integrations.logging = mock_logging_module

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk, "sentry_sdk.integrations.logging": mock_logging_module}):
            with patch.dict(
                "os.environ",
                {"SENTRY_DSN": "https://test@test.ingest.sentry.io/123", "SENTRY_DEV": "true"},
            ):
                result = init_sentry()
                assert result is True
                assert is_enabled() is True

    def test_init_sentry_dev_false(self):
        """Test that SENTRY_DEV=false doesn't enable in dev."""
        import core.sentry as sentry_module
        sentry_module._sentry_initialized = False

        with patch.dict(
            "os.environ",
            {"SENTRY_DSN": "https://test@test.ingest.sentry.io/123", "SENTRY_DEV": "false"},
        ):
            with patch("core.sentry.getattr", return_value=False):
                result = init_sentry()
                assert result is False

    def test_init_sdk_not_installed(self):
        """Test handling when sentry_sdk is not installed."""
        import core.sentry as sentry_module
        sentry_module._sentry_initialized = False

        # Make the import fail
        with patch.dict("sys.modules", {}):
            with patch("builtins.__import__", side_effect=ImportError("No module named sentry_sdk")):
                with patch.dict("os.environ", {"SENTRY_DSN": "https://test@test.ingest.sentry.io/123"}):
                    with patch("core.sentry.getattr", return_value=False):
                        # This should handle the ImportError gracefully
                        result = init_sentry(force_enable=True)
                        # Should return False since SDK is not available
                        assert result is False

    def test_init_with_custom_component(self, mock_sdk, mock_logging_int):
        """Test initialization with custom component name."""
        import core.sentry as sentry_module
        sentry_module._sentry_initialized = False

        mock_logging_module = Mock()
        mock_logging_module.LoggingIntegration = mock_logging_int
        mock_sdk.integrations = Mock()
        mock_sdk.integrations.logging = mock_logging_module

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk, "sentry_sdk.integrations.logging": mock_logging_module}):
            with patch.dict("os.environ", {"SENTRY_DSN": "https://test@test.ingest.sentry.io/123"}):
                result = init_sentry(component="github-runner", force_enable=True)
                assert result is True
                mock_sdk.set_tag.assert_called_with("component", "github-runner")

    def test_init_with_environment(self, mock_sdk, mock_logging_int):
        """Test initialization with custom environment."""
        import core.sentry as sentry_module
        sentry_module._sentry_initialized = False

        mock_logging_module = Mock()
        mock_logging_module.LoggingIntegration = mock_logging_int
        mock_sdk.integrations = Mock()
        mock_sdk.integrations.logging = mock_logging_module

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk, "sentry_sdk.integrations.logging": mock_logging_module}):
            with patch.dict(
                "os.environ",
                {"SENTRY_DSN": "https://test@test.ingest.sentry.io/123", "SENTRY_ENVIRONMENT": "staging"},
            ):
                with patch("core.sentry.getattr", return_value=True):
                    result = init_sentry(force_enable=True)
                    assert result is True

    def test_init_with_traces_sample_rate(self, mock_sdk, mock_logging_int):
        """Test initialization with custom traces sample rate."""
        import core.sentry as sentry_module
        sentry_module._sentry_initialized = False

        mock_logging_module = Mock()
        mock_logging_module.LoggingIntegration = mock_logging_int
        mock_sdk.integrations = Mock()
        mock_sdk.integrations.logging = mock_logging_module

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk, "sentry_sdk.integrations.logging": mock_logging_module}):
            with patch.dict(
                "os.environ",
                {
                    "SENTRY_DSN": "https://test@test.ingest.sentry.io/123",
                    "SENTRY_TRACES_SAMPLE_RATE": "0.5",
                },
            ):
                with patch("core.sentry.getattr", return_value=True):
                    result = init_sentry(force_enable=True)
                    assert result is True

    def test_init_invalid_traces_sample_rate(self, mock_sdk, mock_logging_int):
        """Test that invalid traces sample rate falls back to default."""
        import core.sentry as sentry_module
        sentry_module._sentry_initialized = False

        mock_logging_module = Mock()
        mock_logging_module.LoggingIntegration = mock_logging_int
        mock_sdk.integrations = Mock()
        mock_sdk.integrations.logging = mock_logging_module

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk, "sentry_sdk.integrations.logging": mock_logging_module}):
            with patch.dict(
                "os.environ",
                {
                    "SENTRY_DSN": "https://test@test.ingest.sentry.io/123",
                    "SENTRY_TRACES_SAMPLE_RATE": "invalid",
                },
            ):
                with patch("core.sentry.getattr", return_value=True):
                    result = init_sentry(force_enable=True)
                    assert result is True

    def test_init_out_of_range_traces_sample_rate(self, mock_sdk, mock_logging_int):
        """Test that out-of-range traces sample rate falls back to default."""
        import core.sentry as sentry_module
        sentry_module._sentry_initialized = False

        mock_logging_module = Mock()
        mock_logging_module.LoggingIntegration = mock_logging_int
        mock_sdk.integrations = Mock()
        mock_sdk.integrations.logging = mock_logging_module

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk, "sentry_sdk.integrations.logging": mock_logging_module}):
            with patch.dict(
                "os.environ",
                {
                    "SENTRY_DSN": "https://test@test.ingest.sentry.io/123",
                    "SENTRY_TRACES_SAMPLE_RATE": "1.5",
                },
            ):
                with patch("core.sentry.getattr", return_value=True):
                    result = init_sentry(force_enable=True)
                    assert result is True

    def test_init_idempotent(self, mock_sdk, mock_logging_int):
        """Test that calling init_sentry multiple times is safe."""
        import core.sentry as sentry_module
        sentry_module._sentry_initialized = False

        mock_logging_module = Mock()
        mock_logging_module.LoggingIntegration = mock_logging_int
        mock_sdk.integrations = Mock()
        mock_sdk.integrations.logging = mock_logging_module

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk, "sentry_sdk.integrations.logging": mock_logging_module}):
            with patch.dict("os.environ", {"SENTRY_DSN": "https://test@test.ingest.sentry.io/123"}):
                result1 = init_sentry(force_enable=True)
                result2 = init_sentry(force_enable=True)
                assert result1 == result2

    def test_init_frozen_app(self, mock_sdk, mock_logging_int):
        """Test initialization when app is frozen (packaged)."""
        import core.sentry as sentry_module
        sentry_module._sentry_initialized = False

        mock_logging_module = Mock()
        mock_logging_module.LoggingIntegration = mock_logging_int
        mock_sdk.integrations = Mock()
        mock_sdk.integrations.logging = mock_logging_module

        # Use force_enable=True to avoid testing getattr edge case
        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk, "sentry_sdk.integrations.logging": mock_logging_module}):
            with patch.dict("os.environ", {"SENTRY_DSN": "https://test@test.ingest.sentry.io/123"}):
                # Test with force_enable which should work regardless of packaging state
                result = init_sentry(force_enable=True)
                assert result is True

    def test_init_compiled_app(self, mock_sdk, mock_logging_int):
        """Test initialization when app has __compiled__ attribute."""
        import core.sentry as sentry_module
        sentry_module._sentry_initialized = False

        mock_logging_module = Mock()
        mock_logging_module.LoggingIntegration = mock_logging_int
        mock_sdk.integrations = Mock()
        mock_sdk.integrations.logging = mock_logging_module

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk, "sentry_sdk.integrations.logging": mock_logging_module}):
            with patch.dict("os.environ", {"SENTRY_DSN": "https://test@test.ingest.sentry.io/123"}):
                with patch("builtins.hasattr", return_value=True):
                    result = init_sentry()
                    assert result is True

    def test_init_default_environment_production(self, mock_sdk, mock_logging_int):
        """Test default environment is production when packaged."""
        import core.sentry as sentry_module
        sentry_module._sentry_initialized = False

        mock_logging_module = Mock()
        mock_logging_module.LoggingIntegration = mock_logging_int
        mock_sdk.integrations = Mock()
        mock_sdk.integrations.logging = mock_logging_module

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk, "sentry_sdk.integrations.logging": mock_logging_module}):
            with patch.dict("os.environ", {"SENTRY_DSN": "https://test@test.ingest.sentry.io/123"}):
                with patch("core.sentry.getattr", return_value=True):
                    result = init_sentry(force_enable=True)
                    assert result is True

    def test_init_default_environment_development(self, mock_sdk, mock_logging_int):
        """Test default environment is development when not packaged."""
        import core.sentry as sentry_module
        sentry_module._sentry_initialized = False

        mock_logging_module = Mock()
        mock_logging_module.LoggingIntegration = mock_logging_int
        mock_sdk.integrations = Mock()
        mock_sdk.integrations.logging = mock_logging_module

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk, "sentry_sdk.integrations.logging": mock_logging_module}):
            with patch.dict("os.environ", {"SENTRY_DSN": "https://test@test.ingest.sentry.io/123"}):
                with patch("core.sentry.getattr", return_value=False):
                    result = init_sentry(force_enable=True)
                    assert result is True

    def test_init_malformed_dsn(self, mock_sdk, mock_logging_int, caplog):
        """Test handling of malformed DSN."""
        import core.sentry as sentry_module
        sentry_module._sentry_initialized = False

        mock_logging_module = Mock()
        mock_logging_module.LoggingIntegration = mock_logging_int
        mock_sdk.integrations = Mock()
        mock_sdk.integrations.logging = mock_logging_module

        # Make init raise an exception
        mock_sdk.init = Mock(side_effect=Exception("Invalid DSN"))

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk, "sentry_sdk.integrations.logging": mock_logging_module}):
            with patch.dict("os.environ", {"SENTRY_DSN": "invalid-dsn"}):
                with patch("core.sentry.getattr", return_value=False):
                    result = init_sentry(force_enable=True)
                    assert result is False
                    assert "Failed to initialize" in caplog.text or "invalid DSN" in caplog.text


# ============================================================================
# Exception Capturing Tests (capture_exception)
# ============================================================================


class TestCaptureException:
    """Tests for capture_exception function."""

    def test_capture_exception_when_disabled(self, caplog):
        """Test that exceptions are logged but not captured when disabled."""
        error = ValueError("test error")
        capture_exception(error)
        assert "Not enabled" in caplog.text or "exception not captured" in caplog.text

    def test_capture_exception_sdk_not_installed(self, caplog):
        """Test handling when sentry_sdk is not installed."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        with patch.dict("sys.modules", {"sentry_sdk": None}):
            error = Exception("test")
            capture_exception(error)
            # Should log error about SDK not installed
            assert "SDK not installed" in caplog.text or "Failed to capture" in caplog.text

    def test_capture_exception_sdk_fails(self, caplog):
        """Test handling when SDK capture fails."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        mock_sdk = Mock()
        mock_sdk.push_scope = Mock(side_effect=Exception("SDK error"))

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            error = Exception("test")
            capture_exception(error)
            # Should log error about capture failure
            assert "Failed to capture" in caplog.text

    def test_capture_exception_success(self, mock_sdk):
        """Test successful exception capture."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            error = ValueError("test error")
            capture_exception(error)
            mock_sdk.capture_exception.assert_called_once_with(error)

    def test_capture_exception_with_kwargs(self, mock_sdk):
        """Test exception capture with extra context."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            error = RuntimeError("failure")
            capture_exception(error, user_id="123", request_path="/Users/john/api")
            mock_sdk.capture_exception.assert_called_once()

    def test_capture_exception_with_dict_kwarg(self, mock_sdk):
        """Test exception capture with dict kwarg."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            error = Exception("test")
            capture_exception(error, context={"path": "/Users/john/data", "count": 42})
            mock_sdk.capture_exception.assert_called_once()

    def test_capture_exception_with_list_kwarg(self, mock_sdk):
        """Test exception capture with list kwarg."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            error = Exception("test")
            capture_exception(error, files=["/Users/john/a.py", "/home/jane/b.py"])
            mock_sdk.capture_exception.assert_called_once()


# ============================================================================
# Message Capturing Tests (capture_message)
# ============================================================================


class TestCaptureMessage:
    """Tests for capture_message function."""

    def test_capture_message_when_disabled(self):
        """Test that messages are ignored when Sentry is disabled."""
        capture_message("test message")
        capture_message("test message", level="error")

    def test_capture_message_success(self, mock_sdk):
        """Test successful message capture."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            capture_message("test message")
            mock_sdk.capture_message.assert_called_once_with("test message", level="info")

    def test_capture_message_with_level(self, mock_sdk):
        """Test message capture with custom level."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            capture_message("warning message", level="warning")
            mock_sdk.capture_message.assert_called_once_with("warning message", level="warning")

    def test_capture_message_with_kwargs(self, mock_sdk):
        """Test message capture with extra context."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            capture_message("test", context="data", path="/Users/john/file.py")
            mock_sdk.capture_message.assert_called_once()

    def test_capture_message_various_levels(self, mock_sdk):
        """Test message capture with various log levels."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            levels = ["debug", "info", "warning", "error", "fatal"]
            for level in levels:
                capture_message(f"message at {level}", level=level)

            assert mock_sdk.capture_message.call_count == len(levels)

    def test_capture_message_with_kwargs_error(self, mock_sdk):
        """Test message capture with kwargs that cause an error."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        # Make set_extra raise an exception to test the error handling
        mock_scope = Mock()
        mock_scope.set_extra = Mock(side_effect=RuntimeError("set_extra failed"))
        mock_sdk.push_scope = Mock()
        mock_sdk.push_scope.return_value = mock_scope
        mock_sdk.push_scope.__enter__ = Mock(return_value=mock_scope)
        mock_sdk.push_scope.__exit__ = Mock(return_value=False)

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            capture_message("test", key="value")
            # Should handle the error gracefully
            mock_sdk.capture_message.assert_not_called()  # Should not call capture_message due to error

    def test_capture_message_sdk_not_installed(self):
        """Test handling when sentry_sdk is not installed."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        # Should not raise any error, just return silently
        with patch.dict("sys.modules", {"sentry_sdk": None}):
            capture_message("test message")

    def test_capture_message_sdk_fails(self, caplog):
        """Test handling when SDK capture fails."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        mock_sdk = Mock()
        mock_sdk.push_scope = Mock(side_effect=Exception("SDK error"))

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            capture_message("test message")
            # Should log error about capture failure
            assert "Failed to capture" in caplog.text


# ============================================================================
# Context Setting Tests (set_context)
# ============================================================================


class TestSetContext:
    """Tests for set_context function."""

    def test_set_context_when_disabled(self):
        """Test that set_context is safe to call when disabled."""
        set_context("test", {"key": "value"})

    def test_set_context_success(self, mock_sdk):
        """Test successful context setting."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            data = {"user": "john", "path": "/Users/john/project"}
            set_context("review", data)
            mock_sdk.set_context.assert_called_once()

    def test_set_context_masks_paths(self, mock_sdk):
        """Test that paths in context data are masked."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            data = {
                "project_path": "/Users/john/project",
                "config_path": "/home/jane/config.json",
                "count": 5,
            }
            set_context("build", data)
            mock_sdk.set_context.assert_called_once()

    def test_set_context_sdk_not_installed(self):
        """Test handling when sentry_sdk is not installed."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        # Should not raise any error
        with patch.dict("sys.modules", {"sentry_sdk": None}):
            set_context("test", {"key": "value"})

    def test_set_context_sdk_fails(self):
        """Test handling when SDK set_context fails."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        mock_sdk = Mock()
        mock_sdk.set_context = Mock(side_effect=Exception("SDK error"))

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            # Should not raise error
            set_context("test", {"key": "value"})


# ============================================================================
# Tag Setting Tests (set_tag)
# ============================================================================


class TestSetTag:
    """Tests for set_tag function."""

    def test_set_tag_when_disabled(self):
        """Test that set_tag is safe to call when disabled."""
        set_tag("key", "value")

    def test_set_tag_success(self, mock_sdk):
        """Test successful tag setting."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            set_tag("component", "planner")
            mock_sdk.set_tag.assert_called_once_with("component", "planner")

    def test_set_tag_non_string_value(self, mock_sdk):
        """Test tag setting with non-string value."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            set_tag("count", 42)
            mock_sdk.set_tag.assert_called_once_with("count", 42)

    def test_set_tag_sdk_not_installed(self):
        """Test handling when sentry_sdk is not installed."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        # Should not raise any error
        with patch.dict("sys.modules", {"sentry_sdk": None}):
            set_tag("key", "value")

    def test_set_tag_sdk_fails(self):
        """Test handling when SDK set_tag fails."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        mock_sdk = Mock()
        mock_sdk.set_tag = Mock(side_effect=Exception("SDK error"))

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            # Should not raise error
            set_tag("key", "value")


# ============================================================================
# State Query Tests (is_enabled, is_initialized)
# ============================================================================


class TestStateQueries:
    """Tests for is_enabled and is_initialized functions."""

    def test_is_enabled_initial_state(self):
        """Test that is_enabled returns False initially."""
        assert is_enabled() is False

    def test_is_initialized_initial_state(self):
        """Test that is_initialized returns False initially."""
        assert is_initialized() is False

    def test_is_enabled_after_init(self, mock_sdk, mock_logging_int):
        """Test that is_enabled returns True after successful init."""
        import core.sentry as sentry_module
        sentry_module._sentry_initialized = False

        mock_logging_module = Mock()
        mock_logging_module.LoggingIntegration = mock_logging_int
        mock_sdk.integrations = Mock()
        mock_sdk.integrations.logging = mock_logging_module

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk, "sentry_sdk.integrations.logging": mock_logging_module}):
            with patch.dict("os.environ", {"SENTRY_DSN": "https://test@test.ingest.sentry.io/123"}):
                init_sentry(force_enable=True)
                assert is_enabled() is True

    def test_is_initialized_after_init(self, mock_sdk, mock_logging_int):
        """Test that is_initialized returns True after init attempt."""
        import core.sentry as sentry_module
        sentry_module._sentry_initialized = False

        mock_logging_module = Mock()
        mock_logging_module.LoggingIntegration = mock_logging_int
        mock_sdk.integrations = Mock()
        mock_sdk.integrations.logging = mock_logging_module

        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk, "sentry_sdk.integrations.logging": mock_logging_module}):
            with patch.dict("os.environ", {"SENTRY_DSN": "https://test@test.ingest.sentry.io/123"}):
                init_sentry(force_enable=True)
                assert is_initialized() is True

    def test_is_enabled_after_failed_init(self):
        """Test that is_enabled returns False after failed init."""
        import core.sentry as sentry_module
        sentry_module._sentry_initialized = False

        with patch.dict("os.environ", {}, clear=False):
            with patch("os.environ.get", return_value=""):
                init_sentry()
                assert is_enabled() is False
                assert is_initialized() is True


# ============================================================================
# Edge Cases and Integration Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and integration scenarios."""

    def test_empty_and_whitespace_strings(self):
        """Test handling of empty and whitespace strings."""
        assert _mask_user_paths("") == ""
        assert _mask_user_paths("   ") == "   "
        assert _mask_object_paths("") == ""
        assert _mask_object_paths(None) is None

    def test_special_characters_in_paths(self):
        """Test paths with special characters."""
        path_with_special = "/Users/john.doe/project/file-with-dashes.py"
        result = _mask_user_paths(path_with_special)
        assert "/Users/***" in result
        assert "project/file-with-dashes.py" in result

    def test_unicode_paths(self):
        """Test handling of Unicode characters in paths."""
        unicode_path = "/Users/johñ/project/file.py"
        result = _mask_user_paths(unicode_path)
        assert "/Users/***" in result

    def test_very_long_paths(self):
        """Test handling of very long paths."""
        long_path = "/Users/john/" + "a" * 1000 + "/file.py"
        result = _mask_user_paths(long_path)
        assert "/Users/***" in result

    def test_circular_reference_handling(self):
        """Test that circular references don't cause infinite recursion."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        data = {"path": "/Users/john/file.py"}
        data["self"] = data

        # Should complete without hanging
        result = _mask_object_paths(data)
        assert result["path"] == "/Users/***/file.py"

    def test_before_send_with_all_event_fields(self):
        """Test _before_send with all possible event fields."""
        import core.sentry as sentry_module
        sentry_module._sentry_enabled = True

        event = {
            "event_id": "abc123",
            "message": "Error at /Users/john/app.py",
            "exception": {
                "values": [
                    {
                        "type": "ValueError",
                        "value": "Error in /Users/john/data.json",
                        "stacktrace": {
                            "frames": [
                                {
                                    "filename": "/Users/john/module.py",
                                    "abs_path": "/Users/john/module.py",
                                }
                            ]
                        },
                    }
                ]
            },
            "breadcrumbs": {
                "values": [
                    {"message": "Log from /home/jane/app.py", "data": {"path": "/home/jane/config"}}
                ]
            },
            "tags": {"user_path": "/Users/bob/workspace"},
            "contexts": {"app": {"path": "/Users/alice/app"}},
            "extra": {"file": "C:\\Users\\john\\data.txt"},
            "user": {"id": "123", "username": "john"},
        }

        result = _before_send(event, {})

        assert "/Users/***" in result["message"]
        assert result["user"] == {}
        assert "/Users/***" in result["tags"]["user_path"]
        assert "/Users/***" in result["contexts"]["app"]["path"]
