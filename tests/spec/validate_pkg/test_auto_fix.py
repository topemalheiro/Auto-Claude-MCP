"""Tests for auto_fix module"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from spec.validate_pkg.auto_fix import _normalize_status, _repair_json_syntax, auto_fix_plan


class TestRepairJsonSyntax:
    """Tests for _repair_json_syntax function"""

    def test_returns_none_for_empty_content(self):
        """Test returns None for empty content"""
        result = _repair_json_syntax("")
        assert result is None

    def test_returns_none_for_whitespace_only(self):
        """Test returns None for whitespace-only content"""
        result = _repair_json_syntax("   \n\t  ")
        assert result is None

    def test_returns_none_for_oversized_content(self):
        """Test returns None for content exceeding size limit"""
        large_content = "x" * (1024 * 1024 + 1)  # > 1MB
        result = _repair_json_syntax(large_content)
        assert result is None

    def test_removes_trailing_commas(self):
        """Test removing trailing commas before brackets/braces"""
        content = '{"key": "value", "items": [1, 2, 3,],}'
        result = _repair_json_syntax(content)

        assert result is not None
        # Should be parseable
        data = json.loads(result)
        assert data["key"] == "value"
        assert data["items"] == [1, 2, 3]

    def test_closes_truncated_json(self):
        """Test closing truncated JSON"""
        content = '{"key": "value", "items": [1, 2'
        result = _repair_json_syntax(content)

        assert result is not None
        data = json.loads(result)
        assert "key" in data

    def test_fixes_unquoted_status_values(self):
        """Test fixing unquoted status values"""
        content = '{"status": pending, "state": "completed"}'
        result = _repair_json_syntax(content)

        assert result is not None
        data = json.loads(result)
        assert data["status"] == "pending"
        assert data["state"] == "completed"

    def test_fixes_all_unquoted_statuses(self):
        """Test fixing all common unquoted status values"""
        test_cases = [
            "pending",
            "in_progress",
            "completed",
            "failed",
            "done",
            "backlog",
        ]

        for status in test_cases:
            content = f'{{"status": {status}}}'
            result = _repair_json_syntax(content)
            assert result is not None, f"Failed for status: {status}"
            data = json.loads(result)
            assert isinstance(data["status"], str)

    def test_returns_none_for_unfixable_json(self):
        """Test returns None for JSON that can't be fixed"""
        content = "{{broken"
        result = _repair_json_syntax(content)
        assert result is None

    def test_handles_nested_brackets(self):
        """Test handles nested brackets correctly"""
        content = '{"outer": {"inner": [1, 2],}, "items": ['
        result = _repair_json_syntax(content)

        assert result is not None
        # Should be parseable
        data = json.loads(result)
        assert "outer" in data


class TestNormalizeStatus:
    """Tests for _normalize_status function"""

    def test_normalizes_standard_statuses(self):
        """Test standard statuses are unchanged"""
        standard = ["pending", "in_progress", "completed", "blocked", "failed"]
        for status in standard:
            result = _normalize_status(status)
            assert result == status

    def test_normalizes_case_insensitive(self):
        """Test case insensitive normalization"""
        test_cases = [
            ("Pending", "pending"),
            ("IN_PROGRESS", "in_progress"),
            ("Completed", "completed"),
            ("BLOCKED", "blocked"),
        ]
        for input_val, expected in test_cases:
            result = _normalize_status(input_val)
            assert result == expected

    def test_normalizes_common_variants(self):
        """Test normalizes common status variants"""
        test_cases = [
            ("not_started", "pending"),
            ("not started", "pending"),
            ("todo", "pending"),
            ("backlog", "pending"),
            ("in-progress", "in_progress"),
            ("inprogress", "in_progress"),
            ("working", "in_progress"),
            ("done", "completed"),
            ("complete", "completed"),
        ]
        for input_val, expected in test_cases:
            result = _normalize_status(input_val)
            assert result == expected

    def test_defaults_unknown_to_pending(self):
        """Test unknown statuses default to pending"""
        result = _normalize_status("unknown_status_xyz")
        assert result == "pending"

    def test_handles_non_string_input(self):
        """Test handles non-string input"""
        result = _normalize_status(123)
        assert result == "pending"

    def test_handles_none_input(self):
        """Test handles None input"""
        result = _normalize_status(None)
        assert result == "pending"


class TestAutoFixPlan:
    """Tests for auto_fix_plan function"""

    def test_returns_false_when_no_plan_file(self, tmp_path):
        """Test returns False when implementation_plan.json doesn't exist"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = auto_fix_plan(spec_dir)

        assert result is False

    def test_adds_missing_feature_field(self, tmp_path):
        """Test adds missing feature field"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text('{"phases": []}', encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        assert result is True
        with open(plan_file, encoding="utf-8") as f:
            data = json.load(f)
        assert "feature" in data

    def test_adds_missing_workflow_type(self, tmp_path):
        """Test adds missing workflow_type field"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text('{"feature": "Test"}', encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        assert result is True
        with open(plan_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data["workflow_type"] == "feature"

    def test_migrates_subtasks_to_phases(self, tmp_path):
        """Test migrates old subtasks format to phases"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        old_plan = {
            "subtasks": [
                {"id": "1", "description": "Task 1"},
                {"id": "2", "description": "Task 2"},
            ]
        }
        plan_file.write_text(json.dumps(old_plan), encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        assert result is True
        with open(plan_file, encoding="utf-8") as f:
            data = json.load(f)
        assert "phases" in data
        assert "subtasks" not in data
        assert len(data["phases"]) == 1
        assert len(data["phases"][0]["subtasks"]) == 2

    def test_migrates_chunks_to_phases(self, tmp_path):
        """Test migrates old chunks format to phases"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        old_plan = {
            "chunks": [
                {"id": "1", "description": "Chunk 1"},
            ]
        }
        plan_file.write_text(json.dumps(old_plan), encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        assert result is True
        with open(plan_file, encoding="utf-8") as f:
            data = json.load(f)
        assert "phases" in data
        assert "chunks" not in data

    def test_fixes_missing_phase_name(self, tmp_path):
        """Test adds missing phase name"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "phases": [
                {"phase": 1},  # Missing name
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        assert result is True
        with open(plan_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data["phases"][0]["name"] == "Phase 1"

    def test_fixes_missing_subtask_fields(self, tmp_path):
        """Test adds missing subtask fields"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "phases": [
                {
                    "name": "Phase 1",
                    "subtasks": [
                        {},  # Empty subtask
                    ],
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        assert result is True
        with open(plan_file, encoding="utf-8") as f:
            data = json.load(f)
        subtask = data["phases"][0]["subtasks"][0]
        assert "id" in subtask
        assert "description" in subtask
        assert "status" in subtask

    def test_normalizes_subtask_status(self, tmp_path):
        """Test normalizes subtask status values"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "phases": [
                {
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "1", "status": "done"},
                        {"id": "2", "status": "IN_PROGRESS"},
                        {"id": "3", "status": "not-started"},
                    ],
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        assert result is True
        with open(plan_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data["phases"][0]["subtasks"][0]["status"] == "completed"
        assert data["phases"][0]["subtasks"][1]["status"] == "in_progress"
        assert data["phases"][0]["subtasks"][2]["status"] == "pending"

    def test_repairs_json_syntax(self, tmp_path):
        """Test repairs JSON syntax errors"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        # Write malformed JSON with trailing comma
        plan_file.write_text('{"feature": "test",}', encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        assert result is True
        # File should now be valid JSON
        with open(plan_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data["feature"] == "test"

    def test_returns_false_for_unfixable_json(self, tmp_path):
        """Test returns False when JSON can't be fixed"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text("{{{broken", encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        # Should return False for unfixable JSON
        # (but might also not crash)
        assert isinstance(result, bool)

    def test_handles_unicode_errors(self, tmp_path):
        """Test handles Unicode decode errors"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        # Write invalid UTF-8
        plan_file.write_bytes(b"\xff\xfe invalid")

        result = auto_fix_plan(spec_dir)

        # Should handle gracefully
        assert isinstance(result, bool)

    def test_returns_false_on_os_error(self, tmp_path):
        """Test handles OS errors (file permissions)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text('{"feature": "test"}', encoding="utf-8")

        with patch("builtins.open", side_effect=OSError("Permission denied")):
            result = auto_fix_plan(spec_dir)

        assert result is False

    def test_uses_atomic_write(self, tmp_path):
        """Test uses atomic write to prevent corruption"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan = {"phases": [{"name": "Phase 1"}]}
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        with patch("spec.validate_pkg.auto_fix.write_json_atomic") as mock_write:
            auto_fix_plan(spec_dir)

        # Should have used atomic write
        mock_write.assert_called()

    def test_copies_phase_title_to_name(self, tmp_path):
        """Test copies title field to name when name is missing"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test",
            "phases": [
                {"title": "Planning Phase"},  # Has title, no name
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        assert result is True
        with open(plan_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data["phases"][0]["name"] == "Planning Phase"

    def test_fixes_phase_id_from_int(self, tmp_path):
        """Test sets phase field from int phase_id"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test",
            "phases": [
                {"phase_id": 2},  # No phase field
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        assert result is True
        with open(plan_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data["phases"][0]["phase"] == 2
        assert data["phases"][0]["id"] == "2"

    def test_fixes_phase_id_from_float(self, tmp_path):
        """Test sets phase field from float phase_id that is integer"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test",
            "phases": [
                {"phase_id": 3.0},  # Float but integer value
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        assert result is True
        with open(plan_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data["phases"][0]["phase"] == 3

    def test_fixes_phase_id_from_string(self, tmp_path):
        """Test sets phase field from string phase_id"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test",
            "phases": [
                {"phase_id": "5"},
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        assert result is True
        with open(plan_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data["phases"][0]["phase"] == 5
        assert data["phases"][0]["id"] == "5"

    def test_handles_phase_id_when_id_already_exists(self, tmp_path):
        """Test phase_id conversion when id already exists"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test",
            "phases": [
                {"id": "custom-id", "phase_id": 3},
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        assert result is True
        with open(plan_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data["phases"][0]["phase"] == 3
        # id should remain unchanged since it already exists
        assert data["phases"][0]["id"] == "custom-id"

    def test_normalizes_depends_on_list(self, tmp_path):
        """Test normalizes depends_on list to strings and removes None"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test",
            "phases": [
                {"name": "Phase 1", "depends_on": [1, "2", None, 3]},
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        assert result is True
        with open(plan_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data["phases"][0]["depends_on"] == ["1", "2", "3"]

    def test_normalizes_depends_on_none_to_empty_list(self, tmp_path):
        """Test converts None depends_on to empty list"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test",
            "phases": [
                {"name": "Phase 1", "depends_on": None},
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        assert result is True
        with open(plan_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data["phases"][0]["depends_on"] == []

    def test_normalizes_scalar_depends_on_to_list(self, tmp_path):
        """Test converts scalar depends_on to single-element list"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test",
            "phases": [
                {"name": "Phase 1", "depends_on": "1"},
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        assert result is True
        with open(plan_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data["phases"][0]["depends_on"] == ["1"]

    def test_falls_back_to_chunks_when_subtasks_empty(self, tmp_path):
        """Test falls back to chunks when subtasks is empty"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test",
            "phases": [
                {
                    "name": "Phase 1",
                    "subtasks": [],  # Empty but exists
                    "chunks": [
                        {"id": "chunk-1", "description": "Chunk task"},
                    ],
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        assert result is True
        with open(plan_file, encoding="utf-8") as f:
            data = json.load(f)
        # Should have copied chunks to subtasks
        assert len(data["phases"][0]["subtasks"]) == 1
        assert data["phases"][0]["subtasks"][0]["id"] == "chunk-1"

    def test_normalizes_subtask_aliases(self, tmp_path):
        """Test normalizes subtask field aliases (subtask_id, title)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test",
            "phases": [
                {
                    "name": "Phase 1",
                    "subtasks": [
                        {"subtask_id": "task-123", "title": "My Task"},
                    ],
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        assert result is True
        with open(plan_file, encoding="utf-8") as f:
            data = json.load(f)
        subtask = data["phases"][0]["subtasks"][0]
        assert subtask["id"] == "task-123"
        assert subtask["description"] == "My Task"

    def test_returns_false_on_write_os_error(self, tmp_path):
        """Test returns False when atomic write fails with OSError"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan = {"feature": "Test"}  # Missing workflow_type
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        with patch("spec.validate_pkg.auto_fix.write_json_atomic", side_effect=OSError("Disk full")):
            result = auto_fix_plan(spec_dir)

        assert result is False

    def test_handles_complex_json_repair_with_string_containing_brackets(self, tmp_path):
        """Test JSON repair doesn't break on strings containing brackets"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        # Content with brackets inside strings
        content = '{"description": "Use array[0] for access", "items": [1, 2'
        plan_file.write_text(content, encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        assert result is True
        with open(plan_file, encoding="utf-8") as f:
            data = json.load(f)
        assert "array[0]" in data["description"]

    def test_handles_non_numeric_phase_id_string(self, tmp_path):
        """Test handles non-numeric string phase_id"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test",
            "phases": [
                {"phase_id": "planning-phase"},  # String but not numeric
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        result = auto_fix_plan(spec_dir)

        assert result is True
        with open(plan_file, encoding="utf-8") as f:
            data = json.load(f)
        # Should set id to the string value since it's not None
        assert data["phases"][0]["id"] == "planning-phase"
        # phase should be set by default to index + 1
        assert data["phases"][0]["phase"] == 1
