"""Tests for keyword_extractor"""

from context.keyword_extractor import KeywordExtractor
import pytest


def test_KeywordExtractor_extract_keywords():
    """Test KeywordExtractor.extract_keywords"""

    # Arrange
    task = "Add user authentication with JWT tokens to the API endpoint"

    # Act
    result = KeywordExtractor.extract_keywords(task, max_keywords=10)

    # Assert
    assert isinstance(result, list)
    assert "user" in result
    assert "authentication" in result
    assert "jwt" in result
    assert "tokens" in result
    assert "api" in result
    assert "endpoint" in result
    # Stopwords should be filtered out
    assert "add" not in result
    assert "to" not in result
    assert "the" not in result
    assert "with" not in result
