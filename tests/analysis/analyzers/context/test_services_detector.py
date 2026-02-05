"""Tests for services_detector"""

from analysis.analyzers.context.services_detector import ServicesDetector
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_ServicesDetector___init__():
    """Test ServicesDetector.__init__"""
    path = Path("/tmp/test")
    analysis = {}

    detector = ServicesDetector(path, analysis)

    assert detector.path == path.resolve()
    assert detector.analysis is analysis


@patch("analysis.analyzers.context.services_detector.ServicesDetector._get_all_dependencies")
def test_ServicesDetector_detect(mock_get_all_dependencies):
    """Test ServicesDetector.detect"""
    mock_get_all_dependencies.return_value = {"psycopg2", "redis", "celery"}

    analysis = {}
    detector = ServicesDetector(Path("/tmp/test"), analysis)
    detector.detect()

    assert "services" in analysis
    assert "databases" in analysis["services"]
    # Should detect PostgreSQL from psycopg2
    assert any(db["type"] == "postgresql" for db in analysis["services"]["databases"])
