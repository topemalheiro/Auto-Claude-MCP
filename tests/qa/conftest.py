"""
Fixtures for QA tests.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from typing import Any

import pytest


def _create_message_class(msg_type: str) -> type:
    """Create a message class with the correct type name."""
    class Message:
        def __init__(self, content: list | None = None, is_error: bool = False):
            self.content = content or []
            self.is_error = is_error
    Message.__name__ = msg_type
    return Message


def _create_block_class(block_type: str) -> type:
    """Create a block class with the correct type name."""
    class Block:
        def __init__(self, text: str | None = None, name: str | None = None,
                     input_data: dict | None = None, is_error: bool = False,
                     content: str | None = None):
            if text is not None:
                self.text = text
            if name is not None:
                self.name = name
            if input_data is not None:
                self.input = input_data
            if is_error:
                self.is_error = is_error
            if content is not None:
                self.content = content
    Block.__name__ = block_type
    return Block


class MockMessage:
    """Mock message factory for SDK client."""

    def __new__(cls, msg_type: str, content: list | None = None, is_error: bool = False):
        msg_class = _create_message_class(msg_type)
        return msg_class(content, is_error)


class MockBlock:
    """Mock content block factory for SDK messages."""

    def __new__(cls, block_type: str, text: str | None = None, name: str | None = None,
               input_data: dict | None = None, is_error: bool = False,
               content: str | None = None):
        block_class = _create_block_class(block_type)
        return block_class(text, name, input_data, is_error, content)


def create_async_response(messages: list) -> Any:
    """
    Create an async iterable mock for SDK client responses.

    This is needed because the SDK uses async for to iterate over messages.
    """
    class AsyncIteratorMock:
        def __init__(self, items):
            self.items = items
            self.index = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.index >= len(self.items):
                raise StopAsyncIteration
            item = self.items[self.index]
            self.index += 1
            return item

    return AsyncIteratorMock(messages)


def create_async_response_exception(error: Exception) -> Any:
    """
    Create an async iterable mock that raises an exception during iteration.

    This is needed to test exception handling in async for loops.
    """
    class AsyncIteratorExceptionMock:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise error

    return AsyncIteratorExceptionMock()


@pytest.fixture
def temp_spec_dir(tmp_path: Path) -> Path:
    """Create a temporary spec directory with necessary files."""
    spec_dir = tmp_path / ".auto-claude" / "specs" / "001-test"
    spec_dir.mkdir(parents=True)
    return spec_dir


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory."""
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True)
    return project_dir


@pytest.fixture
def sample_implementation_plan() -> dict[str, Any]:
    """Sample implementation plan data."""
    return {
        "title": "Test Feature",
        "description": "Test feature description",
        "subtasks": [
            {
                "id": "1",
                "title": "Subtask 1",
                "status": "complete",
                "files": ["test.py"],
            },
            {
                "id": "2",
                "title": "Subtask 2",
                "status": "complete",
                "files": ["test2.py"],
            },
        ],
        "qa_signoff": {
            "status": "pending",
            "qa_session": 0,
        },
        "qa_iteration_history": [],
        "qa_stats": {},
    }


@pytest.fixture
def approved_plan(sample_implementation_plan: dict[str, Any]) -> dict[str, Any]:
    """Implementation plan with approved status."""
    plan = sample_implementation_plan.copy()
    plan["qa_signoff"] = {
        "status": "approved",
        "timestamp": "2024-01-01T00:00:00Z",
        "qa_session": 1,
        "report_file": "qa_report.md",
        "tests_passed": {"unit": "10/10", "integration": "5/5", "e2e": "2/2"},
        "verified_by": "qa_agent",
    }
    return plan


@pytest.fixture
def rejected_plan(sample_implementation_plan: dict[str, Any]) -> dict[str, Any]:
    """Implementation plan with rejected status."""
    plan = sample_implementation_plan.copy()
    plan["qa_signoff"] = {
        "status": "rejected",
        "timestamp": "2024-01-01T00:00:00Z",
        "qa_session": 1,
        "issues_found": [
            {
                "type": "critical",
                "title": "Test failure",
                "location": "test.py:10",
                "fix_required": "Fix the test",
            },
            {
                "type": "minor",
                "title": "Style issue",
                "location": "test2.py:5",
                "fix_required": "Fix the style",
            },
        ],
        "fix_request_file": "QA_FIX_REQUEST.md",
    }
    return plan


@pytest.fixture
def sample_issues() -> list[dict[str, Any]]:
    """Sample QA issues."""
    return [
        {
            "type": "critical",
            "title": "Test failure in auth module",
            "file": "auth.py",
            "line": 42,
            "location": "auth.py:42",
            "fix_required": "Fix authentication logic",
            "description": "Authentication fails when using invalid credentials",
        },
        {
            "type": "minor",
            "title": "Missing error handling",
            "file": "utils.py",
            "line": 15,
            "location": "utils.py:15",
            "fix_required": "Add error handling",
            "description": "Function should handle edge cases",
        },
    ]


@pytest.fixture
def iteration_history() -> list[dict[str, Any]]:
    """Sample iteration history."""
    return [
        {
            "iteration": 1,
            "status": "rejected",
            "timestamp": "2024-01-01T00:00:00Z",
            "issues": [
                {
                    "type": "critical",
                    "title": "Test failure in auth module",
                    "file": "auth.py",
                    "line": 42,
                },
            ],
            "duration_seconds": 45.5,
        },
        {
            "iteration": 2,
            "status": "rejected",
            "timestamp": "2024-01-01T01:00:00Z",
            "issues": [
                {
                    "type": "critical",
                    "title": "Test failure in auth module",  # Same issue recurring
                    "file": "auth.py",
                    "line": 42,
                },
            ],
            "duration_seconds": 30.2,
        },
    ]


@pytest.fixture
def mock_sdk_client() -> MagicMock:
    """
    Mock Claude SDK client.

    Note: receive_response is NOT an AsyncMock because the code uses
    `async for msg in client.receive_response():` which expects an async iterator.
    Tests should set client.receive_response.return_value to an async iterator
    created by create_async_response().
    """
    client = MagicMock()
    client.query = AsyncMock()
    # receive_response should return an async iterator, set via return_value in tests
    client.receive_response = MagicMock()
    return client


@pytest.fixture
def mock_task_logger() -> MagicMock:
    """Mock task logger."""
    logger = MagicMock()
    logger.log = MagicMock()
    logger.tool_start = MagicMock()
    logger.tool_end = MagicMock()
    logger.log_error = MagicMock()
    logger.start_phase = MagicMock()
    logger.end_phase = MagicMock()
    return logger


@pytest.fixture
def mock_task_event_emitter() -> MagicMock:
    """Mock task event emitter."""
    emitter = MagicMock()
    emitter.emit = MagicMock()
    return emitter


def create_spec_files(
    spec_dir: Path,
    implementation_plan: dict[str, Any] | None = None,
    qa_report: str | None = None,
    fix_request: str | None = None,
) -> None:
    """Helper to create spec directory files."""
    # Create implementation_plan.json
    if implementation_plan is not None:
        plan_file = spec_dir / "implementation_plan.json"
        with open(plan_file, "w") as f:
            json.dump(implementation_plan, f)

    # Create qa_report.md
    if qa_report is not None:
        report_file = spec_dir / "qa_report.md"
        report_file.write_text(qa_report)

    # Create QA_FIX_REQUEST.md
    if fix_request is not None:
        fix_file = spec_dir / "QA_FIX_REQUEST.md"
        fix_file.write_text(fix_request)
