"""Tests for audit"""

from runners.github.audit import AuditAction, AuditContext, AuditEntry, AuditLogger, ActorType, audit_operation, get_audit_logger
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import tempfile
from datetime import datetime, timezone


def test_get_audit_logger():
    """Test get_audit_logger"""
    # Arrange & Act
    result = get_audit_logger()

    # Assert
    assert result is not None
    assert isinstance(result, AuditLogger)


def test_get_audit_logger_with_empty_inputs():
    """Test get_audit_logger with empty inputs"""
    # Arrange & Act
    result = get_audit_logger()

    # Assert
    assert result is not None
    assert isinstance(result, AuditLogger)


def test_get_audit_logger_with_invalid_input():
    """Test get_audit_logger returns instance"""
    # Arrange & Act - get_audit_logger always returns an instance
    result = get_audit_logger()

    # Assert
    assert result is not None


def test_audit_operation():
    """Test audit_operation returns decorator"""
    # Arrange
    action_start = AuditAction.PR_REVIEW_STARTED
    action_complete = AuditAction.PR_REVIEW_COMPLETED
    action_failed = AuditAction.PR_REVIEW_FAILED

    # Act
    decorator = audit_operation(action_start, action_complete, action_failed)

    # Assert
    assert decorator is not None
    assert callable(decorator)


def test_audit_operation_with_empty_inputs():
    """Test audit_operation with empty inputs"""
    # Arrange
    action_start = None
    action_complete = None
    action_failed = None

    # Act
    decorator = audit_operation(action_start, action_complete, action_failed)

    # Assert
    assert decorator is not None


def test_audit_operation_with_invalid_input():
    """Test audit_operation decorator works with audit_context param"""
    # Arrange
    @audit_operation(
        AuditAction.PR_REVIEW_STARTED,
        AuditAction.PR_REVIEW_COMPLETED,
        AuditAction.PR_REVIEW_FAILED,
        actor_type=ActorType.USER,
        repo="test/repo"
    )
    def test_func(audit_context=None):
        return "success"

    # Act
    result = test_func()

    # Assert
    assert result == "success"


def test_AuditContext_to_dict():
    """Test AuditContext.to_dict"""
    # Arrange
    instance = AuditContext(
        correlation_id="test-123",
        actor_type=ActorType.USER
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result is not None
    assert result["correlation_id"] == "test-123"
    assert result["actor_type"] == "user"


def test_AuditEntry_to_dict():
    """Test AuditEntry.to_dict"""
    # Arrange
    instance = AuditEntry(
        timestamp=datetime.now(timezone.utc),
        correlation_id="test-123",
        action=AuditAction.PR_REVIEW_STARTED,
        actor_type=ActorType.USER,
        actor_id="user1",
        repo="owner/repo",
        pr_number=123,
        issue_number=None,
        result="success",
        duration_ms=100,
        error=None,
        details={},
        token_usage=None,
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result is not None
    assert result["correlation_id"] == "test-123"
    assert result["action"] == "pr_review_started"


def test_AuditEntry_to_json():
    """Test AuditEntry.to_json"""
    # Arrange
    instance = AuditEntry(
        timestamp=datetime.now(timezone.utc),
        correlation_id="test-123",
        action=AuditAction.PR_REVIEW_STARTED,
        actor_type=ActorType.USER,
        actor_id="user1",
        repo="owner/repo",
        pr_number=123,
        issue_number=None,
        result="success",
        duration_ms=100,
        error=None,
        details={},
        token_usage=None,
    )

    # Act
    result = instance.to_json()

    # Assert
    assert result is not None
    assert isinstance(result, str)
    assert "test-123" in result


def test_AuditLogger___init__():
    """Test AuditLogger.__init__"""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        retention_days = 30
        max_file_size_mb = 100
        enabled = True

        # Act
        instance = AuditLogger(log_dir, retention_days, max_file_size_mb, enabled)

        # Assert
        assert instance.log_dir == log_dir
        assert instance.retention_days == retention_days
        assert instance.max_file_size_mb == max_file_size_mb
        assert instance.enabled is True


def test_AuditLogger_get_instance():
    """Test AuditLogger.get_instance"""
    # Arrange
    AuditLogger.reset_instance()

    # Act
    with tempfile.TemporaryDirectory() as tmpdir:
        result = AuditLogger.get_instance(log_dir=Path(tmpdir))

    # Assert
    assert result is not None
    assert isinstance(result, AuditLogger)


def test_AuditLogger_reset_instance():
    """Test AuditLogger.reset_instance"""
    # Arrange
    AuditLogger.reset_instance()

    # Act
    AuditLogger.reset_instance()

    # Assert - no error raised
    assert True


def test_AuditLogger_generate_correlation_id():
    """Test AuditLogger.generate_correlation_id"""
    # Arrange
    instance = AuditLogger(enabled=False)

    # Act
    result = instance.generate_correlation_id()

    # Assert
    assert result is not None
    assert isinstance(result, str)
    assert result.startswith("gh-")
    assert len(result) > 5


def test_AuditLogger_start_operation():
    """Test AuditLogger.start_operation"""
    # Arrange
    instance = AuditLogger(enabled=False)

    # Act
    result = instance.start_operation(
        actor_type=ActorType.USER,
        actor_id="user1",
        repo="owner/repo",
        pr_number=123,
    )

    # Assert
    assert result is not None
    assert isinstance(result, AuditContext)
    assert result.actor_type == ActorType.USER


def test_AuditLogger_log():
    """Test AuditLogger.log"""
    # Arrange
    instance = AuditLogger(enabled=False)
    context = instance.start_operation(
        actor_type=ActorType.USER,
        actor_id="user1",
        repo="owner/repo",
    )

    # Act
    result = instance.log(
        context=context,
        action=AuditAction.PR_REVIEW_STARTED,
        result="success",
    )

    # Assert
    assert result is not None
    assert isinstance(result, AuditEntry)


def test_AuditLogger_operation():
    """Test AuditLogger.operation"""
    # Arrange
    instance = AuditLogger(enabled=False)

    # Act
    with instance.operation(
        action_start=AuditAction.PR_REVIEW_STARTED,
        action_complete=AuditAction.PR_REVIEW_COMPLETED,
        action_failed=AuditAction.PR_REVIEW_FAILED,
        actor_type=ActorType.USER,
        repo="owner/repo",
    ) as ctx:
        ctx.metadata["test"] = "value"

    # Assert - context manager completes without error
    assert ctx.metadata["test"] == "value"


def test_AuditLogger_log_github_api_call():
    """Test AuditLogger.log_github_api_call"""
    # Arrange
    instance = AuditLogger(enabled=False)
    context = instance.start_operation(
        actor_type=ActorType.USER,
        repo="owner/repo",
    )

    # Act
    instance.log_github_api_call(
        context=context,
        endpoint="/repos/owner/repo",
        method="GET",
        status_code=200,
        duration_ms=50,
    )

    # Assert - no error raised
    assert True


def test_AuditLogger_log_ai_agent():
    """Test AuditLogger.log_ai_agent"""
    # Arrange
    instance = AuditLogger(enabled=False)
    context = instance.start_operation(
        actor_type=ActorType.AUTOMATION,
        repo="owner/repo",
    )

    # Act
    instance.log_ai_agent(
        context=context,
        agent_type="reviewer",
        model="claude-3",
        input_tokens=100,
        output_tokens=50,
        duration_ms=1000,
    )

    # Assert - no error raised
    assert True


def test_AuditLogger_log_permission_check():
    """Test AuditLogger.log_permission_check"""
    # Arrange
    instance = AuditLogger(enabled=False)
    context = instance.start_operation(
        actor_type=ActorType.SYSTEM,
        repo="owner/repo",
    )

    # Act
    instance.log_permission_check(
        context=context,
        allowed=True,
        reason="user is admin",
        username="user1",
        role="admin",
    )

    # Assert - no error raised
    assert True


def test_AuditLogger_log_state_transition():
    """Test AuditLogger.log_state_transition"""
    # Arrange
    instance = AuditLogger(enabled=False)
    context = instance.start_operation(
        actor_type=ActorType.SYSTEM,
        repo="owner/repo",
    )

    # Act
    instance.log_state_transition(
        context=context,
        from_state="pending",
        to_state="active",
        reason="approved",
    )

    # Assert - no error raised
    assert True


def test_AuditLogger_log_override():
    """Test AuditLogger.log_override"""
    # Arrange
    instance = AuditLogger(enabled=False)
    context = instance.start_operation(
        actor_type=ActorType.USER,
        repo="owner/repo",
    )

    # Act
    instance.log_override(
        context=context,
        override_type="manual",
        original_action="auto_close",
        actor_id="user1",
    )

    # Assert - no error raised
    assert True


def test_AuditLogger_query_logs():
    """Test AuditLogger.query_logs"""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        instance = AuditLogger(log_dir=Path(tmpdir), enabled=True)

        # Act
        result = instance.query_logs(correlation_id="test-123")

        # Assert
        assert result is not None
        assert isinstance(result, list)


def test_AuditLogger_get_operation_history():
    """Test AuditLogger.get_operation_history"""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        instance = AuditLogger(log_dir=Path(tmpdir), enabled=True)

        # Act
        result = instance.get_operation_history(correlation_id="test-123")

        # Assert
        assert result is not None
        assert isinstance(result, list)


def test_AuditLogger_get_statistics():
    """Test AuditLogger.get_statistics"""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        instance = AuditLogger(log_dir=Path(tmpdir), enabled=True)

        # Act
        result = instance.get_statistics(repo="owner/repo")

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert "total_entries" in result
