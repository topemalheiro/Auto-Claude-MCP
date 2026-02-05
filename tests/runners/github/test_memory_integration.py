"""Tests for memory_integration"""

from runners.github.memory_integration import GitHubMemoryIntegration, ReviewContext, MemoryHint
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
import asyncio


def test_ReviewContext_to_prompt_section():
    """Test ReviewContext.to_prompt_section"""

    # Arrange - use correct MemoryHint constructor
    hints = [MemoryHint(hint_type="file_insight", content="Test insight for test.py", relevance_score=0.9)]
    instance = ReviewContext(
        file_insights=hints,
        similar_changes=[],
        gotchas=[],
        patterns=[],
        past_reviews=[]
    )

    # Act
    result = instance.to_prompt_section()

    # Assert
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_ReviewContext_has_context():
    """Test ReviewContext.has_context"""

    # Arrange - use correct MemoryHint constructor
    instance = ReviewContext(
        file_insights=[MemoryHint(hint_type="file_insight", content="Test", relevance_score=0.8)],
        similar_changes=[],
        gotchas=[],
        patterns=[],
        past_reviews=[]
    )

    # Assert - has_context should return True since we have file_insights
    assert instance.has_context is True

    # Test with empty context
    empty_instance = ReviewContext()
    assert empty_instance.has_context is False


def test_GitHubMemoryIntegration___init__():
    """Test GitHubMemoryIntegration.__init__"""

    # Arrange & Act
    repo = "owner/repo"
    state_dir = Path("/tmp/state")
    project_dir = Path("/tmp/project")
    instance = GitHubMemoryIntegration(repo, state_dir, project_dir)

    # Assert
    assert instance.repo == repo
    assert instance.state_dir == state_dir
    assert instance.project_dir == project_dir


def test_GitHubMemoryIntegration_get_review_context():
    """Test GitHubMemoryIntegration.get_review_context"""

    # Arrange
    instance = GitHubMemoryIntegration("owner/repo", None, None)

    file_paths = ["app/main.py"]
    change_description = "Fix bug in authentication"
    pr_number = 123

    # Act
    result = asyncio.run(instance.get_review_context(file_paths, change_description, pr_number))

    # Assert
    assert result is not None
    assert isinstance(result, ReviewContext)


def test_GitHubMemoryIntegration_store_review_insight():
    """Test GitHubMemoryIntegration.store_review_insight"""

    # Arrange
    instance = GitHubMemoryIntegration("owner/repo", None, None)

    # Act
    result = asyncio.run(instance.store_review_insight(
        pr_number=123,
        file_paths=["test.py"],
        insight="Missing error handling",
        category="error_handling",
        severity="medium"
    ))

    # Assert - should not raise exception even if memory is disabled
    assert result is None or result is True


def test_GitHubMemoryIntegration_store_review_outcome():
    """Test GitHubMemoryIntegration.store_review_outcome"""

    # Arrange
    instance = GitHubMemoryIntegration("owner/repo", None, None)

    # Act
    result = asyncio.run(instance.store_review_outcome(
        pr_number=123,
        prediction="needs_review",
        outcome="approved",
        was_correct=True,
        notes="Prediction was accurate"
    ))

    # Assert
    assert result is None or result is True


def test_GitHubMemoryIntegration_get_codebase_patterns():
    """Test GitHubMemoryIntegration.get_codebase_patterns"""

    # Arrange
    instance = GitHubMemoryIntegration("owner/repo", None, None)

    # Act
    result = asyncio.run(instance.get_codebase_patterns(area="authentication"))

    # Assert
    assert result is not None
    assert isinstance(result, list)


def test_GitHubMemoryIntegration_explain_finding():
    """Test GitHubMemoryIntegration.explain_finding"""

    # Arrange
    instance = GitHubMemoryIntegration("owner/repo", None, None)

    # Act - explain_finding may return None if memory is disabled
    result = asyncio.run(instance.explain_finding(
        finding_id="security-001",
        finding_description="SQL injection vulnerability",
        file_path="app/auth.py"
    ))

    # Assert - can be None if memory not available
    assert result is None or isinstance(result, str) or isinstance(result, dict)


def test_GitHubMemoryIntegration_close():
    """Test GitHubMemoryIntegration.close"""

    # Arrange
    instance = GitHubMemoryIntegration("owner/repo", None, None)

    # Act - close is async
    result = asyncio.run(instance.close())

    # Assert
    assert result is None


def test_GitHubMemoryIntegration_get_summary():
    """Test GitHubMemoryIntegration.get_summary"""

    # Arrange
    instance = GitHubMemoryIntegration("owner/repo", None, None)

    # Act
    result = instance.get_summary()

    # Assert
    assert result is not None
    assert isinstance(result, dict)
