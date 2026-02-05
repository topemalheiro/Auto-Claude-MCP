"""
Fixtures and configuration for core module tests.
"""

import os
import sys
from pathlib import Path

import pytest


# Set environment variable to prevent io_utils from closing stdout during tests
os.environ["AUTO_CLAUDE_TESTS"] = "1"


def pytest_collection_modifyitems(items):
    """
    Disable pytest capture for io_utils tests.

    The io_utils tests patch sys.stdout and call safe_print which
    calls sys.stdout.close(). This causes pytest's capture fixture
    to fail with "I/O operation on closed file" during teardown.

    We disable capture for these tests to avoid the issue.
    """
    for item in items:
        if "test_io_utils.py" in str(item.fspath):
            item.add_marker(pytest.mark.filterwarnings("ignore::RuntimeWarning"))
            item.add_marker(pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning"))


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
