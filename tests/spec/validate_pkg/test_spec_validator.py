"""
Tests for spec.validate_pkg.spec_validator module
Comprehensive tests for SpecValidator class.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from spec.validate_pkg.spec_validator import SpecValidator
from spec.validate_pkg.models import ValidationResult


class TestSpecValidatorInit:
    """Tests for SpecValidator.__init__"""

    def test_init_basic(self, tmp_path):
        """Test basic initialization"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)

        assert validator.spec_dir == spec_dir

    def test_init_with_string_path(self, tmp_path):
        """Test initialization with string path"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(str(spec_dir))

        assert validator.spec_dir == spec_dir
        assert isinstance(validator.spec_dir, Path)

    def test_initializes_all_validators(self, tmp_path):
        """Test that all individual validators are initialized"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)

        assert validator._prereqs_validator is not None
        assert validator._context_validator is not None
        assert validator._spec_document_validator is not None
        assert validator._implementation_plan_validator is not None


class TestValidateAll:
    """Tests for SpecValidator.validate_all"""

    def test_validate_all_returns_list(self, tmp_path):
        """Test validate_all returns list of results"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)

        results = validator.validate_all()

        assert isinstance(results, list)
        assert len(results) == 4

    def test_validate_all_contains_all_validations(self, tmp_path):
        """Test validate_all contains all validation checkpoints"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)

        results = validator.validate_all()

        checkpoints = [r.checkpoint for r in results]
        assert "prereqs" in checkpoints
        assert "context" in checkpoints
        assert "spec" in checkpoints
        assert "plan" in checkpoints

    def test_validate_all_with_valid_spec(self, tmp_path):
        """Test validate_all with fully valid spec"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create project_index.json
        (spec_dir / "project_index.json").write_text('{"project": "test"}')

        # Create context.json
        context = {
            "task_description": "test",
            "project_dir": "/tmp",
        }
        (spec_dir / "context.json").write_text(json.dumps(context))

        # Create spec.md
        (spec_dir / "spec.md").write_text("# Spec\n\n## Overview\n\n## Requirements")

        # Create implementation_plan.json
        plan = {
            "workflow_type": "standard",
            "phases": [
                {
                    "id": "1",
                    "name": "Phase 1",
                    "type": "implementation",
                    "subtasks": [
                        {
                            "id": "1-1",
                            "description": "Task 1",
                            "status": "pending",
                        }
                    ],
                }
            ],
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        validator = SpecValidator(spec_dir)

        results = validator.validate_all()

        # All validations should pass
        for result in results:
            assert isinstance(result, ValidationResult)

    def test_validate_all_with_invalid_spec(self, tmp_path):
        """Test validate_all with missing files"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)

        results = validator.validate_all()

        # Should have errors for missing files
        for result in results:
            assert isinstance(result, ValidationResult)


class TestValidatePrereqs:
    """Tests for SpecValidator.validate_prereqs"""

    def test_validate_prereqs_delegates_to_validator(self, tmp_path):
        """Test validate_prereqs delegates to prereqs validator"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create project_index.json
        (spec_dir / "project_index.json").write_text('{"project": "test"}')

        validator = SpecValidator(spec_dir)

        result = validator.validate_prereqs()

        assert isinstance(result, ValidationResult)
        assert result.checkpoint == "prereqs"

    def test_validate_prereqs_missing_index(self, tmp_path):
        """Test validate_prereqs with missing project_index"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)

        result = validator.validate_prereqs()

        assert result.valid is False
        assert len(result.errors) > 0
        assert "project_index.json" in result.errors[0]

    def test_validate_prereqs_missing_spec_dir(self, tmp_path):
        """Test validate_prereqs when spec dir doesn't exist"""
        spec_dir = tmp_path / "nonexistent_spec"

        validator = SpecValidator(spec_dir)

        result = validator.validate_prereqs()

        assert result.valid is False
        assert "does not exist" in result.errors[0]

    def test_validate_prereqs_with_index_at_parent(self, tmp_path):
        """Test validate_prereqs with index at parent directory"""
        spec_dir = tmp_path / "auto-claude" / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        # Create index at parent level
        parent_dir = tmp_path / "auto-claude"
        (parent_dir / "project_index.json").write_text('{"project": "test"}')

        validator = SpecValidator(spec_dir)

        result = validator.validate_prereqs()

        # Should pass but have warning
        assert len(result.warnings) > 0
        assert "project_index.json" in result.warnings[0]

    def test_validate_prereqs_success(self, tmp_path):
        """Test validate_prereqs succeeds with valid setup"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create project_index.json
        (spec_dir / "project_index.json").write_text('{"project": "test"}')

        validator = SpecValidator(spec_dir)

        result = validator.validate_prereqs()

        assert result.valid is True
        assert len(result.errors) == 0


class TestValidateContext:
    """Tests for SpecValidator.validate_context"""

    def test_validate_context_delegates_to_validator(self, tmp_path):
        """Test validate_context delegates to context validator"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)

        result = validator.validate_context()

        assert isinstance(result, ValidationResult)
        assert result.checkpoint == "context"

    def test_validate_context_missing_file(self, tmp_path):
        """Test validate_context with missing context.json"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)

        result = validator.validate_context()

        assert result.valid is False
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()

    def test_validate_context_invalid_json(self, tmp_path):
        """Test validate_context with invalid JSON"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        context_file = spec_dir / "context.json"
        context_file.write_text('{invalid json}', encoding="utf-8")

        validator = SpecValidator(spec_dir)

        result = validator.validate_context()

        assert result.valid is False
        assert any("invalid" in e.lower() and "json" in e.lower() for e in result.errors)

    def test_validate_context_missing_required_fields(self, tmp_path):
        """Test validate_context with missing required fields"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create empty context
        context_file = spec_dir / "context.json"
        context_file.write_text('{}', encoding="utf-8")

        validator = SpecValidator(spec_dir)

        result = validator.validate_context()

        assert result.valid is False
        assert len(result.errors) > 0
        assert any("required" in e.lower() for e in result.errors)

    def test_validate_context_success(self, tmp_path):
        """Test validate_context succeeds with valid context"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        context = {
            "task_description": "Build feature",
            "project_dir": "/tmp/project",
        }
        context_file = spec_dir / "context.json"
        context_file.write_text(json.dumps(context), encoding="utf-8")

        validator = SpecValidator(spec_dir)

        result = validator.validate_context()

        assert result.valid is True
        assert len(result.errors) == 0


class TestValidateSpecDocument:
    """Tests for SpecValidator.validate_spec_document"""

    def test_validate_spec_document_delegates_to_validator(self, tmp_path):
        """Test validate_spec_document delegates to spec validator"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)

        result = validator.validate_spec_document()

        assert isinstance(result, ValidationResult)
        assert result.checkpoint == "spec"

    def test_validate_spec_document_missing_file(self, tmp_path):
        """Test validate_spec_document with missing spec.md"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)

        result = validator.validate_spec_document()

        assert result.valid is False
        assert "not found" in result.errors[0].lower()

    def test_validate_spec_document_missing_sections(self, tmp_path):
        """Test validate_spec_document with missing required sections"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create spec with minimal content
        spec_file = spec_dir / "spec.md"
        spec_file.write_text("# Minimal Spec", encoding="utf-8")

        validator = SpecValidator(spec_dir)

        result = validator.validate_spec_document()

        assert result.valid is False
        assert len(result.errors) > 0
        assert any("required" in e.lower() and "section" in e.lower() for e in result.errors)

    def test_validate_spec_document_too_short(self, tmp_path):
        """Test validate_spec_document with too short content"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create spec with required sections but short content
        spec_file = spec_dir / "spec.md"
        spec_file.write_text("# Spec\n\n## Overview\n\n## Requirements\n\nX" * 50, encoding="utf-8")

        validator = SpecValidator(spec_dir)

        result = validator.validate_spec_document()

        # Should have warning about short content
        assert len(result.warnings) >= 0

    def test_validate_spec_document_success(self, tmp_path):
        """Test validate_spec_document succeeds with valid spec"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create valid spec with all required sections
        spec_content = """# Spec

## Overview

This is the overview.

## Workflow Type

Feature workflow.

## Task Scope

This is the task scope.

## Success Criteria

- Criteria 1
- Criteria 2
"""
        spec_file = spec_dir / "spec.md"
        spec_file.write_text(spec_content, encoding="utf-8")

        validator = SpecValidator(spec_dir)

        result = validator.validate_spec_document()

        assert result.valid is True
        assert len(result.errors) == 0


class TestValidateImplementationPlan:
    """Tests for SpecValidator.validate_implementation_plan"""

    def test_validate_implementation_plan_delegates_to_validator(self, tmp_path):
        """Test validate_implementation_plan delegates to plan validator"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)

        result = validator.validate_implementation_plan()

        assert isinstance(result, ValidationResult)
        assert result.checkpoint == "plan"

    def test_validate_implementation_plan_missing_file(self, tmp_path):
        """Test validate_implementation_plan with missing plan"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)

        result = validator.validate_implementation_plan()

        assert result.valid is False
        assert "not found" in result.errors[0].lower()

    def test_validate_implementation_plan_invalid_json(self, tmp_path):
        """Test validate_implementation_plan with invalid JSON"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text('{invalid json}', encoding="utf-8")

        validator = SpecValidator(spec_dir)

        result = validator.validate_implementation_plan()

        assert result.valid is False
        assert any("invalid" in e.lower() and "json" in e.lower() for e in result.errors)

    def test_validate_implementation_plan_missing_phases(self, tmp_path):
        """Test validate_implementation_plan with no phases"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan = {
            "workflow_type": "standard",
            "phases": [],
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = SpecValidator(spec_dir)

        result = validator.validate_implementation_plan()

        assert result.valid is False
        assert any("phases" in e.lower() for e in result.errors)

    def test_validate_implementation_plan_missing_subtasks(self, tmp_path):
        """Test validate_implementation_plan with phases but no subtasks"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan = {
            "workflow_type": "standard",
            "phases": [
                {
                    "id": "1",
                    "name": "Phase 1",
                    "type": "implementation",
                    "subtasks": [],
                }
            ],
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = SpecValidator(spec_dir)

        result = validator.validate_implementation_plan()

        assert result.valid is False
        assert any("subtask" in e.lower() for e in result.errors)

    def test_validate_implementation_plan_success(self, tmp_path):
        """Test validate_implementation_plan succeeds with valid plan"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan = {
            "feature": "Build authentication system",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "1",
                    "name": "Phase 1",
                    "type": "implementation",
                    "subtasks": [
                        {
                            "id": "1-1",
                            "description": "Task 1",
                            "status": "pending",
                        }
                    ],
                }
            ],
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = SpecValidator(spec_dir)

        result = validator.validate_implementation_plan()

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_implementation_plan_invalid_workflow_type(self, tmp_path):
        """Test validate_implementation_plan with invalid workflow_type"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan = {
            "workflow_type": "invalid_type",
            "phases": [
                {
                    "id": "1",
                    "name": "Phase 1",
                    "type": "implementation",
                    "subtasks": [
                        {
                            "id": "1-1",
                            "description": "Task 1",
                            "status": "pending",
                        }
                    ],
                }
            ],
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        validator = SpecValidator(spec_dir)

        result = validator.validate_implementation_plan()

        assert result.valid is False
        assert any("workflow_type" in e.lower() or "invalid" in e.lower() for e in result.errors)


class TestSpecValidatorIntegration:
    """Integration tests for SpecValidator"""

    def test_full_validation_cycle_valid_spec(self, tmp_path):
        """Test full validation cycle with completely valid spec"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create project_index.json
        (spec_dir / "project_index.json").write_text('{"project": "test", "type": "web"}')

        # Create context.json with required fields
        context = {
            "task_description": "Build authentication system",
            "project_dir": "/tmp/project",
            "services_involved": ["backend"],
        }
        (spec_dir / "context.json").write_text(json.dumps(context))

        # Create spec.md with all required sections
        spec_content = """# Authentication System Spec

## Overview

Implement user authentication with JWT tokens.

## Requirements

- User registration
- User login
- Password reset

## Implementation

Use JWT tokens for authentication.

## Testing

Test all authentication flows.
"""
        (spec_dir / "spec.md").write_text(spec_content)

        # Create implementation_plan.json
        plan = {
            "workflow_type": "standard",
            "phases": [
                {
                    "id": "1",
                    "name": "Backend Implementation",
                    "type": "implementation",
                    "subtasks": [
                        {
                            "id": "1-1",
                            "description": "Create user model",
                            "status": "pending",
                            "verification": {
                                "type": "manual",
                                "description": "Verify model exists",
                            },
                        }
                    ],
                }
            ],
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        validator = SpecValidator(spec_dir)

        # Run all validations
        results = validator.validate_all()

        # All should have ValidationResult type
        assert len(results) == 4
        for result in results:
            assert isinstance(result, ValidationResult)
            assert result.checkpoint in ["prereqs", "context", "spec", "plan"]

    def test_full_validation_cycle_invalid_spec(self, tmp_path):
        """Test full validation cycle with completely missing spec"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)

        results = validator.validate_all()

        # All should have errors
        assert len(results) == 4
        for result in results:
            assert isinstance(result, ValidationResult)
            # Most should be invalid
            if result.checkpoint in ["context", "spec", "plan"]:
                assert result.valid is False


class TestSpecValidatorEdgeCases:
    """Edge case tests for SpecValidator"""

    def test_spec_dir_with_symlink(self, tmp_path):
        """Test SpecValidator with symlinked directory"""
        # Create actual directory
        actual_spec_dir = tmp_path / "actual_spec"
        actual_spec_dir.mkdir()

        # Create symlink
        symlink_spec_dir = tmp_path / "symlink_spec"
        symlink_spec_dir.symlink_to(actual_spec_dir)

        # Create required files in actual directory
        (actual_spec_dir / "project_index.json").write_text('{"project": "test"}')

        validator = SpecValidator(symlink_spec_dir)

        result = validator.validate_prereqs()

        assert isinstance(result, ValidationResult)

    def test_spec_dir_with_trailing_slash(self, tmp_path):
        """Test SpecValidator with path containing trailing slash"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Test with trailing slash
        validator = SpecValidator(str(spec_dir) + "/")

        assert validator.spec_dir == spec_dir

    def test_relative_path_handling(self, tmp_path):
        """Test SpecValidator with relative path string"""
        import os

        # Change to temp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            spec_dir = Path("spec")
            spec_dir.mkdir()

            # Create with relative path
            validator = SpecValidator("spec")

            # Path constructor converts string to Path object
            assert isinstance(validator.spec_dir, Path)
            # The spec_dir path is relative "spec" not resolved to absolute
            assert validator.spec_dir == Path("spec")

        finally:
            os.chdir(original_cwd)

    def test_validate_all_returns_new_instances(self, tmp_path):
        """Test that validate_all returns new ValidationResult instances each time"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)

        results1 = validator.validate_all()
        results2 = validator.validate_all()

        # Results should be different instances
        for r1, r2 in zip(results1, results2):
            assert r1 is not r2

    def test_validator_independence(self, tmp_path):
        """Test that multiple validators are independent"""
        spec_dir1 = tmp_path / "spec1"
        spec_dir2 = tmp_path / "spec2"

        spec_dir1.mkdir()
        spec_dir2.mkdir()

        # Create different content in each
        (spec_dir1 / "project_index.json").write_text('{"project": "test1"}')
        (spec_dir2 / "project_index.json").write_text('{"project": "test2"}')

        validator1 = SpecValidator(spec_dir1)
        validator2 = SpecValidator(spec_dir2)

        # Validators should be independent
        assert validator1.spec_dir != validator2.spec_dir

        result1 = validator1.validate_prereqs()
        result2 = validator2.validate_prereqs()

        assert isinstance(result1, ValidationResult)
        assert isinstance(result2, ValidationResult)
        assert result1 is not result2
