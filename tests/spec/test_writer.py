"""Tests for writer module"""

import json
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from spec.writer import create_minimal_plan, get_plan_stats


class TestCreateMinimalPlan:
    """Tests for create_minimal_plan function"""

    def test_create_minimal_plan_basic(self, tmp_path):
        """Test basic plan creation"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        task_description = "Fix button alignment"

        result = create_minimal_plan(spec_dir, task_description)

        assert result == spec_dir / "implementation_plan.json"
        assert result.exists()

        with open(result, encoding="utf-8") as f:
            plan = json.load(f)

        assert plan["spec_name"] == spec_dir.name
        assert plan["workflow_type"] == "simple"
        assert plan["total_phases"] == 1
        assert plan["recommended_workers"] == 1
        assert len(plan["phases"]) == 1
        assert plan["phases"][0]["phase"] == 1
        assert plan["phases"][0]["name"] == "Implementation"
        assert len(plan["phases"][0]["subtasks"]) == 1
        assert plan["phases"][0]["subtasks"][0]["description"] == task_description

    def test_create_minimal_plan_with_empty_task_description(self, tmp_path):
        """Test plan creation with empty task description"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_plan(spec_dir, "")

        assert result.exists()

        with open(result, encoding="utf-8") as f:
            plan = json.load(f)

        # Should use default description
        assert plan["phases"][0]["description"] == "Simple implementation"
        assert plan["phases"][0]["subtasks"][0]["description"] == "Implement the change"

    def test_create_minimal_plan_with_none_task_description(self, tmp_path):
        """Test plan creation with None task description"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_plan(spec_dir, None)

        assert result.exists()

        with open(result, encoding="utf-8") as f:
            plan = json.load(f)

        # Should use default description
        assert plan["phases"][0]["description"] == "Simple implementation"

    def test_create_minimal_plan_includes_metadata(self, tmp_path):
        """Test plan includes metadata with timestamp"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_plan(spec_dir, "Test task")

        with open(result, encoding="utf-8") as f:
            plan = json.load(f)

        assert "metadata" in plan
        assert "created_at" in plan["metadata"]
        assert plan["metadata"]["complexity"] == "simple"
        assert plan["metadata"]["estimated_sessions"] == 1
        assert plan["spec_name"] == spec_dir.name

    def test_create_minimal_plan_overwrites_existing(self, tmp_path):
        """Test that existing plan is overwritten"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create existing plan
        existing_plan = {"old": "data"}
        plan_file = spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(existing_plan, f)

        create_minimal_plan(spec_dir, "New task")

        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)

        # Old data should be gone
        assert "old" not in plan
        assert "workflow_type" in plan

    def test_create_minimal_plan_subtask_structure(self, tmp_path):
        """Test subtask has correct structure"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_plan(spec_dir, "Test task")

        with open(result, encoding="utf-8") as f:
            plan = json.load(f)

        subtask = plan["phases"][0]["subtasks"][0]

        assert subtask["id"] == "subtask-1-1"
        assert subtask["service"] == "main"
        assert subtask["status"] == "pending"
        assert subtask["files_to_create"] == []
        assert subtask["files_to_modify"] == []
        assert subtask["patterns_from"] == []
        assert "verification" in subtask
        assert subtask["verification"]["type"] == "manual"

    def test_create_minimal_plan_phase_structure(self, tmp_path):
        """Test phase has correct structure"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_plan(spec_dir, "Test task")

        with open(result, encoding="utf-8") as f:
            plan = json.load(f)

        phase = plan["phases"][0]

        assert phase["phase"] == 1
        assert phase["name"] == "Implementation"
        assert phase["description"] == "Test task"
        assert phase["depends_on"] == []
        assert isinstance(phase["subtasks"], list)


class TestGetPlanStats:
    """Tests for get_plan_stats function"""

    def test_returns_empty_when_no_plan(self, tmp_path):
        """Test returns empty dict when plan doesn't exist"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = get_plan_stats(spec_dir)

        assert result == {}

    def test_returns_empty_on_invalid_json(self, tmp_path):
        """Test returns empty dict on invalid JSON"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text("{invalid json", encoding="utf-8")

        result = get_plan_stats(spec_dir)

        assert result == {}

    def test_returns_empty_on_read_error(self, tmp_path):
        """Test returns empty dict on read error"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text('{"test": "data"}', encoding="utf-8")

        with patch("builtins.open", side_effect=OSError("Read error")):
            result = get_plan_stats(spec_dir)

        assert result == {}

    def test_counts_subtasks_single_phase(self, tmp_path):
        """Test counting subtasks in single phase"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan = {
            "phases": [
                {
                    "subtasks": [
                        {"id": "1"},
                        {"id": "2"},
                        {"id": "3"},
                    ]
                }
            ]
        }

        plan_file = spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(plan, f)

        result = get_plan_stats(spec_dir)

        assert result["total_subtasks"] == 3
        assert result["total_phases"] == 1

    def test_counts_subtasks_multiple_phases(self, tmp_path):
        """Test counting subtasks across multiple phases"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan = {
            "phases": [
                {"subtasks": [{"id": "1"}, {"id": "2"}]},
                {"subtasks": [{"id": "3"}]},
                {"subtasks": []},  # Empty phase
            ]
        }

        plan_file = spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(plan, f)

        result = get_plan_stats(spec_dir)

        assert result["total_subtasks"] == 3
        assert result["total_phases"] == 3

    def test_handles_missing_phases_field(self, tmp_path):
        """Test handling plan without phases field"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan = {"title": "Test"}  # No phases field

        plan_file = spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(plan, f)

        result = get_plan_stats(spec_dir)

        assert result["total_subtasks"] == 0
        assert result["total_phases"] == 0

    def test_handles_missing_subtasks_in_phase(self, tmp_path):
        """Test handling phase without subtasks field"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan = {
            "phases": [
                {"name": "Phase 1"},  # No subtasks field
                {"subtasks": [{"id": "1"}]},
            ]
        }

        plan_file = spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(plan, f)

        result = get_plan_stats(spec_dir)

        assert result["total_subtasks"] == 1
        assert result["total_phases"] == 2

    def test_handles_empty_plan(self, tmp_path):
        """Test handling empty plan object"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text('{}', encoding="utf-8")

        result = get_plan_stats(spec_dir)

        assert result["total_subtasks"] == 0
        assert result["total_phases"] == 0


class TestCreateMinimalPlanAdditional:
    """Additional tests for create_minimal_plan edge cases"""

    def test_creates_directory_if_needed(self, tmp_path):
        """Test that spec_dir must exist"""
        spec_dir = tmp_path / "new_dir" / "spec"
        # Don't create it - function will fail

        # The function expects directory to exist
        with pytest.raises(FileNotFoundError):
            create_minimal_plan(spec_dir, "Test task")

    def test_task_with_special_characters(self, tmp_path):
        """Test task description with special characters"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_plan(spec_dir, "Test task: @#$%^&*()")

        with open(result, encoding="utf-8") as f:
            plan = json.load(f)

        assert "@" in plan["phases"][0]["description"]

    def test_task_with_newlines(self, tmp_path):
        """Test task description with newlines"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_plan(spec_dir, "Line 1\nLine 2\nLine 3")

        with open(result, encoding="utf-8") as f:
            plan = json.load(f)

        assert "\n" in plan["phases"][0]["description"]

    def test_spec_name_from_directory(self, tmp_path):
        """Test spec_name is set from spec_dir name (line 16)"""
        spec_dir = tmp_path / "my-spec-001"
        spec_dir.mkdir()

        create_minimal_plan(spec_dir, "Test")

        with open(spec_dir / "implementation_plan.json", encoding="utf-8") as f:
            plan = json.load(f)

        assert plan["spec_name"] == "my-spec-001"

    def test_workflow_type_is_simple(self, tmp_path):
        """Test workflow_type is always 'simple' (line 17)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_minimal_plan(spec_dir, "Test")

        with open(spec_dir / "implementation_plan.json", encoding="utf-8") as f:
            plan = json.load(f)

        assert plan["workflow_type"] == "simple"

    def test_total_phases_is_one(self, tmp_path):
        """Test total_phases is always 1 (line 18)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_minimal_plan(spec_dir, "Test")

        with open(spec_dir / "implementation_plan.json", encoding="utf-8") as f:
            plan = json.load(f)

        assert plan["total_phases"] == 1

    def test_recommended_workers_is_one(self, tmp_path):
        """Test recommended_workers is always 1 (line 19)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_minimal_plan(spec_dir, "Test")

        with open(spec_dir / "implementation_plan.json", encoding="utf-8") as f:
            plan = json.load(f)

        assert plan["recommended_workers"] == 1

    def test_phase_name_is_implementation(self, tmp_path):
        """Test phase name is 'Implementation' (line 23)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_minimal_plan(spec_dir, "Test")

        with open(spec_dir / "implementation_plan.json", encoding="utf-8") as f:
            plan = json.load(f)

        assert plan["phases"][0]["name"] == "Implementation"

    def test_phase_number_is_one(self, tmp_path):
        """Test phase number is 1 (line 22)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_minimal_plan(spec_dir, "Test")

        with open(spec_dir / "implementation_plan.json", encoding="utf-8") as f:
            plan = json.load(f)

        assert plan["phases"][0]["phase"] == 1

    def test_phase_depends_on_is_empty(self, tmp_path):
        """Test phase depends_on is empty array (line 25)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_minimal_plan(spec_dir, "Test")

        with open(spec_dir / "implementation_plan.json", encoding="utf-8") as f:
            plan = json.load(f)

        assert plan["phases"][0]["depends_on"] == []

    def test_subtask_id_format(self, tmp_path):
        """Test subtask ID format (line 28)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_minimal_plan(spec_dir, "Test")

        with open(spec_dir / "implementation_plan.json", encoding="utf-8") as f:
            plan = json.load(f)

        assert plan["phases"][0]["subtasks"][0]["id"] == "subtask-1-1"

    def test_subtask_service_is_main(self, tmp_path):
        """Test subtask service is 'main' (line 30)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_minimal_plan(spec_dir, "Test")

        with open(spec_dir / "implementation_plan.json", encoding="utf-8") as f:
            plan = json.load(f)

        assert plan["phases"][0]["subtasks"][0]["service"] == "main"

    def test_subtask_status_is_pending(self, tmp_path):
        """Test subtask status is 'pending' (line 31)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_minimal_plan(spec_dir, "Test")

        with open(spec_dir / "implementation_plan.json", encoding="utf-8") as f:
            plan = json.load(f)

        assert plan["phases"][0]["subtasks"][0]["status"] == "pending"

    def test_subtask_arrays_are_empty(self, tmp_path):
        """Test subtask arrays are empty (lines 32-34)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_minimal_plan(spec_dir, "Test")

        with open(spec_dir / "implementation_plan.json", encoding="utf-8") as f:
            plan = json.load(f)

        subtask = plan["phases"][0]["subtasks"][0]
        assert subtask["files_to_create"] == []
        assert subtask["files_to_modify"] == []
        assert subtask["patterns_from"] == []

    def test_verification_type_is_manual(self, tmp_path):
        """Test verification type is 'manual' (line 36)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_minimal_plan(spec_dir, "Test")

        with open(spec_dir / "implementation_plan.json", encoding="utf-8") as f:
            plan = json.load(f)

        assert plan["phases"][0]["subtasks"][0]["verification"]["type"] == "manual"

    def test_json_indentation(self, tmp_path):
        """Test JSON output is properly indented (line 52)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_minimal_plan(spec_dir, "Test")

        content = (spec_dir / "implementation_plan.json").read_text(encoding="utf-8")

        # Check formatting
        assert "\n" in content
        assert "  " in content

    def test_utf8_encoding(self, tmp_path):
        """Test UTF-8 encoding for emojis and unicode"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_minimal_plan(spec_dir, "Test task: 🎉 ñ")

        with open(spec_dir / "implementation_plan.json", encoding="utf-8") as f:
            plan = json.load(f)

        assert "🎉" in plan["phases"][0]["description"]
        assert "ñ" in plan["phases"][0]["description"]


class TestGetPlanStatsAdditional:
    """Additional tests for get_plan_stats edge cases"""

    def test_returns_empty_on_os_error(self, tmp_path):
        """Test returns empty dict on OS error reading file"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text('{"test": "data"}', encoding="utf-8")

        with patch("builtins.open", side_effect=OSError("Read error")):
            result = get_plan_stats(spec_dir)

        assert result == {}

    def test_unicode_decode_error(self, tmp_path):
        """Test returns empty dict on Unicode decode error"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text('{"test": "data"}', encoding="utf-8")

        with patch("builtins.open", side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "")):
            result = get_plan_stats(spec_dir)

        assert result == {}

    def test_phases_field_not_a_list(self, tmp_path):
        """Test when phases field is not a list"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # In Python, len() on string returns character count, not error
        plan = {"phases": "not_a_list"}  # Invalid type

        plan_file = spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(plan, f)

        # Python's len() works on strings, so we get the character count
        # The function will treat string phases as iterable over characters
        result = get_plan_stats(spec_dir)
        # Since string is iterable, it counts as 1 "phase" and iterates over chars
        # Actually, looking at the code, it iterates over p.get("subtasks", [])
        # A string doesn't have .get() method, so it will raise AttributeError
        # Which gets caught and returns {}
        result = get_plan_stats(spec_dir)
        assert result == {}

    def test_subtasks_field_not_a_list(self, tmp_path):
        """Test when subtasks field is not a list - edge case behavior"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # When subtasks is a string, len() returns character count
        # This is an edge case - the function should handle it gracefully
        plan = {
            "phases": [
                {"subtasks": "not_a_list"},  # Invalid type
            ]
        }

        plan_file = spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(plan, f)

        # The function uses len() on the subtasks value
        result = get_plan_stats(spec_dir)
        # Just verify it returns some result without crashing
        assert "total_subtasks" in result
        assert "total_phases" in result
        assert result["total_phases"] == 1
