"""Tests for cleanup"""

from runners.github.cleanup import CleanupResult, DataCleaner, RetentionConfig, RetentionPolicy
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
from datetime import datetime, timedelta, timezone
import asyncio


def test_RetentionConfig_get_retention_days():
    """Test RetentionConfig.get_retention_days"""

    # Arrange
    config = RetentionConfig(
        completed_days=90,
        failed_days=30,
        cancelled_days=7,
        stale_days=14
    )

    # Act & Assert
    assert config.get_retention_days(RetentionPolicy.COMPLETED) == 90
    assert config.get_retention_days(RetentionPolicy.FAILED) == 30
    assert config.get_retention_days(RetentionPolicy.CANCELLED) == 7
    assert config.get_retention_days(RetentionPolicy.STALE) == 14
    assert config.get_retention_days(RetentionPolicy.ARCHIVED) == -1


def test_RetentionConfig_to_dict():
    """Test RetentionConfig.to_dict"""

    # Arrange
    config = RetentionConfig(
        completed_days=100,
        failed_days=40,
        cancelled_days=10,
        stale_days=20,
        archive_enabled=False,
        gdpr_mode=True
    )

    # Act
    result = config.to_dict()

    # Assert
    assert result == {
        "completed_days": 100,
        "failed_days": 40,
        "cancelled_days": 10,
        "stale_days": 20,
        "archive_enabled": False,
        "gdpr_mode": True,
    }


def test_RetentionConfig_from_dict():
    """Test RetentionConfig.from_dict"""

    # Arrange
    data = {
        "completed_days": 60,
        "failed_days": 20,
        "cancelled_days": 5,
        "stale_days": 10,
        "archive_enabled": True,
        "gdpr_mode": False,
        "extra_field": "ignored"  # Should be filtered
    }

    # Act
    result = RetentionConfig.from_dict(data)

    # Assert
    assert result.completed_days == 60
    assert result.failed_days == 20
    assert result.cancelled_days == 5
    assert result.stale_days == 10
    assert result.archive_enabled is True
    assert result.gdpr_mode is False


def test_CleanupResult_to_dict():
    """Test CleanupResult.to_dict"""

    # Arrange
    now = datetime.now(timezone.utc)
    result = CleanupResult(
        deleted_count=10,
        archived_count=5,
        pruned_index_entries=3,
        freed_bytes=1024000,
        errors=["error1", "error2"],
        started_at=now,
        completed_at=now + timedelta(seconds=5),
        dry_run=False
    )

    # Act
    dict_result = result.to_dict()

    # Assert
    assert dict_result["deleted_count"] == 10
    assert dict_result["archived_count"] == 5
    assert dict_result["pruned_index_entries"] == 3
    assert dict_result["freed_bytes"] == 1024000
    assert dict_result["freed_mb"] == round(1024000 / (1024 * 1024), 2)
    assert dict_result["errors"] == ["error1", "error2"]
    assert dict_result["duration_seconds"] == 5.0
    assert dict_result["dry_run"] is False


def test_CleanupResult_freed_mb():
    """Test CleanupResult.freed_mb property"""

    # Arrange
    result = CleanupResult(freed_bytes=2097152)  # 2 MB

    # Assert
    assert result.freed_mb == 2.0


def test_CleanupResult_duration():
    """Test CleanupResult.duration property"""

    # Arrange
    now = datetime.now(timezone.utc)
    result = CleanupResult(
        started_at=now,
        completed_at=now + timedelta(seconds=10)
    )

    # Assert
    assert result.duration == timedelta(seconds=10)
    assert result.duration.total_seconds() == 10


def test_DataCleaner___init__():
    """Test DataCleaner.__init__"""

    # Arrange
    state_dir = Path("/tmp/test_state")
    config = RetentionConfig(completed_days=60)

    # Act
    cleaner = DataCleaner(state_dir, config)

    # Assert
    assert cleaner.state_dir == state_dir
    assert cleaner.config.completed_days == 60
    assert cleaner.archive_dir == state_dir / "archive"


def test_DataCleaner_get_storage_metrics(tmp_path):
    """Test DataCleaner.get_storage_metrics"""

    # Arrange
    cleaner = DataCleaner(tmp_path)

    # Act
    metrics = cleaner.get_storage_metrics()

    # Assert
    assert metrics is not None
    assert hasattr(metrics, "to_dict")


def test_DataCleaner_run_cleanup(tmp_path):
    """Test DataCleaner.run_cleanup with dry run"""

    # Arrange
    cleaner = DataCleaner(tmp_path)

    # Create some test files
    pr_dir = tmp_path / "pr"
    pr_dir.mkdir(parents=True)
    old_file = pr_dir / "old_pr.json"
    old_file.write_text('{"status": "completed", "updated_at": "2020-01-01T00:00:00Z"}')

    # Act
    result = asyncio.run(cleaner.run_cleanup(dry_run=True, older_than_days=0))

    # Assert
    assert result.dry_run is True
    assert result.completed_at is not None


def test_DataCleaner_purge_issue(tmp_path):
    """Test DataCleaner.purge_issue"""

    # Arrange
    cleaner = DataCleaner(tmp_path)

    # Create test issue file
    issues_dir = tmp_path / "issues"
    issues_dir.mkdir(parents=True)
    issue_file = issues_dir / "issue_123.json"
    issue_file.write_text('{"issue_number": 123, "status": "completed"}')

    # Act
    result = asyncio.run(cleaner.purge_issue(123))

    # Assert
    assert result is not None
    assert isinstance(result, CleanupResult)


def test_DataCleaner_purge_pr(tmp_path):
    """Test DataCleaner.purge_pr"""

    # Arrange
    cleaner = DataCleaner(tmp_path)

    # Create test PR file
    pr_dir = tmp_path / "pr"
    pr_dir.mkdir(parents=True)
    pr_file = pr_dir / "pr_456.json"
    pr_file.write_text('{"pr_number": 456, "status": "completed"}')

    # Act
    result = asyncio.run(cleaner.purge_pr(456))

    # Assert
    assert result is not None
    assert isinstance(result, CleanupResult)


def test_DataCleaner_purge_repo(tmp_path):
    """Test DataCleaner.purge_repo"""

    # Arrange
    cleaner = DataCleaner(tmp_path)

    # Create test files
    pr_dir = tmp_path / "pr"
    pr_dir.mkdir(parents=True)
    pr_file = pr_dir / "pr_789.json"
    pr_file.write_text('{"pr_number": 789, "repo": "owner/repo"}')

    # Act
    result = asyncio.run(cleaner.purge_repo("owner/repo"))

    # Assert
    assert result is not None
    assert isinstance(result, CleanupResult)


def test_DataCleaner_get_retention_summary(tmp_path):
    """Test DataCleaner.get_retention_summary"""

    # Arrange
    config = RetentionConfig(completed_days=100)
    cleaner = DataCleaner(tmp_path, config)

    # Act
    summary = cleaner.get_retention_summary()

    # Assert
    assert "config" in summary
    assert "storage" in summary
    assert "archive_enabled" in summary
    assert "gdpr_mode" in summary
    assert summary["config"]["completed_days"] == 100
    assert summary["archive_enabled"] is True  # default
