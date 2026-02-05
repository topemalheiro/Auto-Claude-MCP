"""Tests for batch_validator"""

from runners.github.batch_validator import BatchValidationResult, BatchValidator, validate_batches
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import pytest


def test_BatchValidationResult_to_dict():
    """Test BatchValidationResult.to_dict"""

    # Arrange
    instance = BatchValidationResult(
        batch_id="test-batch",
        is_valid=True,
        confidence=0.95,
        reasoning="All issues are related",
        suggested_splits=None,
        common_theme="Authentication bugs"
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result == {
        "batch_id": "test-batch",
        "is_valid": True,
        "confidence": 0.95,
        "reasoning": "All issues are related",
        "suggested_splits": None,
        "common_theme": "Authentication bugs",
    }


def test_BatchValidator___init__():
    """Test BatchValidator.__init__"""

    # Arrange
    project_dir = Path("/tmp/test")
    model = "sonnet"
    thinking_budget = 20000

    # Act
    instance = BatchValidator(project_dir, model, thinking_budget)

    # Assert
    assert instance.project_dir == project_dir
    # Model gets resolved via resolve_model_id, so just check it's set
    assert instance.model is not None
    assert isinstance(instance.model, str)
    assert instance.thinking_budget == thinking_budget


def test_BatchValidator_validate_batch_single_issue():
    """Test BatchValidator.validate_batch with single issue (always valid)"""

    # Arrange
    project_dir = Path("/tmp/test")
    instance = BatchValidator(project_dir)

    # Act - should be synchronous for single issue
    import asyncio
    result = asyncio.run(instance.validate_batch(
        batch_id="single-batch",
        primary_issue=123,
        issues=[{"issue_number": 123, "title": "Test issue"}],
        themes=["bug"]
    ))

    # Assert
    assert result.is_valid is True
    assert result.confidence == 1.0
    assert "Single issue batch" in result.reasoning
    assert result.suggested_splits is None


def test_BatchValidator_format_issues():
    """Test BatchValidator._format_issues"""

    # Arrange
    instance = BatchValidator(Path("/tmp/test"))
    issues = [
        {
            "issue_number": 123,
            "title": "Bug in auth",
            "labels": ["bug", "auth"],
            "body": "Short body",
            "similarity_to_primary": 1.0
        },
        {
            "issue_number": 124,
            "title": "Another bug",
            "labels": [],
            "body": "x" * 600,  # Long body should be truncated
            "similarity_to_primary": 0.85
        }
    ]

    # Act
    result = instance._format_issues(issues)

    # Assert
    assert "Issue #123" in result
    assert "Bug in auth" in result
    assert "Issue #124" in result
    assert "..." in result  # Truncation marker
    assert "bug, auth" in result


def test_validate_batches():
    """Test validate_batches function"""

    # Arrange
    batches = [
        {
            "batch_id": "batch-1",
            "primary_issue": 123,
            "issues": [{"issue_number": 123, "title": "Single issue"}],
            "common_themes": ["bug"]
        },
        {
            "batch_id": "batch-2",
            "primary_issue": 124,
            "issues": [{"issue_number": 124, "title": "Another issue"}],
            "common_themes": ["feature"]
        }
    ]
    project_dir = Path("/tmp/test")

    # Act
    import asyncio
    results = asyncio.run(validate_batches(batches, project_dir))

    # Assert
    assert len(results) == 2
    assert all(isinstance(r, BatchValidationResult) for r in results)
    assert results[0].batch_id == "batch-1"
    assert results[1].batch_id == "batch-2"


def test_validate_batches_with_empty_inputs():
    """Test validate_batches with empty inputs"""

    # Arrange
    batches = []
    project_dir = Path("/tmp/test")

    # Act
    import asyncio
    results = asyncio.run(validate_batches(batches, project_dir))

    # Assert
    assert results == []


def test_validate_batches_with_invalid_input():
    """Test validate_batches handles exceptions gracefully"""

    # Arrange - batch with no primary_issue (will raise KeyError)
    # The function doesn't have explicit error handling, so we expect it to fail
    batches = [
        {
            "batch_id": "bad-batch",
            "issues": []
        }
    ]
    project_dir = Path("/tmp/test")

    # Act - should raise KeyError due to missing primary_issue
    import asyncio
    with pytest.raises(KeyError):
        results = asyncio.run(validate_batches(batches, project_dir))
