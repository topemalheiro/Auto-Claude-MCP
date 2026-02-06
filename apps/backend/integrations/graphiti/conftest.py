"""Fixtures for graphiti integration tests."""

from importlib.util import find_spec
from pathlib import Path

import pytest


def _check_graphiti_available() -> bool:
    """Check if graphiti dependencies are available."""
    return find_spec("kuzu") is not None or find_spec("real_ladybug") is not None


# Skip all graphiti integration tests if dependencies are not available
pytestmark = pytest.mark.skipif(
    not _check_graphiti_available(),
    reason="graphiti dependencies (kuzu or real_ladybug) not available",
)


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    """Provide a temporary database path for testing.

    Args:
        tmp_path: pytest's built-in temporary directory fixture

    Returns:
        str: Path to temporary database directory
    """
    db_dir = tmp_path / "graphiti_db"
    db_dir.mkdir(exist_ok=True)
    return str(db_dir)


@pytest.fixture
def database() -> str:
    """Provide a test database name.

    Returns:
        str: Test database name
    """
    return "test_db"
