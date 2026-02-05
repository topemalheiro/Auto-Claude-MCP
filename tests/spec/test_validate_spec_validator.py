"""Tests for spec.validate_pkg.spec_validator module"""

import json
from pathlib import Path

import pytest

from spec.validate_pkg.models import ValidationResult
from spec.validate_pkg.spec_validator import SpecValidator
from spec.validate_pkg.validators import (
    ContextValidator,
    ImplementationPlanValidator,
    PrereqsValidator,
    SpecDocumentValidator,
)


class TestSpecValidator:
    """Tests for SpecValidator class"""

    def test_init(self, tmp_path):
        """Test validator initialization"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)

        assert validator.spec_dir == spec_dir
        assert isinstance(validator._prereqs_validator, PrereqsValidator)
        assert isinstance(validator._context_validator, ContextValidator)
        assert isinstance(validator._spec_document_validator, SpecDocumentValidator)
        assert isinstance(validator._implementation_plan_validator, ImplementationPlanValidator)

    def test_init_with_path_string(self, tmp_path):
        """Test validator initialization with string path"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(str(spec_dir))

        assert validator.spec_dir == spec_dir

    def test_validate_prereqs_missing_directory(self, tmp_path):
        """Test validate_prereqs with missing spec directory"""
        spec_dir = tmp_path / "nonexistent" / "spec"

        validator = SpecValidator(spec_dir)
        result = validator.validate_prereqs()

        assert result.valid is False
        assert result.checkpoint == "prereqs"
        assert len(result.errors) > 0
        assert "does not exist" in result.errors[0]
        assert len(result.fixes) > 0

    def test_validate_prereqs_success(self, tmp_path):
        """Test validate_prereqs with valid setup"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "project_index.json").write_text('{"project_type": "test"}', encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_prereqs()

        assert result.valid is True
        assert result.checkpoint == "prereqs"
        assert len(result.errors) == 0

    def test_validate_prereqs_with_auto_claude_index(self, tmp_path):
        """Test validate_prereqs with auto-claude index"""
        # Create spec dir (this creates auto-claude and specs/001)
        spec_dir = tmp_path / "auto-claude" / "specs" / "001"
        spec_dir.mkdir(parents=True)

        # Get the auto-claude level directory
        auto_claude_dir = tmp_path / "auto-claude"
        (auto_claude_dir / "project_index.json").write_text('{"project_type": "monorepo"}', encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_prereqs()

        # Should have warning about auto-claude index
        assert result.valid is True
        assert len(result.warnings) > 0
        assert "auto-claude" in result.warnings[0]
        assert len(result.fixes) > 0

    def test_validate_prereqs_no_index(self, tmp_path):
        """Test validate_prereqs with no project index"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)
        result = validator.validate_prereqs()

        assert result.valid is False
        assert len(result.errors) > 0
        assert "project_index.json" in result.errors[0]
        assert len(result.fixes) > 0

    def test_validate_context_missing_file(self, tmp_path):
        """Test validate_context with missing context.json"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)
        result = validator.validate_context()

        assert result.valid is False
        assert result.checkpoint == "context"
        assert "not found" in result.errors[0]
        assert len(result.fixes) > 0

    def test_validate_context_invalid_json(self, tmp_path):
        """Test validate_context with invalid JSON"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "context.json").write_text('{invalid json}', encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_context()

        assert result.valid is False
        assert "invalid JSON" in result.errors[0]
        assert len(result.fixes) > 0

    def test_validate_context_missing_required_fields(self, tmp_path):
        """Test validate_context with missing required fields"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "context.json").write_text('{"other": "data"}', encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_context()

        assert result.valid is False
        assert "Missing required field" in result.errors[0]
        assert "task_description" in result.errors[0]

    def test_validate_context_with_warnings(self, tmp_path):
        """Test validate_context generates warnings for missing recommended fields"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "context.json").write_text('{"task_description": "Build feature"}', encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_context()

        assert result.valid is True
        assert len(result.warnings) > 0
        assert any("files_to_modify" in w for w in result.warnings)

    def test_validate_context_success(self, tmp_path):
        """Test validate_context with valid context"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_data = {
            "task_description": "Build feature",
            "files_to_modify": ["file1.ts"],
            "files_to_reference": ["file2.ts"],
            "scoped_services": ["frontend"],
        }
        (spec_dir / "context.json").write_text(json.dumps(context_data), encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_context()

        assert result.valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_validate_spec_document_missing(self, tmp_path):
        """Test validate_spec_document with missing spec.md"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)
        result = validator.validate_spec_document()

        assert result.valid is False
        assert result.checkpoint == "spec"
        assert "not found" in result.errors[0]
        assert len(result.fixes) > 0

    def test_validate_spec_document_missing_required_sections(self, tmp_path):
        """Test validate_spec_document with missing required sections"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Some content\n\nNot enough sections.", encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_spec_document()

        assert result.valid is False
        assert len(result.errors) >= 4  # Missing 4 required sections
        assert any("Overview" in e for e in result.errors)

    def test_validate_spec_document_success(self, tmp_path):
        """Test validate_spec_document with valid spec"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_content = """# Overview

This is a test spec.

## Workflow Type

Feature

## Task Scope

Build a feature.

## Success Criteria

- Feature works
- Tests pass
"""
        (spec_dir / "spec.md").write_text(spec_content, encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_spec_document()

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_spec_document_short_content_warning(self, tmp_path):
        """Test validate_spec_document warns on short content"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        # Short content with required sections
        spec_content = """## Overview
Test

## Workflow Type
Feature

## Task Scope
Test

## Success Criteria
Test
"""
        (spec_dir / "spec.md").write_text(spec_content, encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_spec_document()

        assert result.valid is True
        assert any("too short" in w for w in result.warnings)

    def test_validate_implementation_plan_missing(self, tmp_path):
        """Test validate_implementation_plan with missing plan"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)
        result = validator.validate_implementation_plan()

        assert result.valid is False
        assert result.checkpoint == "plan"
        assert "not found" in result.errors[0]
        assert len(result.fixes) > 0

    def test_validate_implementation_plan_invalid_json(self, tmp_path):
        """Test validate_implementation_plan with invalid JSON"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "implementation_plan.json").write_text('{invalid}', encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_implementation_plan()

        assert result.valid is False
        assert "invalid JSON" in result.errors[0]

    def test_validate_implementation_plan_missing_required_fields(self, tmp_path):
        """Test validate_implementation_plan with missing required fields"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "implementation_plan.json").write_text('{"other": "data"}', encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_implementation_plan()

        assert result.valid is False
        assert any("feature" in e for e in result.errors)
        assert any("workflow_type" in e for e in result.errors)

    def test_validate_implementation_plan_invalid_workflow_type(self, tmp_path):
        """Test validate_implementation_plan with invalid workflow_type"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan = {
            "feature": "Test feature",
            "workflow_type": "invalid_type",
            "phases": [],
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan), encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_implementation_plan()

        assert result.valid is False
        assert any("Invalid workflow_type" in e for e in result.errors)

    def test_validate_implementation_plan_no_phases(self, tmp_path):
        """Test validate_implementation_plan with no phases"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [],
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan), encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_implementation_plan()

        assert result.valid is False
        assert any("No phases" in e for e in result.errors)

    def test_validate_implementation_plan_valid(self, tmp_path):
        """Test validate_implementation_plan with valid plan"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase1",
                    "name": "Setup",
                    "type": "setup",
                    "subtasks": [
                        {
                            "id": "task1",
                            "description": "Do something",
                            "status": "pending",
                        }
                    ],
                }
            ],
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan), encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_implementation_plan()

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_implementation_plan_circular_dependency(self, tmp_path):
        """Test validate_implementation_plan detects circular dependencies"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase2",
                    "name": "Phase 2",
                    "depends_on": ["phase1"],
                    "subtasks": [{"id": "task1", "description": "Task", "status": "pending"}],
                },
                {
                    "id": "phase1",
                    "name": "Phase 1",
                    "depends_on": ["phase2"],  # Circular!
                    "subtasks": [{"id": "task2", "description": "Task", "status": "pending"}],
                },
            ],
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan), encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_implementation_plan()

        assert result.valid is False
        assert any("cycle" in e.lower() for e in result.errors)

    def test_validate_implementation_plan_missing_subtask_fields(self, tmp_path):
        """Test validate_implementation_plan with missing subtask fields"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase1",
                    "name": "Setup",
                    "subtasks": [
                        {
                            # Missing required fields
                        }
                    ],
                }
            ],
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan), encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_implementation_plan()

        assert result.valid is False
        assert any("missing required field" in e for e in result.errors)

    def test_validate_implementation_plan_invalid_verification(self, tmp_path):
        """Test validate_implementation_plan with invalid verification"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase1",
                    "name": "Setup",
                    "subtasks": [
                        {
                            "id": "task1",
                            "description": "Do something",
                            "status": "pending",
                            "verification": {
                                # Missing 'type' field
                                "command": "echo test",
                            },
                        }
                    ],
                }
            ],
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan), encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_implementation_plan()

        assert result.valid is False
        assert any("verification" in e.lower() for e in result.errors)

    def test_validate_all(self, tmp_path):
        """Test validate_all runs all validators"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create minimal valid files
        (spec_dir / "project_index.json").write_text('{"project_type": "test"}', encoding="utf-8")
        (spec_dir / "context.json").write_text('{"task_description": "Test"}', encoding="utf-8")
        (spec_dir / "spec.md").write_text(
            "## Overview\nTest\n## Workflow Type\nFeature\n## Task Scope\nTest\n## Success Criteria\nTest",
            encoding="utf-8",
        )
        plan = {
            "feature": "Test",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "p1",
                    "name": "Phase",
                    "subtasks": [{"id": "t1", "description": "Task", "status": "pending"}],
                }
            ],
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan), encoding="utf-8")

        validator = SpecValidator(spec_dir)
        results = validator.validate_all()

        assert len(results) == 4
        assert all(isinstance(r, ValidationResult) for r in results)
        assert results[0].checkpoint == "prereqs"
        assert results[1].checkpoint == "context"
        assert results[2].checkpoint == "spec"
        assert results[3].checkpoint == "plan"

    def test_validate_all_with_failures(self, tmp_path):
        """Test validate_all returns failures for invalid spec"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)
        results = validator.validate_all()

        assert len(results) == 4
        # All should fail since no files exist
        assert all(not r.valid for r in results)

    def test_result_string_formatting(self, tmp_path):
        """Test ValidationResult __str__ method"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = SpecValidator(spec_dir)
        result = validator.validate_prereqs()

        result_str = str(result)
        assert "Checkpoint:" in result_str
        assert "Status:" in result_str

        if result.errors:
            assert "Errors:" in result_str
        if result.warnings:
            assert "Warnings:" in result_str
        if result.fixes and not result.valid:
            assert "Suggested Fixes:" in result_str

    def test_implementation_plan_legacy_format(self, tmp_path):
        """Test validate_implementation_plan with legacy phase numbers"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "phase": 1,  # Legacy format
                    "name": "Setup",
                    "subtasks": [
                        {
                            "id": "task1",
                            "description": "Do something",
                            "status": "pending",
                        }
                    ],
                }
            ],
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan), encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_implementation_plan()

        assert result.valid is True
        assert len(result.errors) == 0

    def test_implementation_plan_no_subtasks(self, tmp_path):
        """Test validate_implementation_plan with phases but no subtasks"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase1",
                    "name": "Setup",
                    "subtasks": [],  # Empty subtasks
                }
            ],
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan), encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_implementation_plan()

        assert result.valid is False
        assert any("No subtasks" in e for e in result.errors)

    def test_implementation_plan_invalid_status(self, tmp_path):
        """Test validate_implementation_plan with invalid subtask status"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase1",
                    "name": "Setup",
                    "subtasks": [
                        {
                            "id": "task1",
                            "description": "Do something",
                            "status": "invalid_status",
                        }
                    ],
                }
            ],
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan), encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_implementation_plan()

        assert result.valid is False
        assert any("invalid status" in e.lower() for e in result.errors)

    def test_implementation_plan_nonexistent_dependency(self, tmp_path):
        """Test validate_implementation_plan with dependency on non-existent phase"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase1",
                    "name": "Phase 1",
                    "depends_on": ["nonexistent_phase"],
                    "subtasks": [{"id": "task1", "description": "Task", "status": "pending"}],
                }
            ],
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan), encoding="utf-8")

        validator = SpecValidator(spec_dir)
        result = validator.validate_implementation_plan()

        assert result.valid is False
        assert any("non-existent" in e.lower() for e in result.errors)
