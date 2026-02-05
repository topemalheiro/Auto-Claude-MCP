"""Tests for agents.tools_pkg.permissions module."""

from pathlib import Path
from unittest.mock import patch
import pytest
import os

from agents.tools_pkg.permissions import (
    get_allowed_tools,
    get_all_agent_types,
    _get_mcp_tools_for_servers,
)
from agents.tools_pkg.models import AGENT_CONFIGS


class TestGetAllowedTools:
    """Test get_allowed_tools function."""

    def test_returns_tools_for_valid_agent_type(self):
        """Test that tools are returned for valid agent types."""
        tools = get_allowed_tools("coder")

        assert isinstance(tools, list)
        assert len(tools) > 0
        # Coder should have base tools
        assert "Read" in tools
        assert "Write" in tools

    def test_raises_error_for_unknown_agent_type(self):
        """Test that ValueError is raised for unknown agent type."""
        with pytest.raises(ValueError, match="Unknown agent type"):
            get_allowed_tools("unknown_agent_type")

    def test_includes_base_tools(self):
        """Test that base tools are included."""
        tools = get_allowed_tools("planner")

        assert "Read" in tools
        assert "Write" in tools
        assert "Bash" in tools

    def test_includes_web_tools(self):
        """Test that web tools are included."""
        tools = get_allowed_tools("coder")

        assert "WebFetch" in tools
        assert "WebSearch" in tools

    def test_includes_context7_tools(self):
        """Test that Context7 tools are included by default."""
        tools = get_allowed_tools("coder")

        assert "mcp__context7__resolve-library-id" in tools
        assert "mcp__context7__get-library-docs" in tools

    def test_filters_context7_when_disabled(self):
        """Test that Context7 tools can be filtered via mcp_config."""
        tools = get_allowed_tools(
            "coder",
            mcp_config={"CONTEXT7_ENABLED": "false"}
        )

        assert "mcp__context7__resolve-library-id" not in tools

    def test_respects_auto_claude_tools(self):
        """Test that auto-claude tools are included when available."""
        with patch("agents.tools_pkg.permissions.is_tools_available", return_value=True):
            tools = get_allowed_tools("coder")

            # Should have some auto-claude tools
            assert any(t.startswith("mcp__auto-claude__") for t in tools)

    def test_excludes_auto_claude_when_unavailable(self):
        """Test that auto-claude tools are excluded when unavailable."""
        with patch("agents.tools_pkg.permissions.is_tools_available", return_value=False):
            tools = get_allowed_tools("coder")

            # Should NOT have auto-claude tools
            assert not any(t.startswith("mcp__auto-claude__") for t in tools)

    def test_includes_linear_when_enabled(self):
        """Test that Linear tools are included when enabled."""
        tools = get_allowed_tools(
            "coder",
            linear_enabled=True
        )

        assert "mcp__linear-server__list_teams" in tools

    def test_excludes_linear_when_disabled(self):
        """Test that Linear tools are excluded when disabled."""
        tools = get_allowed_tools(
            "coder",
            linear_enabled=False
        )

        assert "mcp__linear-server__list_teams" not in tools

    def test_includes_electron_when_electron_project(self):
        """Test that Electron tools are included for Electron projects."""
        tools = get_allowed_tools(
            "qa_reviewer",
            project_capabilities={"is_electron": True},
            mcp_config={"ELECTRON_MCP_ENABLED": "true"}
        )

        assert "mcp__electron__get_electron_window_info" in tools

    def test_includes_puppeteer_when_web_project(self):
        """Test that Puppeteer tools are included for web projects."""
        tools = get_allowed_tools(
            "qa_reviewer",
            project_capabilities={"is_electron": False, "is_web_frontend": True},
            mcp_config={"PUPPETEER_MCP_ENABLED": "true"}
        )

        assert "mcp__puppeteer__puppeteer_connect_active_tab" in tools

    def test_filters_graphiti_when_disabled(self):
        """Test that Graphiti tools are filtered when not enabled."""
        # Clear the env var if set
        original = os.environ.get("GRAPHITI_MCP_URL")
        if "GRAPHITI_MCP_URL" in os.environ:
            del os.environ["GRAPHITI_MCP_URL"]

        try:
            tools = get_allowed_tools("coder")

            # Should NOT have graphiti tools when env var not set
            assert "mcp__graphiti-memory__search_nodes" not in tools
        finally:
            if original:
                os.environ["GRAPHITI_MCP_URL"] = original


class TestGetMcpToolsForServers:
    """Test _get_mcp_tools_for_servers function."""

    def test_maps_context7_server(self):
        """Test mapping of context7 server."""
        tools = _get_mcp_tools_for_servers(["context7"])

        assert "mcp__context7__resolve-library-id" in tools
        assert "mcp__context7__get-library-docs" in tools

    def test_maps_linear_server(self):
        """Test mapping of linear server."""
        tools = _get_mcp_tools_for_servers(["linear"])

        assert "mcp__linear-server__list_teams" in tools
        assert "mcp__linear-server__get_team" in tools

    def test_maps_graphiti_server(self):
        """Test mapping of graphiti server."""
        tools = _get_mcp_tools_for_servers(["graphiti"])

        assert "mcp__graphiti-memory__search_nodes" in tools
        assert "mcp__graphiti-memory__add_episode" in tools

    def test_maps_electron_server(self):
        """Test mapping of electron server."""
        tools = _get_mcp_tools_for_servers(["electron"])

        assert "mcp__electron__get_electron_window_info" in tools
        assert "mcp__electron__take_screenshot" in tools

    def test_maps_puppeteer_server(self):
        """Test mapping of puppeteer server."""
        tools = _get_mcp_tools_for_servers(["puppeteer"])

        assert "mcp__puppeteer__puppeteer_connect_active_tab" in tools
        assert "mcp__puppeteer__puppeteer_navigate" in tools

    def test_combines_multiple_servers(self):
        """Test combining tools from multiple servers."""
        tools = _get_mcp_tools_for_servers(["context7", "linear"])

        # Should have tools from both servers
        assert "mcp__context7__resolve-library-id" in tools
        assert "mcp__linear-server__list_teams" in tools


class TestGetAllAgentTypes:
    """Test get_all_agent_types function."""

    def test_returns_all_registered_agent_types(self):
        """Test that all agent types are returned."""
        agent_types = get_all_agent_types()

        assert isinstance(agent_types, list)
        assert len(agent_types) > 0

        # Check for some known agent types
        assert "coder" in agent_types
        assert "planner" in agent_types
        assert "qa_reviewer" in agent_types
        assert "qa_fixer" in agent_types

    def test_returns_sorted_list(self):
        """Test that agent types are sorted alphabetically."""
        agent_types = get_all_agent_types()

        # Check if sorted
        assert agent_types == sorted(agent_types)

    def test_includes_spec_creation_phases(self):
        """Test that spec creation phases are included."""
        agent_types = get_all_agent_types()

        assert "spec_gatherer" in agent_types
        assert "spec_researcher" in agent_types
        assert "spec_writer" in agent_types
        assert "spec_critic" in agent_types

    def test_includes_utility_phases(self):
        """Test that utility phases are included."""
        agent_types = get_all_agent_types()

        assert "insights" in agent_types
        assert "merge_resolver" in agent_types
        assert "commit_message" in agent_types
        assert "pr_template_filler" in agent_types
