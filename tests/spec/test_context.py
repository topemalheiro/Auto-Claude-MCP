"""Tests for context module (spec/context.py)

NOTE: These tests run actual context discovery scripts - integration tests marked as slow.
Can be excluded with: pytest -m "not slow"
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from subprocess import TimeoutExpired

import pytest

from spec.context import (
    run_context_discovery,
    create_minimal_context,
    get_context_stats,
)

pytestmark = pytest.mark.slow


class TestRunContextDiscovery:
    """Tests for run_context_discovery function"""

    def test_returns_success_when_context_exists(self, tmp_path):
        """Test returns success when context.json already exists"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        context_file.write_text('{"task_description": "test"}', encoding="utf-8")

        success, message = run_context_discovery(
            tmp_path / "project", spec_dir, "Test task", []
        )

        assert success is True
        assert "already exists" in message

    def test_returns_failure_when_script_not_found(self, tmp_path):
        """Test handling missing context.py script"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        success, message = run_context_discovery(
            project_dir, spec_dir, "Test task", []
        )

        assert success is False
        assert "Script not found" in message

    def test_runs_context_script_successfully(self, tmp_path):
        """Test running context.py script successfully"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create the context.py script in auto-claude
        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        script_path = auto_claude / "context.py"
        script_path.write_text("# mock context script", encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Mock subprocess.run to create the context file
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Context discovered"
        mock_result.stderr = ""

        def side_effect(*args, **kwargs):
            # Create context file when subprocess runs
            context_file = spec_dir / "context.json"
            context_file.write_text(
                json.dumps({
                    "task_description": "Test task",
                    "files_to_modify": [],
                    "files_to_reference": [],
                }),
                encoding="utf-8"
            )
            return mock_result

        with patch("subprocess.run", side_effect=side_effect):
            success, message = run_context_discovery(
                project_dir, spec_dir, "Test task", []
            )

        assert success is True
        assert "Created" in message
        assert (spec_dir / "context.json").exists()

    def test_runs_context_script_with_services(self, tmp_path):
        """Test running context.py with services argument"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        script_path = auto_claude / "context.py"
        script_path.write_text("# mock context script", encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_result = MagicMock()
        mock_result.returncode = 0

        captured_args = []

        def side_effect(*args, **kwargs):
            captured_args.append(args[0])  # Capture command
            context_file = spec_dir / "context.json"
            context_file.write_text(
                json.dumps({"task_description": "test"}),
                encoding="utf-8"
            )
            return mock_result

        with patch("subprocess.run", side_effect=side_effect):
            success, message = run_context_discovery(
                project_dir, spec_dir, "Test task", ["frontend", "backend"]
            )

        assert success is True
        # Check that services were passed in the command
        cmd = captured_args[0]
        assert "--services" in cmd
        services_index = cmd.index("--services")
        assert cmd[services_index + 1] == "frontend,backend"

    def test_handles_script_timeout(self, tmp_path):
        """Test handling script timeout"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        script_path = auto_claude / "context.py"
        script_path.write_text("# mock", encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        with patch("subprocess.run", side_effect=TimeoutExpired("cmd", 300)):
            success, message = run_context_discovery(
                project_dir, spec_dir, "Test task", []
            )

        assert success is False
        assert "timed out" in message.lower()

    def test_handles_general_exception(self, tmp_path):
        """Test handling general exceptions"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        script_path = auto_claude / "context.py"
        script_path.write_text("# mock", encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        with patch("subprocess.run", side_effect=RuntimeError("Unexpected error")):
            success, message = run_context_discovery(
                project_dir, spec_dir, "Test task", []
            )

        assert success is False
        assert "Unexpected error" in message

    def test_returns_failure_on_nonzero_exit_code(self, tmp_path):
        """Test handling non-zero exit code from script"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        script_path = auto_claude / "context.py"
        script_path.write_text("# mock", encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Context discovery failed"

        with patch("subprocess.run", return_value=mock_result):
            success, message = run_context_discovery(
                project_dir, spec_dir, "Test task", []
            )

        assert success is False

    def test_fixes_missing_task_description_field(self, tmp_path):
        """Test fixing missing task_description field (lines 69-77)"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        script_path = auto_claude / "context.py"
        script_path.write_text("# mock", encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_result = MagicMock()
        mock_result.returncode = 0

        def side_effect(*args, **kwargs):
            # Create context with "task" field instead of "task_description"
            context_file = spec_dir / "context.json"
            context_file.write_text(
                json.dumps({"task": "Test task", "files": []}),
                encoding="utf-8"
            )
            return mock_result

        with patch("subprocess.run", side_effect=side_effect):
            success, message = run_context_discovery(
                project_dir, spec_dir, "Test task", []
            )

        assert success is True

        # Check that field was renamed
        with open(spec_dir / "context.json", encoding="utf-8") as f:
            data = json.load(f)

        assert "task_description" in data
        assert "task" not in data
        assert data["task_description"] == "Test task"

    def test_adds_task_description_when_missing(self, tmp_path):
        """Test adding task_description when completely missing (line 74)"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        script_path = auto_claude / "context.py"
        script_path.write_text("# mock", encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_result = MagicMock()
        mock_result.returncode = 0

        def side_effect(*args, **kwargs):
            # Create context without task_description or task
            context_file = spec_dir / "context.json"
            context_file.write_text(
                json.dumps({"files": []}),
                encoding="utf-8"
            )
            return mock_result

        with patch("subprocess.run", side_effect=side_effect):
            success, message = run_context_discovery(
                project_dir, spec_dir, "Original task", []
            )

        assert success is True

        with open(spec_dir / "context.json", encoding="utf-8") as f:
            data = json.load(f)

        assert data["task_description"] == "Original task"

    def test_deletes_context_on_invalid_json(self, tmp_path):
        """Test deleting context file when it has invalid JSON (line 79)"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        script_path = auto_claude / "context.py"
        script_path.write_text("# mock", encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_result = MagicMock()
        mock_result.returncode = 0

        def side_effect(*args, **kwargs):
            # Create file with invalid JSON
            context_file = spec_dir / "context.json"
            context_file.write_text("{invalid json}", encoding="utf-8")
            return mock_result

        with patch("subprocess.run", side_effect=side_effect):
            success, message = run_context_discovery(
                project_dir, spec_dir, "Test task", []
            )

        assert success is False
        assert "Invalid" in message
        # File should be deleted
        assert not (spec_dir / "context.json").exists()

    def test_handles_unicode_decode_error(self, tmp_path):
        """Test handling UnicodeDecodeError (line 78)"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        script_path = auto_claude / "context.py"
        script_path.write_text("# mock", encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_result = MagicMock()
        mock_result.returncode = 0

        def side_effect(*args, **kwargs):
            # Create file
            context_file = spec_dir / "context.json"
            context_file.write_text("{}", encoding="utf-8")
            return mock_result

        with patch("subprocess.run", side_effect=side_effect):
            with patch("builtins.open", side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "")):
                success, message = run_context_discovery(
                    project_dir, spec_dir, "Test task", []
                )

        assert success is False

    def test_handles_os_error_on_context_write(self, tmp_path):
        """Test handling OSError during context write (line 78)"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        script_path = auto_claude / "context.py"
        script_path.write_text("# mock", encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_result = MagicMock()
        mock_result.returncode = 0

        def side_effect(*args, **kwargs):
            # Create file
            context_file = spec_dir / "context.json"
            context_file.write_text("{}", encoding="utf-8")
            return mock_result

        with patch("subprocess.run", side_effect=side_effect):
            with patch("builtins.open", side_effect=OSError("Write error")):
                success, message = run_context_discovery(
                    project_dir, spec_dir, "Test task", []
                )

        assert success is False

    def test_task_defaults_to_unknown_when_empty(self, tmp_path):
        """Test task description defaults to "unknown task" when empty (line 45, 74)"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        script_path = auto_claude / "context.py"
        script_path.write_text("# mock", encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_result = MagicMock()
        mock_result.returncode = 0

        def side_effect(*args, **kwargs):
            # Create context without task_description
            context_file = spec_dir / "context.json"
            context_file.write_text(
                json.dumps({"files": []}),
                encoding="utf-8"
            )
            return mock_result

        with patch("subprocess.run", side_effect=side_effect):
            # Pass empty task description
            success, message = run_context_discovery(
                project_dir, spec_dir, "", []
            )

        assert success is True

        with open(spec_dir / "context.json", encoding="utf-8") as f:
            data = json.load(f)

        assert data["task_description"] == "unknown task"


class TestCreateMinimalContext:
    """Tests for create_minimal_context function"""

    def test_creates_minimal_context(self, tmp_path):
        """Test creating minimal context.json"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_context(
            spec_dir, "Test task", ["frontend", "backend"]
        )

        assert result == spec_dir / "context.json"
        assert result.exists()

        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert data["task_description"] == "Test task"
        assert data["scoped_services"] == ["frontend", "backend"]
        assert data["files_to_modify"] == []
        assert data["files_to_reference"] == []

    def test_includes_timestamp(self, tmp_path):
        """Test includes created_at timestamp"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_minimal_context(spec_dir, "Test task", [])

        with open(spec_dir / "context.json", encoding="utf-8") as f:
            data = json.load(f)

        assert "created_at" in data

    def test_handles_empty_services(self, tmp_path):
        """Test with empty services list"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_minimal_context(spec_dir, "Test task", [])

        with open(spec_dir / "context.json", encoding="utf-8") as f:
            data = json.load(f)

        assert data["scoped_services"] == []

    def test_handles_empty_task_description(self, tmp_path):
        """Test with empty task description"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_minimal_context(spec_dir, "", [])

        with open(spec_dir / "context.json", encoding="utf-8") as f:
            data = json.load(f)

        # Empty string defaults to "unknown task" (line 101)
        assert data["task_description"] == "unknown task"

    def test_overwrites_existing_context(self, tmp_path):
        """Test overwriting existing context.json"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        existing = spec_dir / "context.json"
        existing.write_text('{"old": "data"}', encoding="utf-8")

        create_minimal_context(spec_dir, "New task", ["service"])

        with open(existing, encoding="utf-8") as f:
            data = json.load(f)

        assert "old" not in data
        assert data["task_description"] == "New task"


class TestGetContextStats:
    """Tests for get_context_stats function"""

    def test_returns_empty_when_no_context(self, tmp_path):
        """Test returns empty dict when context doesn't exist"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = get_context_stats(spec_dir)

        assert result == {}

    def test_returns_stats_from_valid_context(self, tmp_path):
        """Test returns stats from valid context.json"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        context = {
            "task_description": "Test",
            "files_to_modify": ["file1.py", "file2.py"],
            "files_to_reference": ["file3.py"],
        }

        context_file = spec_dir / "context.json"
        context_file.write_text(json.dumps(context), encoding="utf-8")

        result = get_context_stats(spec_dir)

        assert result["files_to_modify"] == 2
        assert result["files_to_reference"] == 1

    def test_handles_empty_arrays(self, tmp_path):
        """Test with empty file arrays"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        context = {
            "task_description": "Test",
            "files_to_modify": [],
            "files_to_reference": [],
        }

        context_file = spec_dir / "context.json"
        context_file.write_text(json.dumps(context), encoding="utf-8")

        result = get_context_stats(spec_dir)

        assert result["files_to_modify"] == 0
        assert result["files_to_reference"] == 0

    def test_handles_missing_fields(self, tmp_path):
        """Test when fields are missing"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        context = {"task_description": "Test"}

        context_file = spec_dir / "context.json"
        context_file.write_text(json.dumps(context), encoding="utf-8")

        result = get_context_stats(spec_dir)

        assert result["files_to_modify"] == 0
        assert result["files_to_reference"] == 0

    def test_handles_invalid_json(self, tmp_path):
        """Test returns empty dict on invalid JSON"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        context_file = spec_dir / "context.json"
        context_file.write_text("{invalid json", encoding="utf-8")

        result = get_context_stats(spec_dir)

        assert result == {}

    def test_handles_read_error(self, tmp_path):
        """Test returns empty dict on read error"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        context_file = spec_dir / "context.json"
        context_file.write_text('{"test": "data"}', encoding="utf-8")

        with patch("builtins.open", side_effect=OSError("Read error")):
            result = get_context_stats(spec_dir)

        assert result == {}
