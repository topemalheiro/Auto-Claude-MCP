"""Tests for spec_runner"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from runners.spec_runner import main


def test_main_with_task():
    """Test main with task argument"""
    with patch("sys.argv", ["spec_runner.py", "--task", "Test task", "--no-build"]), \
         patch("runners.spec_runner.SpecOrchestrator") as mock_orchestrator_class, \
         patch("runners.spec_runner.ReviewState") as mock_review_state, \
         patch("runners.spec_runner.resolve_model_id") as mock_resolve_model, \
         patch("runners.spec_runner.asyncio.run") as mock_asyncio_run:

        # Set up mocks
        mock_asyncio_run.return_value = True
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.spec_dir = Path("/fake/spec/dir")
        mock_orchestrator.project_dir = Path("/fake/project")

        mock_review = MagicMock()
        mock_review.is_approved.return_value = False
        mock_review_state.load.return_value = mock_review

        mock_resolve_model.return_value = "claude-sonnet-4-20250514"

        # Act - should not raise SystemExit because no-build flag prevents build
        with pytest.raises(SystemExit) as exc_info:
            main()

        # Assert - exited with code 0 because no-build flag and success
        assert exc_info.value.code == 0


def test_main_with_no_build():
    """Test main with --no-build flag (successful case)"""
    with patch("sys.argv", ["spec_runner.py", "--task", "Test task", "--no-build"]), \
         patch("runners.spec_runner.SpecOrchestrator") as mock_orchestrator_class, \
         patch("runners.spec_runner.resolve_model_id") as mock_resolve_model, \
         patch("runners.spec_runner.asyncio.run") as mock_asyncio_run:

        # Set up mocks - asyncio.run needs to return the result of the coroutine
        mock_asyncio_run.return_value = True
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.spec_dir = Path("/fake/spec/dir")
        mock_orchestrator.project_dir = Path("/fake/project")

        mock_resolve_model.return_value = "claude-sonnet-4-20250514"

        # Act - should exit with 0 for success
        with pytest.raises(SystemExit) as exc_info:
            main()

        # Assert
        assert exc_info.value.code == 0
        mock_asyncio_run.assert_called_once()


def test_main_with_empty_task_file():
    """Test main with empty task file raises error"""
    with patch("sys.argv", ["spec_runner.py", "--task-file", "/fake/empty.txt"]), \
         patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_text", return_value=""):

        # Act - should exit with code 1 for empty file
        with pytest.raises(SystemExit) as exc_info:
            main()

        # Assert
        assert exc_info.value.code == 1


def test_main_with_nonexistent_task_file():
    """Test main with non-existent task file raises error"""
    with patch("sys.argv", ["spec_runner.py", "--task-file", "/fake/nonexistent.txt"]), \
         patch("pathlib.Path.exists", return_value=False):

        # Act - should exit with code 1 for missing file
        with pytest.raises(SystemExit) as exc_info:
            main()

        # Assert
        assert exc_info.value.code == 1


def test_main_with_complexity_override():
    """Test main with complexity override"""
    with patch("sys.argv", ["spec_runner.py", "--task", "Test task", "--complexity", "simple", "--no-build"]), \
         patch("runners.spec_runner.SpecOrchestrator") as mock_orchestrator_class, \
         patch("runners.spec_runner.resolve_model_id") as mock_resolve_model, \
         patch("runners.spec_runner.asyncio.run") as mock_asyncio_run:

        # Set up mocks - asyncio.run needs to return the result of the coroutine
        mock_asyncio_run.return_value = True
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.spec_dir = Path("/fake/spec/dir")
        mock_orchestrator.project_dir = Path("/fake/project")

        mock_resolve_model.return_value = "claude-sonnet-4-20250514"

        # Act
        with pytest.raises(SystemExit) as exc_info:
            main()

        # Assert
        assert exc_info.value.code == 0
        # Verify complexity override was passed to orchestrator
        mock_orchestrator_class.assert_called_once()
        call_kwargs = mock_orchestrator_class.call_args[1]
        assert call_kwargs["complexity_override"] == "simple"


def test_main_orchestrator_failure():
    """Test main when orchestrator run fails"""
    with patch("sys.argv", ["spec_runner.py", "--task", "Test task", "--no-build"]), \
         patch("runners.spec_runner.SpecOrchestrator") as mock_orchestrator_class, \
         patch("runners.spec_runner.resolve_model_id") as mock_resolve_model, \
         patch("runners.spec_runner.asyncio.run") as mock_asyncio_run:

        # Set up mocks - orchestrator fails
        mock_asyncio_run.return_value = False
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.spec_dir = Path("/fake/spec/dir")
        mock_orchestrator.project_dir = Path("/fake/project")

        mock_resolve_model.return_value = "claude-sonnet-4-20250514"

        # Act - should exit with code 1 for failure
        with pytest.raises(SystemExit) as exc_info:
            main()

        # Assert
        assert exc_info.value.code == 1


def test_main_keyboard_interrupt():
    """Test main with keyboard interrupt"""
    with patch("sys.argv", ["spec_runner.py", "--task", "Test task", "--no-build"]), \
         patch("runners.spec_runner.SpecOrchestrator") as mock_orchestrator_class, \
         patch("runners.spec_runner.resolve_model_id") as mock_resolve_model, \
         patch("runners.spec_runner.asyncio.run") as mock_asyncio_run:

        # Set up mocks - keyboard interrupt
        mock_asyncio_run.side_effect = KeyboardInterrupt()
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.spec_dir = Path("/fake/spec/dir")
        mock_orchestrator.project_dir = Path("/fake/project")

        mock_resolve_model.return_value = "claude-sonnet-4-20250514"

        # Act - should exit with code 1 for interrupt
        with pytest.raises(SystemExit) as exc_info:
            main()

        # Assert
        assert exc_info.value.code == 1
