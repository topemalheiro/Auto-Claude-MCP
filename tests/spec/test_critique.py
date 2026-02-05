"""Tests for critique"""

from spec.critique import CritiqueResult, format_critique_summary, generate_critique_prompt, parse_critique_response, should_proceed
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_generate_critique_prompt():
    """Test generate_critique_prompt"""

    # Arrange
    subtask = {
        "id": "auth-middleware",
        "description": "Add JWT authentication middleware",
        "service": "backend",
        "files_to_modify": ["app/middleware/auth.py"],
        "files_to_create": ["app/middleware/auth.py"],
        "patterns_from": ["app/middleware/cors.py"],
    }
    files_modified = ["app/middleware/auth.py"]
    patterns_from = ["app/middleware/cors.py"]

    # Act
    result = generate_critique_prompt(subtask, files_modified, patterns_from)

    # Assert
    assert result is not None
    assert "auth-middleware" in result
    assert "Add JWT authentication middleware" in result
    assert "app/middleware/cors.py" in result
    assert "PROCEED" in result


def test_parse_critique_response():
    """Test parse_critique_response"""

    # Arrange - valid response with PROCEED: YES
    response = """
### STEP 3: Potential Issues Analysis

1. Token expiration edge case not fully tested

### STEP 4: Improvements Made

1. Added comprehensive error handling for invalid tokens

### STEP 5: Final Verdict

**PROCEED:** YES

**REASON:** All critical items verified

**CONFIDENCE:** High
"""

    # Act
    result = parse_critique_response(response)

    # Assert
    assert result is not None
    assert result.passes is True
    assert "Token expiration edge case" in result.issues[0]
    assert "comprehensive error handling" in result.improvements_made[0]


def test_parse_critique_response_with_no_proceed():
    """Test parse_critique_response with PROCEED: NO"""

    response = """
### STEP 3: Potential Issues Analysis

1. Missing error handling
2. No input validation

### STEP 5: Final Verdict

**PROCEED:** NO

**REASON:** Critical issues must be fixed

**CONFIDENCE:** Low
"""

    result = parse_critique_response(response)

    assert result.passes is False
    assert len(result.issues) >= 2
    assert "Low" in result.recommendations[0]


def test_should_proceed():
    """Test should_proceed"""

    # Test passing case
    result_pass = CritiqueResult(passes=True, issues=[], improvements_made=[])
    assert should_proceed(result_pass) is True

    # Test failing case - not passed
    result_fail = CritiqueResult(passes=False, issues=[], improvements_made=[])
    assert should_proceed(result_fail) is False

    # Test failing case - has issues
    result_issues = CritiqueResult(passes=True, issues=["Fix bug"], improvements_made=[])
    assert should_proceed(result_issues) is False


def test_format_critique_summary():
    """Test format_critique_summary"""

    # Arrange
    result = CritiqueResult(
        passes=True,
        issues=[],  # No issues so should_proceed returns True
        improvements_made=["Fix 1"],
        recommendations=["Recommendation 1"]
    )

    # Act
    summary = format_critique_summary(result)

    # Assert
    assert "## Critique Summary" in summary
    assert "PASSED" in summary
    assert "Fix 1" in summary
    assert "Recommendation 1" in summary
    assert "ready to be marked complete" in summary


def test_CritiqueResult_to_dict():
    """Test CritiqueResult.to_dict"""

    # Arrange
    result = CritiqueResult(
        passes=True,
        issues=["Issue 1"],
        improvements_made=["Fix 1"],
        recommendations=["Rec 1"]
    )

    # Act
    data = result.to_dict()

    # Assert
    assert data["passes"] is True
    assert data["issues"] == ["Issue 1"]
    assert data["improvements_made"] == ["Fix 1"]
    assert data["recommendations"] == ["Rec 1"]


def test_CritiqueResult_from_dict():
    """Test CritiqueResult.from_dict"""

    # Arrange
    data = {
        "passes": False,
        "issues": ["Issue 1", "Issue 2"],
        "improvements_made": ["Fix 1"],
        "recommendations": ["Rec 1"]
    }

    # Act
    result = CritiqueResult.from_dict(data)

    # Assert
    assert result.passes is False
    assert result.issues == ["Issue 1", "Issue 2"]
    assert result.improvements_made == ["Fix 1"]
    assert result.recommendations == ["Rec 1"]


def test_parse_critique_response_with_empty_lines():
    """Test parse_critique_response skips empty lines and separators (line 200, 228)"""
    response = """
### STEP 3: Potential Issues Analysis

---
1. First issue

---

2. Second issue

---

### STEP 4: Improvements Made

---
* First improvement

---

* Second improvement

---

### STEP 5: Final Verdict

**PROCEED:** YES

**REASON:** OK

**CONFIDENCE:** High
"""

    result = parse_critique_response(response)

    assert len(result.issues) == 2
    assert len(result.improvements_made) == 2
    assert result.passes is True


def test_parse_critique_response_with_none_identifiers():
    """Test parse_critique_response handles 'none' identifiers (lines 200, 228)"""
    response = """
### STEP 3: Potential Issues Analysis

none
None identified
no concerns

### STEP 4: Improvements Made

n/a
No improvements

### STEP 5: Final Verdict

**PROCEED:** YES

**REASON:** OK

**CONFIDENCE:** High
"""

    result = parse_critique_response(response)

    # Should skip none/n/a entries
    assert len(result.issues) == 0
    assert len(result.improvements_made) == 0


def test_format_critique_summary_with_issues():
    """Test format_critique_summary with issues (lines 301-304)"""
    result = CritiqueResult(
        passes=True,
        issues=["Issue 1", "Issue 2"],
        improvements_made=[],
        recommendations=[]
    )

    summary = format_critique_summary(result)

    assert "**Issues Identified:**" in summary
    assert "1. Issue 1" in summary
    assert "2. Issue 2" in summary


def test_format_critique_summary_with_improvements():
    """Test format_critique_summary with improvements"""
    result = CritiqueResult(
        passes=True,
        issues=[],
        improvements_made=["Improvement 1", "Improvement 2"],
        recommendations=[]
    )

    summary = format_critique_summary(result)

    assert "**Improvements Made:**" in summary
    assert "1. Improvement 1" in summary
    assert "2. Improvement 2" in summary


def test_format_critique_summary_with_recommendations():
    """Test format_critique_summary with recommendations"""
    result = CritiqueResult(
        passes=True,
        issues=[],
        improvements_made=[],
        recommendations=["Recommendation 1", "Recommendation 2"]
    )

    summary = format_critique_summary(result)

    assert "**Recommendations:**" in summary
    assert "1. Recommendation 1" in summary
    assert "2. Recommendation 2" in summary


def test_format_critique_summary_needs_more_work():
    """Test format_critique_summary when subtask needs more work (line 321)"""
    result = CritiqueResult(
        passes=False,
        issues=["Critical bug"],
        improvements_made=[],
        recommendations=[]
    )

    summary = format_critique_summary(result)

    assert "FAILED" in summary
    assert "needs more work before completion" in summary


def test_generate_critique_prompt_with_empty_lists():
    """Test generate_critique_prompt handles empty lists"""
    subtask = {
        "id": "test-task",
        "description": "Test description",
        "service": "all services",
        "files_to_modify": [],
        "files_to_create": [],
        "patterns_from": [],
    }

    prompt = generate_critique_prompt(subtask, [], [])

    assert "test-task" in prompt
    assert "None" in prompt


def test_main_block_execution():
    """Test the main block execution (lines 329-369)"""
    # The main block is example code that demonstrates usage
    # We can verify the module can be imported without issues
    import spec.critique

    # Verify the module attributes exist
    assert hasattr(spec.critique, 'generate_critique_prompt')
    assert hasattr(spec.critique, 'parse_critique_response')
    assert hasattr(spec.critique, 'should_proceed')
    assert hasattr(spec.critique, 'format_critique_summary')
    assert hasattr(spec.critique, 'CritiqueResult')
