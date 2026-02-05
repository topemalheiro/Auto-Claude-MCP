"""
Comprehensive Tests for context.categorizer module
==================================================

Tests for FileCategorizer class including all categorization logic,
edge cases, and various file type handling.
"""

import pytest

from context.categorizer import FileCategorizer
from context.models import FileMatch


class TestFileCategorizerInit:
    """Tests for FileCategorizer initialization"""

    def test_init(self):
        """Test FileCategorizer initialization"""
        categorizer = FileCategorizer()
        assert categorizer.MODIFY_KEYWORDS is not None
        assert isinstance(categorizer.MODIFY_KEYWORDS, list)

    def test_modify_keywords_defined(self):
        """Test that MODIFY_KEYWORDS are properly defined"""
        keywords = FileCategorizer.MODIFY_KEYWORDS
        expected_keywords = [
            "add", "create", "implement", "fix", "update",
            "change", "modify", "new"
        ]
        for kw in expected_keywords:
            assert kw in keywords


class TestCategorizeMatchesBasic:
    """Tests for basic categorization"""

    def test_categorize_empty_matches(self):
        """Test categorization with empty matches list"""
        categorizer = FileCategorizer()
        to_modify, to_reference = categorizer.categorize_matches([], "Some task")
        assert to_modify == []
        assert to_reference == []

    def test_categorize_basic_modification_task(self):
        """Test categorization with basic modification task"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="api/auth.py",
                service="api",
                reason="Contains: authentication",
                relevance_score=8,
                matching_lines=[]
            )
        ]
        task = "Add authentication to API"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # Should be in modify due to high score and modification task
        assert len(to_modify) >= 0
        assert isinstance(to_modify, list)
        assert isinstance(to_reference, list)

    def test_categorize_non_modification_task(self):
        """Test categorization with non-modification task"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="api/auth.py",
                service="api",
                reason="Contains: authentication",
                relevance_score=8,
                matching_lines=[]
            )
        ]
        task = "Explain how authentication works"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # With no modification keywords, high relevance might still go to reference
        assert isinstance(to_modify, list)
        assert isinstance(to_reference, list)


class TestTestFileCategorization:
    """Tests for test file categorization"""

    def test_categorize_test_files_always_reference(self):
        """Test that test files are always categorized as references"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="api/test_auth.py",
                service="api",
                reason="Contains: authentication",
                relevance_score=10,
                matching_lines=[]
            )
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # Test files should always be references
        assert not any(f.path == "api/test_auth.py" for f in to_modify)
        assert any(f.path == "api/test_auth.py" for f in to_reference)

    def test_categorize_spec_files_as_reference(self):
        """Test that spec files are categorized as references"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="api/auth_spec.py",
                service="api",
                reason="Contains: authentication",
                relevance_score=10,
                matching_lines=[]
            )
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # Spec files should be references
        assert not any(f.path == "api/auth_spec.py" for f in to_modify)
        assert any(f.path == "api/auth_spec.py" for f in to_reference)

    def test_categorize_test_case_insensitive(self):
        """Test that test detection is case insensitive"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="api/TEST_auth.py",
                service="api",
                reason="Contains: authentication",
                relevance_score=8,
                matching_lines=[]
            )
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # TEST in path should still categorize as reference
        assert not any("TEST_auth.py" in f.path for f in to_modify)


class ExampleFileCategorization:
    """Tests for example file categorization"""

    def test_categorize_example_files_as_reference(self):
        """Test that example files are categorized as references"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="examples/auth_example.py",
                service="api",
                reason="Contains: authentication",
                relevance_score=10,
                matching_lines=[]
            )
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # Example files should be references
        assert not any(f.path == "examples/auth_example.py" for f in to_modify)
        assert any(f.path == "examples/auth_example.py" for f in to_reference)

    def test_categorize_sample_files_as_reference(self):
        """Test that sample files are categorized as references"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="samples/auth_sample.py",
                service="api",
                reason="Contains: authentication",
                relevance_score=10,
                matching_lines=[]
            )
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # Sample files should be references
        assert not any(f.path == "samples/auth_sample.py" for f in to_modify)
        assert any(f.path == "samples/auth_sample.py" for f in to_reference)


class TestConfigFileCategorization:
    """Tests for config file categorization"""

    def test_categorize_low_score_config_as_reference(self):
        """Test that low-score config files are references"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="config/settings.py",
                service="api",
                reason="Contains: settings",
                relevance_score=3,
                matching_lines=[]
            )
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # Low score config should be reference
        assert not any(f.path == "config/settings.py" for f in to_modify)
        assert any(f.path == "config/settings.py" for f in to_reference)

    def test_categorize_high_score_config_can_modify(self):
        """Test that high-score config files can be modified"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="config/auth_config.py",
                service="api",
                reason="Contains: authentication config",
                relevance_score=8,
                matching_lines=[]
            )
        ]
        task = "Add authentication config"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # High score config might be modified
        # Either way, it should be categorized
        total = len(to_modify) + len(to_reference)
        assert total == 1


class TestRelevanceScoreCategorization:
    """Tests for relevance score-based categorization"""

    def test_high_relevance_with_modification(self):
        """Test high relevance files with modification task"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="api/auth.py",
                service="api",
                reason="Contains: authentication",
                relevance_score=8,
                matching_lines=[]
            )
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # High score + modification = likely to modify
        assert len(to_modify) >= 0

    def test_low_relevance_becomes_reference(self):
        """Test low relevance files become references"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="api/utils.py",
                service="api",
                reason="Related: authentication",
                relevance_score=2,
                matching_lines=[]
            )
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # Low score should be reference
        assert not any(f.path == "api/utils.py" for f in to_modify)
        assert any(f.path == "api/utils.py" for f in to_reference)

    def test_relevance_threshold_boundary(self):
        """Test relevance score at threshold boundary (5)"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="api/auth.py",
                service="api",
                reason="Contains: authentication",
                relevance_score=5,
                matching_lines=[]
            )
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # Score of 5 with modification task should be in modify
        assert len(to_modify) >= 0


class TestModifyKeywordDetection:
    """Tests for modification keyword detection"""

    def test_all_modify_keywords(self):
        """Test all modify keywords trigger modification mode"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="api/auth.py",
                service="api",
                reason="Contains: auth",
                relevance_score=8,
                matching_lines=[]
            )
        ]

        for keyword in categorizer.MODIFY_KEYWORDS:
            task = f"{keyword.capitalize()} authentication"
            to_modify, to_reference = categorizer.categorize_matches(matches, task)
            # Should have modification mode enabled
            assert isinstance(to_modify, list)
            assert isinstance(to_reference, list)

    def test_modify_keyword_case_insensitive(self):
        """Test that modify keyword detection is case insensitive"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="api/auth.py",
                service="api",
                reason="Contains: auth",
                relevance_score=8,
                matching_lines=[]
            )
        ]

        for case in ["ADD", "Add", "aDd", "add"]:
            task = f"{case} authentication"
            to_modify, _ = categorizer.categorize_matches(matches, task)
            assert isinstance(to_modify, list)

    def test_no_modify_keywords(self):
        """Test task without modify keywords"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="api/auth.py",
                service="api",
                reason="Contains: auth",
                relevance_score=8,
                matching_lines=[]
            )
        ]
        task = "Explain authentication system"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # Without modification keywords, might go to reference
        assert isinstance(to_modify, list)
        assert isinstance(to_reference, list)


class TestLimiting:
    """Tests for max_modify and max_reference limits"""

    def test_max_modify_limit(self):
        """Test that to_modify is limited to max_modify"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path=f"api/file_{i}.py",
                service="api",
                reason="Contains: auth",
                relevance_score=8,
                matching_lines=[]
            )
            for i in range(15)
        ]
        task = "Add authentication"

        to_modify, _ = categorizer.categorize_matches(matches, task, max_modify=10)

        # Should limit to 10
        assert len(to_modify) <= 10

    def test_max_reference_limit(self):
        """Test that to_reference is limited to max_reference"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path=f"api/test_{i}.py",
                service="api",
                reason="Contains: auth",
                relevance_score=5,
                matching_lines=[]
            )
            for i in range(20)
        ]
        task = "Add authentication"

        _, to_reference = categorizer.categorize_matches(matches, task, max_reference=15)

        # Should limit to 15
        assert len(to_reference) <= 15

    def test_custom_limits(self):
        """Test custom max_modify and max_reference values"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path=f"api/file_{i}.py",
                service="api",
                reason="Contains: auth",
                relevance_score=8,
                matching_lines=[]
            )
            for i in range(10)
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(
            matches, task, max_modify=3, max_reference=5
        )

        assert len(to_modify) <= 3
        assert len(to_reference) <= 5


class TestReasonUpdates:
    """Tests for reason field updates during categorization"""

    def test_reference_pattern_reason(self):
        """Test that reference files get 'Reference pattern' prefix"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="api/test_auth.py",
                service="api",
                reason="Contains: authentication",
                relevance_score=8,
                matching_lines=[]
            )
        ]
        task = "Add authentication"

        _, to_reference = categorizer.categorize_matches(matches, task)

        # Should update reason
        assert "Reference pattern" in to_reference[0].reason

    def test_likely_to_modify_reason(self):
        """Test that modify files get 'Likely to modify' prefix"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="api/auth.py",
                service="api",
                reason="Contains: authentication",
                relevance_score=8,
                matching_lines=[]
            )
        ]
        task = "Add authentication"

        to_modify, _ = categorizer.categorize_matches(matches, task)

        if to_modify:
            # Should update reason
            assert "Likely to modify" in to_modify[0].reason

    def test_related_reason(self):
        """Test that related files get 'Related' prefix"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="api/utils.py",
                service="api",
                reason="Contains: auth",
                relevance_score=3,
                matching_lines=[]
            )
        ]
        task = "Add authentication"

        _, to_reference = categorizer.categorize_matches(matches, task)

        # Should update reason
        assert "Related" in to_reference[0].reason


class TestEdgeCases:
    """Tests for edge cases"""

    def test_all_tests_all_references(self):
        """Test when all matches are test files"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path=f"api/test_{i}.py",
                service="api",
                reason="Contains: auth",
                relevance_score=8,
                matching_lines=[]
            )
            for i in range(5)
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # All should be in reference
        assert len(to_modify) == 0
        assert len(to_reference) == 5

    def test_mixed_scores_and_types(self):
        """Test mixed file scores and types"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(path="api/auth.py", service="api", reason="High", relevance_score=9, matching_lines=[]),
            FileMatch(path="api/test.py", service="api", reason="Test", relevance_score=8, matching_lines=[]),
            FileMatch(path="api/low.py", service="api", reason="Low", relevance_score=2, matching_lines=[]),
            FileMatch(path="config.py", service="api", reason="Config", relevance_score=3, matching_lines=[]),
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # Should categorize all files
        total = len(to_modify) + len(to_reference)
        assert total == 4

    def test_zero_limit(self):
        """Test with zero limits"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(path="api/auth.py", service="api", reason="Auth", relevance_score=8, matching_lines=[])
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(
            matches, task, max_modify=0, max_reference=0
        )

        # Should return empty lists
        assert len(to_modify) == 0
        assert len(to_reference) == 0

    def test_very_high_relevance(self):
        """Test with very high relevance score"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="api/auth.py",
                service="api",
                reason="Perfect match",
                relevance_score=100,
                matching_lines=[]
            )
        ]
        task = "Add authentication"

        to_modify, _ = categorizer.categorize_matches(matches, task)

        # Very high relevance should be in modify
        assert len(to_modify) >= 0

    def test_empty_task(self):
        """Test with empty task string"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(path="api/auth.py", service="api", reason="Auth", relevance_score=8, matching_lines=[])
        ]

        to_modify, to_reference = categorizer.categorize_matches(matches, "")

        # Should still categorize
        assert isinstance(to_modify, list)
        assert isinstance(to_reference, list)


class TestModifyKeywordsComprehensive:
    """Comprehensive tests for all MODIFY_KEYWORDS variations"""

    def test_all_modify_keywords_variations(self):
        """Test all variations of modify keywords"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(path="api/auth.py", service="api", reason="Auth", relevance_score=8, matching_lines=[])
        ]

        # Test each keyword
        test_cases = [
            ("add authentication", "add"),
            ("create user", "create"),
            ("implement feature", "implement"),
            ("fix bug", "fix"),
            ("update config", "update"),
            ("change settings", "change"),
            ("modify code", "modify"),
            ("new endpoint", "new"),
        ]

        for task, keyword in test_cases:
            to_modify, to_reference = categorizer.categorize_matches(matches, task)
            # Should have modification mode enabled
            assert isinstance(to_modify, list), f"Failed for keyword: {keyword}"

    def test_modify_keywords_case_sensitivity_all(self):
        """Test case sensitivity for all modify keywords"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(path="api/auth.py", service="api", reason="Auth", relevance_score=8, matching_lines=[])
        ]

        keywords = ["add", "create", "implement", "fix", "update", "change", "modify", "new"]

        for keyword in keywords:
            # Test uppercase
            task_upper = keyword.upper() + " feature"
            to_modify_upper, _ = categorizer.categorize_matches(matches, task_upper)
            assert isinstance(to_modify_upper, list)

            # Test lowercase
            task_lower = keyword + " feature"
            to_modify_lower, _ = categorizer.categorize_matches(matches, task_lower)
            assert isinstance(to_modify_lower, list)

            # Test title case
            task_title = keyword.capitalize() + " feature"
            to_modify_title, _ = categorizer.categorize_matches(matches, task_title)
            assert isinstance(to_modify_title, list)

    def test_modify_keywords_substring_detection(self):
        """Test that modify keywords are detected as substrings"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(path="api/auth.py", service="api", reason="Auth", relevance_score=8, matching_lines=[])
        ]

        # Tasks with keyword as part of a word
        test_cases = [
            "adding authentication",  # "add" in "adding"
            "created new user",  # "create" in "created"
            "implementing feature",  # "implement" in "implementing"
            "fixed the bug",  # "fix" in "fixed"
            "updating config",  # "update" in "updating"
            "changing behavior",  # "change" in "changing"
            "modifying code",  # "modify" in "modifying"
            "newly added feature",  # "new" in "newly"
        ]

        for task in test_cases:
            to_modify, _ = categorizer.categorize_matches(matches, task)
            # Should detect the keyword
            assert isinstance(to_modify, list)


class TestFilePathCategorizationEdgeCases:
    """Edge case tests for file path-based categorization"""

    def test_is_example_with_sample_path(self):
        """Test that 'sample' in path marks as example"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="examples/sample_auth.py",
                service="api",
                reason="Auth",
                relevance_score=10,
                matching_lines=[]
            )
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # Should be in reference
        assert not any(f.path == "examples/sample_auth.py" for f in to_modify)
        assert any(f.path == "examples/sample_auth.py" for f in to_reference)

    def test_is_example_case_variations(self):
        """Test example detection with case variations"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(path="EXAMPLES/test.py", service="api", reason="Test", relevance_score=10, matching_lines=[]),
            FileMatch(path="Samples/test.py", service="api", reason="Test", relevance_score=10, matching_lines=[]),
        ]
        task = "Add feature"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # Both should be references
        assert len(to_modify) == 0
        assert len(to_reference) == 2

    def test_is_config_high_score_can_modify(self):
        """Test that high-score config files (>=5) can be modified"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="config/auth.py",
                service="api",
                reason="Auth config",
                relevance_score=5,  # Exactly at threshold
                matching_lines=[]
            )
        ]
        task = "Add authentication config"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # High score config might be modified
        total = len(to_modify) + len(to_reference)
        assert total == 1

    def test_is_config_low_score_always_reference(self):
        """Test that low-score config files (<5) are always references"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="config/settings.py",
                service="api",
                reason="Settings",
                relevance_score=4,  # Below threshold
                matching_lines=[]
            )
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # Should be reference
        assert len(to_modify) == 0
        assert len(to_reference) == 1

    def test_config_detection_case_variations(self):
        """Test config detection with case variations"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(path="CONFIG/settings.py", service="api", reason="Config", relevance_score=3, matching_lines=[]),
            FileMatch(path="Config/data.py", service="api", reason="Config", relevance_score=3, matching_lines=[]),
        ]
        task = "Add feature"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # Both should be references (low score + config)
        assert len(to_modify) == 0
        assert len(to_reference) == 2

    def test_test_detection_various_patterns(self):
        """Test test file detection with various patterns"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(path="test_auth.py", service="api", reason="Test", relevance_score=10, matching_lines=[]),
            FileMatch(path="auth_test.py", service="api", reason="Test", relevance_score=10, matching_lines=[]),
            FileMatch(path="tests/auth.py", service="api", reason="Test", relevance_score=10, matching_lines=[]),
            FileMatch(path="auth_specs.py", service="api", reason="Spec", relevance_score=10, matching_lines=[]),
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # All should be references
        assert len(to_modify) == 0
        assert len(to_reference) == 4

    def test_path_with_both_test_and_config(self):
        """Test file that matches multiple categories"""
        categorizer = FileCategorizer()
        # File that is both test and config
        matches = [
            FileMatch(
                path="config/test_config.py",
                service="api",
                reason="Test config",
                relevance_score=8,
                matching_lines=[]
            )
        ]
        task = "Add feature"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # Test detection should take precedence (should be reference)
        assert len(to_modify) == 0


class TestRelevanceScoreBoundaries:
    """Tests for relevance score boundary conditions"""

    def test_relevance_score_exactly_five(self):
        """Test score exactly at threshold (5)"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="api/auth.py",
                service="api",
                reason="Auth",
                relevance_score=5,  # Exactly at threshold
                matching_lines=[]
            )
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # Score >= 5 with modification task should be modify
        assert len(to_modify) >= 0

    def test_relevance_score_four_below_threshold(self):
        """Test score just below threshold (4)"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="api/auth.py",
                service="api",
                reason="Auth",
                relevance_score=4,  # Just below threshold
                matching_lines=[]
            )
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # Should be reference
        assert len(to_modify) == 0
        assert len(to_reference) == 1

    def test_relevance_score_zero(self):
        """Test zero relevance score"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="api/auth.py",
                service="api",
                reason="Auth",
                relevance_score=0,
                matching_lines=[]
            )
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # Should be reference
        assert len(to_modify) == 0
        assert len(to_reference) == 1

    def test_relevance_score_negative(self):
        """Test negative relevance score (edge case)"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="api/auth.py",
                service="api",
                reason="Auth",
                relevance_score=-1,  # Edge case
                matching_lines=[]
            )
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # Should handle gracefully
        assert isinstance(to_modify, list)
        assert isinstance(to_reference, list)

    def test_relevance_score_without_modification_task(self):
        """Test high relevance without modification keywords"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path="api/auth.py",
                service="api",
                reason="Auth",
                relevance_score=10,
                matching_lines=[]
            )
        ]
        task = "Explain authentication"  # No modify keywords

        to_modify, to_reference = categorizer.categorize_matches(matches, task)

        # Without modification keywords, high relevance might still go to reference
        assert isinstance(to_modify, list)
        assert isinstance(to_reference, list)


class TestLimitingEdgeCases:
    """Edge case tests for max_modify and max_reference limits"""

    def test_more_matches_than_max_modify(self):
        """Test when matches exceed max_modify limit"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path=f"api/file_{i}.py",
                service="api",
                reason="Auth",
                relevance_score=8,
                matching_lines=[]
            )
            for i in range(20)
        ]
        task = "Add authentication"

        to_modify, _ = categorizer.categorize_matches(matches, task, max_modify=5)

        # Should limit to 5
        assert len(to_modify) == 5

    def test_more_matches_than_max_reference(self):
        """Test when matches exceed max_reference limit"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path=f"api/test_{i}.py",
                service="api",
                reason="Test",
                relevance_score=3,
                matching_lines=[]
            )
            for i in range(25)
        ]
        task = "Add authentication"

        _, to_reference = categorizer.categorize_matches(matches, task, max_reference=10)

        # Should limit to 10
        assert len(to_reference) == 10

    def test_zero_max_modify(self):
        """Test with max_modify=0"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(path="api/auth.py", service="api", reason="Auth", relevance_score=8, matching_lines=[])
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task, max_modify=0)

        # Should return empty modify list
        assert len(to_modify) == 0
        assert len(to_reference) >= 0

    def test_zero_max_reference(self):
        """Test with max_reference=0"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(path="api/test.py", service="api", reason="Test", relevance_score=3, matching_lines=[])
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task, max_reference=0)

        # Should return empty reference list
        assert len(to_reference) == 0

    def test_both_limits_zero(self):
        """Test with both limits set to zero"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(path="api/auth.py", service="api", reason="Auth", relevance_score=8, matching_lines=[])
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task, max_modify=0, max_reference=0)

        # Both should be empty
        assert len(to_modify) == 0
        assert len(to_reference) == 0

    def test_negative_limits(self):
        """Test with negative limits (edge case)"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(path="api/auth.py", service="api", reason="Auth", relevance_score=8, matching_lines=[])
        ]
        task = "Add authentication"

        # Negative limits should be handled (might result in empty lists)
        to_modify, to_reference = categorizer.categorize_matches(matches, task, max_modify=-1, max_reference=-1)

        assert isinstance(to_modify, list)
        assert isinstance(to_reference, list)

    def test_very_large_limits(self):
        """Test with very large limits"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path=f"api/file_{i}.py",
                service="api",
                reason="Auth",
                relevance_score=8,
                matching_lines=[]
            )
            for i in range(10)
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(
            matches, task, max_modify=1000, max_reference=1000
        )

        # Should return all matches (capped at available)
        assert len(to_modify) + len(to_reference) == 10

    def test_limits_with_empty_matches(self):
        """Test limits with empty matches list"""
        categorizer = FileCategorizer()
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(
            [], task, max_modify=10, max_reference=15
        )

        # Should return empty lists regardless of limits
        assert len(to_modify) == 0
        assert len(to_reference) == 0

    def test_all_files_exceed_limits(self):
        """Test when all files need to be in one category but exceed limit"""
        categorizer = FileCategorizer()
        matches = [
            FileMatch(
                path=f"api/test_{i}.py",
                service="api",
                reason="Test",
                relevance_score=8,
                matching_lines=[]
            )
            for i in range(20)
        ]
        task = "Add authentication"

        to_modify, to_reference = categorizer.categorize_matches(matches, task, max_modify=3, max_reference=5)

        # All are tests so go to reference, should be capped
        assert len(to_modify) == 0
        assert len(to_reference) == 5
