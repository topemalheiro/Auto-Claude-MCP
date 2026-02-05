"""
Tests for GitLab Runner
========================

Tests for runners.gitlab.runner - GitLab automation CLI runner
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime

import pytest

from runners.gitlab.models import (
    GitLabRunnerConfig,
    MergeVerdict,
    MRReviewFinding,
    MRReviewResult,
    ReviewCategory,
    ReviewSeverity,
)
from runners.gitlab.runner import get_config, main, print_progress, cmd_review_mr, cmd_followup_review_mr


class TestPrintProgress:
    """Tests for print_progress function."""

    def test_print_progress_with_mr_iid(self, capsys):
        """Test print_progress with MR IID."""
        from runners.gitlab.orchestrator import ProgressCallback

        callback = ProgressCallback(
            phase="analyzing", progress=50, message="Processing...", mr_iid=123
        )

        print_progress(callback)

        captured = capsys.readouterr()
        assert "[MR !123]" in captured.out
        assert "50%" in captured.out  # Format has padding
        assert "Processing..." in captured.out

    def test_print_progress_without_mr_iid(self, capsys):
        """Test print_progress without MR IID."""
        from runners.gitlab.orchestrator import ProgressCallback

        callback = ProgressCallback(
            phase="initializing", progress=0, message="Starting..."
        )

        print_progress(callback)

        captured = capsys.readouterr()
        assert "[MR !" not in captured.out
        assert "0%" in captured.out
        assert "Starting..." in captured.out

    def test_print_progress_100_percent(self, capsys):
        """Test print_progress with 100% progress."""
        from runners.gitlab.orchestrator import ProgressCallback

        callback = ProgressCallback(
            phase="complete", progress=100, message="Complete!", mr_iid=456
        )

        print_progress(callback)

        captured = capsys.readouterr()
        assert "[MR !456]" in captured.out
        assert "100%" in captured.out
        assert "Complete!" in captured.out

    def test_print_progress_single_digit_progress(self, capsys):
        """Test print_progress with single digit progress."""
        from runners.gitlab.orchestrator import ProgressCallback

        callback = ProgressCallback(
            phase="starting", progress=5, message="Initializing..."
        )

        print_progress(callback)

        captured = capsys.readouterr()
        assert "  5%" in captured.out  # Should be padded to 3 digits


class TestGetConfig:
    """Tests for get_config function."""

    @pytest.fixture
    def base_args(self, tmp_path):
        """Create base args object."""
        class Args:
            project_dir = tmp_path
            token = None
            project = None
            instance = None
            model = "test-model"
            thinking_level = "medium"

        return Args()

    def test_get_config_from_explicit_args(self, base_args):
        """Test get_config from explicit CLI arguments."""
        base_args.token = "cli_token"
        base_args.project = "group/project"
        base_args.instance = "https://custom.gitlab.com"

        config = get_config(base_args)

        assert config.token == "cli_token"
        assert config.project == "group/project"
        assert config.instance_url == "https://custom.gitlab.com"
        assert config.model == "test-model"
        assert config.thinking_level == "medium"

    def test_get_config_from_env_vars(self, base_args, monkeypatch):
        """Test get_config from environment variables."""
        monkeypatch.setenv("GITLAB_TOKEN", "env_token")
        monkeypatch.setenv("GITLAB_PROJECT", "group/env-project")
        monkeypatch.setenv("GITLAB_INSTANCE_URL", "https://env.gitlab.com")

        config = get_config(base_args)

        assert config.token == "env_token"
        assert config.project == "group/env-project"
        assert config.instance_url == "https://env.gitlab.com"

    def test_get_config_explicit_overrides_env(self, base_args, monkeypatch):
        """Test that explicit args override environment variables."""
        base_args.token = "cli_token"
        base_args.project = "group/cli-project"

        monkeypatch.setenv("GITLAB_TOKEN", "env_token")
        monkeypatch.setenv("GITLAB_PROJECT", "group/env-project")

        config = get_config(base_args)

        assert config.token == "cli_token"
        assert config.project == "group/cli-project"

    def test_get_config_from_project_config_file(self, base_args, tmp_path):
        """Test get_config reads from project config file."""
        # Create config file
        config_dir = tmp_path / ".auto-claude" / "gitlab"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"

        config_data = {
            "project": "group/config-project",
            "instance_url": "https://config.gitlab.com",
            "token": "config_token",
        }
        config_file.write_text(json.dumps(config_data))

        config = get_config(base_args)

        assert config.token == "config_token"
        assert config.project == "group/config-project"
        assert config.instance_url == "https://config.gitlab.com"

    def test_get_config_project_file_overrides_env(self, base_args, monkeypatch, tmp_path):
        """Test that project config file overrides env vars."""
        # Set token to avoid token error
        base_args.token = "test_token"

        # Create config file
        config_dir = tmp_path / ".auto-claude" / "gitlab"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"

        config_data = {
            "project": "group/config-project",
            "instance_url": "https://config.gitlab.com",
        }
        config_file.write_text(json.dumps(config_data))

        monkeypatch.setenv("GITLAB_PROJECT", "group/env-project")

        config = get_config(base_args)

        # Project config should take priority over env
        assert config.project == "group/config-project"

    def test_get_config_fallback_to_env_when_no_project_config(self, base_args, monkeypatch):
        """Test fallback to env vars when no project config exists."""
        monkeypatch.setenv("GITLAB_PROJECT", "group/env-project")
        monkeypatch.setenv("GITLAB_TOKEN", "env_token")

        config = get_config(base_args)

        assert config.token == "env_token"
        assert config.project == "group/env-project"

    def test_get_config_from_glab_cli(self, base_args, monkeypatch):
        """Test getting token from glab CLI."""
        # Set project so it doesn't exit
        base_args.project = "group/project"
        # Mock subprocess.run to simulate glab output
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Token: glab_token_123\n"

        with patch("subprocess.run", return_value=mock_result):
            config = get_config(base_args)

        assert config.token == "glab_token_123"

    def test_get_config_glab_cli_multiline_output(self, base_args):
        """Test parsing glab CLI output with multiple lines."""
        base_args.project = "group/project"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "GitLab.com\nToken: multi_line_token_456\nAuthenticated as: user\n"

        with patch("subprocess.run", return_value=mock_result):
            config = get_config(base_args)

        assert config.token == "multi_line_token_456"

    def test_get_config_glab_cli_not_available(self, base_args, monkeypatch):
        """Test when glab CLI is not available."""
        monkeypatch.setenv("GITLAB_TOKEN", "env_token")
        monkeypatch.setenv("GITLAB_PROJECT", "group/project")

        # Mock subprocess.run to raise FileNotFoundError
        with patch("subprocess.run", side_effect=FileNotFoundError):
            config = get_config(base_args)

        # Should fall back to env var
        assert config.token == "env_token"

    def test_get_config_glab_cli_non_zero_exit(self, base_args, monkeypatch):
        """Test when glab CLI returns non-zero exit code."""
        monkeypatch.setenv("GITLAB_TOKEN", "env_token")
        monkeypatch.setenv("GITLAB_PROJECT", "group/project")

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "Not authenticated"

        with patch("subprocess.run", return_value=mock_result):
            config = get_config(base_args)

        # Should fall back to env var
        assert config.token == "env_token"

    def test_get_config_missing_token_exits(self, base_args):
        """Test that missing token exits with error."""
        base_args.project = "group/project"  # Set project to avoid that error
        with pytest.raises(SystemExit) as exc_info:
            get_config(base_args)
        assert exc_info.value.code == 1

    def test_get_config_missing_project_exits(self, base_args, monkeypatch):
        """Test that missing project exits with error."""
        monkeypatch.setenv("GITLAB_TOKEN", "token")
        # No project set
        with pytest.raises(SystemExit) as exc_info:
            get_config(base_args)
        assert exc_info.value.code == 1

    def test_get_config_invalid_project_file(self, base_args, tmp_path, capsys):
        """Test handling of invalid project config file."""
        # Set token and project to avoid premature exits
        base_args.token = "token"
        base_args.project = "group/project"

        # Create invalid config file
        config_dir = tmp_path / ".auto-claude" / "gitlab"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"
        config_file.write_text("invalid json content")

        # Should print warning but not crash
        config = get_config(base_args)

        # Check that config was still created successfully
        assert config.token == "token"
        assert config.project == "group/project"

    def test_get_config_corrupt_json_file(self, base_args, tmp_path):
        """Test handling of corrupt JSON config file."""
        base_args.token = "token"
        base_args.project = "group/project"

        # Create corrupt config file
        config_dir = tmp_path / ".auto-claude" / "gitlab"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"
        config_file.write_text('{"project": "incomplete"')

        # Should handle gracefully
        config = get_config(base_args)
        assert config.token == "token"

    def test_get_config_default_instance_url(self, base_args):
        """Test default instance URL."""
        base_args.token = "token"
        base_args.project = "group/project"

        config = get_config(base_args)

        assert config.instance_url == "https://gitlab.com"

    def test_get_config_default_model_and_thinking(self, base_args):
        """Test default model and thinking_level are preserved."""
        base_args.token = "token"
        base_args.project = "group/project"

        config = get_config(base_args)

        assert config.model == "test-model"
        assert config.thinking_level == "medium"

    def test_get_config_explicit_instance_overrides_all(self, base_args, monkeypatch):
        """Test explicit instance URL overrides env and config file."""
        base_args.token = "token"
        base_args.project = "group/project"
        base_args.instance = "https://explicit.gitlab.com"

        # Set up env and config file that should be overridden
        monkeypatch.setenv("GITLAB_INSTANCE_URL", "https://env.gitlab.com")

        config_dir = base_args.project_dir / ".auto-claude" / "gitlab"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({"instance_url": "https://config.gitlab.com"}))

        config = get_config(base_args)
        assert config.instance_url == "https://explicit.gitlab.com"

    def test_get_config_partial_project_config(self, base_args, tmp_path):
        """Test project config file with partial data."""
        base_args.token = "cli_token"

        # Create config file with only project (no token or instance)
        config_dir = tmp_path / ".auto-claude" / "gitlab"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({"project": "group/from-config"}))

        config = get_config(base_args)
        assert config.project == "group/from-config"
        assert config.token == "cli_token"  # From CLI arg
        assert config.instance_url == "https://gitlab.com"  # Default


class TestCmdReviewMr:
    """Tests for cmd_review_mr function."""

    @pytest.fixture
    def base_args(self, tmp_path):
        """Create base args object."""
        class Args:
            project_dir = tmp_path
            token = "test_token"
            project = "group/project"
            instance = "https://gitlab.com"
            model = "test-model"
            thinking_level = "medium"
            mr_iid = 123

        return Args()

    @pytest.mark.asyncio
    async def test_cmd_review_mr_success(self, base_args, capsys):
        """Test cmd_review_mr successful execution."""
        mock_result = MRReviewResult(
            mr_iid=123,
            project="group/project",
            success=True,
            findings=[
                MRReviewFinding(
                    id="finding-1",
                    severity=ReviewSeverity.HIGH,
                    category=ReviewCategory.SECURITY,
                    title="Security issue",
                    description="Fix this",
                    file="auth.py",
                    line=10,
                )
            ],
            summary="Review complete",
            overall_status="request_changes",
            verdict=MergeVerdict.NEEDS_REVISION,
            verdict_reasoning="Issues found",
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.review_mr = AsyncMock(return_value=mock_result)

        with patch(
            "runners.gitlab.runner.GitLabOrchestrator", return_value=mock_orchestrator
        ):
            exit_code = await cmd_review_mr(base_args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "MR !123 Review Complete" in captured.out
        assert "Status: request_changes" in captured.out
        assert "Findings: 1" in captured.out

    @pytest.mark.asyncio
    async def test_cmd_review_mr_failure(self, base_args, capsys):
        """Test cmd_review_mr with review failure."""
        mock_result = MRReviewResult(
            mr_iid=123,
            project="group/project",
            success=False,
            error="API connection failed",
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.review_mr = AsyncMock(return_value=mock_result)

        with patch(
            "runners.gitlab.runner.GitLabOrchestrator", return_value=mock_orchestrator
        ):
            exit_code = await cmd_review_mr(base_args)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Review failed: API connection failed" in captured.out

    @pytest.mark.asyncio
    async def test_cmd_review_mr_with_multiple_findings(self, base_args, capsys):
        """Test cmd_review_mr with multiple findings."""
        mock_result = MRReviewResult(
            mr_iid=123,
            project="group/project",
            success=True,
            findings=[
                MRReviewFinding(
                    id="f1",
                    severity=ReviewSeverity.CRITICAL,
                    category=ReviewCategory.SECURITY,
                    title="Critical issue",
                    description="Fix now",
                    file="auth.py",
                    line=10,
                ),
                MRReviewFinding(
                    id="f2",
                    severity=ReviewSeverity.MEDIUM,
                    category=ReviewCategory.QUALITY,
                    title="Code quality",
                    description="Improve this",
                    file="utils.py",
                    line=50,
                ),
                MRReviewFinding(
                    id="f3",
                    severity=ReviewSeverity.LOW,
                    category=ReviewCategory.STYLE,
                    title="Style issue",
                    description="Minor style",
                    file="main.py",
                    line=100,
                ),
            ],
            summary="Review complete",
            overall_status="approve",
            verdict=MergeVerdict.READY_TO_MERGE,
            verdict_reasoning="Looks good",
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.review_mr = AsyncMock(return_value=mock_result)

        with patch(
            "runners.gitlab.runner.GitLabOrchestrator", return_value=mock_orchestrator
        ):
            exit_code = await cmd_review_mr(base_args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Findings: 3" in captured.out
        assert "[CRITICAL]" in captured.out
        assert "[MEDIUM]" in captured.out
        assert "[LOW]" in captured.out

    @pytest.mark.asyncio
    async def test_cmd_review_mr_with_empty_findings(self, base_args, capsys):
        """Test cmd_review_mr with no findings."""
        mock_result = MRReviewResult(
            mr_iid=123,
            project="group/project",
            success=True,
            findings=[],
            summary="No issues found",
            overall_status="approve",
            verdict=MergeVerdict.READY_TO_MERGE,
            verdict_reasoning="Clean review",
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.review_mr = AsyncMock(return_value=mock_result)

        with patch(
            "runners.gitlab.runner.GitLabOrchestrator", return_value=mock_orchestrator
        ):
            exit_code = await cmd_review_mr(base_args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Findings: 0" in captured.out
        assert "Status: approve" in captured.out

    @pytest.mark.asyncio
    async def test_cmd_review_mr_orchestrator_exception(self, base_args, capsys):
        """Test cmd_review_mr when orchestrator raises exception."""
        mock_orchestrator = MagicMock()
        mock_orchestrator.review_mr = AsyncMock(
            side_effect=RuntimeError("Orchestrator failed")
        )

        with patch(
            "runners.gitlab.runner.GitLabOrchestrator", return_value=mock_orchestrator
        ):
            with pytest.raises(RuntimeError, match="Orchestrator failed"):
                await cmd_review_mr(base_args)

    @pytest.mark.asyncio
    async def test_cmd_review_mr_verdict_display(self, base_args, capsys):
        """Test verdict display in cmd_review_mr output."""
        for verdict, expected_text in [
            (MergeVerdict.READY_TO_MERGE, "ready_to_merge"),
            (MergeVerdict.MERGE_WITH_CHANGES, "merge_with_changes"),
            (MergeVerdict.NEEDS_REVISION, "needs_revision"),
            (MergeVerdict.BLOCKED, "blocked"),
        ]:
            mock_result = MRReviewResult(
                mr_iid=123,
                project="group/project",
                success=True,
                findings=[],
                summary="Review complete",
                overall_status="approve",
                verdict=verdict,
                verdict_reasoning="Test",
            )

            mock_orchestrator = MagicMock()
            mock_orchestrator.review_mr = AsyncMock(return_value=mock_result)

            with patch(
                "runners.gitlab.runner.GitLabOrchestrator", return_value=mock_orchestrator
            ):
                exit_code = await cmd_review_mr(base_args)

            assert exit_code == 0
            captured = capsys.readouterr()
            assert f"Verdict: {expected_text}" in captured.out

    @pytest.mark.asyncio
    async def test_cmd_review_mr_severity_emoji(self, base_args, capsys):
        """Test severity emoji display in cmd_review_mr output."""
        mock_result = MRReviewResult(
            mr_iid=123,
            project="group/project",
            success=True,
            findings=[
                MRReviewFinding(
                    id="f1",
                    severity=ReviewSeverity.CRITICAL,
                    category=ReviewCategory.SECURITY,
                    title="Critical",
                    description="Fix",
                    file="file.py",
                    line=1,
                ),
                MRReviewFinding(
                    id="f2",
                    severity=ReviewSeverity.HIGH,
                    category=ReviewCategory.SECURITY,
                    title="High",
                    description="Fix",
                    file="file.py",
                    line=2,
                ),
                MRReviewFinding(
                    id="f3",
                    severity=ReviewSeverity.MEDIUM,
                    category=ReviewCategory.QUALITY,
                    title="Medium",
                    description="Fix",
                    file="file.py",
                    line=3,
                ),
                MRReviewFinding(
                    id="f4",
                    severity=ReviewSeverity.LOW,
                    category=ReviewCategory.STYLE,
                    title="Low",
                    description="Fix",
                    file="file.py",
                    line=4,
                ),
            ],
            summary="Review complete",
            overall_status="request_changes",
            verdict=MergeVerdict.NEEDS_REVISION,
            verdict_reasoning="Issues",
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.review_mr = AsyncMock(return_value=mock_result)

        with patch(
            "runners.gitlab.runner.GitLabOrchestrator", return_value=mock_orchestrator
        ):
            exit_code = await cmd_review_mr(base_args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "!" in captured.out  # CRITICAL
        assert "*" in captured.out  # HIGH
        assert "-" in captured.out  # MEDIUM
        assert "." in captured.out  # LOW


class TestCmdFollowupReviewMr:
    """Tests for cmd_followup_review_mr function."""

    @pytest.fixture
    def base_args(self, tmp_path):
        """Create base args object."""
        class Args:
            project_dir = tmp_path
            token = "test_token"
            project = "group/project"
            instance = "https://gitlab.com"
            model = "test-model"
            thinking_level = "medium"
            mr_iid = 123

        return Args()

    @pytest.mark.asyncio
    async def test_cmd_followup_review_mr_success(self, base_args, capsys):
        """Test cmd_followup_review_mr successful execution."""
        mock_result = MRReviewResult(
            mr_iid=123,
            project="group/project",
            success=True,
            is_followup_review=True,
            resolved_findings=["finding-1"],
            unresolved_findings=["finding-2"],
            new_findings_since_last_review=["finding-3"],
            findings=[],
            summary="Follow-up review complete",
            overall_status="comment",
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.followup_review_mr = AsyncMock(return_value=mock_result)

        with patch(
            "runners.gitlab.runner.GitLabOrchestrator", return_value=mock_orchestrator
        ):
            exit_code = await cmd_followup_review_mr(base_args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "MR !123 Follow-up Review Complete" in captured.out
        assert "Resolved: 1 finding(s)" in captured.out
        assert "Still Open: 1 finding(s)" in captured.out
        assert "New Issues: 1 finding(s)" in captured.out

    @pytest.mark.asyncio
    async def test_cmd_followup_review_mr_value_error(self, base_args, capsys):
        """Test cmd_followup_review_mr with ValueError (no previous review)."""
        mock_orchestrator = MagicMock()
        mock_orchestrator.followup_review_mr = AsyncMock(
            side_effect=ValueError("No previous review found")
        )

        with patch(
            "runners.gitlab.runner.GitLabOrchestrator", return_value=mock_orchestrator
        ):
            exit_code = await cmd_followup_review_mr(base_args)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Follow-up review failed: No previous review found" in captured.out

    @pytest.mark.asyncio
    async def test_cmd_followup_review_mr_failure(self, base_args, capsys):
        """Test cmd_followup_review_mr with review failure."""
        mock_result = MRReviewResult(
            mr_iid=123,
            project="group/project",
            success=False,
            error="Diff calculation failed",
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.followup_review_mr = AsyncMock(return_value=mock_result)

        with patch(
            "runners.gitlab.runner.GitLabOrchestrator", return_value=mock_orchestrator
        ):
            exit_code = await cmd_followup_review_mr(base_args)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Follow-up review failed: Diff calculation failed" in captured.out

    @pytest.mark.asyncio
    async def test_cmd_followup_review_mr_with_remaining_findings(self, base_args, capsys):
        """Test cmd_followup_review_mr with remaining findings."""
        mock_result = MRReviewResult(
            mr_iid=123,
            project="group/project",
            success=True,
            is_followup_review=True,
            resolved_findings=["f1"],
            unresolved_findings=["f2", "f3"],
            new_findings_since_last_review=[],
            findings=[
                MRReviewFinding(
                    id="f2",
                    severity=ReviewSeverity.HIGH,
                    category=ReviewCategory.SECURITY,
                    title="Unresolved issue",
                    description="Fix this",
                    file="auth.py",
                    line=10,
                ),
                MRReviewFinding(
                    id="f3",
                    severity=ReviewSeverity.MEDIUM,
                    category=ReviewCategory.QUALITY,
                    title="Another issue",
                    description="Fix this too",
                    file="utils.py",
                    line=20,
                ),
            ],
            summary="Follow-up complete",
            overall_status="request_changes",
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.followup_review_mr = AsyncMock(return_value=mock_result)

        with patch(
            "runners.gitlab.runner.GitLabOrchestrator", return_value=mock_orchestrator
        ):
            exit_code = await cmd_followup_review_mr(base_args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Still Open: 2 finding(s)" in captured.out
        assert "Remaining Findings:" in captured.out
        assert "[HIGH] Unresolved issue" in captured.out
        assert "[MEDIUM] Another issue" in captured.out

    @pytest.mark.asyncio
    async def test_cmd_followup_review_mr_summary_truncation(self, base_args, capsys):
        """Test that summary is truncated to 500 chars in output."""
        long_summary = "x" * 1000

        mock_result = MRReviewResult(
            mr_iid=123,
            project="group/project",
            success=True,
            is_followup_review=True,
            resolved_findings=[],
            unresolved_findings=[],
            new_findings_since_last_review=[],
            findings=[],
            summary=long_summary,
            overall_status="approve",
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.followup_review_mr = AsyncMock(return_value=mock_result)

        with patch(
            "runners.gitlab.runner.GitLabOrchestrator", return_value=mock_orchestrator
        ):
            exit_code = await cmd_followup_review_mr(base_args)

        assert exit_code == 0
        captured = capsys.readouterr()
        # Summary should be truncated to 500 chars + "..."
        assert "Summary:" in captured.out
        # Check truncation happened
        assert "..." in captured.out

    @pytest.mark.asyncio
    async def test_cmd_followup_review_mr_all_resolved(self, base_args, capsys):
        """Test cmd_followup_review_mr when all findings are resolved."""
        mock_result = MRReviewResult(
            mr_iid=123,
            project="group/project",
            success=True,
            is_followup_review=True,
            resolved_findings=["f1", "f2", "f3"],
            unresolved_findings=[],
            new_findings_since_last_review=[],
            findings=[],
            summary="All issues resolved!",
            overall_status="approve",
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.followup_review_mr = AsyncMock(return_value=mock_result)

        with patch(
            "runners.gitlab.runner.GitLabOrchestrator", return_value=mock_orchestrator
        ):
            exit_code = await cmd_followup_review_mr(base_args)

        assert exit_code == 0
        captured = capsys.readouterr()
        # Only prints "Resolved:" when list is non-empty
        assert "Resolved: 3 finding(s)" in captured.out
        # "Still Open:" is only printed when list is non-empty, so not printed here
        assert "Still Open: 0 finding(s)" not in captured.out
        assert "New Issues: 0 finding(s)" not in captured.out

    @pytest.mark.asyncio
    async def test_cmd_followup_review_mr_only_new_issues(self, base_args, capsys):
        """Test cmd_followup_review_mr with only new issues."""
        mock_result = MRReviewResult(
            mr_iid=123,
            project="group/project",
            success=True,
            is_followup_review=True,
            resolved_findings=[],
            unresolved_findings=[],
            new_findings_since_last_review=["f4", "f5"],
            findings=[
                MRReviewFinding(
                    id="f4",
                    severity=ReviewSeverity.HIGH,
                    category=ReviewCategory.SECURITY,
                    title="New issue 1",
                    description="Fix",
                    file="new.py",
                    line=1,
                ),
            ],
            summary="New issues found",
            overall_status="request_changes",
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.followup_review_mr = AsyncMock(return_value=mock_result)

        with patch(
            "runners.gitlab.runner.GitLabOrchestrator", return_value=mock_orchestrator
        ):
            exit_code = await cmd_followup_review_mr(base_args)

        assert exit_code == 0
        captured = capsys.readouterr()
        # "Resolved:" only prints when list is non-empty
        assert "Resolved: 0 finding(s)" not in captured.out
        assert "New Issues: 2 finding(s)" in captured.out


class TestMain:
    """Tests for main CLI entry point."""

    def test_main_with_no_command(self, capsys):
        """Test main with no command prints help and exits."""
        with patch("sys.argv", ["runner.py"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1

    def test_main_review_mr_command(self):
        """Test main routes to review-mr command."""
        with patch("sys.argv", ["runner.py", "review-mr", "123"]), patch(
            "runners.gitlab.runner.cmd_review_mr",
            return_value=AsyncMock(return_value=0),
        ) as mock_cmd, patch("asyncio.run", return_value=0) as mock_run:
            try:
                main()
            except SystemExit:
                pass

        # Verify asyncio.run was called
        assert mock_run.called

    def test_main_followup_review_mr_command(self):
        """Test main routes to followup-review-mr command."""
        with patch("sys.argv", ["runner.py", "followup-review-mr", "456"]), patch(
            "runners.gitlab.runner.cmd_followup_review_mr",
            return_value=AsyncMock(return_value=0),
        ) as mock_cmd, patch("asyncio.run", return_value=0) as mock_run:
            try:
                main()
            except SystemExit:
                pass

        # Verify asyncio.run was called
        assert mock_run.called

    def test_main_keyboard_interrupt(self, capsys):
        """Test main handles KeyboardInterrupt."""
        with patch("sys.argv", ["runner.py", "review-mr", "123"]), patch(
            "asyncio.run", side_effect=KeyboardInterrupt
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Interrupted" in captured.out

    def test_main_unhandled_exception(self, capsys):
        """Test main handles unhandled exceptions."""
        with patch("sys.argv", ["runner.py", "review-mr", "123"]), patch(
            "asyncio.run", side_effect=RuntimeError("Unexpected error")
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: Unexpected error" in captured.out

    def test_main_unknown_command(self, capsys):
        """Test main with unknown command exits with error."""
        with patch("sys.argv", ["runner.py", "unknown-command"]), patch(
            "argparse.ArgumentParser.print_help"
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        # argparse returns exit code 2 for invalid arguments
        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "invalid choice" in captured.err

    def test_main_argument_defaults(self):
        """Test main with default arguments."""
        with patch("sys.argv", ["runner.py", "review-mr", "123"]), patch(
            "runners.gitlab.runner.cmd_review_mr",
            return_value=AsyncMock(return_value=0),
        ) as mock_cmd:
            # Just verify parsing doesn't fail
            try:
                main()
            except SystemExit:
                pass

    def test_main_with_all_global_options(self):
        """Test main with all global options."""
        with patch("sys.argv", [
            "runner.py",
            "--project-dir", "/custom/path",
            "--token", "mytoken",
            "--project", "group/repo",
            "--instance", "https://custom.com",
            "--model", "custom-model",
            "--thinking-level", "high",
            "review-mr", "123",
        ]), patch("asyncio.run", return_value=0):
            try:
                main()
            except SystemExit:
                pass

    def test_main_exit_code_propagation(self):
        """Test that exit code from command is propagated."""
        with patch("sys.argv", ["runner.py", "review-mr", "123"]), patch(
            "asyncio.run", return_value=42
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 42

    def test_main_invalid_thinking_level(self, capsys):
        """Test main with invalid thinking level."""
        with patch("sys.argv", [
            "runner.py",
            "--thinking-level", "invalid",
            "review-mr", "123",
        ]):
            with pytest.raises(SystemExit):
                main()


class TestArgumentParser:
    """Tests for argument parsing."""

    def test_parse_review_mr_command(self):
        """Test parsing review-mr command."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--project-dir", type=Path, default=Path.cwd())
        parser.add_argument("--token", type=str)
        parser.add_argument("--project", type=str)
        parser.add_argument("--instance", type=str)
        parser.add_argument("--model", type=str)
        parser.add_argument("--thinking-level", type=str)
        subparsers = parser.add_subparsers(dest="command")
        review_parser = subparsers.add_parser("review-mr")
        review_parser.add_argument("mr_iid", type=int)

        args = parser.parse_args(["review-mr", "123"])

        assert args.command == "review-mr"
        assert args.mr_iid == 123

    def test_parse_followup_review_mr_command(self):
        """Test parsing followup-review-mr command."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--project-dir", type=Path, default=Path.cwd())
        parser.add_argument("--token", type=str)
        parser.add_argument("--project", type=str)
        parser.add_argument("--instance", type=str)
        parser.add_argument("--model", type=str)
        parser.add_argument("--thinking-level", type=str)
        subparsers = parser.add_subparsers(dest="command")
        followup_parser = subparsers.add_parser("followup-review-mr")
        followup_parser.add_argument("mr_iid", type=int)

        args = parser.parse_args(["followup-review-mr", "456"])

        assert args.command == "followup-review-mr"
        assert args.mr_iid == 456

    def test_parse_global_options(self):
        """Test parsing global options."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--project-dir", type=Path, default=Path.cwd())
        parser.add_argument("--token", type=str)
        parser.add_argument("--project", type=str)
        parser.add_argument("--instance", type=str)
        parser.add_argument("--model", type=str)
        parser.add_argument("--thinking-level", type=str)
        subparsers = parser.add_subparsers(dest="command")
        review_parser = subparsers.add_parser("review-mr")
        review_parser.add_argument("mr_iid", type=int)

        args = parser.parse_args(
            [
                "--project-dir",
                "/custom/path",
                "--token",
                "mytoken",
                "--project",
                "group/repo",
                "--instance",
                "https://custom.com",
                "--model",
                "custom-model",
                "--thinking-level",
                "high",
                "review-mr",
                "123",
            ]
        )

        assert args.project_dir == Path("/custom/path")
        assert args.token == "mytoken"
        assert args.project == "group/repo"
        assert args.instance == "https://custom.com"
        assert args.model == "custom-model"
        assert args.thinking_level == "high"

    def test_thinking_level_choices(self):
        """Test thinking_level accepts only valid choices."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--thinking-level",
            type=str,
            choices=["none", "low", "medium", "high"],
        )

        # Valid choices should work
        for level in ["none", "low", "medium", "high"]:
            args = parser.parse_args(["--thinking-level", level])
            assert args.thinking_level == level

        # Invalid choice should fail
        with pytest.raises(SystemExit):
            parser.parse_args(["--thinking-level", "invalid"])

    def test_parse_invalid_mr_iid(self):
        """Test parsing invalid MR IID (non-integer)."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--project-dir", type=Path, default=Path.cwd())
        subparsers = parser.add_subparsers(dest="command")
        review_parser = subparsers.add_parser("review-mr")
        review_parser.add_argument("mr_iid", type=int)

        # Non-integer should fail
        with pytest.raises(SystemExit):
            parser.parse_args(["review-mr", "abc"])

    def test_parse_negative_mr_iid(self):
        """Test parsing negative MR IID."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--project-dir", type=Path, default=Path.cwd())
        subparsers = parser.add_subparsers(dest="command")
        review_parser = subparsers.add_parser("review-mr")
        review_parser.add_argument("mr_iid", type=int)

        # Negative numbers are technically valid integers
        args = parser.parse_args(["review-mr", "-1"])
        assert args.mr_iid == -1

    def test_parse_zero_mr_iid(self):
        """Test parsing zero MR IID."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--project-dir", type=Path, default=Path.cwd())
        subparsers = parser.add_subparsers(dest="command")
        review_parser = subparsers.add_parser("review-mr")
        review_parser.add_argument("mr_iid", type=int)

        args = parser.parse_args(["review-mr", "0"])
        assert args.mr_iid == 0


class TestGetConfigEdgeCases:
    """Additional edge case tests for get_config."""

    @pytest.fixture
    def base_args(self, tmp_path):
        """Create base args object."""
        class Args:
            project_dir = tmp_path
            token = None
            project = None
            instance = None
            model = "test-model"
            thinking_level = "medium"

        return Args()

    def test_get_config_empty_token_from_glab(self, base_args):
        """Test when glab returns empty token."""
        base_args.project = "group/project"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Token: \n"  # Empty token

        with patch("subprocess.run", return_value=mock_result):
            # Should exit since no valid token found
            with pytest.raises(SystemExit) as exc_info:
                get_config(base_args)
            assert exc_info.value.code == 1

    def test_get_config_glab_no_token_line(self, base_args):
        """Test when glab output doesn't contain Token: line."""
        base_args.project = "group/project"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "GitLab.com\nAuthenticated as: user\n"

        with patch("subprocess.run", return_value=mock_result):
            # Should exit since no token found
            with pytest.raises(SystemExit) as exc_info:
                get_config(base_args)
            assert exc_info.value.code == 1

    def test_get_config_project_file_read_permission_error(self, base_args, tmp_path):
        """Test when project config file exists but can't be read."""
        base_args.token = "test_token"
        base_args.project = "group/project"

        config_dir = tmp_path / ".auto-claude" / "gitlab"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"
        config_file.write_text('{"project": "test"}')

        # Mock open to raise permission error
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            # Should fall back to args
            config = get_config(base_args)
            assert config.project == "group/project"

    def test_get_config_empty_string_args(self, base_args):
        """Test when args are empty strings instead of None."""
        base_args.token = ""
        base_args.project = ""
        base_args.instance = ""

        # Should treat empty strings as missing
        with pytest.raises(SystemExit):
            get_config(base_args)

    def test_get_config_whitespace_in_glab_output(self, base_args):
        """Test handling of whitespace in glab output."""
        base_args.project = "group/project"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "  Token:   token_with_spaces   \n"

        with patch("subprocess.run", return_value=mock_result):
            config = get_config(base_args)
            # Should strip whitespace
            assert config.token == "token_with_spaces"

    def test_get_config_model_from_args(self, base_args):
        """Test model is passed from args to config."""
        base_args.token = "token"
        base_args.project = "group/project"
        base_args.model = "custom-ai-model"

        config = get_config(base_args)
        assert config.model == "custom-ai-model"

    def test_get_config_thinking_level_from_args(self, base_args):
        """Test thinking_level is passed from args to config."""
        base_args.token = "token"
        base_args.project = "group/project"
        base_args.thinking_level = "high"

        config = get_config(base_args)
        assert config.thinking_level == "high"


class TestOrchestratorIntegration:
    """Tests for orchestrator integration in commands."""

    @pytest.fixture
    def base_args(self, tmp_path):
        """Create base args object."""
        class Args:
            project_dir = tmp_path
            token = "test_token"
            project = "group/project"
            instance = "https://gitlab.com"
            model = "test-model"
            thinking_level = "medium"
            mr_iid = 123

        return Args()

    @pytest.mark.asyncio
    async def test_review_mr_orchestrator_initialization(self, base_args):
        """Test that orchestrator is initialized correctly."""
        mock_result = MRReviewResult(
            mr_iid=123,
            project="group/project",
            success=True,
            findings=[],
            summary="Complete",
            overall_status="approve",
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.review_mr = AsyncMock(return_value=mock_result)

        with patch(
            "runners.gitlab.runner.GitLabOrchestrator", return_value=mock_orchestrator
        ) as mock_init:
            await cmd_review_mr(base_args)

        # Verify orchestrator was initialized with correct args
        mock_init.assert_called_once()
        call_kwargs = mock_init.call_args[1]
        assert call_kwargs["project_dir"] == base_args.project_dir
        assert "config" in call_kwargs
        assert "progress_callback" in call_kwargs

    @pytest.mark.asyncio
    async def test_followup_review_mr_orchestrator_initialization(self, base_args):
        """Test that orchestrator is initialized correctly for follow-up."""
        mock_result = MRReviewResult(
            mr_iid=123,
            project="group/project",
            success=True,
            is_followup_review=True,
            findings=[],
            summary="Complete",
            overall_status="approve",
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.followup_review_mr = AsyncMock(return_value=mock_result)

        with patch(
            "runners.gitlab.runner.GitLabOrchestrator", return_value=mock_orchestrator
        ) as mock_init:
            await cmd_followup_review_mr(base_args)

        # Verify orchestrator was initialized
        mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_progress_callback_invoked(self, base_args):
        """Test that progress callback is passed to orchestrator during review."""
        mock_result = MRReviewResult(
            mr_iid=123,
            project="group/project",
            success=True,
            findings=[],
            summary="Complete",
            overall_status="approve",
        )

        mock_orchestrator_instance = MagicMock()
        mock_orchestrator_instance.review_mr = AsyncMock(return_value=mock_result)

        with patch(
            "runners.gitlab.runner.GitLabOrchestrator",
            return_value=mock_orchestrator_instance,
        ) as mock_orchestrator_class:
            await cmd_review_mr(base_args)

        # Verify orchestrator was called and progress_callback was passed
        mock_orchestrator_class.assert_called_once()
        call_kwargs = mock_orchestrator_class.call_args[1]
        assert "progress_callback" in call_kwargs
        assert call_kwargs["progress_callback"] is not None
        assert callable(call_kwargs["progress_callback"])
