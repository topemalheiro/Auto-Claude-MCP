"""Tests for plan"""

from implementation_plan.plan import ImplementationPlan
from implementation_plan.enums import PhaseType, SubtaskStatus, WorkflowType
from implementation_plan.phase import Phase
from implementation_plan.subtask import Subtask
from implementation_plan.verification import Verification, VerificationType
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import pytest
import json


@pytest.fixture
def sample_plan():
    """Create a sample ImplementationPlan for testing"""
    subtask1 = Subtask(
        id="1",
        description="Task 1",
        status=SubtaskStatus.COMPLETED,
        verification=Verification(type=VerificationType.COMMAND, run="pytest")
    )
    subtask2 = Subtask(
        id="2",
        description="Task 2",
        status=SubtaskStatus.PENDING
    )

    phase1 = Phase(
        phase=1,
        name="Setup",
        type=PhaseType.INVESTIGATION,
        subtasks=[subtask1],
        depends_on=[],
        parallel_safe=False
    )

    phase2 = Phase(
        phase=2,
        name="Implementation",
        type=PhaseType.IMPLEMENTATION,
        subtasks=[subtask2],
        depends_on=[1],
        parallel_safe=True
    )

    return ImplementationPlan(
        feature="Test Feature",
        workflow_type=WorkflowType.FEATURE,
        services_involved=["api", "web"],
        phases=[phase1, phase2],
        final_acceptance=["Tests pass", "Documentation complete"],
        status="in_progress",
        planStatus="in_progress"
    )


def test_ImplementationPlan_to_dict(sample_plan):
    """Test ImplementationPlan.to_dict"""

    # Act
    result = sample_plan.to_dict()

    # Assert
    assert result["feature"] == "Test Feature"
    assert result["workflow_type"] == "feature"
    assert result["services_involved"] == ["api", "web"]
    assert len(result["phases"]) == 2
    assert result["final_acceptance"] == ["Tests pass", "Documentation complete"]
    assert result["status"] == "in_progress"
    assert result["planStatus"] == "in_progress"


def test_ImplementationPlan_from_dict():
    """Test ImplementationPlan.from_dict"""

    # Arrange
    data = {
        "feature": "From Dict Feature",
        "workflow_type": "investigation",
        "services_involved": ["database"],
        "phases": [
            {
                "phase": 1,
                "name": "Phase 1",
                "type": "implementation",
                "subtasks": [
                    {"id": "1", "description": "Task 1", "status": "pending"}
                ]
            }
        ],
        "final_acceptance": ["Done"],
        "status": "backlog",
        "planStatus": "pending",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-02T00:00:00"
    }

    # Act
    result = ImplementationPlan.from_dict(data)

    # Assert
    assert result.feature == "From Dict Feature"
    assert result.workflow_type == WorkflowType.INVESTIGATION
    assert result.services_involved == ["database"]
    assert len(result.phases) == 1
    assert result.phases[0].name == "Phase 1"
    assert result.final_acceptance == ["Done"]
    assert result.status == "backlog"
    assert result.planStatus == "pending"
    assert result.created_at == "2024-01-01T00:00:00"
    assert result.updated_at == "2024-01-02T00:00:00"


def test_ImplementationPlan_from_dict_with_title():
    """Test ImplementationPlan.from_dict supports 'title' field"""

    # Arrange
    data = {
        "title": "Title Feature",  # Using 'title' instead of 'feature'
        "workflow_type": "feature",
        "phases": []
    }

    # Act
    result = ImplementationPlan.from_dict(data)

    # Assert
    assert result.feature == "Title Feature"


def test_ImplementationPlan_from_dict_unknown_workflow():
    """Test ImplementationPlan.from_dict with unknown workflow type"""

    # Arrange
    data = {
        "feature": "Unknown Workflow",
        "workflow_type": "unknown_type",
        "phases": []
    }

    # Act
    with patch('builtins.print'):  # Suppress warning print
        result = ImplementationPlan.from_dict(data)

    # Assert
    assert result.feature == "Unknown Workflow"
    assert result.workflow_type == WorkflowType.FEATURE  # Defaults to FEATURE


def test_ImplementationPlan_save(sample_plan, tmp_path):
    """Test ImplementationPlan.save"""

    # Arrange
    path = tmp_path / "plan.json"

    # Act
    sample_plan.save(path)

    # Assert
    assert path.exists()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["feature"] == "Test Feature"
    assert data["updated_at"] is not None  # Timestamp was updated


@pytest.mark.asyncio
async def test_ImplementationPlan_async_save(sample_plan, tmp_path):
    """Test ImplementationPlan.async_save"""

    # Arrange
    path = tmp_path / "async_plan.json"
    old_updated_at = sample_plan.updated_at

    # Act
    await sample_plan.async_save(path)

    # Assert
    assert path.exists()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["feature"] == "Test Feature"
    assert data["updated_at"] != old_updated_at  # Timestamp was updated


@pytest.mark.asyncio
async def test_ImplementationPlan_async_save_rollback_on_error(sample_plan, tmp_path):
    """Test ImplementationPlan.async_save rolls back on write error"""

    # Arrange
    path = tmp_path / "fail_plan.json"
    old_status = sample_plan.status

    # Act & Assert
    # Patch at the module where it's imported
    with patch('implementation_plan.plan.write_json_atomic', side_effect=IOError("Write failed")):
        with pytest.raises(IOError):
            await sample_plan.async_save(path)

    # Status should be restored (not modified by _update_timestamps_and_status)
    # Actually, the rollback restores from old_state, so status should be preserved
    assert sample_plan.status == old_status


def test_ImplementationPlan_update_status_from_subtasks(sample_plan):
    """Test ImplementationPlan.update_status_from_subtasks"""

    # Plan has 1 completed and 1 pending subtask
    # Act
    sample_plan.update_status_from_subtasks()

    # Assert - some progress, so in_progress
    assert sample_plan.status == "in_progress"
    assert sample_plan.planStatus == "in_progress"


def test_ImplementationPlan_update_status_all_complete(sample_plan):
    """Test update_status_from_subtasks when all subtasks complete"""

    # Arrange - mark all as complete
    for subtask in sample_plan.phases[0].subtasks + sample_plan.phases[1].subtasks:
        subtask.status = SubtaskStatus.COMPLETED

    # Act
    sample_plan.update_status_from_subtasks()

    # Assert - all done, waiting for QA
    assert sample_plan.status == "ai_review"
    assert sample_plan.planStatus == "review"


def test_ImplementationPlan_update_status_all_complete_with_qa(sample_plan):
    """Test update_status_from_subtasks with QA signoff"""

    # Arrange - all complete with QA approval
    for subtask in sample_plan.phases[0].subtasks + sample_plan.phases[1].subtasks:
        subtask.status = SubtaskStatus.COMPLETED
    sample_plan.qa_signoff = {"status": "approved", "reviewed_by": "test"}

    # Act
    sample_plan.update_status_from_subtasks()

    # Assert - QA approved, ready for human review
    assert sample_plan.status == "human_review"
    assert sample_plan.planStatus == "review"


def test_ImplementationPlan_load(tmp_path):
    """Test ImplementationPlan.load"""

    # Arrange
    data = {
        "feature": "Load Test",
        "workflow_type": "feature",
        "phases": [
            {
                "phase": 1,
                "name": "Phase 1",
                "type": "implementation",
                "subtasks": [
                    {"id": "1", "description": "Task 1", "status": "pending"}
                ]
            }
        ],
        "final_acceptance": []
    }
    path = tmp_path / "load_test.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    # Act
    result = ImplementationPlan.load(path)

    # Assert
    assert result.feature == "Load Test"
    assert len(result.phases) == 1


def test_ImplementationPlan_get_available_phases(sample_plan):
    """Test ImplementationPlan.get_available_phases"""

    # Phase 1 is complete, Phase 2 depends on Phase 1
    # Act
    result = sample_plan.get_available_phases()

    # Assert - Phase 2 is available (its dependency Phase 1 is complete)
    assert len(result) == 1
    assert result[0].phase == 2


def test_ImplementationPlan_get_available_phases_blocked(sample_plan):
    """Test get_available_phases with blocked phases"""

    # Arrange - mark Phase 1 as incomplete
    sample_plan.phases[0].subtasks[0].status = SubtaskStatus.PENDING

    # Act
    result = sample_plan.get_available_phases()

    # Assert - Phase 1 is available (no dependencies), Phase 2 is blocked
    assert len(result) == 1
    assert result[0].phase == 1


def test_ImplementationPlan_get_next_subtask(sample_plan):
    """Test ImplementationPlan.get_next_subtask"""

    # Act
    result = sample_plan.get_next_subtask()

    # Assert - Should return Phase 2 and its pending subtask
    assert result is not None
    phase, subtask = result
    assert phase.phase == 2
    assert subtask.id == "2"


def test_ImplementationPlan_get_next_subtask_none_available(sample_plan):
    """Test get_next_subtask when no subtasks available"""

    # Arrange - mark all as complete
    for phase in sample_plan.phases:
        for subtask in phase.subtasks:
            subtask.status = SubtaskStatus.COMPLETED

    # Act
    result = sample_plan.get_next_subtask()

    # Assert
    assert result is None


def test_ImplementationPlan_get_progress(sample_plan):
    """Test ImplementationPlan.get_progress"""

    # Act
    result = sample_plan.get_progress()

    # Assert
    assert result["total_phases"] == 2
    assert result["completed_phases"] == 1  # Phase 1 is complete
    assert result["total_subtasks"] == 2
    assert result["completed_subtasks"] == 1
    assert result["failed_subtasks"] == 0
    assert result["percent_complete"] == 50.0
    assert result["is_complete"] is False


def test_ImplementationPlan_get_progress_empty():
    """Test get_progress with no subtasks"""

    # Arrange
    plan = ImplementationPlan(feature="Empty", phases=[])

    # Act
    result = plan.get_progress()

    # Assert
    assert result["total_phases"] == 0
    assert result["completed_phases"] == 0
    assert result["total_subtasks"] == 0
    assert result["completed_subtasks"] == 0
    assert result["percent_complete"] == 0
    assert result["is_complete"] is True  # Empty plan is considered complete


def test_ImplementationPlan_get_status_summary(sample_plan, capsys):
    """Test ImplementationPlan.get_status_summary"""

    # Act
    result = sample_plan.get_status_summary()

    # Assert
    assert "Test Feature" in result
    assert "Progress: 1/2 subtasks" in result
    assert "Phases: 1/2 complete" in result
    assert "Phase 2 (Implementation)" in result


def test_ImplementationPlan_get_status_summary_complete(sample_plan):
    """Test get_status_summary when complete"""

    # Arrange - mark all as complete
    for phase in sample_plan.phases:
        for subtask in phase.subtasks:
            subtask.status = SubtaskStatus.COMPLETED

    # Act
    result = sample_plan.get_status_summary()

    # Assert
    assert "COMPLETE" in result


def test_ImplementationPlan_get_status_summary_blocked(sample_plan):
    """Test get_status_summary when blocked"""

    # Arrange - mark Phase 1 as incomplete so Phase 2 is blocked
    sample_plan.phases[0].subtasks[0].status = SubtaskStatus.PENDING

    # Act
    result = sample_plan.get_status_summary()

    # Assert - Phase 1 is available (not complete yet), so it should show next task
    # Not BLOCKED since Phase 1 itself is available
    assert "Phase 1 (Setup) - Task 1" in result


def test_ImplementationPlan_add_followup_phase(sample_plan):
    """Test ImplementationPlan.add_followup_phase"""

    # Arrange
    new_subtasks = [
        Subtask(id="3", description="New task", status=SubtaskStatus.PENDING)
    ]

    # Act
    result = sample_plan.add_followup_phase(
        name="Follow-up Phase",
        subtasks=new_subtasks,
        phase_type=PhaseType.IMPLEMENTATION,
        parallel_safe=False
    )

    # Assert
    assert result.phase == 3  # Next phase number
    assert result.name == "Follow-up Phase"
    assert len(result.depends_on) == 2  # Depends on phases 1 and 2
    assert len(sample_plan.phases) == 3
    assert sample_plan.phases[2] == result
    assert sample_plan.status == "in_progress"
    assert sample_plan.planStatus == "in_progress"
    assert sample_plan.qa_signoff is None


def test_ImplementationPlan_add_followup_phase_empty_plan():
    """Test add_followup_phase on empty plan"""

    # Arrange
    plan = ImplementationPlan(feature="Empty Plan", phases=[])
    new_subtasks = [Subtask(id="1", description="First task")]

    # Act
    result = plan.add_followup_phase("First Phase", new_subtasks)

    # Assert
    assert result.phase == 1
    assert len(result.depends_on) == 0


def test_ImplementationPlan_reset_for_followup(sample_plan):
    """Test ImplementationPlan.reset_for_followup"""

    # Arrange - mark as complete
    for phase in sample_plan.phases:
        for subtask in phase.subtasks:
            subtask.status = SubtaskStatus.COMPLETED
    sample_plan.status = "ai_review"
    sample_plan.planStatus = "review"
    sample_plan.qa_signoff = {"status": "approved"}
    sample_plan.recoveryNote = "Some note"

    # Act
    result = sample_plan.reset_for_followup()

    # Assert
    assert result is True
    assert sample_plan.status == "in_progress"
    assert sample_plan.planStatus == "in_progress"
    assert sample_plan.qa_signoff is None
    assert sample_plan.recoveryNote is None


def test_ImplementationPlan_reset_for_followup_already_in_progress(sample_plan):
    """Test reset_for_followup when already in progress"""

    # Arrange - already in progress
    sample_plan.status = "in_progress"

    # Act
    result = sample_plan.reset_for_followup()

    # Assert
    assert result is False  # No reset needed


def test_ImplementationPlan_reset_for_followup_with_pending_subtasks():
    """Test reset_for_followup with pending subtasks"""

    # Arrange - has pending subtasks but status says complete
    plan = ImplementationPlan(
        feature="Test",
        phases=[
            Phase(
                phase=1,
                name="Phase 1",
                subtasks=[Subtask(id="1", description="Task", status=SubtaskStatus.PENDING)]
            )
        ],
        status="done"
    )

    # Act
    result = plan.reset_for_followup()

    # Assert - should reset because subtasks aren't actually done
    assert result is True
    assert plan.status == "in_progress"
