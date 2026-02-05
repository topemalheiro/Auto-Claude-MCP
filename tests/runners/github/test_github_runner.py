"""
Tests for GitHub Runner
========================

Tests for runners.github.runner - GitHub runner CLI entry point
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import argparse

import pytest

from runners.github.models import (
    AutoFixState,
    AutoFixStatus,
    GitHubRunnerConfig,
    MergeVerdict,
    PRReviewFinding,
    PRReviewResult,
    ReviewCategory,
    ReviewSeverity,
)
from runners.github.runner import (
    get_config,
    main,
    print_progress,
    ProgressCallback,
)


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


@pytest.fixture
def mock_args(temp_project_dir: Path):
    """Create mock argparse namespace."""
    return argparse.Namespace(
        project=temp_project_dir,
        token="test_token",
        bot_token="test_bot_token",
        repo="owner/repo",
        model="claude-sonnet-4-5-20250929",
        thinking_level="medium",
    )


def test_print_progress():
    """Test print_progress function."""
    callback = ProgressCallback(
        phase="test_phase",
        progress=50,
        message="Test message",
        pr_number=123,
    )

    # Just ensure it doesn't raise an exception
    print_progress(callback)


def test_print_progress_with_issue_number():
    """Test print_progress function with issue number."""
    callback = ProgressCallback(
        phase="test_phase",
        progress=75,
        message="Testing issue",
        issue_number=42,
    )

    # Just ensure it doesn't raise an exception
    print_progress(callback)


@patch("core.gh_executable.get_gh_executable")
@patch("subprocess.run")
def test_get_config_with_explicit_args(mock_run, mock_gh_executable, mock_args):
    """Test get_config with explicit CLI args."""
    mock_gh_executable.return_value = "gh"
    mock_run.return_value = MagicMock(returncode=0, stdout="test_token", stderr="")

    config = get_config(mock_args)

    assert config.token == "test_token"
    assert config.repo == "owner/repo"
    assert config.model == "claude-sonnet-4-5-20250929"
    assert config.thinking_level == "medium"


@patch("core.gh_executable.get_gh_executable")
@patch("subprocess.run")
@patch.dict("os.environ", {"GITHUB_TOKEN": "env_token", "GITHUB_REPO": "env/repo"})
def test_get_config_from_env(mock_run, mock_gh_executable, temp_project_dir):
    """Test get_config loading from environment variables."""
    mock_gh_executable.return_value = "gh"

    # Create args without explicit token/repo
    args = argparse.Namespace(
        project=temp_project_dir,
        token=None,
        bot_token=None,
        repo=None,
        model="claude-sonnet-4-5-20250929",
        thinking_level="medium",
    )

    config = get_config(args)

    assert config.token == "env_token"
    assert config.repo == "env/repo"


@patch("core.gh_executable.get_gh_executable")
@patch("subprocess.run")
def test_get_config_auto_detect_repo(mock_run, mock_gh_executable, temp_project_dir):
    """Test get_config auto-detecting repo from git remote."""
    mock_gh_executable.return_value = "gh"

    # Mock gh auth token
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout="gh_token", stderr=""),
        MagicMock(returncode=0, stdout="auto/detected", stderr=""),
    ]

    args = argparse.Namespace(
        project=temp_project_dir,
        token=None,
        bot_token=None,
        repo=None,
        model="claude-sonnet-4-5-20250929",
        thinking_level="medium",
    )

    config = get_config(args)

    assert config.token == "gh_token"
    assert config.repo == "auto/detected"


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_review_pr_success(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_review_pr with successful review."""
    # Setup mocks
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_result = PRReviewResult(
        pr_number=123,
        repo="owner/repo",
        success=True,
        findings=[
            PRReviewFinding(
                id="1",
                severity=ReviewSeverity.LOW,
                category=ReviewCategory.STYLE,
                title="Minor issue",
                description="Style suggestion",
                file="app.py",
                line=42,
            )
        ],
        summary="LGTM with minor suggestions",
        overall_status="approve",
        verdict=MergeVerdict.READY_TO_MERGE,
    )

    mock_orchestrator = AsyncMock()
    mock_orchestrator.review_pr = AsyncMock(return_value=mock_result)
    mock_orchestrator_class.return_value = mock_orchestrator

    # Set args for review-pr command
    mock_args.pr_number = 123
    mock_args.auto_post = False
    mock_args.force = False

    from runners.github.runner import cmd_review_pr

    exit_code = await cmd_review_pr(mock_args)

    assert exit_code == 0
    mock_orchestrator.review_pr.assert_called_once_with(123, force_review=False)


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_review_pr_failure(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_review_pr with failed review."""
    # Setup mocks
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_result = PRReviewResult(
        pr_number=123,
        repo="owner/repo",
        success=False,
        error="API rate limit exceeded",
    )

    mock_orchestrator = AsyncMock()
    mock_orchestrator.review_pr = AsyncMock(return_value=mock_result)
    mock_orchestrator_class.return_value = mock_orchestrator

    # Set args for review-pr command
    mock_args.pr_number = 123
    mock_args.auto_post = False
    mock_args.force = False

    from runners.github.runner import cmd_review_pr

    exit_code = await cmd_review_pr(mock_args)

    assert exit_code == 1


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_review_pr_with_force(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_review_pr with force flag."""
    # Setup mocks
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_result = PRReviewResult(
        pr_number=123,
        repo="owner/repo",
        success=True,
        findings=[],
        summary="LGTM",
        overall_status="approve",
        verdict=MergeVerdict.READY_TO_MERGE,
    )

    mock_orchestrator = AsyncMock()
    mock_orchestrator.review_pr = AsyncMock(return_value=mock_result)
    mock_orchestrator_class.return_value = mock_orchestrator

    # Set args for review-pr command with force
    mock_args.pr_number = 123
    mock_args.auto_post = False
    mock_args.force = True

    from runners.github.runner import cmd_review_pr

    exit_code = await cmd_review_pr(mock_args)

    assert exit_code == 0
    mock_orchestrator.review_pr.assert_called_once_with(123, force_review=True)


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_followup_review_pr_success(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_followup_review_pr with successful review."""
    # Setup mocks
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_result = PRReviewResult(
        pr_number=123,
        repo="owner/repo",
        success=True,
        findings=[],
        summary="No new commits since last review",
        overall_status="approve",
        verdict=MergeVerdict.READY_TO_MERGE,
        is_followup_review=True,
        resolved_findings=[],
        unresolved_findings=[],
        new_findings_since_last_review=[],
    )

    mock_orchestrator = AsyncMock()
    mock_orchestrator.followup_review_pr = AsyncMock(return_value=mock_result)
    mock_orchestrator_class.return_value = mock_orchestrator

    # Set args for followup-review-pr command
    mock_args.pr_number = 123

    from runners.github.runner import cmd_followup_review_pr

    exit_code = await cmd_followup_review_pr(mock_args)

    assert exit_code == 0
    mock_orchestrator.followup_review_pr.assert_called_once_with(123)


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_followup_review_pr_no_previous_review(
    mock_orchestrator_class, mock_get_config, mock_args
):
    """Test cmd_followup_review_pr when no previous review exists."""
    # Setup mocks
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_orchestrator = AsyncMock()
    mock_orchestrator.followup_review_pr = AsyncMock(
        side_effect=ValueError("No previous review found")
    )
    mock_orchestrator_class.return_value = mock_orchestrator

    # Set args for followup-review-pr command
    mock_args.pr_number = 123

    from runners.github.runner import cmd_followup_review_pr

    exit_code = await cmd_followup_review_pr(mock_args)

    assert exit_code == 1


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_triage(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_triage."""
    # Setup mocks
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    from runners.github.models import TriageResult, TriageCategory

    mock_results = [
        TriageResult(
            issue_number=1,
            repo="owner/repo",
            category=TriageCategory.BUG,
            confidence=0.9,
            is_duplicate=False,
            is_spam=False,
            is_feature_creep=False,
            labels_to_add=["bug"],
            labels_to_remove=[],
        ),
        TriageResult(
            issue_number=2,
            repo="owner/repo",
            category=TriageCategory.FEATURE,
            confidence=0.8,
            is_duplicate=True,
            duplicate_of=1,
            is_spam=False,
            is_feature_creep=False,
            labels_to_add=["duplicate"],
            labels_to_remove=[],
        ),
    ]

    mock_orchestrator = AsyncMock()
    mock_orchestrator.triage_issues = AsyncMock(return_value=mock_results)
    mock_orchestrator_class.return_value = mock_orchestrator

    # Set args for triage command
    mock_args.issues = [1, 2]
    mock_args.apply_labels = False

    from runners.github.runner import cmd_triage

    exit_code = await cmd_triage(mock_args)

    assert exit_code == 0
    mock_orchestrator.triage_issues.assert_called_once_with(
        issue_numbers=[1, 2], apply_labels=False
    )


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_auto_fix(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_auto_fix."""
    # Setup mocks
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_state = AutoFixState(
        issue_number=42,
        issue_url="https://github.com/owner/repo/issues/42",
        repo="owner/repo",
        status=AutoFixStatus.CREATING_SPEC,
        spec_id="spec-001",
        created_at="2025-01-01T00:00:00Z",
    )

    mock_orchestrator = AsyncMock()
    mock_orchestrator.auto_fix_issue = AsyncMock(return_value=mock_state)
    mock_orchestrator_class.return_value = mock_orchestrator

    # Set args for auto-fix command
    mock_args.issue_number = 42

    from runners.github.runner import cmd_auto_fix

    exit_code = await cmd_auto_fix(mock_args)

    assert exit_code == 0
    mock_orchestrator.auto_fix_issue.assert_called_once_with(42)


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_check_labels(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_check_labels."""
    # Setup mocks
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_config.auto_fix_enabled = True
    mock_get_config.return_value = mock_config

    mock_orchestrator = AsyncMock()
    mock_orchestrator.check_auto_fix_labels = AsyncMock(return_value=[1, 2, 3])
    mock_orchestrator_class.return_value = mock_orchestrator

    from runners.github.runner import cmd_check_labels

    # Create empty args for check-auto-fix-labels command
    args = argparse.Namespace(
        project=mock_args.project,
        token=mock_args.token,
        bot_token=mock_args.bot_token,
        repo=mock_args.repo,
        model=mock_args.model,
        thinking_level=mock_args.thinking_level,
    )

    exit_code = await cmd_check_labels(args)

    assert exit_code == 0
    mock_orchestrator.check_auto_fix_labels.assert_called_once()


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_check_new(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_check_new."""
    # Setup mocks
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_config.auto_fix_enabled = True
    mock_get_config.return_value = mock_config

    mock_orchestrator = AsyncMock()
    mock_orchestrator.check_new_issues = AsyncMock(return_value=[{"number": 1}, {"number": 2}])
    mock_orchestrator_class.return_value = mock_orchestrator

    from runners.github.runner import cmd_check_new

    # Create empty args for check-new command
    args = argparse.Namespace(
        project=mock_args.project,
        token=mock_args.token,
        bot_token=mock_args.bot_token,
        repo=mock_args.repo,
        model=mock_args.model,
        thinking_level=mock_args.thinking_level,
    )

    exit_code = await cmd_check_new(args)

    assert exit_code == 0
    mock_orchestrator.check_new_issues.assert_called_once()


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_queue(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_queue."""
    # Setup mocks
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_queue = [
        AutoFixState(
            issue_number=1,
            issue_url="https://github.com/owner/repo/issues/1",
            repo="owner/repo",
            status=AutoFixStatus.BUILDING,
            spec_id="spec-001",
            created_at="2025-01-01T00:00:00Z",
        ),
        AutoFixState(
            issue_number=2,
            issue_url="https://github.com/owner/repo/issues/2",
            repo="owner/repo",
            status=AutoFixStatus.PENDING,
            created_at="2025-01-01T01:00:00Z",
        ),
    ]

    mock_orchestrator = AsyncMock()
    mock_orchestrator.get_auto_fix_queue = AsyncMock(return_value=mock_queue)
    mock_orchestrator_class.return_value = mock_orchestrator

    from runners.github.runner import cmd_queue

    # Create empty args for queue command
    args = argparse.Namespace(
        project=mock_args.project,
        token=mock_args.token,
        bot_token=mock_args.bot_token,
        repo=mock_args.repo,
        model=mock_args.model,
        thinking_level=mock_args.thinking_level,
    )

    exit_code = await cmd_queue(args)

    assert exit_code == 0
    mock_orchestrator.get_auto_fix_queue.assert_called_once()


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_batch_issues(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_batch_issues."""
    # Setup mocks
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_config.auto_fix_enabled = True
    mock_get_config.return_value = mock_config

    mock_orchestrator = AsyncMock()
    mock_orchestrator.batch_and_fix_issues = AsyncMock(return_value=[])
    mock_orchestrator_class.return_value = mock_orchestrator

    from runners.github.runner import cmd_batch_issues

    # Set args for batch-issues command
    mock_args.issues = [1, 2, 3]

    exit_code = await cmd_batch_issues(mock_args)

    assert exit_code == 0
    mock_orchestrator.batch_and_fix_issues.assert_called_once_with([1, 2, 3])


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_batch_status(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_batch_status."""
    # Setup mocks
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_status = {
        "total_batches": 5,
        "pending": 1,
        "processing": 2,
        "completed": 2,
        "failed": 0,
    }

    mock_orchestrator = AsyncMock()
    mock_orchestrator.get_batch_status = AsyncMock(return_value=mock_status)
    mock_orchestrator_class.return_value = mock_orchestrator

    from runners.github.runner import cmd_batch_status

    # Create empty args for batch-status command
    args = argparse.Namespace(
        project=mock_args.project,
        token=mock_args.token,
        bot_token=mock_args.bot_token,
        repo=mock_args.repo,
        model=mock_args.model,
        thinking_level=mock_args.thinking_level,
    )

    exit_code = await cmd_batch_status(args)

    assert exit_code == 0


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_analyze_preview(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_analyze_preview."""
    # Setup mocks
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_preview = {
        "success": True,
        "total_issues": 10,
        "analyzed_issues": 10,
        "proposed_batches": [],
        "single_issues": [],
    }

    mock_orchestrator = AsyncMock()
    mock_orchestrator.analyze_issues_preview = AsyncMock(return_value=mock_preview)
    mock_orchestrator_class.return_value = mock_orchestrator

    from runners.github.runner import cmd_analyze_preview

    # Set args for analyze-preview command
    mock_args.issues = [1, 2, 3]
    mock_args.max_issues = 100
    mock_args.json = False

    exit_code = await cmd_analyze_preview(mock_args)

    assert exit_code == 0
    mock_orchestrator.analyze_issues_preview.assert_called_once_with(
        issue_numbers=[1, 2, 3], max_issues=100
    )


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_approve_batches(mock_orchestrator_class, mock_get_config, temp_project_dir):
    """Test cmd_approve_batches."""
    # Setup mocks
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_orchestrator = AsyncMock()
    mock_orchestrator.approve_and_execute_batches = AsyncMock(return_value=[])
    mock_orchestrator_class.return_value = mock_orchestrator

    # Create temporary batch file
    import json

    batch_file = temp_project_dir / "batches.json"
    batch_data = [{"batch_id": "batch-1", "theme": "Fixes"}]
    batch_file.write_text(json.dumps(batch_data))

    from runners.github.runner import cmd_approve_batches

    # Create args for approve-batches command
    args = argparse.Namespace(
        project=temp_project_dir,
        token="test_token",
        bot_token=None,
        repo=None,
        model="claude-sonnet-4-5-20250929",
        thinking_level="medium",
        batch_file=batch_file,
    )

    exit_code = await cmd_approve_batches(args)

    assert exit_code == 0
    mock_orchestrator.approve_and_execute_batches.assert_called_once()


@patch("runners.github.runner.sys.exit")
@patch("argparse.ArgumentParser.parse_args")
@patch("asyncio.run")
def test_main_entrypoint(mock_asyncio_run, mock_parse_args, mock_sys_exit):
    """Test main() entry point."""
    # Mock args
    mock_args = MagicMock()
    mock_args.command = "review-pr"
    mock_args.project = Path("/test/project")
    mock_parse_args.return_value = mock_args

    # Mock asyncio.run to return exit code
    mock_asyncio_run.return_value = 0

    from runners.github.runner import main

    main()

    mock_asyncio_run.assert_called_once()
    mock_sys_exit.assert_called_once_with(0)


@patch("runners.github.runner.asyncio.run")
@patch("runners.github.runner.sys.exit")
@patch("argparse.ArgumentParser.parse_args")
def test_main_no_command(mock_parse_args, mock_sys_exit, mock_asyncio_run):
    """Test main() with no command specified."""
    mock_args = MagicMock()
    mock_args.command = None
    mock_parse_args.return_value = mock_args
    # Make sys.exit actually raise SystemExit to stop execution
    mock_sys_exit.side_effect = SystemExit

    from runners.github.runner import main

    with pytest.raises(SystemExit):
        main()

    mock_sys_exit.assert_called_once_with(1)


@patch("runners.github.runner.safe_print")
@patch("argparse.ArgumentParser.parse_args")
@patch("sys.exit")
def test_main_keyboard_interrupt(mock_sys_exit, mock_parse_args, mock_safe_print):
    """Test main() handling KeyboardInterrupt."""
    mock_args = MagicMock()
    mock_args.command = "review-pr"
    mock_parse_args.return_value = mock_args

    with patch("asyncio.run", side_effect=KeyboardInterrupt):
        from runners.github.runner import main

        main()

    mock_sys_exit.assert_called_once_with(1)


@patch("runners.github.runner.capture_exception")
@patch("runners.github.runner.debug_error")
@patch("runners.github.runner.safe_print")
@patch("traceback.print_exc")
@patch("argparse.ArgumentParser.parse_args")
@patch("sys.exit")
def test_main_exception(
    mock_sys_exit, mock_parse_args, mock_print_exc, mock_safe_print, mock_debug_error, mock_capture_exception
):
    """Test main() handling generic exception."""
    mock_args = MagicMock()
    mock_args.command = "review-pr"
    mock_args.project = Path("/test")
    mock_args.repo = "test/repo"
    mock_parse_args.return_value = mock_args

    with patch("asyncio.run", side_effect=Exception("Test error")):
        from runners.github.runner import main

        main()

    mock_sys_exit.assert_called_once_with(1)
    mock_capture_exception.assert_called_once()


# ============================================================================
# Additional Edge Case Tests
# ============================================================================


@patch("core.gh_executable.get_gh_executable")
@patch("subprocess.run")
def test_get_config_missing_token_and_no_gh(mock_run, mock_gh_executable, temp_project_dir, capsys):
    """Test get_config when no token available and gh CLI fails."""
    mock_gh_executable.return_value = "gh"
    # gh auth token fails
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Not logged in")

    args = argparse.Namespace(
        project=temp_project_dir,
        token=None,
        bot_token=None,
        repo="owner/repo",
        model="claude-sonnet-4-5-20250929",
        thinking_level="medium",
    )

    from runners.github.runner import get_config

    with pytest.raises(SystemExit) as exc_info:
        get_config(args)

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "No GitHub token found" in captured.out


@patch("core.gh_executable.get_gh_executable")
@patch("subprocess.run")
@patch.dict("os.environ", {}, clear=True)
def test_get_config_missing_repo(mock_run, mock_gh_executable, temp_project_dir, capsys):
    """Test get_config when no repo can be determined."""
    mock_gh_executable.return_value = "gh"
    # gh auth token succeeds but gh repo view fails
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout="gh_token", stderr=""),  # auth token
        MagicMock(returncode=1, stdout="", stderr="Not a git repo"),  # repo view
    ]

    args = argparse.Namespace(
        project=temp_project_dir,
        token=None,
        bot_token=None,
        repo=None,
        model="claude-sonnet-4-5-20250929",
        thinking_level="medium",
    )

    from runners.github.runner import get_config

    with pytest.raises(SystemExit) as exc_info:
        get_config(args)

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "No GitHub repo found" in captured.out


@patch("core.gh_executable.get_gh_executable")
@patch("subprocess.run")
def test_get_config_with_all_explicit_args(mock_run, mock_gh_executable, mock_args):
    """Test get_config when all args are explicitly provided."""
    mock_gh_executable.return_value = "gh"

    config = get_config(mock_args)

    assert config.token == "test_token"
    assert config.bot_token == "test_bot_token"
    assert config.repo == "owner/repo"
    assert config.model == "claude-sonnet-4-5-20250929"
    assert config.thinking_level == "medium"
    # Should not call subprocess when all args provided
    mock_run.assert_not_called()


@patch("core.gh_executable.get_gh_executable")
@patch("subprocess.run")
def test_get_config_with_bot_token(mock_run, mock_gh_executable, temp_project_dir):
    """Test get_config with bot token from environment."""
    mock_gh_executable.return_value = "gh"
    mock_run.return_value = MagicMock(returncode=0, stdout="gh_token", stderr="")

    args = argparse.Namespace(
        project=temp_project_dir,
        token=None,
        bot_token=None,
        repo="owner/repo",
        model="claude-sonnet-4-5-20250929",
        thinking_level="medium",
    )

    with patch.dict("os.environ", {"GITHUB_BOT_TOKEN": "env_bot_token"}):
        config = get_config(args)

    assert config.token == "gh_token"
    assert config.bot_token == "env_bot_token"


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_review_pr_with_findings(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_review_pr with multiple findings of different severities."""
    from runners.github.models import ReviewSeverity, ReviewCategory

    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_result = PRReviewResult(
        pr_number=123,
        repo="owner/repo",
        success=True,
        findings=[
            PRReviewFinding(
                id="1",
                severity=ReviewSeverity.CRITICAL,
                category=ReviewCategory.SECURITY,
                title="Security vulnerability",
                description="Critical security issue",
                file="auth.py",
                line=10,
            ),
            PRReviewFinding(
                id="2",
                severity=ReviewSeverity.HIGH,
                category=ReviewCategory.QUALITY,
                title="Null pointer dereference",
                description="Potential crash",
                file="utils.py",
                line=42,
            ),
            PRReviewFinding(
                id="3",
                severity=ReviewSeverity.MEDIUM,
                category=ReviewCategory.PERFORMANCE,
                title="Inefficient loop",
                description="O(n^2) complexity",
                file="processor.py",
                line=100,
            ),
        ],
        summary="Found several issues that need attention",
        overall_status="request_changes",
        verdict=MergeVerdict.NEEDS_REVISION,
    )

    mock_orchestrator = AsyncMock()
    mock_orchestrator.review_pr = AsyncMock(return_value=mock_result)
    mock_orchestrator_class.return_value = mock_orchestrator

    mock_args.pr_number = 123
    mock_args.auto_post = False
    mock_args.force = False

    from runners.github.runner import cmd_review_pr

    exit_code = await cmd_review_pr(mock_args)

    assert exit_code == 0


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_review_pr_exception_handling(
    mock_orchestrator_class, mock_get_config, mock_args
):
    """Test cmd_review_pr handles exceptions from orchestrator."""
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_orchestrator = AsyncMock()
    mock_orchestrator.review_pr = AsyncMock(side_effect=Exception("API timeout"))
    mock_orchestrator_class.return_value = mock_orchestrator

    mock_args.pr_number = 123
    mock_args.auto_post = False
    mock_args.force = False

    from runners.github.runner import cmd_review_pr

    with pytest.raises(Exception, match="API timeout"):
        await cmd_review_pr(mock_args)


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_followup_review_pr_with_findings(
    mock_orchestrator_class, mock_get_config, mock_args
):
    """Test cmd_followup_review_pr with resolved and unresolved findings."""
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_result = PRReviewResult(
        pr_number=123,
        repo="owner/repo",
        success=True,
        findings=[
            PRReviewFinding(
                id="3",
                severity=ReviewSeverity.LOW,
                category=ReviewCategory.STYLE,
                title="Minor style issue",
                description="Style suggestion",
                file="app.py",
                line=50,
            )
        ],
        summary="Some issues resolved, one remains",
        overall_status="approve",
        verdict=MergeVerdict.READY_TO_MERGE,
        is_followup_review=True,
        resolved_findings=[
            PRReviewFinding(
                id="1",
                severity=ReviewSeverity.HIGH,
                category=ReviewCategory.QUALITY,
                title="Fixed bug",
                description="This was fixed",
                file="fix.py",
                line=10,
            )
        ],
        unresolved_findings=[
            PRReviewFinding(
                id="2",
                severity=ReviewSeverity.MEDIUM,
                category=ReviewCategory.PERFORMANCE,
                title="Still needs work",
                description="Not yet addressed",
                file="slow.py",
                line=20,
            )
        ],
        new_findings_since_last_review=[
            PRReviewFinding(
                id="3",
                severity=ReviewSeverity.LOW,
                category=ReviewCategory.STYLE,
                title="New issue",
                description="Introduced in new commit",
                file="new.py",
                line=5,
            )
        ],
    )

    mock_orchestrator = AsyncMock()
    mock_orchestrator.followup_review_pr = AsyncMock(return_value=mock_result)
    mock_orchestrator_class.return_value = mock_orchestrator

    mock_args.pr_number = 123

    from runners.github.runner import cmd_followup_review_pr

    exit_code = await cmd_followup_review_pr(mock_args)

    assert exit_code == 0


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_followup_review_pr_generic_exception(
    mock_orchestrator_class, mock_get_config, mock_args
):
    """Test cmd_followup_review_pr handles generic exceptions."""
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_orchestrator = AsyncMock()
    mock_orchestrator.followup_review_pr = AsyncMock(side_effect=RuntimeError("Network error"))
    mock_orchestrator_class.return_value = mock_orchestrator

    mock_args.pr_number = 123

    from runners.github.runner import cmd_followup_review_pr

    with pytest.raises(RuntimeError, match="Network error"):
        await cmd_followup_review_pr(mock_args)


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_triage_empty_results(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_triage with no issues to triage."""
    from runners.github.models import TriageResult

    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_orchestrator = AsyncMock()
    mock_orchestrator.triage_issues = AsyncMock(return_value=[])
    mock_orchestrator_class.return_value = mock_orchestrator

    mock_args.issues = None
    mock_args.apply_labels = False

    from runners.github.runner import cmd_triage

    exit_code = await cmd_triage(mock_args)

    assert exit_code == 0
    mock_orchestrator.triage_issues.assert_called_once_with(issue_numbers=None, apply_labels=False)


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_triage_with_flags(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_triage with spam, duplicate, and feature creep flags."""
    from runners.github.models import TriageResult, TriageCategory

    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_results = [
        TriageResult(
            issue_number=1,
            repo="owner/repo",
            category=TriageCategory.SPAM,
            confidence=0.95,
            is_duplicate=False,
            is_spam=True,
            is_feature_creep=False,
            labels_to_add=["spam"],
            labels_to_remove=[],
        ),
        TriageResult(
            issue_number=2,
            repo="owner/repo",
            category=TriageCategory.BUG,
            confidence=0.85,
            is_duplicate=False,
            is_spam=False,
            is_feature_creep=True,
            labels_to_add=["bug", "feature-creep"],
            labels_to_remove=[],
        ),
    ]

    mock_orchestrator = AsyncMock()
    mock_orchestrator.triage_issues = AsyncMock(return_value=mock_results)
    mock_orchestrator_class.return_value = mock_orchestrator

    mock_args.issues = [1, 2]
    mock_args.apply_labels = True

    from runners.github.runner import cmd_triage

    exit_code = await cmd_triage(mock_args)

    assert exit_code == 0
    mock_orchestrator.triage_issues.assert_called_once_with(issue_numbers=[1, 2], apply_labels=True)


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_auto_fix_with_pr_number(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_auto_fix when a PR has been created."""
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_state = AutoFixState(
        issue_number=42,
        issue_url="https://github.com/owner/repo/issues/42",
        repo="owner/repo",
        status=AutoFixStatus.PR_CREATED,
        spec_id="spec-001",
        pr_number=123,
        created_at="2025-01-01T00:00:00Z",
    )

    mock_orchestrator = AsyncMock()
    mock_orchestrator.auto_fix_issue = AsyncMock(return_value=mock_state)
    mock_orchestrator_class.return_value = mock_orchestrator

    mock_args.issue_number = 42

    from runners.github.runner import cmd_auto_fix

    exit_code = await cmd_auto_fix(mock_args)

    assert exit_code == 0


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_auto_fix_with_error(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_auto_fix when auto-fix has failed."""
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_state = AutoFixState(
        issue_number=42,
        issue_url="https://github.com/owner/repo/issues/42",
        repo="owner/repo",
        status=AutoFixStatus.FAILED,
        spec_id="spec-001",
        created_at="2025-01-01T00:00:00Z",
        error="Build failed: compilation error",
    )

    mock_orchestrator = AsyncMock()
    mock_orchestrator.auto_fix_issue = AsyncMock(return_value=mock_state)
    mock_orchestrator_class.return_value = mock_orchestrator

    mock_args.issue_number = 42

    from runners.github.runner import cmd_auto_fix

    exit_code = await cmd_auto_fix(mock_args)

    assert exit_code == 0


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_check_labels_empty(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_check_labels when no issues with labels found."""
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_config.auto_fix_enabled = True
    mock_get_config.return_value = mock_config

    mock_orchestrator = AsyncMock()
    mock_orchestrator.check_auto_fix_labels = AsyncMock(return_value=[])
    mock_orchestrator_class.return_value = mock_orchestrator

    args = argparse.Namespace(
        project=mock_args.project,
        token=mock_args.token,
        bot_token=mock_args.bot_token,
        repo=mock_args.repo,
        model=mock_args.model,
        thinking_level=mock_args.thinking_level,
    )

    from runners.github.runner import cmd_check_labels

    exit_code = await cmd_check_labels(args)

    assert exit_code == 0
    mock_orchestrator.check_auto_fix_labels.assert_called_once()


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_check_new_with_issues(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_check_new returns JSON with new issues."""
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_config.auto_fix_enabled = True
    mock_get_config.return_value = mock_config

    mock_orchestrator = AsyncMock()
    mock_orchestrator.check_new_issues = AsyncMock(
        return_value=[
            {"number": 10, "title": "New bug"},
            {"number": 11, "title": "Feature request"},
        ]
    )
    mock_orchestrator_class.return_value = mock_orchestrator

    args = argparse.Namespace(
        project=mock_args.project,
        token=mock_args.token,
        bot_token=mock_args.bot_token,
        repo=mock_args.repo,
        model=mock_args.model,
        thinking_level=mock_args.thinking_level,
    )

    from runners.github.runner import cmd_check_new

    exit_code = await cmd_check_new(args)

    assert exit_code == 0


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_queue_empty(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_queue with empty queue."""
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_orchestrator = AsyncMock()
    mock_orchestrator.get_auto_fix_queue = AsyncMock(return_value=[])
    mock_orchestrator_class.return_value = mock_orchestrator

    args = argparse.Namespace(
        project=mock_args.project,
        token=mock_args.token,
        bot_token=mock_args.bot_token,
        repo=mock_args.repo,
        model=mock_args.model,
        thinking_level=mock_args.thinking_level,
    )

    from runners.github.runner import cmd_queue

    exit_code = await cmd_queue(args)

    assert exit_code == 0


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_queue_with_all_statuses(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_queue displays all different status types."""
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_queue = [
        AutoFixState(
            issue_number=1,
            issue_url="https://github.com/owner/repo/issues/1",
            repo="owner/repo",
            status=AutoFixStatus.PENDING,
            spec_id="spec-001",
            created_at="2025-01-01T00:00:00Z",
        ),
        AutoFixState(
            issue_number=2,
            issue_url="https://github.com/owner/repo/issues/2",
            repo="owner/repo",
            status=AutoFixStatus.COMPLETED,
            spec_id="spec-002",
            pr_number=100,
            created_at="2025-01-01T01:00:00Z",
        ),
        AutoFixState(
            issue_number=3,
            issue_url="https://github.com/owner/repo/issues/3",
            repo="owner/repo",
            status=AutoFixStatus.FAILED,
            spec_id="spec-003",
            created_at="2025-01-01T02:00:00Z",
            error="Timeout waiting for build",
        ),
    ]

    mock_orchestrator = AsyncMock()
    mock_orchestrator.get_auto_fix_queue = AsyncMock(return_value=mock_queue)
    mock_orchestrator_class.return_value = mock_orchestrator

    args = argparse.Namespace(
        project=mock_args.project,
        token=mock_args.token,
        bot_token=mock_args.bot_token,
        repo=mock_args.repo,
        model=mock_args.model,
        thinking_level=mock_args.thinking_level,
    )

    from runners.github.runner import cmd_queue

    exit_code = await cmd_queue(args)

    assert exit_code == 0


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_batch_issues_no_batches(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_batch_issues when no batches are created."""
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_config.auto_fix_enabled = True
    mock_get_config.return_value = mock_config

    mock_orchestrator = AsyncMock()
    mock_orchestrator.batch_and_fix_issues = AsyncMock(return_value=[])
    mock_orchestrator_class.return_value = mock_orchestrator

    mock_args.issues = [1, 2, 3]

    from runners.github.runner import cmd_batch_issues

    exit_code = await cmd_batch_issues(mock_args)

    assert exit_code == 0


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_batch_issues_with_multiple_batches(
    mock_orchestrator_class, mock_get_config, mock_args
):
    """Test cmd_batch_issues with multiple batches created."""
    from runners.github.batch_issues import IssueBatch, BatchStatus

    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_config.auto_fix_enabled = True
    mock_get_config.return_value = mock_config

    # Create mock batches
    from runners.github.batch_issues import IssueBatchItem

    mock_batches = [
        IssueBatch(
            batch_id="batch-1",
            repo="owner/repo",
            primary_issue=1,
            theme="Authentication fixes",
            status=BatchStatus.PENDING,
            issues=[
                IssueBatchItem(
                    issue_number=1,
                    title="Login fails",
                    body="Cannot login",
                    similarity_to_primary=1.0,
                ),
                IssueBatchItem(
                    issue_number=2,
                    title="Auth error",
                    body="Cannot auth",
                    similarity_to_primary=0.9,
                ),
            ],
            spec_id="spec-001",
            created_at="2025-01-01T00:00:00Z",
        ),
        IssueBatch(
            batch_id="batch-2",
            repo="owner/repo",
            primary_issue=3,
            theme="Performance improvements",
            status=BatchStatus.BUILDING,
            issues=[
                IssueBatchItem(
                    issue_number=3,
                    title="Slow query",
                    body="Query is slow",
                    similarity_to_primary=1.0,
                ),
            ],
            spec_id="spec-002",
            created_at="2025-01-01T01:00:00Z",
        ),
    ]

    mock_orchestrator = AsyncMock()
    mock_orchestrator.batch_and_fix_issues = AsyncMock(return_value=mock_batches)
    mock_orchestrator_class.return_value = mock_orchestrator

    mock_args.issues = [1, 2]

    from runners.github.runner import cmd_batch_issues

    exit_code = await cmd_batch_issues(mock_args)

    assert exit_code == 0


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_batch_issues_all_open(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_batch_issues with no specific issues (all open)."""
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_config.auto_fix_enabled = True
    mock_get_config.return_value = mock_config

    mock_orchestrator = AsyncMock()
    mock_orchestrator.batch_and_fix_issues = AsyncMock(return_value=[])
    mock_orchestrator_class.return_value = mock_orchestrator

    # No specific issues - should batch all open
    mock_args.issues = None

    from runners.github.runner import cmd_batch_issues

    exit_code = await cmd_batch_issues(mock_args)

    assert exit_code == 0
    mock_orchestrator.batch_and_fix_issues.assert_called_once_with(None)


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_analyze_preview_with_error(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_analyze_preview when analysis fails."""
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_preview = {
        "success": False,
        "error": "Failed to connect to GitHub API",
    }

    mock_orchestrator = AsyncMock()
    mock_orchestrator.analyze_issues_preview = AsyncMock(return_value=mock_preview)
    mock_orchestrator_class.return_value = mock_orchestrator

    mock_args.issues = [1, 2, 3]
    mock_args.max_issues = 100
    mock_args.json = False

    from runners.github.runner import cmd_analyze_preview

    exit_code = await cmd_analyze_preview(mock_args)

    assert exit_code == 1


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_analyze_preview_with_batches(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_analyze_preview with proposed batches."""
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_preview = {
        "success": True,
        "total_issues": 15,
        "analyzed_issues": 15,
        "already_batched": 5,
        "proposed_batches": [
            {
                "theme": "Authentication issues",
                "confidence": 0.92,
                "validated": True,
                "primary_issue": 1,
                "issue_count": 5,
                "reasoning": "All relate to login failures",
                "issues": [
                    {"issue_number": 1, "title": "Login fails", "similarity_to_primary": 1.0},
                    {"issue_number": 5, "title": "Cannot auth", "similarity_to_primary": 0.89},
                ],
            },
            {
                "theme": "UI bugs",
                "confidence": 0.75,
                "validated": False,
                "primary_issue": 10,
                "issue_count": 3,
                "reasoning": "Similar UI rendering problems",
                "issues": [
                    {"issue_number": 10, "title": "Button misaligned", "similarity_to_primary": 1.0},
                ],
            },
        ],
        "single_issues": [
            {"issue_number": 20, "title": "Unique feature request"},
        ],
    }

    mock_orchestrator = AsyncMock()
    mock_orchestrator.analyze_issues_preview = AsyncMock(return_value=mock_preview)
    mock_orchestrator_class.return_value = mock_orchestrator

    mock_args.issues = None
    mock_args.max_issues = 100
    mock_args.json = False

    from runners.github.runner import cmd_analyze_preview

    exit_code = await cmd_analyze_preview(mock_args)

    assert exit_code == 0


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_analyze_preview_json_output(mock_orchestrator_class, mock_get_config, mock_args):
    """Test cmd_analyze_preview with JSON output enabled."""
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    mock_preview = {
        "success": True,
        "total_issues": 5,
        "analyzed_issues": 5,
        "already_batched": 0,
        "proposed_batches": [
            {
                "theme": "Test batch",
                "confidence": 0.9,
                "validated": True,
                "primary_issue": 1,
                "issue_count": 3,
                "reasoning": "Similar issues",
                "issues": [],
            },
        ],
        "single_issues": [],
    }

    mock_orchestrator = AsyncMock()
    mock_orchestrator.analyze_issues_preview = AsyncMock(return_value=mock_preview)
    mock_orchestrator_class.return_value = mock_orchestrator

    mock_args.issues = [1, 2, 3]
    mock_args.max_issues = 100
    mock_args.json = True

    from runners.github.runner import cmd_analyze_preview

    exit_code = await cmd_analyze_preview(mock_args)

    assert exit_code == 0


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_approve_batches_invalid_json(mock_orchestrator_class, mock_get_config, temp_project_dir):
    """Test cmd_approve_batches with invalid JSON file."""
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    # Create invalid JSON file
    batch_file = temp_project_dir / "invalid.json"
    batch_file.write_text("{ invalid json }")

    from runners.github.runner import cmd_approve_batches

    args = argparse.Namespace(
        project=temp_project_dir,
        token="test_token",
        bot_token=None,
        repo=None,
        model="claude-sonnet-4-5-20250929",
        thinking_level="medium",
        batch_file=batch_file,
    )

    exit_code = await cmd_approve_batches(args)

    assert exit_code == 1


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_approve_batches_file_not_found(mock_orchestrator_class, mock_get_config, temp_project_dir):
    """Test cmd_approve_batches with non-existent file."""
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    from runners.github.runner import cmd_approve_batches

    batch_file = temp_project_dir / "nonexistent.json"

    args = argparse.Namespace(
        project=temp_project_dir,
        token="test_token",
        bot_token=None,
        repo=None,
        model="claude-sonnet-4-5-20250929",
        thinking_level="medium",
        batch_file=batch_file,
    )

    exit_code = await cmd_approve_batches(args)

    assert exit_code == 1


@pytest.mark.asyncio
@patch("runners.github.runner.get_config")
@patch("runners.github.runner.GitHubOrchestrator")
async def test_cmd_approve_batches_empty_file(mock_orchestrator_class, mock_get_config, temp_project_dir):
    """Test cmd_approve_batches with empty JSON file."""
    mock_config = MagicMock(spec=GitHubRunnerConfig)
    mock_get_config.return_value = mock_config

    # Create empty JSON file
    import json

    batch_file = temp_project_dir / "empty.json"
    batch_file.write_text(json.dumps([]))

    # The orchestrator is created but approve_and_execute_batches should not be called
    mock_orchestrator = AsyncMock()
    mock_orchestrator.approve_and_execute_batches = AsyncMock(return_value=[])
    mock_orchestrator_class.return_value = mock_orchestrator

    from runners.github.runner import cmd_approve_batches

    args = argparse.Namespace(
        project=temp_project_dir,
        token="test_token",
        bot_token=None,
        repo=None,
        model="claude-sonnet-4-5-20250929",
        thinking_level="medium",
        batch_file=batch_file,
    )

    exit_code = await cmd_approve_batches(args)

    assert exit_code == 0
    # Orchestrator is created, but approve_and_execute_batches should not be called for empty file
    mock_orchestrator.approve_and_execute_batches.assert_not_called()


@patch("runners.github.runner.sys.exit")
@patch("argparse.ArgumentParser.parse_args")
@patch("asyncio.run")
def test_main_unknown_command(mock_asyncio_run, mock_parse_args, mock_sys_exit):
    """Test main() with unknown command."""
    mock_args = MagicMock()
    mock_args.command = "unknown-command"
    mock_args.project = Path("/test/project")
    mock_parse_args.return_value = mock_args

    # Make sys.exit actually raise SystemExit to stop execution
    mock_sys_exit.side_effect = SystemExit

    from runners.github.runner import main

    with pytest.raises(SystemExit):
        main()

    mock_sys_exit.assert_called_once_with(1)


@patch("runners.github.runner.safe_print")
@patch("argparse.ArgumentParser.parse_args")
@patch("sys.exit")
def test_main_sentry_context_set(mock_sys_exit, mock_parse_args, mock_safe_print):
    """Test that Sentry context is set correctly in main()."""
    mock_args = MagicMock()
    mock_args.command = "review-pr"
    mock_args.project = Path("/test/project")
    mock_args.repo = "owner/repo"
    mock_parse_args.return_value = mock_args

    with patch("asyncio.run", return_value=0):
        with patch("runners.github.runner.set_context") as mock_set_context:
            from runners.github.runner import main

            main()

            mock_set_context.assert_called_once_with(
                "command",
                {
                    "name": "review-pr",
                    "project": str(Path("/test/project")),
                    "repo": "owner/repo",
                },
            )


@patch("runners.github.runner.sys.exit")
@patch("argparse.ArgumentParser.parse_args")
@patch("asyncio.run")
def test_main_with_auto_post_review(mock_asyncio_run, mock_parse_args, mock_sys_exit):
    """Test main() with auto_post review flag."""
    mock_args = MagicMock()
    mock_args.command = "review-pr"
    mock_args.project = Path("/test/project")
    mock_args.auto_post = True
    mock_args.pr_number = 123
    mock_parse_args.return_value = mock_args

    mock_asyncio_run.return_value = 0

    from runners.github.runner import main

    main()

    # Verify handler was called with args
    mock_asyncio_run.assert_called_once()
    mock_sys_exit.assert_called_once_with(0)


def test_print_progress_with_all_fields():
    """Test print_progress with all optional fields set."""
    from runners.github.runner import ProgressCallback

    # Callback with pr_number takes precedence
    callback = ProgressCallback(
        phase="building",
        progress=42,
        message="Building spec",
        pr_number=100,
        issue_number=200,  # Should be ignored when pr_number is set
    )

    from runners.github.runner import print_progress

    # Should not raise exception
    print_progress(callback)


def test_progress_callback_model():
    """Test ProgressCallback model validation."""
    from runners.github.runner import ProgressCallback

    # Test with required fields only
    callback = ProgressCallback(
        phase="test",
        progress=50,
        message="Test message",
    )

    assert callback.phase == "test"
    assert callback.progress == 50
    assert callback.message == "Test message"
    assert callback.pr_number is None
    assert callback.issue_number is None

    # Test with optional fields
    callback2 = ProgressCallback(
        phase="review",
        progress=100,
        message="Complete",
        pr_number=123,
    )

    assert callback2.pr_number == 123
    assert callback2.issue_number is None
