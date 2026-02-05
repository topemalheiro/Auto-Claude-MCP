"""
Tests for core.plan_normalization module
=========================================

Comprehensive tests for implementation plan normalization utilities including:
- Subtask alias normalization (subtask_id -> id)
- Description alias normalization (title -> description)
- Empty/missing field handling
- Change detection for normalization
"""

import pytest

from core.plan_normalization import normalize_subtask_aliases


# ============================================================================
# normalize_subtask_aliases tests
# ============================================================================


class TestNormalizeSubtaskAliases:
    """Tests for normalize_subtask_aliases function."""

    # ------------------------------------------------------------------------
    # ID normalization tests
    # ------------------------------------------------------------------------

    def test_normalize_id_with_subtask_id_string(self):
        """Test normalization copies subtask_id string to id when id is missing."""
        subtask = {"subtask_id": "1.1", "description": "Task 1.1"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result["id"] == "1.1"
        assert result["subtask_id"] == "1.1"  # Original preserved
        assert changed is True

    def test_normalize_id_with_subtask_id_int(self):
        """Test normalization converts subtask_id int to id string."""
        subtask = {"subtask_id": 11, "description": "Task 11"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result["id"] == "11"
        assert changed is True

    def test_normalize_id_with_subtask_id_float(self):
        """Test normalization converts subtask_id float to id string."""
        subtask = {"subtask_id": 1.5, "description": "Task 1.5"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result["id"] == "1.5"
        assert changed is True

    def test_normalize_id_skips_when_id_present(self):
        """Test normalization skips id when already present."""
        subtask = {"id": "1.1", "subtask_id": "1.1", "description": "Task"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result["id"] == "1.1"
        assert changed is False

    def test_normalize_id_skips_when_id_present_different(self):
        """Test normalization doesn't override existing id even if different."""
        subtask = {"id": "1.1", "subtask_id": "2.2", "description": "Task"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result["id"] == "1.1"  # Original id preserved
        assert changed is False

    def test_normalize_id_skips_when_id_empty_string(self):
        """Test normalization copies subtask_id when id is empty string."""
        subtask = {"id": "", "subtask_id": "1.1", "description": "Task"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result["id"] == "1.1"
        assert changed is True

    def test_normalize_id_skips_when_id_whitespace_only(self):
        """Test normalization copies subtask_id when id is whitespace only."""
        subtask = {"id": "   ", "subtask_id": "1.1", "description": "Task"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result["id"] == "1.1"
        assert changed is True

    def test_normalize_id_skips_when_subtask_id_none(self):
        """Test normalization skips when subtask_id is None."""
        subtask = {"id": None, "subtask_id": None, "description": "Task"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result.get("id") is None
        assert changed is False

    def test_normalize_id_skips_when_subtask_id_empty_string(self):
        """Test normalization skips when subtask_id is empty string."""
        subtask = {"id": None, "subtask_id": "", "description": "Task"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result.get("id") is None
        assert changed is False

    def test_normalize_id_skips_when_subtask_id_whitespace(self):
        """Test normalization skips when subtask_id is whitespace."""
        subtask = {"id": None, "subtask_id": "   ", "description": "Task"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result.get("id") is None
        assert changed is False

    def test_normalize_id_trims_subtask_id_whitespace(self):
        """Test normalization trims whitespace from subtask_id."""
        subtask = {"subtask_id": "  1.1  ", "description": "Task"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result["id"] == "1.1"
        assert changed is True

    # ------------------------------------------------------------------------
    # Description normalization tests
    # ------------------------------------------------------------------------

    def test_normalize_description_with_title_string(self):
        """Test normalization copies title to description when description is missing."""
        subtask = {"id": "1.1", "title": "Build feature"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result["description"] == "Build feature"
        assert result["title"] == "Build feature"  # Original preserved
        assert changed is True

    def test_normalize_description_skips_when_description_present(self):
        """Test normalization skips description when already present."""
        subtask = {"id": "1.1", "description": "Task details", "title": "Title"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result["description"] == "Task details"
        assert changed is False

    def test_normalize_description_overrides_empty_description(self):
        """Test normalization copies title when description is empty string."""
        subtask = {"id": "1.1", "description": "", "title": "Title"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result["description"] == "Title"
        assert changed is True

    def test_normalize_description_overrides_whitespace_description(self):
        """Test normalization copies title when description is whitespace."""
        subtask = {"id": "1.1", "description": "   ", "title": "Title"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result["description"] == "Title"
        assert changed is True

    def test_normalize_description_skips_when_description_none(self):
        """Test normalization copies title when description is None."""
        subtask = {"id": "1.1", "description": None, "title": "Title"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result["description"] == "Title"
        assert changed is True

    def test_normalize_description_trims_title_whitespace(self):
        """Test normalization trims whitespace from title."""
        subtask = {"id": "1.1", "description": None, "title": "  Title  "}
        result, changed = normalize_subtask_aliases(subtask)

        assert result["description"] == "Title"
        assert changed is True

    def test_normalize_description_skips_when_title_none(self):
        """Test normalization skips when title is None."""
        subtask = {"id": "1.1", "description": None, "title": None}
        result, changed = normalize_subtask_aliases(subtask)

        assert result.get("description") is None
        assert changed is False

    def test_normalize_description_skips_when_title_empty_string(self):
        """Test normalization skips when title is empty string."""
        subtask = {"id": "1.1", "description": None, "title": ""}
        result, changed = normalize_subtask_aliases(subtask)

        assert result.get("description") is None
        assert changed is False

    def test_normalize_description_skips_when_title_whitespace(self):
        """Test normalization skips when title is whitespace only."""
        subtask = {"id": "1.1", "description": None, "title": "   "}
        result, changed = normalize_subtask_aliases(subtask)

        assert result.get("description") is None
        assert changed is False

    def test_normalize_description_skips_when_title_not_string(self):
        """Test normalization skips when title is not a string."""
        subtask = {"id": "1.1", "description": None, "title": 123}
        result, changed = normalize_subtask_aliases(subtask)

        assert result.get("description") is None
        assert changed is False

    # ------------------------------------------------------------------------
    # Combined normalization tests
    # ------------------------------------------------------------------------

    def test_normalize_both_id_and_description(self):
        """Test normalization of both id and description in one call."""
        subtask = {"subtask_id": "1.1", "title": "Build feature"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result["id"] == "1.1"
        assert result["description"] == "Build feature"
        assert changed is True

    def test_normalize_neither_needed(self):
        """Test normalization when nothing needs to change."""
        subtask = {"id": "1.1", "description": "Task"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result == subtask
        assert changed is False

    def test_normalize_preserves_other_fields(self):
        """Test normalization preserves all other fields."""
        subtask = {
            "subtask_id": "1.1",
            "title": "Task",
            "status": "pending",
            "phase": 1,
            "dependencies": ["1.0"],
        }
        result, changed = normalize_subtask_aliases(subtask)

        assert result["status"] == "pending"
        assert result["phase"] == 1
        assert result["dependencies"] == ["1.0"]
        assert changed is True

    def test_normalize_with_empty_subtask(self):
        """Test normalization with empty subtask dict."""
        subtask = {}
        result, changed = normalize_subtask_aliases(subtask)

        assert result == {}
        assert changed is False

    def test_normalize_does_not_mutate_original(self):
        """Test normalization does not modify the original dict."""
        subtask = {"subtask_id": "1.1", "title": "Task"}
        original_subtask_id = subtask["subtask_id"]
        original_has_id = "id" in subtask

        result, changed = normalize_subtask_aliases(subtask)

        # Original should be unchanged
        assert "id" not in subtask or subtask.get("id") is None
        assert subtask["subtask_id"] == original_subtask_id
        # Result should have id
        assert result["id"] == "1.1"

    # ------------------------------------------------------------------------
    # Edge case tests
    # ------------------------------------------------------------------------

    def test_normalize_id_with_leading_zeros(self):
        """Test normalization preserves leading zeros in subtask_id."""
        subtask = {"subtask_id": "01.01", "description": "Task"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result["id"] == "01.01"
        assert changed is True

    def test_normalize_id_with_special_characters(self):
        """Test normalization handles special characters in subtask_id."""
        subtask = {"subtask_id": "task-1_alpha", "description": "Task"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result["id"] == "task-1_alpha"
        assert changed is True

    def test_normalize_description_with_multiline_title(self):
        """Test normalization handles multiline title."""
        subtask = {"id": "1.1", "description": None, "title": "Line 1\nLine 2"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result["description"] == "Line 1\nLine 2"
        assert changed is True

    def test_normalize_description_with_unicode_title(self):
        """Test normalization handles Unicode in title."""
        subtask = {"id": "1.1", "description": None, "title": "Build 世界 🌍"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result["description"] == "Build 世界 🌍"
        assert changed is True

    def test_normalize_with_zero_id(self):
        """Test normalization handles '0' as valid subtask_id."""
        subtask = {"subtask_id": "0", "description": "Task zero"}
        result, changed = normalize_subtask_aliases(subtask)

        assert result["id"] == "0"
        assert changed is True

    def test_normalize_with_falsey_but_valid_values(self):
        """Test normalization distinguishes between falsey and invalid."""
        # Empty string is invalid
        subtask1 = {"subtask_id": "", "description": "Task"}
        result1, changed1 = normalize_subtask_aliases(subtask1)
        assert "id" not in result1 or result1["id"] == ""
        assert changed1 is False

        # "0" is valid
        subtask2 = {"subtask_id": "0", "description": "Task"}
        result2, changed2 = normalize_subtask_aliases(subtask2)
        assert result2["id"] == "0"
        assert changed2 is True

    # ------------------------------------------------------------------------
    # Real-world scenario tests
    # ------------------------------------------------------------------------

    def test_normalize_legacy_subtask_format(self):
        """Test normalization of legacy subtask format."""
        # Old format used subtask_id and title
        subtask = {
            "subtask_id": "3.2.1",
            "title": "Implement authentication flow",
            "status": "pending",
        }
        result, changed = normalize_subtask_aliases(subtask)

        assert result["id"] == "3.2.1"
        assert result["description"] == "Implement authentication flow"
        assert result["subtask_id"] == "3.2.1"
        assert result["title"] == "Implement authentication flow"
        assert result["status"] == "pending"
        assert changed is True

    def test_normalize_mixed_format(self):
        """Test normalization when some fields already normalized."""
        subtask = {
            "id": "1.1",
            "subtask_id": "1.1",
            "description": "Already has description",
            "title": "Extra title",
        }
        result, changed = normalize_subtask_aliases(subtask)

        # Should not change anything
        assert result["id"] == "1.1"
        assert result["description"] == "Already has description"
        assert changed is False

    def test_normalize_preserves_complex_nested_structure(self):
        """Test normalization preserves complex nested data structures."""
        subtask = {
            "subtask_id": "1.1",
            "title": "Task",
            "metadata": {
                "complex": {"nested": {"data": [1, 2, 3]}},
                "list": ["a", "b", "c"],
            },
            "status": "pending",
        }
        result, changed = normalize_subtask_aliases(subtask)

        assert result["id"] == "1.1"
        assert result["description"] == "Task"
        assert result["metadata"]["complex"]["nested"]["data"] == [1, 2, 3]
        assert result["metadata"]["list"] == ["a", "b", "c"]
        assert changed is True
