"""Comprehensive tests for schema.py module."""

import pytest

from integrations.graphiti.queries_pkg.schema import (
    EPISODE_TYPE_SESSION_INSIGHT,
    EPISODE_TYPE_CODEBASE_DISCOVERY,
    EPISODE_TYPE_PATTERN,
    EPISODE_TYPE_GOTCHA,
    EPISODE_TYPE_TASK_OUTCOME,
    EPISODE_TYPE_QA_RESULT,
    EPISODE_TYPE_HISTORICAL_CONTEXT,
    MAX_CONTEXT_RESULTS,
    MAX_RETRIES,
    RETRY_DELAY_SECONDS,
    GroupIdMode,
)


class TestEpisodeTypeConstants:
    """Tests for episode type constants."""

    def test_session_insight_constant(self):
        """Test EPISODE_TYPE_SESSION_INSIGHT value."""
        assert EPISODE_TYPE_SESSION_INSIGHT == "session_insight"

    def test_codebase_discovery_constant(self):
        """Test EPISODE_TYPE_CODEBASE_DISCOVERY value."""
        assert EPISODE_TYPE_CODEBASE_DISCOVERY == "codebase_discovery"

    def test_pattern_constant(self):
        """Test EPISODE_TYPE_PATTERN value."""
        assert EPISODE_TYPE_PATTERN == "pattern"

    def test_gotcha_constant(self):
        """Test EPISODE_TYPE_GOTCHA value."""
        assert EPISODE_TYPE_GOTCHA == "gotcha"

    def test_task_outcome_constant(self):
        """Test EPISODE_TYPE_TASK_OUTCOME value."""
        assert EPISODE_TYPE_TASK_OUTCOME == "task_outcome"

    def test_qa_result_constant(self):
        """Test EPISODE_TYPE_QA_RESULT value."""
        assert EPISODE_TYPE_QA_RESULT == "qa_result"

    def test_historical_context_constant(self):
        """Test EPISODE_TYPE_HISTORICAL_CONTEXT value."""
        assert EPISODE_TYPE_HISTORICAL_CONTEXT == "historical_context"


class TestConfigurationConstants:
    """Tests for configuration constants."""

    def test_max_context_results(self):
        """Test MAX_CONTEXT_RESULTS value."""
        assert MAX_CONTEXT_RESULTS == 10

    def test_max_retries(self):
        """Test MAX_RETRIES value."""
        assert MAX_RETRIES == 2

    def test_retry_delay_seconds(self):
        """Test RETRY_DELAY_SECONDS value."""
        assert RETRY_DELAY_SECONDS == 1


class TestGroupIdMode:
    """Tests for GroupIdMode class."""

    def test_spec_mode_value(self):
        """Test GroupIdMode.SPEC value."""
        assert GroupIdMode.SPEC == "spec"

    def test_project_mode_value(self):
        """Test GroupIdMode.PROJECT value."""
        assert GroupIdMode.PROJECT == "project"

    def test_modes_are_strings(self):
        """Test that mode values are strings."""
        assert isinstance(GroupIdMode.SPEC, str)
        assert isinstance(GroupIdMode.PROJECT, str)

    def test_modes_are_different(self):
        """Test that SPEC and PROJECT modes are different."""
        assert GroupIdMode.SPEC != GroupIdMode.PROJECT
