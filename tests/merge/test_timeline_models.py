"""Tests for timeline_models"""

from datetime import datetime
from merge.timeline_models import (
    BranchPoint,
    FileTimeline,
    MainBranchEvent,
    MergeContext,
    TaskFileView,
    TaskIntent,
    WorktreeState,
)


def test_MainBranchEvent_to_dict():
    """Test MainBranchEvent.to_dict"""

    # Arrange
    instance = MainBranchEvent(
        commit_hash="abc123",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        content="file content",
        source="human",
        commit_message="Initial commit",
        author="Test Author",
        diff_summary="+10 -5 lines",
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result is not None
    assert result["commit_hash"] == "abc123"
    assert result["timestamp"] == "2024-01-01T12:00:00"
    assert result["content"] == "file content"
    assert result["source"] == "human"
    assert result["commit_message"] == "Initial commit"
    assert result["author"] == "Test Author"
    assert result["diff_summary"] == "+10 -5 lines"
    assert result["merged_from_task"] is None


def test_MainBranchEvent_from_dict():
    """Test MainBranchEvent.from_dict"""

    # Arrange
    data = {
        "commit_hash": "abc123",
        "timestamp": "2024-01-01T12:00:00",
        "content": "file content",
        "source": "human",
        "commit_message": "Initial commit",
        "author": "Test Author",
        "diff_summary": "+10 -5 lines",
    }

    # Act
    result = MainBranchEvent.from_dict(data)

    # Assert
    assert result is not None
    assert result.commit_hash == "abc123"
    assert result.content == "file content"
    assert result.source == "human"
    assert result.commit_message == "Initial commit"
    assert result.author == "Test Author"
    assert result.diff_summary == "+10 -5 lines"
    assert result.merged_from_task is None


def test_BranchPoint_to_dict():
    """Test BranchPoint.to_dict"""

    # Arrange
    instance = BranchPoint(
        commit_hash="abc123",
        content="baseline content",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result is not None
    assert result["commit_hash"] == "abc123"
    assert result["content"] == "baseline content"
    assert result["timestamp"] == "2024-01-01T12:00:00"


def test_BranchPoint_from_dict():
    """Test BranchPoint.from_dict"""

    # Arrange
    data = {
        "commit_hash": "abc123",
        "content": "baseline content",
        "timestamp": "2024-01-01T12:00:00",
    }

    # Act
    result = BranchPoint.from_dict(data)

    # Assert
    assert result is not None
    assert result.commit_hash == "abc123"
    assert result.content == "baseline content"


def test_WorktreeState_to_dict():
    """Test WorktreeState.to_dict"""

    # Arrange
    instance = WorktreeState(
        content="modified content",
        last_modified=datetime(2024, 1, 2, 12, 0, 0),
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result is not None
    assert result["content"] == "modified content"
    assert result["last_modified"] == "2024-01-02T12:00:00"


def test_WorktreeState_from_dict():
    """Test WorktreeState.from_dict"""

    # Arrange
    data = {
        "content": "modified content",
        "last_modified": "2024-01-02T12:00:00",
    }

    # Act
    result = WorktreeState.from_dict(data)

    # Assert
    assert result is not None
    assert result.content == "modified content"


def test_TaskIntent_to_dict():
    """Test TaskIntent.to_dict"""

    # Arrange
    instance = TaskIntent(
        title="Add feature",
        description="Implement new feature",
        from_plan=True,
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result is not None
    assert result["title"] == "Add feature"
    assert result["description"] == "Implement new feature"
    assert result["from_plan"] is True


def test_TaskIntent_from_dict():
    """Test TaskIntent.from_dict"""

    # Arrange
    data = {
        "title": "Add feature",
        "description": "Implement new feature",
        "from_plan": True,
    }

    # Act
    result = TaskIntent.from_dict(data)

    # Assert
    assert result is not None
    assert result.title == "Add feature"
    assert result.description == "Implement new feature"
    assert result.from_plan is True


def test_TaskFileView_to_dict():
    """Test TaskFileView.to_dict"""

    # Arrange
    branch_point = BranchPoint(
        commit_hash="abc123",
        content="baseline",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
    )
    worktree_state = WorktreeState(
        content="modified",
        last_modified=datetime(2024, 1, 2, 12, 0, 0),
    )
    task_intent = TaskIntent(title="Fix", description="Bug fix")

    instance = TaskFileView(
        task_id="task_001",
        branch_point=branch_point,
        worktree_state=worktree_state,
        task_intent=task_intent,
        commits_behind_main=2,
        status="active",
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result is not None
    assert result["task_id"] == "task_001"
    assert result["branch_point"]["commit_hash"] == "abc123"
    assert result["worktree_state"]["content"] == "modified"
    assert result["task_intent"]["title"] == "Fix"
    assert result["commits_behind_main"] == 2
    assert result["status"] == "active"


def test_TaskFileView_from_dict():
    """Test TaskFileView.from_dict"""

    # Arrange
    data = {
        "task_id": "task_001",
        "branch_point": {
            "commit_hash": "abc123",
            "content": "baseline",
            "timestamp": "2024-01-01T12:00:00",
        },
        "worktree_state": {
            "content": "modified",
            "last_modified": "2024-01-02T12:00:00",
        },
        "task_intent": {"title": "Fix", "description": "Bug fix", "from_plan": False},
        "commits_behind_main": 2,
        "status": "active",
        "merged_at": None,
    }

    # Act
    result = TaskFileView.from_dict(data)

    # Assert
    assert result is not None
    assert result.task_id == "task_001"
    assert result.branch_point.commit_hash == "abc123"
    assert result.worktree_state.content == "modified"
    assert result.task_intent.title == "Fix"
    assert result.commits_behind_main == 2
    assert result.status == "active"


def test_FileTimeline_add_main_event():
    """Test FileTimeline.add_main_event"""

    # Arrange
    instance = FileTimeline(file_path="test.py")
    event = MainBranchEvent(
        commit_hash="abc123",
        timestamp=datetime.now(),
        content="content",
        source="human",
    )

    # Act
    instance.add_main_event(event)

    # Assert
    assert len(instance.main_branch_history) == 1
    assert instance.main_branch_history[0] == event


def test_FileTimeline_add_task_view():
    """Test FileTimeline.add_task_view"""

    # Arrange
    instance = FileTimeline(file_path="test.py")
    task_view = TaskFileView(
        task_id="task_001",
        branch_point=BranchPoint(
            commit_hash="abc123",
            content="baseline",
            timestamp=datetime.now(),
        ),
    )

    # Act
    instance.add_task_view(task_view)

    # Assert
    assert "task_001" in instance.task_views
    assert instance.task_views["task_001"] == task_view


def test_FileTimeline_get_task_view():
    """Test FileTimeline.get_task_view"""

    # Arrange
    instance = FileTimeline(file_path="test.py")
    task_view = TaskFileView(
        task_id="task_001",
        branch_point=BranchPoint(
            commit_hash="abc123",
            content="baseline",
            timestamp=datetime.now(),
        ),
    )
    instance.add_task_view(task_view)

    # Act
    result = instance.get_task_view("task_001")

    # Assert
    assert result is not None
    assert result.task_id == "task_001"


def test_FileTimeline_get_active_tasks():
    """Test FileTimeline.get_active_tasks"""

    # Arrange
    instance = FileTimeline(file_path="test.py")
    task_view1 = TaskFileView(
        task_id="task_001",
        branch_point=BranchPoint(
            commit_hash="abc123",
            content="baseline",
            timestamp=datetime.now(),
        ),
        status="active",
    )
    task_view2 = TaskFileView(
        task_id="task_002",
        branch_point=BranchPoint(
            commit_hash="abc123",
            content="baseline",
            timestamp=datetime.now(),
        ),
        status="merged",
    )
    instance.add_task_view(task_view1)
    instance.add_task_view(task_view2)

    # Act
    result = instance.get_active_tasks()

    # Assert
    assert len(result) == 1
    assert result[0].task_id == "task_001"


def test_FileTimeline_get_events_since_commit():
    """Test FileTimeline.get_events_since_commit"""

    # Arrange
    instance = FileTimeline(file_path="test.py")
    event1 = MainBranchEvent(
        commit_hash="abc123",
        timestamp=datetime.now(),
        content="v1",
        source="human",
    )
    event2 = MainBranchEvent(
        commit_hash="def456",
        timestamp=datetime.now(),
        content="v2",
        source="human",
    )
    instance.add_main_event(event1)
    instance.add_main_event(event2)

    # Act
    result = instance.get_events_since_commit("abc123")

    # Assert
    assert len(result) == 1
    assert result[0].commit_hash == "def456"


def test_FileTimeline_get_current_main_state():
    """Test FileTimeline.get_current_main_state"""

    # Arrange
    instance = FileTimeline(file_path="test.py")
    event = MainBranchEvent(
        commit_hash="abc123",
        timestamp=datetime.now(),
        content="current",
        source="human",
    )
    instance.add_main_event(event)

    # Act
    result = instance.get_current_main_state()

    # Assert
    assert result is not None
    assert result.commit_hash == "abc123"
    assert result.content == "current"


def test_FileTimeline_to_dict():
    """Test FileTimeline.to_dict"""

    # Arrange
    instance = FileTimeline(file_path="test.py")
    event = MainBranchEvent(
        commit_hash="abc123",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        content="content",
        source="human",
    )
    instance.add_main_event(event)

    # Act
    result = instance.to_dict()

    # Assert
    assert result is not None
    assert result["file_path"] == "test.py"
    assert len(result["main_branch_history"]) == 1
    assert result["main_branch_history"][0]["commit_hash"] == "abc123"


def test_FileTimeline_from_dict():
    """Test FileTimeline.from_dict"""

    # Arrange
    data = {
        "file_path": "test.py",
        "main_branch_history": [
            {
                "commit_hash": "abc123",
                "timestamp": "2024-01-01T12:00:00",
                "content": "content",
                "source": "human",
                "merged_from_task": None,
                "commit_message": "",
                "author": None,
                "diff_summary": None,
            }
        ],
        "task_views": {},
        "created_at": "2024-01-01T12:00:00",
        "last_updated": "2024-01-01T12:00:00",
    }

    # Act
    result = FileTimeline.from_dict(data)

    # Assert
    assert result is not None
    assert result.file_path == "test.py"
    assert len(result.main_branch_history) == 1
    assert result.main_branch_history[0].commit_hash == "abc123"


def test_MergeContext_to_dict():
    """Test MergeContext.to_dict"""

    # Arrange
    instance = MergeContext(
        file_path="test.py",
        task_id="task_001",
        task_intent=TaskIntent(title="Fix", description="Bug fix"),
        task_branch_point=BranchPoint(
            commit_hash="abc123",
            content="baseline",
            timestamp=datetime.now(),
        ),
        main_evolution=[],
        task_worktree_content="modified",
        current_main_content="main content",
        current_main_commit="def456",
        other_pending_tasks=[],
        total_commits_behind=2,
        total_pending_tasks=0,
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result is not None
    assert result["file_path"] == "test.py"
    assert result["task_id"] == "task_001"
    assert result["task_intent"]["title"] == "Fix"
    assert result["total_commits_behind"] == 2
