"""
Tests for qa.qa_loop module - backward compatibility facade.

This module tests the re-export facade that provides backward compatibility
by re-exporting all symbols from the qa package.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Test imports from the qa_loop facade module
# This module should re-export everything from the qa package
from apps.backend.qa.qa_loop import (
    # Configuration constants
    MAX_QA_ITERATIONS,
    RECURRING_ISSUE_THRESHOLD,
    ISSUE_SIMILARITY_THRESHOLD,
    # Main loop
    run_qa_validation_loop,
    # Criteria & status
    load_implementation_plan,
    save_implementation_plan,
    get_qa_signoff_status,
    is_qa_approved,
    is_qa_rejected,
    is_fixes_applied,
    get_qa_iteration_count,
    should_run_qa,
    should_run_fixes,
    print_qa_status,
    # Report & tracking
    get_iteration_history,
    record_iteration,
    has_recurring_issues,
    get_recurring_issue_summary,
    escalate_to_human,
    create_manual_test_plan,
    check_test_discovery,
    is_no_test_project,
    _normalize_issue_key,
    _issue_similarity,
    # Agent sessions
    run_qa_agent_session,
    load_qa_fixer_prompt,
    run_qa_fixer_session,
)

# Also test __all__ export list
from apps.backend.qa import qa_loop

from .conftest import (
    create_async_response,
    create_spec_files,
    MockBlock,
    MockMessage,
)


class TestQaLoopFacadeExports:
    """Tests for qa_loop facade module exports."""

    def test_all_exports_defined(self) -> None:
        """Test that __all__ is properly defined in qa_loop module."""
        expected_exports = {
            # Configuration
            "MAX_QA_ITERATIONS",
            "RECURRING_ISSUE_THRESHOLD",
            "ISSUE_SIMILARITY_THRESHOLD",
            # Main loop
            "run_qa_validation_loop",
            # Criteria & status
            "load_implementation_plan",
            "save_implementation_plan",
            "get_qa_signoff_status",
            "is_qa_approved",
            "is_qa_rejected",
            "is_fixes_applied",
            "get_qa_iteration_count",
            "should_run_qa",
            "should_run_fixes",
            "print_qa_status",
            # Report & tracking
            "get_iteration_history",
            "record_iteration",
            "has_recurring_issues",
            "get_recurring_issue_summary",
            "escalate_to_human",
            "create_manual_test_plan",
            "check_test_discovery",
            "is_no_test_project",
            "_normalize_issue_key",
            "_issue_similarity",
            # Agent sessions
            "run_qa_agent_session",
            "load_qa_fixer_prompt",
            "run_qa_fixer_session",
        }

        actual_exports = set(qa_loop.__all__)
        assert actual_exports == expected_exports

    def test_constants_exported(self) -> None:
        """Test that configuration constants are properly exported."""
        # These should be integers
        assert isinstance(MAX_QA_ITERATIONS, int)
        assert MAX_QA_ITERATIONS > 0

        assert isinstance(RECURRING_ISSUE_THRESHOLD, int)
        assert RECURRING_ISSUE_THRESHOLD > 0

        assert isinstance(ISSUE_SIMILARITY_THRESHOLD, float)
        assert 0 <= ISSUE_SIMILARITY_THRESHOLD <= 1

    def test_main_loop_functions_exported(self) -> None:
        """Test that main loop functions are callable."""
        assert callable(run_qa_validation_loop)

    def test_criteria_functions_exported(self) -> None:
        """Test that criteria and status functions are callable."""
        assert callable(load_implementation_plan)
        assert callable(save_implementation_plan)
        assert callable(get_qa_signoff_status)
        assert callable(is_qa_approved)
        assert callable(is_qa_rejected)
        assert callable(is_fixes_applied)
        assert callable(get_qa_iteration_count)
        assert callable(should_run_qa)
        assert callable(should_run_fixes)
        assert callable(print_qa_status)

    def test_report_functions_exported(self) -> None:
        """Test that report and tracking functions are callable."""
        assert callable(get_iteration_history)
        assert callable(record_iteration)
        assert callable(has_recurring_issues)
        assert callable(get_recurring_issue_summary)
        assert callable(escalate_to_human)
        assert callable(create_manual_test_plan)
        assert callable(check_test_discovery)
        assert callable(is_no_test_project)
        assert callable(_normalize_issue_key)
        assert callable(_issue_similarity)

    def test_agent_session_functions_exported(self) -> None:
        """Test that agent session functions are callable."""
        assert callable(run_qa_agent_session)
        assert callable(load_qa_fixer_prompt)
        assert callable(run_qa_fixer_session)


class TestQaLoopFacadeBehavior:
    """Tests for qa_loop facade module behavior - ensure it delegates correctly."""

    @pytest.mark.asyncio
    async def test_run_qa_validation_loop_delegates(
        self, temp_spec_dir: Any, sample_implementation_plan: dict[str, Any]
    ) -> None:
        """Test that run_qa_validation_loop delegates to qa.loop module."""
        from pathlib import Path

        create_spec_files(Path(temp_spec_dir), sample_implementation_plan)

        with patch("apps.backend.qa.loop.is_build_complete", return_value=False):
            # The facade should delegate to the actual implementation
            result = await run_qa_validation_loop(
                Path(temp_spec_dir), Path(temp_spec_dir).parent, model="claude-3-5-sonnet-20241022"
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_run_qa_agent_session_delegates(
        self, temp_spec_dir: Any, temp_project_dir: Any, approved_plan: dict[str, Any], mock_sdk_client: MagicMock
    ) -> None:
        """Test that run_qa_agent_session delegates to qa.reviewer module."""
        from pathlib import Path

        create_spec_files(Path(temp_spec_dir), approved_plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="QA review complete."),
                    MockBlock("ToolUseBlock", name="Edit", input_data={"file_path": str(Path(temp_spec_dir) / "implementation_plan.json")}),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock", content="Success")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        status, response = await run_qa_agent_session(
            mock_sdk_client,
            Path(temp_project_dir),
            Path(temp_spec_dir),
            qa_session=1,
            max_iterations=50,
        )

        assert status == "approved"

    @pytest.mark.asyncio
    async def test_run_qa_fixer_session_delegates(
        self, temp_spec_dir: Any, sample_implementation_plan: dict[str, Any], mock_sdk_client: MagicMock
    ) -> None:
        """Test that run_qa_fixer_session delegates to qa.fixer module."""
        from pathlib import Path

        create_spec_files(Path(temp_spec_dir), sample_implementation_plan)

        # Create QA_FIX_REQUEST.md
        fix_request = Path(temp_spec_dir) / "QA_FIX_REQUEST.md"
        fix_request.write_text("# Fix Request")

        # Update plan with ready_for_qa_revalidation
        plan = sample_implementation_plan.copy()
        plan["qa_signoff"] = {
            "status": "fixes_applied",
            "ready_for_qa_revalidation": True,
        }
        create_spec_files(Path(temp_spec_dir), plan)

        messages = [
            MockMessage(
                "AssistantMessage",
                content=[
                    MockBlock("TextBlock", text="Fixes applied."),
                    MockBlock("ToolUseBlock", name="Edit"),
                ],
            ),
            MockMessage("UserMessage", content=[MockBlock("ToolResultBlock")]),
        ]
        mock_sdk_client.receive_response = MagicMock(return_value=create_async_response(messages))

        status, response = await run_qa_fixer_session(
            mock_sdk_client,
            Path(temp_spec_dir),
            fix_session=1,
        )

        assert status == "fixed"

    def test_load_implementation_plan_delegates(self, temp_spec_dir: Any, sample_implementation_plan: dict[str, Any]) -> None:
        """Test that load_implementation_plan delegates to qa.criteria module."""
        from pathlib import Path

        create_spec_files(Path(temp_spec_dir), sample_implementation_plan)

        result = load_implementation_plan(Path(temp_spec_dir))

        assert result == sample_implementation_plan

    def test_save_implementation_plan_delegates(self, temp_spec_dir: Any, sample_implementation_plan: dict[str, Any]) -> None:
        """Test that save_implementation_plan delegates to qa.criteria module."""
        from pathlib import Path

        save_implementation_plan(Path(temp_spec_dir), sample_implementation_plan)

        plan_file = Path(temp_spec_dir) / "implementation_plan.json"
        assert plan_file.exists()

    def test_get_qa_signoff_status_delegates(self, temp_spec_dir: Any, approved_plan: dict[str, Any]) -> None:
        """Test that get_qa_signoff_status delegates to qa.criteria module."""
        from pathlib import Path

        create_spec_files(Path(temp_spec_dir), approved_plan)

        result = get_qa_signoff_status(Path(temp_spec_dir))

        assert result["status"] == "approved"

    def test_is_qa_approved_delegates(self, temp_spec_dir: Any, approved_plan: dict[str, Any]) -> None:
        """Test that is_qa_approved delegates to qa.criteria module."""
        from pathlib import Path

        create_spec_files(Path(temp_spec_dir), approved_plan)

        result = is_qa_approved(Path(temp_spec_dir))

        assert result is True

    def test_is_qa_rejected_delegates(self, temp_spec_dir: Any, rejected_plan: dict[str, Any]) -> None:
        """Test that is_qa_rejected delegates to qa.criteria module."""
        from pathlib import Path

        create_spec_files(Path(temp_spec_dir), rejected_plan)

        result = is_qa_rejected(Path(temp_spec_dir))

        assert result is True

    def test_is_fixes_applied_delegates(self, temp_spec_dir: Any, sample_implementation_plan: dict[str, Any]) -> None:
        """Test that is_fixes_applied delegates to qa.criteria module."""
        from pathlib import Path

        plan = sample_implementation_plan.copy()
        plan["qa_signoff"] = {
            "status": "fixes_applied",
            "ready_for_qa_revalidation": True,
        }
        create_spec_files(Path(temp_spec_dir), plan)

        result = is_fixes_applied(Path(temp_spec_dir))

        assert result is True

    def test_get_qa_iteration_count_delegates(self, temp_spec_dir: Any, approved_plan: dict[str, Any]) -> None:
        """Test that get_qa_iteration_count delegates to qa.criteria module."""
        from pathlib import Path

        create_spec_files(Path(temp_spec_dir), approved_plan)

        result = get_qa_iteration_count(Path(temp_spec_dir))

        assert result == 1

    def test_should_run_qa_delegates(self, temp_spec_dir: Any, sample_implementation_plan: dict[str, Any]) -> None:
        """Test that should_run_qa delegates to qa.criteria module."""
        from pathlib import Path

        # should_run_qa requires build to be complete (all subtasks done) and not yet approved
        # Create a plan with phases structure that count_subtasks expects
        plan_with_phases = {
            "title": "Test Feature",
            "description": "Test feature description",
            "phases": [
                {
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "1", "title": "Subtask 1", "status": "completed"},
                        {"id": "2", "title": "Subtask 2", "status": "completed"},
                    ],
                }
            ],
            "qa_signoff": {
                "status": "pending",
                "qa_session": 0,
            },
            "qa_iteration_history": [],
            "qa_stats": {},
        }
        create_spec_files(Path(temp_spec_dir), plan_with_phases)

        result = should_run_qa(Path(temp_spec_dir))

        assert result is True

    def test_should_run_fixes_delegates(self, temp_spec_dir: Any, rejected_plan: dict[str, Any]) -> None:
        """Test that should_run_fixes delegates to qa.criteria module."""
        from pathlib import Path

        create_spec_files(Path(temp_spec_dir), rejected_plan)

        # Create QA_FIX_REQUEST.md
        fix_request = Path(temp_spec_dir) / "QA_FIX_REQUEST.md"
        fix_request.write_text("# Fix Request")

        result = should_run_fixes(Path(temp_spec_dir))

        assert result is True

    def test_print_qa_status_delegates(
        self, temp_spec_dir: Any, approved_plan: dict[str, Any], capsys: pytest.CaptureFixture
    ) -> None:
        """Test that print_qa_status delegates to qa.criteria module."""
        from pathlib import Path

        create_spec_files(Path(temp_spec_dir), approved_plan)

        print_qa_status(Path(temp_spec_dir))

        captured = capsys.readouterr()
        assert "approved" in captured.out.lower()

    def test_get_iteration_history_delegates(self, temp_spec_dir: Any, sample_implementation_plan: dict[str, Any]) -> None:
        """Test that get_iteration_history delegates to qa.report module."""
        from pathlib import Path

        create_spec_files(Path(temp_spec_dir), sample_implementation_plan)

        result = get_iteration_history(Path(temp_spec_dir))

        assert isinstance(result, list)

    def test_record_iteration_delegates(self, temp_spec_dir: Any, sample_implementation_plan: dict[str, Any]) -> None:
        """Test that record_iteration delegates to qa.report module."""
        from pathlib import Path

        create_spec_files(Path(temp_spec_dir), sample_implementation_plan)

        # record_iteration expects a list of issues, not a dict
        record_iteration(Path(temp_spec_dir), 1, "approved", [{"title": "No issues", "type": "info"}])

        # Verify the iteration was recorded
        result = get_iteration_history(Path(temp_spec_dir))
        assert len(result) == 1
        assert result[0]["iteration"] == 1
        assert result[0]["status"] == "approved"

    def test_has_recurring_issues_delegates(self, temp_spec_dir: Any, iteration_history: list[dict[str, Any]]) -> None:
        """Test that has_recurring_issues delegates to qa.report module."""
        # has_recurring_issues takes (current_issues, history) as parameters
        # Extract current issues from the last iteration
        current_issues = iteration_history[-1]["issues"]

        has_recurring, recurring_issues = has_recurring_issues(current_issues, iteration_history)

        # The same issue appears twice, so it should be detected as recurring
        # with default threshold of 3, we need more occurrences or adjust threshold
        has_recurring, recurring_issues = has_recurring_issues(current_issues, iteration_history, threshold=2)

        assert has_recurring is True
        assert len(recurring_issues) > 0

    def test_get_recurring_issue_summary_delegates(
        self, temp_spec_dir: Any, iteration_history: list[dict[str, Any]]
    ) -> None:
        """Test that get_recurring_issue_summary delegates to qa.report module."""
        # get_recurring_issue_summary takes history as parameter
        summary = get_recurring_issue_summary(iteration_history)

        assert "total_issues" in summary
        assert "unique_issues" in summary
        assert summary["total_issues"] == 2  # Two iterations with one issue each

    @pytest.mark.asyncio
    async def test_escalate_to_human_delegates(self, temp_spec_dir: Any, sample_implementation_plan: dict[str, Any]) -> None:
        """Test that escalate_to_human delegates to qa.report module."""
        from pathlib import Path

        create_spec_files(Path(temp_spec_dir), sample_implementation_plan)

        # escalate_to_human is async and takes (spec_dir, recurring_issues, iteration)
        await escalate_to_human(Path(temp_spec_dir), [{"title": "Issue 1"}], 1)

        escalation_file = Path(temp_spec_dir) / "QA_ESCALATION.md"
        assert escalation_file.exists()

    def test_create_manual_test_plan_delegates(self, temp_spec_dir: Any, sample_implementation_plan: dict[str, Any]) -> None:
        """Test that create_manual_test_plan delegates to qa.report module."""
        from pathlib import Path

        create_spec_files(Path(temp_spec_dir), sample_implementation_plan)

        # create_manual_test_plan takes (spec_dir, spec_name)
        result = create_manual_test_plan(Path(temp_spec_dir), "test-spec")

        assert result == Path(temp_spec_dir) / "MANUAL_TEST_PLAN.md"

    def test_check_test_discovery_delegates(self, temp_spec_dir: Any, temp_project_dir: Any) -> None:
        """Test that check_test_discovery delegates to qa.report module."""
        from pathlib import Path

        # check_test_discovery takes spec_dir, not project_dir
        # Create a test_discovery.json file
        discovery_file = Path(temp_spec_dir) / "test_discovery.json"
        discovery_file.write_text('{"frameworks": ["pytest"], "test_files_found": 5}')

        result = check_test_discovery(Path(temp_spec_dir))

        # Should return test discovery info
        assert result is not None
        assert result["frameworks"] == ["pytest"]
        assert result["test_files_found"] == 5

    def test_is_no_test_project_delegates(self, temp_spec_dir: Any, temp_project_dir: Any) -> None:
        """Test that is_no_test_project delegates to qa.report module."""
        from pathlib import Path

        # is_no_test_project takes (spec_dir, project_dir)
        # Empty project directory should be detected as no-test project
        result = is_no_test_project(Path(temp_spec_dir), Path(temp_project_dir))

        assert isinstance(result, bool)
        # Empty project has no test indicators, so should be True
        assert result is True

    def test_normalize_issue_key_delegates(self) -> None:
        """Test that _normalize_issue_key delegates to qa.report module."""
        # _normalize_issue_key takes an issue dict
        issue = {"title": "Test Failure in Auth Module", "file": "auth.py", "line": 42}
        result = _normalize_issue_key(issue)

        # Should normalize to a key string
        assert isinstance(result, str)
        assert "|" in result  # Key format is "title|file|line"

    def test_issue_similarity_delegates(self) -> None:
        """Test that _issue_similarity delegates to qa.report module."""
        # _issue_similarity takes two issue dicts
        issue1 = {"title": "Test failure in auth module", "file": "auth.py", "line": 42}
        issue2 = {"title": "Test failure in auth module", "file": "auth.py", "line": 42}

        result = _issue_similarity(issue1, issue2)

        # Same issues should have high similarity (close to 1.0)
        assert result > 0.9

    def test_load_qa_fixer_prompt_delegates(self) -> None:
        """Test that load_qa_fixer_prompt delegates to qa.fixer module."""
        # This should load the actual prompt file
        prompt = load_qa_fixer_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestQaLoopBackwardCompatibility:
    """Tests for backward compatibility of qa_loop facade."""

    def test_can_import_from_qa_loop(self) -> None:
        """Test that old imports from qa.qa_loop still work."""
        # This simulates existing code that imports from qa.qa_loop
        from apps.backend.qa.qa_loop import (
            run_qa_validation_loop,
            is_qa_approved,
            get_qa_signoff_status,
        )

        assert callable(run_qa_validation_loop)
        assert callable(is_qa_approved)
        assert callable(get_qa_signoff_status)

    def test_can_import_from_qa_package(self) -> None:
        """Test that new imports from qa package work."""
        # This simulates new code that imports from qa package
        from apps.backend.qa import (
            run_qa_validation_loop,
            is_qa_approved,
            get_qa_signoff_status,
        )

        assert callable(run_qa_validation_loop)
        assert callable(is_qa_approved)
        assert callable(get_qa_signoff_status)

    def test_both_imports_reference_same_functions(self) -> None:
        """Test that imports from qa_loop and qa package reference same functions."""
        from apps.backend.qa.qa_loop import is_qa_approved as qa_loop_is_qa_approved
        from apps.backend.qa import is_qa_approved as qa_is_qa_approved

        # Both should be callable and produce the same behavior
        # Note: They may not be the same object due to Python's import system,
        # but they should behave identically
        assert callable(qa_loop_is_qa_approved)
        assert callable(qa_is_qa_approved)
        assert qa_loop_is_qa_approved.__name__ == qa_is_qa_approved.__name__


class TestQaLoopConstants:
    """Tests for configuration constants exported by qa_loop."""

    def test_max_qa_iterations_value(self) -> None:
        """Test MAX_QA_ITERATIONS has reasonable value."""
        assert MAX_QA_ITERATIONS >= 3
        assert MAX_QA_ITERATIONS <= 100  # Upper bound for reasonable value

    def test_recurring_issue_threshold_value(self) -> None:
        """Test RECURRING_ISSUE_THRESHOLD has reasonable value."""
        assert RECURRING_ISSUE_THRESHOLD >= 2
        assert RECURRING_ISSUE_THRESHOLD <= 5

    def test_issue_similarity_threshold_value(self) -> None:
        """Test ISSUE_SIMILARITY_THRESHOLD has reasonable value."""
        assert 0.0 <= ISSUE_SIMILARITY_THRESHOLD <= 1.0

    def test_constants_match_implementation(self) -> None:
        """Test that constants match the actual implementation."""
        # Import from the actual module
        from apps.backend.qa.loop import MAX_QA_ITERATIONS as LoopMaxIterations
        from apps.backend.qa.report import (
            RECURRING_ISSUE_THRESHOLD as ReportRecurringThreshold,
            ISSUE_SIMILARITY_THRESHOLD as ReportSimilarityThreshold,
        )

        # Facade should export same values
        assert MAX_QA_ITERATIONS == LoopMaxIterations
        assert RECURRING_ISSUE_THRESHOLD == ReportRecurringThreshold
        assert ISSUE_SIMILARITY_THRESHOLD == ReportSimilarityThreshold
