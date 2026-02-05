"""Tests for auth_detector"""

from analysis.analyzers.context.auth_detector import AuthDetector
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_AuthDetector___init__():
    """Test AuthDetector.__init__"""
    path = Path("/tmp/test")
    analysis = {}

    detector = AuthDetector(path, analysis)

    assert detector.path == path.resolve()
    assert detector.analysis is analysis


@patch("analysis.analyzers.context.auth_detector.BaseAnalyzer._exists")
@patch("analysis.analyzers.context.auth_detector.BaseAnalyzer._read_file")
@patch("analysis.analyzers.context.auth_detector.BaseAnalyzer._read_json")
def test_AuthDetector_detect_jwt(mock_read_json, mock_read_file, mock_exists):
    """Test AuthDetector.detect with JWT"""
    mock_exists.return_value = True
    mock_read_file.return_value = "pyjwt\nrequests\n"
    mock_read_json.return_value = None

    analysis = {}
    detector = AuthDetector(Path("/tmp/test"), analysis)
    detector.detect()

    assert "auth" in analysis
    assert "jwt" in analysis["auth"]["strategies"]


@patch("analysis.analyzers.context.auth_detector.BaseAnalyzer._exists")
@patch("analysis.analyzers.context.auth_detector.BaseAnalyzer._read_file")
@patch("analysis.analyzers.context.auth_detector.BaseAnalyzer._read_json")
def test_AuthDetector_detect_oauth(mock_read_json, mock_read_file, mock_exists):
    """Test AuthDetector.detect with OAuth"""
    mock_exists.return_value = True
    mock_read_file.return_value = ""
    mock_read_json.return_value = {
        "dependencies": {"authlib": "^1.0.0"}
    }

    analysis = {}
    detector = AuthDetector(Path("/tmp/test"), analysis)
    detector.detect()

    assert "auth" in analysis
    assert "oauth" in analysis["auth"]["strategies"]


@patch("analysis.analyzers.context.auth_detector.BaseAnalyzer._exists")
@patch("analysis.analyzers.context.auth_detector.BaseAnalyzer._read_file")
@patch("analysis.analyzers.context.auth_detector.BaseAnalyzer._read_json")
def test_AuthDetector_detect_none(mock_read_json, mock_read_file, mock_exists):
    """Test AuthDetector.detect with no auth"""
    mock_exists.return_value = False

    analysis = {}
    detector = AuthDetector(Path("/tmp/test"), analysis)
    detector.detect()

    assert "auth" not in analysis
