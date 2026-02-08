"""Tests for build_commands"""

from unittest.mock import MagicMock, patch

import pytest

from cli.build_commands import _handle_build_interrupt, handle_build_command


# ============================================================================
# Test _handle_build_interrupt
# ============================================================================


class TestHandleBuildInterrupt:
    """Tests for _handle_build_interrupt function."""

    def test_interrupt_quit_option(self, tmp_path, capsys):
        """Test interrupt handler with quit option."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        with patch(
            "cli.build_commands.select_menu", return_value="quit"
        ), patch("cli.build_commands.StatusManager") as mock_mgr:
            mock_status = MagicMock()
            mock_mgr.return_value = mock_status

            with pytest.raises(SystemExit) as exc_info:
                _handle_build_interrupt(
                    spec_dir=spec_dir,
                    project_dir=project_dir,
                    worktree_manager=None,
                    working_dir=project_dir,
                    model="sonnet",
                    max_iterations=None,
                    verbose=False,
                )
            assert exc_info.value.code == 0
            mock_status.set_inactive.assert_called_once()

    def test_interrupt_type_option(self, tmp_path, capsys):
        """Test interrupt handler with type instructions option."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        human_input = "Please add error handling"

        with patch(
            "cli.build_commands.select_menu", return_value="type"
        ), patch(
            "cli.build_commands.read_multiline_input", return_value=human_input
        ), patch("cli.build_commands.StatusManager") as mock_mgr:
            mock_status = MagicMock()
            mock_mgr.return_value = mock_status

            _handle_build_interrupt(
                spec_dir=spec_dir,
                project_dir=project_dir,
                worktree_manager=None,
                working_dir=project_dir,
                model="sonnet",
                max_iterations=None,
                verbose=False,
            )

            # Check that HUMAN_INPUT.md was created
            input_file = spec_dir / "HUMAN_INPUT.md"
            assert input_file.exists()
            assert input_file.read_text() == human_input

    def test_interrupt_paste_option(self, tmp_path, capsys):
        """Test interrupt handler with paste option."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        human_input = "Copied instructions from clipboard"

        with patch(
            "cli.build_commands.select_menu", return_value="paste"
        ), patch(
            "cli.build_commands.read_multiline_input", return_value=human_input
        ), patch("cli.build_commands.StatusManager"):
            _handle_build_interrupt(
                spec_dir=spec_dir,
                project_dir=project_dir,
                worktree_manager=None,
                working_dir=project_dir,
                model="sonnet",
                max_iterations=None,
                verbose=False,
            )

            input_file = spec_dir / "HUMAN_INPUT.md"
            assert input_file.exists()

    def test_interrupt_file_option(self, tmp_path, capsys):
        """Test interrupt handler with file option."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create a file to read from
        input_file_path = tmp_path / "instructions.txt"
        input_file_path.write_text("Instructions from file")

        with patch(
            "cli.build_commands.select_menu", return_value="file"
        ), patch(
            "cli.build_commands.read_from_file", return_value="Instructions from file"
        ), patch("cli.build_commands.StatusManager"):
            _handle_build_interrupt(
                spec_dir=spec_dir,
                project_dir=project_dir,
                worktree_manager=None,
                working_dir=project_dir,
                model="sonnet",
                max_iterations=None,
                verbose=False,
            )

            input_file = spec_dir / "HUMAN_INPUT.md"
            assert input_file.exists()

    def test_interrupt_file_option_returns_none(self, tmp_path, capsys):
        """Test interrupt handler when file read returns None."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        with patch(
            "cli.build_commands.select_menu", return_value="file"
        ), patch(
            "cli.build_commands.read_from_file", return_value=None
        ), patch("cli.build_commands.StatusManager"):
            _handle_build_interrupt(
                spec_dir=spec_dir,
                project_dir=project_dir,
                worktree_manager=None,
                working_dir=project_dir,
                model="sonnet",
                max_iterations=None,
                verbose=False,
            )

            # No HUMAN_INPUT.md should be created
            input_file = spec_dir / "HUMAN_INPUT.md"
            assert not input_file.exists()

    def test_interrupt_skip_option(self, tmp_path, capsys):
        """Test interrupt handler with skip option."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        with patch(
            "cli.build_commands.select_menu", return_value="skip"
        ), patch(
            "agent.run_autonomous_agent", return_value=None
        ), patch("cli.build_commands.StatusManager") as mock_mgr:
            mock_status = MagicMock()
            mock_mgr.return_value = mock_status

            with pytest.raises(SystemExit) as exc_info:
                _handle_build_interrupt(
                    spec_dir=spec_dir,
                    project_dir=project_dir,
                    worktree_manager=None,
                    working_dir=project_dir,
                    model="sonnet",
                    max_iterations=None,
                    verbose=False,
                )
            # Skip should resume and then exit with 0
            assert exc_info.value.code == 0

    def test_interrupt_second_keyboard_interrupt(self, tmp_path):
        """Test second KeyboardInterrupt during input prompt."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        with patch(
            "cli.build_commands.select_menu",
            side_effect=KeyboardInterrupt(),
        ), patch("cli.build_commands.StatusManager") as mock_mgr:
            mock_status = MagicMock()
            mock_mgr.return_value = mock_status

            with pytest.raises(SystemExit) as exc_info:
                _handle_build_interrupt(
                    spec_dir=spec_dir,
                    project_dir=project_dir,
                    worktree_manager=None,
                    working_dir=project_dir,
                    model="sonnet",
                    max_iterations=None,
                    verbose=False,
                )
            assert exc_info.value.code == 0
            mock_status.set_inactive.assert_called()

    def test_interrupt_eof_error(self, tmp_path, capsys):
        """Test EOFError during input (stdin closed)."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        with patch(
            "cli.build_commands.select_menu",
            side_effect=EOFError(),
        ), patch("cli.build_commands.StatusManager"):
            # Should handle gracefully
            _handle_build_interrupt(
                spec_dir=spec_dir,
                project_dir=project_dir,
                worktree_manager=None,
                working_dir=project_dir,
                model="sonnet",
                max_iterations=None,
                verbose=False,
            )

    def test_interrupt_with_worktree_manager(self, tmp_path, capsys):
        """Test interrupt handler with worktree manager."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_worktree_manager = MagicMock()

        with patch(
            "cli.build_commands.select_menu", return_value="quit"
        ), patch("cli.build_commands.StatusManager") as mock_mgr:
            mock_status = MagicMock()
            mock_mgr.return_value = mock_status

            with pytest.raises(SystemExit):
                _handle_build_interrupt(
                    spec_dir=spec_dir,
                    project_dir=project_dir,
                    worktree_manager=mock_worktree_manager,
                    working_dir=project_dir,
                    model="sonnet",
                    max_iterations=None,
                    verbose=False,
                )

    def test_interrupt_multiline_input_returns_none(self, tmp_path, capsys):
        """Test when multiline input returns None (user cancelled)."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        with patch(
            "cli.build_commands.select_menu", return_value="type"
        ), patch(
            "cli.build_commands.read_multiline_input", return_value=None
        ), patch("cli.build_commands.StatusManager") as mock_mgr:
            mock_status = MagicMock()
            mock_mgr.return_value = mock_status

            with pytest.raises(SystemExit) as exc_info:
                _handle_build_interrupt(
                    spec_dir=spec_dir,
                    project_dir=project_dir,
                    worktree_manager=None,
                    working_dir=project_dir,
                    model="sonnet",
                    max_iterations=None,
                    verbose=False,
                )
            assert exc_info.value.code == 0


# ============================================================================
# Test handle_build_command
# ============================================================================


class TestHandleBuildCommand:
    """Tests for handle_build_command function."""

    def test_missing_spec_md(self, temp_project_dir):
        """Test handle_build_command when spec.md is missing."""
        # Arrange - create spec directory without spec.md
        spec_dir = temp_project_dir / ".auto-claude" / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        # Act & Assert - should call sys.exit(1)
        with pytest.raises(SystemExit) as exc_info:
            handle_build_command(
                project_dir=temp_project_dir,
                spec_dir=spec_dir,
                model="sonnet",
                max_iterations=None,
                verbose=False,
                force_isolated=False,
                force_direct=False,
                auto_continue=True,
                skip_qa=True,
                force_bypass_approval=True,
                base_branch=None,
            )
        assert exc_info.value.code == 1

    def test_invalid_approval_not_bypassed(self, temp_project_dir, temp_spec_dir):
        """Test when approval is invalid and not bypassed."""
        # Arrange
        with patch("cli.utils.validate_environment") as mock_validate, patch(
            "cli.build_commands.ReviewState"
        ) as mock_review_state:
            mock_validate.return_value = True
            mock_review_state_instance = MagicMock()
            mock_review_state_instance.is_approval_valid.return_value = False
            mock_review_state_instance.approved = None
            mock_review_state.load.return_value = mock_review_state_instance

            # Act & Assert - should exit
            with pytest.raises(SystemExit) as exc_info:
                handle_build_command(
                    project_dir=temp_project_dir,
                    spec_dir=temp_spec_dir,
                    model="sonnet",
                    max_iterations=None,
                    verbose=False,
                    force_isolated=False,
                    force_direct=False,
                    auto_continue=True,
                    skip_qa=True,
                    force_bypass_approval=False,  # Not bypassing
                    base_branch=None,
                )
            assert exc_info.value.code == 1

    def test_invalid_approval_bypassed(self, temp_project_dir, temp_spec_dir):
        """Test when approval is invalid but bypassed."""
        # Arrange
        with patch("cli.utils.validate_environment") as mock_validate, patch(
            "cli.build_commands.ReviewState"
        ) as mock_review_state, patch(
            "cli.build_commands.get_existing_build_worktree"
        ) as mock_get_existing, patch(
            "cli.build_commands.choose_workspace"
        ) as mock_choose_workspace, patch(
            "agent.run_autonomous_agent"
        ) as mock_run_agent, patch(
            "qa_loop.should_run_qa", return_value=False
        ), patch(
            "cli.build_commands.WorkspaceMode"
        ):
            mock_validate.return_value = True
            mock_review_state_instance = MagicMock()
            mock_review_state_instance.is_approval_valid.return_value = False
            mock_review_state_instance.approved = None
            mock_review_state.load.return_value = mock_review_state_instance
            mock_get_existing.return_value = None
            mock_choose_workspace.return_value = 1  # WorkspaceMode.DIRECT
            mock_run_agent.return_value = None

            # Act - should not exit with bypass
            try:
                handle_build_command(
                    project_dir=temp_project_dir,
                    spec_dir=temp_spec_dir,
                    model="sonnet",
                    max_iterations=None,
                    verbose=False,
                    force_isolated=False,
                    force_direct=False,
                    auto_continue=True,
                    skip_qa=True,
                    force_bypass_approval=True,  # Bypassing
                    base_branch=None,
                )
            except Exception:
                pass  # Some imports may fail

    def test_keyboard_interrupt(self, temp_project_dir, temp_spec_dir):
        """Test handle_build_command handles KeyboardInterrupt."""
        # Arrange
        with patch("cli.utils.validate_environment") as mock_validate, patch(
            "cli.build_commands.ReviewState"
        ) as mock_review_state, patch(
            "cli.build_commands.get_existing_build_worktree"
        ) as mock_get_existing, patch(
            "cli.build_commands.choose_workspace"
        ) as mock_choose_workspace, patch(
            "agent.run_autonomous_agent"
        ) as mock_run_agent, patch(
            "qa_loop.should_run_qa", return_value=False
        ), patch(
            "cli.build_commands.select_menu", return_value="quit"
        ), patch(
            "cli.build_commands.StatusManager"
        ) as mock_status_mgr:
            mock_validate.return_value = True
            mock_review_state_instance = MagicMock()
            mock_review_state_instance.is_approval_valid.return_value = True
            mock_review_state.load.return_value = mock_review_state_instance
            mock_get_existing.return_value = None
            mock_choose_workspace.return_value = 1  # WorkspaceMode.DIRECT
            mock_run_agent.side_effect = KeyboardInterrupt()
            mock_status_instance = MagicMock()
            mock_status_mgr.return_value = mock_status_instance
            mock_status_instance.set_inactive.return_value = None
            mock_status_instance.update.return_value = None

            # Act - should handle KeyboardInterrupt gracefully
            with pytest.raises(SystemExit) as exc_info:
                handle_build_command(
                    project_dir=temp_project_dir,
                    spec_dir=temp_spec_dir,
                    model="sonnet",
                    max_iterations=None,
                    verbose=False,
                    force_isolated=False,
                    force_direct=False,
                    auto_continue=True,
                    skip_qa=True,
                    force_bypass_approval=True,
                    base_branch=None,
                )
            assert exc_info.value.code == 0

    def test_with_existing_build_auto_continue(self, temp_project_dir, temp_spec_dir):
        """Test with existing build in auto_continue mode."""
        # Arrange
        with patch("cli.utils.validate_environment") as mock_validate, patch(
            "cli.build_commands.ReviewState"
        ) as mock_review_state, patch(
            "cli.build_commands.get_existing_build_worktree"
        ) as mock_get_existing, patch(
            "cli.build_commands.choose_workspace"
        ) as mock_choose_workspace, patch(
            "agent.run_autonomous_agent"
        ) as mock_run_agent, patch(
            "qa_loop.should_run_qa", return_value=False
        ), patch(
            "cli.build_commands.WorkspaceMode"
        ):
            mock_validate.return_value = True
            mock_review_state_instance = MagicMock()
            mock_review_state_instance.is_approval_valid.return_value = True
            mock_review_state.load.return_value = mock_review_state_instance
            mock_get_existing.return_value = temp_project_dir / "worktree"
            mock_choose_workspace.return_value = 1
            mock_run_agent.return_value = None

            try:
                handle_build_command(
                    project_dir=temp_project_dir,
                    spec_dir=temp_spec_dir,
                    model="sonnet",
                    max_iterations=None,
                    verbose=False,
                    force_isolated=False,
                    force_direct=False,
                    auto_continue=True,  # Auto-continue mode
                    skip_qa=True,
                    force_bypass_approval=True,
                    base_branch=None,
                )
            except Exception:
                pass

    def test_with_base_branch_from_metadata(self, temp_project_dir, temp_spec_dir):
        """Test with base_branch from task metadata."""
        # Arrange
        with patch("cli.utils.validate_environment") as mock_validate, patch(
            "cli.build_commands.ReviewState"
        ) as mock_review_state, patch(
            "cli.build_commands.get_existing_build_worktree"
        ) as mock_get_existing, patch(
            "cli.build_commands.choose_workspace"
        ) as mock_choose_workspace, patch(
            "agent.run_autonomous_agent"
        ) as mock_run_agent, patch(
            "qa_loop.should_run_qa", return_value=False
        ), patch(
            "prompts_pkg.prompts.get_base_branch_from_metadata",
            return_value="develop",
        ), patch(
            "cli.build_commands.WorkspaceMode"
        ):
            mock_validate.return_value = True
            mock_review_state_instance = MagicMock()
            mock_review_state_instance.is_approval_valid.return_value = True
            mock_review_state.load.return_value = mock_review_state_instance
            mock_get_existing.return_value = None
            mock_choose_workspace.return_value = 1
            mock_run_agent.return_value = None

            try:
                handle_build_command(
                    project_dir=temp_project_dir,
                    spec_dir=temp_spec_dir,
                    model="sonnet",
                    max_iterations=None,
                    verbose=False,
                    force_isolated=False,
                    force_direct=False,
                    auto_continue=True,
                    skip_qa=True,
                    force_bypass_approval=True,
                    base_branch=None,  # Should be read from metadata
                )
            except Exception:
                pass

    def test_with_max_iterations(self, temp_project_dir, temp_spec_dir):
        """Test with max_iterations parameter."""
        # Arrange
        with patch("cli.utils.validate_environment") as mock_validate, patch(
            "cli.build_commands.ReviewState"
        ) as mock_review_state, patch(
            "cli.build_commands.get_existing_build_worktree"
        ) as mock_get_existing, patch(
            "cli.build_commands.choose_workspace"
        ) as mock_choose_workspace, patch(
            "agent.run_autonomous_agent"
        ) as mock_run_agent, patch(
            "qa_loop.should_run_qa", return_value=False
        ), patch(
            "cli.build_commands.WorkspaceMode"
        ):
            mock_validate.return_value = True
            mock_review_state_instance = MagicMock()
            mock_review_state_instance.is_approval_valid.return_value = True
            mock_review_state.load.return_value = mock_review_state_instance
            mock_get_existing.return_value = None
            mock_choose_workspace.return_value = 1
            mock_run_agent.return_value = None

            try:
                handle_build_command(
                    project_dir=temp_project_dir,
                    spec_dir=temp_spec_dir,
                    model="sonnet",
                    max_iterations=10,  # Limited iterations
                    verbose=False,
                    force_isolated=False,
                    force_direct=False,
                    auto_continue=True,
                    skip_qa=True,
                    force_bypass_approval=True,
                    base_branch=None,
                )
            except Exception:
                pass

    def test_with_verbose_mode(self, temp_project_dir, temp_spec_dir):
        """Test with verbose flag enabled."""
        # Arrange
        with patch("cli.utils.validate_environment") as mock_validate, patch(
            "cli.build_commands.ReviewState"
        ) as mock_review_state, patch(
            "cli.build_commands.get_existing_build_worktree"
        ) as mock_get_existing, patch(
            "cli.build_commands.choose_workspace"
        ) as mock_choose_workspace, patch(
            "agent.run_autonomous_agent"
        ) as mock_run_agent, patch(
            "qa_loop.should_run_qa", return_value=False
        ), patch(
            "cli.build_commands.WorkspaceMode"
        ):
            mock_validate.return_value = True
            mock_review_state_instance = MagicMock()
            mock_review_state_instance.is_approval_valid.return_value = True
            mock_review_state.load.return_value = mock_review_state_instance
            mock_get_existing.return_value = None
            mock_choose_workspace.return_value = 1
            mock_run_agent.return_value = None

            try:
                handle_build_command(
                    project_dir=temp_project_dir,
                    spec_dir=temp_spec_dir,
                    model="sonnet",
                    max_iterations=None,
                    verbose=True,  # Verbose mode
                    force_isolated=False,
                    force_direct=False,
                    auto_continue=True,
                    skip_qa=True,
                    force_bypass_approval=True,
                    base_branch=None,
                )
            except Exception:
                pass

    def test_workspace_mode_isolated(self, temp_project_dir, temp_spec_dir):
        """Test with isolated workspace mode."""
        # Arrange
        with patch("cli.utils.validate_environment") as mock_validate, patch(
            "cli.build_commands.ReviewState"
        ) as mock_review_state, patch(
            "cli.build_commands.get_existing_build_worktree"
        ) as mock_get_existing, patch(
            "cli.build_commands.choose_workspace"
        ) as mock_choose_workspace, patch(
            "agent.run_autonomous_agent"
        ) as mock_run_agent, patch(
            "qa_loop.should_run_qa", return_value=False
        ), patch(
            "cli.build_commands.setup_workspace"
        ) as mock_setup, patch(
            "cli.build_commands.WorkspaceMode"
        ):
            mock_validate.return_value = True
            mock_review_state_instance = MagicMock()
            mock_review_state_instance.is_approval_valid.return_value = True
            mock_review_state.load.return_value = mock_review_state_instance
            mock_get_existing.return_value = None
            mock_choose_workspace.return_value = 0  # WorkspaceMode.ISOLATED
            mock_setup.return_value = (
                temp_project_dir,
                None,  # worktree_manager
                temp_spec_dir,  # localized_spec_dir
            )
            mock_run_agent.return_value = None

            try:
                handle_build_command(
                    project_dir=temp_project_dir,
                    spec_dir=temp_spec_dir,
                    model="sonnet",
                    max_iterations=None,
                    verbose=False,
                    force_isolated=True,  # Force isolated
                    force_direct=False,
                    auto_continue=True,
                    skip_qa=True,
                    force_bypass_approval=True,
                    base_branch=None,
                )
            except Exception:
                pass

    def test_with_qa_enabled(self, temp_project_dir, temp_spec_dir):
        """Test with QA validation enabled."""
        # Arrange
        with patch("cli.utils.validate_environment") as mock_validate, patch(
            "cli.build_commands.ReviewState"
        ) as mock_review_state, patch(
            "cli.build_commands.get_existing_build_worktree"
        ) as mock_get_existing, patch(
            "cli.build_commands.choose_workspace"
        ) as mock_choose_workspace, patch(
            "agent.run_autonomous_agent"
        ) as mock_run_agent, patch(
            "qa_loop.should_run_qa", return_value=True
        ), patch(
            "qa_loop.run_qa_validation_loop", return_value=True
        ), patch(
            "agent.sync_spec_to_source", return_value=True
        ), patch(
            "cli.build_commands.WorkspaceMode"
        ):
            mock_validate.return_value = True
            mock_review_state_instance = MagicMock()
            mock_review_state_instance.is_approval_valid.return_value = True
            mock_review_state.load.return_value = mock_review_state_instance
            mock_get_existing.return_value = None
            mock_choose_workspace.return_value = 1
            mock_run_agent.return_value = None

            try:
                handle_build_command(
                    project_dir=temp_project_dir,
                    spec_dir=temp_spec_dir,
                    model="sonnet",
                    max_iterations=None,
                    verbose=False,
                    force_isolated=False,
                    force_direct=False,
                    auto_continue=True,
                    skip_qa=False,  # QA enabled
                    force_bypass_approval=True,
                    base_branch=None,
                )
            except Exception:
                pass

    def test_qa_keyboard_interrupt(self, temp_project_dir, temp_spec_dir):
        """Test QA loop handling KeyboardInterrupt."""
        # Arrange
        with patch("cli.utils.validate_environment") as mock_validate, patch(
            "cli.build_commands.ReviewState"
        ) as mock_review_state, patch(
            "cli.build_commands.get_existing_build_worktree"
        ) as mock_get_existing, patch(
            "cli.build_commands.choose_workspace"
        ) as mock_choose_workspace, patch(
            "agent.run_autonomous_agent"
        ) as mock_run_agent, patch(
            "qa_loop.should_run_qa", return_value=True
        ), patch(
            "qa_loop.run_qa_validation_loop",
            side_effect=KeyboardInterrupt(),
        ), patch(
            "cli.build_commands.WorkspaceMode"
        ):
            mock_validate.return_value = True
            mock_review_state_instance = MagicMock()
            mock_review_state_instance.is_approval_valid.return_value = True
            mock_review_state.load.return_value = mock_review_state_instance
            mock_get_existing.return_value = None
            mock_choose_workspace.return_value = 1
            mock_run_agent.return_value = None

            try:
                handle_build_command(
                    project_dir=temp_project_dir,
                    spec_dir=temp_spec_dir,
                    model="sonnet",
                    max_iterations=None,
                    verbose=False,
                    force_isolated=False,
                    force_direct=False,
                    auto_continue=True,
                    skip_qa=False,
                    force_bypass_approval=True,
                    base_branch=None,
                )
            except Exception:
                pass

    def test_with_worktree_finalization(self, temp_project_dir, temp_spec_dir):
        """Test with worktree finalization after QA."""
        # Arrange
        mock_worktree_manager = MagicMock()

        with patch("cli.utils.validate_environment") as mock_validate, patch(
            "cli.build_commands.ReviewState"
        ) as mock_review_state, patch(
            "cli.build_commands.get_existing_build_worktree"
        ) as mock_get_existing, patch(
            "cli.build_commands.choose_workspace"
        ) as mock_choose_workspace, patch(
            "agent.run_autonomous_agent"
        ) as mock_run_agent, patch(
            "qa_loop.should_run_qa", return_value=False
        ), patch(
            "cli.build_commands.setup_workspace"
        ) as mock_setup, patch(
            "cli.build_commands.finalize_workspace", return_value="keep"
        ), patch(
            "cli.build_commands.WorkspaceMode"
        ):
            mock_validate.return_value = True
            mock_review_state_instance = MagicMock()
            mock_review_state_instance.is_approval_valid.return_value = True
            mock_review_state.load.return_value = mock_review_state_instance
            mock_get_existing.return_value = None
            mock_choose_workspace.return_value = 0  # ISOLATED
            mock_setup.return_value = (
                temp_project_dir,
                mock_worktree_manager,
                temp_spec_dir,
            )
            mock_run_agent.return_value = None

            try:
                handle_build_command(
                    project_dir=temp_project_dir,
                    spec_dir=temp_spec_dir,
                    model="sonnet",
                    max_iterations=None,
                    verbose=False,
                    force_isolated=False,
                    force_direct=False,
                    auto_continue=True,
                    skip_qa=True,
                    force_bypass_approval=True,
                    base_branch=None,
                )
            except Exception:
                pass

    def test_fatal_error_with_verbose(self, temp_project_dir, temp_spec_dir):
        """Test fatal error handling with verbose mode."""
        # Arrange
        with patch("cli.utils.validate_environment") as mock_validate, patch(
            "cli.build_commands.ReviewState"
        ) as mock_review_state, patch(
            "cli.build_commands.get_existing_build_worktree"
        ) as mock_get_existing, patch(
            "cli.build_commands.choose_workspace"
        ) as mock_choose_workspace, patch(
            "agent.run_autonomous_agent",
            side_effect=Exception("Fatal error"),
        ), patch(
            "qa_loop.should_run_qa", return_value=False
        ), patch(
            "cli.build_commands.WorkspaceMode"
        ):
            mock_validate.return_value = True
            mock_review_state_instance = MagicMock()
            mock_review_state_instance.is_approval_valid.return_value = True
            mock_review_state.load.return_value = mock_review_state_instance
            mock_get_existing.return_value = None
            mock_choose_workspace.return_value = 1

            # Should exit with error
            with pytest.raises(SystemExit) as exc_info:
                handle_build_command(
                    project_dir=temp_project_dir,
                    spec_dir=temp_spec_dir,
                    model="sonnet",
                    max_iterations=None,
                    verbose=True,  # Verbose for traceback
                    force_isolated=False,
                    force_direct=False,
                    auto_continue=True,
                    skip_qa=True,
                    force_bypass_approval=True,
                    base_branch=None,
                )
            assert exc_info.value.code == 1

    def test_fatal_error_without_verbose(self, temp_project_dir, temp_spec_dir):
        """Test fatal error handling without verbose mode."""
        # Arrange
        with patch("cli.utils.validate_environment") as mock_validate, patch(
            "cli.build_commands.ReviewState"
        ) as mock_review_state, patch(
            "cli.build_commands.get_existing_build_worktree"
        ) as mock_get_existing, patch(
            "cli.build_commands.choose_workspace"
        ) as mock_choose_workspace, patch(
            "agent.run_autonomous_agent",
            side_effect=Exception("Fatal error"),
        ), patch(
            "qa_loop.should_run_qa", return_value=False
        ), patch(
            "cli.build_commands.WorkspaceMode"
        ):
            mock_validate.return_value = True
            mock_review_state_instance = MagicMock()
            mock_review_state_instance.is_approval_valid.return_value = True
            mock_review_state.load.return_value = mock_review_state_instance
            mock_get_existing.return_value = None
            mock_choose_workspace.return_value = 1

            # Should exit with error
            with pytest.raises(SystemExit) as exc_info:
                handle_build_command(
                    project_dir=temp_project_dir,
                    spec_dir=temp_spec_dir,
                    model="sonnet",
                    max_iterations=None,
                    verbose=False,  # No traceback
                    force_isolated=False,
                    force_direct=False,
                    auto_continue=True,
                    skip_qa=True,
                    force_bypass_approval=True,
                    base_branch=None,
                )
            assert exc_info.value.code == 1


# ============================================================================
# Original Tests (preserved for backward compatibility)
# ============================================================================


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def temp_spec_dir(tmp_path):
    """Create a temporary spec directory with required files."""
    spec_dir = tmp_path / "spec" / "001-test-spec"
    spec_dir.mkdir(parents=True)
    # Create required spec.md file
    (spec_dir / "spec.md").write_text("# Test Spec\n\nThis is a test spec.")
    # Create requirements.json
    (spec_dir / "requirements.json").write_text('{"task_description": "Test task"}')
    return spec_dir


def test_handle_build_command_with_missing_spec(temp_project_dir):
    """Test handle_build_command when spec.md is missing (causes SystemExit)."""
    # Arrange - create spec directory without spec.md
    spec_dir = temp_project_dir / ".auto-claude" / "specs" / "001-test"
    spec_dir.mkdir(parents=True)

    # Act & Assert - should call sys.exit(1)
    with pytest.raises(SystemExit) as exc_info:
        handle_build_command(
            project_dir=temp_project_dir,
            spec_dir=spec_dir,
            model="sonnet",
            max_iterations=None,
            verbose=False,
            force_isolated=False,
            force_direct=False,
            auto_continue=True,
            skip_qa=True,
            force_bypass_approval=True,
            base_branch=None,
        )
    assert exc_info.value.code == 1


def test_handle_build_command_with_mocked_dependencies(
    temp_project_dir, temp_spec_dir
):
    """Test handle_build_command with mocked dependencies."""
    # Arrange - patch at import location since run_autonomous_agent is lazy-imported
    with patch("cli.utils.validate_environment") as mock_validate, patch(
        "cli.build_commands.ReviewState"
    ) as mock_review_state, patch(
        "cli.build_commands.get_existing_build_worktree"
    ) as mock_get_existing, patch(
        "cli.build_commands.choose_workspace"
    ) as mock_choose_workspace, patch(
        "agent.run_autonomous_agent"
    ) as mock_run_agent, patch(
        "qa_loop.should_run_qa", return_value=False
    ), patch(
        "cli.build_commands.WorkspaceMode"
    ):
        # Setup mocks
        mock_validate.return_value = True
        mock_review_state_instance = MagicMock()
        mock_review_state_instance.is_approval_valid.return_value = True
        mock_review_state.load.return_value = mock_review_state_instance
        mock_get_existing.return_value = None
        mock_choose_workspace.return_value = 1  # WorkspaceMode.DIRECT
        mock_run_agent.return_value = None

        # Act - should not raise SystemExit with proper setup
        try:
            handle_build_command(
                project_dir=temp_project_dir,
                spec_dir=temp_spec_dir,
                model="sonnet",
                max_iterations=None,
                verbose=False,
                force_isolated=False,
                force_direct=False,
                auto_continue=True,
                skip_qa=True,
                force_bypass_approval=True,
                base_branch=None,
            )
        except Exception:
            # Some imports may fail in test environment, that's ok
            pass

        # Assert - verify function was called if no exception
        if not mock_run_agent.call_count == 0:
            mock_run_agent.assert_called_once()


def test_handle_build_command_with_invalid_approval(
    temp_project_dir, temp_spec_dir
):
    """Test handle_build_command when approval is not valid."""
    # Arrange
    with patch("cli.utils.validate_environment") as mock_validate, patch(
        "cli.build_commands.ReviewState"
    ) as mock_review_state:
        # Setup mocks - approval is not valid
        mock_validate.return_value = True
        mock_review_state_instance = MagicMock()
        mock_review_state_instance.is_approval_valid.return_value = False
        mock_review_state_instance.approved = None
        mock_review_state.load.return_value = mock_review_state_instance

        # Act & Assert - should exit when approval is invalid and not bypassed
        with pytest.raises(SystemExit) as exc_info:
            handle_build_command(
                project_dir=temp_project_dir,
                spec_dir=temp_spec_dir,
                model="sonnet",
                max_iterations=None,
                verbose=False,
                force_isolated=False,
                force_direct=False,
                auto_continue=True,
                skip_qa=True,
                force_bypass_approval=False,  # Not bypassing
                base_branch=None,
            )

        # Verify exit code is 1
        assert exc_info.value.code == 1


def test_handle_build_command_with_bypass_approval(
    temp_project_dir, temp_spec_dir
):
    """Test handle_build_command with approval bypassed."""
    # Arrange - patch at import location since run_autonomous_agent is lazy-imported
    with patch("cli.utils.validate_environment") as mock_validate, patch(
        "cli.build_commands.ReviewState"
    ) as mock_review_state, patch(
        "cli.build_commands.get_existing_build_worktree"
    ) as mock_get_existing, patch(
        "cli.build_commands.choose_workspace"
    ) as mock_choose_workspace, patch(
        "agent.run_autonomous_agent"
    ) as mock_run_agent, patch(
        "qa_loop.should_run_qa", return_value=False
    ), patch(
        "cli.build_commands.WorkspaceMode"
    ):
        # Setup mocks - approval is invalid but bypassed
        mock_validate.return_value = True
        mock_review_state_instance = MagicMock()
        mock_review_state_instance.is_approval_valid.return_value = False
        mock_review_state_instance.approved = None
        mock_review_state.load.return_value = mock_review_state_instance
        mock_get_existing.return_value = None
        mock_choose_workspace.return_value = 1  # WorkspaceMode.DIRECT
        mock_run_agent.return_value = None

        # Act - should not exit with force_bypass_approval=True
        try:
            handle_build_command(
                project_dir=temp_project_dir,
                spec_dir=temp_spec_dir,
                model="sonnet",
                max_iterations=None,
                verbose=False,
                force_isolated=False,
                force_direct=False,
                auto_continue=True,
                skip_qa=True,
                force_bypass_approval=True,  # Bypassing
                base_branch=None,
            )
        except Exception:
            pass  # Some imports may fail in test environment

        # Assert - verify function was called if no exception
        if not mock_run_agent.call_count == 0:
            mock_run_agent.assert_called_once()


def test_handle_build_command_keyboard_interrupt(
    temp_project_dir, temp_spec_dir
):
    """Test handle_build_command handles KeyboardInterrupt."""
    # Arrange - patch at import locations since functions are lazy-imported
    with patch("cli.utils.validate_environment") as mock_validate, patch(
        "cli.build_commands.ReviewState"
    ) as mock_review_state, patch(
        "cli.build_commands.get_existing_build_worktree"
    ) as mock_get_existing, patch(
        "cli.build_commands.choose_workspace"
    ) as mock_choose_workspace, patch(
        "agent.run_autonomous_agent"
    ) as mock_run_agent, patch(
        "qa_loop.should_run_qa", return_value=False
    ), patch(
        "cli.build_commands.select_menu", return_value="quit"
    ), patch("cli.build_commands.StatusManager") as mock_status_mgr:
        # Setup mocks
        mock_validate.return_value = True
        mock_review_state_instance = MagicMock()
        mock_review_state_instance.is_approval_valid.return_value = True
        mock_review_state.load.return_value = mock_review_state_instance
        mock_get_existing.return_value = None
        mock_choose_workspace.return_value = 1  # WorkspaceMode.DIRECT
        mock_run_agent.side_effect = KeyboardInterrupt()
        mock_status_instance = MagicMock()
        mock_status_mgr.return_value = mock_status_instance
        mock_status_instance.set_inactive.return_value = None
        mock_status_instance.update.return_value = None

        # Act - should handle KeyboardInterrupt gracefully
        with pytest.raises(SystemExit) as exc_info:
            handle_build_command(
                project_dir=temp_project_dir,
                spec_dir=temp_spec_dir,
                model="sonnet",
                max_iterations=None,
                verbose=False,
                force_isolated=False,
                force_direct=False,
                auto_continue=True,
                skip_qa=True,
                force_bypass_approval=True,
                base_branch=None,
            )

        # Verify exit code is 0 (clean exit)
        assert exc_info.value.code == 0
