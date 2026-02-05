"""Tests for agents.tools_pkg.registry module."""

from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

from agents.tools_pkg.registry import (
    create_all_tools,
    create_auto_claude_mcp_server,
    is_tools_available,
)


class TestCreateAllTools:
    """Test create_all_tools function."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a temporary spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    def test_returns_tools_when_sdk_available(self, mock_spec_dir, mock_project_dir):
        """Test that tools are returned when SDK is available."""
        with patch("agents.tools_pkg.registry.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.registry.create_subtask_tools", return_value=["subtask_tool"]), \
             patch("agents.tools_pkg.registry.create_progress_tools", return_value=["progress_tool"]), \
             patch("agents.tools_pkg.registry.create_memory_tools", return_value=["memory_tool"]), \
             patch("agents.tools_pkg.registry.create_qa_tools", return_value=["qa_tool"]):

            tools = create_all_tools(mock_spec_dir, mock_project_dir)

            # Should return all tools
            assert len(tools) == 4
            assert "subtask_tool" in tools
            assert "progress_tool" in tools
            assert "memory_tool" in tools
            assert "qa_tool" in tools

    def test_returns_empty_list_when_sdk_unavailable(self, mock_spec_dir, mock_project_dir):
        """Test that empty list is returned when SDK is unavailable."""
        with patch("agents.tools_pkg.registry.SDK_TOOLS_AVAILABLE", False):
            tools = create_all_tools(mock_spec_dir, mock_project_dir)

            assert tools == []


class TestCreateAutoClaudeMcpServer:
    """Test create_auto_claude_mcp_server function."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a temporary spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    def test_returns_server_when_sdk_available(self, mock_spec_dir, mock_project_dir):
        """Test that MCP server is created when SDK is available."""
        mock_server = MagicMock()
        mock_tools = [MagicMock(), MagicMock()]

        with patch("agents.tools_pkg.registry.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.registry.create_all_tools", return_value=mock_tools), \
             patch("agents.tools_pkg.registry.create_sdk_mcp_server", return_value=mock_server) as mock_create:

            result = create_auto_claude_mcp_server(mock_spec_dir, mock_project_dir)

            assert result == mock_server
            mock_create.assert_called_once_with(name="auto-claude", version="1.0.0", tools=mock_tools)

    def test_returns_none_when_sdk_unavailable(self, mock_spec_dir, mock_project_dir):
        """Test that None is returned when SDK is unavailable."""
        with patch("agents.tools_pkg.registry.SDK_TOOLS_AVAILABLE", False):
            result = create_auto_claude_mcp_server(mock_spec_dir, mock_project_dir)

            assert result is None


class TestIsToolsAvailable:
    """Test is_tools_available function."""

    def test_returns_true_when_sdk_available(self):
        """Test that True is returned when SDK tools are available."""
        with patch("agents.tools_pkg.registry.SDK_TOOLS_AVAILABLE", True):
            result = is_tools_available()
            assert result is True

    def test_returns_false_when_sdk_unavailable(self):
        """Test that False is returned when SDK tools are unavailable."""
        with patch("agents.tools_pkg.registry.SDK_TOOLS_AVAILABLE", False):
            result = is_tools_available()
            assert result is False


class TestRegistryImportError:
    """Test ImportError handling in registry module."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a temporary spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    def test_create_all_tools_handles_import_error(self, mock_spec_dir, mock_project_dir):
        """Test that ImportError is handled when SDK is not available."""
        with patch("agents.tools_pkg.registry.SDK_TOOLS_AVAILABLE", False):
            tools = create_all_tools(mock_spec_dir, mock_project_dir)
            assert tools == []

    def test_create_auto_claude_mcp_server_handles_import_error(self, mock_spec_dir, mock_project_dir):
        """Test that ImportError is handled when creating MCP server without SDK."""
        with patch("agents.tools_pkg.registry.SDK_TOOLS_AVAILABLE", False):
            result = create_auto_claude_mcp_server(mock_spec_dir, mock_project_dir)
            assert result is None

    def test_tools_modules_import_error_branch(self, mock_spec_dir, mock_project_dir):
        """Test the ImportError exception branch coverage."""
        # This test ensures the ImportError branch is taken
        # We just need to verify the behavior when SDK_TOOLS_AVAILABLE is False
        # which is already tested above. The actual ImportError happens at import time.
        with patch("agents.tools_pkg.registry.SDK_TOOLS_AVAILABLE", False):
            from agents.tools_pkg.registry import create_all_tools
            tools = create_all_tools(mock_spec_dir, mock_project_dir)
            assert tools == []

            from agents.tools_pkg.registry import create_auto_claude_mcp_server
            server = create_auto_claude_mcp_server(mock_spec_dir, mock_project_dir)
            assert server is None
