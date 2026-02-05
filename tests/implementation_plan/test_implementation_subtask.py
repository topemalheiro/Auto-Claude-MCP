"""
Comprehensive tests for implementation_plan.subtask module.
"""

from datetime import datetime
from unittest.mock import patch
import pytest

from implementation_plan.subtask import Subtask
from implementation_plan.enums import SubtaskStatus
from implementation_plan.verification import Verification, VerificationType


class TestSubtaskInstantiation:
    """Tests for Subtask dataclass instantiation and defaults."""

    def test_subtask_minimal_creation(self):
        """Test creating a Subtask with minimal required fields."""
        subtask = Subtask(id="1", description="Test subtask")

        assert subtask.id == "1"
        assert subtask.description == "Test subtask"
        assert subtask.status == SubtaskStatus.PENDING
        assert subtask.service is None
        assert subtask.all_services is False
        assert subtask.files_to_modify == []
        assert subtask.files_to_create == []
        assert subtask.patterns_from == []
        assert subtask.verification is None
        assert subtask.expected_output is None
        assert subtask.actual_output is None
        assert subtask.started_at is None
        assert subtask.completed_at is None
        assert subtask.session_id is None
        assert subtask.critique_result is None

    def test_subtask_with_all_fields(self):
        """Test creating a Subtask with all fields populated."""
        verification = Verification(
            type=VerificationType.COMMAND,
            run="pytest tests/"
        )

        subtask = Subtask(
            id="2",
            description="Complex subtask",
            status=SubtaskStatus.IN_PROGRESS,
            service="backend",
            all_services=False,
            files_to_modify=["app.py", "models.py"],
            files_to_create=["test_app.py"],
            patterns_from=["existing_feature.py"],
            verification=verification,
            expected_output="All tests pass",
            actual_output="Tests passed",
            started_at="2024-01-01T10:00:00",
            completed_at="2024-01-01T11:00:00",
            session_id=1,
            critique_result={"score": 0.9, "issues": []}
        )

        assert subtask.id == "2"
        assert subtask.description == "Complex subtask"
        assert subtask.status == SubtaskStatus.IN_PROGRESS
        assert subtask.service == "backend"
        assert subtask.all_services is False
        assert subtask.files_to_modify == ["app.py", "models.py"]
        assert subtask.files_to_create == ["test_app.py"]
        assert subtask.patterns_from == ["existing_feature.py"]
        assert subtask.verification.type == VerificationType.COMMAND
        assert subtask.expected_output == "All tests pass"
        assert subtask.actual_output == "Tests passed"
        assert subtask.started_at == "2024-01-01T10:00:00"
        assert subtask.completed_at == "2024-01-01T11:00:00"
        assert subtask.session_id == 1
        assert subtask.critique_result == {"score": 0.9, "issues": []}

    def test_subtask_all_services_flag(self):
        """Test Subtask with all_services flag for integration tasks."""
        subtask = Subtask(
            id="3",
            description="Integration task",
            all_services=True
        )

        assert subtask.all_services is True
        assert subtask.service is None

    def test_subtask_default_list_factories(self):
        """Test that list fields use default_factory correctly."""
        subtask1 = Subtask(id="1", description="Test 1")
        subtask2 = Subtask(id="2", description="Test 2")

        # Lists should be independent (not shared)
        subtask1.files_to_modify.append("file1.py")
        subtask2.files_to_modify.append("file2.py")

        assert subtask1.files_to_modify == ["file1.py"]
        assert subtask2.files_to_modify == ["file2.py"]
        assert subtask1.files_to_create == []
        assert subtask2.files_to_create == []


class TestSubtaskToDict:
    """Tests for Subtask.to_dict() method."""

    def test_to_dict_minimal(self):
        """Test to_dict with minimal Subtask."""
        subtask = Subtask(id="1", description="Test")
        result = subtask.to_dict()

        assert result == {
            "id": "1",
            "description": "Test",
            "status": "pending"
        }

    def test_to_dict_with_status(self):
        """Test to_dict with different status values."""
        for status in [SubtaskStatus.PENDING, SubtaskStatus.IN_PROGRESS,
                       SubtaskStatus.COMPLETED, SubtaskStatus.BLOCKED,
                       SubtaskStatus.FAILED]:
            subtask = Subtask(id="1", description="Test", status=status)
            result = subtask.to_dict()
            assert result["status"] == status.value

    def test_to_dict_with_service(self):
        """Test to_dict includes service field."""
        subtask = Subtask(
            id="1",
            description="Test",
            service="frontend"
        )
        result = subtask.to_dict()

        assert result["service"] == "frontend"

    def test_to_dict_with_all_services(self):
        """Test to_dict includes all_services field when True."""
        subtask = Subtask(
            id="1",
            description="Test",
            all_services=True
        )
        result = subtask.to_dict()

        assert result["all_services"] is True

    def test_to_dict_excludes_all_services_when_false(self):
        """Test to_dict excludes all_services when False."""
        subtask = Subtask(
            id="1",
            description="Test",
            all_services=False
        )
        result = subtask.to_dict()

        assert "all_services" not in result

    def test_to_dict_with_files(self):
        """Test to_dict includes file lists."""
        subtask = Subtask(
            id="1",
            description="Test",
            files_to_modify=["app.py", "models.py"],
            files_to_create=["test_app.py"],
            patterns_from=["existing.py"]
        )
        result = subtask.to_dict()

        assert result["files_to_modify"] == ["app.py", "models.py"]
        assert result["files_to_create"] == ["test_app.py"]
        assert result["patterns_from"] == ["existing.py"]

    def test_to_dict_with_verification(self):
        """Test to_dict includes verification."""
        verification = Verification(
            type=VerificationType.COMMAND,
            run="pytest tests/"
        )
        subtask = Subtask(
            id="1",
            description="Test",
            verification=verification
        )
        result = subtask.to_dict()

        assert result["verification"] == {
            "type": "command",
            "run": "pytest tests/"
        }

    def test_to_dict_with_expected_output(self):
        """Test to_dict includes expected_output."""
        subtask = Subtask(
            id="1",
            description="Test",
            expected_output="Knowledge gathered"
        )
        result = subtask.to_dict()

        assert result["expected_output"] == "Knowledge gathered"

    def test_to_dict_with_actual_output(self):
        """Test to_dict includes actual_output."""
        subtask = Subtask(
            id="1",
            description="Test",
            actual_output="Discovery completed"
        )
        result = subtask.to_dict()

        assert result["actual_output"] == "Discovery completed"

    def test_to_dict_with_timestamps(self):
        """Test to_dict includes timestamp fields."""
        subtask = Subtask(
            id="1",
            description="Test",
            started_at="2024-01-01T10:00:00",
            completed_at="2024-01-01T11:00:00"
        )
        result = subtask.to_dict()

        assert result["started_at"] == "2024-01-01T10:00:00"
        assert result["completed_at"] == "2024-01-01T11:00:00"

    def test_to_dict_with_session_id(self):
        """Test to_dict includes session_id."""
        subtask = Subtask(
            id="1",
            description="Test",
            session_id=5
        )
        result = subtask.to_dict()

        assert result["session_id"] == 5

    def test_to_dict_with_session_id_zero(self):
        """Test to_dict includes session_id when value is 0."""
        subtask = Subtask(
            id="1",
            description="Test",
            session_id=0
        )
        result = subtask.to_dict()

        assert result["session_id"] == 0

    def test_to_dict_excludes_session_id_when_none(self):
        """Test to_dict excludes session_id when None."""
        subtask = Subtask(
            id="1",
            description="Test",
            session_id=None
        )
        result = subtask.to_dict()

        assert "session_id" not in result

    def test_to_dict_with_critique_result(self):
        """Test to_dict includes critique_result."""
        subtask = Subtask(
            id="1",
            description="Test",
            critique_result={"score": 0.85, "suggestions": ["improve x"]}
        )
        result = subtask.to_dict()

        assert result["critique_result"] == {"score": 0.85, "suggestions": ["improve x"]}

    def test_to_dict_complete_subtask(self):
        """Test to_dict with all fields populated."""
        verification = Verification(
            type=VerificationType.API,
            url="http://localhost:8000/health",
            method="GET",
            expect_status=200
        )

        subtask = Subtask(
            id="complete-1",
            description="Complete subtask with all fields",
            status=SubtaskStatus.COMPLETED,
            service="backend",
            all_services=False,
            files_to_modify=["views.py"],
            files_to_create=["test_views.py"],
            patterns_from=["models.py"],
            verification=verification,
            expected_output="API responds correctly",
            actual_output="All checks passed",
            started_at="2024-01-01T09:00:00",
            completed_at="2024-01-01T10:30:00",
            session_id=2,
            critique_result={"quality": "high"}
        )
        result = subtask.to_dict()

        assert result["id"] == "complete-1"
        assert result["description"] == "Complete subtask with all fields"
        assert result["status"] == "completed"
        assert result["service"] == "backend"
        assert result["files_to_modify"] == ["views.py"]
        assert result["files_to_create"] == ["test_views.py"]
        assert result["patterns_from"] == ["models.py"]
        assert result["verification"]["type"] == "api"
        assert result["expected_output"] == "API responds correctly"
        assert result["actual_output"] == "All checks passed"
        assert result["started_at"] == "2024-01-01T09:00:00"
        assert result["completed_at"] == "2024-01-01T10:30:00"
        assert result["session_id"] == 2
        assert result["critique_result"] == {"quality": "high"}


class TestSubtaskFromDict:
    """Tests for Subtask.from_dict() class method."""

    def test_from_dict_minimal(self):
        """Test from_dict with minimal data."""
        data = {
            "id": "1",
            "description": "Test subtask"
        }
        subtask = Subtask.from_dict(data)

        assert subtask.id == "1"
        assert subtask.description == "Test subtask"
        assert subtask.status == SubtaskStatus.PENDING
        assert subtask.service is None
        assert subtask.all_services is False

    def test_from_dict_with_status(self):
        """Test from_dict with status field."""
        data = {
            "id": "1",
            "description": "Test",
            "status": "in_progress"
        }
        subtask = Subtask.from_dict(data)

        assert subtask.status == SubtaskStatus.IN_PROGRESS

    def test_from_dict_status_defaults_to_pending(self):
        """Test from_dict defaults status to PENDING when missing."""
        data = {
            "id": "1",
            "description": "Test"
        }
        subtask = Subtask.from_dict(data)

        assert subtask.status == SubtaskStatus.PENDING

    def test_from_dict_with_all_statuses(self):
        """Test from_dict with all possible status values."""
        status_values = ["pending", "in_progress", "completed", "blocked", "failed"]

        for status_val in status_values:
            data = {
                "id": "1",
                "description": "Test",
                "status": status_val
            }
            subtask = Subtask.from_dict(data)
            assert subtask.status.value == status_val

    def test_from_dict_with_service(self):
        """Test from_dict with service field."""
        data = {
            "id": "1",
            "description": "Test",
            "service": "worker"
        }
        subtask = Subtask.from_dict(data)

        assert subtask.service == "worker"

    def test_from_dict_with_all_services_true(self):
        """Test from_dict with all_services=True."""
        data = {
            "id": "1",
            "description": "Test",
            "all_services": True
        }
        subtask = Subtask.from_dict(data)

        assert subtask.all_services is True

    def test_from_dict_with_all_services_false(self):
        """Test from_dict with all_services=False."""
        data = {
            "id": "1",
            "description": "Test",
            "all_services": False
        }
        subtask = Subtask.from_dict(data)

        assert subtask.all_services is False

    def test_from_dict_all_services_defaults_to_false(self):
        """Test from_dict defaults all_services to False when missing."""
        data = {
            "id": "1",
            "description": "Test"
        }
        subtask = Subtask.from_dict(data)

        assert subtask.all_services is False

    def test_from_dict_with_files(self):
        """Test from_dict with file lists."""
        data = {
            "id": "1",
            "description": "Test",
            "files_to_modify": ["a.py", "b.py"],
            "files_to_create": ["test_a.py"],
            "patterns_from": ["template.py"]
        }
        subtask = Subtask.from_dict(data)

        assert subtask.files_to_modify == ["a.py", "b.py"]
        assert subtask.files_to_create == ["test_a.py"]
        assert subtask.patterns_from == ["template.py"]

    def test_from_dict_with_empty_file_lists(self):
        """Test from_dict with empty file lists."""
        data = {
            "id": "1",
            "description": "Test",
            "files_to_modify": [],
            "files_to_create": [],
            "patterns_from": []
        }
        subtask = Subtask.from_dict(data)

        assert subtask.files_to_modify == []
        assert subtask.files_to_create == []
        assert subtask.patterns_from == []

    def test_from_dict_with_verification(self):
        """Test from_dict with verification."""
        data = {
            "id": "1",
            "description": "Test",
            "verification": {
                "type": "command",
                "run": "pytest tests/"
            }
        }
        subtask = Subtask.from_dict(data)

        assert subtask.verification is not None
        assert subtask.verification.type == VerificationType.COMMAND
        assert subtask.verification.run == "pytest tests/"

    def test_from_dict_with_verification_none_type(self):
        """Test from_dict with verification type=none."""
        data = {
            "id": "1",
            "description": "Test",
            "verification": {
                "type": "none"
            }
        }
        subtask = Subtask.from_dict(data)

        assert subtask.verification is not None
        assert subtask.verification.type == VerificationType.NONE

    def test_from_dict_with_expected_output(self):
        """Test from_dict with expected_output."""
        data = {
            "id": "1",
            "description": "Test",
            "expected_output": "Some knowledge"
        }
        subtask = Subtask.from_dict(data)

        assert subtask.expected_output == "Some knowledge"

    def test_from_dict_with_actual_output(self):
        """Test from_dict with actual_output."""
        data = {
            "id": "1",
            "description": "Test",
            "actual_output": "Discovery result"
        }
        subtask = Subtask.from_dict(data)

        assert subtask.actual_output == "Discovery result"

    def test_from_dict_with_timestamps(self):
        """Test from_dict with timestamps."""
        data = {
            "id": "1",
            "description": "Test",
            "started_at": "2024-01-01T10:00:00",
            "completed_at": "2024-01-01T11:00:00"
        }
        subtask = Subtask.from_dict(data)

        assert subtask.started_at == "2024-01-01T10:00:00"
        assert subtask.completed_at == "2024-01-01T11:00:00"

    def test_from_dict_with_session_id(self):
        """Test from_dict with session_id."""
        data = {
            "id": "1",
            "description": "Test",
            "session_id": 10
        }
        subtask = Subtask.from_dict(data)

        assert subtask.session_id == 10

    def test_from_dict_with_critique_result(self):
        """Test from_dict with critique_result."""
        data = {
            "id": "1",
            "description": "Test",
            "critique_result": {"score": 0.95, "issues": []}
        }
        subtask = Subtask.from_dict(data)

        assert subtask.critique_result == {"score": 0.95, "issues": []}

    def test_from_dict_complete_data(self):
        """Test from_dict with complete subtask data."""
        data = {
            "id": "full-1",
            "description": "Full subtask",
            "status": "completed",
            "service": "frontend",
            "all_services": False,
            "files_to_modify": ["App.tsx"],
            "files_to_create": ["App.test.tsx"],
            "patterns_from": ["Button.tsx"],
            "verification": {
                "type": "component",
                "run": "npm test -- App.test.tsx",
                "scenario": "Verify App component"
            },
            "expected_output": "Component renders",
            "actual_output": "Component rendered successfully",
            "started_at": "2024-01-01T08:00:00",
            "completed_at": "2024-01-01T09:00:00",
            "session_id": 3,
            "critique_result": {"passes": True}
        }
        subtask = Subtask.from_dict(data)

        assert subtask.id == "full-1"
        assert subtask.description == "Full subtask"
        assert subtask.status == SubtaskStatus.COMPLETED
        assert subtask.service == "frontend"
        assert subtask.files_to_modify == ["App.tsx"]
        assert subtask.files_to_create == ["App.test.tsx"]
        assert subtask.patterns_from == ["Button.tsx"]
        assert subtask.verification.type == VerificationType.COMPONENT
        assert subtask.expected_output == "Component renders"
        assert subtask.actual_output == "Component rendered successfully"
        assert subtask.started_at == "2024-01-01T08:00:00"
        assert subtask.completed_at == "2024-01-01T09:00:00"
        assert subtask.session_id == 3
        assert subtask.critique_result == {"passes": True}


class TestSubtaskSerializationRoundtrip:
    """Tests for Subtask serialization/deserialization roundtrip."""

    def test_to_dict_from_dict_roundtrip(self):
        """Test that to_dict/from_dict roundtrip preserves data."""
        original = Subtask(
            id="roundtrip-1",
            description="Roundtrip test",
            status=SubtaskStatus.IN_PROGRESS,
            service="backend",
            all_services=False,
            files_to_modify=["api.py"],
            files_to_create=["test_api.py"],
            patterns_from=["models.py"],
            verification=Verification(
                type=VerificationType.COMMAND,
                run="pytest"
            ),
            expected_output="Expected",
            actual_output="Actual",
            started_at="2024-01-01T10:00:00",
            completed_at=None,
            session_id=1,
            critique_result={"key": "value"}
        )

        # Serialize to dict
        data = original.to_dict()

        # Deserialize from dict
        restored = Subtask.from_dict(data)

        # Verify all fields match
        assert restored.id == original.id
        assert restored.description == original.description
        assert restored.status == original.status
        assert restored.service == original.service
        assert restored.all_services == original.all_services
        assert restored.files_to_modify == original.files_to_modify
        assert restored.files_to_create == original.files_to_create
        assert restored.patterns_from == original.patterns_from
        assert restored.verification.type == original.verification.type
        assert restored.verification.run == original.verification.run
        assert restored.expected_output == original.expected_output
        assert restored.actual_output == original.actual_output
        assert restored.started_at == original.started_at
        assert restored.completed_at == original.completed_at
        assert restored.session_id == original.session_id
        assert restored.critique_result == original.critique_result

    def test_roundtrip_with_minimal_subtask(self):
        """Test roundtrip with minimal subtask data."""
        original = Subtask(id="1", description="Minimal")
        data = original.to_dict()
        restored = Subtask.from_dict(data)

        assert restored.id == original.id
        assert restored.description == original.description
        assert restored.status == original.status


class TestSubtaskStart:
    """Tests for Subtask.start() method."""

    def test_start_sets_status_to_in_progress(self):
        """Test start() sets status to IN_PROGRESS."""
        subtask = Subtask(id="1", description="Test")
        subtask.start(session_id=1)

        assert subtask.status == SubtaskStatus.IN_PROGRESS

    def test_start_sets_timestamp(self):
        """Test start() sets started_at timestamp."""
        subtask = Subtask(id="1", description="Test")

        with patch("implementation_plan.subtask.datetime") as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"
            subtask.start(session_id=1)

        assert subtask.started_at is not None
        # Verify it's an ISO format string
        datetime.fromisoformat(subtask.started_at)

    def test_start_sets_session_id(self):
        """Test start() sets session_id."""
        subtask = Subtask(id="1", description="Test")
        subtask.start(session_id=5)

        assert subtask.session_id == 5

    def test_start_clears_previous_completed_at(self):
        """Test start() clears completed_at from previous runs."""
        subtask = Subtask(
            id="1",
            description="Test",
            completed_at="2024-01-01T10:00:00"
        )
        subtask.start(session_id=1)

        assert subtask.completed_at is None

    def test_start_clears_previous_actual_output(self):
        """Test start() clears actual_output from previous runs."""
        subtask = Subtask(
            id="1",
            description="Test",
            actual_output="Previous output"
        )
        subtask.start(session_id=1)

        assert subtask.actual_output is None

    def test_start_preserves_other_fields(self):
        """Test start() preserves other fields."""
        verification = Verification(type=VerificationType.COMMAND, run="pytest")
        subtask = Subtask(
            id="1",
            description="Test",
            service="backend",
            files_to_modify=["app.py"],
            expected_output="Success",
            verification=verification,
            critique_result={"score": 0.8}
        )

        subtask.start(session_id=2)

        assert subtask.id == "1"
        assert subtask.description == "Test"
        assert subtask.service == "backend"
        assert subtask.files_to_modify == ["app.py"]
        assert subtask.expected_output == "Success"
        assert subtask.verification.type == VerificationType.COMMAND
        assert subtask.critique_result == {"score": 0.8}

    def test_start_multiple_times(self):
        """Test calling start() multiple times updates timestamp."""
        subtask = Subtask(id="1", description="Test")

        subtask.start(session_id=1)
        first_timestamp = subtask.started_at

        import time
        time.sleep(0.01)  # Small delay to ensure different timestamp

        subtask.start(session_id=2)
        second_timestamp = subtask.started_at

        assert subtask.session_id == 2
        assert first_timestamp != second_timestamp

    def test_start_from_completed_state(self):
        """Test start() can be called on a completed subtask (restart)."""
        subtask = Subtask(
            id="1",
            description="Test",
            status=SubtaskStatus.COMPLETED,
            completed_at="2024-01-01T10:00:00",
            actual_output="First attempt"
        )

        subtask.start(session_id=2)

        assert subtask.status == SubtaskStatus.IN_PROGRESS
        assert subtask.completed_at is None
        assert subtask.actual_output is None
        assert subtask.session_id == 2

    def test_start_from_failed_state(self):
        """Test start() can be called on a failed subtask (retry)."""
        subtask = Subtask(
            id="1",
            description="Test",
            status=SubtaskStatus.FAILED,
            actual_output="FAILED: Error occurred"
        )

        subtask.start(session_id=3)

        assert subtask.status == SubtaskStatus.IN_PROGRESS
        assert subtask.actual_output is None
        assert subtask.session_id == 3


class TestSubtaskComplete:
    """Tests for Subtask.complete() method."""

    def test_complete_sets_status_to_completed(self):
        """Test complete() sets status to COMPLETED."""
        subtask = Subtask(id="1", description="Test")
        subtask.complete()

        assert subtask.status == SubtaskStatus.COMPLETED

    def test_complete_sets_timestamp(self):
        """Test complete() sets completed_at timestamp."""
        subtask = Subtask(id="1", description="Test")
        subtask.complete()

        assert subtask.completed_at is not None
        # Verify it's a valid ISO format string
        datetime.fromisoformat(subtask.completed_at)

    def test_complete_with_output(self):
        """Test complete() with output parameter."""
        subtask = Subtask(id="1", description="Test")
        subtask.complete(output="Task completed successfully")

        assert subtask.actual_output == "Task completed successfully"

    def test_complete_without_output(self):
        """Test complete() without output parameter."""
        subtask = Subtask(
            id="1",
            description="Test",
            actual_output="Previous output"
        )
        subtask.complete()

        # actual_output should not be changed if no output provided
        assert subtask.actual_output == "Previous output"

    def test_complete_from_in_progress(self):
        """Test complete() from IN_PROGRESS state."""
        subtask = Subtask(
            id="1",
            description="Test",
            status=SubtaskStatus.IN_PROGRESS,
            started_at="2024-01-01T10:00:00"
        )
        subtask.complete(output="Done")

        assert subtask.status == SubtaskStatus.COMPLETED
        assert subtask.started_at == "2024-01-01T10:00:00"
        assert subtask.actual_output == "Done"

    def test_complete_overwrites_previous_completion(self):
        """Test complete() can be called again (updates timestamp)."""
        subtask = Subtask(
            id="1",
            description="Test",
            status=SubtaskStatus.COMPLETED,
            completed_at="2024-01-01T10:00:00",
            actual_output="First completion"
        )

        subtask.complete(output="Second completion")

        assert subtask.status == SubtaskStatus.COMPLETED
        assert subtask.actual_output == "Second completion"
        assert subtask.completed_at != "2024-01-01T10:00:00"

    def test_complete_preserves_other_fields(self):
        """Test complete() preserves other fields."""
        subtask = Subtask(
            id="1",
            description="Test",
            service="frontend",
            started_at="2024-01-01T09:00:00",
            session_id=2,
            expected_output="Expected result",
            files_to_modify=["App.tsx"]
        )

        subtask.complete(output="Actual result")

        assert subtask.id == "1"
        assert subtask.description == "Test"
        assert subtask.service == "frontend"
        assert subtask.started_at == "2024-01-01T09:00:00"
        assert subtask.session_id == 2
        assert subtask.expected_output == "Expected result"
        assert subtask.files_to_modify == ["App.tsx"]
        assert subtask.actual_output == "Actual result"

    def test_complete_with_empty_string_output(self):
        """Test complete() with empty string output (falsy, so not set)."""
        subtask = Subtask(id="1", description="Test")
        subtask.complete(output="")

        # Empty string is falsy, so actual_output is not set
        assert subtask.actual_output is None

    def test_complete_with_none_output(self):
        """Test complete() with None output (default)."""
        subtask = Subtask(
            id="1",
            description="Test",
            actual_output="Previous"
        )
        subtask.complete(output=None)

        # None should not overwrite existing actual_output
        assert subtask.actual_output == "Previous"


class TestSubtaskFail:
    """Tests for Subtask.fail() method."""

    def test_fail_sets_status_to_failed(self):
        """Test fail() sets status to FAILED."""
        subtask = Subtask(id="1", description="Test")
        subtask.fail()

        assert subtask.status == SubtaskStatus.FAILED

    def test_fail_clears_completed_at(self):
        """Test fail() clears completed_at to maintain consistency."""
        subtask = Subtask(
            id="1",
            description="Test",
            completed_at="2024-01-01T10:00:00"
        )
        subtask.fail()

        assert subtask.completed_at is None

    def test_fail_with_reason(self):
        """Test fail() with reason parameter."""
        subtask = Subtask(id="1", description="Test")
        subtask.fail(reason="Database connection failed")

        assert subtask.actual_output == "FAILED: Database connection failed"

    def test_fail_without_reason(self):
        """Test fail() without reason parameter."""
        subtask = Subtask(
            id="1",
            description="Test",
            actual_output="Previous output"
        )
        subtask.fail()

        # actual_output should not be changed if no reason provided
        assert subtask.actual_output == "Previous output"

    def test_fail_overwrites_actual_output(self):
        """Test fail() with reason overwrites existing actual_output."""
        subtask = Subtask(
            id="1",
            description="Test",
            actual_output="Previous output"
        )
        subtask.fail(reason="New error")

        assert subtask.actual_output == "FAILED: New error"

    def test_fail_from_in_progress(self):
        """Test fail() from IN_PROGRESS state."""
        subtask = Subtask(
            id="1",
            description="Test",
            status=SubtaskStatus.IN_PROGRESS,
            started_at="2024-01-01T10:00:00",
            session_id=1
        )
        subtask.fail(reason="Timeout")

        assert subtask.status == SubtaskStatus.FAILED
        assert subtask.started_at == "2024-01-01T10:00:00"
        assert subtask.session_id == 1
        assert subtask.actual_output == "FAILED: Timeout"
        assert subtask.completed_at is None

    def test_fail_from_completed_state(self):
        """Test fail() can be called on completed subtask."""
        subtask = Subtask(
            id="1",
            description="Test",
            status=SubtaskStatus.COMPLETED,
            completed_at="2024-01-01T11:00:00",
            actual_output="Success"
        )
        subtask.fail(reason="Late failure discovered")

        assert subtask.status == SubtaskStatus.FAILED
        assert subtask.completed_at is None  # Cleared
        assert subtask.actual_output == "FAILED: Late failure discovered"

    def test_fail_preserves_other_fields(self):
        """Test fail() preserves other fields."""
        subtask = Subtask(
            id="1",
            description="Test",
            service="worker",
            started_at="2024-01-01T09:00:00",
            session_id=3,
            expected_output="Process completed",
            files_to_create=["worker.py"]
        )

        subtask.fail(reason="Worker crashed")

        assert subtask.id == "1"
        assert subtask.description == "Test"
        assert subtask.service == "worker"
        assert subtask.started_at == "2024-01-01T09:00:00"
        assert subtask.session_id == 3
        assert subtask.expected_output == "Process completed"
        assert subtask.files_to_create == ["worker.py"]

    def test_fail_with_empty_reason(self):
        """Test fail() with empty string reason (falsy, so not set)."""
        subtask = Subtask(id="1", description="Test")
        subtask.fail(reason="")

        # Empty string is falsy, so actual_output is not set
        assert subtask.actual_output is None

    def test_fail_with_special_characters_in_reason(self):
        """Test fail() with special characters in reason."""
        subtask = Subtask(id="1", description="Test")
        subtask.fail(reason="Error: <timeout> after 30s; status = 500")

        assert subtask.actual_output == "FAILED: Error: <timeout> after 30s; status = 500"


class TestSubtaskStateTransitions:
    """Tests for Subtask state transitions and lifecycle."""

    def test_full_lifecycle_pending_to_completed(self):
        """Test complete lifecycle: PENDING -> IN_PROGRESS -> COMPLETED."""
        subtask = Subtask(id="1", description="Test")

        assert subtask.status == SubtaskStatus.PENDING

        subtask.start(session_id=1)
        assert subtask.status == SubtaskStatus.IN_PROGRESS
        assert subtask.started_at is not None

        subtask.complete(output="Success")
        assert subtask.status == SubtaskStatus.COMPLETED
        assert subtask.completed_at is not None
        assert subtask.actual_output == "Success"

    def test_full_lifecycle_pending_to_failed(self):
        """Test failed lifecycle: PENDING -> IN_PROGRESS -> FAILED."""
        subtask = Subtask(id="1", description="Test")

        assert subtask.status == SubtaskStatus.PENDING

        subtask.start(session_id=1)
        assert subtask.status == SubtaskStatus.IN_PROGRESS

        subtask.fail(reason="Critical error")
        assert subtask.status == SubtaskStatus.FAILED
        assert subtask.completed_at is None
        assert subtask.actual_output == "FAILED: Critical error"

    def test_retry_lifecycle_failed_to_completed(self):
        """Test retry lifecycle: FAILED -> IN_PROGRESS -> COMPLETED."""
        subtask = Subtask(id="1", description="Test")

        # First attempt fails
        subtask.start(session_id=1)
        subtask.fail(reason="First attempt failed")
        assert subtask.status == SubtaskStatus.FAILED

        # Retry succeeds
        subtask.start(session_id=2)
        assert subtask.status == SubtaskStatus.IN_PROGRESS
        assert subtask.completed_at is None
        assert subtask.actual_output is None

        subtask.complete(output="Success on retry")
        assert subtask.status == SubtaskStatus.COMPLETED

    def test_multiple_failures_and_retries(self):
        """Test multiple failure/retry cycles."""
        subtask = Subtask(id="1", description="Test")

        for attempt in range(1, 4):
            subtask.start(session_id=attempt)
            assert subtask.status == SubtaskStatus.IN_PROGRESS
            assert subtask.session_id == attempt

            if attempt < 3:
                subtask.fail(reason=f"Attempt {attempt} failed")
                assert subtask.status == SubtaskStatus.FAILED
            else:
                subtask.complete(output=f"Success on attempt {attempt}")
                assert subtask.status == SubtaskStatus.COMPLETED

    def test_restart_after_completion(self):
        """Test restarting a completed subtask."""
        subtask = Subtask(id="1", description="Test")

        # First completion
        subtask.start(session_id=1)
        subtask.complete(output="First completion")
        first_completed_at = subtask.completed_at

        # Restart
        subtask.start(session_id=2)
        assert subtask.status == SubtaskStatus.IN_PROGRESS
        assert subtask.completed_at is None
        assert subtask.actual_output is None

        # Complete again
        subtask.complete(output="Second completion")
        assert subtask.status == SubtaskStatus.COMPLETED
        assert subtask.completed_at != first_completed_at

    def test_blocked_status_can_start(self):
        """Test that a BLOCKED subtask can be started."""
        subtask = Subtask(
            id="1",
            description="Test",
            status=SubtaskStatus.BLOCKED
        )

        subtask.start(session_id=1)
        assert subtask.status == SubtaskStatus.IN_PROGRESS

    def test_status_transitions_do_not_affect_files(self):
        """Test that state transitions preserve file lists."""
        subtask = Subtask(
            id="1",
            description="Test",
            files_to_modify=["a.py"],
            files_to_create=["test_a.py"]
        )

        subtask.start(session_id=1)
        assert subtask.files_to_modify == ["a.py"]
        assert subtask.files_to_create == ["test_a.py"]

        subtask.complete()
        assert subtask.files_to_modify == ["a.py"]
        assert subtask.files_to_create == ["test_a.py"]

        subtask.start(session_id=2)
        subtask.fail(reason="Error")
        assert subtask.files_to_modify == ["a.py"]
        assert subtask.files_to_create == ["test_a.py"]


class TestSubtaskEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_description(self):
        """Test Subtask with empty description."""
        subtask = Subtask(id="1", description="")
        assert subtask.description == ""

    def test_empty_id(self):
        """Test Subtask with empty id."""
        subtask = Subtask(id="", description="Test")
        assert subtask.id == ""

    def test_very_long_description(self):
        """Test Subtask with very long description."""
        long_desc = "A" * 10000
        subtask = Subtask(id="1", description=long_desc)
        assert len(subtask.description) == 10000

    def test_many_files(self):
        """Test Subtask with many files."""
        files = [f"file_{i}.py" for i in range(1000)]
        subtask = Subtask(
            id="1",
            description="Test",
            files_to_modify=files
        )
        assert len(subtask.files_to_modify) == 1000

    def test_unicode_characters(self):
        """Test Subtask with unicode characters."""
        subtask = Subtask(
            id="1",
            description="Test with emoji: 🔥 and unicode: ñ, 中文, عربي"
        )
        assert "🔥" in subtask.description
        assert "中文" in subtask.description

    def test_special_characters_in_id(self):
        """Test Subtask with special characters in id."""
        subtask = Subtask(
            id="task-123_special.id",
            description="Test"
        )
        assert subtask.id == "task-123_special.id"

    def test_zero_session_id(self):
        """Test Subtask with session_id=0 (edge case)."""
        subtask = Subtask(
            id="1",
            description="Test",
            session_id=0
        )
        result = subtask.to_dict()
        assert result["session_id"] == 0

    def test_large_session_id(self):
        """Test Subtask with very large session_id."""
        subtask = Subtask(
            id="1",
            description="Test",
            session_id=999999
        )
        assert subtask.session_id == 999999

    def test_negative_session_id(self):
        """Test Subtask with negative session_id (edge case, not typical)."""
        subtask = Subtask(
            id="1",
            description="Test",
            session_id=-1
        )
        assert subtask.session_id == -1

    def test_empty_verification_dict(self):
        """Test from_dict with empty verification dict."""
        data = {
            "id": "1",
            "description": "Test",
            "verification": {}
        }
        subtask = Subtask.from_dict(data)

        assert subtask.verification is not None
        assert subtask.verification.type == VerificationType.NONE

    def test_complex_critique_result(self):
        """Test Subtask with complex critique_result structure."""
        critique = {
            "overall_score": 0.85,
            "criteria": {
                "correctness": 0.9,
                "efficiency": 0.8,
                "readability": 0.85
            },
            "issues": [
                {
                    "type": "warning",
                    "message": "Consider optimizing",
                    "location": "line 42"
                }
            ],
            "suggestions": [
                "Use async/await",
                "Add error handling"
            ]
        }
        subtask = Subtask(
            id="1",
            description="Test",
            critique_result=critique
        )

        assert subtask.critique_result == critique

        # Test roundtrip
        data = subtask.to_dict()
        restored = Subtask.from_dict(data)
        assert restored.critique_result == critique


class TestSubtaskWithVerification:
    """Tests for Subtask with Verification objects."""

    def test_subtask_with_command_verification(self):
        """Test Subtask with COMMAND verification."""
        verification = Verification(
            type=VerificationType.COMMAND,
            run="npm test"
        )
        subtask = Subtask(
            id="1",
            description="Test",
            verification=verification
        )

        assert subtask.verification.type == VerificationType.COMMAND
        assert subtask.verification.run == "npm test"

    def test_subtask_with_api_verification(self):
        """Test Subtask with API verification."""
        verification = Verification(
            type=VerificationType.API,
            url="http://localhost:8000/api/test",
            method="POST",
            expect_status=201,
            expect_contains="\"success\":true"
        )
        subtask = Subtask(
            id="1",
            description="Test",
            verification=verification
        )

        assert subtask.verification.type == VerificationType.API
        assert subtask.verification.url == "http://localhost:8000/api/test"
        assert subtask.verification.method == "POST"
        assert subtask.verification.expect_status == 201
        assert subtask.verification.expect_contains == "\"success\":true"

    def test_subtask_with_browser_verification(self):
        """Test Subtask with BROWSER verification."""
        verification = Verification(
            type=VerificationType.BROWSER,
            url="http://localhost:3000",
            scenario="Navigate to login page and enter credentials"
        )
        subtask = Subtask(
            id="1",
            description="Test",
            verification=verification
        )

        assert subtask.verification.type == VerificationType.BROWSER
        assert subtask.verification.url == "http://localhost:3000"
        assert subtask.verification.scenario == "Navigate to login page and enter credentials"

    def test_subtask_with_manual_verification(self):
        """Test Subtask with MANUAL verification."""
        verification = Verification(
            type=VerificationType.MANUAL,
            scenario="Verify UI matches design mockup"
        )
        subtask = Subtask(
            id="1",
            description="Test",
            verification=verification
        )

        assert subtask.verification.type == VerificationType.MANUAL
        assert subtask.verification.scenario == "Verify UI matches design mockup"

    def test_subtask_with_component_verification(self):
        """Test Subtask with COMPONENT verification."""
        verification = Verification(
            type=VerificationType.COMPONENT,
            run="npm test -- Button.test.tsx",
            scenario="Verify Button component renders correctly"
        )
        subtask = Subtask(
            id="1",
            description="Test",
            verification=verification
        )

        assert subtask.verification.type == VerificationType.COMPONENT
        assert subtask.verification.run == "npm test -- Button.test.tsx"
        assert subtask.verification.scenario == "Verify Button component renders correctly"

    def test_subtask_with_none_verification(self):
        """Test Subtask with NONE verification type."""
        verification = Verification(type=VerificationType.NONE)
        subtask = Subtask(
            id="1",
            description="Test",
            verification=verification
        )

        assert subtask.verification.type == VerificationType.NONE

    def test_verification_preserved_in_state_transitions(self):
        """Test that verification is preserved through state transitions."""
        verification = Verification(
            type=VerificationType.COMMAND,
            run="pytest tests/"
        )
        subtask = Subtask(
            id="1",
            description="Test",
            verification=verification
        )

        subtask.start(session_id=1)
        assert subtask.verification.type == VerificationType.COMMAND

        subtask.complete()
        assert subtask.verification.type == VerificationType.COMMAND

        subtask.start(session_id=2)
        subtask.fail(reason="Error")
        assert subtask.verification.type == VerificationType.COMMAND
