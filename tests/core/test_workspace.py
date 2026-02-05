"""Tests for workspace"""

from core.workspace import merge_existing_build
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_merge_existing_build():
    """Test merge_existing_build"""

    # Arrange
    project_dir = Path("/tmp/test")  # TODO: Set up test data
    spec_name = ""  # TODO: Set up test data
    no_commit = True  # TODO: Set up test data
    use_smart_merge = True  # TODO: Set up test data
    base_branch = ""  # TODO: Set up test data

    # Act
    result = merge_existing_build(project_dir, spec_name, no_commit, use_smart_merge, base_branch)

    # Assert
    assert result is not None  # TODO: Add specific assertions
