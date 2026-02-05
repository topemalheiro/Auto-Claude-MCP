"""Tests for prediction.models module."""

import pytest

from prediction.models import PredictedIssue, PreImplementationChecklist


class TestPredictedIssue:
    """Tests for PredictedIssue dataclass."""

    def test_create_predicted_issue_with_all_fields(self):
        """Test creating PredictedIssue with all fields."""
        issue = PredictedIssue(
            category="security",
            description="SQL injection vulnerability",
            likelihood="high",
            prevention="Use parameterized queries",
        )
        assert issue.category == "security"
        assert issue.description == "SQL injection vulnerability"
        assert issue.likelihood == "high"
        assert issue.prevention == "Use parameterized queries"

    def test_to_dict_method(self):
        """Test to_dict method converts PredictedIssue to dictionary."""
        issue = PredictedIssue(
            category="integration",
            description="CORS not configured",
            likelihood="medium",
            prevention="Add CORS middleware",
        )
        result = issue.to_dict()
        assert result == {
            "category": "integration",
            "description": "CORS not configured",
            "likelihood": "medium",
            "prevention": "Add CORS middleware",
        }

    def test_valid_categories(self):
        """Test creating issues with valid categories."""
        categories = [
            "integration",
            "pattern",
            "edge_case",
            "security",
            "performance",
        ]
        for category in categories:
            issue = PredictedIssue(
                category=category,
                description="Test",
                likelihood="high",
                prevention="Test",
            )
            assert issue.category == category

    def test_valid_likelihoods(self):
        """Test creating issues with valid likelihood levels."""
        likelihoods = ["high", "medium", "low"]
        for likelihood in likelihoods:
            issue = PredictedIssue(
                category="test",
                description="Test",
                likelihood=likelihood,
                prevention="Test",
            )
            assert issue.likelihood == likelihood

    def test_predicted_issue_with_special_characters(self):
        """Test PredictedIssue with special characters in text."""
        issue = PredictedIssue(
            category="security",
            description="Use 'quotes' and \"double quotes\"",
            likelihood="high",
            prevention="Escape: \\n \\t \\r",
        )
        assert "quotes" in issue.description
        assert "Escape:" in issue.prevention

    def test_predicted_issue_with_unicode(self):
        """Test PredictedIssue with unicode characters."""
        issue = PredictedIssue(
            category="pattern",
            description="Use café not coffee",
            likelihood="medium",
            prevention="Add émojis 🎉",
        )
        assert "café" in issue.description
        assert "émojis 🎉" in issue.prevention


class TestPreImplementationChecklist:
    """Tests for PreImplementationChecklist dataclass."""

    def test_create_checklist_with_required_fields(self):
        """Test creating checklist with only required fields."""
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Add authentication",
        )
        assert checklist.subtask_id == "001"
        assert checklist.subtask_description == "Add authentication"
        assert checklist.predicted_issues == []
        assert checklist.patterns_to_follow == []
        assert checklist.files_to_reference == []
        assert checklist.common_mistakes == []
        assert checklist.verification_reminders == []

    def test_create_checklist_with_all_fields(self):
        """Test creating checklist with all fields populated."""
        checklist = PreImplementationChecklist(
            subtask_id="002",
            subtask_description="Create API endpoint",
            predicted_issues=[
                PredictedIssue(
                    category="security",
                    description="No auth",
                    likelihood="high",
                    prevention="Add decorator",
                )
            ],
            patterns_to_follow=["Use Flask blueprints"],
            files_to_reference=["api/users.py", "models/user.py"],
            common_mistakes=["Don't forget validation"],
            verification_reminders=["Test with invalid input"],
        )
        assert checklist.subtask_id == "002"
        assert checklist.subtask_description == "Create API endpoint"
        assert len(checklist.predicted_issues) == 1
        assert checklist.predicted_issues[0].category == "security"
        assert len(checklist.patterns_to_follow) == 1
        assert len(checklist.files_to_reference) == 2
        assert len(checklist.common_mistakes) == 1
        assert len(checklist.verification_reminders) == 1

    def test_checklist_with_multiple_predicted_issues(self):
        """Test checklist with multiple predicted issues."""
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Test",
            predicted_issues=[
                PredictedIssue("security", "Issue 1", "high", "Prevention 1"),
                PredictedIssue("pattern", "Issue 2", "medium", "Prevention 2"),
                PredictedIssue("edge_case", "Issue 3", "low", "Prevention 3"),
            ],
        )
        assert len(checklist.predicted_issues) == 3
        assert checklist.predicted_issues[0].likelihood == "high"
        assert checklist.predicted_issues[1].likelihood == "medium"
        assert checklist.predicted_issues[2].likelihood == "low"

    def test_checklist_with_multiple_patterns(self):
        """Test checklist with multiple patterns to follow."""
        patterns = [
            "Use dependency injection",
            "Follow naming conventions",
            "Add type hints",
            "Write docstrings",
        ]
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Test",
            patterns_to_follow=patterns,
        )
        assert len(checklist.patterns_to_follow) == 4
        assert checklist.patterns_to_follow[0] == "Use dependency injection"
        assert checklist.patterns_to_follow[3] == "Write docstrings"

    def test_checklist_with_multiple_files(self):
        """Test checklist with multiple files to reference."""
        files = [
            "models/user.py",
            "services/auth.py",
            "utils/validation.py",
            "tests/test_auth.py",
        ]
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Test",
            files_to_reference=files,
        )
        assert len(checklist.files_to_reference) == 4
        assert checklist.files_to_reference[0] == "models/user.py"

    def test_checklist_with_multiple_gotchas(self):
        """Test checklist with multiple common mistakes."""
        mistakes = [
            "Don't store passwords in plain text",
            "Remember to validate tokens",
            "Handle edge cases",
        ]
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Test",
            common_mistakes=mistakes,
        )
        assert len(checklist.common_mistakes) == 3
        assert "passwords" in checklist.common_mistakes[0]

    def test_checklist_with_multiple_reminders(self):
        """Test checklist with multiple verification reminders."""
        reminders = [
            "Test authentication flow",
            "Verify token expiration",
            "Check permission handling",
            "Test with invalid credentials",
        ]
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Test",
            verification_reminders=reminders,
        )
        assert len(checklist.verification_reminders) == 4
        assert "authentication flow" in checklist.verification_reminders[0]

    def test_checklist_field_mutability(self):
        """Test that checklist fields can be modified."""
        checklist = PreImplementationChecklist(
            subtask_id="001", subtask_description="Test"
        )
        checklist.subtask_description = "Updated description"
        assert checklist.subtask_description == "Updated description"

        checklist.patterns_to_follow.append("New pattern")
        assert len(checklist.patterns_to_follow) == 1

    def test_checklist_with_unicode_subtask_description(self):
        """Test checklist with unicode characters in subtask description."""
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Créate API with spëcial çharacters 🎉",
        )
        assert "Créate" in checklist.subtask_description
        assert "🎉" in checklist.subtask_description

    def test_checklist_with_empty_strings(self):
        """Test checklist with empty strings in list fields."""
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Test",
            patterns_to_follow=[""],
            common_mistakes=["", ""],
        )
        assert len(checklist.patterns_to_follow) == 1
        assert checklist.patterns_to_follow[0] == ""
        assert len(checklist.common_mistakes) == 2

    def test_checklist_immutability_of_predicted_issues(self):
        """Test that predicted issues list can be modified."""
        issue = PredictedIssue("test", "desc", "high", "prev")
        checklist = PreImplementationChecklist(
            subtask_id="001", subtask_description="Test", predicted_issues=[issue]
        )
        checklist.predicted_issues.append(
            PredictedIssue("test2", "desc2", "low", "prev2")
        )
        assert len(checklist.predicted_issues) == 2


class TestModelIntegration:
    """Integration tests for prediction models."""

    def test_complete_checklist_with_all_data_types(self):
        """Test a complete checklist with various data types."""
        checklist = PreImplementationChecklist(
            subtask_id="123",
            subtask_description="Complex task with special chars: @#$%",
            predicted_issues=[
                PredictedIssue(
                    "security",
                    "Issue with 'quotes' and \"double quotes\"",
                    "high",
                    "Prevention with\nnewlines and\ttabs",
                )
            ],
            patterns_to_follow=[
                "Pattern 1 with café",
                "Pattern 2 with emoji 🚀",
                "Pattern 3 with <html> tags",
            ],
            files_to_reference=[
                "path/to/file.py",
                "another/path/file.ts",
                "../relative/path.js",
            ],
            common_mistakes=[
                "Mistake 1: Don't do X",
                "Mistake 2: Always do Y",
            ],
            verification_reminders=[
                "Verify: Check 1",
                "Verify: Check 2",
                "Verify: Check 3",
            ],
        )
        assert checklist.subtask_id == "123"
        assert "@" in checklist.subtask_description
        assert len(checklist.predicted_issues) == 1
        assert "quotes" in checklist.predicted_issues[0].description
        assert len(checklist.patterns_to_follow) == 3
        assert "café" in checklist.patterns_to_follow[0]
        assert len(checklist.files_to_reference) == 3
        assert len(checklist.common_mistakes) == 2
        assert len(checklist.verification_reminders) == 3

    def test_predictor_issue_to_dict_integration(self):
        """Test converting issues to dict within checklist context."""
        checklist = PreImplementationChecklist(
            subtask_id="001",
            subtask_description="Test",
            predicted_issues=[
                PredictedIssue("cat1", "desc1", "high", "prev1"),
                PredictedIssue("cat2", "desc2", "low", "prev2"),
            ],
        )
        issue_dicts = [issue.to_dict() for issue in checklist.predicted_issues]
        assert len(issue_dicts) == 2
        assert issue_dicts[0]["category"] == "cat1"
        assert issue_dicts[1]["likelihood"] == "low"
