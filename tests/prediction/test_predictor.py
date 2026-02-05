"""Tests for predictor"""

from prediction.predictor import BugPredictor
from prediction.models import PreImplementationChecklist, PredictedIssue
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_BugPredictor___init__():
    """Test BugPredictor.__init__"""
    spec_dir = Path("/tmp/test")

    instance = BugPredictor(spec_dir)

    assert instance.spec_dir == spec_dir
    assert instance.memory_dir == spec_dir / "memory"
    assert instance.memory_loader is not None
    assert instance.risk_analyzer is not None
    assert instance.checklist_generator is not None
    assert instance.formatter is not None


def test_BugPredictor_generate_checklist():
    """Test BugPredictor.generate_checklist"""
    spec_dir = Path("/tmp/test")
    subtask = {
        "id": "subtask-001",
        "description": "Add user authentication",
        "patterns_from": ["apps/backend/auth.py"],
        "verification": {"type": "api", "method": "POST", "url": "/api/auth"}
    }

    instance = BugPredictor(spec_dir)

    # Mock the memory_loader methods
    instance.memory_loader.load_attempt_history = MagicMock(return_value=[])
    instance.memory_loader.load_patterns = MagicMock(return_value=[])
    instance.memory_loader.load_gotchas = MagicMock(return_value=[])

    # Mock the risk_analyzer
    instance.risk_analyzer.analyze_subtask_risks = MagicMock(return_value=[])

    # Mock the checklist_generator
    expected_checklist = PreImplementationChecklist(
        subtask_id="subtask-001",
        subtask_description="Add user authentication"
    )
    instance.checklist_generator.generate_checklist = MagicMock(return_value=expected_checklist)

    result = instance.generate_checklist(subtask)

    assert result is not None
    assert result.subtask_id == "subtask-001"
    assert result.subtask_description == "Add user authentication"


def test_BugPredictor_format_checklist_markdown():
    """Test BugPredictor.format_checklist_markdown"""
    spec_dir = Path("/tmp/test")

    # Create a proper checklist object
    checklist = PreImplementationChecklist(
        subtask_id="test-001",
        subtask_description="Add user authentication",
        predicted_issues=[
            PredictedIssue(
                category="security",
                description="Password hashing",
                likelihood="high",
                prevention="Use bcrypt"
            )
        ],
        patterns_to_follow=["Use bcrypt", "Validate input"],
        files_to_reference=["apps/backend/auth.py"],
        common_mistakes=["Never log passwords"],
        verification_reminders=["Test API endpoint: POST /api/auth/login"]
    )

    instance = BugPredictor(spec_dir)

    result = instance.format_checklist_markdown(checklist)

    assert result is not None
    assert "Pre-Implementation Checklist" in result
    assert "Add user authentication" in result
    assert "Predicted Issues" in result
    assert "Password hashing" in result
    assert "Use bcrypt" in result
    assert "Never log passwords" in result
    assert "POST /api/auth/login" in result


def test_BugPredictor_format_checklist_markdown_empty():
    """Test BugPredictor.format_checklist_markdown with minimal checklist"""
    spec_dir = Path("/tmp/test")

    checklist = PreImplementationChecklist(
        subtask_id="test-002",
        subtask_description="Simple task"
    )

    instance = BugPredictor(spec_dir)

    result = instance.format_checklist_markdown(checklist)

    assert result is not None
    assert "Pre-Implementation Checklist" in result
    assert "Simple task" in result
    assert "Before You Start Implementing" in result


def test_BugPredictor_load_known_gotchas():
    """Test BugPredictor.load_known_gotchas"""
    spec_dir = Path("/tmp/test")
    instance = BugPredictor(spec_dir)

    # Mock the memory_loader
    expected_gotchas = ["Never log sensitive data", "Always validate input"]
    instance.memory_loader.load_gotchas = MagicMock(return_value=expected_gotchas)

    result = instance.load_known_gotchas()

    assert result == expected_gotchas
    instance.memory_loader.load_gotchas.assert_called_once()


def test_BugPredictor_load_known_patterns():
    """Test BugPredictor.load_known_patterns"""
    spec_dir = Path("/tmp/test")
    instance = BugPredictor(spec_dir)

    # Mock the memory_loader
    expected_patterns = ["Use async/await for I/O", "Add type hints"]
    instance.memory_loader.load_patterns = MagicMock(return_value=expected_patterns)

    result = instance.load_known_patterns()

    assert result == expected_patterns
    instance.memory_loader.load_patterns.assert_called_once()


def test_BugPredictor_load_attempt_history():
    """Test BugPredictor.load_attempt_history"""
    spec_dir = Path("/tmp/test")
    instance = BugPredictor(spec_dir)

    # Mock the memory_loader
    expected_history = [
        {"subtask_id": "old-001", "description": "Auth", "success": False, "error": "Token validation failed"}
    ]
    instance.memory_loader.load_attempt_history = MagicMock(return_value=expected_history)

    result = instance.load_attempt_history()

    assert result == expected_history
    instance.memory_loader.load_attempt_history.assert_called_once()


def test_BugPredictor_analyze_subtask_risks():
    """Test BugPredictor.analyze_subtask_risks"""
    spec_dir = Path("/tmp/test")
    subtask = {
        "id": "test-003",
        "description": "Implement OAuth flow",
        "files_to_modify": ["apps/backend/auth.py"]
    }

    instance = BugPredictor(spec_dir)

    # Mock the memory_loader and risk_analyzer
    instance.memory_loader.load_attempt_history = MagicMock(return_value=[])
    expected_issues = [
        PredictedIssue(
            category="security",
            description="CSRF vulnerability",
            likelihood="high",
            prevention="Use state parameter"
        )
    ]
    instance.risk_analyzer.analyze_subtask_risks = MagicMock(return_value=expected_issues)

    result = instance.analyze_subtask_risks(subtask)

    assert result == expected_issues
    instance.risk_analyzer.analyze_subtask_risks.assert_called_once_with(subtask, [])


def test_BugPredictor_get_similar_past_failures():
    """Test BugPredictor.get_similar_past_failures"""
    spec_dir = Path("/tmp/test")
    subtask = {
        "id": "test-004",
        "description": "Add rate limiting",
        "files_to_modify": ["apps/backend/middleware.py"]
    }

    instance = BugPredictor(spec_dir)

    # Mock the memory_loader and risk_analyzer
    past_failures = [
        {"subtask_id": "old-002", "description": "Rate limiting", "error": "Redis connection timeout"}
    ]
    instance.memory_loader.load_attempt_history = MagicMock(return_value=past_failures)
    instance.risk_analyzer.find_similar_failures = MagicMock(return_value=past_failures)

    result = instance.get_similar_past_failures(subtask)

    assert result == past_failures
    instance.risk_analyzer.find_similar_failures.assert_called_once_with(subtask, past_failures)
