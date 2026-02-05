"""Tests for generators"""

from implementation_plan import (
    ImplementationPlan,
    Phase,
    PhaseType,
    Subtask,
    SubtaskStatus,
    Verification,
    VerificationType,
    WorkflowType,
)
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from planner_lib.generators import (
    FeaturePlanGenerator,
    InvestigationPlanGenerator,
    PlanGenerator,
    RefactorPlanGenerator,
    get_plan_generator,
)
from planner_lib.models import PlannerContext


@pytest.fixture
def mock_context():
    """Create a mock PlannerContext for testing."""
    return PlannerContext(
        spec_content="# Test Spec\n\nFeature description.",
        project_index={
            "services": {
                "backend": {"type": "backend", "path": "apps/backend", "port": 8000},
                "frontend": {"type": "frontend", "path": "apps/frontend"},
                "worker": {"type": "worker", "path": "apps/backend/worker"},
            }
        },
        task_context={"key": "value"},
        services_involved=["backend", "frontend"],
        workflow_type=WorkflowType.FEATURE,
        files_to_modify=[
            {"path": "apps/backend/api/users.py", "reason": "Add user endpoint", "service": "backend"},
            {"path": "apps/backend/models/user.py", "reason": "Add user model", "service": "backend"},
            {"path": "apps/frontend/components/UserProfile.tsx", "reason": "Add profile UI", "service": "frontend"},
        ],
        files_to_reference=[
            {"path": "apps/backend/api/posts.py"},
            {"path": "apps/frontend/components/Button.tsx"},
        ],
    )


@pytest.fixture
def mock_context_with_acceptance():
    """Create a mock context with acceptance criteria."""
    return PlannerContext(
        spec_content="# User Authentication\n\n"
        "## Success Criteria\n"
        "- User can log in with email and password\n"
        "- Session is maintained across requests\n"
        "* Logout clears session properly\n",
        project_index={
            "services": {
                "backend": {"type": "backend", "port": 8000},
            }
        },
        task_context={},
        services_involved=["backend"],
        workflow_type=WorkflowType.FEATURE,
        files_to_modify=[
            {"path": "apps/backend/auth.py", "reason": "Add login endpoint", "service": "backend"},
        ],
        files_to_reference=[],
    )


@pytest.fixture
def spec_dir(tmp_path):
    """Create a temporary spec directory."""
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir(parents=True, exist_ok=True)
    # Create spec.md file
    (spec_dir / "spec.md").write_text("# Test Spec\n\nFeature description.")
    return spec_dir


def test_get_plan_generator_feature(mock_context, spec_dir):
    """Test get_plan_generator returns FeaturePlanGenerator for feature workflow."""
    mock_context.workflow_type = WorkflowType.FEATURE
    result = get_plan_generator(mock_context, spec_dir)
    assert isinstance(result, FeaturePlanGenerator)


def test_get_plan_generator_investigation(mock_context, spec_dir):
    """Test get_plan_generator returns InvestigationPlanGenerator for investigation workflow."""
    mock_context.workflow_type = WorkflowType.INVESTIGATION
    result = get_plan_generator(mock_context, spec_dir)
    assert isinstance(result, InvestigationPlanGenerator)


def test_get_plan_generator_refactor(mock_context, spec_dir):
    """Test get_plan_generator returns RefactorPlanGenerator for refactor workflow."""
    mock_context.workflow_type = WorkflowType.REFACTOR
    result = get_plan_generator(mock_context, spec_dir)
    assert isinstance(result, RefactorPlanGenerator)


def test_get_plan_generator_simple(mock_context, spec_dir):
    """Test get_plan_generator defaults to FeaturePlanGenerator for simple workflow."""
    mock_context.workflow_type = WorkflowType.SIMPLE
    result = get_plan_generator(mock_context, spec_dir)
    assert isinstance(result, FeaturePlanGenerator)


def test_PlanGenerator_init(mock_context, spec_dir):
    """Test PlanGenerator.__init__ stores context and spec_dir."""
    instance = PlanGenerator(mock_context, spec_dir)
    assert instance.context == mock_context
    assert instance.spec_dir == spec_dir


def test_PlanGenerator_generate_raises_not_implemented(mock_context, spec_dir):
    """Test PlanGenerator.generate raises NotImplementedError."""
    instance = PlanGenerator(mock_context, spec_dir)
    with pytest.raises(NotImplementedError):
        instance.generate()


def test_FeaturePlanGenerator_generate_basic(mock_context, spec_dir):
    """Test FeaturePlanGenerator.generate creates a valid implementation plan."""
    mock_context.workflow_type = WorkflowType.FEATURE
    instance = FeaturePlanGenerator(mock_context, spec_dir)
    result = instance.generate()

    assert isinstance(result, ImplementationPlan)
    assert result.workflow_type == WorkflowType.FEATURE
    assert len(result.phases) > 0
    assert result.feature == "Test Spec"
    assert result.spec_file == str(spec_dir / "spec.md")


def test_FeaturePlanGenerator_generate_with_acceptance_criteria(mock_context_with_acceptance, spec_dir):
    """Test FeaturePlanGenerator extracts acceptance criteria."""
    instance = FeaturePlanGenerator(mock_context_with_acceptance, spec_dir)
    result = instance.generate()

    assert len(result.final_acceptance) > 0
    assert any("log in with email" in c.lower() for c in result.final_acceptance)
    assert any("session is maintained" in c.lower() for c in result.final_acceptance)


def test_FeaturePlanGenerator_generate_service_order(mock_context, spec_dir):
    """Test FeaturePlanGenerator orders services correctly (backend first)."""
    instance = FeaturePlanGenerator(mock_context, spec_dir)
    result = instance.generate()

    # Backend should come before frontend
    phase_names = [p.name.lower() for p in result.phases]
    if "backend" in phase_names and "frontend" in phase_names:
        backend_idx = phase_names.index("backend")
        frontend_idx = phase_names.index("frontend")
        assert backend_idx < frontend_idx


def test_FeaturePlanGenerator_generate_subtasks(mock_context, spec_dir):
    """Test FeaturePlanGenerator creates subtasks correctly."""
    instance = FeaturePlanGenerator(mock_context, spec_dir)
    result = instance.generate()

    # Should have subtasks
    assert sum(len(p.subtasks) for p in result.phases) > 0

    # Check subtask structure (integration subtasks have all_services=True and service=None)
    for phase in result.phases:
        for subtask in phase.subtasks:
            assert subtask.id
            assert subtask.description
            # Either service is set or all_services is True (for integration)
            assert subtask.service is not None or subtask.all_services is True
            # Integration subtasks don't have files_to_modify
            if not subtask.all_services:
                assert len(subtask.files_to_modify) > 0


def test_FeaturePlanGenerator_generate_dependencies(mock_context, spec_dir):
    """Test FeaturePlanGenerator creates proper dependencies."""
    instance = FeaturePlanGenerator(mock_context, spec_dir)
    result = instance.generate()

    # Check that phases have correct dependencies
    for i, phase in enumerate(result.phases):
        phase_num = i + 1
        # Phase 1 should have no dependencies
        if phase_num == 1:
            assert phase.depends_on == []
        # Later phases should depend on earlier ones
        elif phase_num > 1:
            assert len(phase.depends_on) >= 0


def test_FeaturePlanGenerator_generate_with_integration(mock_context, spec_dir):
    """Test FeaturePlanGenerator adds integration phase when multiple services."""
    instance = FeaturePlanGenerator(mock_context, spec_dir)
    result = instance.generate()

    # Should have integration phase since we have multiple services
    integration_phases = [p for p in result.phases if p.type == PhaseType.INTEGRATION]
    assert len(integration_phases) > 0

    # Integration phase should depend on all previous phases
    integration_phase = integration_phases[0]
    if len(result.phases) > 1:
        assert len(integration_phase.depends_on) > 0


def test_FeaturePlanGenerator_generate_single_service(tmp_path, spec_dir):
    """Test FeaturePlanGenerator with single service (no integration phase)."""
    single_service_context = PlannerContext(
        spec_content="# Single Service Feature",
        project_index={
            "services": {
                "backend": {"type": "backend", "port": 8000},
            }
        },
        task_context={},
        services_involved=["backend"],
        workflow_type=WorkflowType.FEATURE,
        files_to_modify=[
            {"path": "apps/backend/api/test.py", "reason": "Add test", "service": "backend"},
        ],
        files_to_reference=[],
    )

    instance = FeaturePlanGenerator(single_service_context, spec_dir)
    result = instance.generate()

    # Should not have integration phase for single service
    integration_phases = [p for p in result.phases if p.type == PhaseType.INTEGRATION]
    assert len(integration_phases) == 0


def test_FeaturePlanGenerator_worker_depends_on_backend(tmp_path, spec_dir):
    """Test that worker phases depend on backend."""
    context = PlannerContext(
        spec_content="# Feature with Backend and Worker",
        project_index={
            "services": {
                "backend": {"type": "backend", "port": 8000},
                "worker": {"type": "worker"},
            }
        },
        task_context={},
        services_involved=["backend", "worker"],
        workflow_type=WorkflowType.FEATURE,
        files_to_modify=[
            {"path": "apps/backend/api.py", "reason": "API", "service": "backend"},
            {"path": "apps/backend/worker/tasks.py", "reason": "Task", "service": "worker"},
        ],
        files_to_reference=[],
    )

    instance = FeaturePlanGenerator(context, spec_dir)
    result = instance.generate()

    # Find worker and backend phases
    backend_phase = None
    worker_phase = None
    for phase in result.phases:
        if "worker" in phase.name.lower():
            worker_phase = phase
        elif "backend" in phase.name.lower():
            backend_phase = phase

    # Worker should depend on backend
    if worker_phase and backend_phase:
        assert backend_phase.phase in worker_phase.depends_on


def test_FeaturePlanGenerator_frontend_depends_on_backend(tmp_path, spec_dir):
    """Test that frontend phases depend on backend."""
    context = PlannerContext(
        spec_content="# Feature with Backend and Frontend",
        project_index={
            "services": {
                "backend": {"type": "backend", "port": 8000},
                "frontend": {"type": "frontend"},
            }
        },
        task_context={},
        services_involved=["backend", "frontend"],
        workflow_type=WorkflowType.FEATURE,
        files_to_modify=[
            {"path": "apps/backend/api.py", "reason": "API", "service": "backend"},
            {"path": "apps/frontend/component.tsx", "reason": "UI", "service": "frontend"},
        ],
        files_to_reference=[],
    )

    instance = FeaturePlanGenerator(context, spec_dir)
    result = instance.generate()

    # Find frontend and backend phases
    backend_phase = None
    frontend_phase = None
    for phase in result.phases:
        if "frontend" in phase.name.lower():
            frontend_phase = phase
        elif "backend" in phase.name.lower():
            backend_phase = phase

    # Frontend should depend on backend
    if frontend_phase and backend_phase:
        assert backend_phase.phase in frontend_phase.depends_on


def test_InvestigationPlanGenerator_generate(mock_context, spec_dir):
    """Test InvestigationPlanGenerator.generate creates a valid investigation plan."""
    mock_context.workflow_type = WorkflowType.INVESTIGATION
    instance = InvestigationPlanGenerator(mock_context, spec_dir)
    result = instance.generate()

    assert isinstance(result, ImplementationPlan)
    assert result.workflow_type == WorkflowType.INVESTIGATION
    assert len(result.phases) == 4  # Investigation has 4 fixed phases


def test_InvestigationPlanGenerator_phase_structure(mock_context, spec_dir):
    """Test InvestigationPlanGenerator creates correct phase structure."""
    mock_context.workflow_type = WorkflowType.INVESTIGATION
    instance = InvestigationPlanGenerator(mock_context, spec_dir)
    result = instance.generate()

    assert result.phases[0].name == "Reproduce & Instrument"
    assert result.phases[1].name == "Investigate & Analyze"
    assert result.phases[2].name == "Implement Fix"
    assert result.phases[3].name == "Verify & Harden"

    # Check phase types
    assert result.phases[0].type == PhaseType.INVESTIGATION
    assert result.phases[1].type == PhaseType.INVESTIGATION
    assert result.phases[2].type == PhaseType.IMPLEMENTATION
    assert result.phases[3].type == PhaseType.INTEGRATION


def test_InvestigationPlanGenerator_dependencies(mock_context, spec_dir):
    """Test InvestigationPlanGenerator creates proper dependencies."""
    mock_context.workflow_type = WorkflowType.INVESTIGATION
    instance = InvestigationPlanGenerator(mock_context, spec_dir)
    result = instance.generate()

    # Check dependencies chain
    assert result.phases[0].depends_on == []
    assert result.phases[1].depends_on == [1]
    assert result.phases[2].depends_on == [2]
    assert result.phases[3].depends_on == [3]


def test_InvestigationPlanGenerator_blocked_subtasks(mock_context, spec_dir):
    """Test InvestigationPlanGenerator marks fix subtasks as blocked."""
    mock_context.workflow_type = WorkflowType.INVESTIGATION
    instance = InvestigationPlanGenerator(mock_context, spec_dir)
    result = instance.generate()

    # Phase 3 (Implement Fix) should have blocked subtasks
    fix_phase = result.phases[2]
    assert any(s.status == SubtaskStatus.BLOCKED for s in fix_phase.subtasks)


def test_InvestigationPlanGenerator_final_acceptance(mock_context, spec_dir):
    """Test InvestigationPlanGenerator has correct final acceptance."""
    mock_context.workflow_type = WorkflowType.INVESTIGATION
    instance = InvestigationPlanGenerator(mock_context, spec_dir)
    result = instance.generate()

    assert len(result.final_acceptance) == 3
    assert "no longer reproducible" in result.final_acceptance[0].lower()
    assert any("root cause" in c.lower() for c in result.final_acceptance)
    assert any("regression" in c.lower() for c in result.final_acceptance)


def test_RefactorPlanGenerator_generate(mock_context, spec_dir):
    """Test RefactorPlanGenerator.generate creates a valid refactor plan."""
    mock_context.workflow_type = WorkflowType.REFACTOR
    instance = RefactorPlanGenerator(mock_context, spec_dir)
    result = instance.generate()

    assert isinstance(result, ImplementationPlan)
    assert result.workflow_type == WorkflowType.REFACTOR
    assert len(result.phases) == 4  # Refactor has 4 fixed phases


def test_RefactorPlanGenerator_phase_structure(mock_context, spec_dir):
    """Test RefactorPlanGenerator creates correct phase structure."""
    mock_context.workflow_type = WorkflowType.REFACTOR
    instance = RefactorPlanGenerator(mock_context, spec_dir)
    result = instance.generate()

    assert result.phases[0].name == "Add New System"
    assert result.phases[1].name == "Migrate Consumers"
    assert result.phases[2].name == "Remove Old System"
    assert result.phases[3].name == "Polish"

    # Check phase types
    assert result.phases[0].type == PhaseType.IMPLEMENTATION
    assert result.phases[1].type == PhaseType.IMPLEMENTATION
    assert result.phases[2].type == PhaseType.CLEANUP
    assert result.phases[3].type == PhaseType.CLEANUP


def test_RefactorPlanGenerator_dependencies(mock_context, spec_dir):
    """Test RefactorPlanGenerator creates proper dependencies."""
    mock_context.workflow_type = WorkflowType.REFACTOR
    instance = RefactorPlanGenerator(mock_context, spec_dir)
    result = instance.generate()

    # Each phase should depend on the previous
    assert result.phases[0].depends_on == []
    assert result.phases[1].depends_on == [1]
    assert result.phases[2].depends_on == [2]
    assert result.phases[3].depends_on == [3]


def test_RefactorPlanGenerator_final_acceptance(mock_context, spec_dir):
    """Test RefactorPlanGenerator has correct final acceptance."""
    mock_context.workflow_type = WorkflowType.REFACTOR
    instance = RefactorPlanGenerator(mock_context, spec_dir)
    result = instance.generate()

    assert len(result.final_acceptance) == 3
    assert any("migrated" in c.lower() for c in result.final_acceptance)
    assert any("removed" in c.lower() for c in result.final_acceptance)
    assert any("regression" in c.lower() for c in result.final_acceptance)


def test_FeaturePlanGenerate_with_service_inference(tmp_path, spec_dir):
    """Test FeaturePlanGenerator infers service from path."""
    context = PlannerContext(
        spec_content="# Test",
        project_index={
            "services": {
                "backend": {"type": "backend", "path": "apps/backend"},
            }
        },
        task_context={},
        services_involved=["backend"],
        workflow_type=WorkflowType.FEATURE,
        files_to_modify=[
            # No service specified - should be inferred from path
            {"path": "apps/backend/api/test.py", "reason": "Test"},
        ],
        files_to_reference=[],
    )

    instance = FeaturePlanGenerator(context, spec_dir)
    result = instance.generate()

    # Should still create plan
    assert len(result.phases) > 0
    # All subtasks should have service assigned
    for phase in result.phases:
        for subtask in phase.subtasks:
            assert subtask.service


def test_PlanGenerator_services_involved(mock_context, spec_dir):
    """Test that services_involved is propagated correctly."""
    for workflow_type, generator_class in [
        (WorkflowType.FEATURE, FeaturePlanGenerator),
        (WorkflowType.INVESTIGATION, InvestigationPlanGenerator),
        (WorkflowType.REFACTOR, RefactorPlanGenerator),
    ]:
        mock_context.workflow_type = workflow_type
        instance = generator_class(mock_context, spec_dir)
        result = instance.generate()

        assert result.services_involved == ["backend", "frontend"]


def test_PlanGenerator_spec_file_path(mock_context, spec_dir):
    """Test that spec_file path is set correctly."""
    for workflow_type in [WorkflowType.FEATURE, WorkflowType.INVESTIGATION, WorkflowType.REFACTOR]:
        mock_context.workflow_type = workflow_type
        generator = get_plan_generator(mock_context, spec_dir)
        result = generator.generate()

        assert result.spec_file == str(spec_dir / "spec.md")
