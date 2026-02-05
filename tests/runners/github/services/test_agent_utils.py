"""Tests for agent_utils"""

from runners.github.services.agent_utils import create_working_dir_injector
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_create_working_dir_injector():
    """Test create_working_dir_injector"""

    # Arrange
    working_dir = Path("/tmp/test")

    # Act
    result = create_working_dir_injector(working_dir)

    # Assert
    assert result is not None
    assert callable(result)
    # Test the returned injector function
    prompt = "Test prompt"
    fallback = "Fallback prompt"
    injected = result(prompt, fallback)
    assert "/tmp/test" in injected
    assert "Working Directory" in injected


def test_create_working_dir_injector_with_empty_inputs():
    """Test create_working_dir_injector with empty inputs"""

    # Arrange
    working_dir = Path("/tmp/test")

    # Act
    result = create_working_dir_injector(working_dir)

    # Assert
    assert result is not None
    assert callable(result)
    # Test with None prompt
    injected = result(None, "Fallback")
    assert "/tmp/test" in injected
    assert "Fallback" in injected


def test_create_working_dir_injector_with_invalid_input():
    """Test create_working_dir_injector with invalid input"""

    # Arrange & Act & Assert
    # The function accepts any Path object, so even "invalid" paths work
    # The function doesn't raise exceptions - it just creates an injector
    working_dir = Path("/nonexistent/path")
    result = create_working_dir_injector(working_dir)
    assert result is not None
    assert callable(result)
