"""Tests for verification"""

from implementation_plan.verification import Verification
from implementation_plan.enums import VerificationType
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_Verification_to_dict():
    """Test Verification.to_dict"""

    # Arrange - COMMAND type verification
    instance = Verification(
        type=VerificationType.COMMAND,
        run="pytest tests/",
        url=None,
        method=None,
        expect_status=None,
        expect_contains=None,
        scenario=None
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result["type"] == "command"
    assert result["run"] == "pytest tests/"
    assert "url" not in result
    assert "method" not in result


def test_Verification_to_dict_api_test():
    """Test Verification.to_dict with API test"""

    # Arrange - API type verification
    instance = Verification(
        type=VerificationType.API,
        run=None,
        url="http://localhost:8000/api/test",
        method="GET",
        expect_status=200,
        expect_contains="success",
        scenario=None
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result["type"] == "api"
    assert result["url"] == "http://localhost:8000/api/test"
    assert result["method"] == "GET"
    assert result["expect_status"] == 200
    assert result["expect_contains"] == "success"
    assert "run" not in result
    assert "scenario" not in result


def test_Verification_to_dict_browser_test():
    """Test Verification.to_dict with browser test"""

    # Arrange - BROWSER type verification
    instance = Verification(
        type=VerificationType.BROWSER,
        run=None,
        url="http://localhost:3000",
        method=None,
        expect_status=None,
        expect_contains=None,
        scenario="Navigate to home page and verify title"
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result["type"] == "browser"
    assert result["url"] == "http://localhost:3000"
    assert result["scenario"] == "Navigate to home page and verify title"


def test_Verification_to_dict_manual_test():
    """Test Verification.to_dict with manual test"""

    # Arrange - MANUAL type verification
    instance = Verification(
        type=VerificationType.MANUAL,
        run=None,
        url=None,
        method=None,
        expect_status=None,
        expect_contains=None,
        scenario="Verify UI looks correct"
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result["type"] == "manual"
    assert result["scenario"] == "Verify UI looks correct"


def test_Verification_to_dict_component_test():
    """Test Verification.to_dict with component test"""

    # Arrange - COMPONENT type verification
    instance = Verification(
        type=VerificationType.COMPONENT,
        run="npm test -- component",
        scenario="Verify Button component renders"
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result["type"] == "component"
    assert result["run"] == "npm test -- component"
    assert result["scenario"] == "Verify Button component renders"


def test_Verification_to_dict_none_type():
    """Test Verification.to_dict with NONE type"""

    # Arrange - NONE type verification (minimal fields)
    instance = Verification(type=VerificationType.NONE)

    # Act
    result = instance.to_dict()

    # Assert
    assert result["type"] == "none"
    assert len(result) == 1  # Only type field


def test_Verification_from_dict():
    """Test Verification.from_dict"""

    # Arrange
    data = {
        "type": "command",
        "run": "npm test"
    }

    # Act
    result = Verification.from_dict(data)

    # Assert
    assert result.type == VerificationType.COMMAND
    assert result.run == "npm test"
    assert result.url is None
    assert result.method is None


def test_Verification_from_dict_api():
    """Test Verification.from_dict with API test"""

    # Arrange
    data = {
        "type": "api",
        "url": "http://localhost:8000/health",
        "method": "GET",
        "expect_status": 200,
        "expect_contains": "ok"
    }

    # Act
    result = Verification.from_dict(data)

    # Assert
    assert result.type == VerificationType.API
    assert result.url == "http://localhost:8000/health"
    assert result.method == "GET"
    assert result.expect_status == 200
    assert result.expect_contains == "ok"


def test_Verification_from_dict_browser():
    """Test Verification.from_dict with browser test"""

    # Arrange
    data = {
        "type": "browser",
        "url": "http://localhost:3000",
        "scenario": "Click login button and verify redirect"
    }

    # Act
    result = Verification.from_dict(data)

    # Assert
    assert result.type == VerificationType.BROWSER
    assert result.url == "http://localhost:3000"
    assert result.scenario == "Click login button and verify redirect"


def test_Verification_from_dict_manual():
    """Test Verification.from_dict with manual test"""

    # Arrange
    data = {
        "type": "manual",
        "scenario": "Check the UI matches the design mockup"
    }

    # Act
    result = Verification.from_dict(data)

    # Assert
    assert result.type == VerificationType.MANUAL
    assert result.scenario == "Check the UI matches the design mockup"


def test_Verification_from_dict_minimal():
    """Test Verification.from_dict with minimal data"""

    # Arrange - only type field
    data = {"type": "none"}

    # Act
    result = Verification.from_dict(data)

    # Assert
    assert result.type == VerificationType.NONE
    assert result.run is None
    assert result.url is None
    assert result.method is None
    assert result.expect_status is None
    assert result.expect_contains is None
    assert result.scenario is None


def test_Verification_from_dict_defaults_to_none():
    """Test Verification.from_dict defaults type to NONE"""

    # Arrange - missing type field
    data = {}

    # Act
    result = Verification.from_dict(data)

    # Assert
    assert result.type == VerificationType.NONE


def test_Verification_from_dict_component():
    """Test Verification.from_dict with component test"""

    # Arrange
    data = {
        "type": "component",
        "run": "npm test -- Button.test.tsx",
        "scenario": "Verify Button component renders correctly"
    }

    # Act
    result = Verification.from_dict(data)

    # Assert
    assert result.type == VerificationType.COMPONENT
    assert result.run == "npm test -- Button.test.tsx"
    assert result.scenario == "Verify Button component renders correctly"
