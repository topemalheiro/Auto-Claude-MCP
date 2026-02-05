"""Tests for validator module (spec/validator.py)"""

import json
from pathlib import Path

import pytest

from spec.validator import (
    create_empty_hints,
    create_minimal_critique,
    create_minimal_research,
)


class TestCreateMinimalResearch:
    """Tests for create_minimal_research function"""

    def test_creates_research_json(self, tmp_path):
        """Test creates minimal research.json file"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_research(spec_dir, "No research needed")

        assert result == spec_dir / "research.json"
        assert result.exists()

        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert data["research_skipped"] is True
        assert data["reason"] == "No research needed"
        assert data["integrations_researched"] == []

    def test_default_reason(self, tmp_path):
        """Test default reason when not provided"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_research(spec_dir)

        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert data["reason"] == "No research needed"

    def test_custom_reason(self, tmp_path):
        """Test custom reason"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_research(
            spec_dir, "No external integrations required"
        )

        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert data["reason"] == "No external integrations required"

    def test_includes_timestamp(self, tmp_path):
        """Test includes created_at timestamp"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_research(spec_dir)

        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert "created_at" in data

    def test_overwrites_existing_file(self, tmp_path):
        """Test overwrites existing research.json"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        existing = spec_dir / "research.json"
        existing.write_text('{"old": "data"}', encoding="utf-8")

        create_minimal_research(spec_dir, "New reason")

        with open(existing, encoding="utf-8") as f:
            data = json.load(f)

        assert "research_skipped" in data
        assert "old" not in data


class TestCreateMinimalCritique:
    """Tests for create_minimal_critique function"""

    def test_creates_critique_json(self, tmp_path):
        """Test creates minimal critique_report.json file"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_critique(spec_dir, "Critique not required")

        assert result == spec_dir / "critique_report.json"
        assert result.exists()

        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert data["no_issues_found"] is True
        assert data["critique_summary"] == "Critique not required"
        assert data["issues_found"] == []

    def test_default_reason(self, tmp_path):
        """Test default reason when not provided"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_critique(spec_dir)

        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert data["critique_summary"] == "Critique not required"

    def test_custom_summary(self, tmp_path):
        """Test custom critique summary"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_critique(spec_dir, "Spec looks good, no issues")

        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert data["critique_summary"] == "Spec looks good, no issues"

    def test_includes_timestamp(self, tmp_path):
        """Test includes created_at timestamp"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_critique(spec_dir)

        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert "created_at" in data

    def test_overwrites_existing_file(self, tmp_path):
        """Test overwrites existing critique_report.json"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        existing = spec_dir / "critique_report.json"
        existing.write_text('{"old": "data"}', encoding="utf-8")

        create_minimal_critique(spec_dir, "New summary")

        with open(existing, encoding="utf-8") as f:
            data = json.load(f)

        assert "no_issues_found" in data
        assert "old" not in data


class TestCreateEmptyHints:
    """Tests for create_empty_hints function"""

    def test_creates_graph_hints_json(self, tmp_path):
        """Test creates graph_hints.json file"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_empty_hints(spec_dir, enabled=False, reason="Graphiti disabled")

        assert result == spec_dir / "graph_hints.json"
        assert result.exists()

        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert data["enabled"] is False
        assert data["reason"] == "Graphiti disabled"
        assert data["hints"] == []

    def test_enabled_true(self, tmp_path):
        """Test creating hints with enabled=True"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_empty_hints(spec_dir, enabled=True, reason="For testing")

        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert data["enabled"] is True
        assert data["reason"] == "For testing"

    def test_includes_timestamp(self, tmp_path):
        """Test includes created_at timestamp"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_empty_hints(spec_dir, enabled=False, reason="test")

        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert "created_at" in data

    def test_overwrites_existing_file(self, tmp_path):
        """Test overwrites existing graph_hints.json"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        existing = spec_dir / "graph_hints.json"
        existing.write_text('{"old": "data"}', encoding="utf-8")

        create_empty_hints(spec_dir, enabled=False, reason="New reason")

        with open(existing, encoding="utf-8") as f:
            data = json.load(f)

        assert "enabled" in data
        assert "old" not in data

    def test_empty_hints_array(self, tmp_path):
        """Test hints array is empty"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_empty_hints(spec_dir, enabled=True, reason="test")

        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert data["hints"] == []


class TestCreateMinimalResearchAdditional:
    """Additional tests for create_minimal_research edge cases"""

    def test_creates_directory_if_needed(self, tmp_path):
        """Test that spec_dir must exist"""
        spec_dir = tmp_path / "new_dir" / "spec"
        # Don't create it - function will fail

        # The function expects directory to exist
        with pytest.raises(FileNotFoundError):
            create_minimal_research(spec_dir, "test")

    def test_reason_with_special_characters(self, tmp_path):
        """Test reason with special characters"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_research(spec_dir, "No research needed: @#$%^&*()")

        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert "@" in data["reason"]

    def test_reason_with_newlines(self, tmp_path):
        """Test reason with newlines is preserved"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_research(
            spec_dir, "Line 1\nLine 2\nLine 3"
        )

        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert "\n" in data["reason"]

    def test_json_indentation(self, tmp_path):
        """Test JSON output is properly indented"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_minimal_research(spec_dir, "test")

        content = (spec_dir / "research.json").read_text(encoding="utf-8")

        # Check formatting
        assert "\n" in content
        assert "  " in content

    def test_utf8_encoding(self, tmp_path):
        """Test UTF-8 encoding for emojis and unicode"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_research(spec_dir, "Test emoji: 🎉 and unicode: ñ")

        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert "🎉" in data["reason"]
        assert "ñ" in data["reason"]


class TestCreateMinimalCritiqueAdditional:
    """Additional tests for create_minimal_critique edge cases"""

    def test_creates_directory_if_needed(self, tmp_path):
        """Test that spec_dir must exist"""
        spec_dir = tmp_path / "new_dir" / "spec"
        # Don't create it - function will fail

        # The function expects directory to exist
        with pytest.raises(FileNotFoundError):
            create_minimal_critique(spec_dir, "test")

    def test_summary_with_special_characters(self, tmp_path):
        """Test summary with special characters"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_critique(spec_dir, "Summary: @#$%^&*()")

        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert "@" in data["critique_summary"]

    def test_json_indentation(self, tmp_path):
        """Test JSON output is properly indented"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_minimal_critique(spec_dir, "test")

        content = (spec_dir / "critique_report.json").read_text(encoding="utf-8")

        # Check formatting
        assert "\n" in content
        assert "  " in content

    def test_utf8_encoding(self, tmp_path):
        """Test UTF-8 encoding for emojis and unicode"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_minimal_critique(spec_dir, "Test emoji: 🎉 and unicode: ñ")

        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert "🎉" in data["critique_summary"]
        assert "ñ" in data["critique_summary"]

    def test_issues_found_always_empty(self, tmp_path):
        """Test issues_found is always empty array for minimal critique"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_minimal_critique(spec_dir, "Any reason")

        with open(spec_dir / "critique_report.json", encoding="utf-8") as f:
            data = json.load(f)

        assert data["issues_found"] == []
        assert data["no_issues_found"] is True


class TestCreateEmptyHintsAdditional:
    """Additional tests for create_empty_hints edge cases"""

    def test_creates_directory_if_needed(self, tmp_path):
        """Test that spec_dir must exist"""
        spec_dir = tmp_path / "new_dir" / "spec"
        # Don't create it - function will fail

        # The function expects directory to exist
        with pytest.raises(FileNotFoundError):
            create_empty_hints(spec_dir, enabled=False, reason="test")

    def test_reason_with_special_characters(self, tmp_path):
        """Test reason with special characters"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_empty_hints(spec_dir, enabled=False, reason="Reason: @#$%")

        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert "@" in data["reason"]

    def test_json_indentation(self, tmp_path):
        """Test JSON output is properly indented"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_empty_hints(spec_dir, enabled=True, reason="test")

        content = (spec_dir / "graph_hints.json").read_text(encoding="utf-8")

        # Check formatting
        assert "\n" in content
        assert "  " in content

    def test_utf8_encoding(self, tmp_path):
        """Test UTF-8 encoding for emojis and unicode"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = create_empty_hints(spec_dir, enabled=False, reason="Test: 🎉 ñ")

        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert "🎉" in data["reason"]
        assert "ñ" in data["reason"]

    def test_hints_field_is_list(self, tmp_path):
        """Test hints field is always a list"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        create_empty_hints(spec_dir, enabled=True, reason="test")

        with open(spec_dir / "graph_hints.json", encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data["hints"], list)
        assert len(data["hints"]) == 0
