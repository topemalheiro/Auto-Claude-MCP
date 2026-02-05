"""Tests for prediction.formatter module."""

import pytest

from prediction.formatter import ChecklistFormatter
from prediction.models import PreImplementationChecklist, PredictedIssue


class TestChecklistFormatter:
    """Tests for ChecklistFormatter class."""

    def test_format_markdown_with_all_sections(self):
        """Test formatting checklist with all sections populated."""
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Add user authentication",
            predicted_issues=[
                PredictedIssue(
                    category="security",
                    description="Password not hashed",
                    likelihood="high",
                    prevention="Use bcrypt",
                ),
                PredictedIssue(
                    category="pattern",
                    description="Missing validation",
                    likelihood="medium",
                    prevention="Add input validation",
                ),
            ],
            patterns_to_follow=["Use Flask-Login", "Add decorators"],
            files_to_reference=["auth/utils.py", "models/user.py"],
            common_mistakes=["Don't store passwords", "Validate tokens"],
            verification_reminders=["Test login flow", "Check token expiry"],
        )

        result = ChecklistFormatter.format_markdown(checklist)

        assert "## Pre-Implementation Checklist: Add user authentication" in result
        assert "### Predicted Issues (based on similar work)" in result
        assert "Password not hashed" in result
        assert "Use bcrypt" in result
        assert "Missing validation" in result
        assert "Add input validation" in result
        assert "### Patterns to Follow" in result
        assert "- Use Flask-Login" in result
        assert "- Add decorators" in result
        assert "### Known Gotchas in This Codebase" in result
        assert "- [ ] Don't store passwords" in result
        assert "- [ ] Validate tokens" in result
        assert "### Files to Reference" in result
        assert "`auth/utils.py`" in result
        assert "`models/user.py`" in result
        assert "### Verification Reminders" in result
        assert "- [ ] Test login flow" in result
        assert "- [ ] Check token expiry" in result
        assert "### Before You Start Implementing" in result

    def test_format_markdown_minimal(self):
        """Test formatting checklist with only required fields."""
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Minimal task",
        )

        result = ChecklistFormatter.format_markdown(checklist)

        assert "## Pre-Implementation Checklist: Minimal task" in result
        assert "### Before You Start Implementing" in result
        assert "- [ ] I have read and understood all predicted issues above" in result
        assert "- [ ] I have reviewed the reference files" in result
        assert "- [ ] I know how to prevent the high-likelihood issues" in result
        assert "- [ ] I understand the verification requirements" in result

    def test_format_predicted_issues_table(self):
        """Test predicted issues table formatting."""
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Test",
            predicted_issues=[
                PredictedIssue(
                    category="security",
                    description="SQL injection",
                    likelihood="high",
                    prevention="Use parameterized queries",
                ),
            ],
        )

        result = ChecklistFormatter.format_markdown(checklist)

        assert "| Issue | Likelihood | Prevention |" in result
        assert "|-------|------------|------------|" in result
        assert "| SQL injection | High | Use parameterized queries |" in result

    def test_format_predicted_issues_with_pipe_escaping(self):
        """Test that pipe characters in content are escaped."""
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Test",
            predicted_issues=[
                PredictedIssue(
                    category="pattern",
                    description="Use | delimiter",
                    likelihood="medium",
                    prevention="Escape | pipes in content",
                ),
            ],
        )

        result = ChecklistFormatter.format_markdown(checklist)

        # Pipe should be escaped with backslash
        assert r"\|" in result

    def test_format_patterns_section(self):
        """Test patterns section formatting."""
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Test",
            patterns_to_follow=["Pattern 1", "Pattern 2", "Pattern 3"],
        )

        result = ChecklistFormatter.format_markdown(checklist)

        assert "### Patterns to Follow" in result
        assert "From previous sessions and codebase analysis:" in result
        assert "- Pattern 1" in result
        assert "- Pattern 2" in result
        assert "- Pattern 3" in result

    def test_format_gotchas_section(self):
        """Test gotchas section formatting."""
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Test",
            common_mistakes=["Gotcha 1", "Gotcha 2"],
        )

        result = ChecklistFormatter.format_markdown(checklist)

        assert "### Known Gotchas in This Codebase" in result
        assert "From memory/gotchas.md:" in result
        assert "- [ ] Gotcha 1" in result
        assert "- [ ] Gotcha 2" in result

    def test_format_files_to_reference_section(self):
        """Test files to reference section formatting."""
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Test",
            files_to_reference=["path/to/file1.py", "path/to/file2.ts"],
        )

        result = ChecklistFormatter.format_markdown(checklist)

        assert "### Files to Reference" in result
        assert "- `path/to/file1.py` - Check for similar patterns and code style" in result
        assert "- `path/to/file2.ts` - Check for similar patterns and code style" in result

    def test_format_verification_reminders_section(self):
        """Test verification reminders section formatting."""
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Test",
            verification_reminders=["Reminder 1", "Reminder 2", "Reminder 3"],
        )

        result = ChecklistFormatter.format_markdown(checklist)

        assert "### Verification Reminders" in result
        assert "- [ ] Reminder 1" in result
        assert "- [ ] Reminder 2" in result
        assert "- [ ] Reminder 3" in result

    def test_format_pre_start_checklist(self):
        """Test pre-start checklist formatting."""
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Test",
        )

        result = ChecklistFormatter.format_markdown(checklist)

        assert "### Before You Start Implementing" in result
        assert "- [ ] I have read and understood all predicted issues above" in result
        assert (
            "- [ ] I have reviewed the reference files to understand existing patterns"
            in result
        )
        assert "- [ ] I know how to prevent the high-likelihood issues" in result
        assert "- [ ] I understand the verification requirements" in result

    def test_format_markdown_order(self):
        """Test that sections appear in correct order."""
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Test",
            predicted_issues=[PredictedIssue("test", "desc", "high", "prev")],
            patterns_to_follow=["pattern"],
            common_mistakes=["gotcha"],
            files_to_reference=["file.py"],
            verification_reminders=["reminder"],
        )

        result = ChecklistFormatter.format_markdown(checklist)
        lines = result.split("\n")

        # Find section headers
        headers = [line for line in lines if line.startswith("### ")]

        assert headers[0] == "### Predicted Issues (based on similar work)"
        assert headers[1] == "### Patterns to Follow"
        assert headers[2] == "### Known Gotchas in This Codebase"
        assert headers[3] == "### Files to Reference"
        assert headers[4] == "### Verification Reminders"
        assert headers[5] == "### Before You Start Implementing"

    def test_format_markdown_with_unicode(self):
        """Test formatting with unicode characters."""
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Tâsk with ûnïcödé",
            patterns_to_follow=["Pattern with émojis 🎉"],
            common_mistakes=["Don't use café"],
        )

        result = ChecklistFormatter.format_markdown(checklist)

        assert "Tâsk with ûnïcödé" in result
        assert "Pattern with émojis 🎉" in result
        assert "Don't use café" in result

    def test_format_markdown_with_empty_sections(self):
        """Test formatting with some empty sections."""
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Test",
            predicted_issues=[
                PredictedIssue("test", "desc", "high", "prev")
            ],
            patterns_to_follow=[],
            common_mistakes=[],
            files_to_reference=[],
            verification_reminders=[],
        )

        result = ChecklistFormatter.format_markdown(checklist)

        # Only populated sections should appear
        assert "### Predicted Issues (based on similar work)" in result
        assert "### Before You Start Implementing" in result
        # Empty sections should not appear
        assert "### Patterns to Follow" not in result
        assert "### Known Gotchas in This Codebase" not in result
        assert "### Files to Reference" not in result
        assert "### Verification Reminders" not in result

    def test_format_markdown_with_newlines_in_descriptions(self):
        """Test handling of newlines in issue descriptions."""
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Test",
            predicted_issues=[
                PredictedIssue(
                    "test",
                    "Line 1\nLine 2",
                    "high",
                    "Prevention\nwith\nnewlines",
                ),
            ],
        )

        result = ChecklistFormatter.format_markdown(checklist)

        # Should preserve content (table cells handle newlines)
        assert "Line 1" in result
        assert "Prevention" in result

    def test_checklist_formatter_static_methods(self):
        """Test that all format methods are static."""
        # Can't test @staticmethod directly, but can verify they work
        # without instantiation
        checklist = PreImplementationChecklist(
            subtask_id="001", subtask_description="Test"
        )

        # This should work without issues
        result = ChecklistFormatter.format_markdown(checklist)
        assert isinstance(result, str)
