"""Tests for implementation_plan factories"""

from implementation_plan.factories import create_feature_plan, create_investigation_plan, create_refactor_plan
from implementation_plan.enums import PhaseType, SubtaskStatus, VerificationType, WorkflowType
from implementation_plan.phase import Phase
from implementation_plan.subtask import Subtask
from implementation_plan.verification import Verification
from pathlib import Path
import pytest


def test_create_feature_plan_basic():
    """Test create_feature_plan with basic configuration"""

    # Arrange
    feature = "User Authentication"
    services = ["api", "database"]
    phases_config = [
        {
            "name": "Database Schema",
            "type": "implementation",
            "subtasks": [
                {"id": "1", "description": "Create users table", "status": "pending"},
                {"id": "2", "description": "Create sessions table", "status": "pending"},
            ],
            "depends_on": [],
            "parallel_safe": True,
        },
        {
            "name": "API Endpoints",
            "type": "implementation",
            "subtasks": [
                {"id": "3", "description": "Create login endpoint", "status": "pending"},
                {"id": "4", "description": "Create logout endpoint", "status": "pending"},
            ],
            "depends_on": [1],
            "parallel_safe": False,
        },
    ]

    # Act
    result = create_feature_plan(feature, services, phases_config)

    # Assert
    assert result is not None
    assert result.feature == "User Authentication"
    assert result.workflow_type == WorkflowType.FEATURE
    assert result.services_involved == ["api", "database"]
    assert len(result.phases) == 2

    # Phase 1
    assert result.phases[0].phase == 1
    assert result.phases[0].name == "Database Schema"
    assert result.phases[0].type == PhaseType.IMPLEMENTATION
    assert len(result.phases[0].subtasks) == 2
    assert result.phases[0].subtasks[0].id == "1"
    assert result.phases[0].subtasks[0].description == "Create users table"
    assert result.phases[0].subtasks[0].status == SubtaskStatus.PENDING
    assert result.phases[0].depends_on == []
    assert result.phases[0].parallel_safe is True

    # Phase 2
    assert result.phases[1].phase == 2
    assert result.phases[1].name == "API Endpoints"
    assert result.phases[1].depends_on == [1]
    assert result.phases[1].parallel_safe is False

    # Timestamps
    assert result.created_at is not None
    assert result.updated_at is None


def test_create_feature_plan_with_verification():
    """Test create_feature_plan with verification on subtasks"""

    # Arrange
    feature = "Payment Processing"
    services = ["api"]
    phases_config = [
        {
            "name": "Implementation",
            "type": "implementation",
            "subtasks": [
                {
                    "id": "1",
                    "description": "Create payment endpoint",
                    "status": "pending",
                    "verification": {
                        "type": "api",
                        "url": "http://localhost:8000/api/payments",
                        "method": "POST",
                        "expect_status": 201,
                    },
                },
            ],
        },
    ]

    # Act
    result = create_feature_plan(feature, services, phases_config)

    # Assert
    assert len(result.phases) == 1
    assert len(result.phases[0].subtasks) == 1
    assert result.phases[0].subtasks[0].verification is not None
    assert result.phases[0].subtasks[0].verification.type == VerificationType.API
    assert result.phases[0].subtasks[0].verification.url == "http://localhost:8000/api/payments"


def test_create_feature_plan_default_values():
    """Test create_feature_plan with default values"""

    # Arrange
    feature = "Simple Feature"
    services = ["web"]
    phases_config = [
        {
            "name": "Basic Phase",
            "subtasks": [{"id": "1", "description": "Task 1"}],
            # Missing optional fields
        },
    ]

    # Act
    result = create_feature_plan(feature, services, phases_config)

    # Assert
    assert result.phases[0].type == PhaseType.IMPLEMENTATION  # Default
    assert result.phases[0].depends_on == []  # Default
    assert result.phases[0].parallel_safe is False  # Default


def test_create_feature_plan_empty():
    """Test create_feature_plan with empty phases"""

    # Arrange
    feature = "Empty Plan"
    services = []
    phases_config = []

    # Act
    result = create_feature_plan(feature, services, phases_config)

    # Assert
    assert result.feature == "Empty Plan"
    assert result.services_involved == []
    assert result.phases == []
    assert result.created_at is not None


def test_create_investigation_plan_basic():
    """Test create_investigation_plan creates proper investigation structure"""

    # Arrange
    bug_description = "Memory leak in worker process"
    services = ["worker", "database"]

    # Act
    result = create_investigation_plan(bug_description, services)

    # Assert
    assert result is not None
    assert result.feature == "Fix: Memory leak in worker process"
    assert result.workflow_type == WorkflowType.INVESTIGATION
    assert result.services_involved == ["worker", "database"]
    assert len(result.phases) == 3
    assert result.created_at is not None


def test_create_investigation_plan_phase1_structure():
    """Test investigation plan Phase 1 (Reproduce & Instrument)"""

    # Arrange
    bug_description = "Login failure"
    services = ["api"]

    # Act
    result = create_investigation_plan(bug_description, services)

    # Assert - Phase 1
    phase1 = result.phases[0]
    assert phase1.phase == 1
    assert phase1.name == "Reproduce & Instrument"
    assert phase1.type == PhaseType.INVESTIGATION
    assert phase1.depends_on == []

    # Check subtasks
    assert len(phase1.subtasks) == 2
    assert phase1.subtasks[0].id == "add-logging"
    assert phase1.subtasks[0].description == "Add detailed logging around suspected areas"
    assert phase1.subtasks[0].expected_output == "Logs capture relevant state and events"
    assert phase1.subtasks[0].status == SubtaskStatus.PENDING

    assert phase1.subtasks[1].id == "create-repro"
    assert phase1.subtasks[1].description == "Create reliable reproduction steps"
    assert phase1.subtasks[1].expected_output == "Can reproduce bug on demand"


def test_create_investigation_plan_phase2_structure():
    """Test investigation plan Phase 2 (Identify Root Cause)"""

    # Arrange
    bug_description = "Data corruption"
    services = ["database"]

    # Act
    result = create_investigation_plan(bug_description, services)

    # Assert - Phase 2
    phase2 = result.phases[1]
    assert phase2.phase == 2
    assert phase2.name == "Identify Root Cause"
    assert phase2.type == PhaseType.INVESTIGATION
    assert phase2.depends_on == [1]

    # Check subtasks
    assert len(phase2.subtasks) == 1
    assert phase2.subtasks[0].id == "analyze"
    assert phase2.subtasks[0].description == "Analyze logs and behavior"
    assert phase2.subtasks[0].expected_output == "Root cause hypothesis with evidence"


def test_create_investigation_plan_phase3_blocked():
    """Test investigation plan Phase 3 (Fix) starts as blocked"""

    # Arrange
    bug_description = "UI rendering issue"
    services = ["frontend"]

    # Act
    result = create_investigation_plan(bug_description, services)

    # Assert - Phase 3
    phase3 = result.phases[2]
    assert phase3.phase == 3
    assert phase3.name == "Implement Fix"
    assert phase3.type == PhaseType.IMPLEMENTATION
    assert phase3.depends_on == [2]

    # Check subtasks - should be BLOCKED pending investigation
    assert len(phase3.subtasks) == 2
    assert phase3.subtasks[0].id == "fix"
    assert phase3.subtasks[0].description == "[TO BE DETERMINED FROM INVESTIGATION]"
    assert phase3.subtasks[0].status == SubtaskStatus.BLOCKED

    assert phase3.subtasks[1].id == "regression-test"
    assert phase3.subtasks[1].description == "Add regression test to prevent recurrence"
    assert phase3.subtasks[1].status == SubtaskStatus.BLOCKED


def test_create_investigation_plan_empty_services():
    """Test create_investigation_plan with empty services list"""

    # Arrange
    bug_description = "Unknown issue"
    services = []

    # Act
    result = create_investigation_plan(bug_description, services)

    # Assert
    assert result.services_involved == []
    assert len(result.phases) == 3


def test_create_refactor_plan_basic():
    """Test create_refactor_plan creates proper refactor structure"""

    # Arrange
    refactor_description = "Migrate from Redis to Memcached"
    services = ["api", "cache"]
    stages = [
        {
            "name": "Add Memcached Support",
            "type": "implementation",
            "subtasks": [
                {"id": "1", "description": "Install Memcached client", "status": "pending"},
                {"id": "2", "description": "Create cache abstraction layer", "status": "pending"},
            ],
            "depends_on": [],
        },
        {
            "name": "Migrate Consumers",
            "type": "implementation",
            "subtasks": [
                {"id": "3", "description": "Update API to use abstraction", "status": "pending"},
            ],
            "depends_on": [1],
        },
        {
            "name": "Remove Redis",
            "type": "cleanup",
            "subtasks": [
                {"id": "4", "description": "Uninstall Redis client", "status": "pending"},
            ],
            "depends_on": [2],
        },
    ]

    # Act
    result = create_refactor_plan(refactor_description, services, stages)

    # Assert
    assert result is not None
    assert result.feature == "Migrate from Redis to Memcached"
    assert result.workflow_type == WorkflowType.REFACTOR
    assert result.services_involved == ["api", "cache"]
    assert len(result.phases) == 3
    assert result.created_at is not None


def test_create_refactor_plan_stage_types():
    """Test refactor plan stages preserve their types"""

    # Arrange
    stages = [
        {
            "name": "Stage 1",
            "type": "setup",
            "subtasks": [{"id": "1", "description": "Setup task"}],
        },
        {
            "name": "Stage 2",
            "type": "implementation",
            "subtasks": [{"id": "2", "description": "Impl task"}],
        },
        {
            "name": "Stage 3",
            "type": "cleanup",
            "subtasks": [{"id": "3", "description": "Cleanup task"}],
        },
    ]

    # Act
    result = create_refactor_plan("Refactor", ["service"], stages)

    # Assert
    assert result.phases[0].type == PhaseType.SETUP
    assert result.phases[1].type == PhaseType.IMPLEMENTATION
    assert result.phases[2].type == PhaseType.CLEANUP


def test_create_refactor_plan_auto_depends_on():
    """Test refactor plan auto-generates depends_on when not specified"""

    # Arrange
    stages = [
        {
            "name": "Stage 1",
            "subtasks": [{"id": "1", "description": "Task 1"}],
            # No depends_on specified
        },
        {
            "name": "Stage 2",
            "subtasks": [{"id": "2", "description": "Task 2"}],
            # No depends_on specified
        },
        {
            "name": "Stage 3",
            "subtasks": [{"id": "3", "description": "Task 3"}],
            # No depends_on specified
        },
    ]

    # Act
    result = create_refactor_plan("Sequential Refactor", ["service"], stages)

    # Assert - Each stage should depend on previous
    assert result.phases[0].depends_on == []  # First stage has no dependencies
    assert result.phases[1].depends_on == [1]  # Second depends on first
    assert result.phases[2].depends_on == [2]  # Third depends on second


def test_create_refactor_plan_explicit_depends_on():
    """Test refactor plan respects explicit depends_on"""

    # Arrange
    stages = [
        {
            "name": "Stage 1",
            "subtasks": [{"id": "1", "description": "Task 1"}],
            "depends_on": [],  # Explicit empty
        },
        {
            "name": "Stage 3",
            "subtasks": [{"id": "3", "description": "Task 3"}],
            "depends_on": [1, 2],  # Depends on both 1 and 2 (parallel phases)
        },
    ]

    # Act
    result = create_refactor_plan("Complex Refactor", ["service"], stages)

    # Assert
    assert result.phases[0].depends_on == []
    assert result.phases[1].depends_on == [1, 2]


def test_create_refactor_plan_empty_stages():
    """Test create_refactor_plan with empty stages"""

    # Arrange
    refactor_description = "Empty Refactor"
    services = []
    stages = []

    # Act
    result = create_refactor_plan(refactor_description, services, stages)

    # Assert
    assert result.feature == "Empty Refactor"
    assert result.services_involved == []
    assert result.phases == []


def test_create_refactor_plan_single_stage():
    """Test create_refactor_plan with single stage"""

    # Arrange
    stages = [
        {
            "name": "Only Stage",
            "subtasks": [{"id": "1", "description": "Single task"}],
        },
    ]

    # Act
    result = create_refactor_plan("Single Stage Refactor", ["service"], stages)

    # Assert
    assert len(result.phases) == 1
    assert result.phases[0].phase == 1
    assert result.phases[0].depends_on == []


def test_all_factories_create_valid_plans():
    """Test all factory functions create valid ImplementationPlan objects"""

    # Arrange
    feature = "Feature Plan"
    services = ["api"]
    phases_config = [
        {
            "name": "Phase 1",
            "subtasks": [{"id": "1", "description": "Task 1"}],
        },
    ]

    # Act
    feature_plan = create_feature_plan(feature, services, phases_config)
    investigation_plan = create_investigation_plan("Bug", services)
    refactor_plan = create_refactor_plan("Refactor", services, phases_config)

    # Assert - All should have valid timestamps
    assert feature_plan.created_at is not None
    assert investigation_plan.created_at is not None
    assert refactor_plan.created_at is not None

    # All should be serializable
    for plan in [feature_plan, investigation_plan, refactor_plan]:
        data = plan.to_dict()
        assert "feature" in data
        assert "workflow_type" in data
        assert "phases" in data
        assert "created_at" in data
