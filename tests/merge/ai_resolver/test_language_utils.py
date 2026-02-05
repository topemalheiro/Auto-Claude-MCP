"""Tests for language_utils"""

from merge.ai_resolver.language_utils import infer_language, locations_overlap
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_infer_language():
    """Test infer_language"""

    # Arrange
    file_path = ""  # TODO: Set up test data

    # Act
    result = infer_language(file_path)

    # Assert
    assert result is not None  # TODO: Add specific assertions



def test_locations_overlap():
    """Test locations_overlap"""

    # Arrange
    loc1 = ""  # TODO: Set up test data
    loc2 = ""  # TODO: Set up test data

    # Act
    result = locations_overlap(loc1, loc2)

    # Assert
    assert result is not None  # TODO: Add specific assertions
