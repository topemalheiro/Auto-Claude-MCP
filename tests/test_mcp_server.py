"""
Tests for mcp_server/server.py
===============================

Tests that the MCP server instance is configured correctly and
all tools are registered.
"""

import sys
from pathlib import Path

# Add backend to sys.path
_backend = Path(__file__).parent.parent / "apps" / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

# Pre-mock SDK modules before any mcp_server imports
from unittest.mock import MagicMock

if "claude_agent_sdk" not in sys.modules:
    sys.modules["claude_agent_sdk"] = MagicMock()
    sys.modules["claude_agent_sdk.types"] = MagicMock()

# Mock heavy backend dependencies that tool modules import
_modules_to_mock = [
    "cli.utils",
    "core.client",
    "core.auth",
    "core.worktree",
    "agents",
    "agents.planner",
    "agents.coder",
    "agents.session",
    "qa",
    "qa.reviewer",
    "qa.fixer",
    "qa.loop",
    "qa.criteria",
    "spec",
    "spec.pipeline",
    "context",
    "context.builder",
    "context.search",
    "runners",
    "runners.spec_runner",
    "runners.roadmap",
    "runners.insights",
    "runners.github",
    "runners.github.services",
    "runners.github.services.parallel_orchestrator_reviewer",
    "services",
    "services.recovery",
    "integrations",
    "integrations.graphiti",
    "integrations.github",
    "project",
    "project.analysis",
    "merge",
]
for mod_name in _modules_to_mock:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()


class TestMCPServerInstance:
    """Tests for the MCP server instance."""

    def test_mcp_instance_exists(self):
        """The mcp server instance is created."""
        from mcp_server.server import mcp

        assert mcp is not None

    def test_mcp_instance_name(self):
        """The mcp server has the correct name."""
        from mcp_server.server import mcp

        assert mcp.name == "Auto Claude"


class TestRegisterAllTools:
    """Tests for register_all_tools()."""

    def test_register_all_tools_registers_43_tools(self):
        """register_all_tools() registers exactly 43 tools."""
        from mcp_server.server import mcp, register_all_tools

        register_all_tools()

        # FastMCP stores tools in _tool_manager._tools dict
        tool_count = len(mcp._tool_manager._tools)
        assert tool_count == 43, (
            f"Expected 43 tools, got {tool_count}. "
            f"Tools: {sorted(mcp._tool_manager._tools.keys())}"
        )

    def test_register_all_tools_idempotent(self):
        """Calling register_all_tools() multiple times doesn't duplicate tools."""
        from mcp_server.server import mcp, register_all_tools

        register_all_tools()
        count_first = len(mcp._tool_manager._tools)

        register_all_tools()
        count_second = len(mcp._tool_manager._tools)

        assert count_first == count_second
