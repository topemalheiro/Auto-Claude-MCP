"""Tests for errors"""

from runners.github.errors import (
    APIError,
    AuthenticationError,
    ErrorCategory,
    ErrorSeverity,
    GitHubAutomationError,
    RateLimitError,
    Result,
    StructuredError,
    ValidationError,
    capture_error,
    format_error_for_ui,
)
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_capture_error():
    """Test capture_error"""

    # Arrange
    exc = ValueError("test error")
    correlation_id = "test-123"
    source = "test.source"
    pr_number = 42
    issue_number = 10
    repo = "owner/repo"

    # Act
    result = capture_error(exc, correlation_id, source, pr_number, issue_number, repo)

    # Assert
    assert result is not None
    assert result.message == "test error"
    assert result.correlation_id == "test-123"
    assert result.source == "test.source"
    assert result.pr_number == 42
    assert result.issue_number == 10
    assert result.repo == "owner/repo"


def test_capture_error_with_empty_inputs():
    """Test capture_error with empty inputs"""

    # Arrange
    exc = ValueError("test error")
    correlation_id = ""
    source = ""
    pr_number = 0
    issue_number = 0
    repo = ""

    # Act
    result = capture_error(exc, correlation_id, source, pr_number, issue_number, repo)

    # Assert
    assert result is not None
    assert result.message == "test error"


def test_capture_error_with_github_automation_error():
    """Test capture_error with GitHubAutomationError subclass"""

    # Arrange
    exc = AuthenticationError("Auth failed", details={"user": "test"})
    correlation_id = "test-123"
    source = "test.source"
    pr_number = 42
    issue_number = 10
    repo = "owner/repo"

    # Act
    result = capture_error(exc, correlation_id, source, pr_number, issue_number, repo)

    # Assert
    assert result is not None
    assert result.message == "Auth failed"
    assert result.category == ErrorCategory.AUTHENTICATION
    assert result.action_hint == "Check your GitHub token configuration"
    assert result.details == {"user": "test"}


def test_capture_error_with_timeout():
    """Test capture_error with GitHub automation TimeoutError"""

    # Arrange - Use the GitHub automation TimeoutError which has proper category
    from runners.github.errors import TimeoutError as GitHubTimeoutError
    exc = GitHubTimeoutError("Operation timed out")
    correlation_id = "test-123"

    # Act
    result = capture_error(exc, correlation_id)

    # Assert
    assert result is not None
    assert result.category == ErrorCategory.TIMEOUT
    assert result.retryable is True
    assert result.action_hint == "The operation took too long. Try again"


def test_format_error_for_ui():
    """Test format_error_for_ui"""

    # Arrange
    error = StructuredError(
        message="Test error",
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.ERROR,
        code="TEST_ERROR",
        correlation_id="test-123",
        retryable=True,
        retry_after_seconds=60,
        action_hint="Fix the input",
    )

    # Act
    result = format_error_for_ui(error)

    # Assert
    assert result is not None
    assert result["title"] == "Validation Error"
    assert result["message"] == "Test error"
    assert result["severity"] == "error"
    assert result["retryable"] is True
    assert result["retry_after"] == 60
    assert result["action"] == "Fix the input"
    assert result["details"]["code"] == "TEST_ERROR"
    assert result["details"]["correlation_id"] == "test-123"


def test_format_error_for_ui_with_empty_inputs():
    """Test format_error_for_ui with minimal error"""

    # Arrange
    error = StructuredError(
        message="Test error",
        category=ErrorCategory.INTERNAL,
    )

    # Act
    result = format_error_for_ui(error)

    # Assert
    assert result is not None
    assert result["title"] == "Internal Error"
    assert result["message"] == "Test error"


def test_StructuredError_to_dict():
    """Test StructuredError.to_dict"""

    # Arrange
    instance = StructuredError(
        message="Test error",
        category=ErrorCategory.API_ERROR,
        severity=ErrorSeverity.WARNING,
        code="API_500",
        correlation_id="corr-123",
        details={"status": 500},
        retryable=True,
        retry_after_seconds=30,
        action_hint="Retry later",
        source="api.client",
        pr_number=42,
        issue_number=10,
        repo="owner/repo",
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result is not None
    assert result["message"] == "Test error"
    assert result["category"] == "api_error"
    assert result["severity"] == "warning"
    assert result["code"] == "API_500"
    assert result["correlation_id"] == "corr-123"
    assert result["details"] == {"status": 500}
    assert result["retryable"] is True
    assert result["retry_after_seconds"] == 30
    assert result["action_hint"] == "Retry later"
    assert result["source"] == "api.client"
    assert result["pr_number"] == 42
    assert result["issue_number"] == 10
    assert result["repo"] == "owner/repo"


def test_StructuredError_from_exception():
    """Test StructuredError.from_exception"""

    # Arrange
    exc = ValueError("Invalid value")
    category = ErrorCategory.VALIDATION
    severity = ErrorSeverity.ERROR
    correlation_id = "test-123"

    # Act
    result = StructuredError.from_exception(
        exc,
        category=category,
        severity=severity,
        correlation_id=correlation_id,
    )

    # Assert
    assert result is not None
    assert result.message == "Invalid value"
    assert result.category == ErrorCategory.VALIDATION
    assert result.severity == ErrorSeverity.ERROR
    assert result.correlation_id == "test-123"
    assert result.code == "ValueError"
    assert result.stack_trace is not None


def test_GitHubAutomationError___init__():
    """Test GitHubAutomationError.__init__"""

    # Arrange & Act
    message = "Test error"
    details = {"key": "value"}
    correlation_id = "corr-123"
    instance = GitHubAutomationError(message, details, correlation_id, extra="extra_value")

    # Assert
    assert instance.message == "Test error"
    assert instance.details == {"key": "value"}
    assert instance.correlation_id == "corr-123"
    assert instance.extra == {"extra": "extra_value"}
    assert instance.category == ErrorCategory.INTERNAL
    assert instance.severity == ErrorSeverity.ERROR
    assert instance.retryable is False


def test_GitHubAutomationError_to_structured_error():
    """Test GitHubAutomationError.to_structured_error"""

    # Arrange
    instance = ValidationError("Validation failed", details={"field": "email"})
    instance.correlation_id = "corr-123"

    # Act
    result = instance.to_structured_error()

    # Assert
    assert result is not None
    assert result.message == "Validation failed"
    assert result.category == ErrorCategory.VALIDATION
    assert result.details == {"field": "email"}
    assert result.code == "ValidationError"
    assert result.correlation_id == "corr-123"
    assert result.stack_trace is not None


def test_RateLimitError___init__():
    """Test RateLimitError.__init__"""

    # Arrange & Act
    message = "Rate limit exceeded"
    retry_after_seconds = 120
    instance = RateLimitError(message, retry_after_seconds)

    # Assert
    assert instance.message == "Rate limit exceeded"
    assert instance.retry_after_seconds == 120
    assert instance.category == ErrorCategory.RATE_LIMITED
    assert instance.severity == ErrorSeverity.WARNING
    assert instance.retryable is True
    assert instance.action_hint == "Rate limited. Retry in 120 seconds"


def test_RateLimitError_to_structured_error():
    """Test RateLimitError.to_structured_error"""

    # Arrange
    instance = RateLimitError("Rate limited", retry_after_seconds=60)

    # Act
    result = instance.to_structured_error()

    # Assert
    assert result is not None
    assert result.message == "Rate limited"
    assert result.retry_after_seconds == 60
    assert result.category == ErrorCategory.RATE_LIMITED


def test_APIError___init__():
    """Test APIError.__init__"""

    # Arrange & Act
    message = "API request failed"
    status_code = 500
    instance = APIError(message, status_code)

    # Assert
    assert instance.message == "API request failed"
    assert instance.status_code == 500
    assert instance.details == {"status_code": 500}
    assert instance.category == ErrorCategory.API_ERROR
    assert instance.retryable is True
    assert instance.action_hint == "GitHub service issue. Retry later"


def test_APIError___init__with_client_error():
    """Test APIError.__init__ with 4xx status code"""

    # Arrange & Act
    message = "Not found"
    status_code = 404
    instance = APIError(message, status_code)

    # Assert
    assert instance.message == "Not found"
    assert instance.status_code == 404
    assert instance.details == {"status_code": 404}
    assert instance.retryable is False
    assert instance.action_hint is None


def test_Result_success():
    """Test Result.success"""

    # Arrange
    data = {"findings": [], "verdict": "ready_to_merge"}

    # Act
    result = Result.success(data)

    # Assert
    assert result is not None
    assert result.ok is True
    assert result.data == data
    assert result.error is None


def test_Result_failure():
    """Test Result.failure"""

    # Arrange
    error = StructuredError(
        message="Failed",
        category=ErrorCategory.INTERNAL,
    )

    # Act
    result = Result.failure(error)

    # Assert
    assert result is not None
    assert result.ok is False
    assert result.data is None
    assert result.error == error


def test_Result_from_exception():
    """Test Result.from_exception"""

    # Arrange
    exc = ValueError("Something went wrong")

    # Act
    result = Result.from_exception(exc, source="test.module")

    # Assert
    assert result is not None
    assert result.ok is False
    assert result.error is not None
    assert result.error.message == "Something went wrong"
    assert result.error.source == "test.module"


def test_Result_to_dict():
    """Test Result.to_dict"""

    # Arrange - success case
    instance = Result.success(data={"key": "value"})

    # Act
    result = instance.to_dict()

    # Assert
    assert result is not None
    assert result["ok"] is True
    assert result["data"] == {"key": "value"}
    assert result["error"] is None


def test_Result_to_dict_failure():
    """Test Result.to_dict with failure"""

    # Arrange
    error = StructuredError(
        message="Error",
        category=ErrorCategory.INTERNAL,
    )
    instance = Result.failure(error)

    # Act
    result = instance.to_dict()

    # Assert
    assert result is not None
    assert result["ok"] is False
    assert result["data"] is None
    assert result["error"] is not None
    assert result["error"]["message"] == "Error"
