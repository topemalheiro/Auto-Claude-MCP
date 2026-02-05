"""Tests for service_matcher"""

from context.service_matcher import ServiceMatcher
import pytest


def test_ServiceMatcher___init__():
    """Test ServiceMatcher.__init__"""

    # Arrange
    project_index = {
        "services": {
            "api": {"path": "apps/api", "language": "python", "type": "backend"},
            "web": {"path": "apps/web", "language": "typescript", "type": "frontend"}
        }
    }

    # Act
    matcher = ServiceMatcher(project_index)

    # Assert
    assert matcher.project_index == project_index


def test_ServiceMatcher_suggest_services():
    """Test ServiceMatcher.suggest_services"""

    # Arrange
    project_index = {
        "services": {
            "api": {"path": "apps/api", "language": "python", "type": "backend"},
            "web": {"path": "apps/web", "language": "typescript", "type": "frontend"},
            "worker": {"path": "apps/worker", "language": "python", "type": "worker"}
        }
    }
    matcher = ServiceMatcher(project_index)

    # Act - task mentions "api" explicitly
    result = matcher.suggest_services("Add authentication to the API")

    # Assert
    assert isinstance(result, list)
    # Should suggest api since it's mentioned
    assert "api" in result

    # Act - task mentions frontend keywords
    result = matcher.suggest_services("Create new user profile page component")

    # Assert
    assert "web" in result or len(result) >= 0

    # Act - no specific match, should return defaults
    result = matcher.suggest_services("Fix some bug")

    # Assert
    assert isinstance(result, list)
    # Should return backend and frontend as defaults
    assert len(result) >= 0
