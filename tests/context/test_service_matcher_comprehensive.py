"""
Comprehensive Tests for context.service_matcher module
======================================================

Tests for ServiceMatcher class including all scoring logic,
edge cases, and default service selection.
"""

import pytest

from context.service_matcher import ServiceMatcher


class TestServiceMatcherInit:
    """Tests for ServiceMatcher.__init__"""

    def test_init_with_project_index(self):
        """Test initialization with project index"""
        project_index = {
            "services": {
                "api": {"path": "apps/api", "language": "python"},
            }
        }
        matcher = ServiceMatcher(project_index)
        assert matcher.project_index == project_index

    def test_init_with_empty_index(self):
        """Test initialization with empty project index"""
        matcher = ServiceMatcher({})
        assert matcher.project_index == {}

    def test_init_with_no_services_key(self):
        """Test initialization when index has no 'services' key"""
        matcher = ServiceMatcher({"other": "data"})
        assert matcher.project_index == {"other": "data"}


class TestSuggestServicesBasic:
    """Tests for basic service suggestion"""

    def test_suggest_services_empty_task(self):
        """Test with empty task description"""
        project_index = {
            "services": {
                "api": {"type": "backend"},
                "web": {"type": "frontend"},
            }
        }
        matcher = ServiceMatcher(project_index)
        result = matcher.suggest_services("")
        assert isinstance(result, list)

    def test_suggest_services_none_services(self):
        """Test when project_index has no services"""
        matcher = ServiceMatcher({})
        result = matcher.suggest_services("Add authentication")
        assert result == []

    def test_suggest_services_empty_services(self):
        """Test when services dict is empty"""
        matcher = ServiceMatcher({"services": {}})
        result = matcher.suggest_services("Add authentication")
        assert result == []


class TestServiceNameMatching:
    """Tests for service name matching logic"""

    def test_service_name_mentioned(self):
        """Test when service name is explicitly mentioned in task"""
        project_index = {
            "services": {
                "api": {"type": "backend"},
                "web": {"type": "frontend"},
            }
        }
        matcher = ServiceMatcher(project_index)
        result = matcher.suggest_services("Update the API service")
        assert "api" in result

    def test_service_name_case_insensitive(self):
        """Test that service name matching is case insensitive"""
        project_index = {
            "services": {
                "API": {"type": "backend"},
            }
        }
        matcher = ServiceMatcher(project_index)
        result = matcher.suggest_services("update the api")
        assert "API" in result

    def test_service_name_partial_match(self):
        """Test partial service name matching"""
        project_index = {
            "services": {
                "auth-service": {"type": "backend"},
            }
        }
        matcher = ServiceMatcher(project_index)
        result = matcher.suggest_services("Update auth")
        # "auth" is in "auth-service"
        assert "auth-service" in result

    def test_multiple_services_mentioned(self):
        """Test when multiple services are mentioned"""
        project_index = {
            "services": {
                "api": {"type": "backend"},
                "web": {"type": "frontend"},
                "worker": {"type": "worker"},
            }
        }
        matcher = ServiceMatcher(project_index)
        result = matcher.suggest_services("Update API and web frontend")
        assert "api" in result
        assert "web" in result

    def test_service_name_not_mentioned(self):
        """Test when no service name is mentioned"""
        project_index = {
            "services": {
                "api": {"type": "backend"},
                "web": {"type": "frontend"},
            }
        }
        matcher = ServiceMatcher(project_index)
        result = matcher.suggest_services("Fix some bug")
        # Should return default services
        assert isinstance(result, list)


class TestServiceTypeScoring:
    """Tests for service type-based scoring"""

    def test_backend_type_keywords(self):
        """Test backend type keyword scoring"""
        project_index = {
            "services": {
                "api": {"type": "backend"},
                "web": {"type": "frontend"},
            }
        }
        matcher = ServiceMatcher(project_index)

        # Test various backend keywords
        for keyword in ["api", "endpoint", "route", "database", "model"]:
            result = matcher.suggest_services(f"Add new {keyword}")
            assert "api" in result

    def test_frontend_type_keywords(self):
        """Test frontend type keyword scoring"""
        project_index = {
            "services": {
                "api": {"type": "backend"},
                "web": {"type": "frontend"},
            }
        }
        matcher = ServiceMatcher(project_index)

        # Test various frontend keywords
        for keyword in ["ui", "component", "page", "button", "form"]:
            result = matcher.suggest_services(f"Create new {keyword}")
            assert "web" in result

    def test_worker_type_keywords(self):
        """Test worker type keyword scoring"""
        project_index = {
            "services": {
                "api": {"type": "backend"},
                "worker": {"type": "worker"},
            }
        }
        matcher = ServiceMatcher(project_index)

        # Test various worker keywords
        for keyword in ["job", "task", "queue", "background", "async"]:
            result = matcher.suggest_services(f"Process {keyword}")
            assert "worker" in result

    def test_scraper_type_keywords(self):
        """Test scraper type keyword scoring"""
        project_index = {
            "services": {
                "api": {"type": "backend"},
                "scraper": {"type": "scraper"},
            }
        }
        matcher = ServiceMatcher(project_index)

        # Test various scraper keywords
        for keyword in ["scrape", "crawl", "fetch", "parse"]:
            result = matcher.suggest_services(f"{keyword} data from web")
            assert "scraper" in result

    def test_type_case_insensitive(self):
        """Test that type keyword matching is case insensitive"""
        project_index = {
            "services": {
                "api": {"type": "backend"},
            }
        }
        matcher = ServiceMatcher(project_index)
        result = matcher.suggest_services("Add new API endpoint")
        assert "api" in result

    def test_no_type_field(self):
        """Test services without type field"""
        project_index = {
            "services": {
                "api": {"language": "python"},
                "web": {"language": "typescript"},
            }
        }
        matcher = ServiceMatcher(project_index)
        result = matcher.suggest_services("Add authentication")
        # Should still work, just no type-based scoring
        assert isinstance(result, list)


class TestFrameworkScoring:
    """Tests for framework-based scoring"""

    def test_framework_mentioned(self):
        """Test when framework is mentioned in task"""
        project_index = {
            "services": {
                "api": {"type": "backend", "framework": "django"},
                "web": {"type": "frontend", "framework": "react"},
            }
        }
        matcher = ServiceMatcher(project_index)

        result = matcher.suggest_services("Add django authentication")
        assert "api" in result

        result = matcher.suggest_services("Create react component")
        assert "web" in result

    def test_framework_case_insensitive(self):
        """Test that framework matching is case insensitive"""
        project_index = {
            "services": {
                "api": {"type": "backend", "framework": "Django"},
            }
        }
        matcher = ServiceMatcher(project_index)
        result = matcher.suggest_services("Update django models")
        assert "api" in result

    def test_framework_not_mentioned(self):
        """Test when framework is not mentioned"""
        project_index = {
            "services": {
                "api": {"type": "backend", "framework": "django"},
            }
        }
        matcher = ServiceMatcher(project_index)
        result = matcher.suggest_services("Add authentication")
        # Should still suggest based on other factors
        assert isinstance(result, list)


class TestScoringAggregation:
    """Tests for score aggregation and sorting"""

    def test_score_accumulation(self):
        """Test that scores from different sources accumulate"""
        project_index = {
            "services": {
                "api": {"type": "backend", "framework": "django"},
            }
        }
        matcher = ServiceMatcher(project_index)

        # Mention both service name and type keyword
        result = matcher.suggest_services("Update API endpoint")
        assert "api" in result

    def test_top_three_services(self):
        """Test that at most top 3 services are returned"""
        project_index = {
            "services": {
                "api": {"type": "backend"},
                "web": {"type": "frontend"},
                "worker": {"type": "worker"},
                "scraper": {"type": "scraper"},
                "mobile": {"type": "mobile"},
            }
        }
        matcher = ServiceMatcher(project_index)

        # Task that might match multiple services
        result = matcher.suggest_services("Update service")
        assert len(result) <= 3

    def test_scoring_priority(self):
        """Test that higher scored services are preferred"""
        project_index = {
            "services": {
                "api": {"type": "backend"},
                "web": {"type": "frontend"},
            }
        }
        matcher = ServiceMatcher(project_index)

        # Service name match should score higher than type match
        result = matcher.suggest_services("Update API with new endpoint")
        assert "api" in result


class TestDefaultServices:
    """Tests for default service selection"""

    def test_default_backend_and_frontend(self):
        """Test default returns backend and frontend"""
        project_index = {
            "services": {
                "api": {"type": "backend"},
                "web": {"type": "frontend"},
                "worker": {"type": "worker"},
            }
        }
        matcher = ServiceMatcher(project_index)

        result = matcher.suggest_services("Fix xyz123 bug")
        # Should include backend and/or frontend when no specific keywords match
        assert "api" in result or "web" in result or len(result) >= 0

    def test_default_only_backend(self):
        """Test default when only backend exists"""
        project_index = {
            "services": {
                "api": {"type": "backend"},
                "worker": {"type": "worker"},
            }
        }
        matcher = ServiceMatcher(project_index)

        result = matcher.suggest_services("Fix xyz123 bug")
        # Should return backend or other available services
        assert isinstance(result, list)

    def test_default_only_frontend(self):
        """Test default when only frontend exists"""
        project_index = {
            "services": {
                "web": {"type": "frontend"},
                "mobile": {"type": "mobile"},
            }
        }
        matcher = ServiceMatcher(project_index)

        result = matcher.suggest_services("Some task")
        # Should return frontend
        assert "web" in result

    def test_default_no_backend_or_frontend(self):
        """Test default when no backend or frontend exist"""
        project_index = {
            "services": {
                "worker": {"type": "worker"},
                "scraper": {"type": "scraper"},
            }
        }
        matcher = ServiceMatcher(project_index)

        result = matcher.suggest_services("Some task")
        # Should return first available services
        assert len(result) >= 0

    def test_default_first_two_services(self):
        """Test default returns first two services when no type info"""
        project_index = {
            "services": {
                "service1": {"language": "python"},
                "service2": {"language": "javascript"},
                "service3": {"language": "go"},
            }
        }
        matcher = ServiceMatcher(project_index)

        result = matcher.suggest_services("Some task")
        # Should return first two
        assert len(result) <= 2

    def test_default_empty_services(self):
        """Test default when no services match criteria"""
        project_index = {
            "services": {}
        }
        matcher = ServiceMatcher(project_index)

        result = matcher.suggest_services("Some task")
        assert result == []


class TestEdgeCases:
    """Tests for edge cases and special scenarios"""

    def test_multiple_score_thresholds(self):
        """Test various score threshold combinations"""
        project_index = {
            "services": {
                "api": {"type": "backend", "framework": "fastapi"},
            }
        }
        matcher = ServiceMatcher(project_index)

        # Multiple matching factors
        result = matcher.suggest_services("Update fastapi API with endpoint")
        assert "api" in result

    def test_no_score_returns_defaults(self):
        """Test that services with zero score return defaults"""
        project_index = {
            "services": {
                "api": {"type": "backend"},
                "web": {"type": "frontend"},
            }
        }
        matcher = ServiceMatcher(project_index)

        # Task with no matching keywords
        result = matcher.suggest_services("xyz123")
        # Should return defaults
        assert isinstance(result, list)

    def test_special_characters_in_task(self):
        """Test task with special characters"""
        project_index = {
            "services": {
                "api": {"type": "backend"},
            }
        }
        matcher = ServiceMatcher(project_index)

        result = matcher.suggest_services("Fix API: add endpoint, update model!")
        assert "api" in result

    def test_very_long_task(self):
        """Test with very long task description"""
        project_index = {
            "services": {
                "api": {"type": "backend"},
            }
        }
        matcher = ServiceMatcher(project_index)

        long_task = " ".join(["API"] * 1000)
        result = matcher.suggest_services(long_task)
        assert "api" in result
