"""Tests for prompts"""

from merge.ai_resolver.prompts import format_batch_merge_prompt, format_merge_prompt
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_format_merge_prompt():
    """Test format_merge_prompt"""

    # Arrange
    context = ""  # TODO: Set up test data
    language = ""  # TODO: Set up test data

    # Act
    result = format_merge_prompt(context, language)

    # Assert
    assert result is not None  # TODO: Add specific assertions



def test_format_batch_merge_prompt():
    """Test format_batch_merge_prompt"""

    # Arrange
    file_path = ""  # TODO: Set up test data
    num_conflicts = 0  # TODO: Set up test data
    combined_context = ""  # TODO: Set up test data
    language = ""  # TODO: Set up test data

    # Act
    result = format_batch_merge_prompt(file_path, num_conflicts, combined_context, language)

    # Assert
    assert result is not None  # TODO: Add specific assertions
