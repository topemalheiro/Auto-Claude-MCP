"""Tests for jobs_detector"""

from analysis.analyzers.context.jobs_detector import JobsDetector
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_JobsDetector___init__():
    """Test JobsDetector.__init__"""
    path = Path("/tmp/test")
    analysis = {}

    detector = JobsDetector(path, analysis)

    assert detector.path == path.resolve()
    assert detector.analysis is analysis


@patch("analysis.analyzers.context.jobs_detector.JobsDetector._detect_celery")
def test_JobsDetector_detect(mock_detect_celery):
    """Test JobsDetector.detect"""
    mock_detect_celery.return_value = {"type": "celery", "tasks": ["task1", "task2"]}

    analysis = {}
    detector = JobsDetector(Path("/tmp/test"), analysis)
    detector.detect()

    assert "background_jobs" in analysis
    assert analysis["background_jobs"]["type"] == "celery"
