"""Tests for tracker_cli"""

from datetime import datetime
from merge.tracker_cli import (
    cmd_init_from_worktree,
    cmd_list_files,
    cmd_notify_commit,
    cmd_show_context,
    cmd_show_drift,
    cmd_show_timeline,
    find_project_root,
    get_tracker,
    main,
)
from merge.timeline_models import (
    BranchPoint,
    FileTimeline,
    MainBranchEvent,
    MergeContext,
    TaskFileView,
    TaskIntent,
)
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_find_project_root():
    """Test find_project_root finds project directory"""

    # Act
    result = find_project_root()

    # Assert
    assert result is not None
    assert isinstance(result, Path)


@patch("merge.tracker_cli.Path")
def test_find_project_root_with_auto_claude(mock_path):
    """Test find_project_root finds .auto-claude directory"""

    # Arrange
    mock_cwd = MagicMock()
    mock_cwd.exists.side_effect = lambda x: x == ".auto-claude"
    mock_path.cwd.return_value = mock_cwd
    mock_path.return_value.exists.return_value = False

    # Act
    result = find_project_root()

    # Assert
    assert result is not None


def test_get_tracker():
    """Test get_tracker returns FileTimelineTracker instance"""

    # Act
    result = get_tracker()

    # Assert
    assert result is not None
    assert hasattr(result, "on_main_branch_commit")
    assert hasattr(result, "get_timeline")
    assert hasattr(result, "get_task_drift")
    assert hasattr(result, "get_merge_context")


@patch("merge.tracker_cli.get_tracker")
def test_cmd_notify_commit(mock_get_tracker, capsys):
    """Test cmd_notify_commit processes commit hash"""

    # Arrange
    args = MagicMock()
    args.commit_hash = "abc123def456"

    mock_tracker = MagicMock()
    mock_get_tracker.return_value = mock_tracker

    # Act
    cmd_notify_commit(args)

    # Assert
    mock_tracker.on_main_branch_commit.assert_called_once_with("abc123def456")
    captured = capsys.readouterr()
    assert "Processing commit:" in captured.out


@patch("merge.tracker_cli.get_tracker")
def test_cmd_show_timeline_no_timeline(mock_get_tracker, capsys):
    """Test cmd_show_timeline handles missing timeline"""

    # Arrange
    args = MagicMock()
    args.file_path = "test.py"

    mock_tracker = MagicMock()
    mock_tracker.get_timeline.return_value = None
    mock_get_tracker.return_value = mock_tracker

    # Act
    cmd_show_timeline(args)

    # Assert
    mock_tracker.get_timeline.assert_called_once_with("test.py")
    captured = capsys.readouterr()
    assert "No timeline found" in captured.out


@patch("merge.tracker_cli.get_tracker")
def test_cmd_show_timeline_with_data(mock_get_tracker, capsys):
    """Test cmd_show_timeline displays timeline information"""

    # Arrange
    args = MagicMock()
    args.file_path = "test.py"

    mock_timeline = MagicMock()
    mock_timeline.created_at = datetime.now()
    mock_timeline.last_updated = datetime.now()
    mock_timeline.main_branch_history = []
    mock_timeline.task_views = {}

    mock_tracker = MagicMock()
    mock_tracker.get_timeline.return_value = mock_timeline
    mock_get_tracker.return_value = mock_tracker

    # Act
    cmd_show_timeline(args)

    # Assert
    mock_tracker.get_timeline.assert_called_once_with("test.py")
    captured = capsys.readouterr()
    assert "Timeline for:" in captured.out


@patch("merge.tracker_cli.get_tracker")
def test_cmd_show_drift_empty(mock_get_tracker, capsys):
    """Test cmd_show_drift handles empty drift"""

    # Arrange
    args = MagicMock()
    args.task_id = "task_001"

    mock_tracker = MagicMock()
    mock_tracker.get_task_drift.return_value = {}
    mock_get_tracker.return_value = mock_tracker

    # Act
    cmd_show_drift(args)

    # Assert
    mock_tracker.get_task_drift.assert_called_once_with("task_001")
    captured = capsys.readouterr()
    assert "No files found" in captured.out


@patch("merge.tracker_cli.get_tracker")
def test_cmd_show_drift_with_data(mock_get_tracker, capsys):
    """Test cmd_show_drift displays drift information"""

    # Arrange
    args = MagicMock()
    args.task_id = "task_001"

    mock_tracker = MagicMock()
    mock_tracker.get_task_drift.return_value = {"test.py": 5, "main.py": 3}
    mock_get_tracker.return_value = mock_tracker

    # Act
    cmd_show_drift(args)

    # Assert
    mock_tracker.get_task_drift.assert_called_once_with("task_001")
    captured = capsys.readouterr()
    assert "Drift Report" in captured.out
    assert "test.py:" in captured.out


@patch("merge.tracker_cli.get_tracker")
def test_cmd_show_context_no_context(mock_get_tracker, capsys):
    """Test cmd_show_context handles missing context"""

    # Arrange
    args = MagicMock()
    args.task_id = "task_001"
    args.file_path = "test.py"

    mock_tracker = MagicMock()
    mock_tracker.get_merge_context.return_value = None
    mock_get_tracker.return_value = mock_tracker

    # Act
    cmd_show_context(args)

    # Assert
    mock_tracker.get_merge_context.assert_called_once_with("task_001", "test.py")
    captured = capsys.readouterr()
    assert "No merge context available" in captured.out


@patch("merge.tracker_cli.get_tracker")
def test_cmd_show_context_with_data(mock_get_tracker, capsys):
    """Test cmd_show_context displays merge context"""

    # Arrange
    args = MagicMock()
    args.task_id = "task_001"
    args.file_path = "test.py"

    mock_context = MagicMock()
    mock_context.task_intent = MagicMock()
    mock_context.task_intent.title = "Test Task"
    mock_context.task_intent.description = "Test description"
    mock_context.task_branch_point = MagicMock()
    mock_context.task_branch_point.commit_hash = "abc123"
    mock_context.current_main_commit = "def456"
    mock_context.total_commits_behind = 5
    mock_context.total_pending_tasks = 2
    mock_context.main_evolution = []
    mock_context.other_pending_tasks = []

    mock_tracker = MagicMock()
    mock_tracker.get_merge_context.return_value = mock_context
    mock_get_tracker.return_value = mock_tracker

    # Act
    cmd_show_context(args)

    # Assert
    mock_tracker.get_merge_context.assert_called_once_with("task_001", "test.py")
    captured = capsys.readouterr()
    assert "Merge Context" in captured.out


@patch("merge.tracker_cli.get_tracker")
def test_cmd_list_files_empty(mock_get_tracker, capsys):
    """Test cmd_list_files handles empty timeline list"""

    # Arrange
    args = MagicMock()

    mock_tracker = MagicMock()
    mock_tracker._timelines = {}
    mock_get_tracker.return_value = mock_tracker

    # Act
    cmd_list_files(args)

    # Assert
    captured = capsys.readouterr()
    assert "No files currently tracked" in captured.out


@patch("merge.tracker_cli.get_tracker")
def test_cmd_list_files_with_data(mock_get_tracker, capsys):
    """Test cmd_list_files displays tracked files"""

    # Arrange
    args = MagicMock()

    mock_timeline = MagicMock()
    mock_timeline.task_views = {}
    mock_timeline.main_branch_history = []

    mock_tracker = MagicMock()
    mock_tracker._timelines = {"test.py": mock_timeline, "main.py": mock_timeline}
    mock_get_tracker.return_value = mock_tracker

    # Act
    cmd_list_files(args)

    # Assert
    captured = capsys.readouterr()
    assert "Tracked Files" in captured.out


@patch("merge.tracker_cli.get_tracker")
def test_cmd_init_from_worktree(mock_get_tracker, capsys):
    """Test cmd_init_from_worktree initializes tracking"""

    # Arrange
    args = MagicMock()
    args.task_id = "task_001"
    args.worktree_path = "/tmp/test"
    args.intent = "Test intent"
    args.title = "Test title"

    mock_tracker = MagicMock()
    mock_get_tracker.return_value = mock_tracker

    with patch.object(Path, "exists", return_value=True):
        # Act
        cmd_init_from_worktree(args)

        # Assert
        mock_tracker.initialize_from_worktree.assert_called_once()
        captured = capsys.readouterr()
        assert "Initializing tracking" in captured.out


@patch("merge.tracker_cli.get_tracker")
def test_cmd_init_from_worktree_not_exists(mock_get_tracker, capsys):
    """Test cmd_init_from_worktree handles missing worktree"""

    # Arrange
    args = MagicMock()
    args.task_id = "task_001"
    args.worktree_path = "/nonexistent/path"
    args.intent = "Test intent"
    args.title = "Test title"

    mock_tracker = MagicMock()
    mock_get_tracker.return_value = mock_tracker

    # Use a custom mock for Path that returns exists=False
    with patch("merge.tracker_cli.Path") as MockPath:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_instance.resolve.return_value = Path("/tmp/fake")
        MockPath.return_value = mock_path_instance

        # Act & Assert
        with pytest.raises(SystemExit):
            cmd_init_from_worktree(args)

    captured = capsys.readouterr()
    assert "does not exist" in captured.out


@patch("merge.tracker_cli.get_tracker")
def test_cmd_init_from_worktree_empty_args(mock_get_tracker, capsys):
    """Test cmd_init_from_worktree handles empty intent/title"""

    # Arrange
    args = MagicMock()
    args.task_id = "task_001"
    args.worktree_path = "/tmp/test"
    args.intent = None
    args.title = None

    mock_tracker = MagicMock()
    mock_get_tracker.return_value = mock_tracker

    with patch.object(Path, "exists", return_value=True):
        # Act
        cmd_init_from_worktree(args)

        # Assert
        mock_tracker.initialize_from_worktree.assert_called_once()


@patch("sys.argv", ["tracker_cli"])
def test_main_no_command():
    """Test main with no command triggers help"""

    # Act & Assert
    with pytest.raises(SystemExit):
        main()


@patch("sys.argv", ["tracker_cli", "notify-commit", "abc123"])
def test_main_with_notify_command(capsys):
    """Test main with notify-commit command"""

    # Arrange
    with patch("merge.tracker_cli.get_tracker") as mock_get_tracker:
        mock_tracker = MagicMock()
        mock_get_tracker.return_value = mock_tracker

        # Act - main() should complete successfully
        main()

        # Assert
        mock_tracker.on_main_branch_commit.assert_called_once_with("abc123")
        captured = capsys.readouterr()
        assert "Processing commit:" in captured.out


@patch("sys.argv", ["tracker_cli", "list-files"])
def test_main_with_list_command(capsys):
    """Test main with list-files command"""

    # Arrange
    with patch("merge.tracker_cli.get_tracker") as mock_get_tracker:
        mock_tracker = MagicMock()
        mock_tracker._timelines = {}
        mock_get_tracker.return_value = mock_tracker

        # Act - main() should complete successfully
        main()

        # Assert - command should execute without error
        mock_get_tracker.assert_called_once()
        captured = capsys.readouterr()
        assert "Tracked Files" in captured.out
