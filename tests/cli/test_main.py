"""
Comprehensive tests for cli.main module

Tests parse_args, main, and _run_cli functions with various flag combinations,
edge cases, and error scenarios.
"""

import json
import platform
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call

import pytest


# =============================================================================
# Test parse_args function
# =============================================================================


class TestParseArgsBasics:
    """Test basic argument parsing functionality."""

    def test_parse_args_empty_defaults(self):
        """Test parse_args with no arguments returns defaults."""
        with patch("sys.argv", ["run.py"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.spec is None
        assert result.list is False
        assert result.verbose is False
        assert result.max_iterations is None
        assert result.model is None
        assert result.isolated is False
        assert result.direct is False

    def test_parse_args_with_spec_short_name(self):
        """Test parse_args with short spec identifier."""
        with patch("sys.argv", ["run.py", "--spec", "001"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.spec == "001"

    def test_parse_args_with_spec_full_name(self):
        """Test parse_args with full spec name."""
        with patch("sys.argv", ["run.py", "--spec", "001-add-feature"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.spec == "001-add-feature"

    def test_parse_args_with_list(self):
        """Test parse_args with --list flag."""
        with patch("sys.argv", ["run.py", "--list"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.list is True

    def test_parse_args_with_verbose(self):
        """Test parse_args with --verbose flag."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--verbose"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.verbose is True

    def test_parse_args_with_max_iterations(self):
        """Test parse_args with --max-iterations."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--max-iterations", "5"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.max_iterations == 5

    def test_parse_args_with_model(self):
        """Test parse_args with --model override."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--model", "opus"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.model == "opus"

    def test_parse_args_invalid_option(self):
        """Test parse_args with invalid option raises SystemExit."""
        with patch("sys.argv", ["run.py", "--invalid-option"]):
            from cli.main import parse_args

            with pytest.raises(SystemExit):
                parse_args()


class TestParseArgsWorkspaceOptions:
    """Test workspace-related argument parsing."""

    def test_parse_args_isolated_flag(self):
        """Test --isolated flag for workspace isolation."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--isolated"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.isolated is True
        assert result.direct is False

    def test_parse_args_direct_flag(self):
        """Test --direct flag for direct build."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--direct"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.direct is True
        assert result.isolated is False

    def test_parse_args_isolated_and_direct_mutually_exclusive(self):
        """Test that --isolated and --direct are mutually exclusive."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--isolated", "--direct"]):
            from cli.main import parse_args

            # argparse should reject this
            with pytest.raises(SystemExit):
                parse_args()


class TestParseArgsBuildManagementOptions:
    """Test build management command argument parsing."""

    def test_parse_args_merge_flag(self):
        """Test --merge flag."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--merge"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.merge is True

    def test_parse_args_review_flag(self):
        """Test --review flag."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--review"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.review is True

    def test_parse_args_discard_flag(self):
        """Test --discard flag."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--discard"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.discard is True

    def test_parse_args_create_pr_flag(self):
        """Test --create-pr flag."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--create-pr"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.create_pr is True

    def test_parse_args_pr_options(self):
        """Test PR-related options."""
        with patch("sys.argv", [
            "run.py", "--spec", "001", "--create-pr",
            "--pr-target", "develop",
            "--pr-title", "Custom PR Title",
            "--pr-draft"
        ]):
            from cli.main import parse_args
            result = parse_args()

        assert result.pr_target == "develop"
        assert result.pr_title == "Custom PR Title"
        assert result.pr_draft is True

    def test_parse_args_no_commit_flag(self):
        """Test --no-commit flag for merge."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--merge", "--no-commit"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.merge is True
        assert result.no_commit is True

    def test_parse_args_merge_preview_flag(self):
        """Test --merge-preview flag."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--merge-preview"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.merge_preview is True

    def test_parse_args_build_management_mutually_exclusive(self):
        """Test that build management flags are mutually exclusive."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--merge", "--review"]):
            from cli.main import parse_args

            with pytest.raises(SystemExit):
                parse_args()


class TestParseArgsQAOptions:
    """Test QA-related argument parsing."""

    def test_parse_args_qa_flag(self):
        """Test --qa flag."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--qa"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.qa is True

    def test_parse_args_qa_status_flag(self):
        """Test --qa-status flag."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--qa-status"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.qa_status is True

    def test_parse_args_skip_qa_flag(self):
        """Test --skip-qa flag."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--skip-qa"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.skip_qa is True

    def test_parse_args_review_status_flag(self):
        """Test --review-status flag."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--review-status"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.review_status is True


class TestParseArgsFollowupOptions:
    """Test follow-up task argument parsing."""

    def test_parse_args_followup_flag(self):
        """Test --followup flag."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--followup"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.followup is True


class TestParseArgsWorktreeManagementOptions:
    """Test worktree management argument parsing."""

    def test_parse_args_list_worktrees_flag(self):
        """Test --list-worktrees flag."""
        with patch("sys.argv", ["run.py", "--list-worktrees"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.list_worktrees is True

    def test_parse_args_cleanup_worktrees_flag(self):
        """Test --cleanup-worktrees flag."""
        with patch("sys.argv", ["run.py", "--cleanup-worktrees"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.cleanup_worktrees is True

    def test_parse_args_base_branch(self):
        """Test --base-branch option."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--base-branch", "main"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.base_branch == "main"


class TestParseArgsBatchOptions:
    """Test batch management argument parsing."""

    def test_parse_args_batch_create(self):
        """Test --batch-create with file path."""
        with patch("sys.argv", ["run.py", "--batch-create", "tasks.json"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.batch_create == "tasks.json"

    def test_parse_args_batch_status(self):
        """Test --batch-status flag."""
        with patch("sys.argv", ["run.py", "--batch-status"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.batch_status is True

    def test_parse_args_batch_cleanup(self):
        """Test --batch-cleanup flag."""
        with patch("sys.argv", ["run.py", "--batch-cleanup"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.batch_cleanup is True

    def test_parse_args_no_dry_run(self):
        """Test --no-dry-run flag."""
        with patch("sys.argv", ["run.py", "--batch-cleanup", "--no-dry-run"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.no_dry_run is True


class TestParseArgsOtherOptions:
    """Test other argument parsing options."""

    @pytest.mark.skipif(platform.system() == "Windows", reason="Path separators differ on Windows")
    def test_parse_args_project_dir(self):
        """Test --project-dir option."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--project-dir", "/custom/path"]):
            from cli.main import parse_args
            result = parse_args()

        assert isinstance(result.project_dir, Path)
        assert str(result.project_dir) == "/custom/path"

    def test_parse_args_auto_continue(self):
        """Test --auto-continue flag for non-interactive mode."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--auto-continue"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.auto_continue is True

    def test_parse_args_force(self):
        """Test --force flag to bypass approval."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--force"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.force is True


class TestParseArgsComplexCombinations:
    """Test complex argument combinations."""

    def test_parse_args_full_build_command(self):
        """Test a full build command with multiple options."""
        with patch("sys.argv", [
            "run.py", "--spec", "001", "--verbose", "--isolated",
            "--max-iterations", "10", "--model", "sonnet"
        ]):
            from cli.main import parse_args
            result = parse_args()

        assert result.spec == "001"
        assert result.verbose is True
        assert result.isolated is True
        assert result.max_iterations == 10
        assert result.model == "sonnet"

    def test_parse_args_merge_with_options(self):
        """Test merge command with all options."""
        with patch("sys.argv", [
            "run.py", "--spec", "001", "--merge",
            "--no-commit", "--base-branch", "develop"
        ]):
            from cli.main import parse_args
            result = parse_args()

        assert result.merge is True
        assert result.no_commit is True
        assert result.base_branch == "develop"

    def test_parse_args_create_pr_with_options(self):
        """Test create-pr with all options."""
        with patch("sys.argv", [
            "run.py", "--spec", "001", "--create-pr",
            "--pr-target", "main",
            "--pr-title", "Feature: Add new capability",
            "--pr-draft"
        ]):
            from cli.main import parse_args
            result = parse_args()

        assert result.create_pr is True
        assert result.pr_target == "main"
        assert result.pr_title == "Feature: Add new capability"
        assert result.pr_draft is True


# =============================================================================
# Test main function
# =============================================================================


class TestMainFunctionBasics:
    """Test main function basic behavior."""

    def test_main_sets_up_environment(self):
        """Test that main calls setup_environment."""
        from cli.main import main

        with patch("sys.argv", ["run.py", "--list"]), \
             patch("cli.main.setup_environment") as mock_setup, \
             patch("cli.main.print_specs_list"), \
             patch("core.sentry.init_sentry"), \
             patch("core.sentry.capture_exception"):
            main()

        mock_setup.assert_called_once()

    def test_main_initializes_sentry(self):
        """Test that main initializes Sentry."""
        from cli.main import main

        with patch("sys.argv", ["run.py", "--list"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.print_specs_list"), \
             patch("core.sentry.init_sentry") as mock_init_sentry, \
             patch("core.sentry.capture_exception"):
            main()

        mock_init_sentry.assert_called_once_with(component="cli")

    def test_main_keyboard_interrupt(self):
        """Test main handles KeyboardInterrupt with exit code 130."""
        from cli.main import main

        with patch("sys.argv", ["run.py", "--list"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.print_specs_list", side_effect=KeyboardInterrupt()), \
             patch("core.sentry.init_sentry"), \
             patch("core.sentry.capture_exception"):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 130

    def test_main_unexpected_error(self):
        """Test main captures unexpected errors to Sentry."""
        from cli.main import main

        with patch("sys.argv", ["run.py", "--list"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.print_specs_list", side_effect=RuntimeError("Test error")), \
             patch("core.sentry.init_sentry"), \
             patch("core.sentry.capture_exception") as mock_capture:
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
            mock_capture.assert_called_once()


class TestMainCommandDispatch:
    """Test main function command routing."""

    def test_main_list_command(self):
        """Test main routes --list to print_specs_list."""
        from cli.main import main

        with patch("sys.argv", ["run.py", "--list"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.print_banner"), \
             patch("cli.main.print_specs_list") as mock_print_specs:
            main()

        mock_print_specs.assert_called_once()

    def test_main_list_worktrees_command(self):
        """Test main routes --list-worktrees."""
        from cli.main import main

        with patch("sys.argv", ["run.py", "--list-worktrees"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.handle_list_worktrees_command") as mock_handle:
            main()

        mock_handle.assert_called_once()

    def test_main_cleanup_worktrees_command(self):
        """Test main routes --cleanup-worktrees."""
        from cli.main import main

        with patch("sys.argv", ["run.py", "--cleanup-worktrees"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.handle_cleanup_worktrees_command") as mock_handle:
            main()

        mock_handle.assert_called_once()

    def test_main_batch_create_command(self):
        """Test main routes --batch-create."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/project")
        with patch("sys.argv", ["run.py", "--batch-create", "tasks.json"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=mock_spec_dir), \
             patch("cli.main.handle_batch_create_command") as mock_handle:
            main()

        mock_handle.assert_called_once_with("tasks.json", str(mock_spec_dir))

    def test_main_batch_status_command(self):
        """Test main routes --batch-status."""
        from cli.main import main

        with patch("sys.argv", ["run.py", "--batch-status"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.handle_batch_status_command") as mock_handle:
            main()

        mock_handle.assert_called_once()

    def test_main_batch_cleanup_command(self):
        """Test main routes --batch-cleanup."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/project")
        with patch("sys.argv", ["run.py", "--batch-cleanup"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=mock_spec_dir), \
             patch("cli.main.handle_batch_cleanup_command") as mock_handle:
            main()

        mock_handle.assert_called_once_with(str(mock_spec_dir), dry_run=True)

    def test_main_batch_cleanup_no_dry_run(self):
        """Test main routes --batch-cleanup with --no-dry-run."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/project")
        with patch("sys.argv", ["run.py", "--batch-cleanup", "--no-dry-run"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=mock_spec_dir), \
             patch("cli.main.handle_batch_cleanup_command") as mock_handle:
            main()

        mock_handle.assert_called_once_with(str(mock_spec_dir), dry_run=False)


class TestMainSpecRequiredValidation:
    """Test main function validates --spec is provided."""

    def test_main_requires_spec_without_list(self):
        """Test main exits with error when --spec is missing."""
        from cli.main import main

        with patch("sys.argv", ["run.py"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_shows_usage_when_spec_missing(self, capsys):
        """Test main shows usage instructions when --spec is missing."""
        from cli.main import main

        with patch("sys.argv", ["run.py"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")):
            with pytest.raises(SystemExit):
                main()

        captured = capsys.readouterr()
        assert "--spec is required" in captured.out
        assert "python auto-claude/run.py --list" in captured.out
        assert "claude /spec" in captured.out


class TestMainSpecNotFound:
    """Test main function when spec is not found."""

    def test_main_exits_when_spec_not_found(self):
        """Test main exits when spec doesn't exist."""
        from cli.main import main

        with patch("sys.argv", ["run.py", "--spec", "999-nonexistent"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")), \
             patch("cli.main.find_spec", return_value=None):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_prints_available_specs_when_not_found(self, capsys):
        """Test main prints spec list when spec not found."""
        from cli.main import main

        with patch("sys.argv", ["run.py", "--spec", "999"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")), \
             patch("cli.main.find_spec", return_value=None), \
             patch("cli.main.print_specs_list"):
            with pytest.raises(SystemExit):
                main()

        captured = capsys.readouterr()
        assert "not found" in captured.out


class TestMainBuildManagementCommands:
    """Test main function routing for build management commands."""

    def test_main_merge_command(self):
        """Test main routes --merge command."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/specs/001-test")
        with patch("sys.argv", ["run.py", "--spec", "001", "--merge"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")), \
             patch("cli.main.find_spec", return_value=mock_spec_dir), \
             patch("cli.main.handle_merge_command", return_value=True) as mock_handle:
            main()

        mock_handle.assert_called_once()

    def test_main_merge_command_failure_exits(self):
        """Test main exits when merge fails."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/specs/001-test")
        with patch("sys.argv", ["run.py", "--spec", "001", "--merge"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")), \
             patch("cli.main.find_spec", return_value=mock_spec_dir), \
             patch("cli.main.handle_merge_command", return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_review_command(self):
        """Test main routes --review command."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/specs/001-test")
        with patch("sys.argv", ["run.py", "--spec", "001", "--review"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")), \
             patch("cli.main.find_spec", return_value=mock_spec_dir), \
             patch("cli.main.handle_review_command") as mock_handle:
            main()

        mock_handle.assert_called_once()

    def test_main_discard_command(self):
        """Test main routes --discard command."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/specs/001-test")
        with patch("sys.argv", ["run.py", "--spec", "001", "--discard"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")), \
             patch("cli.main.find_spec", return_value=mock_spec_dir), \
             patch("cli.main.handle_discard_command") as mock_handle:
            main()

        mock_handle.assert_called_once()

    def test_main_create_pr_command(self):
        """Test main routes --create-pr command."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/specs/001-test")
        with patch("sys.argv", ["run.py", "--spec", "001", "--create-pr"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")), \
             patch("cli.main.find_spec", return_value=mock_spec_dir), \
             patch("cli.main.handle_create_pr_command", return_value={"success": True}) as mock_handle:
            main()

        mock_handle.assert_called_once()

    def test_main_create_pr_command_failure_exits(self):
        """Test main exits when create-pr fails."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/specs/001-test")
        with patch("sys.argv", ["run.py", "--spec", "001", "--create-pr"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")), \
             patch("cli.main.find_spec", return_value=mock_spec_dir), \
             patch("cli.main.handle_create_pr_command", return_value={"success": False}):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_merge_preview_command(self, capsys):
        """Test main routes --merge-preview and outputs JSON."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/specs/001-test")
        mock_result = {"conflicts": [], "files": ["test.py"]}
        with patch("sys.argv", ["run.py", "--spec", "001", "--merge-preview"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")), \
             patch("cli.main.find_spec", return_value=mock_spec_dir), \
             patch("cli.workspace_commands.handle_merge_preview_command", return_value=mock_result):
            main()

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result == mock_result


class TestMainQACommands:
    """Test main function routing for QA commands."""

    def test_main_qa_status_command(self):
        """Test main routes --qa-status command."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/specs/001-test")
        with patch("sys.argv", ["run.py", "--spec", "001", "--qa-status"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")), \
             patch("cli.main.find_spec", return_value=mock_spec_dir), \
             patch("cli.main.handle_qa_status_command") as mock_handle:
            main()

        mock_handle.assert_called_once()

    def test_main_review_status_command(self):
        """Test main routes --review-status command."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/specs/001-test")
        with patch("sys.argv", ["run.py", "--spec", "001", "--review-status"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")), \
             patch("cli.main.find_spec", return_value=mock_spec_dir), \
             patch("cli.main.handle_review_status_command") as mock_handle:
            main()

        mock_handle.assert_called_once()

    def test_main_qa_command(self):
        """Test main routes --qa command."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/specs/001-test")
        with patch("sys.argv", ["run.py", "--spec", "001", "--qa"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")), \
             patch("cli.main.find_spec", return_value=mock_spec_dir), \
             patch.dict("os.environ", {}, clear=False), \
             patch("cli.main.handle_qa_command") as mock_handle:
            main()

        mock_handle.assert_called_once()

    def test_main_followup_command(self):
        """Test main routes --followup command."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/specs/001-test")
        with patch("sys.argv", ["run.py", "--spec", "001", "--followup"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")), \
             patch("cli.main.find_spec", return_value=mock_spec_dir), \
             patch.dict("os.environ", {}, clear=False), \
             patch("cli.main.handle_followup_command") as mock_handle:
            main()

        mock_handle.assert_called_once()


class TestMainNormalBuildFlow:
    """Test main function normal build flow."""

    def test_main_normal_build(self):
        """Test main routes to handle_build_command for normal build."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/specs/001-test")
        with patch("sys.argv", ["run.py", "--spec", "001"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")), \
             patch("cli.main.find_spec", return_value=mock_spec_dir), \
             patch.dict("os.environ", {}, clear=False), \
             patch("cli.main.handle_build_command") as mock_handle:
            main()

        mock_handle.assert_called_once()

    def test_main_build_with_all_options(self):
        """Test main passes all build options correctly."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/specs/001-test")
        with patch("sys.argv", [
            "run.py", "--spec", "001",
            "--max-iterations", "5",
            "--verbose",
            "--isolated",
            "--auto-continue",
            "--skip-qa",
            "--force",
            "--base-branch", "develop"
        ]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")), \
             patch("cli.main.find_spec", return_value=mock_spec_dir), \
             patch.dict("os.environ", {}, clear=False), \
             patch("cli.main.handle_build_command") as mock_handle:
            main()

        # Verify all options were passed
        call_args = mock_handle.call_args
        assert call_args.kwargs["max_iterations"] == 5
        assert call_args.kwargs["verbose"] is True
        assert call_args.kwargs["force_isolated"] is True
        assert call_args.kwargs["auto_continue"] is True
        assert call_args.kwargs["skip_qa"] is True
        assert call_args.kwargs["force_bypass_approval"] is True
        assert call_args.kwargs["base_branch"] == "develop"

    def test_main_model_from_cli_arg(self):
        """Test main uses model from CLI argument."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/specs/001-test")
        with patch("sys.argv", ["run.py", "--spec", "001", "--model", "opus"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")), \
             patch("cli.main.find_spec", return_value=mock_spec_dir), \
             patch("cli.main.handle_build_command") as mock_handle:
            main()

        call_args = mock_handle.call_args
        assert call_args.kwargs["model"] == "opus"

    def test_main_model_from_env_var(self):
        """Test main uses model from environment variable."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/specs/001-test")
        with patch("sys.argv", ["run.py", "--spec", "001"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")), \
             patch("cli.main.find_spec", return_value=mock_spec_dir), \
             patch.dict("os.environ", {"AUTO_BUILD_MODEL": "sonnet"}, clear=False), \
             patch("cli.main.handle_build_command") as mock_handle:
            main()

        call_args = mock_handle.call_args
        assert call_args.kwargs["model"] == "sonnet"

    def test_main_model_cli_arg_takes_precedence(self):
        """Test CLI model arg takes precedence over env var."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/specs/001-test")
        with patch("sys.argv", ["run.py", "--spec", "001", "--model", "opus"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")), \
             patch("cli.main.find_spec", return_value=mock_spec_dir), \
             patch.dict("os.environ", {"AUTO_BUILD_MODEL": "sonnet"}, clear=False), \
             patch("cli.main.handle_build_command") as mock_handle:
            main()

        call_args = mock_handle.call_args
        assert call_args.kwargs["model"] == "opus"


# =============================================================================
# Test _run_cli function
# =============================================================================


class TestRunCliSentryContext:
    """Test Sentry context setting in _run_cli."""

    def test_sentry_context_set_on_spec_found(self):
        """Test that Sentry context is set when spec is found."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/specs/001-test")
        with patch("sys.argv", ["run.py", "--spec", "001", "--qa-status"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp/project")), \
             patch("cli.main.find_spec", return_value=mock_spec_dir), \
             patch("cli.main.handle_qa_status_command"), \
             patch("core.sentry.set_context") as mock_set_context:
            main()

        # Verify Sentry context was set with spec and project info
        mock_set_context.assert_called_once_with("spec", {
            "name": "001-test",
            "project": "/tmp/project"
        })

    def test_sentry_context_includes_spec_and_project(self):
        """Test Sentry context includes spec name and project."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/specs/001-custom-name")
        mock_project_dir = Path("/tmp/custom-project")
        with patch("sys.argv", ["run.py", "--spec", "001", "--review-status"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=mock_project_dir), \
             patch("cli.main.find_spec", return_value=mock_spec_dir), \
             patch("cli.main.handle_review_status_command"), \
             patch("core.sentry.set_context") as mock_set_context:
            main()

        # Verify context contains the right information
        mock_set_context.assert_called_once()
        call_args = mock_set_context.call_args
        assert call_args[0][0] == "spec"
        assert call_args[0][1]["name"] == "001-custom-name"
        assert call_args[0][1]["project"] == str(mock_project_dir)


# =============================================================================
# Test edge cases and error handling
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_parse_args_with_zero_iterations(self):
        """Test parse_args accepts zero as max_iterations."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--max-iterations", "0"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.max_iterations == 0

    def test_parse_args_with_large_iterations(self):
        """Test parse_args accepts large max_iterations value."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--max-iterations", "999999"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.max_iterations == 999999

    def test_parse_args_invalid_iterations(self):
        """Test parse_args rejects non-integer max_iterations."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--max-iterations", "abc"]):
            from cli.main import parse_args

            with pytest.raises(SystemExit):
                parse_args()

    def test_parse_args_negative_iterations(self):
        """Test parse_args accepts negative iterations (though not recommended)."""
        with patch("sys.argv", ["run.py", "--spec", "001", "--max-iterations", "-1"]):
            from cli.main import parse_args
            result = parse_args()

        assert result.max_iterations == -1

    def test_parse_args_empty_spec(self):
        """Test parse_args with empty --spec value."""
        with patch("sys.argv", ["run.py", "--spec", ""]):
            from cli.main import parse_args
            result = parse_args()

        assert result.spec == ""

    def test_main_with_project_dir_resolved(self):
        """Test main resolves project directory path."""
        from cli.main import main

        with patch("sys.argv", ["run.py", "--list"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir") as mock_get_dir, \
             patch("cli.main.print_specs_list"):
            mock_get_dir.return_value = Path("/custom/path").resolve()
            main()

            mock_get_dir.assert_called_once()

    def test_main_with_base_branch_passed_to_commands(self):
        """Test main passes base_branch to commands."""
        from cli.main import main

        mock_spec_dir = Path("/tmp/specs/001-test")
        with patch("sys.argv", ["run.py", "--spec", "001", "--merge", "--base-branch", "custom-branch"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.get_project_dir", return_value=Path("/tmp")), \
             patch("cli.main.find_spec", return_value=mock_spec_dir), \
             patch("cli.main.handle_merge_command", return_value=True) as mock_handle:
            main()

        call_args = mock_handle.call_args
        assert call_args.kwargs["base_branch"] == "custom-branch"


class TestErrorHandling:
    """Test error handling in main and _run_cli."""

    def test_main_exception_message_printed(self, capsys):
        """Test that exception message is printed on error."""
        from cli.main import main

        with patch("sys.argv", ["run.py", "--list"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.print_specs_list", side_effect=ValueError("Test error")), \
             patch("core.sentry.init_sentry"), \
             patch("core.sentry.capture_exception"):
            with pytest.raises(SystemExit):
                main()

        captured = capsys.readouterr()
        assert "Unexpected error" in captured.out

    def test_main_sentry_capture_exception_details(self):
        """Test that exception is captured to Sentry with details."""
        from cli.main import main

        test_error = ValueError("Detailed error message")
        with patch("sys.argv", ["run.py", "--list"]), \
             patch("cli.main.setup_environment"), \
             patch("cli.main.print_specs_list", side_effect=test_error), \
             patch("core.sentry.init_sentry"), \
             patch("core.sentry.capture_exception") as mock_capture:
            with pytest.raises(SystemExit):
                main()

        mock_capture.assert_called_once_with(test_error)
