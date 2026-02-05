"""Tests for comparison"""

from merge.semantic_analysis.comparison import classify_function_modification, classify_modification, compare_elements, get_add_change_type, get_location, get_remove_change_type
from merge.semantic_analysis.models import ExtractedElement
from merge.types import ChangeType
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_compare_elements():
    """Test compare_elements"""

    # Arrange
    before = {
        "func1": ExtractedElement(
            element_type="function",
            name="func1",
            start_line=1,
            end_line=5,
            content="def func1(): pass"
        )
    }

    after = {
        "func1": ExtractedElement(
            element_type="function",
            name="func1",
            start_line=1,
            end_line=5,
            content="def func1(): pass"
        ),
        "func2": ExtractedElement(
            element_type="function",
            name="func2",
            start_line=6,
            end_line=10,
            content="def func2(): pass"
        )
    }

    ext = ".py"

    # Act
    result = compare_elements(before, after, ext)

    # Assert
    assert result is not None
    assert len(result) >= 1  # Should detect func2 as added


def test_get_add_change_type():
    """Test get_add_change_type"""

    # Arrange & Act & Assert
    assert get_add_change_type("function") == ChangeType.ADD_FUNCTION
    assert get_add_change_type("class") == ChangeType.ADD_CLASS
    assert get_add_change_type("import") == ChangeType.ADD_IMPORT


def test_get_remove_change_type():
    """Test get_remove_change_type"""

    # Arrange & Act & Assert
    assert get_remove_change_type("function") == ChangeType.REMOVE_FUNCTION
    assert get_remove_change_type("class") == ChangeType.REMOVE_CLASS
    assert get_remove_change_type("import") == ChangeType.REMOVE_IMPORT


def test_get_location():
    """Test get_location"""

    # Arrange
    element = ExtractedElement(
        element_type="function",
        name="myFunc",
        start_line=10,
        end_line=15,
        content="def myFunc(): pass",
        parent="MyClass"
    )

    # Act
    result = get_location(element)

    # Assert
    assert result is not None
    assert "MyClass" in result or "myFunc" in result


def test_classify_modification():
    """Test classify_modification"""

    # Arrange
    before = ExtractedElement(
        element_type="function",
        name="myFunc",
        start_line=10,
        end_line=15,
        content="def myFunc(): pass"
    )

    after = ExtractedElement(
        element_type="function",
        name="myFunc",
        start_line=10,
        end_line=20,
        content="def myFunc():\n    return True"
    )

    ext = ".py"

    # Act
    result = classify_modification(before, after, ext)

    # Assert
    assert result is not None


def test_classify_function_modification():
    """Test classify_function_modification"""

    # Arrange
    before = "def myFunc():\n    pass"
    after = "def myFunc():\n    return True"
    ext = ".py"

    # Act
    result = classify_function_modification(before, after, ext)

    # Assert
    assert result is not None
