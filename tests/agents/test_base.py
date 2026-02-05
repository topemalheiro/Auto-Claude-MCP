"""Tests for agents.base module constants and exports."""

import pytest

from agents.base import (
    AUTO_CONTINUE_DELAY_SECONDS,
    HUMAN_INTERVENTION_FILE,
    INITIAL_RETRY_DELAY_SECONDS,
    MAX_CONCURRENCY_RETRIES,
    MAX_RETRY_DELAY_SECONDS,
)


class TestBaseConstants:
    """Test base module constants."""

    def test_auto_continue_delay_seconds(self):
        """Test AUTO_CONTINUE_DELAY_SECONDS is a positive integer."""
        assert isinstance(AUTO_CONTINUE_DELAY_SECONDS, int)
        assert AUTO_CONTINUE_DELAY_SECONDS > 0
        assert AUTO_CONTINUE_DELAY_SECONDS == 3

    def test_human_intervention_file(self):
        """Test HUMAN_INTERVENTION_FILE is correct."""
        assert isinstance(HUMAN_INTERVENTION_FILE, str)
        assert HUMAN_INTERVENTION_FILE == "PAUSE"

    def test_max_concurrency_retries(self):
        """Test MAX_CONCURRENCY_RETRIES is a positive integer."""
        assert isinstance(MAX_CONCURRENCY_RETRIES, int)
        assert MAX_CONCURRENCY_RETRIES > 0
        assert MAX_CONCURRENCY_RETRIES == 5

    def test_initial_retry_delay_seconds(self):
        """Test INITIAL_RETRY_DELAY_SECONDS is a positive integer."""
        assert isinstance(INITIAL_RETRY_DELAY_SECONDS, int)
        assert INITIAL_RETRY_DELAY_SECONDS > 0
        assert INITIAL_RETRY_DELAY_SECONDS == 2

    def test_max_retry_delay_seconds(self):
        """Test MAX_RETRY_DELAY_SECONDS is reasonable."""
        assert isinstance(MAX_RETRY_DELAY_SECONDS, int)
        assert MAX_RETRY_DELAY_SECONDS > 0
        assert MAX_RETRY_DELAY_SECONDS == 32

    def test_retry_delays_relationship(self):
        """Test that retry delay values are consistent."""
        # Max should be >= initial
        assert MAX_RETRY_DELAY_SECONDS >= INITIAL_RETRY_DELAY_SECONDS
        # With exponential doubling (2, 4, 8, 16, 32), max should be 2^MAX_RETRIES
        assert MAX_RETRY_DELAY_SECONDS == INITIAL_RETRY_DELAY_SECONDS * (2 ** (MAX_CONCURRENCY_RETRIES - 1))
