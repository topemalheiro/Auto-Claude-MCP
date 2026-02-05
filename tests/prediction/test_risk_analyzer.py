"""Tests for risk_analyzer"""

from prediction.models import PredictedIssue
from prediction.patterns import get_common_issues
from prediction.risk_analyzer import RiskAnalyzer
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def default_common_issues():
    """Get the default common issues for testing."""
    return get_common_issues()


@pytest.fixture
def custom_common_issues():
    """Create custom common issues for testing."""
    return {
        "test_work": [
            PredictedIssue(
                "test_category",
                "Test issue description",
                "high",
                "Test prevention",
            ),
            PredictedIssue(
                "test_category_2",
                "Another test issue",
                "medium",
                "Another prevention",
            ),
        ],
        "another_type": [
            PredictedIssue(
                "security",
                "Security issue",
                "high",
                "Security prevention",
            ),
        ],
    }


def test_RiskAnalyzer_init_default(default_common_issues):
    """Test RiskAnalyzer initialization with default common issues."""
    analyzer = RiskAnalyzer()

    assert analyzer.common_issues is not None
    assert isinstance(analyzer.common_issues, dict)
    assert len(analyzer.common_issues) > 0


def test_RiskAnalyzer_init_custom(custom_common_issues):
    """Test RiskAnalyzer initialization with custom common issues."""
    analyzer = RiskAnalyzer(custom_common_issues)

    assert analyzer.common_issues == custom_common_issues
    assert "test_work" in analyzer.common_issues
    assert "another_type" in analyzer.common_issues


def test_RiskAnalyzer_init_none():
    """Test RiskAnalyzer initialization with None."""
    analyzer = RiskAnalyzer(None)

    assert analyzer.common_issues is not None
    assert len(analyzer.common_issues) > 0


def test_RiskAnalyzer_analyze_subtask_risks_api_endpoint():
    """Test risk analysis for API endpoint work type."""
    analyzer = RiskAnalyzer()

    subtask = {
        "id": "api-001",
        "description": "Add new user endpoint for creating users",
        "files_to_modify": ["apps/backend/api/users.py"],
        "service": "backend",
    }

    risks = analyzer.analyze_subtask_risks(subtask, None)

    assert len(risks) > 0
    assert all(isinstance(r, PredictedIssue) for r in risks)

    # Check for expected API-related risks
    categories = [r.category for r in risks]
    likelihoods = [r.likelihood for r in risks]

    # API endpoints should have security and integration issues
    assert "security" in categories or "integration" in categories

    # Check ordering - high likelihood should come first
    if len(risks) > 1:
        for i in range(len(risks) - 1):
            likelihood_order = {"high": 0, "medium": 1, "low": 2}
            current_order = likelihood_order.get(risks[i].likelihood, 3)
            next_order = likelihood_order.get(risks[i + 1].likelihood, 3)
            assert current_order <= next_order


def test_RiskAnalyzer_analyze_subtask_risks_database_model():
    """Test risk analysis for database model work type."""
    analyzer = RiskAnalyzer()

    subtask = {
        "id": "db-001",
        "description": "Create user model with authentication fields",
        "files_to_modify": ["apps/backend/models/user.py"],
        "service": "backend",
    }

    risks = analyzer.analyze_subtask_risks(subtask, None)

    assert len(risks) > 0

    # Check for expected database-related risks
    descriptions = [r.description.lower() for r in risks]
    assert any("migration" in d for d in descriptions)


def test_RiskAnalyzer_analyze_subtask_risks_frontend_component():
    """Test risk analysis for frontend component work type."""
    analyzer = RiskAnalyzer()

    subtask = {
        "id": "fe-001",
        "description": "Create user profile component",
        "files_to_modify": ["apps/frontend/components/UserProfile.tsx"],
        "service": "frontend",
    }

    risks = analyzer.analyze_subtask_risks(subtask, None)

    assert len(risks) > 0

    # Check for expected frontend-related risks
    categories = [r.category for r in risks]
    assert "edge_case" in categories  # Loading/error states


def test_RiskAnalyzer_analyze_subtask_risks_authentication():
    """Test risk analysis for authentication work type."""
    analyzer = RiskAnalyzer()

    subtask = {
        "id": "auth-001",
        "description": "Implement OAuth login flow",
        "files_to_modify": ["apps/backend/auth/oauth.py"],
        "service": "backend",
    }

    risks = analyzer.analyze_subtask_risks(subtask, None)

    assert len(risks) > 0

    # Authentication should have high-priority security issues
    security_risks = [r for r in risks if r.category == "security"]
    assert len(security_risks) > 0

    # Check for high likelihood
    high_risks = [r for r in security_risks if r.likelihood == "high"]
    assert len(high_risks) > 0


def test_RiskAnalyzer_analyze_subtask_risks_with_attempt_history():
    """Test risk analysis with historical attempt data."""
    analyzer = RiskAnalyzer()

    subtask = {
        "id": "api-002",
        "description": "Add user profile endpoint",
        "files_to_modify": ["apps/backend/api/profile.py"],
        "service": "backend",
    }

    attempt_history = [
        {
            "subtask_id": "api-001",
            "subtask_description": "Previous user endpoint implementation",
            "status": "failed",
            "error_message": "CORS configuration caused browser to block requests",
            "files_modified": ["apps/backend/api/users.py"],
        },
        {
            "subtask_id": "db-001",
            "subtask_description": "Some other task",
            "status": "failed",
            "error_message": "Database connection timeout",
            "files_modified": ["apps/backend/db.py"],
        },
    ]

    risks = analyzer.analyze_subtask_risks(subtask, attempt_history)

    assert len(risks) > 0

    # Should include pattern issues from similar failures
    pattern_issues = [r for r in risks if r.category == "pattern"]
    assert len(pattern_issues) > 0


def test_RiskAnalyzer_analyze_subtask_risks_empty_subtask():
    """Test risk analysis with empty subtask."""
    analyzer = RiskAnalyzer()

    subtask = {}
    risks = analyzer.analyze_subtask_risks(subtask, None)

    # Should return empty list or only general issues
    assert isinstance(risks, list)


def test_RiskAnalyzer_analyze_subtask_risks_deduplication():
    """Test that duplicate issues are removed."""
    custom_issues = {
        "api_endpoint": [
            PredictedIssue(
                "integration",
                "Duplicate issue description",
                "high",
                "Prevention 1",
            ),
            PredictedIssue(
                "security",
                "Different issue",
                "medium",
                "Prevention 2",
            ),
        ],
        "database_query": [
            PredictedIssue(
                "integration",
                "Duplicate issue description",  # Duplicate description
                "low",
                "Prevention 3",
            ),
        ],
    }

    analyzer = RiskAnalyzer(custom_issues)

    subtask = {
        "id": "test-001",
        "description": "Create API endpoint with database query",
        "files_to_modify": ["apps/backend/api/test.py"],
    }

    risks = analyzer.analyze_subtask_risks(subtask, None)

    # Check that duplicates are removed (by description)
    descriptions = [r.description for r in risks]
    assert descriptions.count("Duplicate issue description") == 1


def test_RiskAnalyzer_analyze_subtask_risks_max_limit():
    """Test that only top 7 most relevant issues are returned."""
    # Create a custom analyzer with many issues
    many_issues = {
        "test_type": [
            PredictedIssue(f"cat_{i}", f"Issue {i}", "medium", f"Prevention {i}")
            for i in range(20)
        ]
    }

    analyzer = RiskAnalyzer(many_issues)

    subtask = {
        "id": "test-001",
        "description": "test endpoint",
        "files_to_modify": ["test.py"],
    }

    # Mock detect_work_type to return our test type
    with patch("prediction.risk_analyzer.detect_work_type", return_value=["test_type"]):
        risks = analyzer.analyze_subtask_risks(subtask, None)

    # Should return at most 7 issues
    assert len(risks) <= 7


def test_RiskAnalyzer_find_similar_failures_no_history():
    """Test finding similar failures with no history."""
    analyzer = RiskAnalyzer()

    subtask = {
        "id": "test-001",
        "description": "Test subtask",
        "files_to_modify": ["test.py"],
    }

    similar = analyzer.find_similar_failures(subtask, [])

    assert similar == []


def test_RiskAnalyzer_find_similar_failures_none_history():
    """Test finding similar failures with None history."""
    analyzer = RiskAnalyzer()

    subtask = {
        "id": "test-001",
        "description": "Test subtask",
        "files_to_modify": ["test.py"],
    }

    similar = analyzer.find_similar_failures(subtask, None)

    assert similar == []


def test_RiskAnalyzer_find_similar_failures_by_description():
    """Test finding similar failures by description keywords."""
    analyzer = RiskAnalyzer()

    subtask = {
        "id": "auth-001",
        "description": "Implement OAuth authentication flow",
        "files_to_modify": ["apps/backend/auth.py"],
    }

    attempt_history = [
        {
            "subtask_id": "auth-002",
            "subtask_description": "Previous OAuth implementation with token refresh",
            "status": "failed",
            "error_message": "Token refresh failed due to expired secret",
            "files_modified": ["apps/backend/auth.py"],
        },
        {
            "subtask_id": "db-001",
            "subtask_description": "Unrelated database migration",
            "status": "failed",
            "error_message": "Migration conflict",
            "files_modified": ["alembic/versions/001.py"],
        },
    ]

    similar = analyzer.find_similar_failures(subtask, attempt_history)

    # Should find the OAuth-related failure
    assert len(similar) > 0
    assert any("OAuth" in str(s.get("description", "")) for s in similar)


def test_RiskAnalyzer_find_similar_failures_by_files():
    """Test finding similar failures by file overlap."""
    analyzer = RiskAnalyzer()

    subtask = {
        "id": "api-001",
        "description": "Some API work",
        "files_to_modify": ["apps/backend/api/users.py", "apps/backend/models/user.py"],
        "files_to_create": ["apps/backend/api/endpoints.py"],
    }

    attempt_history = [
        {
            "subtask_id": "api-002",
            "subtask_description": "Different description",
            "status": "failed",
            "error_message": "Import error in users module",
            "files_modified": ["apps/backend/api/users.py"],
        },
        {
            "subtask_id": "api-003",
            "subtask_description": "Another task",
            "status": "failed",
            "error_message": "Model validation error",
            "files_modified": ["apps/backend/models/user.py"],
        },
    ]

    similar = analyzer.find_similar_failures(subtask, attempt_history)

    # Should find both due to file overlap (stronger signal)
    assert len(similar) >= 1


def test_RiskAnalyzer_find_similar_failures_scoring():
    """Test that similarity scoring works correctly."""
    analyzer = RiskAnalyzer()

    subtask = {
        "id": "test-001",
        "description": "Implement user authentication with OAuth",
        "files_to_modify": ["apps/backend/auth.py"],
    }

    attempt_history = [
        {
            "subtask_id": "test-002",
            "subtask_description": "Implement user authentication with OAuth flow",
            "status": "failed",
            "error_message": "OAuth configuration error",
            "files_modified": ["apps/backend/auth.py"],
        },
        {
            "subtask_id": "test-003",
            "subtask_description": "User login endpoint",
            "status": "failed",
            "error_message": "Login validation failed",
            "files_modified": ["apps/backend/api/users.py"],
        },
    ]

    similar = analyzer.find_similar_failures(subtask, attempt_history)

    # First result should have higher similarity score (more keywords + file overlap)
    if len(similar) > 1:
        assert similar[0]["similarity_score"] >= similar[1]["similarity_score"]


def test_RiskAnalyzer_find_similar_failures_threshold():
    """Test that low-similarity failures are filtered out."""
    analyzer = RiskAnalyzer()

    subtask = {
        "id": "test-001",
        "description": "Implement file upload feature",
        "files_to_modify": ["apps/backend/upload.py"],
    }

    attempt_history = [
        {
            "subtask_id": "test-002",
            "subtask_description": "Database query optimization",
            "status": "failed",
            "error_message": "Query timeout",
            "files_modified": ["apps/backend/db.py"],
        },
    ]

    similar = analyzer.find_similar_failures(subtask, attempt_history)

    # Should not match due to low similarity
    assert len(similar) == 0


def test_RiskAnalyzer_find_similar_failures_max_results():
    """Test that at most 3 similar failures are returned."""
    analyzer = RiskAnalyzer()

    subtask = {
        "id": "api-001",
        "description": "Create user API endpoint",
        "files_to_modify": ["apps/backend/api/users.py"],
    }

    # Create more than 3 similar failures
    attempt_history = [
        {
            "subtask_id": f"api-{i:03d}",
            "subtask_description": f"User API endpoint iteration {i}",
            "status": "failed",
            "error_message": f"Error {i}",
            "files_modified": ["apps/backend/api/users.py"],
        }
        for i in range(1, 10)
    ]

    similar = analyzer.find_similar_failures(subtask, attempt_history)

    # Should return at most 3
    assert len(similar) <= 3


def test_RiskAnalyzer_find_similar_failures_ignores_success():
    """Test that successful attempts are ignored."""
    analyzer = RiskAnalyzer()

    subtask = {
        "id": "test-001",
        "description": "Implement authentication",
        "files_to_modify": ["apps/backend/auth.py"],
    }

    attempt_history = [
        {
            "subtask_id": "test-002",
            "subtask_description": "Previous authentication implementation",
            "status": "success",  # Should be ignored
            "error_message": "",
            "files_modified": ["apps/backend/auth.py"],
        },
        {
            "subtask_id": "test-003",
            "subtask_description": "Failed auth attempt",
            "status": "failed",
            "error_message": "Auth failed",
            "files_modified": ["apps/backend/auth.py"],
        },
    ]

    similar = analyzer.find_similar_failures(subtask, attempt_history)

    # Should only find the failed one
    assert len(similar) == 1
    assert similar[0]["subtask_id"] == "test-003"


def test_RiskAnalyzer_likelihood_sorting():
    """Test that issues are sorted by likelihood (high first)."""
    custom_issues = {
        "test_type": [
            PredictedIssue("low", "Low priority issue", "low", "Prevention"),
            PredictedIssue("high", "High priority issue", "high", "Prevention"),
            PredictedIssue("medium", "Medium priority issue", "medium", "Prevention"),
        ],
    }

    analyzer = RiskAnalyzer(custom_issues)

    subtask = {"id": "test-001", "description": "test work"}

    with patch("prediction.risk_analyzer.detect_work_type", return_value=["test_type"]):
        risks = analyzer.analyze_subtask_risks(subtask, None)

    # Check order: high, medium, low
    likelihoods = [r.likelihood for r in risks]
    assert likelihoods == ["high", "medium", "low"]


def test_RiskAnalyzer_no_work_type_detected():
    """Test behavior when no work type is detected."""
    analyzer = RiskAnalyzer()

    subtask = {
        "id": "test-001",
        "description": "Some generic task description",
        "files_to_modify": ["generic.py"],
    }

    with patch("prediction.risk_analyzer.detect_work_type", return_value=[]):
        risks = analyzer.analyze_subtask_risks(subtask, None)

    # Should return empty list when no work type is detected
    assert risks == []


def test_RiskAnalyzer_similar_failures_without_failure_reason():
    """Test handling of similar failures with empty failure_reason."""
    analyzer = RiskAnalyzer()

    subtask = {
        "id": "test-001",
        "description": "API endpoint work",
        "files_to_modify": ["api/users.py"],
    }

    attempt_history = [
        {
            "subtask_id": "old-001",
            "subtask_description": "API endpoint implementation",
            "status": "failed",
            "error_message": "",  # Empty error message
            "files_modified": ["api/users.py"],
        }
    ]

    risks = analyzer.analyze_subtask_risks(subtask, attempt_history)

    # Should not add issues for failures without reasons
    # May still have common issues for the work type
    assert all(isinstance(r, PredictedIssue) for r in risks)


def test_RiskAnalyzer_similar_failures_with_failure_reason():
    """Test handling of similar failures with actual failure_reason."""
    analyzer = RiskAnalyzer()

    subtask = {
        "id": "test-001",
        "description": "API endpoint work",
        "files_to_modify": ["api/users.py"],
    }

    attempt_history = [
        {
            "subtask_id": "old-001",
            "subtask_description": "API endpoint implementation",
            "status": "failed",
            "error_message": "CORS configuration blocked requests",  # Has failure reason
            "files_modified": ["api/users.py"],
        }
    ]

    risks = analyzer.analyze_subtask_risks(subtask, attempt_history)

    # Should add pattern issues for failures with reasons
    pattern_issues = [r for r in risks if r.category == "pattern"]
    assert len(pattern_issues) > 0
    assert any("CORS" in r.description or "blocked" in r.description for r in pattern_issues)
