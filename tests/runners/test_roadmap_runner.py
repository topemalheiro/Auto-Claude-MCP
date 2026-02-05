"""Tests for roadmap_runner"""

from runners.roadmap_runner import main
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture
def mock_project_dir(tmp_path):
    """Create a mock project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


@patch("runners.roadmap_runner.RoadmapOrchestrator")
@patch("runners.roadmap_runner.asyncio.run")
def test_main(mock_asyncio_run, mock_orchestrator_class, mock_project_dir):
    """Test main with valid arguments."""

    # Arrange
    mock_orchestrator = MagicMock()
    mock_orchestrator.run.return_value = True
    mock_orchestrator_class.return_value = mock_orchestrator
    mock_asyncio_run.return_value = True

    with patch("sys.argv", [
        "roadmap_runner.py",
        "--project", str(mock_project_dir)
    ]):
        # Act & Assert - expect SystemExit(0)
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    # Assert - orchestrator was created correctly
    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["project_dir"] == mock_project_dir.resolve()


@patch("runners.roadmap_runner.asyncio.run")
def test_main_with_nonexistent_project(mock_asyncio_run, tmp_path):
    """Test main with nonexistent project directory exits with error."""

    # Mock asyncio.run to prevent it from actually running anything
    # The exit should happen before asyncio.run is called
    mock_asyncio_run.return_value = True

    # Use a path that definitely doesn't exist (within tmp_path for safety)
    nonexistent_path = tmp_path / "this_does_not_exist_xyz123"

    with patch("sys.argv", ["roadmap_runner.py", "--project", str(nonexistent_path)]):
        # Act & Assert - should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            main()
        # Exit code 1 is expected for nonexistent project
        assert exc_info.value.code == 1

    # asyncio.run should NOT have been called since we exit early
    mock_asyncio_run.assert_not_called()


@patch("runners.roadmap_runner.RoadmapOrchestrator")
@patch("runners.roadmap_runner.asyncio.run")
def test_main_with_competitor_analysis(mock_asyncio_run, mock_orchestrator_class, mock_project_dir):
    """Test main with competitor analysis flag."""

    # Arrange
    mock_orchestrator = MagicMock()
    mock_orchestrator.run.return_value = True
    mock_orchestrator_class.return_value = mock_orchestrator
    mock_asyncio_run.return_value = True

    with patch("sys.argv", [
        "roadmap_runner.py",
        "--project", str(mock_project_dir),
        "--competitor-analysis"
    ]):
        # Act & Assert - expect SystemExit(0)
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    # Assert - orchestrator should be created with competitor analysis enabled
    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["enable_competitor_analysis"] is True
    assert call_kwargs["refresh_competitor_analysis"] is False


@patch("runners.roadmap_runner.RoadmapOrchestrator")
@patch("runners.roadmap_runner.asyncio.run")
def test_main_with_refresh_competitor_analysis(mock_asyncio_run, mock_orchestrator_class, mock_project_dir):
    """Test main with refresh competitor analysis flag."""

    # Arrange
    mock_orchestrator = MagicMock()
    mock_orchestrator.run.return_value = True
    mock_orchestrator_class.return_value = mock_orchestrator
    mock_asyncio_run.return_value = True

    with patch("sys.argv", [
        "roadmap_runner.py",
        "--project", str(mock_project_dir),
        "--competitor-analysis",
        "--refresh-competitor-analysis"
    ]):
        # Act & Assert - expect SystemExit(0)
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    # Assert - orchestrator should be created with both flags enabled
    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["enable_competitor_analysis"] is True
    assert call_kwargs["refresh_competitor_analysis"] is True
