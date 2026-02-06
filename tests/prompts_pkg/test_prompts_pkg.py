"""
Comprehensive tests for prompts module.
Tests prompt loading, branch validation, recovery context, and QA prompt generation.
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
from unittest.mock import AsyncMock
import pytest

from prompts_pkg.prompts import (
    _validate_branch_name,
    get_base_branch_from_metadata,
    _detect_base_branch,
    get_planner_prompt,
    get_coding_prompt,
    _get_recovery_context,
    get_followup_planner_prompt,
    is_first_run,
    get_qa_reviewer_prompt,
    get_qa_fixer_prompt,
)


class TestValidateBranchName:
    """Tests for _validate_branch_name function."""

    def test_valid_simple_branch(self):
        """Test valid simple branch name."""
        result = _validate_branch_name("main")
        assert result == "main"

    def test_valid_feature_branch(self):
        """Test valid feature branch name."""
        result = _validate_branch_name("feature/add-new-feature")
        assert result == "feature/add-new-feature"

    def test_valid_branch_with_dots(self):
        """Test valid branch with dots."""
        result = _validate_branch_name("release/v1.2.3")
        assert result == "release/v1.2.3"

    def test_valid_branch_with_underscores(self):
        """Test valid branch with underscores."""
        result = _validate_branch_name("feature/new_api_endpoints")
        assert result == "feature/new_api_endpoints"

    def test_none_returns_none(self):
        """Test None input returns None."""
        result = _validate_branch_name(None)
        assert result is None

    def test_non_string_returns_none(self):
        """Test non-string input returns None."""
        result = _validate_branch_name(123)
        assert result is None

    def test_empty_string_returns_none(self):
        """Test empty string returns None."""
        result = _validate_branch_name("")
        assert result is None

    def test_whitespace_only_returns_none(self):
        """Test whitespace-only string returns None."""
        result = _validate_branch_name("   ")
        assert result is None

    def test_trims_whitespace(self):
        """Test whitespace is trimmed from valid branches."""
        result = _validate_branch_name("  main  ")
        assert result == "main"

    def test_too_long_returns_none(self):
        """Test branch name over 255 characters returns None."""
        long_branch = "a" * 256
        result = _validate_branch_name(long_branch)
        assert result is None

    def test_exactly_255_chars_accepted(self):
        """Test branch name of exactly 255 characters is accepted."""
        branch = "a" * 255
        result = _validate_branch_name(branch)
        assert result == branch

    def test_no_alphanumeric_returns_none(self):
        """Test branch with no alphanumeric characters returns None."""
        result = _validate_branch_name("---/...")
        assert result is None

    def test_rejects_special_characters(self):
        """Test branch with special characters is rejected."""
        result = _validate_branch_name("feature$branch")
        assert result is None

    def test_rejects_newlines(self):
        """Test branch with newline is rejected."""
        result = _validate_branch_name("main\nmalicious")
        assert result is None

    def test_rejects_shell_commands(self):
        """Test branch with shell commands is rejected."""
        result = _validate_branch_name("main; rm -rf /")
        assert result is None


class TestGetBaseBranchFromMetadata:
    """Tests for get_base_branch_from_metadata function."""

    def test_reads_valid_branch_from_metadata(self, tmp_path):
        """Test reads and validates baseBranch from metadata."""
        metadata_file = tmp_path / "task_metadata.json"
        metadata_file.write_text('{"baseBranch": "develop"}', encoding="utf-8")

        result = get_base_branch_from_metadata(tmp_path)

        assert result == "develop"

    def test_returns_none_when_missing(self, tmp_path):
        """Test returns None when metadata file doesn't exist."""
        result = get_base_branch_from_metadata(tmp_path)

        assert result is None

    def test_returns_none_for_invalid_json(self, tmp_path):
        """Test returns None for invalid JSON."""
        metadata_file = tmp_path / "task_metadata.json"
        metadata_file.write_text('{invalid json}', encoding="utf-8")

        result = get_base_branch_from_metadata(tmp_path)

        assert result is None

    def test_validates_branch_name(self, tmp_path):
        """Test validates branch name before returning."""
        metadata_file = tmp_path / "task_metadata.json"
        metadata_file.write_text('{"baseBranch": "main; malicious"}', encoding="utf-8")

        result = get_base_branch_from_metadata(tmp_path)

        assert result is None  # Rejected by validation

    def test_returns_none_for_missing_key(self, tmp_path):
        """Test returns None when baseBranch key is missing."""
        metadata_file = tmp_path / "task_metadata.json"
        metadata_file.write_text('{"otherKey": "value"}', encoding="utf-8")

        result = get_base_branch_from_metadata(tmp_path)

        assert result is None

    def test_returns_none_for_null_branch(self, tmp_path):
        """Test returns None when baseBranch is null."""
        metadata_file = tmp_path / "task_metadata.json"
        metadata_file.write_text('{"baseBranch": null}', encoding="utf-8")

        result = get_base_branch_from_metadata(tmp_path)

        assert result is None


class TestDetectBaseBranch:
    """Tests for _detect_base_branch function."""

    def test_returns_metadata_branch(self, tmp_path):
        """Test returns branch from metadata when available."""
        metadata_file = tmp_path / "task_metadata.json"
        metadata_file.write_text('{"baseBranch": "custom-branch"}', encoding="utf-8")

        result = _detect_base_branch(tmp_path, tmp_path)

        assert result == "custom-branch"

    def test_returns_env_branch(self, tmp_path, monkeypatch):
        """Test returns branch from DEFAULT_BRANCH env var."""
        monkeypatch.setenv("DEFAULT_BRANCH", "env-branch")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = _detect_base_branch(tmp_path, tmp_path)

        assert result == "env-branch"

    def test_validates_env_branch(self, tmp_path, monkeypatch):
        """Test validates branch from DEFAULT_BRANCH env var."""
        monkeypatch.setenv("DEFAULT_BRANCH", "invalid;branch")

        result = _detect_base_branch(tmp_path, tmp_path)

        # Should skip invalid env branch and fall back
        assert result != "invalid;branch"

    def test_detects_main_branch(self, tmp_path):
        """Test detects main branch when it exists."""
        with patch("subprocess.run") as mock_run:
            # Create a function that returns the appropriate mock based on the command
            def run_side_effect(*args, **kwargs):
                cmd = args[0] if args else []
                # git rev-parse --verify <branch>
                if len(cmd) >= 4 and cmd[0] == "git" and cmd[1] == "rev-parse" and cmd[2] == "--verify":
                    branch = cmd[3]
                    # main exists
                    if branch == "main":
                        return Mock(returncode=0)
                return Mock(returncode=1)

            mock_run.side_effect = run_side_effect
            # Mock check for metadata file - needs to be called on Path instance
            original_exists = Path.exists
            def exists_side_effect(self):
                # Return False for metadata file check
                if "task_metadata.json" in str(self):
                    return False
                return original_exists(self)

            with patch.object(Path, "exists", exists_side_effect):
                result = _detect_base_branch(tmp_path, tmp_path)

        assert result == "main"

    def test_detects_master_branch(self, tmp_path):
        """Test detects master branch when main doesn't exist."""
        with patch("subprocess.run") as mock_run:
            # Track which branches we've "checked"
            branches_checked = []

            # Create a function that returns the appropriate mock based on the command
            def run_side_effect(*args, **kwargs):
                cmd = args[0] if args else []
                # git rev-parse --verify <branch>
                if len(cmd) >= 4 and cmd[0] == "git" and cmd[1] == "rev-parse" and cmd[2] == "--verify":
                    branch = cmd[3]
                    branches_checked.append(branch)
                    # main doesn't exist, master exists
                    if branch == "main":
                        return Mock(returncode=1)
                    elif branch == "master":
                        return Mock(returncode=0)
                return Mock(returncode=1)

            mock_run.side_effect = run_side_effect
            original_exists = Path.exists
            def exists_side_effect(self):
                if "task_metadata.json" in str(self):
                    return False
                return original_exists(self)

            with patch.object(Path, "exists", exists_side_effect):
                result = _detect_base_branch(tmp_path, tmp_path)

        assert result == "master"

    def test_detects_develop_branch(self, tmp_path):
        """Test detects develop branch when main/master don't exist."""
        with patch("subprocess.run") as mock_run:
            # Create a function that returns the appropriate mock based on the command
            def run_side_effect(*args, **kwargs):
                cmd = args[0] if args else []
                # git rev-parse --verify <branch>
                if len(cmd) >= 4 and cmd[0] == "git" and cmd[1] == "rev-parse" and cmd[2] == "--verify":
                    branch = cmd[3]
                    # main doesn't exist, master doesn't exist, develop exists
                    if branch == "main":
                        return Mock(returncode=1)
                    elif branch == "master":
                        return Mock(returncode=1)
                    elif branch == "develop":
                        return Mock(returncode=0)
                return Mock(returncode=1)

            mock_run.side_effect = run_side_effect
            original_exists = Path.exists
            def exists_side_effect(self):
                if "task_metadata.json" in str(self):
                    return False
                return original_exists(self)

            with patch.object(Path, "exists", exists_side_effect):
                result = _detect_base_branch(tmp_path, tmp_path)

        assert result == "develop"

    def test_falls_back_to_main(self, tmp_path):
        """Test falls back to 'main' when nothing else is found."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1)  # All branches fail

            result = _detect_base_branch(tmp_path, tmp_path)

        assert result == "main"

    def test_handles_subprocess_timeout(self, tmp_path):
        """Test handles subprocess timeout gracefully."""
        from subprocess import TimeoutExpired

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = TimeoutExpired("git", 3)

            result = _detect_base_branch(tmp_path, tmp_path)

        # Should fall back to main
        assert result == "main"


class TestGetPlannerPrompt:
    """Tests for get_planner_prompt function."""

    def test_raises_file_not_found(self, tmp_path):
        """Test raises FileNotFoundError when planner.md doesn't exist."""
        with patch("prompts_pkg.prompts.PROMPTS_DIR", tmp_path / "nonexistent"):
            with pytest.raises(FileNotFoundError, match="Planner prompt not found"):
                get_planner_prompt(Path("/spec"))

    def test_injects_spec_path(self, tmp_path):
        """Test injects spec directory path into prompt."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        planner_file = prompts_dir / "planner.md"
        planner_file.write_text("# Planner Content\n\nCreate a plan.", encoding="utf-8")

        spec_dir = Path("/project/specs/001")

        with patch("prompts_pkg.prompts.PROMPTS_DIR", prompts_dir):
            result = get_planner_prompt(spec_dir)

        assert str(spec_dir) in result
        assert "SPEC LOCATION" in result
        assert "Planner Content" in result

    def test_includes_file_creation_instructions(self, tmp_path):
        """Test includes file creation instructions."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        planner_file = prompts_dir / "planner.md"
        planner_file.write_text("# Planner", encoding="utf-8")

        spec_dir = Path("/project/specs/001")

        with patch("prompts_pkg.prompts.PROMPTS_DIR", prompts_dir):
            result = get_planner_prompt(spec_dir)

        assert "implementation_plan.json" in result
        assert "build-progress.txt" in result
        assert "init.sh" in result
        assert "USE WRITE TOOL" in result


class TestGetCodingPrompt:
    """Tests for get_coding_prompt function."""

    def test_raises_file_not_found(self, tmp_path):
        """Test raises FileNotFoundError when coder.md doesn't exist."""
        with patch("prompts_pkg.prompts.PROMPTS_DIR", tmp_path / "nonexistent"):
            with pytest.raises(FileNotFoundError, match="Coding prompt not found"):
                get_coding_prompt(Path("/spec"))

    def test_injects_spec_paths(self, tmp_path):
        """Test injects spec file paths into prompt."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        coder_file = prompts_dir / "coder.md"
        coder_file.write_text("# Coder Content", encoding="utf-8")

        spec_dir = Path("/project/specs/001")

        with patch("prompts_pkg.prompts.PROMPTS_DIR", prompts_dir):
            result = get_coding_prompt(spec_dir)

        assert "spec.md" in result
        assert "implementation_plan.json" in result
        assert "build-progress.txt" in result
        assert "Coder Content" in result

    def test_includes_recovery_context(self, tmp_path):
        """Test includes recovery context when attempt history exists."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        coder_file = prompts_dir / "coder.md"
        coder_file.write_text("# Coder", encoding="utf-8")

        spec_dir = tmp_path / "specs" / "001"
        spec_dir.mkdir(parents=True)
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir()
        history_file = memory_dir / "attempt_history.json"
        history_data = {
            "stuck_subtasks": [
                {"subtask_id": "subtask-1", "reason": " failing", "attempt_count": 3}
            ]
        }
        history_file.write_text(json.dumps(history_data), encoding="utf-8")

        with patch("prompts_pkg.prompts.PROMPTS_DIR", prompts_dir):
            result = get_coding_prompt(spec_dir)

        assert "RECOVERY ALERT" in result
        assert "subtask-1" in result
        assert "3 attempts" in result

    def test_includes_human_input(self, tmp_path):
        """Test includes human input when file exists."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        coder_file = prompts_dir / "coder.md"
        coder_file.write_text("# Coder", encoding="utf-8")

        spec_dir = tmp_path / "specs" / "001"
        spec_dir.mkdir(parents=True)
        human_input_file = spec_dir / "HUMAN_INPUT.md"
        human_input_file.write_text("Please fix the bug in the auth module.", encoding="utf-8")

        with patch("prompts_pkg.prompts.PROMPTS_DIR", prompts_dir):
            result = get_coding_prompt(spec_dir)

        assert "HUMAN INPUT" in result
        assert "fix the bug" in result


class TestGetRecoveryContext:
    """Tests for _get_recovery_context function."""

    def test_returns_empty_when_no_history(self, tmp_path):
        """Test returns empty string when no history file exists."""
        spec_dir = tmp_path / "specs" / "001"
        spec_dir.mkdir(parents=True)

        result = _get_recovery_context(spec_dir)

        assert result == ""

    def test_detects_stuck_subtasks(self, tmp_path):
        """Test detects and reports stuck subtasks."""
        spec_dir = tmp_path / "specs" / "001"
        spec_dir.mkdir(parents=True)
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir()
        history_file = memory_dir / "attempt_history.json"
        history_data = {
            "stuck_subtasks": [
                {"subtask_id": "subtask-1", "reason": "API errors", "attempt_count": 3},
                {"subtask_id": "subtask-2", "reason": "Timeout", "attempt_count": 5},
            ]
        }
        history_file.write_text(json.dumps(history_data), encoding="utf-8")

        result = _get_recovery_context(spec_dir)

        assert "RECOVERY ALERT" in result
        assert "subtask-1" in result
        assert "API errors" in result
        assert "3 attempts" in result
        assert "subtask-2" in result

    def test_detects_retries(self, tmp_path):
        """Test detects subtasks with multiple retries."""
        spec_dir = tmp_path / "specs" / "001"
        spec_dir.mkdir(parents=True)
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir()
        history_file = memory_dir / "attempt_history.json"
        history_data = {
            "subtasks": {
                "subtask-1": {
                    "attempts": [{}, {}, {}],
                    "status": "pending",
                },
                "subtask-2": {
                    "attempts": [{}, {}],
                    "status": "pending",
                }
            }
        }
        history_file.write_text(json.dumps(history_data), encoding="utf-8")

        result = _get_recovery_context(spec_dir)

        assert "RETRY AWARENESS" in result
        assert "subtask-1" in result
        assert "3 attempts" in result
        assert "subtask-2" in result

    def test_ignores_completed_subtasks(self, tmp_path):
        """Test ignores completed subtasks in retry check."""
        spec_dir = tmp_path / "specs" / "001"
        spec_dir.mkdir(parents=True)
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir()
        history_file = memory_dir / "attempt_history.json"
        history_data = {
            "subtasks": {
                "subtask-1": {
                    "attempts": [{}, {}],
                    "status": "completed",
                }
            }
        }
        history_file.write_text(json.dumps(history_data), encoding="utf-8")

        result = _get_recovery_context(spec_dir)

        assert "RETRY AWARENESS" not in result

    def test_handles_invalid_json(self, tmp_path):
        """Test handles invalid JSON gracefully."""
        spec_dir = tmp_path / "specs" / "001"
        spec_dir.mkdir(parents=True)
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir()
        history_file = memory_dir / "attempt_history.json"
        history_file.write_text("{invalid}", encoding="utf-8")

        result = _get_recovery_context(spec_dir)

        assert result == ""

    def test_handles_os_error(self, tmp_path):
        """Test handles OS errors gracefully."""
        spec_dir = tmp_path / "specs" / "001"
        spec_dir.mkdir(parents=True)
        memory_dir = spec_dir / "memory"
        memory_dir.mkdir()
        # Create a directory instead of a file
        history_file = memory_dir / "attempt_history.json"
        history_file.mkdir()

        result = _get_recovery_context(spec_dir)

        assert result == ""


class TestGetFollowupPlannerPrompt:
    """Tests for get_followup_planner_prompt function."""

    def test_raises_file_not_found(self, tmp_path):
        """Test raises FileNotFoundError when followup_planner.md doesn't exist."""
        with patch("prompts_pkg.prompts.PROMPTS_DIR", tmp_path / "nonexistent"):
            with pytest.raises(FileNotFoundError, match="Follow-up planner prompt not found"):
                get_followup_planner_prompt(Path("/spec"))

    def test_injects_followup_context(self, tmp_path):
        """Test injects follow-up specific context."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        followup_file = prompts_dir / "followup_planner.md"
        followup_file.write_text("# Followup Planner", encoding="utf-8")

        spec_dir = Path("/project/specs/001")

        with patch("prompts_pkg.prompts.PROMPTS_DIR", prompts_dir):
            result = get_followup_planner_prompt(spec_dir)

        assert "FOLLOW-UP MODE" in result
        assert "FOLLOWUP_REQUEST.md" in result
        assert "APPEND to this" in result
        assert "Followup Planner" in result


class TestIsFirstRun:
    """Tests for is_first_run function."""

    def test_returns_true_when_missing(self, tmp_path):
        """Test returns True when implementation_plan.json doesn't exist."""
        result = is_first_run(tmp_path)

        assert result is True

    def test_returns_true_for_empty_plan(self, tmp_path):
        """Test returns True for plan with no phases."""
        plan_file = tmp_path / "implementation_plan.json"
        plan_file.write_text('{"phases": []}', encoding="utf-8")

        result = is_first_run(tmp_path)

        assert result is True

    def test_returns_true_for_phases_with_no_subtasks(self, tmp_path):
        """Test returns True when phases have no subtasks."""
        plan_data = {
            "phases": [
                {"name": "Phase 1", "subtasks": []},
                {"name": "Phase 2", "subtasks": []},
            ]
        }
        plan_file = tmp_path / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

        result = is_first_run(tmp_path)

        assert result is True

    def test_returns_false_for_plan_with_subtasks(self, tmp_path):
        """Test returns False when plan has subtasks."""
        plan_data = {
            "phases": [
                {
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending"}
                    ]
                }
            ]
        }
        plan_file = tmp_path / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

        result = is_first_run(tmp_path)

        assert result is False

    def test_returns_true_for_invalid_json(self, tmp_path):
        """Test returns True for invalid JSON."""
        plan_file = tmp_path / "implementation_plan.json"
        plan_file.write_text("{invalid", encoding="utf-8")

        result = is_first_run(tmp_path)

        assert result is True

    def test_returns_true_on_os_error(self, tmp_path):
        """Test returns True on OS error."""
        # Create a directory instead of a file
        plan_dir = tmp_path / "implementation_plan.json"
        plan_dir.mkdir()

        result = is_first_run(tmp_path)

        assert result is True


class TestGetQaReviewerPrompt:
    """Tests for get_qa_reviewer_prompt function."""

    def test_loads_base_prompt(self, tmp_path):
        """Test loads base QA reviewer prompt."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        qa_file = prompts_dir / "qa_reviewer.md"
        qa_file.write_text("# QA Reviewer\n\nReview the code.", encoding="utf-8")

        spec_dir = tmp_path / "specs" / "001"
        spec_dir.mkdir(parents=True)
        project_dir = tmp_path

        with patch("prompts_pkg.prompts.PROMPTS_DIR", prompts_dir):
            result = get_qa_reviewer_prompt(spec_dir, project_dir)

        assert "QA Reviewer" in result

    def test_detects_base_branch(self, tmp_path):
        """Test detects and injects base branch."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        qa_file = prompts_dir / "qa_reviewer.md"
        qa_file.write_text("Compare: {{BASE_BRANCH}}", encoding="utf-8")

        spec_dir = tmp_path / "specs" / "001"
        spec_dir.mkdir(parents=True)
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("prompts_pkg.prompts.PROMPTS_DIR", prompts_dir):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)  # main exists

                result = get_qa_reviewer_prompt(spec_dir, project_dir)

        assert "main" in result

    def test_includes_spec_paths(self, tmp_path):
        """Test includes spec file paths."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        qa_file = prompts_dir / "qa_reviewer.md"
        qa_file.write_text("# QA", encoding="utf-8")

        spec_dir = tmp_path / "specs" / "001"
        spec_dir.mkdir(parents=True)
        project_dir = tmp_path

        with patch("prompts_pkg.prompts.PROMPTS_DIR", prompts_dir):
            result = get_qa_reviewer_prompt(spec_dir, project_dir)

        assert "qa_report.md" in result
        assert "QA_FIX_REQUEST.md" in result

    def test_detects_project_capabilities(self, tmp_path):
        """Test detects and lists project capabilities."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        qa_file = prompts_dir / "qa_reviewer.md"
        qa_file.write_text("# QA\n\n<!-- PROJECT-SPECIFIC VALIDATION TOOLS WILL BE INJECTED HERE -->\n\n<!-- - API validation (for projects with API endpoints) -->", encoding="utf-8")

        # Create project index
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()
        index_file = auto_claude_dir / "project_index.json"
        index_data = {
            "services": {
                "backend": {
                    "dependencies": ["fastapi"],
                    "api": {"routes": ["/api/*"]},
                }
            }
        }
        index_file.write_text(json.dumps(index_data), encoding="utf-8")

        spec_dir = tmp_path / "specs" / "001"
        spec_dir.mkdir(parents=True)
        project_dir = tmp_path

        with patch("prompts_pkg.prompts.PROMPTS_DIR", prompts_dir):
            result = get_qa_reviewer_prompt(spec_dir, project_dir)

        assert "PROJECT CAPABILITIES DETECTED" in result
        assert "- Api" in result  # Capitalization in output is "Api" not "Has Api"


class TestGetQaFixerPrompt:
    """Tests for get_qa_fixer_prompt function."""

    def test_loads_base_prompt(self, tmp_path):
        """Test loads base QA fixer prompt."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        fixer_file = prompts_dir / "qa_fixer.md"
        fixer_file.write_text("# QA Fixer\n\nFix the issues.", encoding="utf-8")

        spec_dir = Path("/project/specs/001")
        project_dir = Path("/project")

        with patch("prompts_pkg.prompts.PROMPTS_DIR", prompts_dir):
            result = get_qa_fixer_prompt(spec_dir, project_dir)

        assert "QA Fixer" in result

    def test_includes_spec_paths(self, tmp_path):
        """Test includes spec file paths."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        fixer_file = prompts_dir / "qa_fixer.md"
        fixer_file.write_text("# Fixer", encoding="utf-8")

        spec_dir = Path("/project/specs/001")
        project_dir = Path("/project")

        with patch("prompts_pkg.prompts.PROMPTS_DIR", prompts_dir):
            result = get_qa_fixer_prompt(spec_dir, project_dir)

        assert "QA_FIX_REQUEST.md" in result
        assert "qa_report.md" in result

    def test_includes_project_root(self, tmp_path):
        """Test includes project root path."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        fixer_file = prompts_dir / "qa_fixer.md"
        fixer_file.write_text("# Fixer", encoding="utf-8")

        spec_dir = Path("/project/specs/001")
        project_dir = Path("/project")

        with patch("prompts_pkg.prompts.PROMPTS_DIR", prompts_dir):
            result = get_qa_fixer_prompt(spec_dir, project_dir)

        assert str(project_dir) in result
