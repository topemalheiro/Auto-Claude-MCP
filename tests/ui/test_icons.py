"""Tests for icons"""

from unittest.mock import MagicMock, patch

import pytest

from ui.icons import Icons, icon


def test_icon_unicode():
    """Test icon returns unicode when supported"""

    # Arrange
    icon_tuple = ("✓", "[OK]")

    with patch("ui.icons.UNICODE", True):
        # Act
        result = icon(icon_tuple)

        # Assert
        assert result == "✓"


def test_icon_ascii_fallback():
    """Test icon returns ASCII fallback when unicode not supported"""

    # Arrange
    icon_tuple = ("✓", "[OK]")

    with patch("ui.icons.UNICODE", False):
        # Act
        result = icon(icon_tuple)

        # Assert
        assert result == "[OK]"


def test_icon_success():
    """Test Icons.SUCCESS"""

    # Arrange
    with patch("ui.icons.UNICODE", True):
        # Act
        result = icon(Icons.SUCCESS)

        # Assert
        assert result == "✓"


def test_icon_error():
    """Test Icons.ERROR"""

    # Arrange
    with patch("ui.icons.UNICODE", True):
        # Act
        result = icon(Icons.ERROR)

        # Assert
        assert result == "✗"


def test_icon_warning():
    """Test Icons.WARNING"""

    # Arrange
    with patch("ui.icons.UNICODE", True):
        # Act
        result = icon(Icons.WARNING)

        # Assert
        assert result == "⚠"


def test_icon_arrow_right():
    """Test Icons.ARROW_RIGHT"""

    # Arrange
    with patch("ui.icons.UNICODE", True):
        # Act
        result = icon(Icons.ARROW_RIGHT)

        # Assert
        assert result == "→"


def test_icon_arrow_right_ascii():
    """Test Icons.ARROW_RIGHT ASCII fallback"""

    # Arrange
    with patch("ui.icons.UNICODE", False):
        # Act
        result = icon(Icons.ARROW_RIGHT)

        # Assert
        assert result == "->"


def test_icon_subtask():
    """Test Icons.SUBTASK"""

    # Arrange
    with patch("ui.icons.UNICODE", True):
        # Act
        result = icon(Icons.SUBTASK)

        # Assert
        assert result == "▣"


def test_icon_phase():
    """Test Icons.PHASE"""

    # Arrange
    with patch("ui.icons.UNICODE", True):
        # Act
        result = icon(Icons.PHASE)

        # Assert
        assert result == "◆"


def test_icon_worker():
    """Test Icons.WORKER"""

    # Arrange
    with patch("ui.icons.UNICODE", True):
        # Act
        result = icon(Icons.WORKER)

        # Assert
        assert result == "⚡"


def test_icon_pause():
    """Test Icons.PAUSE"""

    # Arrange
    with patch("ui.icons.UNICODE", True):
        # Act
        result = icon(Icons.PAUSE)

        # Assert
        assert result == "⏸"


def test_icon_pause_ascii():
    """Test Icons.PAUSE ASCII fallback"""

    # Arrange
    with patch("ui.icons.UNICODE", False):
        # Act
        result = icon(Icons.PAUSE)

        # Assert
        assert result == "||"


def test_icon_pointer():
    """Test Icons.POINTER"""

    # Arrange
    with patch("ui.icons.UNICODE", True):
        # Act
        result = icon(Icons.POINTER)

        # Assert
        assert result == "❯"


def test_icon_pointer_ascii():
    """Test Icons.POINTER ASCII fallback"""

    # Arrange
    with patch("ui.icons.UNICODE", False):
        # Act
        result = icon(Icons.POINTER)

        # Assert
        assert result == ">"


def test_icons_class_has_all_attributes():
    """Test Icons class has all expected attributes"""

    # Arrange & Act
    attributes = [
        "SUCCESS",
        "ERROR",
        "WARNING",
        "INFO",
        "PENDING",
        "IN_PROGRESS",
        "COMPLETE",
        "BLOCKED",
        "PLAY",
        "PAUSE",
        "STOP",
        "SKIP",
        "ARROW_RIGHT",
        "ARROW_DOWN",
        "ARROW_UP",
        "POINTER",
        "BULLET",
        "FOLDER",
        "FILE",
        "GEAR",
        "SEARCH",
        "BRANCH",
        "COMMIT",
        "LIGHTNING",
        "LINK",
        "SUBTASK",
        "PHASE",
        "WORKER",
        "SESSION",
        "EDIT",
        "CLIPBOARD",
        "DOCUMENT",
        "DOOR",
        "SHIELD",
    ]

    # Assert
    for attr in attributes:
        assert hasattr(Icons, attr), f"Icons.{attr} not found"


def test_icon_all_icons_are_tuples():
    """Test all Icons attributes are tuples"""

    # Arrange & Act
    for attr in dir(Icons):
        if not attr.startswith("_"):
            value = getattr(Icons, attr)
            if isinstance(value, tuple):
                # Assert
                assert len(value) == 2, f"Icons.{attr} should be a 2-element tuple"
                assert isinstance(value[0], str), f"Icons.{attr}[0] should be a string"
                assert isinstance(value[1], str), f"Icons.{attr}[1] should be a string"
