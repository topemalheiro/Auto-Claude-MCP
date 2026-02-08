"""Tests for port_detector"""

from pathlib import Path

from analysis.analyzers.port_detector import PortDetector


def test_PortDetector___init__():
    """Test PortDetector.__init__"""

    # Act - Constructor called during instantiation
    PortDetector(Path("/tmp/test"), {})

    # Assert
    assert True  # Function runs without error

def test_PortDetector_detect_port_from_sources():
    """Test PortDetector.detect_port_from_sources"""

    # Arrange
    instance = PortDetector(Path("/tmp/test"), {})
    default_port = 8000

    # Act
    _ = instance.detect_port_from_sources(default_port)

    # Assert
    # /tmp/test has no port configuration, should return default
    assert result == default_port
