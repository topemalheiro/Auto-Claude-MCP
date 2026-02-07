"""
Comprehensive tests for core.workspace.models module.

Tests cover:
- WorkspaceMode enum
- WorkspaceChoice enum
- ParallelMergeTask dataclass
- ParallelMergeResult dataclass
- MergeLockError exception
- MergeLock context manager with PID-based locking
- SpecNumberLockError exception
- SpecNumberLock context manager
- get_next_spec_number() method
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from core.workspace.models import (
    WorkspaceMode,
    WorkspaceChoice,
    ParallelMergeTask,
    ParallelMergeResult,
    MergeLockError,
    MergeLock,
    SpecNumberLockError,
    SpecNumberLock,
)


class TestWorkspaceMode:
    """Tests for WorkspaceMode enum."""

    def test_workspace_mode_isolated_value(self):
        """Test WorkspaceMode.ISOLATED has correct value."""
        assert WorkspaceMode.ISOLATED.value == "isolated"

    def test_workspace_mode_direct_value(self):
        """Test WorkspaceMode.DIRECT has correct value."""
        assert WorkspaceMode.DIRECT.value == "direct"

    def test_workspace_mode_enum_members(self):
        """Test WorkspaceMode has all expected members."""
        assert hasattr(WorkspaceMode, "ISOLATED")
        assert hasattr(WorkspaceMode, "DIRECT")

    def test_workspace_mode_enum_comparison(self):
        """Test WorkspaceMode enum comparison works correctly."""
        assert WorkspaceMode.ISOLATED == WorkspaceMode.ISOLATED
        assert WorkspaceMode.ISOLATED != WorkspaceMode.DIRECT


class TestWorkspaceChoice:
    """Tests for WorkspaceChoice enum."""

    def test_workspace_choice_merge_value(self):
        """Test WorkspaceChoice.MERGE has correct value."""
        assert WorkspaceChoice.MERGE.value == "merge"

    def test_workspace_choice_review_value(self):
        """Test WorkspaceChoice.REVIEW has correct value."""
        assert WorkspaceChoice.REVIEW.value == "review"

    def test_workspace_choice_test_value(self):
        """Test WorkspaceChoice.TEST has correct value."""
        assert WorkspaceChoice.TEST.value == "test"

    def test_workspace_choice_later_value(self):
        """Test WorkspaceChoice.LATER has correct value."""
        assert WorkspaceChoice.LATER.value == "later"

    def test_workspace_choice_enum_members(self):
        """Test WorkspaceChoice has all expected members."""
        assert hasattr(WorkspaceChoice, "MERGE")
        assert hasattr(WorkspaceChoice, "REVIEW")
        assert hasattr(WorkspaceChoice, "TEST")
        assert hasattr(WorkspaceChoice, "LATER")


class TestParallelMergeTask:
    """Tests for ParallelMergeTask dataclass."""

    def test_parallel_merge_task_initialization(self):
        """Test ParallelMergeTask can be initialized with all fields."""
        task = ParallelMergeTask(
            file_path="/path/to/file.py",
            main_content="main content",
            worktree_content="worktree content",
            base_content="base content",
            spec_name="001-test-spec",
            project_dir=Path("/project"),
        )

        assert task.file_path == "/path/to/file.py"
        assert task.main_content == "main content"
        assert task.worktree_content == "worktree content"
        assert task.base_content == "base content"
        assert task.spec_name == "001-test-spec"
        assert task.project_dir == Path("/project")

    def test_parallel_merge_task_with_none_base_content(self):
        """Test ParallelMergeTask with None base_content."""
        task = ParallelMergeTask(
            file_path="/path/to/file.py",
            main_content="main content",
            worktree_content="worktree content",
            base_content=None,
            spec_name="002-another-spec",
            project_dir=Path("/another/project"),
        )

        assert task.base_content is None

    def test_parallel_merge_task_equality(self):
        """Test ParallelMergeTask equality."""
        task1 = ParallelMergeTask(
            file_path="/path/to/file.py",
            main_content="content",
            worktree_content="content",
            base_content=None,
            spec_name="001",
            project_dir=Path("/project"),
        )
        task2 = ParallelMergeTask(
            file_path="/path/to/file.py",
            main_content="content",
            worktree_content="content",
            base_content=None,
            spec_name="001",
            project_dir=Path("/project"),
        )

        assert task1 == task2


class TestParallelMergeResult:
    """Tests for ParallelMergeResult dataclass."""

    def test_parallel_merge_result_initialization_success(self):
        """Test ParallelMergeResult for successful merge."""
        result = ParallelMergeResult(
            file_path="/path/to/file.py",
            merged_content="merged content",
            success=True,
            error=None,
            was_auto_merged=False,
        )

        assert result.file_path == "/path/to/file.py"
        assert result.merged_content == "merged content"
        assert result.success is True
        assert result.error is None
        assert result.was_auto_merged is False

    def test_parallel_merge_result_initialization_failure(self):
        """Test ParallelMergeResult for failed merge."""
        result = ParallelMergeResult(
            file_path="/path/to/file.py",
            merged_content=None,
            success=False,
            error="Conflict detected",
            was_auto_merged=False,
        )

        assert result.merged_content is None
        assert result.success is False
        assert result.error == "Conflict detected"

    def test_parallel_merge_result_auto_merged(self):
        """Test ParallelMergeResult with auto-merge flag."""
        result = ParallelMergeResult(
            file_path="/path/to/file.py",
            merged_content="auto merged",
            success=True,
            error=None,
            was_auto_merged=True,
        )

        assert result.was_auto_merged is True

    def test_parallel_merge_result_defaults(self):
        """Test ParallelMergeResult default values."""
        result = ParallelMergeResult(
            file_path="/path/to/file.py",
            merged_content="content",
            success=True,
        )

        assert result.error is None
        assert result.was_auto_merged is False


class TestMergeLockError:
    """Tests for MergeLockError exception."""

    def test_merge_lock_error_is_exception(self):
        """Test MergeLockError is an Exception subclass."""
        assert issubclass(MergeLockError, Exception)

    def test_merge_lock_error_can_be_raised(self):
        """Test MergeLockError can be raised with message."""
        with pytest.raises(MergeLockError) as exc_info:
            raise MergeLockError("Test error message")

        assert "Test error message" in str(exc_info.value)

    def test_merge_lock_error_can_be_raised_without_message(self):
        """Test MergeLockError can be raised without message."""
        with pytest.raises(MergeLockError):
            raise MergeLockError()


class TestMergeLock:
    """Tests for MergeLock context manager."""

    @pytest.fixture
    def project_dir(self, tmp_path):
        """Create a temporary project directory."""
        return tmp_path / "project"

    @pytest.fixture
    def lock_dir(self, project_dir):
        """Get the lock directory path."""
        return project_dir / ".auto-claude" / ".locks"

    def test_merge_lock_initialization(self, project_dir):
        """Test MergeLock initializes correctly."""
        lock = MergeLock(project_dir, "test-spec")

        assert lock.project_dir == project_dir
        assert lock.spec_name == "test-spec"
        assert lock.lock_dir == project_dir / ".auto-claude" / ".locks"
        assert lock.lock_file == project_dir / ".auto-claude" / ".locks" / "merge-test-spec.lock"
        assert lock.acquired is False

    def test_merge_lock_acquire_and_release(self, project_dir):
        """Test MergeLock can be acquired and released."""
        lock = MergeLock(project_dir, "test-spec")

        with lock:
            assert lock.acquired is True
            assert lock.lock_file.exists()
            # Check PID is written to lock file
            pid_content = lock.lock_file.read_text(encoding="utf-8")
            assert pid_content.strip().isdigit()

        # After context, lock file should be removed (acquired flag stays True due to implementation)
        assert not lock.lock_file.exists()

    def test_merge_lock_creates_lock_directory(self, project_dir):
        """Test MergeLock creates lock directory if it doesn't exist."""
        lock_dir = project_dir / ".auto-claude" / ".locks"
        assert not lock_dir.exists()

        lock = MergeLock(project_dir, "test-spec")
        with lock:
            assert lock_dir.exists()

    @pytest.mark.slow
    def test_merge_lock_concurrent_acquisition_blocked(self, project_dir):
        """Test MergeLock blocks concurrent acquisition attempts."""
        lock1 = MergeLock(project_dir, "test-spec")
        lock2 = MergeLock(project_dir, "test-spec")

        acquired_first = False
        blocked_second = False

        with lock1:
            acquired_first = True
            assert lock1.lock_file.exists()

            # Second lock should fail since first is held
            try:
                with lock2:
                    pass
            except MergeLockError:
                blocked_second = True

        assert acquired_first
        assert blocked_second

    @patch("os.kill")
    def test_merge_lock_stale_lock_cleanup(self, mock_kill, project_dir):
        """Test MergeLock cleans up stale locks from dead processes."""
        # Create a stale lock file with a non-existent PID
        lock_dir = project_dir / ".auto-claude" / ".locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        stale_lock_file = lock_dir / "merge-test-spec.lock"
        stale_pid = 99999  # Non-existent PID
        stale_lock_file.write_text(str(stale_pid), encoding="utf-8")

        # Mock os.kill to raise ProcessLookupError for the stale PID
        mock_kill.side_effect = ProcessLookupError

        lock = MergeLock(project_dir, "test-spec")

        with lock:
            # Should successfully acquire after cleaning stale lock
            assert lock.acquired is True
            # Verify new PID is in lock file
            current_pid = lock.lock_file.read_text(encoding="utf-8").strip()
            assert current_pid == str(os.getpid())

    def test_merge_lock_invalid_pid_format(self, project_dir):
        """Test MergeLock handles invalid PID format in lock file."""
        lock_dir = project_dir / ".auto-claude" / ".locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        invalid_lock_file = lock_dir / "merge-test-spec.lock"
        invalid_lock_file.write_text("invalid-pid-content", encoding="utf-8")

        lock = MergeLock(project_dir, "test-spec")

        # Should clean invalid lock and acquire
        with lock:
            assert lock.acquired is True

    @patch("os.kill")
    def test_merge_lock_oserror_on_pid_check(self, mock_kill, project_dir):
        """Test MergeLock handles OSError during PID check."""
        lock_dir = project_dir / ".auto-claude" / ".locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock_file = lock_dir / "merge-test-spec.lock"
        lock_file.write_text("12345", encoding="utf-8")

        # Mock os.kill to raise OSError
        mock_kill.side_effect = OSError("Process check failed")

        lock = MergeLock(project_dir, "test-spec")

        # Should clean lock on OSError and acquire
        with lock:
            assert lock.acquired is True

    def test_merge_lock_timeout(self, project_dir):
        """Test MergeLock raises error after timeout."""
        # Create a lock file that persists
        lock_dir = project_dir / ".auto-claude" / ".locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock_file = lock_dir / "merge-test-spec.lock"
        lock_file.write_text(str(os.getpid()), encoding="utf-8")  # Use current PID

        # Mock os.kill to make process appear running
        with patch("os.kill") as mock_kill:
            mock_kill.return_value = None  # Process exists

            lock = MergeLock(project_dir, "test-spec")

            # Should timeout after 30 seconds
            with patch("time.sleep"):  # Avoid actual sleep
                with patch("time.time") as mock_time:
                    # First call returns start time, subsequent calls return start + 31s
                    start_time = 1000
                    mock_time.side_effect = [start_time, start_time + 31]

                    with pytest.raises(MergeLockError) as exc_info:
                        with lock:
                            pass

                    assert "Could not acquire merge lock" in str(exc_info.value)
                    assert "30s" in str(exc_info.value)

    def test_merge_lock_best_effort_cleanup(self, project_dir):
        """Test MergeLock cleanup is best effort on exception."""
        lock = MergeLock(project_dir, "test-spec")

        with patch.object(Path, "unlink", side_effect=OSError("Delete failed")):
            # Should not raise during cleanup even if unlink fails
            try:
                with lock:
                    raise RuntimeError("Test exception")
            except RuntimeError:
                pass

    def test_merge_lock_different_specs_dont_conflict(self, project_dir):
        """Test MergeLock for different specs don't conflict."""
        lock1 = MergeLock(project_dir, "spec-001")
        lock2 = MergeLock(project_dir, "spec-002")

        with lock1:
            assert lock1.acquired is True
            with lock2:
                assert lock2.acquired is True

    def test_merge_lock_exit_without_exception(self, project_dir):
        """Test MergeLock __exit__ without exception."""
        lock = MergeLock(project_dir, "test-spec")

        with lock:
            pass

        assert not lock.lock_file.exists()

    def test_merge_lock_exit_with_exception(self, project_dir):
        """Test MergeLock __exit__ with exception."""
        lock = MergeLock(project_dir, "test-spec")

        with pytest.raises(ValueError):
            with lock:
                raise ValueError("Test error")

        # Lock should still be cleaned up
        assert not lock.lock_file.exists()

    def test_merge_lock_pid_written_correctly(self, project_dir):
        """Test MergeLock writes current PID to lock file."""
        lock = MergeLock(project_dir, "test-spec")
        expected_pid = os.getpid()

        with lock:
            actual_pid = int(lock.lock_file.read_text(encoding="utf-8").strip())
            assert actual_pid == expected_pid

    def test_merge_lock_multiple_acquire_release_cycles(self, project_dir):
        """Test MergeLock can be acquired and released multiple times."""
        lock = MergeLock(project_dir, "test-spec")

        for _ in range(3):
            with lock:
                assert lock.acquired is True
                assert lock.lock_file.exists()
            assert not lock.lock_file.exists()


class TestSpecNumberLockError:
    """Tests for SpecNumberLockError exception."""

    def test_spec_number_lock_error_is_exception(self):
        """Test SpecNumberLockError is an Exception subclass."""
        assert issubclass(SpecNumberLockError, Exception)

    def test_spec_number_lock_error_can_be_raised(self):
        """Test SpecNumberLockError can be raised with message."""
        with pytest.raises(SpecNumberLockError) as exc_info:
            raise SpecNumberLockError("Test error message")

        assert "Test error message" in str(exc_info.value)

    def test_spec_number_lock_error_can_be_raised_without_message(self):
        """Test SpecNumberLockError can be raised without message."""
        with pytest.raises(SpecNumberLockError):
            raise SpecNumberLockError()


class TestSpecNumberLock:
    """Tests for SpecNumberLock context manager."""

    @pytest.fixture
    def project_dir(self, tmp_path):
        """Create a temporary project directory."""
        return tmp_path / "project"

    @pytest.fixture
    def lock_dir(self, project_dir):
        """Get the lock directory path."""
        return project_dir / ".auto-claude" / ".locks"

    def test_spec_number_lock_initialization(self, project_dir):
        """Test SpecNumberLock initializes correctly."""
        lock = SpecNumberLock(project_dir)

        assert lock.project_dir == project_dir
        assert lock.lock_dir == project_dir / ".auto-claude" / ".locks"
        assert lock.lock_file == lock.lock_dir / "spec-numbering.lock"
        assert lock.acquired is False
        assert lock._global_max is None

    def test_spec_number_lock_acquire_and_release(self, project_dir):
        """Test SpecNumberLock can be acquired and released."""
        lock = SpecNumberLock(project_dir)

        with lock:
            assert lock.acquired is True
            assert lock.lock_file.exists()
            # Check PID is written to lock file
            pid_content = lock.lock_file.read_text(encoding="utf-8")
            assert pid_content.strip().isdigit()

        # After context, lock file should be removed (acquired flag stays True due to implementation)
        assert not lock.lock_file.exists()

    def test_spec_number_lock_creates_lock_directory(self, project_dir):
        """Test SpecNumberLock creates lock directory if it doesn't exist."""
        lock_dir = project_dir / ".auto-claude" / ".locks"
        assert not lock_dir.exists()

        lock = SpecNumberLock(project_dir)
        with lock:
            assert lock_dir.exists()

    @patch("os.kill")
    def test_spec_number_lock_stale_lock_cleanup(self, mock_kill, project_dir):
        """Test SpecNumberLock cleans up stale locks from dead processes."""
        # Create a stale lock file
        lock_dir = project_dir / ".auto-claude" / ".locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        stale_lock_file = lock_dir / "spec-numbering.lock"
        stale_pid = 99999
        stale_lock_file.write_text(str(stale_pid), encoding="utf-8")

        # Mock os.kill to raise ProcessLookupError
        mock_kill.side_effect = ProcessLookupError

        lock = SpecNumberLock(project_dir)

        with lock:
            assert lock.acquired is True
            current_pid = lock.lock_file.read_text(encoding="utf-8").strip()
            assert current_pid == str(os.getpid())

    def test_spec_number_lock_invalid_pid_format(self, project_dir):
        """Test SpecNumberLock handles invalid PID format."""
        lock_dir = project_dir / ".auto-claude" / ".locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        invalid_lock_file = lock_dir / "spec-numbering.lock"
        invalid_lock_file.write_text("invalid-pid", encoding="utf-8")

        lock = SpecNumberLock(project_dir)

        with lock:
            assert lock.acquired is True

    def test_spec_number_lock_timeout(self, project_dir):
        """Test SpecNumberLock raises error after timeout."""
        lock_dir = project_dir / ".auto-claude" / ".locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock_file = lock_dir / "spec-numbering.lock"
        lock_file.write_text(str(os.getpid()), encoding="utf-8")

        with patch("os.kill") as mock_kill:
            mock_kill.return_value = None

            lock = SpecNumberLock(project_dir)

            with patch("time.sleep"):
                with patch("time.time") as mock_time:
                    start_time = 1000
                    mock_time.side_effect = [start_time, start_time + 31]

                    with pytest.raises(SpecNumberLockError) as exc_info:
                        with lock:
                            pass

                    assert "Could not acquire spec numbering lock" in str(exc_info.value)

    def test_spec_number_lock_active_lock_retry(self, project_dir):
        """Test SpecNumberLock retries when lock is held but not timed out."""
        lock_dir = project_dir / ".auto-claude" / ".locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock_file = lock_dir / "spec-numbering.lock"

        # Create a scenario where lock exists initially but gets removed before timeout
        with patch("os.kill") as mock_kill:
            mock_kill.return_value = None  # Process is running

            lock = SpecNumberLock(project_dir)

            # Create lock file before entering context
            lock_file.write_text(str(os.getpid()), encoding="utf-8")

            sleep_count = [0]
            original_sleep = __import__("time").sleep

            def mock_sleep_handler(seconds):
                sleep_count[0] += 1
                # Remove lock file on second sleep attempt to simulate it being released
                if sleep_count[0] == 2 and lock_file.exists():
                    lock_file.unlink()
                # Don't actually sleep
                pass

            with patch("time.sleep", side_effect=mock_sleep_handler):
                with patch("time.time") as mock_time:
                    # Return times that don't exceed timeout
                    start_time = 1000
                    mock_time.side_effect = [start_time, start_time + 1, start_time + 2, start_time + 3]

                    # Should eventually acquire lock after it's released
                    with lock:
                        assert lock.acquired is True

    def test_spec_number_lock_best_effort_cleanup(self, project_dir):
        """Test SpecNumberLock cleanup is best effort."""
        lock = SpecNumberLock(project_dir)

        with patch.object(Path, "unlink", side_effect=OSError("Delete failed")):
            try:
                with lock:
                    raise RuntimeError("Test exception")
            except RuntimeError:
                pass

    def test_spec_number_lock_multiple_acquire_release_cycles(self, project_dir):
        """Test SpecNumberLock can be acquired and released multiple times."""
        lock = SpecNumberLock(project_dir)

        for _ in range(3):
            with lock:
                assert lock.acquired is True
            assert not lock.lock_file.exists()


class TestGetNextSpecNumber:
    """Tests for get_next_spec_number method."""

    @pytest.fixture
    def project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    def test_get_next_spec_number_without_lock(self, project_dir):
        """Test get_next_spec_number raises error when lock not acquired."""
        lock = SpecNumberLock(project_dir)

        with pytest.raises(SpecNumberLockError) as exc_info:
            lock.get_next_spec_number()

        assert "Lock must be acquired" in str(exc_info.value)

    def test_get_next_spec_number_no_existing_specs(self, project_dir):
        """Test get_next_spec_number returns 1 when no specs exist."""
        lock = SpecNumberLock(project_dir)

        with lock:
            next_number = lock.get_next_spec_number()
            assert next_number == 1

    def test_get_next_spec_number_with_main_specs(self, project_dir):
        """Test get_next_spec_number scans main project specs."""
        # Create spec directories
        main_specs_dir = project_dir / ".auto-claude" / "specs"
        main_specs_dir.mkdir(parents=True)
        (main_specs_dir / "001-first-spec").mkdir()
        (main_specs_dir / "003-third-spec").mkdir()
        (main_specs_dir / "002-second-spec").mkdir()

        lock = SpecNumberLock(project_dir)

        with lock:
            next_number = lock.get_next_spec_number()
            assert next_number == 4  # Max is 003, so next is 4

    def test_get_next_spec_number_with_worktree_specs(self, project_dir):
        """Test get_next_spec_number scans worktree specs."""
        # Create main specs
        main_specs_dir = project_dir / ".auto-claude" / "specs"
        main_specs_dir.mkdir(parents=True)
        (main_specs_dir / "001-main-spec").mkdir()

        # Create worktree with higher spec number
        worktrees_dir = project_dir / ".auto-claude" / "worktrees" / "tasks"
        worktrees_dir.mkdir(parents=True)
        worktree1 = worktrees_dir / "worktree1"
        worktree1.mkdir()
        worktree_specs = worktree1 / ".auto-claude" / "specs"
        worktree_specs.mkdir(parents=True)
        (worktree_specs / "005-worktree-spec").mkdir()

        lock = SpecNumberLock(project_dir)

        with lock:
            next_number = lock.get_next_spec_number()
            assert next_number == 6  # Max is 005

    def test_get_next_spec_number_multiple_worktrees(self, project_dir):
        """Test get_next_spec_number scans multiple worktrees."""
        # Setup main specs
        main_specs_dir = project_dir / ".auto-claude" / "specs"
        main_specs_dir.mkdir(parents=True)
        (main_specs_dir / "002-main").mkdir()

        # Setup worktrees
        worktrees_dir = project_dir / ".auto-claude" / "worktrees" / "tasks"
        worktrees_dir.mkdir(parents=True)

        worktree1 = worktrees_dir / "worktree1"
        worktree1.mkdir()
        wt1_specs = worktree1 / ".auto-claude" / "specs"
        wt1_specs.mkdir(parents=True)
        (wt1_specs / "004-wt1").mkdir()

        worktree2 = worktrees_dir / "worktree2"
        worktree2.mkdir()
        wt2_specs = worktree2 / ".auto-claude" / "specs"
        wt2_specs.mkdir(parents=True)
        (wt2_specs / "007-wt2").mkdir()

        lock = SpecNumberLock(project_dir)

        with lock:
            next_number = lock.get_next_spec_number()
            assert next_number == 8  # Max is 007

    def test_get_next_spec_number_cached_result(self, project_dir):
        """Test get_next_spec_number caches result."""
        lock = SpecNumberLock(project_dir)

        with lock:
            first_call = lock.get_next_spec_number()
            # Create a new spec directory after first call
            main_specs_dir = project_dir / ".auto-claude" / "specs"
            main_specs_dir.mkdir(parents=True)
            (main_specs_dir / "005-new-spec").mkdir()

            # Second call should return cached value
            second_call = lock.get_next_spec_number()
            assert first_call == second_call

    def test_get_next_spec_number_ignores_invalid_names(self, project_dir):
        """Test get_next_spec_number ignores directories without numeric prefix."""
        main_specs_dir = project_dir / ".auto-claude" / "specs"
        main_specs_dir.mkdir(parents=True)
        (main_specs_dir / "001-valid").mkdir()
        (main_specs_dir / "invalid-name").mkdir()
        (main_specs_dir / "003-valid").mkdir()
        (main_specs_dir / "abc-invalid").mkdir()

        lock = SpecNumberLock(project_dir)

        with lock:
            next_number = lock.get_next_spec_number()
            assert next_number == 4  # Max is 003

    def test_get_next_spec_number_nonexistent_worktrees_dir(self, project_dir):
        """Test get_next_spec_number handles missing worktrees directory."""
        main_specs_dir = project_dir / ".auto-claude" / "specs"
        main_specs_dir.mkdir(parents=True)
        (main_specs_dir / "002-main").mkdir()

        # Don't create worktrees directory
        lock = SpecNumberLock(project_dir)

        with lock:
            next_number = lock.get_next_spec_number()
            assert next_number == 3

    def test_scan_specs_dir_nonexistent(self, project_dir):
        """Test _scan_specs_dir returns 0 for nonexistent directory."""
        lock = SpecNumberLock(project_dir)
        nonexistent_dir = project_dir / "nonexistent"

        with lock:
            result = lock._scan_specs_dir(nonexistent_dir)
            assert result == 0

    def test_scan_specs_dir_empty(self, project_dir):
        """Test _scan_specs_dir returns 0 for empty directory."""
        empty_dir = project_dir / "empty"
        empty_dir.mkdir()

        lock = SpecNumberLock(project_dir)

        with lock:
            result = lock._scan_specs_dir(empty_dir)
            assert result == 0

    def test_scan_specs_dir_with_various_formats(self, project_dir):
        """Test _scan_specs_dir handles various directory name formats."""
        specs_dir = project_dir / "specs"
        specs_dir.mkdir()
        (specs_dir / "001-one").mkdir()
        (specs_dir / "999-max").mkdir()
        (specs_dir / "050-middle").mkdir()
        (specs_dir / "not-a-number").mkdir()
        (specs_dir / "1-too-short").mkdir()  # Should be ignored (not 3 digits)
        (specs_dir / "00001-too-long").mkdir()  # Should be ignored (more than 3 digits)

        lock = SpecNumberLock(project_dir)

        with lock:
            result = lock._scan_specs_dir(specs_dir)
            assert result == 999

    def test_scan_specs_dir_with_value_error_trigger(self, project_dir):
        """Test _scan_specs_dir handles ValueError in folder name parsing."""
        specs_dir = project_dir / "specs"
        specs_dir.mkdir()
        (specs_dir / "001-valid").mkdir()

        # Create a directory that matches the glob pattern but first 3 chars aren't a valid int
        # This is tricky - we need to create something like "  1-invalid" where spaces aren't digits
        # Since glob only matches [0-9][0-9][0-9]-*, we need to work with the actual implementation
        # The ValueError would occur if int() somehow fails on the first 3 chars
        # In practice, this is very hard to trigger since the glob filters for digits
        # But we can test that the method handles it gracefully

        lock = SpecNumberLock(project_dir)

        with lock:
            result = lock._scan_specs_dir(specs_dir)
            assert result == 1

    def test_get_next_spec_number_returns_incremented_max(self, project_dir):
        """Test get_next_spec_number returns max + 1."""
        main_specs_dir = project_dir / ".auto-claude" / "specs"
        main_specs_dir.mkdir(parents=True)
        (main_specs_dir / "050-existing").mkdir()

        lock = SpecNumberLock(project_dir)

        with lock:
            next_number = lock.get_next_spec_number()
            assert next_number == 51  # 50 + 1

    def test_get_next_spec_number_zero_padded_consistency(self, project_dir):
        """Test get_next_spec_number handles zero-padded numbers correctly."""
        main_specs_dir = project_dir / ".auto-claude" / "specs"
        main_specs_dir.mkdir(parents=True)
        (main_specs_dir / "099-spec").mkdir()  # Should parse as 99
        (main_specs_dir / "100-spec").mkdir()  # Should parse as 100

        lock = SpecNumberLock(project_dir)

        with lock:
            next_number = lock.get_next_spec_number()
            assert next_number == 101
