"""Tests for migrations_detector"""

from analysis.analyzers.context.migrations_detector import MigrationsDetector
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_MigrationsDetector___init__():
    """Test MigrationsDetector.__init__"""
    path = Path("/tmp/test")
    analysis = {}

    detector = MigrationsDetector(path, analysis)

    assert detector.path == path.resolve()
    assert detector.analysis is analysis


@patch("analysis.analyzers.context.migrations_detector.MigrationsDetector._detect_alembic")
def test_MigrationsDetector_detect(mock_detect_alembic):
    """Test MigrationsDetector.detect"""
    mock_detect_alembic.return_value = {
        "tool": "alembic",
        "directory": "alembic/versions",
        "config_file": "alembic.ini",
    }

    analysis = {}
    detector = MigrationsDetector(Path("/tmp/test"), analysis)
    detector.detect()

    assert "migrations" in analysis
    assert analysis["migrations"]["tool"] == "alembic"
