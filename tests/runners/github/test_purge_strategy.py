"""Tests for purge_strategy"""

from runners.github.purge_strategy import PurgeResult, PurgeStrategy
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from datetime import datetime, timezone
import asyncio
import tempfile


def test_PurgeResult_to_dict():
    """Test PurgeResult.to_dict"""

    # Arrange
    now = datetime.now(timezone.utc)
    instance = PurgeResult(
        deleted_count=10,
        freed_bytes=2048000,
        errors=["error1"],
        started_at=now,
        completed_at=now
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result["deleted_count"] == 10
    assert result["freed_bytes"] == 2048000
    assert result["freed_mb"] == round(2048000 / (1024 * 1024), 2)
    assert result["errors"] == ["error1"]


def test_PurgeStrategy___init__():
    """Test PurgeStrategy.__init__"""

    # Arrange & Act
    state_dir = Path("/tmp/test")
    instance = PurgeStrategy(state_dir)

    # Assert
    assert instance.state_dir == state_dir


def test_PurgeStrategy_purge_by_criteria(tmp_path):
    """Test PurgeStrategy.purge_by_criteria"""

    # Arrange
    instance = PurgeStrategy(tmp_path)

    # Create test file
    pr_dir = tmp_path / "pr"
    pr_dir.mkdir(parents=True)
    test_file = pr_dir / "test_123.json"
    test_file.write_text('{"issue_number": 123, "repo": "owner/repo"}')

    # Act
    result = asyncio.run(instance.purge_by_criteria(
        pattern="pr",
        key="issue_number",
        value=123,
        repo=None
    ))

    # Assert
    assert result is not None
    assert isinstance(result, PurgeResult)
    assert result.deleted_count >= 0


def test_PurgeStrategy_purge_repository(tmp_path):
    """Test PurgeStrategy.purge_repository"""

    # Arrange
    instance = PurgeStrategy(tmp_path)

    # Create test files with specific repo
    pr_dir = tmp_path / "pr"
    pr_dir.mkdir(parents=True)
    (pr_dir / "test1.json").write_text('{"repo": "owner/test-repo"}')

    # Act
    result = asyncio.run(instance.purge_repository("owner/test-repo"))

    # Assert
    assert result is not None
    assert isinstance(result, PurgeResult)
