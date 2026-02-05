"""Tests for prompt_manager"""

from runners.github.services.prompt_manager import PromptManager
from runners.github.models import ReviewPass
from pathlib import Path
from unittest.mock import MagicMock
import pytest


def test_PromptManager___init__():
    """Test PromptManager.__init__"""

    # Arrange
    prompts_dir = None

    # Act
    instance = PromptManager(prompts_dir)

    # Assert
    assert instance is not None
    assert instance.prompts_dir is not None


def test_PromptManager_get_review_pass_prompt():
    """Test PromptManager.get_review_pass_prompt"""

    # Arrange
    instance = PromptManager()
    review_pass = ReviewPass.SECURITY

    # Act
    result = instance.get_review_pass_prompt(review_pass)

    # Assert
    assert result is not None
    assert isinstance(result, str)
    assert "security" in result.lower() or "vulnerabilities" in result.lower()


def test_PromptManager_get_pr_review_prompt():
    """Test PromptManager.get_pr_review_prompt"""

    # Arrange
    instance = PromptManager()

    # Act
    result = instance.get_pr_review_prompt()

    # Assert
    assert result is not None
    assert isinstance(result, str)


def test_PromptManager_get_followup_review_prompt():
    """Test PromptManager.get_followup_review_prompt"""

    # Arrange
    instance = PromptManager()

    # Act
    result = instance.get_followup_review_prompt()

    # Assert
    assert result is not None
    assert isinstance(result, str)


def test_PromptManager_get_triage_prompt():
    """Test PromptManager.get_triage_prompt"""

    # Arrange
    instance = PromptManager()

    # Act
    result = instance.get_triage_prompt()

    # Assert
    assert result is not None
    assert isinstance(result, str)
