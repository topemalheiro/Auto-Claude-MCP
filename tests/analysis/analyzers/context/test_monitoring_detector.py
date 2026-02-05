"""Tests for monitoring_detector"""

from analysis.analyzers.context.monitoring_detector import MonitoringDetector
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_MonitoringDetector___init__():
    """Test MonitoringDetector.__init__"""
    path = Path("/tmp/test")
    analysis = {}

    detector = MonitoringDetector(path, analysis)

    assert detector.path == path.resolve()
    assert detector.analysis is analysis


@patch("analysis.analyzers.context.monitoring_detector.MonitoringDetector._detect_prometheus")
def test_MonitoringDetector_detect(mock_detect_prometheus):
    """Test MonitoringDetector.detect"""
    mock_detect_prometheus.return_value = {
        "metrics_endpoint": "/metrics",
        "metrics_type": "prometheus",
    }

    analysis = {}
    detector = MonitoringDetector(Path("/tmp/test"), analysis)
    detector.detect()

    assert "monitoring" in analysis
    assert analysis["monitoring"]["metrics_endpoint"] == "/metrics"
    assert analysis["monitoring"]["metrics_type"] == "prometheus"
