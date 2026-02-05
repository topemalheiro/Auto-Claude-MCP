"""Comprehensive tests for compatibility_rules"""

from merge.compatibility_rules import build_default_rules, CompatibilityRule, index_rules
from merge.types import ChangeType, MergeStrategy
import pytest


class TestCompatibilityRule:
    """Test CompatibilityRule dataclass"""

    def test_compatibility_rule_creation(self):
        """Test creating a CompatibilityRule"""
        rule = CompatibilityRule(
            change_type_a=ChangeType.ADD_IMPORT,
            change_type_b=ChangeType.ADD_IMPORT,
            compatible=True,
            strategy=MergeStrategy.COMBINE_IMPORTS,
            reason="Test reason",
            bidirectional=True
        )

        assert rule.change_type_a == ChangeType.ADD_IMPORT
        assert rule.change_type_b == ChangeType.ADD_IMPORT
        assert rule.compatible is True
        assert rule.strategy == MergeStrategy.COMBINE_IMPORTS
        assert rule.reason == "Test reason"
        assert rule.bidirectional is True

    def test_compatibility_rule_defaults(self):
        """Test CompatibilityRule default values"""
        rule = CompatibilityRule(
            change_type_a=ChangeType.ADD_FUNCTION,
            change_type_b=ChangeType.ADD_FUNCTION,
            compatible=True
        )

        assert rule.strategy is None
        assert rule.reason == ""
        assert rule.bidirectional is True


class TestBuildDefaultRules:
    """Test build_default_rules function"""

    def test_build_default_rules_returns_list(self):
        """Test that build_default_rules returns a list"""
        rules = build_default_rules()

        assert isinstance(rules, list)
        assert len(rules) > 0

    def test_build_default_rules_has_import_rules(self):
        """Test that import rules are included"""
        rules = build_default_rules()

        # Check for ADD_IMPORT + ADD_IMPORT rule
        import_add_rules = [
            r for r in rules
            if r.change_type_a == ChangeType.ADD_IMPORT
            and r.change_type_b == ChangeType.ADD_IMPORT
        ]
        assert len(import_add_rules) > 0

        rule = import_add_rules[0]
        assert rule.compatible is True
        assert rule.strategy == MergeStrategy.COMBINE_IMPORTS

    def test_build_default_rules_has_function_rules(self):
        """Test that function rules are included"""
        rules = build_default_rules()

        # Check for ADD_FUNCTION + ADD_FUNCTION rule
        func_add_rules = [
            r for r in rules
            if r.change_type_a == ChangeType.ADD_FUNCTION
            and r.change_type_b == ChangeType.ADD_FUNCTION
        ]
        assert len(func_add_rules) > 0

        rule = func_add_rules[0]
        assert rule.compatible is True
        assert rule.strategy == MergeStrategy.APPEND_FUNCTIONS

    def test_build_default_rules_has_modify_function_conflict(self):
        """Test that MODIFY_FUNCTION + MODIFY_FUNCTION is marked as incompatible"""
        rules = build_default_rules()

        modify_rules = [
            r for r in rules
            if r.change_type_a == ChangeType.MODIFY_FUNCTION
            and r.change_type_b == ChangeType.MODIFY_FUNCTION
        ]
        assert len(modify_rules) > 0

        rule = modify_rules[0]
        assert rule.compatible is False
        assert rule.strategy == MergeStrategy.AI_REQUIRED

    def test_build_default_rules_has_hook_rules(self):
        """Test that React hook rules are included"""
        rules = build_default_rules()

        # Check for ADD_HOOK_CALL + ADD_HOOK_CALL rule
        hook_add_rules = [
            r for r in rules
            if r.change_type_a == ChangeType.ADD_HOOK_CALL
            and r.change_type_b == ChangeType.ADD_HOOK_CALL
        ]
        assert len(hook_add_rules) > 0

        rule = hook_add_rules[0]
        assert rule.compatible is True
        assert rule.strategy == MergeStrategy.ORDER_BY_DEPENDENCY

    def test_build_default_rules_has_jsx_rules(self):
        """Test that JSX rules are included"""
        rules = build_default_rules()

        # Check for WRAP_JSX + WRAP_JSX rule
        wrap_rules = [
            r for r in rules
            if r.change_type_a == ChangeType.WRAP_JSX
            and r.change_type_b == ChangeType.WRAP_JSX
        ]
        assert len(wrap_rules) > 0

        rule = wrap_rules[0]
        assert rule.compatible is True

    def test_build_default_rules_has_class_rules(self):
        """Test that class rules are included"""
        rules = build_default_rules()

        # Check for ADD_METHOD + ADD_METHOD rule
        method_rules = [
            r for r in rules
            if r.change_type_a == ChangeType.ADD_METHOD
            and r.change_type_b == ChangeType.ADD_METHOD
        ]
        assert len(method_rules) > 0

        rule = method_rules[0]
        assert rule.compatible is True
        assert rule.strategy == MergeStrategy.APPEND_METHODS

    def test_build_default_rules_has_type_rules(self):
        """Test that TypeScript type rules are included"""
        rules = build_default_rules()

        # Check for ADD_INTERFACE + ADD_INTERFACE rule
        interface_rules = [
            r for r in rules
            if r.change_type_a == ChangeType.ADD_INTERFACE
            and r.change_type_b == ChangeType.ADD_INTERFACE
        ]
        assert len(interface_rules) > 0

        rule = interface_rules[0]
        assert rule.compatible is True

    def test_build_default_rules_formatting_compatible(self):
        """Test that FORMATTING_ONLY is always compatible"""
        rules = build_default_rules()

        format_rules = [
            r for r in rules
            if r.change_type_a == ChangeType.FORMATTING_ONLY
            and r.change_type_b == ChangeType.FORMATTING_ONLY
        ]
        assert len(format_rules) > 0

        rule = format_rules[0]
        assert rule.compatible is True

    def test_build_default_rules_all_rules_have_reason(self):
        """Test that all rules have a reason"""
        rules = build_default_rules()

        for rule in rules:
            assert isinstance(rule.reason, str)
            assert len(rule.reason) > 0

    def test_build_default_rules_count(self):
        """Test the expected number of default rules"""
        rules = build_default_rules()

        # Should have at least 20 rules covering various combinations
        assert len(rules) >= 20


class TestIndexRules:
    """Test index_rules function"""

    def test_index_rules_empty_list(self):
        """Test indexing an empty list of rules"""
        index = index_rules([])

        assert index == {}
        assert isinstance(index, dict)

    def test_index_rules_single_rule(self):
        """Test indexing a single rule"""
        rule = CompatibilityRule(
            change_type_a=ChangeType.ADD_IMPORT,
            change_type_b=ChangeType.ADD_IMPORT,
            compatible=True
        )

        index = index_rules([rule])

        assert len(index) == 1
        key = (ChangeType.ADD_IMPORT, ChangeType.ADD_IMPORT)
        assert key in index
        assert index[key] == rule

    def test_index_rules_bidirectional(self):
        """Test that bidirectional rules create both entries"""
        rule = CompatibilityRule(
            change_type_a=ChangeType.ADD_IMPORT,
            change_type_b=ChangeType.ADD_FUNCTION,
            compatible=True,
            bidirectional=True
        )

        index = index_rules([rule])

        # Should have both (A, B) and (B, A) entries
        assert len(index) == 2
        key1 = (ChangeType.ADD_IMPORT, ChangeType.ADD_FUNCTION)
        key2 = (ChangeType.ADD_FUNCTION, ChangeType.ADD_IMPORT)
        assert key1 in index
        assert key2 in index

    def test_index_rules_not_bidirectional(self):
        """Test that non-bidirectional rules create single entry"""
        rule = CompatibilityRule(
            change_type_a=ChangeType.ADD_IMPORT,
            change_type_b=ChangeType.ADD_FUNCTION,
            compatible=True,
            bidirectional=False
        )

        index = index_rules([rule])

        # Should only have (A, B) entry
        assert len(index) == 1
        key = (ChangeType.ADD_IMPORT, ChangeType.ADD_FUNCTION)
        assert key in index

    def test_index_rules_same_type_not_duplicated(self):
        """Test that same-type rules don't create duplicate entries"""
        rule = CompatibilityRule(
            change_type_a=ChangeType.ADD_IMPORT,
            change_type_b=ChangeType.ADD_IMPORT,
            compatible=True,
            bidirectional=True
        )

        index = index_rules([rule])

        # Should only have one entry since A == B
        assert len(index) == 1

    def test_index_rules_multiple_rules(self):
        """Test indexing multiple rules"""
        rules = [
            CompatibilityRule(
                change_type_a=ChangeType.ADD_IMPORT,
                change_type_b=ChangeType.ADD_IMPORT,
                compatible=True
            ),
            CompatibilityRule(
                change_type_a=ChangeType.ADD_FUNCTION,
                change_type_b=ChangeType.ADD_FUNCTION,
                compatible=True
            ),
            CompatibilityRule(
                change_type_a=ChangeType.MODIFY_FUNCTION,
                change_type_b=ChangeType.MODIFY_FUNCTION,
                compatible=False
            ),
        ]

        index = index_rules(rules)

        assert len(index) == 3

    def test_index_rules_lookup_performance(self):
        """Test that indexed rules allow efficient lookup"""
        rules = build_default_rules()
        index = index_rules(rules)

        # Should be able to look up any pair efficiently
        key = (ChangeType.ADD_IMPORT, ChangeType.ADD_FUNCTION)
        # This lookup should be O(1)
        result = index.get(key)

        # May or may not exist, but lookup should work
        assert result is None or isinstance(result, CompatibilityRule)

    def test_index_rules_with_defaults(self):
        """Test indexing the default rules"""
        rules = build_default_rules()
        index = index_rules(rules)

        # Index should be non-empty
        assert len(index) > 0

        # Check that some expected keys exist
        assert (ChangeType.ADD_IMPORT, ChangeType.ADD_IMPORT) in index
        assert (ChangeType.ADD_FUNCTION, ChangeType.ADD_FUNCTION) in index
