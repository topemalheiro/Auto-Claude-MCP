"""Tests for categorizer"""

from context.categorizer import FileCategorizer
from context.models import FileMatch
from pathlib import Path
import pytest


def test_FileCategorizer_categorize_matches():
    """Test FileCategorizer.categorize_matches"""

    # Arrange
    categorizer = FileCategorizer()
    matches = [
        FileMatch(
            path="api/auth.py",
            service="api",
            reason="Contains: authentication",
            relevance_score=8,
            matching_lines=[(1, "def authenticate_user"), (10, "class AuthHandler")]
        ),
        FileMatch(
            path="api/test_auth.py",
            service="api",
            reason="Contains: authentication",
            relevance_score=6,
            matching_lines=[(1, "def test_login")]
        ),
        FileMatch(
            path="api/config.py",
            service="api",
            reason="Contains: settings",
            relevance_score=3,
            matching_lines=[]
        ),
    ]
    task = "Add authentication to the API"

    # Act
    to_modify, to_reference = categorizer.categorize_matches(matches, task)

    # Assert
    # High relevance files in modification task should be marked for modification
    assert len(to_modify) >= 1
    # Tests should always be references
    assert any(f.path == "api/test_auth.py" for f in to_reference)
    # Config with low score should be reference
    assert any(f.path == "api/config.py" for f in to_reference)
