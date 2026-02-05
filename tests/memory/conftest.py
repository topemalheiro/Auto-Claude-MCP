"""
Fixtures for memory tests.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

import pytest


@pytest.fixture
def temp_spec_dir(tmp_path: Path) -> Path:
    """Create a temporary spec directory."""
    spec_dir = tmp_path / ".auto-claude" / "specs" / "001-test"
    spec_dir.mkdir(parents=True)
    return spec_dir


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory."""
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True)
    return project_dir


@pytest.fixture
def sample_insights() -> dict[str, Any]:
    """Sample session insights."""
    return {
        "subtasks_completed": ["subtask-1", "subtask-2"],
        "discoveries": {
            "files_understood": {
                "src/api/auth.py": "JWT authentication handler",
                "src/models/user.py": "User database model",
            },
            "patterns_found": [
                "Use async/await for all DB calls",
                "Validate input at service layer",
            ],
            "gotchas_encountered": [
                "Must close DB connections in workers",
                "API rate limits: 100 req/min per IP",
            ],
        },
        "what_worked": [
            "Added comprehensive error handling first",
            "Used transaction for data consistency",
        ],
        "what_failed": [
            "Tried inline validation - should use middleware",
            "Initial schema design was too rigid",
        ],
        "recommendations_for_next_session": [
            "Focus on integration tests next",
            "Consider adding caching layer",
        ],
    }


@pytest.fixture
def mock_graphiti_memory() -> MagicMock:
    """Mock GraphitiMemory instance."""
    mock = MagicMock()
    mock.initialize = AsyncMock()
    mock.save_session_insights = AsyncMock(return_value=True)
    mock.save_codebase_discoveries = AsyncMock()
    mock.save_pattern = AsyncMock()
    mock.save_gotcha = AsyncMock()
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_graphiti_enabled() -> Any:
    """Mock is_graphiti_enabled function."""
    with patch("memory.graphiti_helpers.is_graphiti_enabled", return_value=True):
        yield


@pytest.fixture
def mock_graphiti_disabled() -> Any:
    """Mock is_graphiti_enabled function returning False."""
    with patch("memory.graphiti_helpers.is_graphiti_enabled", return_value=False):
        yield
