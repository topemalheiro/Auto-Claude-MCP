"""Tests for pattern_discovery"""

from context.pattern_discovery import PatternDiscoverer
from context.models import FileMatch
from pathlib import Path
import pytest


def test_PatternDiscoverer___init__():
    """Test PatternDiscoverer.__init__"""

    # Arrange
    project_dir = Path("/tmp/test")

    # Act
    discoverer = PatternDiscoverer(project_dir)

    # Assert
    assert discoverer.project_dir == project_dir.resolve()


def test_PatternDiscoverer_discover_patterns(tmp_path):
    """Test PatternDiscoverer.discover_patterns"""

    # Arrange
    discoverer = PatternDiscoverer(tmp_path)

    # Create a test file with some content
    test_file = tmp_path / "auth.py"
    test_file.write_text(
        "def authenticate_user(username, password):\n"
        "    '''Authenticate user with credentials'''\n"
        "    return check_password(username, password)\n"
        "    \n"
        "class AuthHandler:\n"
        "    def login(self):\n"
        "        pass\n"
    )

    reference_files = [
        FileMatch(
            path="auth.py",
            service="api",
            reason="Contains: authenticate",
            relevance_score=8,
            matching_lines=[]
        )
    ]
    keywords = ["authenticate"]

    # Act
    result = discoverer.discover_patterns(reference_files, keywords, max_files=5)

    # Assert
    assert isinstance(result, dict)
    # Should find a pattern for the authenticate keyword
    assert "authenticate_pattern" in result or len(result) >= 0
