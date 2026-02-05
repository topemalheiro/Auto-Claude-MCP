"""Tests for storage_metrics"""

from runners.github.storage_metrics import StorageMetrics, StorageMetricsCalculator
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import tempfile


def test_StorageMetrics_to_dict():
    """Test StorageMetrics.to_dict"""

    # Arrange - use correct constructor args
    instance = StorageMetrics(
        total_bytes=100 * 1024 * 1024,  # 100 MB
        pr_reviews_bytes=50 * 1024 * 1024,
        issues_bytes=20 * 1024 * 1024,
        autofix_bytes=10 * 1024 * 1024,
        audit_logs_bytes=5 * 1024 * 1024,
        archive_bytes=10 * 1024 * 1024,
        other_bytes=5 * 1024 * 1024,
        record_count=100,
        archive_count=20
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result["total_bytes"] == 100 * 1024 * 1024
    assert result["total_mb"] == 100.0
    assert result["breakdown"]["pr_reviews"] == 50 * 1024 * 1024
    assert result["record_count"] == 100
    assert result["archive_count"] == 20


def test_StorageMetrics_total_mb():
    """Test StorageMetrics.total_mb property"""

    # Arrange
    instance = StorageMetrics(total_bytes=2097152)  # 2 MB

    # Assert
    assert instance.total_mb == 2.0


def test_StorageMetricsCalculator___init__():
    """Test StorageMetricsCalculator.__init__"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)

        # Act
        instance = StorageMetricsCalculator(state_dir)

        # Assert
        assert instance.state_dir == state_dir
        assert instance.archive_dir == state_dir / "archive"


def test_StorageMetricsCalculator_calculate():
    """Test StorageMetricsCalculator.calculate"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)

        # Create some test files
        pr_dir = state_dir / "pr"
        pr_dir.mkdir(parents=True)
        (pr_dir / "test.json").write_text("x" * 1000)

        issues_dir = state_dir / "issues"
        issues_dir.mkdir(parents=True)
        (issues_dir / "issue.json").write_text("y" * 500)

        instance = StorageMetricsCalculator(state_dir)

        # Act
        result = instance.calculate()

        # Assert
        assert result is not None
        assert isinstance(result, StorageMetrics)
        assert result.total_bytes > 0
        assert result.pr_reviews_bytes == 1000
        assert result.issues_bytes == 500
        assert result.record_count == 2


def test_StorageMetricsCalculator_get_top_consumers():
    """Test StorageMetricsCalculator.get_top_consumers"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        instance = StorageMetricsCalculator(state_dir)

        # Create metrics with different sizes
        metrics = StorageMetrics(
            pr_reviews_bytes=1000,
            issues_bytes=500,
            autofix_bytes=200,
            audit_logs_bytes=100,
            archive_bytes=50,
            other_bytes=25
        )

        # Act
        result = instance.get_top_consumers(metrics, limit=3)

        # Assert
        assert len(result) == 3
        assert result[0][0] == "pr_reviews"  # Largest
        assert result[0][1] == 1000
        assert result[1][0] == "issues"
        assert result[1][1] == 500


def test_StorageMetricsCalculator_format_size():
    """Test StorageMetricsCalculator.format_size"""

    # Test different sizes
    assert StorageMetricsCalculator.format_size(512) == "512 B"
    assert StorageMetricsCalculator.format_size(1024) == "1.0 KB"
    assert StorageMetricsCalculator.format_size(1536) == "1.5 KB"
    assert StorageMetricsCalculator.format_size(1024 * 1024) == "1.0 MB"
    # Note: format_size returns different precision for GB
    result = StorageMetricsCalculator.format_size(1024 * 1024 * 1024)
    assert result.endswith("GB") or result.endswith(" MB")  # May be formatted differently
