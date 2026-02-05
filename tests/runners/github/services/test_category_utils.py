"""Tests for category_utils"""

from runners.github.services.category_utils import map_category
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_map_category():
    """Test map_category"""

    # Arrange
    raw_category = "security"

    # Act
    result = map_category(raw_category)

    # Assert
    assert result is not None
    assert result.value == "security"


def test_map_category_with_empty_inputs():
    """Test map_category with empty inputs"""

    # Arrange
    raw_category = ""

    # Act
    result = map_category(raw_category)

    # Assert
    # Empty string defaults to QUALITY after normalization
    assert result is not None
    assert result.value == "quality"


def test_map_category_with_invalid_input():
    """Test map_category with invalid input"""

    # Arrange & Act & Assert
    # The function defaults to QUALITY for unknown categories
    # It doesn't raise exceptions
    raw_category = "unknown_category_xyz"
    result = map_category(raw_category)
    assert result is not None
    assert result.value == "quality"
