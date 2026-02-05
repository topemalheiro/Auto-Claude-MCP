"""
Tests for qa.loop module - main QA validation loop orchestration.
"""

from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from apps.backend.qa.loop import MAX_QA_ITERATIONS, MAX_CONSECUTIVE_ERRORS, run_qa_validation_loop

from .conftest import create_spec_files


class TestRunQaValidationLoop:
    """Tests for run_qa_validation_loop - the main QA orchestration loop."""

    @pytest.mark.asyncio
    async def test_build_not_complete_returns_false(
        self, temp_spec_dir: Path, temp_project_dir: Path, sample_implementation_plan: dict
    ) -> None:
        """Test early return when build is not complete."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        with patch("apps.backend.qa.loop.is_build_complete", return_value=False):
            result = await run_qa_validation_loop(
                temp_project_dir, temp_spec_dir, model="claude-3-5-sonnet-20241022"
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_already_approved_returns_true(
        self, temp_spec_dir: Path, temp_project_dir: Path, approved_plan: dict
    ) -> None:
        """Test early return when already approved."""
        create_spec_files(temp_spec_dir, approved_plan)

        with patch("apps.backend.qa.loop.is_build_complete", return_value=True):
            result = await run_qa_validation_loop(
                temp_project_dir, temp_spec_dir, model="claude-3-5-sonnet-20241022"
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_processes_human_feedback_first(
        self, temp_spec_dir: Path, temp_project_dir: Path, sample_implementation_plan: dict
    ) -> None:
        """Test that human feedback is processed before QA validation."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        # Create QA_FIX_REQUEST.md
        fix_request = temp_spec_dir / "QA_FIX_REQUEST.md"
        fix_request.write_text("# Human feedback\n\nFix this issue.")

        with patch("apps.backend.qa.loop.is_build_complete", return_value=True), patch(
            "apps.backend.qa.loop.is_qa_approved", return_value=False
        ), patch("apps.backend.qa.loop.create_client") as mock_create_client:
            # Mock fixer client to return success
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_create_client.return_value = mock_client

            with patch(
                "apps.backend.qa.loop.run_qa_fixer_session", new_callable=AsyncMock
            ) as mock_fixer:
                mock_fixer.return_value = ("fixed", "Fixes applied")

                with patch(
                    "apps.backend.qa.loop.run_qa_agent_session", new_callable=AsyncMock
                ) as mock_reviewer:
                    # After fixer, QA approves
                    mock_reviewer.return_value = ("approved", "All good")

                    result = await run_qa_validation_loop(
                        temp_project_dir, temp_spec_dir, model="claude-3-5-sonnet-20241022"
                    )

        # Fixer should have been called
        mock_fixer.assert_called_once()
        # Fix request file should be removed
        assert not fix_request.exists()
        assert result is True

    @pytest.mark.asyncio
    async def test_human_feedback_fixer_error_returns_false(
        self, temp_spec_dir: Path, temp_project_dir: Path, sample_implementation_plan: dict
    ) -> None:
        """Test that fixer error during human feedback processing returns False."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        fix_request = temp_spec_dir / "QA_FIX_REQUEST.md"
        fix_request.write_text("# Human feedback")

        with patch("apps.backend.qa.loop.is_build_complete", return_value=True), patch(
            "apps.backend.qa.loop.is_qa_approved", return_value=False
        ), patch("apps.backend.qa.loop.create_client") as mock_create_client:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_create_client.return_value = mock_client

            with patch(
                "apps.backend.qa.loop.run_qa_fixer_session", new_callable=AsyncMock
            ) as mock_fixer:
                mock_fixer.return_value = ("error", "Fixer failed")

                result = await run_qa_validation_loop(
                    temp_project_dir, temp_spec_dir, model="claude-3-5-sonnet-20241022"
                )

        assert result is False

    @pytest.mark.asyncio
    async def test_no_test_project_handling(
        self, temp_spec_dir: Path, temp_project_dir: Path, sample_implementation_plan: dict, capsys: pytest.CaptureFixture
    ) -> None:
        """Test handling of no-test projects."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        with patch("apps.backend.qa.loop.is_build_complete", return_value=True), patch(
            "apps.backend.qa.loop.is_qa_approved", return_value=False
        ), patch("apps.backend.qa.loop.is_no_test_project", return_value=True), patch(
            "apps.backend.qa.loop.create_manual_test_plan", return_value=temp_spec_dir / "MANUAL_TEST_PLAN.md"
        ), patch(
            "apps.backend.qa.loop.create_client"
        ) as mock_create_client, patch(
            "apps.backend.qa.loop.run_qa_agent_session", new_callable=AsyncMock
        ) as mock_reviewer:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_create_client.return_value = mock_client
            mock_reviewer.return_value = ("approved", "Approved")

            await run_qa_validation_loop(
                temp_project_dir, temp_spec_dir, model="claude-3-5-sonnet-20241022"
            )

        captured = capsys.readouterr()
        assert "No test framework detected" in captured.out
        assert "Manual test plan created" in captured.out

    @pytest.mark.asyncio
    async def test_qa_approved_exits_loop(
        self, temp_spec_dir: Path, temp_project_dir: Path, sample_implementation_plan: dict
    ) -> None:
        """Test that loop exits when QA approves."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        with patch("apps.backend.qa.loop.is_build_complete", return_value=True), patch(
            "apps.backend.qa.loop.is_qa_approved", return_value=False
        ), patch("apps.backend.qa.loop.is_no_test_project", return_value=False), patch(
            "apps.backend.qa.loop.create_client"
        ) as mock_create_client, patch(
            "apps.backend.qa.loop.run_qa_agent_session", new_callable=AsyncMock
        ) as mock_reviewer:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_create_client.return_value = mock_client
            mock_reviewer.return_value = ("approved", "QA passed")

            result = await run_qa_validation_loop(
                temp_project_dir, temp_spec_dir, model="claude-3-5-sonnet-20241022"
            )

        assert result is True
        mock_reviewer.assert_called_once()

    @pytest.mark.asyncio
    async def test_qa_rejected_runs_fixer(
        self, temp_spec_dir: Path, temp_project_dir: Path, rejected_plan: dict
    ) -> None:
        """Test that rejection triggers fixer and re-validation."""
        create_spec_files(temp_spec_dir, rejected_plan)

        call_count = {"reviewer": 0, "fixer": 0}

        async def mock_reviewer(*args, **kwargs):
            call_count["reviewer"] += 1
            if call_count["reviewer"] == 1:
                return ("rejected", "Issues found")
            return ("approved", "Fixed")

        async def mock_fixer(*args, **kwargs):
            call_count["fixer"] += 1
            return ("fixed", "Fixes applied")

        with patch("apps.backend.qa.loop.is_build_complete", return_value=True), patch(
            "apps.backend.qa.loop.is_qa_approved", return_value=False
        ), patch("apps.backend.qa.loop.is_no_test_project", return_value=False), patch(
            "apps.backend.qa.loop.create_client"
        ) as mock_create_client, patch(
            "apps.backend.qa.loop.run_qa_agent_session", new=mock_reviewer
        ), patch(
            "apps.backend.qa.loop.run_qa_fixer_session", new=mock_fixer
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_create_client.return_value = mock_client

            result = await run_qa_validation_loop(
                temp_project_dir, temp_spec_dir, model="claude-3-5-sonnet-20241022"
            )

        assert result is True
        assert call_count["reviewer"] == 2
        assert call_count["fixer"] == 1

    @pytest.mark.asyncio
    async def test_fixer_error_breaks_loop(
        self, temp_spec_dir: Path, temp_project_dir: Path, rejected_plan: dict
    ) -> None:
        """Test that fixer error breaks the loop."""
        create_spec_files(temp_spec_dir, rejected_plan)

        with patch("apps.backend.qa.loop.is_build_complete", return_value=True), patch(
            "apps.backend.qa.loop.is_qa_approved", return_value=False
        ), patch("apps.backend.qa.loop.is_no_test_project", return_value=False), patch(
            "apps.backend.qa.loop.create_client"
        ) as mock_create_client, patch(
            "apps.backend.qa.loop.run_qa_agent_session", new_callable=AsyncMock
        ) as mock_reviewer, patch(
            "apps.backend.qa.loop.run_qa_fixer_session", new_callable=AsyncMock
        ) as mock_fixer:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_create_client.return_value = mock_client
            mock_reviewer.return_value = ("rejected", "Issues")
            mock_fixer.return_value = ("error", "Fixer error")

            result = await run_qa_validation_loop(
                temp_project_dir, temp_spec_dir, model="claude-3-5-sonnet-20241022"
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_recurring_issues_escalates(
        self, temp_spec_dir: Path, temp_project_dir: Path, sample_implementation_plan: dict, sample_issues: list
    ) -> None:
        """Test that recurring issues trigger escalation."""
        plan = sample_implementation_plan.copy()
        # Setup history with recurring issues
        plan["qa_iteration_history"] = [
            {"iteration": i, "status": "rejected", "issues": [sample_issues[0]], "timestamp": "2024-01-01T00:00:00Z"}
            for i in range(1, 3)
        ]
        create_spec_files(temp_spec_dir, plan)

        with patch("apps.backend.qa.loop.is_build_complete", return_value=True), patch(
            "apps.backend.qa.loop.is_qa_approved", return_value=False
        ), patch("apps.backend.qa.loop.is_no_test_project", return_value=False), patch(
            "apps.backend.qa.loop.create_client"
        ) as mock_create_client, patch(
            "apps.backend.qa.loop.run_qa_agent_session", new_callable=AsyncMock
        ) as mock_reviewer, patch(
            "apps.backend.qa.loop.has_recurring_issues", return_value=(True, [sample_issues[0]])
        ), patch(
            "apps.backend.qa.loop.record_iteration"
        ), patch(
            "apps.backend.qa.loop.get_iteration_history", return_value=plan["qa_iteration_history"]
        ), patch(
            "apps.backend.qa.loop.get_qa_signoff_status"
        ) as mock_status, patch(
            "apps.backend.qa.loop.get_recurring_issue_summary", return_value={"total_issues": 3, "unique_issues": 1}
        ), patch(
            "apps.backend.qa.loop.is_linear_enabled", return_value=False
        ), patch(
            "apps.backend.qa.loop.emit_phase"
        ), patch(
            "apps.backend.qa.loop.TaskEventEmitter"
        ) as mock_emitter_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_create_client.return_value = mock_client

            # Return rejected status with same recurring issue
            mock_status.return_value = {
                "status": "rejected",
                "issues_found": [sample_issues[0]],
            }

            mock_reviewer.return_value = ("rejected", "Issues found")
            mock_emitter = MagicMock()
            mock_emitter_class.from_spec_dir.return_value = mock_emitter

            result = await run_qa_validation_loop(
                temp_project_dir, temp_spec_dir, model="claude-3-5-sonnet-20241022"
            )

        assert result is False
        # Escalation file should be created
        escalation_file = temp_spec_dir / "QA_ESCALATION.md"
        assert escalation_file.exists()

    @pytest.mark.asyncio
    async def test_max_iterations_returns_false(
        self, temp_spec_dir: Path, temp_project_dir: Path, rejected_plan: dict
    ) -> None:
        """Test that reaching max iterations returns False."""
        plan = rejected_plan.copy()
        plan["qa_signoff"]["qa_session"] = MAX_QA_ITERATIONS  # Already at max
        create_spec_files(temp_spec_dir, plan)

        with patch("apps.backend.qa.loop.is_build_complete", return_value=True), patch(
            "apps.backend.qa.loop.is_qa_approved", return_value=False
        ), patch("apps.backend.qa.loop.is_no_test_project", return_value=False), patch(
            "apps.backend.qa.loop.create_client"
        ) as mock_create_client, patch(
            "apps.backend.qa.loop.run_qa_agent_session", new_callable=AsyncMock
        ) as mock_reviewer:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_create_client.return_value = mock_client
            mock_reviewer.return_value = ("rejected", "Still issues")

            result = await run_qa_validation_loop(
                temp_project_dir, temp_spec_dir, model="claude-3-5-sonnet-20241022"
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_consecutive_errors_escalates(
        self, temp_spec_dir: Path, temp_project_dir: Path, sample_implementation_plan: dict
    ) -> None:
        """Test that consecutive errors trigger escalation."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        with patch("apps.backend.qa.loop.is_build_complete", return_value=True), patch(
            "apps.backend.qa.loop.is_qa_approved", return_value=False
        ), patch("apps.backend.qa.loop.is_no_test_project", return_value=False), patch(
            "apps.backend.qa.loop.create_client"
        ) as mock_create_client, patch(
            "apps.backend.qa.loop.run_qa_agent_session", new_callable=AsyncMock
        ) as mock_reviewer, patch(
            "apps.backend.qa.loop.emit_phase"
        ), patch(
            "apps.backend.qa.loop.TaskEventEmitter"
        ) as mock_emitter_class, patch(
            "apps.backend.qa.loop.get_task_logger"
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_create_client.return_value = mock_client

            # Return error MAX_CONSECUTIVE_ERRORS times
            mock_reviewer.return_value = ("error", "SDK error")

            mock_emitter = MagicMock()
            mock_emitter_class.from_spec_dir.return_value = mock_emitter

            result = await run_qa_validation_loop(
                temp_project_dir, temp_spec_dir, model="claude-3-5-sonnet-20241022"
            )

        assert result is False
        # Should have been called MAX_CONSECUTIVE_ERRORS times
        assert mock_reviewer.call_count == MAX_CONSECUTIVE_ERRORS

    @pytest.mark.asyncio
    async def test_linear_integration(
        self, temp_spec_dir: Path, temp_project_dir: Path, sample_implementation_plan: dict
    ) -> None:
        """Test Linear integration during QA loop."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        mock_linear_task = MagicMock()
        mock_linear_task.task_id = "LIN-123"

        with patch("apps.backend.qa.loop.is_build_complete", return_value=True), patch(
            "apps.backend.qa.loop.is_qa_approved", return_value=False
        ), patch("apps.backend.qa.loop.is_no_test_project", return_value=False), patch(
            "apps.backend.qa.loop.is_linear_enabled", return_value=True
        ), patch(
            "apps.backend.qa.loop.LinearTaskState.load", return_value=mock_linear_task
        ), patch(
            "apps.backend.qa.loop.linear_qa_started", new_callable=AsyncMock
        ) as mock_started, patch(
            "apps.backend.qa.loop.linear_qa_approved", new_callable=AsyncMock
        ) as mock_approved, patch(
            "apps.backend.qa.loop.create_client"
        ) as mock_create_client, patch(
            "apps.backend.qa.loop.run_qa_agent_session", new_callable=AsyncMock
        ) as mock_reviewer:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_create_client.return_value = mock_client
            mock_reviewer.return_value = ("approved", "Approved")

            result = await run_qa_validation_loop(
                temp_project_dir, temp_spec_dir, model="claude-3-5-sonnet-20241022"
            )

        assert result is True
        mock_started.assert_called_once_with(temp_spec_dir)
        mock_approved.assert_called_once_with(temp_spec_dir)

    @pytest.mark.asyncio
    async def test_task_logger_integration(
        self, temp_spec_dir: Path, temp_project_dir: Path, sample_implementation_plan: dict, mock_task_logger: MagicMock
    ) -> None:
        """Test task logger integration."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        with patch("apps.backend.qa.loop.is_build_complete", return_value=True), patch(
            "apps.backend.qa.loop.is_qa_approved", return_value=False
        ), patch("apps.backend.qa.loop.is_no_test_project", return_value=False), patch(
            "apps.backend.qa.loop.get_task_logger", return_value=mock_task_logger
        ), patch(
            "apps.backend.qa.loop.create_client"
        ) as mock_create_client, patch(
            "apps.backend.qa.loop.run_qa_agent_session", new_callable=AsyncMock
        ) as mock_reviewer:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_create_client.return_value = mock_client
            mock_reviewer.return_value = ("approved", "Approved")

            await run_qa_validation_loop(
                temp_project_dir, temp_spec_dir, model="claude-3-5-sonnet-20241022"
            )

        # Verify phase start/end was called
        mock_task_logger.start_phase.assert_called()
        mock_task_logger.end_phase.assert_called_with(
            ANY, success=True, message=ANY
        )

    @pytest.mark.asyncio
    async def test_iteration_recording(
        self, temp_spec_dir: Path, temp_project_dir: Path, sample_implementation_plan: dict
    ) -> None:
        """Test that iterations are recorded properly."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        with patch("apps.backend.qa.loop.is_build_complete", return_value=True), patch(
            "apps.backend.qa.loop.is_qa_approved", return_value=False
        ), patch("apps.backend.qa.loop.is_no_test_project", return_value=False), patch(
            "apps.backend.qa.loop.create_client"
        ) as mock_create_client, patch(
            "apps.backend.qa.loop.run_qa_agent_session", new_callable=AsyncMock
        ) as mock_reviewer, patch(
            "apps.backend.qa.loop.record_iteration"
        ) as mock_record, patch(
            "apps.backend.qa.loop.get_qa_signoff_status"
        ) as mock_status:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_create_client.return_value = mock_client
            mock_reviewer.return_value = ("approved", "Approved")
            mock_status.return_value = {
                "status": "approved",
                "tests_passed": {"unit": "10/10"},
            }

            await run_qa_validation_loop(
                temp_project_dir, temp_spec_dir, model="claude-3-5-sonnet-20241022"
            )

        # Iteration should be recorded
        mock_record.assert_called_once()
        call_args = mock_record.call_args[0]
        assert call_args[1] == 1  # iteration number
        assert call_args[2] == "approved"  # status

    @pytest.mark.asyncio
    async def test_error_context_builds_for_retry(
        self, temp_spec_dir: Path, temp_project_dir: Path, sample_implementation_plan: dict
    ) -> None:
        """Test that error context is built for consecutive error retries."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        error_count = {"count": 0}

        async def mock_reviewer_with_error(client, *args, previous_error=None, **kwargs):
            error_count["count"] += 1
            if error_count["count"] <= 2:
                return ("error", "Failed to update plan")
            return ("approved", "Approved")

        with patch("apps.backend.qa.loop.is_build_complete", return_value=True), patch(
            "apps.backend.qa.loop.is_qa_approved", return_value=False
        ), patch("apps.backend.qa.loop.is_no_test_project", return_value=False), patch(
            "apps.backend.qa.loop.create_client"
        ) as mock_create_client, patch(
            "apps.backend.qa.loop.run_qa_agent_session", new=mock_reviewer_with_error
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_create_client.return_value = mock_client

            await run_qa_validation_loop(
                temp_project_dir, temp_spec_dir, model="claude-3-5-sonnet-20241022"
            )

        # On the second call, previous_error should have been passed
        # Verify by checking that create_client was called multiple times
        assert mock_create_client.call_count >= 2

    @pytest.mark.asyncio
    async def test_final_summary_on_max_iterations(
        self, temp_spec_dir: Path, temp_project_dir: Path, sample_implementation_plan: dict, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that summary is shown when max iterations is reached."""
        plan = sample_implementation_plan.copy()
        plan["qa_signoff"]["qa_session"] = 1
        # Add some iteration history
        plan["qa_iteration_history"] = [
            {"iteration": 1, "status": "rejected", "issues": [{"title": "Issue 1"}], "timestamp": "2024-01-01T00:00:00Z"}
        ]
        create_spec_files(temp_spec_dir, plan)

        with patch("apps.backend.qa.loop.is_build_complete", return_value=True), patch(
            "apps.backend.qa.loop.is_qa_approved", return_value=False
        ), patch("apps.backend.qa.loop.is_no_test_project", return_value=False), patch(
            "apps.backend.qa.loop.create_client"
        ) as mock_create_client, patch(
            "apps.backend.qa.loop.run_qa_agent_session", new_callable=AsyncMock
        ) as mock_reviewer, patch(
            "apps.backend.qa.loop.get_recurring_issue_summary", return_value={
                "total_issues": 5,
                "unique_issues": 2,
                "most_common": [{"title": "Issue 1", "occurrences": 3}],
            }
        ), patch(
            "apps.backend.qa.loop.is_linear_enabled", return_value=False
        ), patch(
            "apps.backend.qa.loop.emit_phase"
        ), patch(
            "apps.backend.qa.loop.TaskEventEmitter"
        ) as mock_emitter_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_create_client.return_value = mock_client
            mock_reviewer.return_value = ("rejected", "Still issues")

            mock_emitter = MagicMock()
            mock_emitter_class.from_spec_dir.return_value = mock_emitter

            await run_qa_validation_loop(
                temp_project_dir, temp_spec_dir, model="claude-3-5-sonnet-20241022"
            )

        captured = capsys.readouterr()
        assert "QA VALIDATION INCOMPLETE" in captured.out
        assert "Total issues found: 5" in captured.out
        assert "Unique issues: 2" in captured.out

    @pytest.mark.asyncio
    async def test_phase_events_emitted(
        self, temp_spec_dir: Path, temp_project_dir: Path, sample_implementation_plan: dict
    ) -> None:
        """Test that phase events are properly emitted."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        with patch("apps.backend.qa.loop.is_build_complete", return_value=True), patch(
            "apps.backend.qa.loop.is_qa_approved", return_value=False
        ), patch("apps.backend.qa.loop.is_no_test_project", return_value=False), patch(
            "apps.backend.qa.loop.create_client"
        ) as mock_create_client, patch(
            "apps.backend.qa.loop.run_qa_agent_session", new_callable=AsyncMock
        ) as mock_reviewer, patch(
            "apps.backend.qa.loop.emit_phase"
        ) as mock_emit:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_create_client.return_value = mock_client
            mock_reviewer.return_value = ("approved", "Approved")

            await run_qa_validation_loop(
                temp_project_dir, temp_spec_dir, model="claude-3-5-sonnet-20241022"
            )

        # Check that key phases were emitted
        phase_calls = [call[0][0] for call in mock_emit.call_args_list]
        from phase_event import ExecutionPhase
        assert ExecutionPhase.QA_REVIEW in phase_calls
        assert ExecutionPhase.COMPLETE in phase_calls
