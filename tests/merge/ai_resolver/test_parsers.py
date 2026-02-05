"""Tests for parsers"""

from merge.ai_resolver.parsers import extract_batch_code_blocks, extract_code_block, looks_like_code
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_extract_code_block():
    """Test extract_code_block"""

    # Arrange
    response = ""  # TODO: Set up test data
    language = ""  # TODO: Set up test data

    # Act
    result = extract_code_block(response, language)

    # Assert
    assert True  # Function runs without error



def test_looks_like_code():
    """Test looks_like_code"""

    # Arrange
    text = ""  # TODO: Set up test data
    language = ""  # TODO: Set up test data

    # Act
    result = looks_like_code(text, language)

    # Assert
    assert result is not None  # TODO: Add specific assertions



def test_extract_batch_code_blocks():
    """Test extract_batch_code_blocks"""

    # Arrange
    response = ""  # TODO: Set up test data
    location = ""  # TODO: Set up test data
    language = ""  # TODO: Set up test data

    # Act
    result = extract_batch_code_blocks(response, location, language)

    # Assert
    assert True  # Function runs without error
