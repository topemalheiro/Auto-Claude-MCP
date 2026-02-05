"""Tests for override"""

from datetime import datetime, timedelta, timezone

import pytest

from runners.github.override import (
    CommandType,
    GracePeriodEntry,
    OverrideManager,
    OverrideRecord,
    OverrideType,
    ParsedCommand,
)


@pytest.fixture
def temp_github_dir(tmp_path):
    """Create a temporary github directory."""
    return tmp_path / "github"


@pytest.fixture
def override_manager(temp_github_dir):
    """Create an OverrideManager instance for testing."""
    return OverrideManager(github_dir=temp_github_dir, grace_period_minutes=5)


def test_OverrideRecord_to_dict():
    """Test OverrideRecord.to_dict"""
    instance = OverrideRecord(
        id="override-001",
        override_type=OverrideType.NOT_SPAM,
        issue_number=123,
        pr_number=None,
        repo="owner/repo",
        actor="test_user",
        reason="Not spam",
        original_state="spam",
        new_state="triaged",
    )
    result = instance.to_dict()
    assert result is not None
    assert result["id"] == "override-001"
    assert result["override_type"] == "not_spam"
    assert result["issue_number"] == 123
    assert result["actor"] == "test_user"


def test_OverrideRecord_from_dict():
    """Test OverrideRecord.from_dict"""
    data = {
        "id": "override-001",
        "override_type": "not_spam",
        "issue_number": 123,
        "pr_number": None,
        "repo": "owner/repo",
        "actor": "test_user",
        "reason": "Not spam",
        "original_state": "spam",
        "new_state": "triaged",
        "created_at": "2025-01-01T00:00:00Z",
        "metadata": {},
    }
    result = OverrideRecord.from_dict(data)
    assert result is not None
    assert result.id == "override-001"
    assert result.override_type == OverrideType.NOT_SPAM
    assert result.issue_number == 123


def test_GracePeriodEntry_to_dict():
    """Test GracePeriodEntry.to_dict"""
    instance = GracePeriodEntry(
        issue_number=123,
        trigger_label="auto-fix",
        triggered_by="test_user",
        triggered_at="2025-01-01T00:00:00Z",
        expires_at="2025-01-01T00:05:00Z",
    )
    result = instance.to_dict()
    assert result is not None
    assert result["issue_number"] == 123
    assert result["trigger_label"] == "auto-fix"
    assert result["triggered_by"] == "test_user"


def test_GracePeriodEntry_from_dict():
    """Test GracePeriodEntry.from_dict"""
    data = {
        "issue_number": 123,
        "trigger_label": "auto-fix",
        "triggered_by": "test_user",
        "triggered_at": "2025-01-01T00:00:00Z",
        "expires_at": "2025-01-01T00:05:00Z",
        "cancelled": False,
        "cancelled_by": None,
        "cancelled_at": None,
    }
    result = GracePeriodEntry.from_dict(data)
    assert result is not None
    assert result.issue_number == 123
    assert result.trigger_label == "auto-fix"


def test_GracePeriodEntry_is_in_grace_period():
    """Test GracePeriodEntry.is_in_grace_period"""
    # Within grace period
    future_time = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    instance = GracePeriodEntry(
        issue_number=123,
        trigger_label="auto-fix",
        triggered_by="test_user",
        triggered_at=datetime.now(timezone.utc).isoformat(),
        expires_at=future_time,
        cancelled=False,
    )
    result = instance.is_in_grace_period()
    assert result is True

    # Expired
    past_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    instance2 = GracePeriodEntry(
        issue_number=124,
        trigger_label="auto-fix",
        triggered_by="test_user",
        triggered_at=datetime.now(timezone.utc).isoformat(),
        expires_at=past_time,
        cancelled=False,
    )
    result = instance2.is_in_grace_period()
    assert result is False

    # Cancelled
    instance3 = GracePeriodEntry(
        issue_number=125,
        trigger_label="auto-fix",
        triggered_by="test_user",
        triggered_at=datetime.now(timezone.utc).isoformat(),
        expires_at=future_time,
        cancelled=True,
    )
    result = instance3.is_in_grace_period()
    assert result is False


def test_GracePeriodEntry_time_remaining():
    """Test GracePeriodEntry.time_remaining"""
    # Future time
    future_time = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    instance = GracePeriodEntry(
        issue_number=123,
        trigger_label="auto-fix",
        triggered_by="test_user",
        triggered_at=datetime.now(timezone.utc).isoformat(),
        expires_at=future_time,
        cancelled=False,
    )
    result = instance.time_remaining()
    assert result is not None
    assert result > timedelta(0)

    # Past time (should return 0)
    past_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    instance2 = GracePeriodEntry(
        issue_number=124,
        trigger_label="auto-fix",
        triggered_by="test_user",
        triggered_at=datetime.now(timezone.utc).isoformat(),
        expires_at=past_time,
        cancelled=False,
    )
    result = instance2.time_remaining()
    assert result == timedelta(0)


def test_ParsedCommand_to_dict():
    """Test ParsedCommand.to_dict"""
    instance = ParsedCommand(
        command=CommandType.CANCEL_AUTOFIX,
        args=["--reason", "test"],
        raw_text="/cancel-autofix --reason test",
        author="test_user",
    )
    result = instance.to_dict()
    assert result is not None
    assert result["command"] == "/cancel-autofix"
    assert result["args"] == ["--reason", "test"]
    assert result["author"] == "test_user"


def test_OverrideManager___init__(temp_github_dir):
    """Test OverrideManager.__init__"""
    instance = OverrideManager(github_dir=temp_github_dir, grace_period_minutes=5)
    assert instance.github_dir == temp_github_dir
    assert instance.grace_period_minutes == 5
    assert instance.override_dir == temp_github_dir / "overrides"


def test_OverrideManager_start_grace_period(override_manager):
    """Test OverrideManager.start_grace_period"""
    result = override_manager.start_grace_period(
        issue_number=123,
        trigger_label="auto-fix",
        triggered_by="test_user",
        grace_minutes=5,
    )
    assert result is not None
    assert result.issue_number == 123
    assert result.trigger_label == "auto-fix"
    assert result.triggered_by == "test_user"


def test_OverrideManager_get_grace_period(override_manager):
    """Test OverrideManager.get_grace_period"""
    # Start a grace period first
    override_manager.start_grace_period(
        issue_number=123,
        trigger_label="auto-fix",
        triggered_by="test_user",
        grace_minutes=5,
    )

    # Get the grace period
    result = override_manager.get_grace_period(123)
    assert result is not None
    assert result.issue_number == 123
    assert result.trigger_label == "auto-fix"

    # Get non-existent grace period
    result2 = override_manager.get_grace_period(999)
    assert result2 is None


def test_OverrideManager_is_in_grace_period(override_manager):
    """Test OverrideManager.is_in_grace_period"""
    # Start a grace period
    override_manager.start_grace_period(
        issue_number=123,
        trigger_label="auto-fix",
        triggered_by="test_user",
        grace_minutes=5,
    )

    # Check if in grace period
    result = override_manager.is_in_grace_period(123)
    assert result is True

    # Check non-existent issue
    result2 = override_manager.is_in_grace_period(999)
    assert result2 is False


def test_OverrideManager_cancel_grace_period(override_manager):
    """Test OverrideManager.cancel_grace_period"""
    # Start a grace period
    override_manager.start_grace_period(
        issue_number=123,
        trigger_label="auto-fix",
        triggered_by="test_user",
        grace_minutes=5,
    )

    # Cancel the grace period
    result = override_manager.cancel_grace_period(123, cancelled_by="admin_user")
    assert result is True

    # Verify it's cancelled
    grace = override_manager.get_grace_period(123)
    assert grace is not None
    assert grace.cancelled is True
    assert grace.cancelled_by == "admin_user"

    # Try to cancel again (should fail)
    result2 = override_manager.cancel_grace_period(123, cancelled_by="admin_user")
    assert result2 is False


def test_OverrideManager_parse_comment(override_manager):
    """Test OverrideManager.parse_comment"""
    # Parse cancel-autofix command
    result = override_manager.parse_comment("/cancel-autofix", "test_user")
    assert result is not None
    assert result.command == CommandType.CANCEL_AUTOFIX
    assert result.author == "test_user"

    # Parse command with args
    result2 = override_manager.parse_comment("/cancel-autofix --reason test", "test_user")
    assert result2 is not None
    assert len(result2.args) == 2

    # Parse non-command
    result3 = override_manager.parse_comment("Just a regular comment", "test_user")
    assert result3 is None


def test_OverrideManager_get_help_text(override_manager):
    """Test OverrideManager.get_help_text"""
    result = override_manager.get_help_text()
    assert result is not None
    assert isinstance(result, str)
    assert "/cancel-autofix" in result
    assert "/help" in result


@pytest.mark.asyncio
async def test_OverrideManager_execute_command(override_manager):
    """Test OverrideManager.execute_command"""
    # Test HELP command which doesn't require grace period
    command = ParsedCommand(
        command=CommandType.HELP,
        args=[],
        raw_text="/help",
        author="test_user",
    )
    result = await override_manager.execute_command(
        command=command,
        issue_number=123,
        pr_number=None,
        repo="owner/repo",
        current_state="building",
    )
    assert result is not None
    assert result["success"] is True
    assert "Available Commands" in result["message"]

    # Test STATUS command
    command2 = ParsedCommand(
        command=CommandType.STATUS,
        args=[],
        raw_text="/status",
        author="test_user",
    )
    result2 = await override_manager.execute_command(
        command=command2,
        issue_number=123,
        pr_number=None,
        repo="owner/repo",
        current_state="building",
    )
    assert result2 is not None
    assert result2["success"] is True


@pytest.mark.asyncio
async def test_OverrideManager_get_override_history(override_manager):
    """Test OverrideManager.get_override_history"""
    # Manually create an override history file
    import json
    from datetime import datetime, timezone

    history_file = override_manager._get_history_file()
    history_file.parent.mkdir(parents=True, exist_ok=True)

    record = OverrideRecord(
        id="override-001",
        override_type=OverrideType.FORCE_RETRY,
        issue_number=123,
        pr_number=None,
        repo="owner/repo",
        actor="test_user",
        reason="Test",
        original_state="building",
        new_state="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    with open(history_file, "w") as f:
        json.dump({
            "records": [record.to_dict()],
            "last_updated": datetime.now(timezone.utc).isoformat()
        }, f)

    # Get history
    result = override_manager.get_override_history(issue_number=123)
    assert result is not None
    assert len(result) > 0
    assert result[0].issue_number == 123
    assert result[0].override_type == OverrideType.FORCE_RETRY


@pytest.mark.asyncio
async def test_OverrideManager_get_override_statistics(override_manager):
    """Test OverrideManager.get_override_statistics"""
    # Manually create an override history file
    import json
    from datetime import datetime, timezone

    history_file = override_manager._get_history_file()
    history_file.parent.mkdir(parents=True, exist_ok=True)

    record1 = OverrideRecord(
        id="override-001",
        override_type=OverrideType.FORCE_RETRY,
        issue_number=123,
        pr_number=None,
        repo="owner/repo",
        actor="test_user",
        reason="Test",
        original_state="building",
        new_state="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    record2 = OverrideRecord(
        id="override-002",
        override_type=OverrideType.APPROVE_SPEC,
        issue_number=124,
        pr_number=None,
        repo="owner/repo",
        actor="test_user",
        reason="Test",
        original_state="pending",
        new_state="approved",
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    with open(history_file, "w") as f:
        json.dump({
            "records": [record1.to_dict(), record2.to_dict()],
            "last_updated": datetime.now(timezone.utc).isoformat()
        }, f)

    # Get statistics
    result = override_manager.get_override_statistics(repo="owner/repo")
    assert result is not None
    assert isinstance(result, dict)
    assert "total" in result
    assert result["total"] >= 2
