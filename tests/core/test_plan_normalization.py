"""Tests for plan_normalization"""

from core.plan_normalization import normalize_subtask_aliases
import pytest


class TestNormalizeSubtaskAliases:
    """Tests for normalize_subtask_aliases function"""

    def test_no_changes_needed(self):
        """Test when subtask already has id and description"""
        subtask = {"id": "task-1", "description": "A task", "status": "pending"}
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is False
        assert result == subtask

    def test_copies_subtask_id_to_id_when_id_missing(self):
        """Test copying subtask_id to id when id is missing"""
        subtask = {"subtask_id": "legacy-123", "status": "pending"}
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is True
        assert result["id"] == "legacy-123"
        assert result["subtask_id"] == "legacy-123"  # original preserved

    def test_copies_numeric_subtask_id_to_id_as_string(self):
        """Test converting numeric subtask_id to string for id"""
        subtask = {"subtask_id": 42, "status": "pending"}
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is True
        assert result["id"] == "42"
        assert result["subtask_id"] == 42  # original preserved

    def test_id_preserved_when_present(self):
        """Test that existing id is not modified"""
        subtask = {"id": "existing-id", "subtask_id": "legacy-123"}
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is False
        assert result["id"] == "existing-id"

    def test_none_id_treated_as_missing(self):
        """Test that None id is treated as missing and uses subtask_id"""
        subtask = {"id": None, "subtask_id": "fallback-id"}
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is True
        assert result["id"] == "fallback-id"

    def test_empty_string_id_treated_as_missing(self):
        """Test that empty string id is treated as missing"""
        subtask = {"id": "   ", "subtask_id": "fallback-id"}
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is True
        assert result["id"] == "fallback-id"

    def test_no_id_copy_when_subtask_id_none(self):
        """Test no id copy when subtask_id is None"""
        subtask = {"subtask_id": None, "status": "pending"}
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is False
        assert "id" not in result

    def test_no_id_copy_when_subtask_id_empty_string(self):
        """Test no id copy when subtask_id is empty string"""
        subtask = {"subtask_id": "   ", "status": "pending"}
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is False
        assert "id" not in result

    def test_copies_title_to_description_when_description_missing(self):
        """Test copying title to description when description is missing"""
        subtask = {"title": "Do something", "status": "pending"}
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is True
        assert result["description"] == "Do something"
        assert result["title"] == "Do something"  # original preserved

    def test_copies_title_to_description_when_description_empty(self):
        """Test copying title to description when description is empty"""
        subtask = {"title": "My Task", "description": "", "status": "pending"}
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is True
        assert result["description"] == "My Task"

    def test_copies_title_to_description_when_description_whitespace(self):
        """Test copying title to description when description is whitespace"""
        subtask = {"title": "My Task", "description": "   ", "status": "pending"}
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is True
        assert result["description"] == "My Task"

    def test_copies_stripped_title_to_description(self):
        """Test that title is stripped before copying to description"""
        subtask = {"title": "  My Task  ", "status": "pending"}
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is True
        assert result["description"] == "My Task"

    def test_description_preserved_when_present(self):
        """Test that existing description is not modified"""
        subtask = {"title": "My Title", "description": "My Description"}
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is False
        assert result["description"] == "My Description"

    def test_description_none_treated_as_missing(self):
        """Test that None description is treated as missing"""
        subtask = {"description": None, "title": "Fallback"}
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is True
        assert result["description"] == "Fallback"

    def test_no_title_copy_when_title_not_string(self):
        """Test no title copy when title is not a string"""
        subtask = {"title": 123, "description": None}
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is False
        assert result.get("description") is None

    def test_no_title_copy_when_title_empty(self):
        """Test no title copy when title is empty string"""
        subtask = {"title": "", "description": None}
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is False
        assert result.get("description") is None

    def test_no_title_copy_when_title_whitespace(self):
        """Test no title copy when title is whitespace"""
        subtask = {"title": "   ", "description": None}
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is False
        assert result.get("description") is None

    def test_both_id_and_description_normalized(self):
        """Test both id and description can be normalized in one call"""
        subtask = {"subtask_id": "123", "title": "Task Title"}
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is True
        assert result["id"] == "123"
        assert result["description"] == "Task Title"

    def test_original_dict_not_modified(self):
        """Test that the original subtask dict is not modified"""
        subtask = {"subtask_id": "123", "title": "Title"}
        original = subtask.copy()
        normalize_subtask_aliases(subtask)

        assert subtask == original
        assert "id" not in subtask
        assert "description" not in subtask

    def test_preserves_all_other_fields(self):
        """Test that all other fields are preserved"""
        subtask = {
            "subtask_id": "123",
            "title": "Title",
            "status": "in_progress",
            "priority": "high",
            "assigned_to": "user1",
            "dependencies": ["task-1", "task-2"],
        }
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is True
        assert result["status"] == "in_progress"
        assert result["priority"] == "high"
        assert result["assigned_to"] == "user1"
        assert result["dependencies"] == ["task-1", "task-2"]

    def test_empty_subtask(self):
        """Test with completely empty subtask"""
        subtask = {}
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is False
        assert result == {}

    def test_id_already_present_non_string(self):
        """Test that non-string id is preserved"""
        subtask = {"id": 123, "subtask_id": "456"}
        result, changed = normalize_subtask_aliases(subtask)

        assert changed is False
        assert result["id"] == 123
