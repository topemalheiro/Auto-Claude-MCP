"""
Pytest configuration and fixtures for Linear integration tests.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# Mock claude_agent_sdk at module level to allow importing Linear modules
# This needs to be done before any imports from integrations.linear
mock_sdk = MagicMock()
mock_claude_agent_options = MagicMock()
mock_claude_sdk_client = MagicMock()

sys.modules["claude_agent_sdk"] = mock_sdk
sys.modules["claude_agent_sdk"].ClaudeAgentOptions = mock_claude_agent_options
sys.modules["claude_agent_sdk"].ClaudeSDKClient = mock_claude_sdk_client

# Also mock the types submodule (needed by core.client.py)
mock_types = MagicMock()
mock_types.HookMatcher = MagicMock()
sys.modules["claude_agent_sdk.types"] = mock_types
sys.modules["claude_agent_sdk"].types = mock_types


@pytest.fixture
def temp_spec_dir(tmp_path: Path) -> Path:
    """Create a temporary spec directory for testing."""
    spec_dir = tmp_path / "specs" / "001-test"
    spec_dir.mkdir(parents=True)
    return spec_dir


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory for testing."""
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True)
    return project_dir


@pytest.fixture
def mock_linear_api_key():
    """Fixture that mocks LINEAR_API_KEY environment variable."""
    with patch.dict("os.environ", {"LINEAR_API_KEY": "test-linear-api-key"}):
        yield "test-linear-api-key"


@pytest.fixture
def without_linear_api_key():
    """Fixture that ensures LINEAR_API_KEY is not set."""
    with patch.dict("os.environ", {}, clear=True):
        yield
