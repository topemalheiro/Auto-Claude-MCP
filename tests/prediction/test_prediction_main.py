"""
Tests for prediction.main module (CLI entry point).
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


class TestPredictionMain:
    """Tests for prediction main CLI function."""

    @patch("prediction.main.generate_subtask_checklist")
    def test_main_no_arguments(self, mock_generate, capsys):
        """Test main with no arguments shows usage."""
        # Import at function level to avoid module-level sys.argv access
        import prediction.main
        main = prediction.main.main

        with patch.object(sys, "argv", ["prediction.py"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    @patch("prediction.main.generate_subtask_checklist")
    def test_main_with_demo_flag(self, mock_generate, capsys):
        """Test main with --demo flag."""
        import prediction.main
        main = prediction.main.main

        mock_generate.return_value = "# Demo Checklist\n\n- Item 1\n- Item 2"

        with patch.object(sys, "argv", ["prediction.py", "/tmp/spec", "--demo"]):
            main()

        captured = capsys.readouterr()
        assert len(captured.out) > 0
        assert "Demo Checklist" in captured.out
        mock_generate.assert_called_once()

    @patch("prediction.main.generate_subtask_checklist")
    def test_main_with_spec_dir(self, mock_generate, tmp_path, capsys):
        """Test main with valid spec directory."""
        import prediction.main
        main = prediction.main.main

        plan_file = tmp_path / "implementation_plan.json"
        plan_data = {
            "phases": [
                {
                    "subtasks": [
                        {
                            "id": "task-001",
                            "status": "pending",
                            "description": "Test task",
                        }
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

        mock_generate.return_value = "# Checklist\n- Item 1\n- Item 2"

        with patch.object(sys, "argv", ["prediction.py", str(tmp_path)]):
            main()

        captured = capsys.readouterr()
        assert "Checklist" in captured.out

    @patch("prediction.main.generate_subtask_checklist")
    def test_main_no_implementation_plan(self, mock_generate, tmp_path, capsys):
        """Test main when implementation_plan.json doesn't exist."""
        import prediction.main
        main = prediction.main.main

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        with patch.object(sys, "argv", ["prediction.py", str(spec_dir)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error:" in captured.out or "implementation_plan.json" in captured.out

    @patch("prediction.main.generate_subtask_checklist")
    def test_main_with_completed_plan(self, mock_generate, tmp_path, capsys):
        """Test main when all tasks are completed."""
        import prediction.main
        main = prediction.main.main

        plan_file = tmp_path / "implementation_plan.json"
        plan_data = {
            "phases": [
                {
                    "subtasks": [
                        {
                            "id": "task-001",
                            "status": "completed",
                        }
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

        with patch.object(sys, "argv", ["prediction.py", str(tmp_path)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "No pending" in captured.out

    @patch("prediction.main.generate_subtask_checklist")
    def test_main_uses_first_pending_task(self, mock_generate, tmp_path):
        """Test main finds and uses first pending task."""
        import prediction.main
        main = prediction.main.main

        plan_file = tmp_path / "implementation_plan.json"
        plan_data = {
            "phases": [
                {
                    "subtasks": [
                        {"id": "task-001", "status": "completed"},
                        {"id": "task-002", "status": "pending", "description": "Second task"},
                        {"id": "task-003", "status": "pending", "description": "Third task"},
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

        mock_generate.return_value = "# Generated checklist"

        with patch.object(sys, "argv", ["prediction.py", str(tmp_path)]):
            main()

        mock_generate.assert_called_once()
        subtask = mock_generate.call_args[0][1]
        assert subtask["id"] == "task-002"

    @patch("prediction.main.generate_subtask_checklist")
    def test_main_with_invalid_plan(self, mock_generate, tmp_path):
        """Test main with invalid JSON in plan."""
        import prediction.main
        main = prediction.main.main

        plan_file = tmp_path / "implementation_plan.json"
        plan_file.write_text("invalid json {{", encoding="utf-8")

        with patch.object(sys, "argv", ["prediction.py", str(tmp_path)]):
            # Invalid JSON causes json.JSONDecodeError to be raised
            with pytest.raises(json.JSONDecodeError):
                main()

    @patch("prediction.main.generate_subtask_checklist")
    def test_main_with_empty_plan(self, mock_generate, tmp_path, capsys):
        """Test main with empty implementation plan."""
        import prediction.main
        main = prediction.main.main

        plan_file = tmp_path / "implementation_plan.json"
        plan_data = {"phases": []}
        plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

        with patch.object(sys, "argv", ["prediction.py", str(tmp_path)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "No pending" in captured.out

    @patch("prediction.main.generate_subtask_checklist")
    def test_main_demo_uses_sample_subtask(self, mock_generate, tmp_path):
        """Test that --demo uses the hardcoded sample subtask."""
        import prediction.main
        main = prediction.main.main

        with patch.object(sys, "argv", ["prediction.py", str(tmp_path), "--demo"]):
            main()

        mock_generate.assert_called_once()
        subtask = mock_generate.call_args[0][1]
        assert subtask["id"] == "avatar-endpoint"
        assert "avatar" in subtask["description"].lower()

    @patch("prediction.main.generate_subtask_checklist")
    def test_main_generates_markdown_output(self, mock_generate, tmp_path, capsys):
        """Test that main outputs markdown formatted checklist."""
        import prediction.main
        main = prediction.main.main

        mock_generate.return_value = "# Predictive Bug Prevention Checklist\n\n- Test authentication\n- Test error handling\n"

        plan_file = tmp_path / "implementation_plan.json"
        plan_data = {
            "phases": [
                {
                    "subtasks": [
                        {
                            "id": "task-001",
                            "status": "pending",
                            "description": "Test",
                        }
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

        with patch.object(sys, "argv", ["prediction.py", str(tmp_path)]):
            main()

        captured = capsys.readouterr()
        assert "# Predictive Bug Prevention Checklist" in captured.out
        assert "- Test authentication" in captured.out

    @patch("prediction.main.generate_subtask_checklist")
    def test_main_with_multiple_phases(self, mock_generate, tmp_path):
        """Test main searches through multiple phases for pending task."""
        import prediction.main
        main = prediction.main.main

        plan_file = tmp_path / "implementation_plan.json"
        plan_data = {
            "phases": [
                {
                    "subtasks": [
                        {"id": "task-001", "status": "completed"},
                    ]
                },
                {
                    "subtasks": [
                        {"id": "task-002", "status": "completed"},
                    ]
                },
                {
                    "subtasks": [
                        {"id": "task-003", "status": "pending", "description": "Third phase task"},
                    ]
                },
            ]
        }
        plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

        mock_generate.return_value = "# Checklist"

        with patch.object(sys, "argv", ["prediction.py", str(tmp_path)]):
            main()

        subtask = mock_generate.call_args[0][1]
        assert subtask["id"] == "task-003"

    @patch("prediction.main.generate_subtask_checklist")
    def test_main_handles_missing_phases(self, mock_generate, tmp_path):
        """Test main when plan has no phases key."""
        import prediction.main
        main = prediction.main.main

        plan_file = tmp_path / "implementation_plan.json"
        plan_data = {}
        plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

        with patch.object(sys, "argv", ["prediction.py", str(tmp_path)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("prediction.main.generate_subtask_checklist")
    def test_main_handles_missing_subtasks(self, mock_generate, tmp_path):
        """Test main when phase has no subtasks key."""
        import prediction.main
        main = prediction.main.main

        plan_file = tmp_path / "implementation_plan.json"
        plan_data = {
            "phases": [
                {}
            ]
        }
        plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

        with patch.object(sys, "argv", ["prediction.py", str(tmp_path)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("prediction.main.generate_subtask_checklist")
    def test_main_prints_checklist_to_stdout(self, mock_generate, tmp_path, capsys):
        """Test that checklist is printed to stdout."""
        import prediction.main
        main = prediction.main.main

        mock_generate.return_value = "# Test Checklist\n\n- Item 1\n- Item 2\n"

        plan_file = tmp_path / "implementation_plan.json"
        plan_data = {
            "phases": [
                {
                    "subtasks": [
                        {
                            "id": "task-001",
                            "status": "pending",
                            "description": "Test",
                        }
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

        with patch.object(sys, "argv", ["prediction.py", str(tmp_path)]):
            main()

        captured = capsys.readouterr()
        assert "# Test Checklist" in captured.out
        assert "Item 1" in captured.out

    @patch("prediction.main.generate_subtask_checklist")
    def test_main_passes_spec_dir_correctly(self, mock_generate, tmp_path):
        """Test that spec_dir is passed correctly to generate_subtask_checklist."""
        import prediction.main
        main = prediction.main.main

        spec_dir = tmp_path / "my_spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan_data = {
            "phases": [
                {
                    "subtasks": [
                        {
                            "id": "task-001",
                            "status": "pending",
                            "description": "Test",
                        }
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

        with patch.object(sys, "argv", ["prediction.py", str(spec_dir)]):
            main()

        assert mock_generate.call_args[0][0] == spec_dir

    @patch("prediction.main.generate_subtask_checklist")
    def test_main_usage_message_format(self, mock_generate, capsys):
        """Test that usage message has correct format."""
        import prediction.main
        main = prediction.main.main

        with patch.object(sys, "argv", ["prediction.py"]):
            with pytest.raises(SystemExit):
                main()

        captured = capsys.readouterr()
        assert "python prediction.py" in captured.out
        assert "[--demo]" in captured.out

    @patch("prediction.main.generate_subtask_checklist")
    def test_main_with_special_characters_in_description(self, mock_generate, tmp_path):
        """Test main with special characters in task description."""
        import prediction.main
        main = prediction.main.main

        special_desc = "Task with 'quotes' and \"double quotes\" and <special> & chars"

        plan_file = tmp_path / "implementation_plan.json"
        plan_data = {
            "phases": [
                {
                    "subtasks": [
                        {
                            "id": "task-001",
                            "status": "pending",
                            "description": special_desc,
                        }
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

        mock_generate.return_value = "# Checklist"

        with patch.object(sys, "argv", ["prediction.py", str(tmp_path)]):
            main()

        subtask = mock_generate.call_args[0][1]
        assert subtask["description"] == special_desc

    def test_main_entry_point(self, tmp_path, capsys):
        """Test that main() can be called as entry point."""
        import prediction.main

        plan_file = tmp_path / "implementation_plan.json"
        plan_data = {
            "phases": [
                {
                    "subtasks": [
                        {
                            "id": "task-001",
                            "status": "pending",
                            "description": "Test entry point",
                        }
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

        with patch.object(sys, "argv", ["prediction.py", str(tmp_path)]):
            # This should not raise
            prediction.main.main()

        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_main_function_callable(self):
        """Test that main function is callable and has proper signature."""
        import prediction.main

        # The main function should be callable without arguments
        assert callable(prediction.main.main)
        # It should be a function
        import inspect
        assert inspect.isfunction(prediction.main.main)
