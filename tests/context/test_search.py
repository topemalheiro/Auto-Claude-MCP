"""Tests for search"""

from context.search import CodeSearcher
from pathlib import Path
import pytest


def test_CodeSearcher___init__():
    """Test CodeSearcher.__init__"""

    # Arrange
    project_dir = Path("/tmp/test")

    # Act
    searcher = CodeSearcher(project_dir)

    # Assert
    assert searcher.project_dir == project_dir.resolve()


def test_CodeSearcher_search_service(tmp_path):
    """Test CodeSearcher.search_service"""

    # Arrange
    searcher = CodeSearcher(tmp_path)

    # Create a test service directory with Python files
    service_dir = tmp_path / "api"
    service_dir.mkdir(parents=True)

    (service_dir / "auth.py").write_text(
        "def authenticate_user(username, password):\n"
        "    '''Authenticate user with credentials'''\n"
        "    return True\n"
    )
    (service_dir / "utils.py").write_text(
        "def helper_function():\n"
        "    pass\n"
    )

    keywords = ["authenticate", "user"]

    # Act
    result = searcher.search_service(service_dir, "api", keywords)

    # Assert
    assert isinstance(result, list)
    assert len(result) >= 1
    # Should find auth.py with high relevance
    auth_match = next((m for m in result if "auth.py" in m.path), None)
    assert auth_match is not None
    assert auth_match.service == "api"
    assert auth_match.relevance_score > 0
