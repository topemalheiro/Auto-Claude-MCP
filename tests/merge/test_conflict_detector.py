"""Comprehensive tests for conflict_detector module"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from merge.compatibility_rules import CompatibilityRule
from merge.conflict_detector import ConflictDetector, analyze_compatibility
from merge.types import (
    ChangeType,
    ConflictRegion,
    ConflictSeverity,
    FileAnalysis,
    MergeStrategy,
    SemanticChange,
)


class TestConflictDetector:
    """Test suite for ConflictDetector class"""

    def test_init_creates_default_rules(self):
        """Test that initialization creates default compatibility rules"""
        detector = ConflictDetector()

        assert detector is not None
        assert hasattr(detector, "_rules")
        assert hasattr(detector, "_rule_index")
        assert len(detector._rules) > 0
        assert len(detector._rule_index) > 0

    def test_add_rule_adds_to_rules_and_index(self):
        """Test adding a custom rule adds it to both rules list and index"""
        detector = ConflictDetector()
        initial_rule_count = len(detector._rules)

        rule = CompatibilityRule(
            change_type_a=ChangeType.ADD_IMPORT,
            change_type_b=ChangeType.ADD_FUNCTION,
            compatible=True,
            strategy="append",
        )

        detector.add_rule(rule)

        assert len(detector._rules) == initial_rule_count + 1
        assert (ChangeType.ADD_IMPORT, ChangeType.ADD_FUNCTION) in detector._rule_index

    def test_add_rule_bidirectional(self):
        """Test that bidirectional rules are added both ways"""
        detector = ConflictDetector()

        rule = CompatibilityRule(
            change_type_a=ChangeType.ADD_IMPORT,
            change_type_b=ChangeType.ADD_FUNCTION,
            compatible=True,
            strategy="append",
            bidirectional=True,
        )

        detector.add_rule(rule)

        # Both directions should be indexed
        assert (ChangeType.ADD_IMPORT, ChangeType.ADD_FUNCTION) in detector._rule_index
        assert (ChangeType.ADD_FUNCTION, ChangeType.ADD_IMPORT) in detector._rule_index

    def test_add_rule_non_bidirectional(self):
        """Test that non-bidirectional rules are only indexed one way"""
        detector = ConflictDetector()

        rule = CompatibilityRule(
            change_type_a=ChangeType.ADD_IMPORT,
            change_type_b=ChangeType.ADD_FUNCTION,
            compatible=True,
            strategy="append",
            bidirectional=False,
        )

        detector.add_rule(rule)

        # Only one direction should be indexed
        assert (ChangeType.ADD_IMPORT, ChangeType.ADD_FUNCTION) in detector._rule_index
        assert (ChangeType.ADD_FUNCTION, ChangeType.ADD_IMPORT) not in detector._rule_index

    def test_detect_conflicts_with_no_changes(self):
        """Test conflict detection with no changes returns empty list"""
        detector = ConflictDetector()

        task_analyses = {
            "task-001": FileAnalysis(file_path="test.py", changes=[]),
            "task-002": FileAnalysis(file_path="test.py", changes=[]),
        }

        conflicts = detector.detect_conflicts(task_analyses)

        assert isinstance(conflicts, list)
        assert len(conflicts) == 0

    def test_detect_conflicts_with_single_task(self):
        """Test conflict detection with single task returns empty list"""
        detector = ConflictDetector()

        change = SemanticChange(
            change_type=ChangeType.ADD_FUNCTION,
            target="new_func",
            location="file_top",
            line_start=5,
            line_end=10,
            content_after="def new_func():\n    pass",
        )

        task_analyses = {
            "task-001": FileAnalysis(file_path="test.py", changes=[change]),
        }

        conflicts = detector.detect_conflicts(task_analyses)

        assert isinstance(conflicts, list)
        assert len(conflicts) == 0

    def test_detect_conflicts_with_compatible_changes(self):
        """Test that compatible changes don't create conflicts"""
        detector = ConflictDetector()

        # Two tasks adding different imports - should be compatible
        change1 = SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="os",
            location="file_top",
            line_start=1,
            line_end=2,
            content_after="import os",
        )

        change2 = SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="sys",
            location="file_top",
            line_start=2,
            line_end=3,
            content_after="import sys",
        )

        task_analyses = {
            "task-001": FileAnalysis(file_path="test.py", changes=[change1]),
            "task-002": FileAnalysis(file_path="test.py", changes=[change2]),
        }

        conflicts = detector.detect_conflicts(task_analyses)

        # Should either have no conflicts or only auto-mergeable ones
        for conflict in conflicts:
            assert conflict.can_auto_merge is True

    def test_detect_conflicts_with_incompatible_changes(self):
        """Test that incompatible changes create conflicts"""
        detector = ConflictDetector()

        # Two tasks modifying the same function
        change1 = SemanticChange(
            change_type=ChangeType.MODIFY_FUNCTION,
            target="existing_func",
            location="function:existing_func",
            line_start=5,
            line_end=10,
            content_before="def existing_func():\n    pass",
            content_after="def existing_func():\n    return True",
        )

        change2 = SemanticChange(
            change_type=ChangeType.MODIFY_FUNCTION,
            target="existing_func",
            location="function:existing_func",
            line_start=5,
            line_end=10,
            content_before="def existing_func():\n    pass",
            content_after="def existing_func():\n    return False",
        )

        task_analyses = {
            "task-001": FileAnalysis(file_path="test.py", changes=[change1]),
            "task-002": FileAnalysis(file_path="test.py", changes=[change2]),
        }

        conflicts = detector.detect_conflicts(task_analyses)

        assert len(conflicts) > 0
        # At least one conflict should exist for same location modifications
        found_same_location = any(
            c.location == "function:existing_func" for c in conflicts
        )
        assert found_same_location is True

    def test_detect_conflicts_returns_conflict_regions(self):
        """Test that detect_conflicts returns proper ConflictRegion objects"""
        detector = ConflictDetector()

        change1 = SemanticChange(
            change_type=ChangeType.MODIFY_FUNCTION,
            target="func",
            location="function:func",
            line_start=1,
            line_end=5,
        )

        change2 = SemanticChange(
            change_type=ChangeType.MODIFY_FUNCTION,
            target="func",
            location="function:func",
            line_start=1,
            line_end=5,
        )

        task_analyses = {
            "task-001": FileAnalysis(file_path="test.py", changes=[change1]),
            "task-002": FileAnalysis(file_path="test.py", changes=[change2]),
        }

        conflicts = detector.detect_conflicts(task_analyses)

        for conflict in conflicts:
            assert isinstance(conflict, ConflictRegion)
            assert hasattr(conflict, "file_path")
            assert hasattr(conflict, "location")
            assert hasattr(conflict, "tasks_involved")
            assert hasattr(conflict, "change_types")
            assert hasattr(conflict, "severity")
            assert hasattr(conflict, "can_auto_merge")
            assert hasattr(conflict, "merge_strategy")
            assert hasattr(conflict, "reason")

    def test_get_compatible_pairs_returns_list(self):
        """Test that get_compatible_pairs returns list of tuples"""
        detector = ConflictDetector()

        pairs = detector.get_compatible_pairs()

        assert isinstance(pairs, list)
        assert len(pairs) > 0

        for pair in pairs:
            assert isinstance(pair, tuple)
            assert len(pair) == 3
            assert isinstance(pair[0], ChangeType)
            assert isinstance(pair[1], ChangeType)
            assert isinstance(pair[2], MergeStrategy)

    def test_explain_conflict_returns_string(self):
        """Test that explain_conflict returns human-readable string"""
        detector = ConflictDetector()

        conflict = ConflictRegion(
            file_path="test.py",
            location="function:my_func",
            tasks_involved=["task-001", "task-002"],
            change_types=[ChangeType.MODIFY_FUNCTION, ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.HIGH,
            can_auto_merge=False,
            reason="Both tasks modified the same function",
        )

        explanation = detector.explain_conflict(conflict)

        assert isinstance(explanation, str)
        assert len(explanation) > 0
        # Should contain relevant information
        assert "test.py" in explanation or "function:my_func" in explanation

    def test_explain_conflict_with_merge_strategy(self):
        """Test explanation for auto-mergeable conflict includes strategy"""
        detector = ConflictDetector()

        conflict = ConflictRegion(
            file_path="test.py",
            location="file_top",
            tasks_involved=["task-001", "task-002"],
            change_types=[ChangeType.ADD_IMPORT, ChangeType.ADD_IMPORT],
            severity=ConflictSeverity.NONE,
            can_auto_merge=True,
            merge_strategy=MergeStrategy.COMBINE_IMPORTS,
            reason="Both tasks added imports",
        )

        explanation = detector.explain_conflict(conflict)

        assert isinstance(explanation, str)
        # Should mention the merge strategy
        assert "combine_imports" in explanation or "import" in explanation.lower()


class TestAnalyzeCompatibility:
    """Test suite for analyze_compatibility function"""

    def test_analyze_compatibility_returns_tuple(self):
        """Test that analyze_compatibility returns a tuple"""
        change_a = SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="os",
            location="file_top",
            line_start=1,
            line_end=2,
        )

        change_b = SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="sys",
            location="file_top",
            line_start=2,
            line_end=3,
        )

        result = analyze_compatibility(change_a, change_b)

        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_analyze_compatibility_with_detector(self):
        """Test analyze_compatibility with provided detector"""
        detector = ConflictDetector()

        change_a = SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="os",
            location="file_top",
            line_start=1,
            line_end=2,
        )

        change_b = SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="sys",
            location="file_top",
            line_start=2,
            line_end=3,
        )

        result = analyze_compatibility(change_a, change_b, detector)

        assert isinstance(result, tuple)
        compatible, strategy, reason = result
        assert isinstance(compatible, bool)
        assert isinstance(strategy, (MergeStrategy, type(None)))
        assert isinstance(reason, str)

    def test_analyze_compatibility_creates_detector_if_not_provided(self):
        """Test that analyze_compatibility creates detector if not provided"""
        change_a = SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="os",
            location="file_top",
            line_start=1,
            line_end=2,
        )

        change_b = SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="sys",
            location="file_top",
            line_start=2,
            line_end=3,
        )

        # Should not raise an error
        result = analyze_compatibility(change_a, change_b)

        assert result is not None

    def test_analyze_compatible_imports(self):
        """Test that adding different imports is compatible"""
        change_a = SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="os",
            location="file_top",
            line_start=1,
            line_end=2,
        )

        change_b = SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="sys",
            location="file_top",
            line_start=2,
            line_end=3,
        )

        compatible, strategy, reason = analyze_compatibility(change_a, change_b)

        assert compatible is True
        assert strategy is not None
        assert len(reason) > 0

    def test_analyze_incompatible_same_target_modifications(self):
        """Test that modifying the same target is incompatible"""
        change_a = SemanticChange(
            change_type=ChangeType.MODIFY_FUNCTION,
            target="my_func",
            location="function:my_func",
            line_start=1,
            line_end=5,
            content_before="def my_func():\n    pass",
            content_after="def my_func():\n    return 1",
        )

        change_b = SemanticChange(
            change_type=ChangeType.MODIFY_FUNCTION,
            target="my_func",
            location="function:my_func",
            line_start=1,
            line_end=5,
            content_before="def my_func():\n    pass",
            content_after="def my_func():\n    return 2",
        )

        compatible, strategy, reason = analyze_compatibility(change_a, change_b)

        # Same target modifications should be incompatible
        assert compatible is False
        assert len(reason) > 0


class TestConflictDetectorIntegration:
    """Integration tests for ConflictDetector"""

    def test_full_conflict_detection_workflow(self):
        """Test complete workflow from detection to explanation"""
        detector = ConflictDetector()

        # Create complex scenario with multiple changes
        change1 = SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="os",
            location="file_top",
            line_start=1,
            line_end=2,
            content_after="import os",
        )

        change2 = SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="json",
            location="file_top",
            line_start=2,
            line_end=3,
            content_after="import json",
        )

        change3 = SemanticChange(
            change_type=ChangeType.MODIFY_FUNCTION,
            target="process",
            location="function:process",
            line_start=10,
            line_end=15,
            content_before="def process():\n    pass",
            content_after="def process():\n    return True",
        )

        task_analyses = {
            "task-001": FileAnalysis(file_path="app.py", changes=[change1, change3]),
            "task-002": FileAnalysis(file_path="app.py", changes=[change2]),
        }

        # Detect conflicts
        conflicts = detector.detect_conflicts(task_analyses)

        # Verify results
        assert isinstance(conflicts, list)

        # Explain any conflicts found
        for conflict in conflicts:
            explanation = detector.explain_conflict(conflict)
            assert isinstance(explanation, str)
            assert len(explanation) > 0

    def test_custom_rule_overrides_default(self):
        """Test that custom rules can be added to override defaults"""
        detector = ConflictDetector()

        # Add a custom rule
        custom_rule = CompatibilityRule(
            change_type_a=ChangeType.ADD_FUNCTION,
            change_type_b=ChangeType.ADD_FUNCTION,
            compatible=True,
            strategy="append",
            reason="Custom rule: allow combining functions",
        )

        detector.add_rule(custom_rule)

        # Verify the rule was added
        assert len(detector._rules) > 0

        # The rule should be accessible in the index
        key = (ChangeType.ADD_FUNCTION, ChangeType.ADD_FUNCTION)
        if custom_rule.bidirectional or custom_rule.change_type_a == custom_rule.change_type_b:
            assert key in detector._rule_index or (
                custom_rule.change_type_b,
                custom_rule.change_type_a,
            ) in detector._rule_index
