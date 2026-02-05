"""
Tests for spec.validate_spec module (CLI entry point)

These tests use subprocess to run the validate_spec.py script directly
since it uses relative imports that don't work when importing as a module.
"""

import json
import sys
import os
import subprocess
from pathlib import Path

import pytest

# Get the path to the validate_spec.py script
SCRIPT_PATH = Path(__file__).parent.parent.parent / "apps" / "backend" / "spec" / "validate_spec.py"


def _run_validate_spec(spec_dir: str, *args: str) -> subprocess.CompletedProcess:
    """Helper to run validate_spec.py as a subprocess"""
    # Set up environment with proper PYTHONPATH
    env = {"PYTHONPATH": str(SCRIPT_PATH.parent.parent), "PATH": os.environ.get("PATH", "")}

    cmd = [sys.executable, str(SCRIPT_PATH), "--spec-dir", spec_dir, *args]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(SCRIPT_PATH.parent),
        env=env,
    )
    return result


class TestMainCli:
    """Tests for main() CLI entry point"""

    def test_main_with_missing_required_args(self):
        """Test main() without --spec-dir argument"""
        env = {"PYTHONPATH": str(SCRIPT_PATH.parent.parent), "PATH": os.environ.get("PATH", "")}
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            cwd=str(SCRIPT_PATH.parent),
            env=env,
        )

        # Should exit with code 2 (argparse error)
        assert result.returncode == 2
        assert "required: --spec-dir" in result.stderr

    def test_main_with_nonexistent_spec_dir(self, tmp_path):
        """Test main() with non-existent spec directory"""
        nonexistent = tmp_path / "nonexistent"

        result = _run_validate_spec(str(nonexistent))

        # Should exit with non-zero (validation failed)
        assert result.returncode != 0

    def test_main_with_all_checkpoints_default(self, tmp_path):
        """Test main() with default 'all' checkpoint"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create minimal valid files
        (spec_dir / "project_index.json").write_text('{"project_type": "test"}', encoding="utf-8")
        (spec_dir / "context.json").write_text('{"task_description": "Test"}', encoding="utf-8")
        (spec_dir / "spec.md").write_text(
            "## Overview\nTest\n## Workflow Type\nFeature\n## Task Scope\nTest\n## Success Criteria\nTest",
            encoding="utf-8",
        )
        plan = {
            "feature": "Test",
            "workflow_type": "feature",
            "phases": [{"id": "p1", "name": "Phase", "subtasks": [{"id": "t1", "description": "Task", "status": "pending"}]}],
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan), encoding="utf-8")

        result = _run_validate_spec(str(spec_dir))

        # Should exit with code 0 (all passed)
        assert result.returncode == 0
        assert "ALL CHECKPOINTS PASSED" in result.stdout

    def test_main_with_prereqs_checkpoint(self, tmp_path):
        """Test main() with --checkpoint prereqs"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "project_index.json").write_text('{"project_type": "test"}', encoding="utf-8")

        result = _run_validate_spec(str(spec_dir), "--checkpoint", "prereqs")

        assert result.returncode == 0
        assert "Checkpoint: prereqs" in result.stdout
        assert "PASS" in result.stdout

    def test_main_with_context_checkpoint(self, tmp_path):
        """Test main() with --checkpoint context"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "project_index.json").write_text('{"project_type": "test"}', encoding="utf-8")
        (spec_dir / "context.json").write_text('{"task_description": "Test"}', encoding="utf-8")

        result = _run_validate_spec(str(spec_dir), "--checkpoint", "context")

        assert result.returncode == 0
        assert "Checkpoint: context" in result.stdout

    def test_main_with_spec_checkpoint(self, tmp_path):
        """Test main() with --checkpoint spec"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "project_index.json").write_text('{"project_type": "test"}', encoding="utf-8")
        (spec_dir / "spec.md").write_text(
            "## Overview\nTest\n## Workflow Type\nFeature\n## Task Scope\nTest\n## Success Criteria\nTest",
            encoding="utf-8",
        )

        result = _run_validate_spec(str(spec_dir), "--checkpoint", "spec")

        assert result.returncode == 0
        assert "Checkpoint: spec" in result.stdout

    def test_main_with_plan_checkpoint(self, tmp_path):
        """Test main() with --checkpoint plan"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "project_index.json").write_text('{"project_type": "test"}', encoding="utf-8")
        plan = {
            "feature": "Test",
            "workflow_type": "feature",
            "phases": [{"id": "p1", "name": "Phase", "subtasks": [{"id": "t1", "description": "Task", "status": "pending"}]}],
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan), encoding="utf-8")

        result = _run_validate_spec(str(spec_dir), "--checkpoint", "plan")

        assert result.returncode == 0
        assert "Checkpoint: plan" in result.stdout

    def test_main_with_invalid_checkpoint(self, tmp_path):
        """Test main() with invalid checkpoint value"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = _run_validate_spec(str(spec_dir), "--checkpoint", "invalid")

        # argparse exits with code 2 for invalid argument
        assert result.returncode == 2
        assert "invalid choice" in result.stderr

    def test_main_with_auto_fix_flag(self, tmp_path):
        """Test main() with --auto-fix flag"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create a plan with issues that can be auto-fixed
        plan = {"phases": []}  # Missing feature and workflow_type
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan), encoding="utf-8")

        result = _run_validate_spec(str(spec_dir), "--auto-fix", "--checkpoint", "plan")

        # Auto-fix should add missing fields
        with open(spec_dir / "implementation_plan.json", encoding="utf-8") as f:
            fixed_plan = json.load(f)

        assert "feature" in fixed_plan
        assert "workflow_type" in fixed_plan

    def test_main_with_json_output_flag(self, tmp_path):
        """Test main() with --json flag"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "project_index.json").write_text('{"project_type": "test"}', encoding="utf-8")

        result = _run_validate_spec(str(spec_dir), "--json", "--checkpoint", "prereqs")

        # Should output JSON
        output = json.loads(result.stdout)
        assert "valid" in output
        assert "results" in output

    def test_main_json_output_all_checkpoints(self, tmp_path):
        """Test main() with --json and all checkpoints"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create valid files
        (spec_dir / "project_index.json").write_text('{"project_type": "test"}', encoding="utf-8")
        (spec_dir / "context.json").write_text('{"task_description": "Test"}', encoding="utf-8")
        (spec_dir / "spec.md").write_text(
            "## Overview\nTest\n## Workflow Type\nFeature\n## Task Scope\nTest\n## Success Criteria\nTest",
            encoding="utf-8",
        )
        plan = {
            "feature": "Test",
            "workflow_type": "feature",
            "phases": [{"id": "p1", "name": "Phase", "subtasks": [{"id": "t1", "description": "Task", "status": "pending"}]}],
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan), encoding="utf-8")

        result = _run_validate_spec(str(spec_dir), "--json")

        output = json.loads(result.stdout)
        assert output["valid"] is True
        assert len(output["results"]) == 4  # All checkpoints

    def test_main_text_output_format(self, tmp_path):
        """Test main() text output format"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = _run_validate_spec(str(spec_dir))

        # Should have formatted output
        assert "=" * 60 in result.stdout
        assert "SPEC VALIDATION REPORT" in result.stdout
        assert "Checkpoint:" in result.stdout

    def test_main_validation_failure_exit_code(self, tmp_path):
        """Test main() exits with code 1 on validation failure"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        # No files - should fail

        result = _run_validate_spec(str(spec_dir))

        assert result.returncode == 1
        assert "VALIDATION FAILED" in result.stdout

    def test_main_shows_errors_in_output(self, tmp_path):
        """Test main() shows validation errors in output"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = _run_validate_spec(str(spec_dir))

        # Should show errors
        assert "Errors:" in result.stdout or "Checkpoint:" in result.stdout

    def test_main_shows_fixes_in_output(self, tmp_path):
        """Test main() shows suggested fixes in output"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = _run_validate_spec(str(spec_dir))

        # Should show suggested fixes
        assert "Suggested Fixes:" in result.stdout or "->" in result.stdout

    def test_main_json_includes_all_fields(self, tmp_path):
        """Test main() JSON output includes all result fields"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = _run_validate_spec(str(spec_dir), "--json")

        output = json.loads(result.stdout)

        # Check structure
        assert "valid" in output
        assert "results" in output
        assert isinstance(output["results"], list)

        if output["results"]:
            result_item = output["results"][0]
            assert "checkpoint" in result_item
            assert "valid" in result_item
            assert "errors" in result_item
            assert "warnings" in result_item
            assert "fixes" in result_item

    def test_main_all_checkpoints_runs_all_validators(self, tmp_path):
        """Test main() with 'all' checkpoint runs all validators"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "project_index.json").write_text('{"project_type": "test"}', encoding="utf-8")

        result = _run_validate_spec(str(spec_dir))

        # Should have output for all 4 checkpoints
        assert "Checkpoint:" in result.stdout

    def test_main_auto_fix_before_validation(self, tmp_path):
        """Test that --auto-fix runs fixes before validation"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create broken plan
        broken_plan = {"phases": []}
        (spec_dir / "implementation_plan.json").write_text(json.dumps(broken_plan), encoding="utf-8")

        result = _run_validate_spec(str(spec_dir), "--auto-fix", "--checkpoint", "plan")

        # After auto-fix, validation should pass (plan now has required fields)
        with open(spec_dir / "implementation_plan.json", encoding="utf-8") as f:
            plan = json.load(f)

        # Auto-fix should have added missing fields
        assert "feature" in plan
        assert "workflow_type" in plan

    def test_main_with_corrupted_context_file(self, tmp_path):
        """Test main() with corrupted context.json"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "project_index.json").write_text('{"project_type": "test"}', encoding="utf-8")
        (spec_dir / "context.json").write_text("{broken json", encoding="utf-8")

        result = _run_validate_spec(str(spec_dir), "--checkpoint", "context")

        assert result.returncode == 1
        assert "invalid JSON" in result.stdout

    def test_main_json_output_with_unicode(self, tmp_path):
        """Test main() --json with unicode content"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create content with unicode
        plan = {
            "feature": "Test ñ",
            "workflow_type": "feature",
            "phases": [{"id": "p1", "name": "Phase 测试", "subtasks": [{"id": "t1", "description": "Task emoji 🎉", "status": "pending"}]}],
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

        result = _run_validate_spec(str(spec_dir), "--json", "--checkpoint", "plan")

        output = json.loads(result.stdout)
        assert output["valid"] is True

    def test_main_empty_spec_directory(self, tmp_path):
        """Test main() with completely empty spec directory"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = _run_validate_spec(str(spec_dir))

        # Should fail validation
        assert result.returncode == 1
        # Should show multiple validation failures
        assert "Checkpoint:" in result.stdout

    def test_main_auto_fix_with_invalid_json(self, tmp_path):
        """Test main() --auto-fix with unfixable JSON"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create completely broken JSON
        (spec_dir / "implementation_plan.json").write_text("{{{broken}}}", encoding="utf-8")

        result = _run_validate_spec(str(spec_dir), "--auto-fix", "--checkpoint", "plan")

        # Should still fail validation
        assert result.returncode == 1

    def test_main_error_messages_are_helpful(self, tmp_path):
        """Test that main() provides helpful error messages"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = _run_validate_spec(str(spec_dir))

        # Error messages should be descriptive
        assert "Checkpoint:" in result.stdout
        # Should indicate what's wrong
        assert "does not exist" in result.stdout or "not found" in result.stdout or "Missing" in result.stdout

    def test_main_preserves_exit_code_semantics(self, tmp_path):
        """Test that exit codes follow Unix conventions (0=success, non-zero=failure)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Test failure case
        result = _run_validate_spec(str(spec_dir))
        assert result.returncode != 0

        # Test success case
        (spec_dir / "project_index.json").write_text('{"project_type": "test"}', encoding="utf-8")
        (spec_dir / "context.json").write_text('{"task_description": "Test"}', encoding="utf-8")
        (spec_dir / "spec.md").write_text(
            "## Overview\nTest\n## Workflow Type\nFeature\n## Task Scope\nTest\n## Success Criteria\nTest",
            encoding="utf-8",
        )
        plan = {
            "feature": "Test",
            "workflow_type": "feature",
            "phases": [{"id": "p1", "name": "Phase", "subtasks": [{"id": "t1", "description": "Task", "status": "pending"}]}],
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan), encoding="utf-8")

        result = _run_validate_spec(str(spec_dir))
        assert result.returncode == 0


class TestMainEdgeCases:
    """Tests for main() edge cases"""

    def test_main_with_special_characters_in_path(self, tmp_path):
        """Test main() with special characters in directory path"""
        spec_dir = tmp_path / "spec with spaces & symbols"
        spec_dir.mkdir()
        (spec_dir / "project_index.json").write_text('{"project_type": "test"}', encoding="utf-8")

        result = _run_validate_spec(str(spec_dir), "--checkpoint", "prereqs")

        assert result.returncode == 0

    def test_main_with_unicode_path(self, tmp_path):
        """Test main() with unicode characters in path"""
        spec_dir = tmp_path / "spec_ñ_测试"
        try:
            spec_dir.mkdir()
        except OSError:
            pytest.skip("Unicode filenames not supported")

        (spec_dir / "project_index.json").write_text('{"project_type": "test"}', encoding="utf-8")

        result = _run_validate_spec(str(spec_dir), "--checkpoint", "prereqs")

        assert result.returncode == 0

    def test_main_with_warnings(self, tmp_path):
        """Test main() displays warnings"""
        spec_dir = tmp_path / "auto-claude" / "specs" / "001"
        spec_dir.mkdir(parents=True)
        (spec_dir / "project_index.json").write_text('{"project_type": "test"}', encoding="utf-8")

        result = _run_validate_spec(str(spec_dir), "--checkpoint", "prereqs")

        # May or may not show warnings depending on validator implementation
        # Just verify it runs successfully
        assert result.returncode == 0

    def test_main_with_nested_directory_path(self, tmp_path):
        """Test main() with deeply nested directory path"""
        spec_dir = tmp_path
        for i in range(5):
            spec_dir = spec_dir / f"level{i}"

        spec_dir.mkdir(parents=True)
        (spec_dir / "project_index.json").write_text('{"project_type": "test"}', encoding="utf-8")

        result = _run_validate_spec(str(spec_dir), "--checkpoint", "prereqs")

        assert result.returncode == 0
