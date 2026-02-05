"""Tests for prediction.patterns module."""

import pytest

from prediction.models import PredictedIssue
from prediction.patterns import detect_work_type, get_common_issues


class TestGetCommonIssues:
    """Tests for get_common_issues function."""

    def test_returns_dict(self):
        """Test that get_common_issues returns a dictionary."""
        result = get_common_issues()
        assert isinstance(result, dict)

    def test_has_expected_work_types(self):
        """Test that expected work types are present."""
        result = get_common_issues()
        expected_types = [
            "api_endpoint",
            "database_model",
            "frontend_component",
            "celery_task",
            "authentication",
            "database_query",
            "file_upload",
        ]
        for work_type in expected_types:
            assert work_type in result

    def test_all_values_are_lists_of_predicted_issues(self):
        """Test that all values are lists of PredictedIssue objects."""
        result = get_common_issues()
        for work_type, issues in result.items():
            assert isinstance(issues, list)
            for issue in issues:
                assert isinstance(issue, PredictedIssue)

    def test_api_endpoint_issues_structure(self):
        """Test API endpoint issues have correct structure."""
        result = get_common_issues()
        api_issues = result["api_endpoint"]
        assert len(api_issues) > 0

        for issue in api_issues:
            assert isinstance(issue.category, str)
            assert isinstance(issue.description, str)
            assert isinstance(issue.likelihood, str)
            assert isinstance(issue.prevention, str)

    def test_api_endpoint_includes_cors_issue(self):
        """Test that API endpoint includes CORS issue."""
        result = get_common_issues()
        api_issues = result["api_endpoint"]
        categories = [issue.category for issue in api_issues]
        assert "integration" in categories
        descriptions = [issue.description for issue in api_issues]
        assert any("CORS" in desc for desc in descriptions)

    def test_api_endpoint_includes_auth_issue(self):
        """Test that API endpoint includes auth middleware issue."""
        result = get_common_issues()
        api_issues = result["api_endpoint"]
        descriptions = [issue.description for issue in api_issues]
        assert any("Authentication" in desc for desc in descriptions)

    def test_database_model_issues(self):
        """Test database model issues."""
        result = get_common_issues()
        db_issues = result["database_model"]
        assert len(db_issues) > 0
        descriptions = [issue.description for issue in db_issues]
        assert any("migration" in desc.lower() for desc in descriptions)

    def test_frontend_component_issues(self):
        """Test frontend component issues."""
        result = get_common_issues()
        frontend_issues = result["frontend_component"]
        assert len(frontend_issues) > 0

        # Should include API client issue
        descriptions = [issue.description for issue in frontend_issues]
        assert any("API client" in desc for desc in descriptions)

    def test_celery_task_issues(self):
        """Test Celery task issues."""
        result = get_common_issues()
        celery_issues = result["celery_task"]
        assert len(celery_issues) > 0

        # Should include registration issue
        descriptions = [issue.description for issue in celery_issues]
        assert any("registered" in desc.lower() for desc in descriptions)

    def test_authentication_issues(self):
        """Test authentication issues."""
        result = get_common_issues()
        auth_issues = result["authentication"]
        assert len(auth_issues) > 0

        # Should include password hashing
        descriptions = [issue.description for issue in auth_issues]
        assert any("password" in desc.lower() for desc in descriptions)

        # All should be security category
        categories = [issue.category for issue in auth_issues]
        assert all(cat == "security" for cat in categories)

    def test_database_query_issues(self):
        """Test database query issues."""
        result = get_common_issues()
        query_issues = result["database_query"]
        assert len(query_issues) > 0

        # Should include N+1 and SQL injection
        descriptions = [issue.description for issue in query_issues]
        assert any("N+1" in desc or "n+1" in desc for desc in descriptions)
        assert any("SQL injection" in desc for desc in descriptions)

    def test_file_upload_issues(self):
        """Test file upload issues."""
        result = get_common_issues()
        upload_issues = result["file_upload"]
        assert len(upload_issues) > 0

        # Should include file type and size validation
        descriptions = [issue.description for issue in upload_issues]
        assert any("File type" in desc for desc in descriptions)
        assert any("File size" in desc for desc in descriptions)


class TestDetectWorkType:
    """Tests for detect_work_type function."""

    def test_returns_list(self):
        """Test that detect_work_type returns a list."""
        subtask = {"description": "Add endpoint"}
        result = detect_work_type(subtask)
        assert isinstance(result, list)

    def test_detect_api_endpoint_from_keywords(self):
        """Test detecting API endpoint from description keywords."""
        test_cases = [
            "Create a new API endpoint",
            "Add route for user data",
            "Implement request handler",
            "Update response format",
        ]
        for description in test_cases:
            subtask = {"description": description}
            result = detect_work_type(subtask)
            assert "api_endpoint" in result, f"Failed for: {description}"

    def test_detect_api_endpoint_from_files(self):
        """Test detecting API endpoint from file paths."""
        subtask = {
            "description": "Update user handler",
            "files_to_modify": ["api/routes.py", "api/handlers.py"],
        }
        result = detect_work_type(subtask)
        assert "api_endpoint" in result

    def test_detect_database_model_from_keywords(self):
        """Test detecting database model from description keywords."""
        test_cases = [
            "Create user model",
            "Add database migration",
            "Update schema",
        ]
        for description in test_cases:
            subtask = {"description": description}
            result = detect_work_type(subtask)
            assert "database_model" in result, f"Failed for: {description}"

    def test_detect_database_model_from_files(self):
        """Test detecting database model from file paths."""
        subtask = {
            "description": "Add user table",
            "files_to_modify": ["models/user.py"],
        }
        result = detect_work_type(subtask)
        assert "database_model" in result

    def test_detect_frontend_component_from_service(self):
        """Test detecting frontend component from service field."""
        subtask = {
            "description": "Add login form",
            "service": "frontend",
        }
        result = detect_work_type(subtask)
        assert "frontend_component" in result

    def test_detect_frontend_component_from_files(self):
        """Test detecting frontend component from file extensions."""
        subtask = {
            "description": "Update component",
            "files_to_create": ["components/Login.tsx"],
        }
        result = detect_work_type(subtask)
        assert "frontend_component" in result

    def test_detect_vue_component(self):
        """Test detecting Vue component."""
        subtask = {
            "description": "Create user card",
            "files_to_create": ["components/UserCard.vue"],
        }
        result = detect_work_type(subtask)
        assert "frontend_component" in result

    def test_detect_svelte_component(self):
        """Test detecting Svelte component."""
        subtask = {
            "description": "Create button",
            "files_to_create": ["components/Button.svelte"],
        }
        result = detect_work_type(subtask)
        assert "frontend_component" in result

    def test_detect_celery_task_from_keywords(self):
        """Test detecting Celery task from description."""
        subtask = {"description": "Create celery task for email"}
        result = detect_work_type(subtask)
        assert "celery_task" in result

    def test_detect_celery_task_from_service(self):
        """Test detecting Celery task from service field."""
        subtask = {
            "description": "Background job",
            "service": "worker",
        }
        result = detect_work_type(subtask)
        assert "celery_task" in result

    def test_detect_authentication_from_keywords(self):
        """Test detecting authentication from description."""
        keywords = ["auth", "login", "password", "token", "session"]
        for keyword in keywords:
            subtask = {"description": f"Add {keyword} functionality"}
            result = detect_work_type(subtask)
            assert "authentication" in result, f"Failed for keyword: {keyword}"

    def test_detect_database_query_from_keywords(self):
        """Test detecting database query from description."""
        subtask = {"description": "Create search query"}
        result = detect_work_type(subtask)
        assert "database_query" in result

    def test_detect_file_upload_from_keywords(self):
        """Test detecting file upload from description."""
        subtask = {"description": "Add image upload"}
        result = detect_work_type(subtask)
        assert "file_upload" in result

    def test_detect_multiple_work_types(self):
        """Test detecting multiple work types from single subtask."""
        subtask = {
            "description": "Create API endpoint for user authentication with file upload",
            "files_to_modify": ["api/routes.py"],
            "service": "frontend",
        }
        result = detect_work_type(subtask)
        assert "api_endpoint" in result
        assert "authentication" in result
        assert "file_upload" in result

    def test_no_work_type_detected(self):
        """Test subtask that doesn't match any work type."""
        subtask = {
            "description": "Update documentation",
            "files_to_modify": ["docs/README.md"],
        }
        result = detect_work_type(subtask)
        # Should return empty list if nothing matches
        assert result == []

    def test_case_insensitive_detection(self):
        """Test that detection is case insensitive."""
        subtask = {"description": "Create API ENDPOINT for User AUTH"}
        result = detect_work_type(subtask)
        assert "api_endpoint" in result
        assert "authentication" in result

    def test_detection_with_files_to_create(self):
        """Test detection using files_to_create field."""
        subtask = {
            "description": "Add feature",
            "files_to_create": ["api/users.py"],
        }
        result = detect_work_type(subtask)
        assert "api_endpoint" in result

    def test_detection_with_combined_file_lists(self):
        """Test detection combining files_to_modify and files_to_create."""
        subtask = {
            "description": "Update feature",
            "files_to_modify": ["models/base.py"],
            "files_to_create": ["models/user.py"],
        }
        result = detect_work_type(subtask)
        assert "database_model" in result

    def test_detects_api_from_both_files_and_description(self):
        """Test that API can be detected from both files and description."""
        subtask = {
            "description": "Update routes",
            "files_to_modify": ["api/users.py"],
        }
        result = detect_work_type(subtask)
        # API endpoint should be detected (may appear multiple times since implementation appends)
        assert "api_endpoint" in result
        assert len(result) >= 1

    def test_empty_subtask(self):
        """Test handling of empty subtask dictionary."""
        subtask = {}
        result = detect_work_type(subtask)
        assert result == []

    def test_subtask_with_missing_fields(self):
        """Test handling of subtask with missing optional fields."""
        subtask = {"description": "Add endpoint"}
        result = detect_work_type(subtask)
        assert "api_endpoint" in result

    def test_detect_celery_task_from_files(self):
        """Test detecting Celery task from file paths."""
        subtask = {
            "description": "Background processing",
            "files_to_create": ["workers/email_task.py", "tasks/notification.py"],
        }
        result = detect_work_type(subtask)
        assert "celery_task" in result


class TestPatternsIntegration:
    """Integration tests for patterns module."""

    def test_get_issues_for_detected_work_type(self):
        """Test getting issues for a detected work type."""
        subtask = {"description": "Create API endpoint"}
        work_types = detect_work_type(subtask)
        all_issues = get_common_issues()

        for work_type in work_types:
            assert work_type in all_issues
            assert len(all_issues[work_type]) > 0

    def test_complete_workflow(self):
        """Test complete workflow: detect type, get issues."""
        subtask = {
            "description": "Add login API endpoint with user model",
            "files_to_modify": ["api/routes.py", "models/user.py"],
        }

        # Detect work types
        work_types = detect_work_type(subtask)
        assert "api_endpoint" in work_types
        assert "authentication" in work_types
        assert "database_model" in work_types

        # Get issues for each work type
        all_issues = get_common_issues()
        for work_type in work_types:
            issues = all_issues[work_type]
            assert len(issues) > 0
            # Verify all issues are PredictedIssue instances
            for issue in issues:
                assert isinstance(issue, PredictedIssue)
                assert issue.description
                assert issue.prevention
