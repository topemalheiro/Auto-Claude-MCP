"""Tests for claude_client"""

from merge.ai_resolver.claude_client import create_claude_resolver
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_create_claude_resolver():
    """Test create_claude_resolver"""

    # Arrange
    # Set up test data

    # Act
    result = create_claude_resolver()

    # Assert
    assert result is not None  # TODO: Add specific assertions
