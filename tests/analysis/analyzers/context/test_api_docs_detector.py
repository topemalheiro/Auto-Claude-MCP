"""Tests for api_docs_detector"""

from analysis.analyzers.context.api_docs_detector import ApiDocsDetector
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_ApiDocsDetector___init__():
    """Test ApiDocsDetector.__init__"""
    path = Path("/tmp/test")
    analysis = {}

    detector = ApiDocsDetector(path, analysis)

    assert detector.path == path.resolve()
    assert detector.analysis is analysis


@patch("analysis.analyzers.context.api_docs_detector.BaseAnalyzer._exists")
@patch("analysis.analyzers.context.api_docs_detector.BaseAnalyzer._read_json")
def test_ApiDocsDetector_detect_fastapi(mock_read_json, mock_exists):
    """Test ApiDocsDetector.detect with FastAPI"""
    mock_exists.return_value = False  # No package.json
    analysis = {"framework": "FastAPI"}

    detector = ApiDocsDetector(Path("/tmp/test"), analysis)
    detector.detect()

    assert "api_documentation" in analysis
    assert analysis["api_documentation"]["type"] == "openapi"
    assert analysis["api_documentation"]["auto_generated"] is True


@patch("analysis.analyzers.context.api_docs_detector.BaseAnalyzer._exists")
@patch("analysis.analyzers.context.api_docs_detector.BaseAnalyzer._read_json")
def test_ApiDocsDetector_detect_swagger(mock_read_json, mock_exists):
    """Test ApiDocsDetector.detect with swagger-ui-express"""
    mock_exists.return_value = True
    mock_read_json.return_value = {
        "dependencies": {"swagger-ui-express": "^4.0.0"}
    }

    analysis = {}
    detector = ApiDocsDetector(Path("/tmp/test"), analysis)
    detector.detect()

    assert "api_documentation" in analysis
    assert analysis["api_documentation"]["type"] == "openapi"
    assert analysis["api_documentation"]["library"] == "swagger-ui-express"


@patch("analysis.analyzers.context.api_docs_detector.BaseAnalyzer._exists")
@patch("analysis.analyzers.context.api_docs_detector.BaseAnalyzer._read_json")
def test_ApiDocsDetector_detect_graphql(mock_read_json, mock_exists):
    """Test ApiDocsDetector.detect with graphql"""
    mock_exists.return_value = True
    mock_read_json.return_value = {
        "dependencies": {"graphql": "^16.0.0"}
    }

    analysis = {}
    detector = ApiDocsDetector(Path("/tmp/test"), analysis)
    detector.detect()

    assert "api_documentation" in analysis
    assert "graphql" in analysis["api_documentation"]


@patch("analysis.analyzers.context.api_docs_detector.BaseAnalyzer._exists")
@patch("analysis.analyzers.context.api_docs_detector.BaseAnalyzer._read_json")
def test_ApiDocsDetector_detect_none(mock_read_json, mock_exists):
    """Test ApiDocsDetector.detect with no API docs"""
    mock_exists.return_value = False

    analysis = {"framework": "Express"}
    detector = ApiDocsDetector(Path("/tmp/test"), analysis)
    detector.detect()

    assert "api_documentation" not in analysis
