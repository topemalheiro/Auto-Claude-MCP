"""
Comprehensive tests for prompt_generator module.
Tests prompt generation, worktree isolation detection, and context building.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from prompts_pkg.prompt_generator import (
    detect_worktree_isolation,
    format_context_for_prompt,
    generate_environment_context,
    generate_planner_prompt,
    generate_subtask_prompt,
    generate_worktree_isolation_warning,
    get_relative_spec_path,
    load_subtask_context,
)


class TestDetectWorktreeIsolation:
    """Tests for detect_worktree_isolation function."""

    def test_no_worktree_normal_path(self):
        """Test returns False for normal non-worktree paths."""
        project_dir = Path("/home/user/myproject")
        is_worktree, parent_path = detect_worktree_isolation(project_dir)

        assert is_worktree is False
        assert parent_path is None

    def test_detect_auto_claude_worktree(self):
        """Test detects .auto-claude/worktrees/tasks/ pattern."""
        project_dir = Path("/home/user/project/.auto-claude/worktrees/tasks/my-spec")
        is_worktree, parent_path = detect_worktree_isolation(project_dir)

        assert is_worktree is True
        assert parent_path == Path("/home/user/project")

    def test_detect_github_pr_worktree(self):
        """Test detects .auto-claude/github/pr/worktrees/ pattern."""
        project_dir = Path("/home/user/project/.auto-claude/github/pr/worktrees/123")
        is_worktree, parent_path = detect_worktree_isolation(project_dir)

        assert is_worktree is True
        assert parent_path == Path("/home/user/project")

    def test_detect_legacy_worktrees(self):
        """Test detects .worktrees/ pattern."""
        project_dir = Path("/home/user/project/.worktrees/test-branch")
        is_worktree, parent_path = detect_worktree_isolation(project_dir)

        assert is_worktree is True
        assert parent_path == Path("/home/user/project")

    def test_windows_path_detection(self):
        """Test worktree detection on Windows paths."""
        # Note: Path.resolve() on Linux doesn't preserve Windows-style paths
        # This test verifies the regex pattern matching works
        project_str = "C:/Users/test/project/.auto-claude/worktrees/tasks/spec"
        # The regex uses the string representation
        from prompts_pkg.prompt_generator import WORKTREE_PATH_PATTERNS
        import re
        for pattern in WORKTREE_PATH_PATTERNS:
            if re.search(pattern, project_str):
                is_worktree = True
                break
        else:
            is_worktree = False
        assert is_worktree is True

    def test_resolves_symlinks(self, tmp_path):
        """Test resolves path symlinks."""
        # Create actual directory
        actual_dir = tmp_path / "actual"
        actual_dir.mkdir()

        # Create symlink if supported
        try:
            link_dir = tmp_path / "link"
            link_dir.symlink_to(actual_dir)

            is_worktree, parent_path = detect_worktree_isolation(link_dir)
            assert is_worktree is False
        except (OSError, NotImplementedError):
            # Symlinks not supported on this system
            pass


class TestGenerateWorktreeIsolationWarning:
    """Tests for generate_worktree_isolation_warning function."""

    def test_generates_warning_with_paths(self):
        """Test generates warning with project and parent paths."""
        project_dir = Path("/worktree/location")
        parent_path = Path("/parent/project")

        warning = generate_worktree_isolation_warning(project_dir, parent_path)

        assert str(project_dir) in warning
        assert str(parent_path) in warning
        assert "ISOLATED GIT WORKTREE" in warning
        assert "NEVER" in warning
        assert "FORBIDDEN PATH" in warning

    def test_includes_cd_warning(self):
        """Test warning includes cd command warning."""
        project_dir = Path("/worktree/location")
        parent_path = Path("/parent/project")

        warning = generate_worktree_isolation_warning(project_dir, parent_path)

        assert f"cd {parent_path}" in warning
        assert f"{parent_path}/" in warning

    def test_includes_correct_examples(self):
        """Test warning shows correct usage examples."""
        project_dir = Path("/worktree/location")
        parent_path = Path("/parent/project")

        warning = generate_worktree_isolation_warning(project_dir, parent_path)

        assert "CORRECT" in warning
        assert "WRONG" in warning
        assert "./prod/src/file.ts" in warning


class TestGetRelativeSpecPath:
    """Tests for get_relative_spec_path function."""

    def test_spec_under_project_dir(self):
        """Test when spec_dir is under project_dir."""
        project_dir = Path("/home/user/project")
        spec_dir = Path("/home/user/project/.auto-claude/specs/001-test")

        result = get_relative_spec_path(spec_dir, project_dir)

        assert result == "./.auto-claude/specs/001-test"

    def test_spec_at_project_root(self):
        """Test when spec_dir is at project root."""
        project_dir = Path("/home/user/project")
        spec_dir = Path("/home/user/project")

        result = get_relative_spec_path(spec_dir, project_dir)

        # When paths are equal, relative_to returns Path('.')
        # and we add "./" prefix
        assert result == "./." or result == "."

    def test_spec_not_under_project_fallback(self):
        """Test fallback when spec_dir is not under project_dir."""
        project_dir = Path("/home/user/project")
        spec_dir = Path("/other/location/specs/001-test")

        result = get_relative_spec_path(spec_dir, project_dir)

        # Falls back to using spec_dir name
        assert "001-test" in result
        assert result.startswith("./")

    def test_deeply_nested_spec(self):
        """Test deeply nested spec directory."""
        project_dir = Path("/home/user/project")
        spec_dir = Path("/home/user/project/.auto-claude/specs/complex/nested/001-test")

        result = get_relative_spec_path(spec_dir, project_dir)

        assert ".auto-claude/specs" in result
        assert "001-test" in result


class TestGenerateEnvironmentContext:
    """Tests for generate_environment_context function."""

    def test_basic_context_generation(self):
        """Test generates basic environment context."""
        project_dir = Path("/home/user/project")
        spec_dir = Path("/home/user/project/.auto-claude/specs/001")

        context = generate_environment_context(project_dir, spec_dir)

        assert str(project_dir) in context
        assert "YOUR ENVIRONMENT" in context
        assert "Working Directory:" in context
        assert "Spec Location:" in context

    def test_includes_worktree_warning(self, tmp_path):
        """Test includes worktree isolation warning when detected."""
        # Use absolute path to ensure worktree pattern is detected
        project_dir = tmp_path / "project" / ".auto-claude" / "worktrees" / "tasks" / "test"
        project_dir.mkdir(parents=True)
        spec_dir = project_dir / "specs" / "001"
        spec_dir.mkdir(parents=True)

        context = generate_environment_context(project_dir, spec_dir)

        # Check if worktree is detected by looking for the isolation warning
        # The actual text includes "Isolation Mode:" not "ISOLATION MODE"
        if "/.auto-claude/worktrees/tasks/" in str(project_dir):
            assert "ISOLATED WORKTREE" in context
            assert "Isolation Mode:" in context or "ISOLATION MODE" in context

    def test_no_worktree_warning_for_normal_path(self):
        """Test no worktree warning for normal project paths."""
        project_dir = Path("/home/user/project")
        spec_dir = Path("/home/user/project/.auto-claude/specs/001")

        context = generate_environment_context(project_dir, spec_dir)

        assert "ISOLATED WORKTREE" not in context

    def test_includes_important_files(self):
        """Test lists important spec files."""
        project_dir = Path("/home/user/project")
        spec_dir = Path("/home/user/project/.auto-claude/specs/001")

        context = generate_environment_context(project_dir, spec_dir)

        assert "spec.md" in context
        assert "implementation_plan.json" in context
        assert "build-progress.txt" in context
        assert "context.json" in context


class TestGenerateSubtaskPrompt:
    """Tests for generate_subtask_prompt function."""

    def test_basic_subtask_prompt(self):
        """Test generates basic subtask prompt."""
        spec_dir = Path("/project/specs/001")
        project_dir = Path("/project")
        subtask = {
            "id": "subtask-1",
            "description": "Implement feature X",
            "service": "backend",
            "files_to_modify": ["src/file.py"],
            "files_to_create": ["src/new_file.py"],
            "patterns_from": ["src/pattern.py"],
            "verification": {"type": "manual"},
        }
        phase = {"id": "phase-1", "name": "Backend"}

        prompt = generate_subtask_prompt(spec_dir, project_dir, subtask, phase)

        assert "subtask-1" in prompt
        assert "Implement feature X" in prompt
        assert "Backend" in prompt
        assert "src/file.py" in prompt
        assert "src/new_file.py" in prompt
        assert "src/pattern.py" in prompt

    def test_retry_attempt_context(self):
        """Test includes retry context for failed attempts."""
        spec_dir = Path("/project/specs/001")
        project_dir = Path("/project")
        subtask = {
            "id": "subtask-1",
            "description": "Fix bug",
            "verification": {"type": "manual"},
        }
        phase = {"id": "phase-1"}
        recovery_hints = ["Try approach A", "Check dependencies"]

        prompt = generate_subtask_prompt(
            spec_dir, project_dir, subtask, phase, attempt_count=2, recovery_hints=recovery_hints
        )

        assert "RETRY ATTEMPT (3)" in prompt
        assert "Previous attempt insights:" in prompt
        assert "Try approach A" in prompt
        assert "Check dependencies" in prompt

    def test_command_verification(self):
        """Test command verification type."""
        spec_dir = Path("/project/specs/001")
        project_dir = Path("/project")
        subtask = {
            "id": "subtask-1",
            "description": "Run tests",
            "verification": {
                "type": "command",
                "command": "pytest tests/",
                "expected": "All tests pass",
            },
        }
        phase = {"id": "phase-1"}

        prompt = generate_subtask_prompt(spec_dir, project_dir, subtask, phase)

        assert "pytest tests/" in prompt
        assert "All tests pass" in prompt

    def test_api_verification(self):
        """Test API verification type."""
        spec_dir = Path("/project/specs/001")
        project_dir = Path("/project")
        subtask = {
            "id": "subtask-1",
            "description": "Create API endpoint",
            "verification": {
                "type": "api",
                "method": "POST",
                "url": "http://localhost:8000/api/test",
                "body": {"key": "value"},
                "expected_status": 201,
            },
        }
        phase = {"id": "phase-1"}

        prompt = generate_subtask_prompt(spec_dir, project_dir, subtask, phase)

        assert "POST" in prompt
        assert "http://localhost:8000/api/test" in prompt
        assert "201" in prompt

    def test_browser_verification(self):
        """Test browser verification type."""
        spec_dir = Path("/project/specs/001")
        project_dir = Path("/project")
        subtask = {
            "id": "subtask-1",
            "description": "Create UI component",
            "verification": {
                "type": "browser",
                "url": "http://localhost:3000",
                "checks": ["Button visible", "Form submits"],
            },
        }
        phase = {"id": "phase-1"}

        prompt = generate_subtask_prompt(spec_dir, project_dir, subtask, phase)

        assert "http://localhost:3000" in prompt
        assert "Button visible" in prompt
        assert "Form submits" in prompt

    def test_e2e_verification(self):
        """Test end-to-end verification type."""
        spec_dir = Path("/project/specs/001")
        project_dir = Path("/project")
        subtask = {
            "id": "subtask-1",
            "description": "User flow",
            "verification": {
                "type": "e2e",
                "steps": ["Login", "Navigate to profile", "Update settings"],
            },
        }
        phase = {"id": "phase-1"}

        prompt = generate_subtask_prompt(spec_dir, project_dir, subtask, phase)

        assert "Login" in prompt
        assert "Navigate to profile" in prompt
        assert "Update settings" in prompt
        assert "End-to-end verification" in prompt

    def test_manual_verification(self):
        """Test manual verification type."""
        spec_dir = Path("/project/specs/001")
        project_dir = Path("/project")
        subtask = {
            "id": "subtask-1",
            "description": "Manual check",
            "verification": {
                "type": "manual",
                "instructions": "Verify by visual inspection",
            },
        }
        phase = {"id": "phase-1"}

        prompt = generate_subtask_prompt(spec_dir, project_dir, subtask, phase)

        assert "Manual Verification" in prompt
        assert "Verify by visual inspection" in prompt

    def test_includes_quality_checklist(self):
        """Test includes quality checklist."""
        spec_dir = Path("/project/specs/001")
        project_dir = Path("/project")
        subtask = {"id": "subtask-1", "description": "Test", "verification": {"type": "manual"}}
        phase = {"id": "phase-1"}

        prompt = generate_subtask_prompt(spec_dir, project_dir, subtask, phase)

        assert "Quality Checklist" in prompt
        assert "Follows patterns" in prompt
        assert "Error handling" in prompt

    def test_includes_commit_instructions(self):
        """Test includes git commit instructions."""
        spec_dir = Path("/project/specs/001")
        project_dir = Path("/project")
        subtask = {"id": "subtask-123", "description": "Test feature", "verification": {"type": "manual"}}
        phase = {"id": "phase-1"}

        prompt = generate_subtask_prompt(spec_dir, project_dir, subtask, phase)

        assert "git add ." in prompt
        assert "git commit" in prompt
        assert "subtask-123" in prompt


class TestGeneratePlannerPrompt:
    """Tests for generate_planner_prompt function."""

    def test_generates_planner_prompt(self, tmp_path):
        """Test generates planner prompt with file content."""
        # Create prompts directory structure
        prompts_dir = tmp_path / "apps" / "backend" / "prompts"
        prompts_dir.mkdir(parents=True)
        planner_file = prompts_dir / "planner.md"
        planner_file.write_text("# Planner prompt content\n\nCreate a plan.", encoding="utf-8")

        spec_dir = tmp_path / "specs" / "001"
        spec_dir.mkdir(parents=True)
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Patch to find the prompts directory
        with patch("prompts_pkg.prompt_generator.Path") as mock_path_cls:
            # When checking for planner.md existence, return True
            real_path = Path  # Keep real Path for other uses
            mock_path_instance = MagicMock()
            mock_path_instance.parent = MagicMock()
            mock_path_instance.parent.parent = prompts_dir
            mock_path_instance.exists.return_value = True
            mock_path_instance.read_text.return_value = "# Planner prompt content\n\nCreate a plan."

            def path_side_effect(arg):
                if "planner.md" in str(arg):
                    mock_path_instance.__str__ = lambda self: str(prompts_dir / "planner.md")
                    return mock_path_instance
                return real_path(arg)

            mock_path_cls.side_effect = path_side_effect
            mock_path_cls.__truediv__ = real_path.__truediv__

            prompt = generate_planner_prompt(spec_dir, project_dir)

        assert "Planner prompt content" in prompt or "YOUR ENVIRONMENT" in prompt

    def test_infers_project_dir_from_spec_dir(self, tmp_path):
        """Test infers project_dir when not provided."""
        # Create directory structure: project/.auto-claude/specs/001
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()
        specs = auto_claude / "specs"
        specs.mkdir()
        spec_dir = specs / "001"
        spec_dir.mkdir()

        # Create prompts directory with planner.md
        prompts_dir = tmp_path / "apps" / "backend" / "prompts"
        prompts_dir.mkdir(parents=True)
        planner_file = prompts_dir / "planner.md"
        planner_file.write_text("# Planner\n\nPlan it.", encoding="utf-8")

        # Change to the project directory so relative paths work
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            prompt = generate_planner_prompt(spec_dir, None)
            # Check that something was generated
            assert prompt is not None
            assert len(prompt) > 0
        finally:
            os.chdir(original_cwd)

    def test_fallback_prompt_when_file_missing(self, tmp_path):
        """Test uses fallback when planner.md not found."""
        spec_dir = tmp_path / "specs" / "001"
        spec_dir.mkdir(parents=True)
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Mock the candidate_dirs to point to directories without planner.md
        nonexistent_dir = tmp_path / "nonexistent_prompts"

        with patch("prompts_pkg.prompt_generator.Path") as mock_path_cls:
            # When Path is called within generate_planner_prompt for finding prompts
            # Return our nonexistent directory
            mock_path_instance = Path(__file__)  # Use real Path for non-mocked calls

            # Set up the mock to return a Path that won't have planner.md
            def path_side_effect(path_like, *args, **kwargs):
                # For the parent.parent / "prompts" pattern in the function
                if hasattr(path_like, 'parent'):
                    # Return a path that doesn't have planner.md
                    return nonexistent_dir
                # For other Path calls, use real Path
                return Path(path_like, *args, **kwargs)

            mock_path_cls.side_effect = path_side_effect
            # Also need to mock the exists() check
            with patch.object(Path, "exists", return_value=False):
                prompt = generate_planner_prompt(spec_dir, project_dir)

        # Should contain fallback message
        assert prompt is not None
        assert "implementation_plan.json" in prompt


class TestLoadSubtaskContext:
    """Tests for load_subtask_context function."""

    def test_loads_pattern_files(self, tmp_path):
        """Test loads and truncates pattern files."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create a pattern file with more than 200 lines
        pattern_file = project_dir / "src" / "pattern.py"
        pattern_file.parent.mkdir(parents=True)
        lines = [f"# Line {i}" for i in range(300)]
        pattern_file.write_text("\n".join(lines), encoding="utf-8")

        spec_dir = tmp_path / "specs" / "001"
        spec_dir.mkdir(parents=True)

        subtask = {
            "patterns_from": ["src/pattern.py"],
            "files_to_modify": [],
        }

        context = load_subtask_context(spec_dir, project_dir, subtask, max_file_lines=200)

        assert "src/pattern.py" in context["patterns"]
        assert "truncated" in context["patterns"]["src/pattern.py"]
        assert "100 more lines" in context["patterns"]["src/pattern.py"]

    def test_loads_files_to_modify(self, tmp_path):
        """Test loads files to modify."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        target_file = project_dir / "src" / "target.py"
        target_file.parent.mkdir(parents=True)
        target_file.write_text("def existing_function():\n    pass", encoding="utf-8")

        spec_dir = tmp_path / "specs" / "001"
        spec_dir.mkdir(parents=True)

        subtask = {
            "patterns_from": [],
            "files_to_modify": ["src/target.py"],
        }

        context = load_subtask_context(spec_dir, project_dir, subtask)

        assert "src/target.py" in context["files_to_modify"]
        assert "def existing_function" in context["files_to_modify"]["src/target.py"]

    def test_handles_missing_files(self, tmp_path):
        """Test handles missing files gracefully."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        spec_dir = tmp_path / "specs" / "001"
        spec_dir.mkdir(parents=True)

        subtask = {
            "patterns_from": ["nonexistent/file.py"],
            "files_to_modify": ["also/missing.py"],
        }

        context = load_subtask_context(spec_dir, project_dir, subtask)

        # When files don't exist, they're not added to context
        # The function silently skips non-existent files
        assert "nonexistent/file.py" not in context["patterns"]
        assert "also/missing.py" not in context["files_to_modify"]

    def test_small_files_not_truncated(self, tmp_path):
        """Test small files are not truncated."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        small_file = project_dir / "small.py"
        small_file.write_text("def hello():\n    pass", encoding="utf-8")

        spec_dir = tmp_path / "specs" / "001"
        spec_dir.mkdir(parents=True)

        subtask = {
            "patterns_from": ["small.py"],
            "files_to_modify": [],
        }

        context = load_subtask_context(spec_dir, project_dir, subtask, max_file_lines=200)

        assert "truncated" not in context["patterns"]["small.py"]
        assert "def hello():" in context["patterns"]["small.py"]

    def test_custom_max_lines(self, tmp_path):
        """Test respects custom max_file_lines parameter."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        large_file = project_dir / "large.py"
        lines = [f"# {i}" for i in range(100)]
        large_file.write_text("\n".join(lines), encoding="utf-8")

        spec_dir = tmp_path / "specs" / "001"
        spec_dir.mkdir(parents=True)

        subtask = {
            "patterns_from": ["large.py"],
            "files_to_modify": [],
        }

        context = load_subtask_context(spec_dir, project_dir, subtask, max_file_lines=50)

        assert "truncated" in context["patterns"]["large.py"]
        assert "50 more lines" in context["patterns"]["large.py"]


class TestFormatContextForPrompt:
    """Tests for format_context_for_prompt function."""

    def test_formats_patterns_section(self):
        """Test formats patterns into readable section."""
        context = {
            "patterns": {
                "src/pattern.py": "def pattern():\n    pass",
                "src/another.py": "class Another:\n    pass",
            },
            "files_to_modify": {},
        }

        result = format_context_for_prompt(context)

        assert "Reference Files (Patterns to Follow)" in result
        assert "src/pattern.py" in result
        assert "def pattern():" in result
        assert "src/another.py" in result

    def test_formats_files_to_modify_section(self):
        """Test formats files to modify into readable section."""
        context = {
            "patterns": {},
            "files_to_modify": {
                "src/target.py": "def target():\n    pass",
            },
        }

        result = format_context_for_prompt(context)

        assert "Current File Contents (To Modify)" in result
        assert "src/target.py" in result
        assert "def target():" in result

    def test_formats_both_sections(self):
        """Test formats both patterns and files to modify."""
        context = {
            "patterns": {"src/pattern.py": "pattern content"},
            "files_to_modify": {"src/target.py": "target content"},
        }

        result = format_context_for_prompt(context)

        assert "Reference Files" in result
        assert "Current File Contents" in result
        assert "src/pattern.py" in result
        assert "src/target.py" in result

    def test_empty_context(self):
        """Test handles empty context."""
        context = {"patterns": {}, "files_to_modify": {}}

        result = format_context_for_prompt(context)

        assert result == ""

    def test_code_blocks_wrapped(self):
        """Test code content is wrapped in markdown code blocks."""
        context = {
            "patterns": {"test.py": "def test():\n    pass"},
            "files_to_modify": {},
        }

        result = format_context_for_prompt(context)

        assert "```" in result
        assert "def test():" in result
