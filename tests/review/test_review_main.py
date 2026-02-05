"""Tests for review.main module facade."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from review import ReviewState, display_review_status, run_review_checkpoint
from ui import print_status


class TestReviewMainImports:
    """Tests for review.main module re-exports."""

    def test_imports_review_state(self):
        """Test that ReviewState can be imported from review."""
        from review import ReviewState as ImportedReviewState

        assert ImportedReviewState is ReviewState

    def test_imports_display_review_status(self):
        """Test that display_review_status can be imported from review."""
        from review import display_review_status as ImportedDisplay

        assert ImportedDisplay is display_review_status

    def test_imports_run_review_checkpoint(self):
        """Test that run_review_checkpoint can be imported from review."""
        from review import run_review_checkpoint as ImportedRun

        assert ImportedRun is run_review_checkpoint


class TestReviewMainFacade:
    """Tests for review.main as a facade module."""

    def test_main_function_exists(self):
        """Test that main function exists in review.main."""
        from review.main import main

        assert callable(main)

    @patch("review.main.run_review_checkpoint")
    @patch("review.main.ReviewState")
    @patch("review.main.print_status")
    def test_main_auto_approve_mode(
        self, mock_print_status, mock_review_state, mock_run_checkpoint, tmp_path
    ):
        """Test main() with --auto-approve flag."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        # Patch sys.argv with the actual spec_dir path
        with patch("sys.argv", ["review.py", "--spec-dir", str(spec_dir), "--auto-approve"]):
            mock_state = MagicMock()
            mock_state.is_approved.return_value = True
            mock_review_state.load.return_value = mock_state
            mock_run_checkpoint.return_value = mock_state

            from review.main import main

            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit with 0 on approval
            assert exc_info.value.code == 0
            mock_run_checkpoint.assert_called_once()

    @patch("review.main.display_review_status")
    @patch("review.main.ReviewState")
    @patch("review.main.print_status")
    def test_main_status_only(
        self, mock_print_status, mock_review_state, mock_display, tmp_path
    ):
        """Test main() with --status flag."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        # Patch sys.argv with the actual spec_dir path
        with patch("sys.argv", ["review.py", "--spec-dir", str(spec_dir), "--status"]):
            mock_state = MagicMock()
            mock_state.is_approval_valid.return_value = True
            mock_review_state.load.return_value = mock_state

            from review.main import main

            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit with 0 if approval valid
            assert exc_info.value.code == 0
            mock_display.assert_called_once()

    @patch("review.main.display_review_status")
    @patch("review.main.ReviewState")
    @patch("review.main.print_status")
    def test_main_status_not_approved(
        self, mock_print_status, mock_review_state, mock_display, tmp_path
    ):
        """Test main() --status when not approved."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        # Patch sys.argv with the actual spec_dir path
        with patch("sys.argv", ["review.py", "--spec-dir", str(spec_dir), "--status"]):
            mock_state = MagicMock()
            mock_state.is_approval_valid.return_value = False
            mock_review_state.load.return_value = mock_state

            from review.main import main

            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit with 1 if not approved
            assert exc_info.value.code == 1

    @patch("review.main.run_review_checkpoint")
    @patch("review.main.ReviewState")
    @patch("review.main.print_status")
    def test_main_interactive_mode(
        self, mock_print_status, mock_review_state, mock_run_checkpoint, tmp_path
    ):
        """Test main() in interactive mode (no flags)."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        # Patch sys.argv with the actual spec_dir path
        with patch("sys.argv", ["review.py", "--spec-dir", str(spec_dir)]):
            mock_state = MagicMock()
            mock_state.is_approved.return_value = True
            mock_review_state.load.return_value = mock_state
            mock_run_checkpoint.return_value = mock_state

            from review.main import main

            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should call run_review_checkpoint
            mock_run_checkpoint.assert_called_once()
            assert exc_info.value.code == 0

    @patch("review.main.run_review_checkpoint")
    @patch("review.main.ReviewState")
    @patch("review.main.print_status")
    def test_main_rejected_exits_with_1(
        self, mock_print_status, mock_review_state, mock_run_checkpoint, tmp_path
    ):
        """Test main() exits with 1 when review is rejected."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        # Patch sys.argv with the actual spec_dir path
        with patch("sys.argv", ["review.py", "--spec-dir", str(spec_dir)]):
            mock_state = MagicMock()
            mock_state.is_approved.return_value = False
            mock_review_state.load.return_value = mock_state
            mock_run_checkpoint.return_value = mock_state

            from review.main import main

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

    @patch("review.main.print_status")
    def test_main_nonexistent_spec_dir(self, mock_print_status, tmp_path):
        """Test main() with nonexistent spec directory."""
        # Use a path that doesn't exist within tmp_path
        nonexistent_path = tmp_path / "does_not_exist"

        with patch("sys.argv", ["review.py", "--spec-dir", str(nonexistent_path)]):
            from review.main import main

            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit with error code
            assert exc_info.value.code == 1
            mock_print_status.assert_called()

    @patch("review.main.run_review_checkpoint")
    @patch("review.main.ReviewState")
    @patch("review.main.print_status")
    def test_main_keyboard_interrupt(
        self, mock_print_status, mock_review_state, mock_run_checkpoint, tmp_path
    ):
        """Test main() handles KeyboardInterrupt gracefully."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        # Patch sys.argv with the actual spec_dir path
        with patch("sys.argv", ["review.py", "--spec-dir", str(spec_dir)]):
            mock_run_checkpoint.side_effect = KeyboardInterrupt()

            from review.main import main

            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit with 0 on keyboard interrupt (graceful)
            assert exc_info.value.code == 0


class TestReviewMainDocstring:
    """Tests for review.main documentation."""

    def test_module_docstring_exists(self):
        """Test that review.main has module documentation."""
        import review.main

        assert review.main.__doc__ is not None
        assert "backward-compatible" in review.main.__doc__.lower()

    def test_facade_documentation_mentions_split(self):
        """Test that facade documentation mentions module split."""
        import review.main

        doc = review.main.__doc__
        assert "review/state.py" in doc or "state" in doc.lower()


class TestReviewMainAsFacade:
    """Tests verifying review.main acts as proper facade."""

    def test_main_delegates_to_review_package(self):
        """Test that main() delegates to review package functions."""
        # This is a structural test - verify main() calls the right functions
        from review.main import main
        import inspect

        source = inspect.getsource(main)
        # Should call run_review_checkpoint
        assert "run_review_checkpoint" in source

    def test_facade_reexports_are_correct(self):
        """Test that facade re-exports match review package exports."""
        from review import ReviewState, display_review_status, run_review_checkpoint
        from review.main import ReviewState as MainReviewState

        # Should be the same class
        assert MainReviewState is ReviewState


class TestReviewMainEdgeCases:
    """Edge case tests for review.main."""

    @patch("review.main.run_review_checkpoint")
    @patch("review.main.ReviewState")
    @patch("review.main.print_status")
    def test_main_with_path_object_as_string(
        self, mock_print_status, mock_review_state, mock_run_checkpoint, tmp_path
    ):
        """Test main() handles string path for spec-dir."""
        spec_dir = str(tmp_path / "specs" / "001-test")
        Path(spec_dir).mkdir(parents=True)

        # Patch sys.argv with the actual spec_dir path
        with patch("sys.argv", ["review.py", "--spec-dir", spec_dir, "--auto-approve"]):
            mock_state = MagicMock()
            mock_state.is_approved.return_value = True
            mock_review_state.load.return_value = mock_state
            mock_run_checkpoint.return_value = mock_state

            from review.main import main

            with pytest.raises(SystemExit):
                main()

            # Verify ReviewState.load was called
            mock_review_state.load.assert_called()

    @patch("review.main.run_review_checkpoint")
    @patch("review.main.ReviewState")
    @patch("review.main.print_status")
    def test_main_status_displays_info(
        self, mock_print_status, mock_review_state, mock_run_checkpoint, tmp_path
    ):
        """Test main() --status displays review info."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        # Patch sys.argv with the actual spec_dir path
        with patch("sys.argv", ["review.py", "--spec-dir", str(spec_dir), "--status"]):
            mock_state = MagicMock()
            mock_state.is_approval_valid.return_value = True
            mock_review_state.load.return_value = mock_state

            from review.main import main

            with pytest.raises(SystemExit):
                main()

            # Verify review state was loaded
            mock_review_state.load.assert_called()
