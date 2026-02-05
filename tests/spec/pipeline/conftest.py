"""
Fixtures for spec.pipeline tests.
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
def temp_specs_dir(tmp_path: Path) -> Path:
    """Create a temporary specs directory."""
    auto_claude = tmp_path / ".auto-claude"
    auto_claude.mkdir(parents=True)
    specs_dir = auto_claude / "specs"
    specs_dir.mkdir(parents=True)
    return specs_dir


@pytest.fixture
def sample_requirements() -> dict[str, Any]:
    """Sample requirements data."""
    return {
        "task_description": "Build a new authentication system",
        "workflow_type": "backend",
        "services_involved": ["api", "database"],
        "user_requirements": [
            "Users should be able to login with email and password",
            "Passwords should be hashed securely",
        ],
        "acceptance_criteria": [
            "Login endpoint returns JWT token",
            "Passwords are hashed using bcrypt",
        ],
        "constraints": [
            "Must use existing user model",
            "JWT secret from environment variable",
        ],
    }


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
def mock_sdk_client():
    """
    Mock Claude SDK client.

    Note: receive_response is a MagicMock that can have its return_value set
    to an async iterator created by create_async_response().

    The code uses `async for msg in client.receive_response():` so tests should:
    1. Create an async iterator: messages = create_async_response([msg1, msg2])
    2. Set it as: mock_sdk_client.receive_response.return_value = messages
    """
    from unittest.mock import AsyncMock
    client = AsyncMock()
    client.query = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()
    # receive_response is a callable that returns an async iterator
    client.receive_response = MagicMock(return_value=create_async_response([]))
    return client
