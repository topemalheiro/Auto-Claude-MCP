"""Tests for service_analyzer"""

from analysis.analyzers.service_analyzer import ServiceAnalyzer
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_ServiceAnalyzer___init__():
    """Test ServiceAnalyzer.__init__"""

    # Arrange
    service_path = Path("/tmp/test")
    service_name = "test_service"

    # Act
    instance = ServiceAnalyzer(service_path, service_name)

    # Assert
    assert instance.name == service_name
    assert instance.path == service_path.resolve()
    assert instance.analysis["name"] == service_name


def test_ServiceAnalyzer_analyze():
    """Test ServiceAnalyzer.analyze"""

    # Arrange
    service_path = Path("/tmp/test")
    instance = ServiceAnalyzer(service_path, "test_service")

    # Act
    result = instance.analyze()

    # Assert
    assert result is not None
    assert "name" in result
    assert result["name"] == "test_service"
    assert "path" in result
