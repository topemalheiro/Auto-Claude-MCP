"""Comprehensive tests for conflict_explanation"""

from merge.conflict_explanation import (
    explain_conflict,
    get_compatible_pairs,
    format_compatibility_summary,
)
from merge.compatibility_rules import CompatibilityRule, build_default_rules
from merge.types import ChangeType, ConflictRegion, ConflictSeverity, MergeStrategy
import pytest


class TestExplainConflict:
    """Test explain_conflict function"""

    def test_explain_conflict_basic(self):
        """Test basic conflict explanation"""
        conflict = ConflictRegion(
            file_path="test.py",
            location="function:myFunc",
            tasks_involved=["task_001", "task_002"],
            change_types=[ChangeType.MODIFY_FUNCTION, ChangeType.ADD_HOOK_CALL],
            severity=ConflictSeverity.MEDIUM,
            can_auto_merge=False,
            reason="Both tasks modified the same function"
        )

        result = explain_conflict(conflict)

        assert "test.py" in result
        assert "function:myFunc" in result
        assert "task_001" in result
        assert "task_002" in result
        assert "medium" in result

    def test_explain_conflict_auto_mergeable(self):
        """Test explanation for auto-mergeable conflict"""
        conflict = ConflictRegion(
            file_path="test.tsx",
            location="function:App",
            tasks_involved=["task_001", "task_002"],
            change_types=[ChangeType.ADD_IMPORT, ChangeType.ADD_IMPORT],
            severity=ConflictSeverity.NONE,
            can_auto_merge=True,
            merge_strategy=MergeStrategy.COMBINE_IMPORTS,
            reason="Adding different imports is compatible"
        )

        result = explain_conflict(conflict)

        assert "auto-merged" in result.lower()
        assert "combine_imports" in result
        assert "test.tsx" in result

    def test_explain_conflict_not_auto_mergeable(self):
        """Test explanation for non-auto-mergeable conflict"""
        conflict = ConflictRegion(
            file_path="test.py",
            location="function:processData",
            tasks_involved=["task_001", "task_002"],
            change_types=[ChangeType.MODIFY_FUNCTION, ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.HIGH,
            can_auto_merge=False,
            merge_strategy=MergeStrategy.AI_REQUIRED,
            reason="Multiple modifications to same function need analysis"
        )

        result = explain_conflict(conflict)

        assert "Cannot be auto-merged" in result
        assert "Multiple modifications to same function need analysis" in result
        assert "test.py" in result

    def test_explain_conflict_with_multiple_change_types(self):
        """Test explanation with multiple change types"""
        conflict = ConflictRegion(
            file_path="component.tsx",
            location="function:UserProfile",
            tasks_involved=["task_001", "task_002", "task_003"],
            change_types=[
                ChangeType.ADD_HOOK_CALL,
                ChangeType.WRAP_JSX,
                ChangeType.MODIFY_JSX_PROPS
            ],
            severity=ConflictSeverity.LOW,
            can_auto_merge=True,
            merge_strategy=MergeStrategy.HOOKS_THEN_WRAP,
            reason="Hooks and wrapping are compatible"
        )

        result = explain_conflict(conflict)

        assert "add_hook_call" in result
        assert "wrap_jsx" in result
        assert "modify_jsx_props" in result
        assert "task_001" in result
        assert "task_002" in result
        assert "task_003" in result

    def test_explain_conflict_critical_severity(self):
        """Test explanation with critical severity"""
        conflict = ConflictRegion(
            file_path="core.py",
            location="function:authenticate",
            tasks_involved=["task_001", "task_002"],
            change_types=[ChangeType.MODIFY_FUNCTION, ChangeType.REMOVE_FUNCTION],
            severity=ConflictSeverity.CRITICAL,
            can_auto_merge=False,
            reason="One task modified while another removed the function"
        )

        result = explain_conflict(conflict)

        assert "critical" in result
        assert "core.py" in result

    def test_explain_conflict_format(self):
        """Test explanation format"""
        conflict = ConflictRegion(
            file_path="test.js",
            location="function:helper",
            tasks_involved=["task_A", "task_B"],
            change_types=[ChangeType.ADD_FUNCTION],
            severity=ConflictSeverity.NONE,
            can_auto_merge=True,
            merge_strategy=MergeStrategy.APPEND_FUNCTIONS
        )

        result = explain_conflict(conflict)

        lines = result.split("\n")
        assert len(lines) >= 6  # Header, tasks, severity, blank, can/cannot, blank, changes
        assert any("Conflict in" in line for line in lines)
        assert any("Tasks involved" in line for line in lines)
        assert any("Severity" in line for line in lines)
        assert any("Changes" in line or "add_function" in line for line in lines)


class TestGetCompatiblePairs:
    """Test get_compatible_pairs function"""

    def test_get_compatible_pairs_empty(self):
        """Test with empty rules list"""
        pairs = get_compatible_pairs([])

        assert pairs == []
        assert isinstance(pairs, list)

    def test_get_compatible_pairs_all_compatible(self):
        """Test with all compatible rules"""
        rules = [
            CompatibilityRule(
                change_type_a=ChangeType.ADD_IMPORT,
                change_type_b=ChangeType.ADD_IMPORT,
                compatible=True,
                strategy=MergeStrategy.COMBINE_IMPORTS,
                reason="Imports are compatible"
            ),
            CompatibilityRule(
                change_type_a=ChangeType.ADD_FUNCTION,
                change_type_b=ChangeType.ADD_FUNCTION,
                compatible=True,
                strategy=MergeStrategy.APPEND_FUNCTIONS,
                reason="Functions are compatible"
            ),
        ]

        pairs = get_compatible_pairs(rules)

        assert len(pairs) == 2
        assert pairs[0] == (ChangeType.ADD_IMPORT, ChangeType.ADD_IMPORT, MergeStrategy.COMBINE_IMPORTS)
        assert pairs[1] == (ChangeType.ADD_FUNCTION, ChangeType.ADD_FUNCTION, MergeStrategy.APPEND_FUNCTIONS)

    def test_get_compatible_pairs_filters_incompatible(self):
        """Test that incompatible rules are filtered out"""
        rules = [
            CompatibilityRule(
                change_type_a=ChangeType.ADD_IMPORT,
                change_type_b=ChangeType.ADD_IMPORT,
                compatible=True,
                strategy=MergeStrategy.COMBINE_IMPORTS,
            ),
            CompatibilityRule(
                change_type_a=ChangeType.MODIFY_FUNCTION,
                change_type_b=ChangeType.MODIFY_FUNCTION,
                compatible=False,
                strategy=MergeStrategy.AI_REQUIRED,
            ),
            CompatibilityRule(
                change_type_a=ChangeType.ADD_FUNCTION,
                change_type_b=ChangeType.ADD_FUNCTION,
                compatible=True,
                strategy=MergeStrategy.APPEND_FUNCTIONS,
            ),
        ]

        pairs = get_compatible_pairs(rules)

        assert len(pairs) == 2
        # Should only include compatible rules
        assert all(pair[2] is not None for pair in pairs)

    def test_get_compatible_pairs_with_none_strategy(self):
        """Test rules with None strategy"""
        rules = [
            CompatibilityRule(
                change_type_a=ChangeType.ADD_COMMENT,
                change_type_b=ChangeType.ADD_COMMENT,
                compatible=True,
                strategy=None,
                reason="Comments don't need special strategy"
            ),
        ]

        pairs = get_compatible_pairs(rules)

        assert len(pairs) == 1
        assert pairs[0][2] is None

    def test_get_compatible_pairs_from_default_rules(self):
        """Test using default rules"""
        rules = build_default_rules()
        pairs = get_compatible_pairs(rules)

        # Should have many compatible pairs
        assert len(pairs) > 0

        # All should have compatible=True (by definition of the function)
        for change_a, change_b, strategy in pairs:
            assert isinstance(change_a, ChangeType)
            assert isinstance(change_b, ChangeType)
            # Strategy can be None


class TestFormatCompatibilitySummary:
    """Test format_compatibility_summary function"""

    def test_format_compatibility_summary_empty(self):
        """Test with empty rules list"""
        summary = format_compatibility_summary([])

        assert "Compatibility Rules Summary" in summary
        assert "Total rules: 0" in summary
        assert "Compatible: 0" in summary
        assert "Incompatible: 0" in summary

    def test_format_compatibility_summary_structure(self):
        """Test summary structure"""
        rules = [
            CompatibilityRule(
                change_type_a=ChangeType.ADD_IMPORT,
                change_type_b=ChangeType.ADD_IMPORT,
                compatible=True,
                strategy=MergeStrategy.COMBINE_IMPORTS,
                reason="Test compatible"
            ),
            CompatibilityRule(
                change_type_a=ChangeType.MODIFY_FUNCTION,
                change_type_b=ChangeType.MODIFY_FUNCTION,
                compatible=False,
                reason="Test incompatible"
            ),
        ]

        summary = format_compatibility_summary(rules)

        assert "Compatibility Rules Summary" in summary
        assert "Total rules: 2" in summary
        assert "Compatible: 1" in summary
        assert "Incompatible: 1" in summary
        assert "Compatible Pairs" in summary
        assert "Incompatible Pairs" in summary

    def test_format_compatibility_summary_compatible_section(self):
        """Test compatible pairs section"""
        rules = [
            CompatibilityRule(
                change_type_a=ChangeType.ADD_IMPORT,
                change_type_b=ChangeType.ADD_IMPORT,
                compatible=True,
                strategy=MergeStrategy.COMBINE_IMPORTS,
                reason="Imports can be combined"
            ),
        ]

        summary = format_compatibility_summary(rules)

        assert "add_import + add_import" in summary
        assert "combine_imports" in summary
        assert "Imports can be combined" in summary

    def test_format_compatibility_summary_incompatible_section(self):
        """Test incompatible pairs section"""
        rules = [
            CompatibilityRule(
                change_type_a=ChangeType.MODIFY_FUNCTION,
                change_type_b=ChangeType.MODIFY_FUNCTION,
                compatible=False,
                reason="Function modifications conflict"
            ),
        ]

        summary = format_compatibility_summary(rules)

        assert "modify_function + modify_function" in summary
        assert "Function modifications conflict" in summary

    def test_format_compatibility_summary_with_defaults(self):
        """Test formatting default rules"""
        rules = build_default_rules()
        summary = format_compatibility_summary(rules)

        # Should have statistics
        assert "Total rules:" in summary
        assert "Compatible:" in summary
        assert "Incompatible:" in summary

        # Should have sections
        assert "Compatible Pairs:" in summary
        assert "Incompatible Pairs:" in summary

    def test_format_compatibility_summary_no_strategy(self):
        """Test formatting rule with no strategy"""
        rules = [
            CompatibilityRule(
                change_type_a=ChangeType.ADD_COMMENT,
                change_type_b=ChangeType.ADD_COMMENT,
                compatible=True,
                strategy=None,
                reason="Comments are independent"
            ),
        ]

        summary = format_compatibility_summary(rules)

        assert "add_comment + add_comment" in summary
        assert "N/A" in summary or "Strategy:" in summary

    def test_format_compatibility_summary_multiline(self):
        """Test that summary is multiline"""
        rules = [
            CompatibilityRule(
                change_type_a=ChangeType.ADD_IMPORT,
                change_type_b=ChangeType.ADD_FUNCTION,
                compatible=True,
                strategy=MergeStrategy.APPEND_FUNCTIONS,
                reason="Test"
            ),
        ]

        summary = format_compatibility_summary(rules)

        lines = summary.split("\n")
        assert len(lines) > 5  # Header, separator, stats, sections
