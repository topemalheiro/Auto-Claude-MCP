"""Tests for icons"""

from unittest.mock import MagicMock, patch

import pytest


def test_icon_unicode():
    """Test icon returns unicode when supported"""
    from ui.icons import Icons, icon


    # Arrange
    icon_tuple = ("✓", "[OK]")

    with patch("ui.icons.UNICODE", True):
        # Act
        result = icon(icon_tuple)

        # Assert
        assert result == "✓"


def test_icon_ascii_fallback():
    """Test icon returns ASCII fallback when unicode not supported"""
    from ui.icons import Icons, icon


    # Arrange
    icon_tuple = ("✓", "[OK]")

    with patch("ui.icons.UNICODE", False):
        # Act
        result = icon(icon_tuple)

        # Assert
        assert result == "[OK]"


def test_icon_success():
    """Test Icons.SUCCESS"""
    from ui.icons import Icons, icon


    # Arrange
    with patch("ui.icons.UNICODE", True):
        # Act
        result = icon(Icons.SUCCESS)

        # Assert
        assert result == "✓"


def test_icon_error():
    """Test Icons.ERROR"""
    from ui.icons import Icons, icon


    # Arrange
    with patch("ui.icons.UNICODE", True):
        # Act
        result = icon(Icons.ERROR)

        # Assert
        assert result == "✗"


def test_icon_warning():
    """Test Icons.WARNING"""
    from ui.icons import Icons, icon


    # Arrange
    with patch("ui.icons.UNICODE", True):
        # Act
        result = icon(Icons.WARNING)

        # Assert
        assert result == "⚠"


def test_icon_arrow_right():
    """Test Icons.ARROW_RIGHT"""
    from ui.icons import Icons, icon


    # Arrange
    with patch("ui.icons.UNICODE", True):
        # Act
        result = icon(Icons.ARROW_RIGHT)

        # Assert
        assert result == "→"


def test_icon_arrow_right_ascii():
    """Test Icons.ARROW_RIGHT ASCII fallback"""
    from ui.icons import Icons, icon


    # Arrange
    with patch("ui.icons.UNICODE", False):
        # Act
        result = icon(Icons.ARROW_RIGHT)

        # Assert
        assert result == "->"


def test_icon_subtask():
    """Test Icons.SUBTASK"""
    from ui.icons import Icons, icon


    # Arrange
    with patch("ui.icons.UNICODE", True):
        # Act
        result = icon(Icons.SUBTASK)

        # Assert
        assert result == "▣"


def test_icon_phase():
    """Test Icons.PHASE"""
    from ui.icons import Icons, icon


    # Arrange
    with patch("ui.icons.UNICODE", True):
        # Act
        result = icon(Icons.PHASE)

        # Assert
        assert result == "◆"


def test_icon_worker():
    """Test Icons.WORKER"""
    from ui.icons import Icons, icon


    # Arrange
    with patch("ui.icons.UNICODE", True):
        # Act
        result = icon(Icons.WORKER)

        # Assert
        assert result == "⚡"


def test_icon_pause():
    """Test Icons.PAUSE"""
    from ui.icons import Icons, icon


    # Arrange
    with patch("ui.icons.UNICODE", True):
        # Act
        result = icon(Icons.PAUSE)

        # Assert
        assert result == "⏸"


def test_icon_pause_ascii():
    """Test Icons.PAUSE ASCII fallback"""
    from ui.icons import Icons, icon


    # Arrange
    with patch("ui.icons.UNICODE", False):
        # Act
        result = icon(Icons.PAUSE)

        # Assert
        assert result == "||"


def test_icon_pointer():
    """Test Icons.POINTER"""
    from ui.icons import Icons, icon


    # Arrange
    with patch("ui.icons.UNICODE", True):
        # Act
        result = icon(Icons.POINTER)

        # Assert
        assert result == "❯"


def test_icon_pointer_ascii():
    """Test Icons.POINTER ASCII fallback"""
    from ui.icons import Icons, icon


    # Arrange
    with patch("ui.icons.UNICODE", False):
        # Act
        result = icon(Icons.POINTER)

        # Assert
        assert result == ">"


def test_icons_class_has_all_attributes():
    """Test Icons class has all expected attributes"""
    from ui.icons import Icons, icon


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
    from ui.icons import Icons, icon


    # Arrange & Act
    for attr in dir(Icons):
        if not attr.startswith("_"):
            value = getattr(Icons, attr)
            if isinstance(value, tuple):
                # Assert
                assert len(value) == 2, f"Icons.{attr} should be a 2-element tuple"
                assert isinstance(value[0], str), f"Icons.{attr}[0] should be a string"
                assert isinstance(value[1], str), f"Icons.{attr}[1] should be a string"
