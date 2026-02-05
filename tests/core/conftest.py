"""
Fixtures and configuration for core module tests.
"""

import os
import sys
from pathlib import Path

import pytest


# Set environment variable to prevent io_utils from closing stdout during tests
os.environ["AUTO_CLAUDE_TESTS"] = "1"


@pytest.fixture(autouse=True)
def reset_pipe_state_for_tests():
    """
    Auto-use fixture to reset pipe state before and after each test.

    Some tests in test_io_utils.py test broken pipe handling which modifies
    the pipe state. This fixture ensures clean state for each test.
    """
    from core.io_utils import reset_pipe_state

    # Reset pipe state before each test
    reset_pipe_state()

    yield

    # Reset pipe state after each test
    reset_pipe_state()
