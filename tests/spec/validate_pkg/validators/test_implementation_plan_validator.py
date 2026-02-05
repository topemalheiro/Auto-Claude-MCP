"""Tests for implementation_plan_validator"""

from spec.validate_pkg.validators.implementation_plan_validator import ImplementationPlanValidator
from spec.validate_pkg.models import ValidationResult
from spec.validate_pkg.schemas import IMPLEMENTATION_PLAN_SCHEMA
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import json


def test_ImplementationPlanValidator___init__():
    """Test ImplementationPlanValidator.__init__"""

    # Arrange
    spec_dir = Path("/tmp/test")

    # Act
    validator = ImplementationPlanValidator(spec_dir)

    # Assert
    assert validator.spec_dir == spec_dir


def test_ImplementationPlanValidator_validate_missing_file(tmp_path):
    """Test ImplementationPlanValidator.validate when plan is missing"""

    # Arrange
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    # No implementation_plan.json created

    validator = ImplementationPlanValidator(spec_dir)

    # Act
    result = validator.validate()

    # Assert
    assert result.valid is False
    assert "not found" in result.errors[0].lower()
    assert len(result.fixes) > 0
    assert result.checkpoint == "plan"


def test_ImplementationPlanValidator_validate_invalid_json(tmp_path):
    """Test ImplementationPlanValidator.validate with invalid JSON"""

    # Arrange
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    plan_file = spec_dir / "implementation_plan.json"
    plan_file.write_text('{invalid json}', encoding="utf-8")

    validator = ImplementationPlanValidator(spec_dir)

    # Act
    result = validator.validate()

    # Assert
    assert result.valid is False
    # The error message includes "invalid json" (case-insensitive match)
    assert "invalid" in result.errors[0].lower() and "json" in result.errors[0].lower()
    assert result.checkpoint == "plan"


def test_ImplementationPlanValidator_validate_valid_plan(tmp_path):
    """Test ImplementationPlanValidator.validate with valid plan"""

    # Arrange
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    plan_file = spec_dir / "implementation_plan.json"
    plan = {
        "workflow_type": "feature",
        "phases": [
            {
                "id": "phase1",
                "name": "Phase 1",
                "type": "implementation",
                "subtasks": [
                    {
                        "id": "subtask1",
                        "description": "Test subtask",
                        "status": "pending",
                    }
                ]
            }
        ]
    }
    plan_file.write_text(json.dumps(plan), encoding="utf-8")

    validator = ImplementationPlanValidator(spec_dir)

    # Act
    result = validator.validate()

    # Assert
    assert isinstance(result, ValidationResult)
    assert result.checkpoint == "plan"


class TestImplementationPlanValidatorMissingFields:
    """Tests for missing required fields in implementation plan."""

    def test_missing_feature_field(self, tmp_path):
        """Test validation when 'feature' field is missing."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            # Missing "feature" field
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase1",
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask1", "description": "Test", "status": "pending"}
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("Missing required field: feature" in e for e in result.errors)

    def test_missing_workflow_type_field(self, tmp_path):
        """Test validation when 'workflow_type' field is missing."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            # Missing "workflow_type"
            "phases": [
                {
                    "id": "phase1",
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask1", "description": "Test", "status": "pending"}
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("Missing required field: workflow_type" in e for e in result.errors)

    def test_missing_phases_field(self, tmp_path):
        """Test validation when 'phases' field is missing."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature"
            # Missing "phases"
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("Missing required field: phases" in e for e in result.errors)


class TestImplementationPlanValidatorWorkflowType:
    """Tests for workflow_type validation."""

    def test_invalid_workflow_type(self, tmp_path):
        """Test validation with invalid workflow_type."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "workflow_type": "invalid_type",
            "phases": [
                {
                    "id": "phase1",
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask1", "description": "Test", "status": "pending"}
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("Invalid workflow_type: invalid_type" in e for e in result.errors)

    def test_valid_workflow_types(self, tmp_path):
        """Test all valid workflow types pass validation."""

        spec_dir = tmp_path / "spec"

        for workflow_type in IMPLEMENTATION_PLAN_SCHEMA["workflow_types"]:
            spec_dir.mkdir(exist_ok=True)
            plan_file = spec_dir / "implementation_plan.json"
            plan = {
                "feature": "Test feature",
                "workflow_type": workflow_type,
                "phases": [
                    {
                        "id": "phase1",
                        "name": "Phase 1",
                        "subtasks": [
                            {"id": "subtask1", "description": "Test", "status": "pending"}
                        ]
                    }
                ]
            }
            plan_file.write_text(json.dumps(plan), encoding="utf-8")

            validator = ImplementationPlanValidator(spec_dir)
            result = validator.validate()

            # Should not have workflow_type error (may have other errors)
            assert not any(
                "Invalid workflow_type" in e for e in result.errors
            ), f"Failed for workflow_type: {workflow_type}"

            # Clean up for next iteration
            plan_file.unlink()


class TestImplementationPlanValidatorPhases:
    """Tests for phases validation."""

    def test_empty_phases_list(self, tmp_path):
        """Test validation with empty phases list."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": []
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("No phases defined" in e for e in result.errors)

    def test_phase_missing_name(self, tmp_path):
        """Test validation when phase is missing 'name' field."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase1",
                    # Missing "name"
                    "subtasks": [
                        {"id": "subtask1", "description": "Test", "status": "pending"}
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("missing required field 'name'" in e for e in result.errors)

    def test_phase_missing_subtasks(self, tmp_path):
        """Test validation when phase is missing 'subtasks' field."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase1",
                    "name": "Phase 1"
                    # Missing "subtasks"
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("missing required field 'subtasks'" in e for e in result.errors)

    def test_phase_missing_id_and_phase(self, tmp_path):
        """Test validation when phase has neither 'id' nor 'phase' field."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask1", "description": "Test", "status": "pending"}
                    ]
                    # Missing both "id" and "phase"
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("missing required field (need one of:" in e for e in result.errors)

    def test_phase_with_legacy_phase_field(self, tmp_path):
        """Test validation supports legacy 'phase' field (numeric)."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "phase": 1,  # Legacy format
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask1", "description": "Test", "status": "pending"}
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        # Should not have field requirement errors
        assert not any("missing required field" in e for e in result.errors)

    def test_phase_invalid_type(self, tmp_path):
        """Test validation with invalid phase type."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase1",
                    "name": "Phase 1",
                    "type": "invalid_type",
                    "subtasks": [
                        {"id": "subtask1", "description": "Test", "status": "pending"}
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("invalid type 'invalid_type'" in e for e in result.errors)

    def test_valid_phase_types(self, tmp_path):
        """Test all valid phase types pass validation."""

        spec_dir = tmp_path / "spec"

        for phase_type in IMPLEMENTATION_PLAN_SCHEMA["phase_schema"]["phase_types"]:
            spec_dir.mkdir(exist_ok=True)
            plan_file = spec_dir / "implementation_plan.json"
            plan = {
                "feature": "Test feature",
                "workflow_type": "feature",
                "phases": [
                    {
                        "id": f"phase_{phase_type}",
                        "name": "Phase 1",
                        "type": phase_type,
                        "subtasks": [
                            {"id": "subtask1", "description": "Test", "status": "pending"}
                        ]
                    }
                ]
            }
            plan_file.write_text(json.dumps(plan), encoding="utf-8")

            validator = ImplementationPlanValidator(spec_dir)
            result = validator.validate()

            # Should not have type error
            assert not any("invalid type" in e for e in result.errors), f"Failed for type: {phase_type}"

            plan_file.unlink()


class TestImplementationPlanValidatorSubtasks:
    """Tests for subtask validation."""

    def test_no_subtasks_in_any_phase(self, tmp_path):
        """Test validation with no subtasks defined."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {"id": "phase1", "name": "Phase 1", "subtasks": []},
                {"id": "phase2", "name": "Phase 2", "subtasks": []}
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("No subtasks defined in any phase" in e for e in result.errors)

    def test_subtask_missing_id(self, tmp_path):
        """Test validation when subtask is missing 'id' field."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase1",
                    "name": "Phase 1",
                    "subtasks": [
                        # Missing "id"
                        {"description": "Test", "status": "pending"}
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("missing required field 'id'" in e for e in result.errors)

    def test_subtask_missing_description(self, tmp_path):
        """Test validation when subtask is missing 'description' field."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase1",
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask1", "status": "pending"}  # Missing description
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("missing required field 'description'" in e for e in result.errors)

    def test_subtask_missing_status(self, tmp_path):
        """Test validation when subtask is missing 'status' field."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase1",
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask1", "description": "Test"}  # Missing status
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("missing required field 'status'" in e for e in result.errors)

    def test_subtask_invalid_status(self, tmp_path):
        """Test validation with invalid subtask status."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase1",
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask1", "description": "Test", "status": "invalid_status"}
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("invalid status 'invalid_status'" in e for e in result.errors)

    def test_valid_status_values(self, tmp_path):
        """Test all valid status values pass validation."""

        spec_dir = tmp_path / "spec"

        for status in IMPLEMENTATION_PLAN_SCHEMA["subtask_schema"]["status_values"]:
            spec_dir.mkdir(exist_ok=True)
            plan_file = spec_dir / "implementation_plan.json"
            plan = {
                "feature": "Test feature",
                "workflow_type": "feature",
                "phases": [
                    {
                        "id": "phase1",
                        "name": "Phase 1",
                        "subtasks": [
                            {"id": f"subtask_{status}", "description": "Test", "status": status}
                        ]
                    }
                ]
            }
            plan_file.write_text(json.dumps(plan), encoding="utf-8")

            validator = ImplementationPlanValidator(spec_dir)
            result = validator.validate()

            # Should not have status error
            assert not any("invalid status" in e for e in result.errors), f"Failed for status: {status}"

            plan_file.unlink()


class TestImplementationPlanValidatorVerification:
    """Tests for verification validation."""

    def test_verification_missing_type(self, tmp_path):
        """Test validation when verification is missing 'type' field."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase1",
                    "name": "Phase 1",
                    "subtasks": [
                        {
                            "id": "subtask1",
                            "description": "Test",
                            "status": "pending",
                            "verification": {"command": "echo test"}  # Missing type
                        }
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("verification missing 'type'" in e for e in result.errors)

    def test_verification_invalid_type(self, tmp_path):
        """Test validation with invalid verification type."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase1",
                    "name": "Phase 1",
                    "subtasks": [
                        {
                            "id": "subtask1",
                            "description": "Test",
                            "status": "pending",
                            "verification": {"type": "invalid_type"}
                        }
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("invalid verification type 'invalid_type'" in e for e in result.errors)

    def test_valid_verification_types(self, tmp_path):
        """Test all valid verification types pass validation."""

        spec_dir = tmp_path / "spec"

        for verif_type in IMPLEMENTATION_PLAN_SCHEMA["verification_schema"]["verification_types"]:
            spec_dir.mkdir(exist_ok=True)
            plan_file = spec_dir / "implementation_plan.json"
            plan = {
                "feature": "Test feature",
                "workflow_type": "feature",
                "phases": [
                    {
                        "id": "phase1",
                        "name": "Phase 1",
                        "subtasks": [
                            {
                                "id": f"subtask_{verif_type}",
                                "description": "Test",
                                "status": "pending",
                                "verification": {"type": verif_type}
                            }
                        ]
                    }
                ]
            }
            plan_file.write_text(json.dumps(plan), encoding="utf-8")

            validator = ImplementationPlanValidator(spec_dir)
            result = validator.validate()

            # Should not have verification type error
            assert not any("invalid verification type" in e for e in result.errors), f"Failed for type: {verif_type}"

            plan_file.unlink()


class TestImplementationPlanValidatorDependencies:
    """Tests for dependency validation."""

    def test_dependency_on_nonexistent_phase(self, tmp_path):
        """Test validation with dependency on non-existent phase."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase1",
                    "name": "Phase 1",
                    "depends_on": ["nonexistent_phase"],
                    "subtasks": [
                        {"id": "subtask1", "description": "Test", "status": "pending"}
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("depends on non-existent phase nonexistent_phase" in e for e in result.errors)

    def test_forward_dependency_creates_cycle(self, tmp_path):
        """Test validation detects forward references (cycles)."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase2",
                    "name": "Phase 2",
                    "depends_on": ["phase3"],  # Forward reference
                    "subtasks": [
                        {"id": "subtask1", "description": "Test", "status": "pending"}
                    ]
                },
                {
                    "id": "phase3",
                    "name": "Phase 3",
                    "subtasks": [
                        {"id": "subtask2", "description": "Test", "status": "pending"}
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("would create cycle" in e for e in result.errors)

    def test_backward_dependency_valid(self, tmp_path):
        """Test validation allows backward dependencies."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase1",
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask1", "description": "Test", "status": "pending"}
                    ]
                },
                {
                    "id": "phase2",
                    "name": "Phase 2",
                    "depends_on": ["phase1"],  # Valid: depends on earlier phase
                    "subtasks": [
                        {"id": "subtask2", "description": "Test", "status": "pending"}
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        # Should not have dependency errors
        assert not any("depends on" in e for e in result.errors)

    def test_legacy_numeric_phase_dependencies(self, tmp_path):
        """Test dependency validation works with legacy numeric phase IDs."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "phase": 1,
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask1", "description": "Test", "status": "pending"}
                    ]
                },
                {
                    "phase": 2,
                    "name": "Phase 2",
                    "depends_on": [1],  # Valid: depends on earlier numeric phase
                    "subtasks": [
                        {"id": "subtask2", "description": "Test", "status": "pending"}
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        # Should not have dependency errors
        assert not any("depends on" in e for e in result.errors)

    def test_mixed_id_formats_dependencies(self, tmp_path):
        """Test dependency validation with mixed id/phase formats."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "phase": 1,  # Legacy format
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask1", "description": "Test", "status": "pending"}
                    ]
                },
                {
                    "id": "phase2",  # New format
                    "name": "Phase 2",
                    "depends_on": [1],  # Can reference legacy numeric phase
                    "subtasks": [
                        {"id": "subtask2", "description": "Test", "status": "pending"}
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        # Should not have "non-existent" errors
        assert not any("non-existent phase" in e for e in result.errors)


class TestImplementationPlanValidatorFullyValid:
    """Tests for fully valid implementation plans."""

    def test_complete_valid_plan_with_all_fields(self, tmp_path):
        """Test validation passes for a complete valid plan."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Test feature",
            "description": "Test description",
            "workflow_type": "feature",
            "workflow_rationale": "Testing workflow",
            "services_involved": ["api", "frontend"],
            "phases": [
                {
                    "id": "setup",
                    "name": "Setup Phase",
                    "type": "setup",
                    "description": "Initial setup",
                    "depends_on": [],
                    "parallel_safe": True,
                    "subtasks": [
                        {
                            "id": "setup-1",
                            "description": "Install dependencies",
                            "status": "pending",
                            "service": "api",
                            "files_to_modify": ["requirements.txt"],
                            "verification": {
                                "type": "command",
                                "command": "pip check"
                            }
                        }
                    ]
                },
                {
                    "id": "implementation",
                    "name": "Implementation Phase",
                    "type": "implementation",
                    "depends_on": ["setup"],
                    "subtasks": [
                        {
                            "id": "impl-1",
                            "description": "Implement feature",
                            "status": "pending",
                            "verification": {
                                "type": "api",
                                "url": "/api/test",
                                "method": "GET",
                                "expect_status": 200
                            }
                        }
                    ]
                }
            ],
            "final_acceptance": ["All tests pass"],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "spec_file": "spec.md",
            "status": "pending"
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True
        assert len(result.errors) == 0
        assert result.checkpoint == "plan"

    def test_valid_plan_with_multiple_phases_and_subtasks(self, tmp_path):
        """Test validation with multiple phases and subtasks."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {
            "feature": "Complex feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase1",
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "s1", "description": "Task 1", "status": "pending"},
                        {"id": "s2", "description": "Task 2", "status": "in_progress"},
                        {"id": "s3", "description": "Task 3", "status": "completed"}
                    ]
                },
                {
                    "id": "phase2",
                    "name": "Phase 2",
                    "depends_on": ["phase1"],
                    "subtasks": [
                        {"id": "s4", "description": "Task 4", "status": "pending"},
                        {"id": "s5", "description": "Task 5", "status": "blocked"}
                    ]
                },
                {
                    "id": "phase3",
                    "name": "Phase 3",
                    "depends_on": ["phase2"],
                    "subtasks": [
                        {"id": "s6", "description": "Task 6", "status": "pending"}
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = ImplementationPlanValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True
        assert len(result.errors) == 0
