"""Tests for env_detector"""

from analysis.analyzers.context.env_detector import EnvironmentDetector
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_EnvironmentDetector___init__():
    """Test EnvironmentDetector.__init__"""
    path = Path("/tmp/test")
    analysis = {}

    detector = EnvironmentDetector(path, analysis)

    assert detector.path == path.resolve()
    assert detector.analysis is analysis


@patch("analysis.analyzers.context.env_detector.BaseAnalyzer._read_file")
def test_EnvironmentDetector_detect(mock_read_file):
    """Test EnvironmentDetector.detect"""
    mock_read_file.return_value = "DATABASE_URL=postgresql://localhost\nAPI_KEY=secret123\n"

    analysis = {}
    detector = EnvironmentDetector(Path("/tmp/test"), analysis)
    detector.detect()

    assert "environment" in analysis
    assert analysis["environment"]["detected_count"] > 0
