"""Tests for response_parsers"""

from runners.github.services.response_parsers import ResponseParser
from pathlib import Path
from unittest.mock import MagicMock
import pytest


def test_ResponseParser_parse_scan_result():
    """Test ResponseParser.parse_scan_result"""

    # Arrange
    response_text = '''
```json
{
    "purpose": "Test purpose",
    "actual_changes": "Test changes",
    "purpose_match": true,
    "risk_areas": ["Security"],
    "complexity": "low"
}
```
'''
    instance = ResponseParser()

    # Act
    result = instance.parse_scan_result(response_text)

    # Assert
    assert result is not None


def test_ResponseParser_parse_review_findings():
    """Test ResponseParser.parse_review_findings"""

    # Arrange
    response_text = '''
```json
[
    {
        "id": "finding-1",
        "severity": "high",
        "category": "security",
        "title": "Test finding",
        "description": "Test description",
        "file": "test.py",
        "line": 42
    }
]
```
'''
    instance = ResponseParser()
    require_evidence = True

    # Act
    result = instance.parse_review_findings(response_text, require_evidence)

    # Assert
    assert result is not None
    assert isinstance(result, list)


def test_ResponseParser_parse_structural_issues():
    """Test ResponseParser.parse_structural_issues"""

    # Arrange
    response_text = '''
```json
[
    {
        "id": "struct-1",
        "issue_type": "feature_creep",
        "severity": "medium",
        "title": "Test issue",
        "description": "Test description",
        "impact": "Test impact",
        "suggestion": "Test suggestion"
    }
]
```
'''
    instance = ResponseParser()

    # Act
    result = instance.parse_structural_issues(response_text)

    # Assert
    assert result is not None
    assert isinstance(result, list)


def test_ResponseParser_parse_ai_comment_triages():
    """Test ResponseParser.parse_ai_comment_triages"""

    # Arrange
    response_text = '''
```json
[
    {
        "comment_id": 123,
        "tool_name": "CodeRabbit",
        "original_summary": "Test summary",
        "verdict": "important",
        "reasoning": "Test reasoning",
        "response_comment": "Test response"
    }
]
```
'''
    instance = ResponseParser()

    # Act
    result = instance.parse_ai_comment_triages(response_text)

    # Assert
    assert result is not None
    assert isinstance(result, list)


def test_ResponseParser_parse_triage_result():
    """Test ResponseParser.parse_triage_result"""

    # Arrange
    issue = {"number": 123, "title": "Test issue"}
    response_text = '''
```json
{
    "category": "bug",
    "confidence": 0.9,
    "priority": "high",
    "labels_to_add": ["type:bug"],
    "is_duplicate": false,
    "is_spam": false
}
```
'''
    repo = "test/repo"
    instance = ResponseParser()

    # Act
    result = instance.parse_triage_result(issue, response_text, repo)

    # Assert
    assert result is not None
    assert result.issue_number == 123
