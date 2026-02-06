"""Tests for planner_lib.models module."""

import json
from pathlib import Path

import pytest

from planner_lib.models import PlannerContext
from implementation_plan import WorkflowType


class TestPlannerContext:
    """Tests for PlannerContext dataclass."""

    def test_create_planner_context_minimal(self):
        """Test creating PlannerContext with minimal data."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        assert context.spec_content == "# Test"
        assert context.project_index == {}
        assert context.task_context == {}
        assert context.services_involved == []
        assert context.workflow_type == WorkflowType.FEATURE
        assert context.files_to_modify == []
        assert context.files_to_reference == []

    def test_create_planner_context_full(self):
        """Test creating PlannerContext with all fields."""
        context = PlannerContext(
            spec_content="# Full Test Spec",
            project_index={"files": []},
            task_context={"description": "Test task"},
            services_involved=["api", "database"],
            workflow_type=WorkflowType.REFACTOR,
            files_to_modify=[{"path": "test.py"}],
            files_to_reference=[{"path": "ref.py"}],
        )
        assert context.spec_content == "# Full Test Spec"
        assert context.project_index == {"files": []}
        assert context.task_context == {"description": "Test task"}
        assert context.services_involved == ["api", "database"]
        assert context.workflow_type == WorkflowType.REFACTOR
        assert context.files_to_modify == [{"path": "test.py"}]
        assert context.files_to_reference == [{"path": "ref.py"}]

    def test_planner_context_with_complex_project_index(self):
        """Test PlannerContext with complex project index."""
        project_index = {
            "files": [
                {"path": "src/main.py", "type": "module"},
                {"path": "tests/test_main.py", "type": "test"},
            ],
            "dependencies": ["pytest", "requests"],
            "structure": {"src": True, "tests": True},
        }
        context = PlannerContext(
            spec_content="Test",
            project_index=project_index,
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        assert len(context.project_index["files"]) == 2
        assert context.project_index["dependencies"] == ["pytest", "requests"]

    def test_planner_context_with_task_context(self):
        """Test PlannerContext with detailed task context."""
        task_context = {
            "description": "Add authentication",
            "files_to_modify": ["auth.py"],
            "patterns_to_follow": ["Use decorators"],
        }
        context = PlannerContext(
            spec_content="Test",
            project_index={},
            task_context=task_context,
            services_involved=["auth"],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        assert context.task_context["description"] == "Add authentication"
        assert "auth.py" in context.task_context["files_to_modify"]

    def test_planner_context_workflow_type_variations(self):
        """Test PlannerContext with different workflow types."""
        workflow_types = [
            WorkflowType.FEATURE,
            WorkflowType.REFACTOR,
            WorkflowType.INVESTIGATION,
            WorkflowType.MIGRATION,
            WorkflowType.SIMPLE,
            WorkflowType.DEVELOPMENT,
            WorkflowType.ENHANCEMENT,
        ]
        for workflow in workflow_types:
            context = PlannerContext(
                spec_content="Test",
                project_index={},
                task_context={},
                services_involved=[],
                workflow_type=workflow,
                files_to_modify=[],
                files_to_reference=[],
            )
            assert context.workflow_type == workflow

    def test_planner_context_with_files(self):
        """Test PlannerContext with files lists."""
        context = PlannerContext(
            spec_content="Test",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[
                {"path": "src/auth.py", "service": "auth"},
                {"path": "src/models.py", "service": "database"},
            ],
            files_to_reference=[
                {"path": "utils/helpers.py", "reason": "similar patterns"},
            ],
        )
        assert len(context.files_to_modify) == 2
        assert len(context.files_to_reference) == 1
        assert context.files_to_modify[0]["service"] == "auth"


class TestPlannerContextEdgeCases:
    """Edge case tests for planner_lib models."""

    def test_planner_context_with_unicode_content(self):
        """Test PlannerContext with unicode characters."""
        context = PlannerContext(
            spec_content="# Spécïal Çharacters with ñ and emojís 🎉",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        assert "Çharacters" in context.spec_content
        assert "🎉" in context.spec_content

    def test_planner_context_with_very_long_content(self):
        """Test PlannerContext with very long content."""
        content = "# Long Spec\n" + "Line\n" * 10000
        context = PlannerContext(
            spec_content=content,
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        assert len(context.spec_content) > 50000

    def test_planner_context_immutability(self):
        """Test that PlannerContext fields can be modified (dataclass is mutable)."""
        context = PlannerContext(
            spec_content="Test",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        # Should be mutable (dataclass default)
        context.spec_content = "Modified"
        assert context.spec_content == "Modified"

        context.project_index["new_key"] = "value"
        assert "new_key" in context.project_index


class TestPlannerModelsIntegration:
    """Integration tests for planner_lib models."""

    def test_complete_planner_context_creation(self):
        """Test creating complete PlannerContext with realistic data."""
        project_index = {
            "files": [
                {"path": "src/auth.py", "service": "auth"},
                {"path": "src/models.py", "service": "database"},
                {"path": "tests/test_auth.py", "service": "tests"},
            ],
            "services": ["auth", "database", "api"],
            "framework": "Flask",
        }

        task_context = {
            "description": "Add JWT-based authentication",
            "files_to_modify": ["src/auth.py", "src/models.py"],
            "files_to_create": ["src/middleware.py"],
            "patterns_to_follow": ["Use decorators for auth"],
            "dependencies": ["PyJWT"],
        }

        context = PlannerContext(
            spec_content="# User Authentication Feature",
            project_index=project_index,
            task_context=task_context,
            services_involved=["auth", "database"],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[
                {"path": "src/auth.py", "service": "auth"},
                {"path": "src/models.py", "service": "database"},
            ],
            files_to_reference=[
                {"path": "utils/helpers.py", "reason": "similar patterns"},
            ],
        )

        assert len(context.project_index["files"]) == 3
        assert "JWT" in context.task_context["description"]
        assert context.workflow_type == WorkflowType.FEATURE
        assert len(context.services_involved) == 2
        assert len(context.files_to_modify) == 2
        assert len(context.files_to_reference) == 1

    def test_planner_context_serialization_compatibility(self):
        """Test that PlannerContext structure is compatible with JSON."""
        context = PlannerContext(
            spec_content="Test",
            project_index={"files": [], "services": []},
            task_context={"description": "Test"},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        # All fields should be JSON-serializable types
        json.dumps(context.project_index)
        json.dumps(context.task_context)
