"""Comprehensive tests for timeline_tracker.py"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import pytest
import tempfile

from merge.timeline_tracker import FileTimelineTracker
from merge.timeline_models import (
    BranchPoint,
    FileTimeline,
    MainBranchEvent,
    MergeContext,
    TaskFileView,
    TaskIntent,
    WorktreeState,
)


class TestFileTimelineTrackerInit:
    """Tests for FileTimelineTracker initialization"""

    def test_init_with_default_storage(self):
        """Test initialization with default storage path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            assert instance.project_path == project_path.resolve()
            # storage_path is computed from resolved project_path
            assert instance.storage_path == project_path.resolve() / ".auto-claude"
            assert isinstance(instance._timelines, dict)

    def test_init_with_custom_storage(self):
        """Test initialization with custom storage path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            storage_path = Path(tmpdir) / "custom_storage"
            instance = FileTimelineTracker(project_path, storage_path)

            assert instance.storage_path == storage_path

    def test_init_loads_existing_timelines(self):
        """Test that existing timelines are loaded on initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()

            # Mock persistence to return existing timelines
            mock_timeline = MagicMock(spec=FileTimeline)

            with patch('merge.timeline_tracker.TimelinePersistence') as mock_persistence:
                mock_persistence.return_value.load_all_timelines.return_value = {
                    "test.py": mock_timeline
                }
                instance = FileTimelineTracker(project_path, storage_path)

                assert instance._timelines == {"test.py": mock_timeline}


class TestOnTaskStart:
    """Tests for on_task_start method"""

    def test_on_task_start_creates_timeline(self):
        """Test on_task_start creates a new timeline if needed"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            with patch.object(instance.git, 'get_current_main_commit', return_value="abc123"):
                with patch.object(instance.git, 'get_file_content_at_commit', return_value="content"):
                    with patch.object(instance, '_persist_timeline'):
                        instance.on_task_start(
                            task_id="task-001",
                            files_to_modify=["test.py"],
                            branch_point_commit="abc123",
                            task_intent="Add feature",
                            task_title="Feature 1",
                        )

                        assert "test.py" in instance._timelines
                        assert isinstance(instance._timelines["test.py"], FileTimeline)

    def test_on_task_start_without_branch_point(self):
        """Test on_task_start when branch_point_commit is not provided"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            with patch.object(instance.git, 'get_current_main_commit', return_value="def456"):
                with patch.object(instance.git, 'get_file_content_at_commit', return_value=""):
                    with patch.object(instance, '_persist_timeline'):
                        instance.on_task_start(
                            task_id="task-002",
                            files_to_modify=["new.py"],
                        )

                        # Should use current main commit
                        timeline = instance._timelines["new.py"]
                        task_view = timeline.get_task_view("task-002")
                        assert task_view.branch_point.commit_hash == "def456"

    def test_on_task_start_with_new_file(self):
        """Test on_task_start for a file that doesn't exist at branch point"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            with patch.object(instance.git, 'get_current_main_commit', return_value="abc123"):
                # File doesn't exist at commit - returns None
                with patch.object(instance.git, 'get_file_content_at_commit', return_value=None):
                    with patch.object(instance, '_persist_timeline'):
                        instance.on_task_start(
                            task_id="task-001",
                            files_to_modify=["new_file.py"],
                        )

                        timeline = instance._timelines["new_file.py"]
                        task_view = timeline.get_task_view("task-001")
                        # Should use empty string for new file
                        assert task_view.branch_point.content == ""

    def test_on_task_start_with_task_intent(self):
        """Test on_task_start properly captures task intent"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            with patch.object(instance.git, 'get_current_main_commit', return_value="abc123"):
                with patch.object(instance.git, 'get_file_content_at_commit', return_value="content"):
                    with patch.object(instance, '_persist_timeline'):
                        instance.on_task_start(
                            task_id="task-001",
                            files_to_modify=["test.py"],
                            task_intent="Implement OAuth login",
                            task_title="Auth Feature",
                        )

                        timeline = instance._timelines["test.py"]
                        task_view = timeline.get_task_view("task-001")
                        assert task_view.task_intent.description == "Implement OAuth login"
                        assert task_view.task_intent.title == "Auth Feature"
                        assert task_view.task_intent.from_plan is True

    def test_on_task_start_multiple_files(self):
        """Test on_task_start with multiple files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            files = ["file1.py", "file2.py", "file3.py"]

            with patch.object(instance.git, 'get_current_main_commit', return_value="abc123"):
                with patch.object(instance.git, 'get_file_content_at_commit', return_value=""):
                    with patch.object(instance, '_persist_timeline') as mock_persist:
                        instance.on_task_start(
                            task_id="task-multi",
                            files_to_modify=files,
                        )

                        # Should create timeline for each file and persist each
                        assert mock_persist.call_count == 3
                        for f in files:
                            assert f in instance._timelines

    def test_on_task_adds_task_view_to_timeline(self):
        """Test that task view is properly added to timeline"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            with patch.object(instance.git, 'get_current_main_commit', return_value="abc123"):
                with patch.object(instance.git, 'get_file_content_at_commit', return_value="orig"):
                    with patch.object(instance, '_persist_timeline'):
                        instance.on_task_start(
                            task_id="task-001",
                            files_to_modify=["test.py"],
                        )

                        timeline = instance._timelines["test.py"]
                        task_view = timeline.get_task_view("task-001")
                        assert task_view is not None
                        assert task_view.status == "active"
                        assert task_view.commits_behind_main == 0


class TestOnMainBranchCommit:
    """Tests for on_main_branch_commit method"""

    def test_on_main_branch_commit_updates_timelines(self):
        """Test on_main_branch_commit updates existing timelines"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            # Create an existing timeline
            instance._timelines["test.py"] = MagicMock(spec=FileTimeline)

            with patch.object(instance.git, 'get_files_changed_in_commit', return_value=["test.py"]):
                with patch.object(instance.git, 'get_file_content_at_commit', return_value="new content"):
                    with patch.object(instance.git, 'get_commit_info', return_value={
                        "message": "Update test",
                        "author": "Test Author",
                        "diff_summary": "Added 5 lines"
                    }):
                        with patch.object(instance, '_persist_timeline'):
                            instance.on_main_branch_commit("commit123")

                            timeline = instance._timelines["test.py"]
                            timeline.add_main_event.assert_called_once()
                            call_args = timeline.add_main_event.call_args[0][0]
                            assert isinstance(call_args, MainBranchEvent)
                            assert call_args.commit_hash == "commit123"
                            assert call_args.source == "human"

    def test_on_main_branch_commit_skips_nonexistent_timelines(self):
        """Test on_main_branch_commit skips files without timelines"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            with patch.object(instance.git, 'get_files_changed_in_commit', return_value=["unknown.py"]):
                with patch.object(instance, '_persist_timeline') as mock_persist:
                    instance.on_main_branch_commit("commit123")

                    # Should not create timeline for unknown files
                    assert "unknown.py" not in instance._timelines
                    mock_persist.assert_not_called()

    def test_on_main_branch_commit_handles_missing_content(self):
        """Test on_main_branch_commit handles missing file content"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            instance._timelines["test.py"] = MagicMock(spec=FileTimeline)

            with patch.object(instance.git, 'get_files_changed_in_commit', return_value=["test.py"]):
                # Content is None (file deleted perhaps)
                with patch.object(instance.git, 'get_file_content_at_commit', return_value=None):
                    instance.on_main_branch_commit("commit123")

                    # Should not add event when content is None
                    instance._timelines["test.py"].add_main_event.assert_not_called()


class TestOnTaskWorktreeChange:
    """Tests for on_task_worktree_change method"""

    def test_on_task_worktree_change_updates_existing_timeline(self):
        """Test on_task_worktree_change updates existing task view"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            # Create timeline with task view
            timeline = MagicMock(spec=FileTimeline)
            task_view = TaskFileView(
                task_id="task-001",
                branch_point=BranchPoint(
                    commit_hash="abc123",
                    content="original",
                    timestamp=datetime.now(),
                ),
                task_intent=TaskIntent(title="Task", description=""),
            )
            timeline.get_task_view.return_value = task_view
            instance._timelines["test.py"] = timeline

            with patch.object(instance, '_persist_timeline'):
                instance.on_task_worktree_change("task-001", "test.py", "new content")

                assert task_view.worktree_state.content == "new content"
                assert task_view.worktree_state.last_modified is not None

    def test_on_task_worktree_change_creates_timeline_if_missing(self):
        """Test on_task_worktree_change creates timeline if it doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            # No existing timeline
            with patch.object(instance, '_persist_timeline'):
                # This should create timeline via _get_or_create_timeline
                # but task view doesn't exist, so it will return early
                instance.on_task_worktree_change("task-001", "test.py", "new content")

                # Timeline should still be created even though task view lookup fails
                assert "test.py" in instance._timelines

    def test_on_task_worktree_change_skips_unregistered_task(self):
        """Test on_task_worktree_change skips task that's not registered"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            timeline = MagicMock(spec=FileTimeline)
            timeline.get_task_view.return_value = None  # Task not found
            instance._timelines["test.py"] = timeline

            with patch.object(instance, '_persist_timeline') as mock_persist:
                instance.on_task_worktree_change("unknown-task", "test.py", "content")

                # Should not persist when task view not found
                mock_persist.assert_not_called()


class TestOnTaskMerged:
    """Tests for on_task_merged method"""

    def test_on_task_merged_marks_task_as_merged(self):
        """Test on_task_merged updates task status and adds merge event"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            timeline = FileTimeline(file_path="test.py")
            task_view = TaskFileView(
                task_id="task-001",
                branch_point=BranchPoint(
                    commit_hash="abc123",
                    content="orig",
                    timestamp=datetime.now(),
                ),
                task_intent=TaskIntent(title="Task", description=""),
            )
            timeline.task_views["task-001"] = task_view
            instance._timelines["test.py"] = timeline

            with patch.object(instance.git, 'get_file_content_at_commit', return_value="merged"):
                with patch.object(instance, '_persist_timeline'):
                    instance.on_task_merged("task-001", "merge123")

                    assert task_view.status == "merged"
                    assert task_view.merged_at is not None
                    assert len(timeline.main_branch_history) == 1
                    assert timeline.main_branch_history[0].source == "merged_task"

    def test_on_task_merged_adds_main_event(self):
        """Test that on_task_merged adds proper main branch event"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            timeline = FileTimeline(file_path="test.py")
            task_view = TaskFileView(
                task_id="task-001",
                branch_point=BranchPoint(
                    commit_hash="abc123",
                    content="orig",
                    timestamp=datetime.now(),
                ),
                task_intent=TaskIntent(title="Task", description=""),
            )
            timeline.task_views["task-001"] = task_view
            instance._timelines["test.py"] = timeline

            with patch.object(instance.git, 'get_file_content_at_commit', return_value="merged content"):
                with patch.object(instance, '_persist_timeline'):
                    instance.on_task_merged("task-001", "commit456")

                    event = timeline.main_branch_history[0]
                    assert event.source == "merged_task"
                    assert event.merged_from_task == "task-001"
                    assert "task-001" in event.commit_message

    def test_on_task_merged_handles_missing_content(self):
        """Test on_task_merged handles missing file content gracefully"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            timeline = FileTimeline(file_path="test.py")
            task_view = TaskFileView(
                task_id="task-001",
                branch_point=BranchPoint(
                    commit_hash="abc123",
                    content="orig",
                    timestamp=datetime.now(),
                ),
                task_intent=TaskIntent(title="Task", description=""),
            )
            timeline.task_views["task-001"] = task_view
            instance._timelines["test.py"] = timeline

            # Content is None
            with patch.object(instance.git, 'get_file_content_at_commit', return_value=None):
                with patch.object(instance, '_persist_timeline'):
                    instance.on_task_merged("task-001", "merge123")

                    # Should still mark as merged even without content
                    assert task_view.status == "merged"
                    # But should not add main event
                    assert len(timeline.main_branch_history) == 0

    def test_on_task_merged_skips_missing_timeline(self):
        """Test on_task_merged skips files without timelines"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            # No timeline for this file
            instance._timelines = {}

            with patch.object(instance, 'get_files_for_task', return_value=["test.py"]):
                with patch.object(instance, '_persist_timeline'):
                    # Should not error
                    instance.on_task_merged("task-001", "merge123")


class TestOnTaskAbandoned:
    """Tests for on_task_abandoned method"""

    def test_on_task_abandoned_marks_task_status(self):
        """Test on_task_abandoned marks task as abandoned"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            timeline = FileTimeline(file_path="test.py")
            task_view = TaskFileView(
                task_id="task-001",
                branch_point=BranchPoint(
                    commit_hash="abc123",
                    content="orig",
                    timestamp=datetime.now(),
                ),
                task_intent=TaskIntent(title="Task", description=""),
            )
            timeline.task_views["task-001"] = task_view
            instance._timelines["test.py"] = timeline

            with patch.object(instance, '_persist_timeline'):
                instance.on_task_abandoned("task-001")

                assert task_view.status == "abandoned"

    def test_on_task_abandoned_handles_missing_task_view(self):
        """Test on_task_abandoned handles missing task view gracefully"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            timeline = FileTimeline(file_path="test.py")
            instance._timelines["test.py"] = timeline

            with patch.object(instance, '_persist_timeline'):
                # Should not error
                instance.on_task_abandoned("unknown-task")


class TestGetMergeContext:
    """Tests for get_merge_context method"""

    def test_get_merge_context_full(self):
        """Test get_merge_context returns complete context"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            # Create timeline with task view
            timeline = MagicMock(spec=FileTimeline)
            task_view = TaskFileView(
                task_id="task-001",
                branch_point=BranchPoint(
                    commit_hash="abc123",
                    content="base content",
                    timestamp=datetime.now(),
                ),
                task_intent=TaskIntent(
                    title="Add Auth",
                    description="Implement OAuth",
                ),
                commits_behind_main=3,
            )
            task_view.worktree_state = WorktreeState(
                content="worktree changes",
                last_modified=datetime.now(),
            )
            timeline.get_task_view.return_value = task_view
            timeline.get_events_since_commit.return_value = []
            timeline.get_active_tasks.return_value = []
            timeline.get_current_main_state.return_value = None
            instance._timelines["test.py"] = timeline

            context = instance.get_merge_context("task-001", "test.py")

            assert context is not None
            assert context.file_path == "test.py"
            assert context.task_id == "task-001"
            assert context.task_intent.title == "Add Auth"
            assert context.task_worktree_content == "worktree changes"
            assert context.total_commits_behind == 3

    def test_get_merge_context_with_pending_tasks(self):
        """Test get_merge_context includes other pending tasks"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            timeline = MagicMock(spec=FileTimeline)
            task_view = TaskFileView(
                task_id="task-001",
                branch_point=BranchPoint(
                    commit_hash="abc123",
                    content="base",
                    timestamp=datetime.now(),
                ),
                task_intent=TaskIntent(title="Task 1", description=""),
            )

            other_task_view = TaskFileView(
                task_id="task-002",
                branch_point=BranchPoint(
                    commit_hash="def456",
                    content="",
                    timestamp=datetime.now(),
                ),
                task_intent=TaskIntent(
                    title="Task 2",
                    description="Other feature",
                    from_plan=False,
                ),
                commits_behind_main=5,
            )

            timeline.get_task_view.return_value = task_view
            timeline.get_events_since_commit.return_value = []
            timeline.get_active_tasks.return_value = [task_view, other_task_view]
            timeline.get_current_main_state.return_value = None
            instance._timelines["test.py"] = timeline

            context = instance.get_merge_context("task-001", "test.py")

            assert context.total_pending_tasks == 1
            assert len(context.other_pending_tasks) == 1
            assert context.other_pending_tasks[0]["task_id"] == "task-002"

    def test_get_merge_context_no_timeline(self):
        """Test get_merge_context returns None when no timeline exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            context = instance.get_merge_context("task-001", "missing.py")

            assert context is None

    def test_get_merge_context_no_task_view(self):
        """Test get_merge_context returns None when task not in timeline"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            timeline = MagicMock(spec=FileTimeline)
            timeline.get_task_view.return_value = None
            instance._timelines["test.py"] = timeline

            context = instance.get_merge_context("unknown-task", "test.py")

            assert context is None

    def test_get_merge_context_without_worktree_state(self):
        """Test get_merge_context falls back to git for worktree content"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            timeline = MagicMock(spec=FileTimeline)
            task_view = TaskFileView(
                task_id="task-001",
                branch_point=BranchPoint(
                    commit_hash="abc123",
                    content="base",
                    timestamp=datetime.now(),
                ),
                task_intent=TaskIntent(title="Task", description=""),
            )
            task_view.worktree_state = None  # No worktree state

            timeline.get_task_view.return_value = task_view
            timeline.get_events_since_commit.return_value = []
            timeline.get_active_tasks.return_value = []
            timeline.get_current_main_state.return_value = None
            instance._timelines["test.py"] = timeline

            with patch.object(instance.git, 'get_worktree_file_content', return_value="git content"):
                context = instance.get_merge_context("task-001", "test.py")

                assert context.task_worktree_content == "git content"


class TestGetFilesForTask:
    """Tests for get_files_for_task method"""

    def test_get_files_for_task_returns_files(self):
        """Test get_files_for_task returns list of files for task"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            # Create timelines with task views
            timeline1 = FileTimeline(file_path="file1.py")
            timeline1.task_views["task-001"] = MagicMock()
            instance._timelines["file1.py"] = timeline1

            timeline2 = FileTimeline(file_path="file2.py")
            timeline2.task_views["task-001"] = MagicMock()
            instance._timelines["file2.py"] = timeline2

            timeline3 = FileTimeline(file_path="file3.py")
            timeline3.task_views["task-002"] = MagicMock()
            instance._timelines["file3.py"] = timeline3

            files = instance.get_files_for_task("task-001")

            assert len(files) == 2
            assert "file1.py" in files
            assert "file2.py" in files
            assert "file3.py" not in files

    def test_get_files_for_task_empty_result(self):
        """Test get_files_for_task returns empty list for unknown task"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            files = instance.get_files_for_task("unknown-task")

            assert files == []


class TestGetPendingTasksForFile:
    """Tests for get_pending_tasks_for_file method"""

    def test_get_pending_tasks_for_file(self):
        """Test get_pending_tasks_for_file returns active tasks"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            timeline = MagicMock(spec=FileTimeline)
            task1 = TaskFileView(
                task_id="task-001",
                branch_point=BranchPoint(
                    commit_hash="abc",
                    content="",
                    timestamp=datetime.now(),
                ),
                task_intent=TaskIntent(title="T1", description=""),
                status="active",
            )
            task2 = TaskFileView(
                task_id="task-002",
                branch_point=BranchPoint(
                    commit_hash="def",
                    content="",
                    timestamp=datetime.now(),
                ),
                task_intent=TaskIntent(title="T2", description=""),
                status="active",
            )
            timeline.get_active_tasks.return_value = [task1, task2]
            instance._timelines["test.py"] = timeline

            pending = instance.get_pending_tasks_for_file("test.py")

            assert len(pending) == 2
            assert pending[0].task_id == "task-001"
            assert pending[1].task_id == "task-002"

    def test_get_pending_tasks_for_file_no_timeline(self):
        """Test get_pending_tasks_for_file returns empty list when no timeline"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            pending = instance.get_pending_tasks_for_file("missing.py")

            assert pending == []


class TestGetTaskDrift:
    """Tests for get_task_drift method"""

    def test_get_task_drift(self):
        """Test get_task_drift returns commits behind for each file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            # Create timelines with different drift
            timeline1 = MagicMock(spec=FileTimeline)
            task_view1 = TaskFileView(
                task_id="task-001",
                branch_point=BranchPoint(
                    commit_hash="abc",
                    content="",
                    timestamp=datetime.now(),
                ),
                task_intent=TaskIntent(title="T1", description=""),
                status="active",
                commits_behind_main=5,
            )
            timeline1.get_task_view.return_value = task_view1
            instance._timelines["file1.py"] = timeline1

            timeline2 = MagicMock(spec=FileTimeline)
            task_view2 = TaskFileView(
                task_id="task-001",
                branch_point=BranchPoint(
                    commit_hash="abc",
                    content="",
                    timestamp=datetime.now(),
                ),
                task_intent=TaskIntent(title="T1", description=""),
                status="active",
                commits_behind_main=10,
            )
            timeline2.get_task_view.return_value = task_view2
            instance._timelines["file2.py"] = timeline2

            # Add a file with inactive task (should not be included)
            timeline3 = MagicMock(spec=FileTimeline)
            task_view3 = TaskFileView(
                task_id="task-001",
                branch_point=BranchPoint(
                    commit_hash="abc",
                    content="",
                    timestamp=datetime.now(),
                ),
                task_intent=TaskIntent(title="T1", description=""),
                status="merged",  # Not active
                commits_behind_main=3,
            )
            timeline3.get_task_view.return_value = task_view3
            instance._timelines["file3.py"] = timeline3

            drift = instance.get_task_drift("task-001")

            assert drift["file1.py"] == 5
            assert drift["file2.py"] == 10
            assert "file3.py" not in drift  # Inactive task not included

    def test_get_task_drift_empty(self):
        """Test get_task_drift returns empty dict for unknown task"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            drift = instance.get_task_drift("unknown-task")

            assert drift == {}


class TestHasTimeline:
    """Tests for has_timeline method"""

    def test_has_timeline_true(self):
        """Test has_timeline returns True when timeline exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            instance._timelines["test.py"] = MagicMock(spec=FileTimeline)

            assert instance.has_timeline("test.py") is True

    def test_has_timeline_false(self):
        """Test has_timeline returns False when timeline doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            assert instance.has_timeline("missing.py") is False


class TestGetTimeline:
    """Tests for get_timeline method"""

    def test_get_timeline_found(self):
        """Test get_timeline returns timeline when it exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            mock_timeline = MagicMock(spec=FileTimeline)
            instance._timelines["test.py"] = mock_timeline

            result = instance.get_timeline("test.py")

            assert result is mock_timeline

    def test_get_timeline_not_found(self):
        """Test get_timeline returns None when timeline doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            result = instance.get_timeline("missing.py")

            assert result is None


class TestCaptureWorktreeState:
    """Tests for capture_worktree_state method"""

    def test_capture_worktree_state(self):
        """Test capture_worktree_state reads and updates files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir()

            # Create test file
            test_file = worktree_path / "test.py"
            test_file.write_text("worktree content")

            instance = FileTimelineTracker(project_path)

            # Create timeline with task view
            timeline = MagicMock(spec=FileTimeline)
            task_view = TaskFileView(
                task_id="task-001",
                branch_point=BranchPoint(
                    commit_hash="abc",
                    content="",
                    timestamp=datetime.now(),
                ),
                task_intent=TaskIntent(title="Task", description=""),
            )
            timeline.get_task_view.return_value = task_view
            instance._timelines["test.py"] = timeline

            with patch.object(instance.git, 'get_changed_files_in_worktree', return_value=["test.py"]):
                with patch.object(instance, '_persist_timeline'):
                    instance.capture_worktree_state("task-001", worktree_path)

                    assert task_view.worktree_state.content == "worktree content"

    def test_capture_worktree_state_unicode_fallback(self):
        """Test capture_worktree_state handles Unicode decode errors"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir()

            # Create a file with content that might have encoding issues
            test_file = worktree_path / "test.py"
            test_file.write_text("content with special chars: café")

            instance = FileTimelineTracker(project_path)

            timeline = MagicMock(spec=FileTimeline)
            task_view = TaskFileView(
                task_id="task-001",
                branch_point=BranchPoint(
                    commit_hash="abc",
                    content="",
                    timestamp=datetime.now(),
                ),
                task_intent=TaskIntent(title="Task", description=""),
            )
            timeline.get_task_view.return_value = task_view
            instance._timelines["test.py"] = timeline

            with patch.object(instance.git, 'get_changed_files_in_worktree', return_value=["test.py"]):
                with patch.object(instance, '_persist_timeline'):
                    instance.capture_worktree_state("task-001", worktree_path)

                    # Should handle UTF-8 correctly
                    assert "café" in task_view.worktree_state.content

    def test_capture_worktree_state_handles_exception(self):
        """Test capture_worktree_state handles exceptions gracefully"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir()

            instance = FileTimelineTracker(project_path)

            with patch.object(instance.git, 'get_changed_files_in_worktree', side_effect=Exception("Git error")):
                # Should not raise
                instance.capture_worktree_state("task-001", worktree_path)


class TestInitializeFromWorktree:
    """Tests for initialize_from_worktree method"""

    def test_initialize_from_worktree(self):
        """Test initialize_from_worktree registers task from existing worktree"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir()

            instance = FileTimelineTracker(project_path)

            with patch.object(instance.git, 'get_branch_point', return_value="abc123"):
                with patch.object(instance.git, 'get_changed_files_in_worktree', return_value=["test.py"]):
                    with patch.object(instance.git, 'get_file_content_at_commit', return_value=""):
                        with patch.object(instance.git, '_detect_target_branch', return_value="main"):
                            with patch.object(instance.git, 'count_commits_between', return_value=5):
                                with patch.object(instance, 'capture_worktree_state'):
                                    with patch.object(instance, '_persist_timeline'):
                                        instance.initialize_from_worktree(
                                            task_id="task-001",
                                            worktree_path=worktree_path,
                                            task_intent="Add feature",
                                        )

                                        # Should create timeline for test.py
                                        timeline = instance._timelines.get("test.py")
                                        assert timeline is not None
                                        # Should update commits_behind_main
                                        task_view = timeline.get_task_view("task-001")
                                        assert task_view is not None
                                        assert task_view.commits_behind_main == 5

    def test_initialize_from_worktree_no_branch_point(self):
        """Test initialize_from_worktree handles missing branch point"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir()

            instance = FileTimelineTracker(project_path)

            with patch.object(instance.git, 'get_branch_point', return_value=None):
                # Should return early without error
                instance.initialize_from_worktree(
                    task_id="task-001",
                    worktree_path=worktree_path,
                )

    def test_initialize_from_worktree_no_changed_files(self):
        """Test initialize_from_worktree handles no changed files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir()

            instance = FileTimelineTracker(project_path)

            with patch.object(instance.git, 'get_branch_point', return_value="abc123"):
                with patch.object(instance.git, 'get_changed_files_in_worktree', return_value=[]):
                    # Should return early without error
                    instance.initialize_from_worktree(
                        task_id="task-001",
                        worktree_path=worktree_path,
                    )

    def test_initialize_from_worktree_with_target_branch(self):
        """Test initialize_from_worktree with explicit target branch"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir()

            instance = FileTimelineTracker(project_path)

            with patch.object(instance.git, 'get_branch_point', return_value="abc123"):
                with patch.object(instance.git, 'get_changed_files_in_worktree', return_value=["test.py"]):
                    with patch.object(instance, 'on_task_start'):
                        with patch.object(instance, 'capture_worktree_state'):
                            with patch.object(instance.git, 'count_commits_between', return_value=3):
                                instance.initialize_from_worktree(
                                    task_id="task-001",
                                    worktree_path=worktree_path,
                                    target_branch="develop",
                                )

                                # Should use explicit target branch
                                instance.git.count_commits_between.assert_called_with("abc123", "develop")

    def test_initialize_from_worktree_exception_handling(self):
        """Test initialize_from_worktree handles exceptions gracefully"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir()

            instance = FileTimelineTracker(project_path)

            with patch.object(instance.git, 'get_branch_point', side_effect=Exception("Error")):
                # Should not raise
                instance.initialize_from_worktree(
                    task_id="task-001",
                    worktree_path=worktree_path,
                )


class TestInternalHelpers:
    """Tests for internal helper methods"""

    def test_get_or_create_timeline_existing(self):
        """Test _get_or_create_timeline returns existing timeline"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            existing = MagicMock(spec=FileTimeline)
            instance._timelines["test.py"] = existing

            result = instance._get_or_create_timeline("test.py")

            assert result is existing

    def test_get_or_create_timeline_new(self):
        """Test _get_or_create_timeline creates new timeline"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            result = instance._get_or_create_timeline("new.py")

            assert isinstance(result, FileTimeline)
            assert "new.py" in instance._timelines

    def test_persist_timeline(self):
        """Test _persist_timeline saves timeline"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()

            instance = FileTimelineTracker(project_path, storage_path)

            timeline = MagicMock(spec=FileTimeline)
            instance._timelines["test.py"] = timeline

            with patch.object(instance.persistence, 'save_timeline'):
                with patch.object(instance.persistence, 'update_index'):
                    instance._persist_timeline("test.py")

                    instance.persistence.save_timeline.assert_called_once_with("test.py", timeline)

    def test_persist_timeline_missing_timeline(self):
        """Test _persist_timeline handles missing timeline gracefully"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            instance = FileTimelineTracker(project_path)

            # No timeline for this file
            instance._timelines = {}

            # Should not error
            instance._persist_timeline("missing.py")
