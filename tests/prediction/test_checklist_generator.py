"""Tests for checklist_generator"""

from prediction.checklist_generator import ChecklistGenerator
from prediction.models import PredictedIssue
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_ChecklistGenerator_generate_checklist():
    """Test ChecklistGenerator.generate_checklist"""
    generator = ChecklistGenerator()

    # Arrange
    subtask = {
        "id": "test-001",
        "description": "Add user authentication",
        "patterns_from": ["apps/backend/auth.py", "apps/backend/models.py"],
        "verification": {
            "type": "api",
            "method": "POST",
            "url": "/api/auth/login"
        }
    }

    predicted_issues = [
        PredictedIssue(
            category="security",
            description="Password hashing vulnerability",
            likelihood="high",
            prevention="Use bcrypt with proper salt rounds"
        ),
        PredictedIssue(
            category="edge_case",
            description="Null token handling",
            likelihood="medium",
            prevention="Add null checks before token validation"
        )
    ]

    known_patterns = [
        "Use bcrypt for password hashing",
        "Store tokens in HTTP-only cookies",
        "Implement rate limiting on auth endpoints"
    ]

    known_gotchas = [
        "Never log sensitive data",
        "Always validate token expiration",
        "Use HTTPS for all auth requests"
    ]

    # Act
    result = generator.generate_checklist(subtask, predicted_issues, known_patterns, known_gotchas)

    # Assert
    assert result is not None
    assert result.subtask_id == "test-001"
    assert result.subtask_description == "Add user authentication"
    assert len(result.predicted_issues) == 2
    assert result.predicted_issues[0].category == "security"
    assert result.predicted_issues[0].likelihood == "high"
    assert len(result.patterns_to_follow) <= 3  # Filtered to relevant
    assert result.files_to_reference == ["apps/backend/auth.py", "apps/backend/models.py"]
    assert len(result.common_mistakes) <= 3  # Filtered to relevant
    assert len(result.verification_reminders) > 0


def test_ChecklistGenerator_filter_relevant_patterns():
    """Test ChecklistGenerator._filter_relevant_patterns"""
    generator = ChecklistGenerator()

    subtask = {
        "id": "test-002",
        "description": "Add database migration for users table",
        "files_to_modify": ["apps/backend/models/user.py"]
    }

    patterns = [
        "Use Alembic for all database migrations",
        "Always add created_at and updated_at timestamps",
        "Add indexes on foreign keys",
        "Use bcrypt for password hashing"  # Not relevant
    ]

    # Act
    result = generator._filter_relevant_patterns(patterns, ["database"], subtask)

    # Assert
    assert len(result) > 0
    # Should include database-related patterns
    assert any("database" in p.lower() or "migration" in p.lower() or "alembic" in p.lower() for p in result)


def test_ChecklistGenerator_filter_relevant_gotchas():
    """Test ChecklistGenerator._filter_relevant_gotchas"""
    generator = ChecklistGenerator()

    subtask = {
        "id": "test-003",
        "description": "Implement user authentication"
    }

    gotchas = [
        "Never store plaintext passwords",
        "Always validate email format before saving",
        "Use transactions for multi-step database operations",
        "Remember to handle duplicate user errors"
    ]

    # Act
    result = generator._filter_relevant_gotchas(gotchas, ["api", "database"], subtask)

    # Assert
    # Should include gotchas related to authentication
    # "user" from description should match "duplicate user errors"
    # "database" work_type should match "database operations"
    assert len(result) > 0
    # At least "user" in "duplicate user errors" or "database" in "database operations" should match
    assert any("user" in g.lower() or "database" in g.lower() for g in result)


def test_ChecklistGenerator_filter_relevant_patterns_by_filename():
    """Test pattern filtering when pattern mentions a file being modified."""
    generator = ChecklistGenerator()

    subtask = {
        "id": "test-004",
        "description": "Update user functionality",
        "files_to_modify": ["apps/backend/models/user.py"]
    }

    patterns = [
        "When modifying user.py, remember to update related models",
        "For authentication changes, update auth.py as well",
        "Pattern mentioning database migrations",
    ]

    # Act - filter patterns for database work type
    result = generator._filter_relevant_patterns(patterns, ["database"], subtask)

    # Assert - should include pattern that mentions the file being modified
    assert len(result) > 0
    # The pattern that mentions "user.py" should be included
    assert any("user.py" in p.lower() for p in result)


def test_ChecklistGenerator_generate_verification_reminders():
    """Test ChecklistGenerator._generate_verification_reminders"""
    generator = ChecklistGenerator()

    # Test API verification
    subtask_api = {
        "id": "test-004",
        "verification": {
            "type": "api",
            "method": "POST",
            "url": "/api/users"
        }
    }

    result_api = generator._generate_verification_reminders(subtask_api)
    assert len(result_api) > 0
    assert "POST" in result_api[0]
    assert "/api/users" in result_api[0]

    # Test browser verification
    subtask_browser = {
        "id": "test-005",
        "verification": {
            "type": "browser",
            "scenario": "Click login button and verify redirect"
        }
    }

    result_browser = generator._generate_verification_reminders(subtask_browser)
    assert len(result_browser) > 0
    assert "browser" in result_browser[0].lower()

    # Test command verification
    subtask_command = {
        "id": "test-006",
        "verification": {
            "type": "command",
            "run": "pytest tests/test_auth.py"
        }
    }

    result_command = generator._generate_verification_reminders(subtask_command)
    assert len(result_command) > 0
    assert "pytest" in result_command[0]

    # Test e2e verification
    subtask_e2e = {
        "id": "test-007",
        "verification": {
            "type": "e2e",
            "steps": ["Open app", "Click login", "Enter credentials", "Verify dashboard"]
        }
    }

    result_e2e = generator._generate_verification_reminders(subtask_e2e)
    assert len(result_e2e) > 0
    assert "4 steps" in result_e2e[0]

    # Test none verification
    subtask_none = {
        "id": "test-008",
        "verification": {
            "type": "none"
        }
    }

    result_none = generator._generate_verification_reminders(subtask_none)
    assert len(result_none) == 0

    # Test e2e verification without steps
    subtask_e2e_no_steps = {
        "id": "test-009",
        "verification": {
            "type": "e2e",
            "steps": []
        }
    }

    result_e2e_no_steps = generator._generate_verification_reminders(subtask_e2e_no_steps)
    assert len(result_e2e_no_steps) == 1
    assert "E2E verification required" in result_e2e_no_steps[0]

    # Test manual verification
    subtask_manual = {
        "id": "test-010",
        "verification": {
            "type": "manual",
            "instructions": "Manually verify the user flow works correctly"
        }
    }

    result_manual = generator._generate_verification_reminders(subtask_manual)
    assert len(result_manual) == 1
    assert "Manually verify" in result_manual[0] or "Manual check" in result_manual[0]
    assert "user flow" in result_manual[0]
