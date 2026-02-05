"""Tests for planner_lib.utils module."""

from unittest.mock import MagicMock, patch

import pytest

from implementation_plan import VerificationType, WorkflowType
from planner_lib.models import PlannerContext
from planner_lib.utils import (
    create_verification,
    determine_service_order,
    extract_acceptance_criteria,
    extract_feature_name,
    get_patterns_for_service,
    group_files_by_service,
    infer_subtask_type,
)


class TestExtractFeatureName:
    """Tests for extract_feature_name function."""

    @pytest.mark.parametrize(
        "spec_content, expected_name",
        [
            ("# Feature Name\n\nDescription", "Feature Name"),
            ("# Specification: User Authentication", "User Authentication"),
            ("# Spec: Add Login", "Add Login"),
            ("# Feature: Payment Gateway", "Payment Gateway"),
            ("# Feature Name with extra text", "Feature Name with extra text"),
            ("## Subheading\n\nNo main heading", "Unnamed Feature"),
            ("No heading at all", "Unnamed Feature"),
            ("", "Unnamed Feature"),
        ],
    )
    def test_extract_feature_name_variations(self, spec_content, expected_name):
        """Test feature name extraction with various spec formats."""
        context = PlannerContext(
            spec_content=spec_content,
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = extract_feature_name(context)
        assert result == expected_name

    def test_extract_feature_name_from_first_heading(self):
        """Test that only the first heading is used."""
        context = PlannerContext(
            spec_content="# First Title\n\n## Second Title",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = extract_feature_name(context)
        assert result == "First Title"

    def test_extract_feature_name_strips_common_prefixes(self):
        """Test that common prefixes are stripped."""
        context = PlannerContext(
            spec_content="# Specification: API Refactoring",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = extract_feature_name(context)
        assert result == "API Refactoring"

    def test_extract_feature_name_handles_unicode(self):
        """Test feature name extraction with unicode characters."""
        context = PlannerContext(
            spec_content="# Spécïal Çharacters ñ",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = extract_feature_name(context)
        assert "Çharacters" in result

    def test_extract_feature_name_very_long_title(self):
        """Test feature name extraction with very long title."""
        long_title = "A" * 500
        context = PlannerContext(
            spec_content=f"# {long_title}",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = extract_feature_name(context)
        assert len(result) == 500

    def test_extract_feature_name_looks_in_first_10_lines(self):
        """Test that only first 10 lines are searched."""
        context = PlannerContext(
            spec_content="\n".join(["Line"] * 15) + "\n# Late Heading",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = extract_feature_name(context)
        assert result == "Unnamed Feature"


class TestGroupFilesByService:
    """Tests for group_files_by_service function."""

    def test_group_files_by_service_with_explicit_service(self):
        """Test grouping files with explicit service field."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[
                {"path": "backend/auth.py", "service": "backend"},
                {"path": "frontend/App.tsx", "service": "frontend"},
                {"path": "backend/models.py", "service": "backend"},
            ],
            files_to_reference=[],
        )
        result = group_files_by_service(context)
        assert len(result) == 2
        assert len(result["backend"]) == 2
        assert len(result["frontend"]) == 1

    def test_group_files_by_service_infers_from_path(self):
        """Test service inference from file paths."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={
                "services": {
                    "backend": {"path": "apps/backend"},
                    "frontend": {"path": "apps/frontend"},
                }
            },
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[
                {"path": "apps/backend/auth.py", "service": "unknown"},
                {"path": "apps/frontend/App.tsx", "service": "unknown"},
            ],
            files_to_reference=[],
        )
        result = group_files_by_service(context)
        assert "backend" in result
        assert "frontend" in result

    def test_group_files_by_service_infers_from_service_name(self):
        """Test service inference when service name is in path."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={
                "services": {"backend": {}, "frontend": {}}
            },
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[
                {"path": "backend/auth.py", "service": "unknown"},
                {"path": "frontend/App.tsx", "service": "unknown"},
            ],
            files_to_reference=[],
        )
        result = group_files_by_service(context)
        assert "backend" in result
        assert "frontend" in result

    def test_group_files_by_service_empty_files_list(self):
        """Test grouping with empty files list."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = group_files_by_service(context)
        assert result == {}

    def test_group_files_by_service_missing_path_key(self):
        """Test handling of files without path key."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[
                {"service": "backend"},
                {"path": "frontend/App.tsx", "service": "frontend"},
            ],
            files_to_reference=[],
        )
        result = group_files_by_service(context)
        assert "backend" in result
        assert "frontend" in result

    def test_group_files_by_service_preserves_file_info(self):
        """Test that file information is preserved in groups."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[
                {"path": "backend/auth.py", "service": "backend", "reason": "add login"},
            ],
            files_to_reference=[],
        )
        result = group_files_by_service(context)
        assert result["backend"][0]["reason"] == "add login"

    def test_group_files_by_service_unknown_service_stays_unknown(self):
        """Test that files without service info remain in 'unknown' group."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[
                {"path": "some/random/file.py", "service": "unknown"},
            ],
            files_to_reference=[],
        )
        result = group_files_by_service(context)
        assert "unknown" in result

    def test_group_files_by_service_multiple_services(self):
        """Test grouping files across multiple services."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={
                "services": {
                    "api": {"path": "services/api"},
                    "worker": {"path": "services/worker"},
                    "web": {"path": "services/web"},
                }
            },
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[
                {"path": "services/api/main.py", "service": "api"},
                {"path": "services/worker/job.py", "service": "worker"},
                {"path": "services/web/App.tsx", "service": "web"},
            ],
            files_to_reference=[],
        )
        result = group_files_by_service(context)
        assert len(result) == 3
        assert "api" in result
        assert "worker" in result
        assert "web" in result


class TestGetPatternsForService:
    """Tests for get_patterns_for_service function."""

    def test_get_patterns_for_service_matching(self):
        """Test getting patterns for a specific service."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[
                {"path": "backend/auth.py", "service": "backend"},
                {"path": "backend/utils.py", "service": "backend"},
                {"path": "frontend/App.tsx", "service": "frontend"},
            ],
        )
        result = get_patterns_for_service(context, "backend")
        assert len(result) == 2
        assert "backend/auth.py" in result
        assert "backend/utils.py" in result

    def test_get_patterns_for_service_no_match(self):
        """Test getting patterns for service with no files."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[
                {"path": "frontend/App.tsx", "service": "frontend"},
            ],
        )
        result = get_patterns_for_service(context, "backend")
        assert result == []

    def test_get_patterns_for_service_unmatched_service(self):
        """Test getting patterns for files without service specified."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[
                {"path": "shared/utils.py", "service": ""},
                {"path": "helpers/common.py", "service": None},
            ],
        )
        result = get_patterns_for_service(context, "backend")
        # Files with empty/None service should match any service query
        assert len(result) == 2

    def test_get_patterns_for_service_limit_to_three(self):
        """Test that only top 3 patterns are returned."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[
                {"path": f"backend/file{i}.py", "service": "backend"}
                for i in range(5)
            ],
        )
        result = get_patterns_for_service(context, "backend")
        assert len(result) == 3

    def test_get_patterns_for_service_empty_reference_list(self):
        """Test getting patterns with empty reference list."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = get_patterns_for_service(context, "backend")
        assert result == []

    def test_get_patterns_for_service_missing_path_key(self):
        """Test handling of reference files without path key."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[
                {"service": "backend"},
                {"path": "backend/utils.py", "service": "backend"},
            ],
        )
        result = get_patterns_for_service(context, "backend")
        assert len(result) == 2
        # One should be empty string from missing path
        assert "" in result


class TestCreateVerification:
    """Tests for create_verification function."""

    def test_create_verification_for_model(self):
        """Test verification creation for model subtasks."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={"services": {}},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = create_verification(context, "backend", "model")
        assert result.type == VerificationType.COMMAND
        assert "Model created" in result.run

    def test_create_verification_for_endpoint(self):
        """Test verification creation for endpoint subtasks."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={"services": {"backend": {"port": 8000}}},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = create_verification(context, "backend", "endpoint")
        assert result.type == VerificationType.API
        assert result.method == "GET"
        assert result.url == "http://localhost:8000/health"
        assert result.expect_status == 200

    def test_create_verification_for_endpoint_without_port(self):
        """Test endpoint verification when service has no port."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={"services": {"backend": {}}},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = create_verification(context, "backend", "endpoint")
        assert result.type == VerificationType.API
        assert result.url == "/health"

    def test_create_verification_for_component(self):
        """Test verification creation for component subtasks."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={"services": {}},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = create_verification(context, "frontend", "component")
        assert result.type == VerificationType.BROWSER
        assert "Component renders" in result.scenario

    def test_create_verification_for_task(self):
        """Test verification creation for task subtasks."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={"services": {}},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = create_verification(context, "worker", "task")
        assert result.type == VerificationType.COMMAND
        assert "Task registered" in result.run

    def test_create_verification_default_manual(self):
        """Test default manual verification for unknown subtask types."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={"services": {}},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = create_verification(context, "service", "unknown_type")
        assert result.type == VerificationType.MANUAL

    def test_create_verification_all_subtask_types(self):
        """Test all known subtask types."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={"services": {"api": {"port": 8080}}},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )

        test_cases = [
            ("model", VerificationType.COMMAND),
            ("endpoint", VerificationType.API),
            ("component", VerificationType.BROWSER),
            ("task", VerificationType.COMMAND),
            ("random", VerificationType.MANUAL),
        ]

        for subtask_type, expected_type in test_cases:
            result = create_verification(context, "api", subtask_type)
            assert result.type == expected_type


class TestExtractAcceptanceCriteria:
    """Tests for extract_acceptance_criteria function."""

    def test_extract_from_success_criteria_section(self):
        """Test extracting from 'Success Criteria' section."""
        context = PlannerContext(
            spec_content="""# Feature

## Success Criteria
- Users can log in
- Sessions are secure
- Password reset works

## Implementation
""",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = extract_acceptance_criteria(context)
        assert len(result) == 3
        assert "Users can log in" in result
        assert "Sessions are secure" in result
        assert "Password reset works" in result

    def test_extract_from_acceptance_section(self):
        """Test extracting from 'Acceptance' section."""
        context = PlannerContext(
            spec_content="""# Feature

## Acceptance Criteria
- Feature works
- No errors

## Other Section
""",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = extract_acceptance_criteria(context)
        assert "Feature works" in result
        assert "No errors" in result

    def test_extract_from_done_when_section(self):
        """Test extracting from 'Done When' section."""
        context = PlannerContext(
            spec_content="""# Feature

## Done When
- Task is complete
- Tests pass

""",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = extract_acceptance_criteria(context)
        assert "Task is complete" in result
        assert "Tests pass" in result

    def test_extract_with_checkbox_format(self):
        """Test extracting checkbox-formatted criteria."""
        context = PlannerContext(
            spec_content="""# Feature

## Success Criteria
- [ ] Users can log in
- [x] Sessions are secure
- [ ] Password reset works
""",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = extract_acceptance_criteria(context)
        assert len(result) == 3

    def test_extract_stops_at_next_section(self):
        """Test that extraction stops at next heading."""
        context = PlannerContext(
            spec_content="""# Feature

## Success Criteria
- First criterion
- Second criterion

## Implementation Plan
This should not be included.
""",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = extract_acceptance_criteria(context)
        assert len(result) == 2
        assert "This should not be included" not in result

    def test_extract_with_asterisk_bullet_points(self):
        """Test extracting asterisk-formatted criteria."""
        context = PlannerContext(
            spec_content="""# Feature

## Success Criteria
* First criterion
* Second criterion
""",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = extract_acceptance_criteria(context)
        assert len(result) == 2

    def test_extract_default_generic_criteria(self):
        """Test default generic criteria when none found."""
        context = PlannerContext(
            spec_content="""# Feature

Just a description without any criteria section.
""",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = extract_acceptance_criteria(context)
        assert "Feature works as specified" in result
        assert "No console errors" in result
        # Check for full text or partial match
        assert any("regressions" in criterion.lower() for criterion in result)

    def test_extract_empty_lines_in_criteria(self):
        """Test handling of empty lines in criteria section."""
        context = PlannerContext(
            spec_content="""# Feature

## Success Criteria
- First criterion

- Second criterion
""",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = extract_acceptance_criteria(context)
        assert len(result) == 2

    def test_extract_case_insensitive_header_detection(self):
        """Test that header detection is case-insensitive."""
        context = PlannerContext(
            spec_content="""# Feature

## SUCCESS CRITERIA
- First criterion

## success criteria
- Second criterion
""",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = extract_acceptance_criteria(context)
        assert len(result) >= 1

    def test_extract_strips_checkbox_markers(self):
        """Test that checkbox markers are stripped from criteria."""
        context = PlannerContext(
            spec_content="""# Feature

## Success Criteria
- [ ] Checkbox item
""",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = extract_acceptance_criteria(context)
        assert result[0] == "Checkbox item"

    def test_extract_from_complete_when_section(self):
        """Test extracting from 'Complete When' section."""
        context = PlannerContext(
            spec_content="""# Feature

## Complete When
- All tests pass
- Documentation is complete
""",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = extract_acceptance_criteria(context)
        assert "All tests pass" in result
        assert "Documentation is complete" in result


class TestDetermineServiceOrder:
    """Tests for determine_service_order function."""

    def test_backend_services_first(self):
        """Test that backend services come first."""
        files_by_service = {
            "frontend": [{"path": "App.tsx"}],
            "backend": [{"path": "main.py"}],
            "worker": [{"path": "job.py"}],
        }
        result = determine_service_order(files_by_service)
        assert result[0] in ["backend", "api", "server"]
        assert "backend" in result[:3]

    def test_worker_services_second(self):
        """Test that worker services come after backend."""
        files_by_service = {
            "worker": [{"path": "job.py"}],
            "backend": [{"path": "main.py"}],
            "frontend": [{"path": "App.tsx"}],
        }
        result = determine_service_order(files_by_service)
        # Worker should come before frontend
        worker_idx = result.index("worker")
        frontend_idx = result.index("frontend")
        assert worker_idx < frontend_idx

    def test_frontend_services_third(self):
        """Test that frontend services come after workers."""
        files_by_service = {
            "frontend": [{"path": "App.tsx"}],
            "backend": [{"path": "main.py"}],
        }
        result = determine_service_order(files_by_service)
        assert result[-1] in ["frontend", "web", "client", "ui"]

    def test_unknown_services_at_end(self):
        """Test that unknown services come at the end."""
        files_by_service = {
            "backend": [{"path": "main.py"}],
            "random_service": [{"path": "random.py"}],
            "frontend": [{"path": "App.tsx"}],
        }
        result = determine_service_order(files_by_service)
        # Random service should be at the end
        assert result[-1] == "random_service"

    def test_all_backend_variations(self):
        """Test all backend service name variations."""
        files_by_service = {
            "api": [{"path": "api.py"}],
            "server": [{"path": "server.py"}],
            "backend": [{"path": "backend.py"}],
        }
        result = determine_service_order(files_by_service)
        # All should be in the result
        assert "api" in result
        assert "server" in result
        assert "backend" in result

    def test_all_worker_variations(self):
        """Test all worker service name variations."""
        files_by_service = {
            "worker": [{"path": "worker.py"}],
            "celery": [{"path": "celery.py"}],
            "jobs": [{"path": "jobs.py"}],
            "tasks": [{"path": "tasks.py"}],
        }
        result = determine_service_order(files_by_service)
        assert "worker" in result
        assert "celery" in result
        assert "jobs" in result
        assert "tasks" in result

    def test_all_frontend_variations(self):
        """Test all frontend service name variations."""
        files_by_service = {
            "frontend": [{"path": "frontend.py"}],
            "web": [{"path": "web.py"}],
            "client": [{"path": "client.py"}],
            "ui": [{"path": "ui.py"}],
        }
        result = determine_service_order(files_by_service)
        assert "frontend" in result
        assert "web" in result
        assert "client" in result
        assert "ui" in result

    def test_empty_dict(self):
        """Test with empty service dict."""
        result = determine_service_order({})
        assert result == []

    def test_single_service(self):
        """Test with single service."""
        files_by_service = {"backend": [{"path": "main.py"}]}
        result = determine_service_order(files_by_service)
        assert result == ["backend"]

    def test_mixed_services_preserves_order_within_category(self):
        """Test that order within category is preserved."""
        files_by_service = {
            "api": [{"path": "api.py"}],
            "backend": [{"path": "backend.py"}],
            "worker": [{"path": "worker.py"}],
            "tasks": [{"path": "tasks.py"}],
            "frontend": [{"path": "frontend.py"}],
            "web": [{"path": "web.py"}],
        }
        result = determine_service_order(files_by_service)
        # Verify categories are grouped
        api_idx = result.index("api")
        backend_idx = result.index("backend")
        worker_idx = result.index("worker")
        frontend_idx = result.index("frontend")

        assert api_idx < worker_idx
        assert backend_idx < worker_idx
        assert worker_idx < frontend_idx


class TestInferSubtaskType:
    """Tests for infer_subtask_type function."""

    @pytest.mark.parametrize(
        "path, expected_type",
        [
            ("models/user.py", "model"),
            ("schema/user.py", "model"),
            ("routes/api.py", "endpoint"),
            ("endpoints/users.py", "endpoint"),
            ("api/main.py", "endpoint"),
            ("components/Button.tsx", "component"),
            ("component/Header.tsx", "component"),
            ("App.tsx", "component"),
            ("View.jsx", "component"),
            ("tasks/process.py", "task"),
            ("worker/job.py", "task"),
            ("celery/task.py", "task"),
        ],
    )
    def test_infer_subtask_type_various_paths(self, path, expected_type):
        """Test subtask type inference from various file paths."""
        result = infer_subtask_type(path)
        assert result == expected_type

    def test_infer_subtask_type_case_insensitive(self):
        """Test that inference is case-insensitive."""
        assert infer_subtask_type("Model.py") == "model"
        assert infer_subtask_type("ROUTE.py") == "endpoint"

    def test_infer_subtask_type_default_code(self):
        """Test default 'code' type for unrecognized paths."""
        result = infer_subtask_type("utils/helper.py")
        assert result == "code"

    def test_infer_subtask_type_react_components(self):
        """Test React component detection."""
        assert infer_subtask_type("Button.tsx") == "component"
        assert infer_subtask_type("Header.jsx") == "component"

    def test_infer_subtask_type_with_directory(self):
        """Test inference with directory paths."""
        assert infer_subtask_type("src/models/User.py") == "model"
        assert infer_subtask_type("src/components/Button.tsx") == "component"

    def test_infer_subtask_type_multiple_keywords(self):
        """Test handling of multiple keywords in path."""
        # Should match first found keyword
        result = infer_subtask_type("models/component.py")
        assert result in ["model", "component"]

    def test_infer_subtask_type_empty_path(self):
        """Test with empty path."""
        result = infer_subtask_type("")
        assert result == "code"

    def test_infer_subtask_type_with_extension_variations(self):
        """Test inference with different file extensions."""
        assert infer_subtask_type("model.py") == "model"
        assert infer_subtask_type("route.py") == "endpoint"
        assert infer_subtask_type("Component.tsx") == "component"
        assert infer_subtask_type("component.jsx") == "component"
        assert infer_subtask_type("task.py") == "task"

    def test_infer_subtask_type_schema_detection(self):
        """Test schema keyword detection."""
        assert infer_subtask_type("schemas/user.py") == "model"
        assert infer_subtask_type("schema/UserSchema.py") == "model"

    def test_infer_subtask_type_api_detection(self):
        """Test API keyword detection."""
        assert infer_subtask_type("api.py") == "endpoint"
        assert infer_subtask_type("my_api.py") == "endpoint"


class TestUtilsEdgeCases:
    """Edge case tests for planner_lib.utils module."""

    def test_extract_feature_name_with_only_whitespace(self):
        """Test feature name extraction with whitespace only."""
        context = PlannerContext(
            spec_content="   \n\n   ",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = extract_feature_name(context)
        assert result == "Unnamed Feature"

    def test_group_files_with_none_service(self):
        """Test grouping files with None service."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[{"path": "file.py", "service": None}],
            files_to_reference=[],
        )
        result = group_files_by_service(context)
        # Should handle None gracefully
        assert len(result) >= 0

    def test_create_verification_with_missing_service_info(self):
        """Test verification creation when service info is missing."""
        context = PlannerContext(
            spec_content="# Test",
            project_index={"services": {}},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = create_verification(context, "nonexistent", "endpoint")
        assert result.type == VerificationType.API
        assert result.url == "/health"

    def test_extract_acceptance_criteria_with_empty_lines(self):
        """Test criteria extraction with only empty lines."""
        context = PlannerContext(
            spec_content="# Feature\n\n## Success Criteria\n\n\n",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        result = extract_acceptance_criteria(context)
        # Should return generic criteria
        assert len(result) > 0

    def test_determine_service_order_with_duplicate_names(self):
        """Test service ordering with potential name conflicts."""
        files_by_service = {
            "backend": [{"path": "backend.py"}],
            "backend_api": [{"path": "api.py"}],
        }
        result = determine_service_order(files_by_service)
        assert len(result) == 2
        assert "backend" in result
        assert "backend_api" in result

    def test_infer_subtask_type_with_special_characters(self):
        """Test subtask type inference with special characters in path."""
        result = infer_subtask_type("my-component/file.py")
        # my-component has "component" in it, so it might be detected as component
        assert result in ["code", "component"]

    def test_all_utils_with_unicode_content(self):
        """Test all utils functions with unicode content."""
        context = PlannerContext(
            spec_content="# Fëaturë with spëcial chars\n\n## Succëss Critëria\n- Tëst critërion",
            project_index={"services": {"backend": {"port": 8000}}},
            task_context={},
            services_involved=["backend"],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )
        # Should handle unicode without errors
        feature_name = extract_feature_name(context)
        criteria = extract_acceptance_criteria(context)
        verification = create_verification(context, "backend", "endpoint")

        assert "spëcial" in feature_name
        assert len(criteria) > 0
        assert verification.type == VerificationType.API
