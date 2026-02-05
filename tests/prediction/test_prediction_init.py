"""
Tests for prediction package __init__ module.
Tests the convenience function and public API.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from prediction import BugPredictor, generate_subtask_checklist
from prediction.models import PreImplementationChecklist, PredictedIssue


class TestPredictionInit:
    """Tests for prediction package initialization and convenience functions."""

    def test_module_exports(self):
        """Test that expected symbols are exported from prediction module."""
        import prediction

        # Check that expected exports exist
        assert hasattr(prediction, "BugPredictor")
        assert hasattr(prediction, "PredictedIssue")
        assert hasattr(prediction, "PreImplementationChecklist")
        assert hasattr(prediction, "generate_subtask_checklist")

    def test_all_list(self):
        """Test __all__ list contains expected exports."""
        import prediction

        expected_all = [
            "BugPredictor",
            "PredictedIssue",
            "PreImplementationChecklist",
            "generate_subtask_checklist",
        ]
        assert prediction.__all__ == expected_all

    def test_generate_subtask_checklist_convenience_function(self):
        """Test the convenience function for generating checklists."""
        spec_dir = Path("/tmp/test_spec")

        subtask = {
            "id": "test-001",
            "description": "Add user authentication",
            "patterns_from": ["apps/backend/auth.py"],
            "verification": {"type": "api", "method": "POST", "url": "/api/auth/login"},
        }

        # Mock the BugPredictor methods
        with patch.object(BugPredictor, "generate_checklist") as mock_generate, patch.object(
            BugPredictor, "format_checklist_markdown"
        ) as mock_format:

            expected_checklist = PreImplementationChecklist(
                subtask_id="test-001", subtask_description="Add user authentication"
            )
            mock_generate.return_value = expected_checklist
            mock_format.return_value = "# Markdown Checklist"

            result = generate_subtask_checklist(spec_dir, subtask)

            # Verify the convenience function works correctly
            assert result == "# Markdown Checklist"
            mock_generate.assert_called_once_with(subtask)
            mock_format.assert_called_once_with(expected_checklist)

    def test_generate_subtask_checklist_with_pathlib_path(self):
        """Test generate_subtask_checklist with pathlib.Path."""
        spec_dir = Path("/tmp/test_spec")
        subtask = {"id": "test-001", "description": "Test"}

        with patch.object(BugPredictor, "generate_checklist") as mock_generate, patch.object(
            BugPredictor, "format_checklist_markdown"
        ) as mock_format:

            mock_generate.return_value = PreImplementationChecklist(
                subtask_id="test-001", subtask_description="Test"
            )
            mock_format.return_value = "# Test"

            result = generate_subtask_checklist(spec_dir, subtask)

            assert result == "# Test"

    def test_generate_subtask_checklist_with_string_path(self):
        """Test generate_subtask_checklist with string path."""
        spec_dir = "/tmp/test_spec"
        subtask = {"id": "test-001", "description": "Test"}

        with patch.object(BugPredictor, "generate_checklist") as mock_generate, patch.object(
            BugPredictor, "format_checklist_markdown"
        ) as mock_format:

            mock_generate.return_value = PreImplementationChecklist(
                subtask_id="test-001", subtask_description="Test"
            )
            mock_format.return_value = "# Test"

            result = generate_subtask_checklist(spec_dir, subtask)

            assert result == "# Test"

    def test_generate_subtask_checklist_integration(self):
        """Test generate_subtask_checklist with real subtask structure."""
        spec_dir = Path("/tmp/test_spec")
        subtask = {
            "id": "auth-001",
            "description": "Implement OAuth authentication",
            "files_to_modify": ["apps/backend/auth.py"],
            "files_to_create": ["apps/backend/models/oauth_token.py"],
            "patterns_from": ["apps/backend/auth/session.py"],
            "service": "backend",
            "verification": {
                "type": "e2e",
                "steps": ["Open login page", "Click OAuth button", "Verify redirect"],
            },
        }

        with patch("prediction.memory_loader.MemoryLoader") as mock_loader, patch(
            "prediction.risk_analyzer.detect_work_type"
        ) as mock_detect:

            # Setup mocks
            mock_loader.return_value.load_attempt_history.return_value = []
            mock_loader.return_value.load_patterns.return_value = []
            mock_loader.return_value.load_gotchas.return_value = []
            mock_detect.return_value = ["authentication"]

            result = generate_subtask_checklist(spec_dir, subtask)

            # Should return markdown string
            assert isinstance(result, str)
            assert len(result) > 0
            # Should contain checklist header
            assert "Pre-Implementation Checklist" in result

    def test_generate_subtask_checklist_returns_markdown(self):
        """Test that the convenience function returns markdown formatted string."""
        spec_dir = Path("/tmp/test_spec")
        subtask = {"id": "test-001", "description": "Simple task"}

        with patch.object(BugPredictor, "generate_checklist") as mock_generate, patch.object(
            BugPredictor, "format_checklist_markdown"
        ) as mock_format:

            checklist = PreImplementationChecklist(
                subtask_id="test-001",
                subtask_description="Simple task",
                predicted_issues=[
                    PredictedIssue("security", "Test issue", "high", "Fix it")
                ],
            )
            mock_generate.return_value = checklist
            mock_format.return_value = "## Pre-Implementation Checklist: Simple task\n\n### Predicted Issues"

            result = generate_subtask_checklist(spec_dir, subtask)

            # Verify markdown formatting
            assert "##" in result
            assert "Pre-Implementation Checklist" in result

    def test_generate_subtask_checklist_with_complex_subtask(self):
        """Test with a subtask containing all possible fields."""
        spec_dir = Path("/tmp/test_spec")
        subtask = {
            "id": "full-001",
            "description": "Complete feature implementation",
            "files_to_modify": ["api/routes.py", "models/user.py"],
            "files_to_create": ["services/auth_service.py"],
            "patterns_from": ["api/base.py", "services/base_service.py"],
            "service": "backend",
            "verification": {
                "type": "api",
                "method": "POST",
                "url": "/api/auth/login",
                "expect_status": 200,
            },
        }

        with patch("prediction.memory_loader.MemoryLoader") as mock_loader, patch(
            "prediction.risk_analyzer.detect_work_type"
        ) as mock_detect:

            # Setup mocks
            mock_loader.return_value.load_attempt_history.return_value = [
                {
                    "subtask_id": "old-001",
                    "subtask_description": "Auth implementation",
                    "status": "failed",
                    "error_message": "Missing token validation",
                    "files_modified": ["api/routes.py"],
                }
            ]
            mock_loader.return_value.load_patterns.return_value = [
                "API: Use proper error handling",
                "Auth: Validate all tokens",
            ]
            mock_loader.return_value.load_gotchas.return_value = [
                "Don't forget to validate tokens",
                "Always check permissions",
            ]
            mock_detect.return_value = ["api_endpoint", "authentication"]

            result = generate_subtask_checklist(spec_dir, subtask)

            # Should include all sections
            assert "Pre-Implementation Checklist" in result
            assert "Complete feature implementation" in result

    def test_bug_predictor_import(self):
        """Test that BugPredictor can be imported from prediction package."""
        from prediction import BugPredictor as ImportedPredictor

        assert ImportedPredictor is BugPredictor

    def test_models_import(self):
        """Test that models can be imported from prediction package."""
        from prediction import PreImplementationChecklist as ImportedChecklist
        from prediction import PredictedIssue as ImportedIssue

        assert ImportedChecklist is PreImplementationChecklist
        assert ImportedIssue is PredictedIssue

    def test_convenience_function_docstring(self):
        """Test that convenience function has proper docstring."""
        assert generate_subtask_checklist.__doc__ is not None
        assert "Convenience function" in generate_subtask_checklist.__doc__
        assert "checklist" in generate_subtask_checklist.__doc__.lower()

    def test_generate_subtask_checklist_with_empty_subtask(self):
        """Test convenience function with minimal subtask."""
        spec_dir = Path("/tmp/test_spec")
        subtask = {}  # Empty subtask

        with patch("prediction.memory_loader.MemoryLoader") as mock_loader, patch(
            "prediction.risk_analyzer.detect_work_type"
        ) as mock_detect:

            # Setup mocks
            mock_loader.return_value.load_attempt_history.return_value = []
            mock_loader.return_value.load_patterns.return_value = []
            mock_loader.return_value.load_gotchas.return_value = []
            mock_detect.return_value = []

            # Should handle empty subtask gracefully
            result = generate_subtask_checklist(spec_dir, subtask)

            # Should still return markdown
            assert isinstance(result, str)
            assert "Pre-Implementation Checklist" in result


class TestPredictionInitEdgeCases:
    """Edge case tests for prediction package initialization."""

    def test_convenience_function_preserves_subtask_data(self):
        """Test that subtask data is preserved through the convenience function."""
        spec_dir = Path("/tmp/test_spec")
        subtask = {
            "id": "complex-001",
            "description": "Task with special chars: <>&\"'",
            "files_to_modify": ["path/to/file.py"],
            "verification": {"type": "manual", "instructions": "Check it works"},
        }

        with patch("prediction.memory_loader.MemoryLoader") as mock_loader, patch(
            "prediction.risk_analyzer.detect_work_type"
        ) as mock_detect:

            # Setup mocks
            mock_loader.return_value.load_attempt_history.return_value = []
            mock_loader.return_value.load_patterns.return_value = []
            mock_loader.return_value.load_gotchas.return_value = []
            mock_detect.return_value = []

            result = generate_subtask_checklist(spec_dir, subtask)

            # Special characters should be preserved
            assert "special chars" in result or "Task with" in result

    def test_convenience_function_with_unicode_subtask(self):
        """Test convenience function with unicode in subtask."""
        spec_dir = Path("/tmp/test_spec")
        subtask = {
            "id": "utf8-001",
            "description": "Tâsk with ûnïcödé and émojis 🎉",
            "files_to_modify": ["path/to/file.py"],
        }

        with patch("prediction.memory_loader.MemoryLoader") as mock_loader, patch(
            "prediction.risk_analyzer.detect_work_type"
        ) as mock_detect:

            # Setup mocks
            mock_loader.return_value.load_attempt_history.return_value = []
            mock_loader.return_value.load_patterns.return_value = []
            mock_loader.return_value.load_gotchas.return_value = []
            mock_detect.return_value = []

            result = generate_subtask_checklist(spec_dir, subtask)

            # Unicode should be preserved
            assert "ûnïcödé" in result or "Tâsk" in result

    def test_convenience_function_multiple_calls(self):
        """Test that convenience function can be called multiple times."""
        spec_dir = Path("/tmp/test_spec")

        with patch("prediction.memory_loader.MemoryLoader") as mock_loader, patch(
            "prediction.risk_analyzer.detect_work_type"
        ) as mock_detect:

            # Setup mocks
            mock_loader.return_value.load_attempt_history.return_value = []
            mock_loader.return_value.load_patterns.return_value = []
            mock_loader.return_value.load_gotchas.return_value = []
            mock_detect.return_value = []

            # Multiple calls should work independently
            result1 = generate_subtask_checklist(spec_dir, {"id": "1", "description": "Task 1"})
            result2 = generate_subtask_checklist(spec_dir, {"id": "2", "description": "Task 2"})

            assert isinstance(result1, str)
            assert isinstance(result2, str)
            assert result1 != result2  # Different tasks should produce different output
