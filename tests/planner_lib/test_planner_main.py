"""Tests for planner_lib.main module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from implementation_plan import ImplementationPlan
from planner_lib.context import ContextLoader
from planner_lib.main import ImplementationPlanner, generate_implementation_plan


class TestImplementationPlanner:
    """Tests for ImplementationPlanner class."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a mock spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    def test_init(self, mock_spec_dir):
        """Test ImplementationPlanner initialization."""
        planner = ImplementationPlanner(mock_spec_dir)
        assert planner.spec_dir == mock_spec_dir
        assert planner.context is None

    def test_init_with_path_string(self, tmp_path):
        """Test initialization with string path."""
        spec_dir = str(tmp_path / "specs" / "001-test")
        Path(spec_dir).mkdir(parents=True)
        planner = ImplementationPlanner(spec_dir)
        assert isinstance(planner.spec_dir, Path)

    def test_load_context_calls_context_loader(self, mock_spec_dir):
        """Test that load_context calls ContextLoader."""
        planner = ImplementationPlanner(mock_spec_dir)

        mock_context = MagicMock()
        with patch.object(
            ContextLoader, "load_context", return_value=mock_context
        ) as mock_load:
            result = planner.load_context()
            assert result == mock_context
            assert planner.context == mock_context
            mock_load.assert_called_once()

    def test_load_context_stores_result(self, mock_spec_dir):
        """Test that load_context stores context in instance."""
        planner = ImplementationPlanner(mock_spec_dir)
        mock_context = {"test": "context"}

        with patch.object(ContextLoader, "load_context", return_value=mock_context):
            planner.load_context()
            assert planner.context == mock_context

    def test_generate_plan_loads_context_if_needed(self, mock_spec_dir):
        """Test that generate_plan loads context if not already loaded."""
        planner = ImplementationPlanner(mock_spec_dir)
        mock_plan = MagicMock()
        mock_context = MagicMock()

        with patch.object(
            ContextLoader, "load_context", return_value=mock_context
        ) as mock_load:
            with patch(
                "planner_lib.main.get_plan_generator", return_value=MagicMock(generate=MagicMock(return_value=mock_plan))
            ) as mock_get_gen:
                result = planner.generate_plan()
                assert result == mock_plan
                mock_load.assert_called_once()
                mock_get_gen.assert_called_once_with(mock_context, mock_spec_dir)

    def test_generate_plan_uses_existing_context(self, mock_spec_dir):
        """Test that generate_plan uses existing context if available."""
        planner = ImplementationPlanner(mock_spec_dir)
        mock_plan = MagicMock()
        mock_context = MagicMock()
        planner.context = mock_context

        with patch.object(ContextLoader, "load_context") as mock_load:
            with patch(
                "planner_lib.main.get_plan_generator", return_value=MagicMock(generate=MagicMock(return_value=mock_plan))
            ) as mock_get_gen:
                result = planner.generate_plan()
                assert result == mock_plan
                mock_load.assert_not_called()
                mock_get_gen.assert_called_once_with(mock_context, mock_spec_dir)

    def test_save_plan(self, mock_spec_dir, tmp_path):
        """Test saving plan to spec directory."""
        planner = ImplementationPlanner(mock_spec_dir)
        mock_plan = MagicMock()
        output_file = mock_spec_dir / "implementation_plan.json"

        with patch.object(mock_plan, "save") as mock_save:
            result = planner.save_plan(mock_plan)
            assert result == output_file
            mock_save.assert_called_once_with(output_file)

    def test_save_plan_returns_path(self, mock_spec_dir):
        """Test that save_plan returns the output path."""
        planner = ImplementationPlanner(mock_spec_dir)
        mock_plan = MagicMock()
        expected_path = mock_spec_dir / "implementation_plan.json"

        with patch.object(mock_plan, "save"):
            result = planner.save_plan(mock_plan)
            assert result == expected_path


class TestGenerateImplementationPlan:
    """Tests for generate_implementation_plan function."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a mock spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    def test_generate_plan_full_workflow(self, mock_spec_dir):
        """Test full workflow of generate_implementation_plan."""
        mock_plan = MagicMock(to_dict=MagicMock(return_value={"plan": "data"}))
        mock_context = MagicMock()

        with patch.object(
            ContextLoader, "load_context", return_value=mock_context
        ):
            with patch(
                "planner_lib.main.get_plan_generator",
                return_value=MagicMock(generate=MagicMock(return_value=mock_plan))
            ) as mock_get_gen:
                result = generate_implementation_plan(mock_spec_dir)
                assert result == mock_plan
                mock_get_gen.assert_called_once()

    def test_generate_plan_saves_to_file(self, mock_spec_dir):
        """Test that generate_implementation_plan saves the plan."""
        mock_plan = MagicMock()
        mock_context = MagicMock()
        expected_path = mock_spec_dir / "implementation_plan.json"

        with patch.object(
            ContextLoader, "load_context", return_value=mock_context
        ):
            with patch(
                "planner_lib.main.get_plan_generator",
                return_value=MagicMock(generate=MagicMock(return_value=mock_plan))
            ):
                with patch.object(mock_plan, "save") as mock_save:
                    result = generate_implementation_plan(mock_spec_dir)
                    mock_save.assert_called_once_with(expected_path)

    def test_generate_plan_with_string_path(self, tmp_path):
        """Test generate_implementation_plan with string path."""
        spec_dir = str(tmp_path / "specs" / "001-test")
        Path(spec_dir).mkdir(parents=True)
        mock_plan = MagicMock()
        mock_context = MagicMock()

        with patch.object(
            ContextLoader, "load_context", return_value=mock_context
        ):
            with patch(
                "planner_lib.main.get_plan_generator",
                return_value=MagicMock(generate=MagicMock(return_value=mock_plan))
            ):
                result = generate_implementation_plan(spec_dir)
                assert result == mock_plan


class TestMainCli:
    """Tests for main() CLI function."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a mock spec directory with context files."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        # Create minimal context files
        (spec_dir / "spec.md").write_text("# Test Spec")
        (spec_dir / "project_index.json").write_text("{}")
        (spec_dir / "context.json").write_text("{}")
        return spec_dir

    def test_main_with_spec_dir(self, mock_spec_dir, capsys):
        """Test main() with spec-dir argument."""
        mock_plan = MagicMock()
        mock_plan.to_dict.return_value = {"phases": []}
        mock_plan.get_status_summary.return_value = "Plan summary"

        with patch(
            "planner_lib.main.ImplementationPlanner"
        ) as MockPlanner:
            mock_instance = MagicMock()
            mock_instance.load_context.return_value = MagicMock()
            mock_instance.generate_plan.return_value = mock_plan
            MockPlanner.return_value = mock_instance

            with patch("sys.argv", ["planner", "--spec-dir", str(mock_spec_dir)]):
                try:
                    from planner_lib.main import main

                    main()
                except SystemExit:
                    pass

        captured = capsys.readouterr()
        assert "Plan saved" in captured.out or "Plan" in captured.out

    def test_main_dry_run(self, mock_spec_dir, capsys):
        """Test main() with --dry-run flag."""
        mock_plan = MagicMock()
        mock_plan.to_dict.return_value = {"test": "plan"}
        mock_plan.get_status_summary.return_value = "Summary"

        with patch(
            "planner_lib.main.ImplementationPlanner"
        ) as MockPlanner:
            mock_instance = MagicMock()
            mock_instance.load_context.return_value = MagicMock()
            mock_instance.generate_plan.return_value = mock_plan
            MockPlanner.return_value = mock_instance

            with patch(
                "sys.argv", ["planner", "--spec-dir", str(mock_spec_dir), "--dry-run"]
            ):
                try:
                    from planner_lib.main import main

                    main()
                except SystemExit:
                    pass

        captured = capsys.readouterr()
        # Should print JSON and summary, not save
        assert "test" in captured.out or "Summary" in captured.out

    def test_main_with_custom_output(self, tmp_path, mock_spec_dir):
        """Test main() with --output argument."""
        output_path = tmp_path / "custom_plan.json"
        mock_plan = MagicMock()
        mock_plan.get_status_summary.return_value = "Summary"

        with patch(
            "planner_lib.main.ImplementationPlanner"
        ) as MockPlanner:
            mock_instance = MagicMock()
            mock_instance.load_context.return_value = MagicMock()
            mock_instance.generate_plan.return_value = mock_plan
            MockPlanner.return_value = mock_instance

            with patch.object(mock_plan, "save") as mock_save:
                with patch(
                    "sys.argv",
                    [
                        "planner",
                        "--spec-dir",
                        str(mock_spec_dir),
                        "--output",
                        str(output_path),
                    ],
                ):
                    try:
                        from planner_lib.main import main

                        main()
                    except SystemExit:
                        pass

                mock_save.assert_called_once()
                call_args = mock_save.call_args[0]
                assert call_args[0] == output_path


class TestImplementationPlannerEdgeCases:
    """Edge case tests for ImplementationPlanner."""

    def test_generate_plan_without_loading_context_first(self, tmp_path):
        """Test generate_plan when context wasn't explicitly loaded."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        planner = ImplementationPlanner(spec_dir)
        mock_plan = MagicMock()
        mock_context = MagicMock()

        with patch.object(
            ContextLoader, "load_context", return_value=mock_context
        ):
            with patch(
                "planner_lib.main.get_plan_generator",
                return_value=MagicMock(generate=MagicMock(return_value=mock_plan))
            ):
                # Should auto-load context
                result = planner.generate_plan()
                assert result == mock_plan

    def test_context_loader_exception_propagates(self, tmp_path):
        """Test that exceptions from ContextLoader propagate."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        planner = ImplementationPlanner(spec_dir)

        with patch.object(
            ContextLoader, "load_context", side_effect=FileNotFoundError("Not found")
        ):
            with pytest.raises(FileNotFoundError):
                planner.load_context()

    def test_generator_exception_propagates(self, tmp_path):
        """Test that exceptions from generator propagate."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        planner = ImplementationPlanner(spec_dir)
        planner.context = MagicMock()

        with patch(
            "planner_lib.main.get_plan_generator",
            side_effect=ValueError("Invalid context"),
        ):
            with pytest.raises(ValueError):
                planner.generate_plan()

    def test_save_plan_handles_existing_file(self, mock_spec_dir):
        """Test that save_plan overwrites existing file."""
        planner = ImplementationPlanner(mock_spec_dir)
        mock_plan = MagicMock()
        output_file = mock_spec_dir / "implementation_plan.json"

        # Create existing file
        output_file.write_text('{"old": "data"}')

        with patch.object(mock_plan, "save") as mock_save:
            planner.save_plan(mock_plan)
            mock_save.assert_called_once_with(output_file)
