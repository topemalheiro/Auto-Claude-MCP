"""Tests for spinner"""

from unittest.mock import MagicMock, patch

import pytest

from ui.spinner import Spinner


def test_Spinner___init__():
    """Test Spinner.__init__"""

    # Arrange & Act
    spinner = Spinner("Loading...")

    # Assert
    assert spinner.message == "Loading..."
    assert spinner.frame == 0
    assert spinner._running is False


def test_Spinner___init__default():
    """Test Spinner.__init__ with default message"""

    # Arrange & Act
    spinner = Spinner()

    # Assert
    assert spinner.message == ""
    assert spinner.frame == 0
    assert spinner._running is False


@patch("sys.stdout")
def test_Spinner_start(mock_stdout):
    """Test Spinner.start"""

    # Arrange
    spinner = Spinner("Loading...")

    # Act
    spinner.start()

    # Assert
    assert spinner._running is True


@patch("sys.stdout")
def test_Spinner_stop(mock_stdout):
    """Test Spinner.stop"""

    # Arrange
    spinner = Spinner("Loading...")
    spinner.start()

    # Act
    spinner.stop("Done!", "success")

    # Assert
    assert spinner._running is False


@patch("sys.stdout")
def test_Spinner_stop_no_message(mock_stdout):
    """Test Spinner.stop without final message"""

    # Arrange
    spinner = Spinner("Loading...")
    spinner.start()

    # Act - should not raise
    spinner.stop()

    # Assert
    assert spinner._running is False


@patch("sys.stdout")
def test_Spinner_update(mock_stdout):
    """Test Spinner.update"""

    # Arrange
    spinner = Spinner("Loading...")
    initial_frame = spinner.frame
    spinner.start()

    # Act
    spinner.update("Still loading...")

    # Assert
    assert spinner.message == "Still loading..."
    assert spinner.frame != initial_frame  # Frame should have advanced


@patch("sys.stdout")
def test_Spinner_update_no_message(mock_stdout):
    """Test Spinner.update without new message"""

    # Arrange
    spinner = Spinner("Loading...")
    initial_frame = spinner.frame
    spinner.start()

    # Act
    spinner.update()

    # Assert
    assert spinner.message == "Loading..."  # Message unchanged
    assert spinner.frame != initial_frame  # Frame should have advanced


def test_Spinner_FRAMES():
    """Test Spinner.FRAMES contains valid frames"""

    # Arrange & Act
    frames = Spinner.FRAMES

    # Assert
    assert isinstance(frames, list)
    assert len(frames) > 0
    assert all(isinstance(f, str) for f in frames)


@patch("sys.stdout")
def test_Spinner_multiple_updates(mock_stdout):
    """Test Spinner with multiple updates"""

    # Arrange
    spinner = Spinner("Step 1")
    spinner.start()

    # Act
    spinner.update("Step 2")
    spinner.update("Step 3")
    spinner.update("Step 4")
    spinner.stop("Complete!")

    # Assert
    assert spinner.message == "Step 4"
    assert spinner._running is False


@patch("sys.stdout")
def test_Spinner_render(mock_stdout):
    """Test Spinner._render"""

    # Arrange
    spinner = Spinner("Test")
    spinner._running = True

    # Act - should not raise
    spinner._render()

    # Assert
    mock_stdout.write.assert_called()
    mock_stdout.flush.assert_called()
