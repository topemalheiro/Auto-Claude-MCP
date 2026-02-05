"""Tests for agents.tools_pkg.models module."""

import os
from pathlib import Path
from unittest.mock import patch
import pytest

from agents.tools_pkg.models import (
    is_electron_mcp_enabled,
    get_agent_config,
    get_required_mcp_servers,
    get_default_thinking_level,
    _map_mcp_server_name,
    AGENT_CONFIGS,
    # Test constants
    BASE_READ_TOOLS,
    BASE_WRITE_TOOLS,
    WEB_TOOLS,
    CONTEXT7_TOOLS,
    LINEAR_TOOLS,
    GRAPHITI_MCP_TOOLS,
    PUPPETEER_TOOLS,
    ELECTRON_TOOLS,
)


class TestIsElectronMcpEnabled:
    """Test is_electron_mcp_enabled function."""

    def test_returns_true_when_env_var_set(self):
        """Test that True is returned when env var is set to 'true'."""
        with patch.dict(os.environ, {"ELECTRON_MCP_ENABLED": "true"}):
            result = is_electron_mcp_enabled()
            assert result is True

    def test_returns_true_when_env_var_set_uppercase(self):
        """Test that True is returned when env var is set to 'TRUE'."""
        with patch.dict(os.environ, {"ELECTRON_MCP_ENABLED": "TRUE"}):
            result = is_electron_mcp_enabled()
            assert result is True

    def test_returns_true_when_env_var_set_mixed_case(self):
        """Test that True is returned when env var is set to 'True'."""
        with patch.dict(os.environ, {"ELECTRON_MCP_ENABLED": "True"}):
            result = is_electron_mcp_enabled()
            assert result is True

    def test_returns_false_when_env_var_not_set(self):
        """Test that False is returned when env var is not set."""
        # Ensure env var is not set
        with patch.dict(os.environ, {}, clear=True):
            result = is_electron_mcp_enabled()
            assert result is False

    def test_returns_false_when_env_var_set_to_false(self):
        """Test that False is returned when env var is set to 'false'."""
        with patch.dict(os.environ, {"ELECTRON_MCP_ENABLED": "false"}):
            result = is_electron_mcp_enabled()
            assert result is False

    def test_returns_false_when_env_var_set_to_other_value(self):
        """Test that False is returned when env var is set to other values."""
        with patch.dict(os.environ, {"ELECTRON_MCP_ENABLED": "yes"}):
            result = is_electron_mcp_enabled()
            assert result is False

    def test_returns_false_when_env_var_set_to_zero(self):
        """Test that False is returned when env var is set to '0'."""
        with patch.dict(os.environ, {"ELECTRON_MCP_ENABLED": "0"}):
            result = is_electron_mcp_enabled()
            assert result is False


class TestAgentConfigsDictionary:
    """Test AGENT_CONFIGS dictionary structure and validation."""

    def test_all_configs_have_required_keys(self):
        """Test that all agent configs have required keys."""
        required_keys = {"tools", "mcp_servers", "auto_claude_tools", "thinking_default"}

        for agent_type, config in AGENT_CONFIGS.items():
            for key in required_keys:
                assert key in config, f"Agent '{agent_type}' missing key '{key}'"

    def test_all_tools_are_lists(self):
        """Test that all tools entries are lists."""
        for agent_type, config in AGENT_CONFIGS.items():
            assert isinstance(config["tools"], list), f"Agent '{agent_type}' tools must be a list"
            assert isinstance(config["mcp_servers"], list), f"Agent '{agent_type}' mcp_servers must be a list"
            assert isinstance(config["auto_claude_tools"], list), f"Agent '{agent_type}' auto_claude_tools must be a list"

    def test_thinking_default_has_valid_values(self):
        """Test that all thinking_default values are valid."""
        valid_levels = {"none", "low", "medium", "high", "ultrathink"}

        for agent_type, config in AGENT_CONFIGS.items():
            thinking = config["thinking_default"]
            assert thinking in valid_levels, f"Agent '{agent_type}' has invalid thinking_default: {thinking}"

    def test_spec_creation_agents_have_minimal_tools(self):
        """Test that spec creation agents don't have heavy MCP servers."""
        spec_agents = ["spec_gatherer", "spec_researcher", "spec_writer", "spec_critic"]

        for agent_type in spec_agents:
            config = AGENT_CONFIGS[agent_type]
            # Spec agents shouldn't need graphiti or linear
            assert "graphiti" not in config["mcp_servers"], f"Agent '{agent_type}' shouldn't have graphiti"
            assert "linear" not in config["mcp_servers"], f"Agent '{agent_type}' shouldn't have linear"

    def test_qa_agents_have_browser_server(self):
        """Test that QA agents have browser in mcp_servers."""
        qa_agents = ["qa_reviewer", "qa_fixer"]

        for agent_type in qa_agents:
            config = AGENT_CONFIGS[agent_type]
            assert "browser" in config["mcp_servers"], f"Agent '{agent_type}' should have browser"

    def test_build_agents_have_auto_claude_server(self):
        """Test that build phase agents have auto-claude in mcp_servers."""
        build_agents = ["planner", "coder", "qa_reviewer", "qa_fixer"]

        for agent_type in build_agents:
            config = AGENT_CONFIGS[agent_type]
            assert "auto-claude" in config["mcp_servers"], f"Agent '{agent_type}' should have auto-claude"

    def test_linear_is_optional_for_build_agents(self):
        """Test that linear is in optional servers for build agents."""
        build_agents = ["planner", "coder", "qa_reviewer", "qa_fixer"]

        for agent_type in build_agents:
            config = AGENT_CONFIGS[agent_type]
            optional = config.get("mcp_servers_optional", [])
            assert "linear" in optional, f"Agent '{agent_type}' should have linear as optional"


class TestGetAgentConfig:
    """Test get_agent_config function."""

    def test_returns_config_for_valid_agent_type(self):
        """Test that config is returned for valid agent type."""
        config = get_agent_config("coder")

        assert config is not None
        assert isinstance(config, dict)
        assert "tools" in config
        assert "mcp_servers" in config
        assert "thinking_default" in config

    def test_raises_error_for_unknown_agent_type(self):
        """Test that ValueError is raised for unknown agent type."""
        with pytest.raises(ValueError, match="Unknown agent type"):
            get_agent_config("unknown_agent_type")

    def test_includes_error_message_with_valid_types(self):
        """Test that error message includes list of valid types."""
        with pytest.raises(ValueError) as exc_info:
            get_agent_config("unknown_type")

        error_msg = str(exc_info.value)
        assert "coder" in error_msg
        assert "planner" in error_msg
        assert "unknown_type" in error_msg

    def test_returns_config_for_all_spec_agents(self):
        """Test that config is returned for all spec agent types."""
        spec_agents = [
            "spec_gatherer",
            "spec_researcher",
            "spec_writer",
            "spec_critic",
            "spec_discovery",
            "spec_context",
            "spec_validation",
            "spec_compaction",
        ]

        for agent_type in spec_agents:
            config = get_agent_config(agent_type)
            assert config is not None
            assert isinstance(config, dict)

    def test_returns_config_for_all_build_agents(self):
        """Test that config is returned for all build agent types."""
        build_agents = ["planner", "coder", "qa_reviewer", "qa_fixer"]

        for agent_type in build_agents:
            config = get_agent_config(agent_type)
            assert config is not None
            assert isinstance(config, dict)

    def test_returns_config_for_utility_agents(self):
        """Test that config is returned for utility agent types."""
        utility_agents = [
            "insights",
            "merge_resolver",
            "commit_message",
            "pr_template_filler",
            "pr_reviewer",
            "pr_orchestrator_parallel",
            "pr_followup_parallel",
            "pr_finding_validator",
        ]

        for agent_type in utility_agents:
            config = get_agent_config(agent_type)
            assert config is not None
            assert isinstance(config, dict)

    def test_returns_config_for_analysis_agents(self):
        """Test that config is returned for analysis agent types."""
        analysis_agents = ["analysis", "batch_analysis", "batch_validation"]

        for agent_type in analysis_agents:
            config = get_agent_config(agent_type)
            assert config is not None
            assert isinstance(config, dict)

    def test_returns_config_for_roadmap_agents(self):
        """Test that config is returned for roadmap agent types."""
        roadmap_agents = [
            "roadmap_discovery",
            "competitor_analysis",
            "ideation",
        ]

        for agent_type in roadmap_agents:
            config = get_agent_config(agent_type)
            assert config is not None
            assert isinstance(config, dict)


class TestGetRequiredMcpServers:
    """Test get_required_mcp_servers function."""

    def test_returns_servers_for_coder(self):
        """Test that correct servers are returned for coder."""
        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config=None
        )

        assert isinstance(servers, list)
        # Should include context7 and graphiti (if enabled)
        assert "context7" in servers
        assert "auto-claude" in servers

    def test_returns_servers_for_planner(self):
        """Test that correct servers are returned for planner."""
        servers = get_required_mcp_servers(
            "planner",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config=None
        )

        assert isinstance(servers, list)
        assert "auto-claude" in servers

    def test_returns_servers_for_qa_reviewer(self):
        """Test that correct servers are returned for qa_reviewer."""
        servers = get_required_mcp_servers(
            "qa_reviewer",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config=None
        )

        assert isinstance(servers, list)
        # Browser should be removed when no project capabilities
        # So the list should NOT contain browser (it gets mapped or removed)
        # Basic servers like context7 and auto-claude should be there
        assert "context7" in servers or "auto-claude" in servers

    def test_includes_linear_when_enabled(self):
        """Test that Linear is included when enabled."""
        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=True,
            mcp_config=None
        )

        assert "linear" in servers

    def test_excludes_linear_when_disabled(self):
        """Test that Linear is excluded when disabled."""
        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config=None
        )

        assert "linear" not in servers

    def test_filters_context7_via_mcp_config(self):
        """Test that Context7 can be filtered via mcp_config."""
        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config={"CONTEXT7_ENABLED": "false"}
        )

        assert "context7" not in servers

    def test_filters_context7_case_insensitive(self):
        """Test that Context7 filtering is case-insensitive."""
        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config={"CONTEXT7_ENABLED": "FALSE"}
        )

        assert "context7" not in servers

    def test_keeps_context7_when_enabled(self):
        """Test that Context7 is kept when explicitly enabled."""
        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config={"CONTEXT7_ENABLED": "true"}
        )

        assert "context7" in servers

    def test_maps_browser_to_electron(self):
        """Test that browser maps to electron for Electron projects."""
        servers = get_required_mcp_servers(
            "qa_reviewer",
            project_capabilities={"is_electron": True},
            linear_enabled=False,
            mcp_config={"ELECTRON_MCP_ENABLED": "true"}
        )

        assert "electron" in servers
        assert "browser" not in servers

    def test_maps_browser_to_electron_via_global_env(self):
        """Test that browser maps to electron via global env var."""
        with patch.dict(os.environ, {"ELECTRON_MCP_ENABLED": "true"}):
            servers = get_required_mcp_servers(
                "qa_reviewer",
                project_capabilities={"is_electron": True},
                linear_enabled=False,
                mcp_config=None
            )

            assert "electron" in servers
            assert "browser" not in servers

    def test_does_not_map_browser_to_electron_when_disabled(self):
        """Test that browser doesn't map to electron when disabled."""
        servers = get_required_mcp_servers(
            "qa_reviewer",
            project_capabilities={"is_electron": True},
            linear_enabled=False,
            mcp_config={"ELECTRON_MCP_ENABLED": "false"}
        )

        # With ELECTRON_MCP_ENABLED=false, electron shouldn't be added
        assert "electron" not in servers
        # Browser should be removed from the list
        assert "browser" not in servers

    def test_maps_browser_to_puppeteer(self):
        """Test that browser maps to puppeteer for web projects."""
        servers = get_required_mcp_servers(
            "qa_reviewer",
            project_capabilities={"is_electron": False, "is_web_frontend": True},
            linear_enabled=False,
            mcp_config={"PUPPETEER_MCP_ENABLED": "true"}
        )

        assert "puppeteer" in servers
        assert "browser" not in servers

    def test_does_not_map_browser_to_puppeteer_when_disabled(self):
        """Test that browser doesn't map to puppeteer when disabled."""
        servers = get_required_mcp_servers(
            "qa_reviewer",
            project_capabilities={"is_electron": False, "is_web_frontend": True},
            linear_enabled=False,
            mcp_config={"PUPPETEER_MCP_ENABLED": "false"}
        )

        assert "puppeteer" not in servers
        assert "browser" not in servers

    def test_browser_removed_when_no_project_capabilities(self):
        """Test that browser is removed when no project capabilities."""
        servers = get_required_mcp_servers(
            "qa_reviewer",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config=None
        )

        # Browser should be removed when there's no project capabilities
        assert "browser" not in servers

    def test_filters_graphiti_when_env_not_set(self):
        """Test that Graphiti is filtered when GRAPHITI_MCP_URL is not set."""
        # Ensure env var is not set
        with patch.dict(os.environ, {}, clear=True):
            servers = get_required_mcp_servers(
                "coder",
                project_capabilities=None,
                linear_enabled=False,
                mcp_config=None
            )

            assert "graphiti" not in servers

    def test_keeps_graphiti_when_env_set(self):
        """Test that Graphiti is kept when GRAPHITI_MCP_URL is set."""
        with patch.dict(os.environ, {"GRAPHITI_MCP_URL": "http://localhost:5433"}):
            servers = get_required_mcp_servers(
                "coder",
                project_capabilities=None,
                linear_enabled=False,
                mcp_config=None
            )

            assert "graphiti" in servers

    def test_linear_mcp_enabled_override_can_disable(self):
        """Test that LINEAR_MCP_ENABLED can disable linear even when linear_enabled=True."""
        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=True,  # But mcp_config overrides
            mcp_config={"LINEAR_MCP_ENABLED": "false"}
        )

        # LINEAR_MCP_ENABLED=false should prevent linear from being added
        assert "linear" not in servers

    def test_linear_mcp_enabled_case_insensitive(self):
        """Test that LINEAR_MCP_ENABLED filtering is case-insensitive."""
        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=True,
            mcp_config={"LINEAR_MCP_ENABLED": "FALSE"}
        )

        assert "linear" not in servers

    def test_applies_per_agent_additions(self):
        """Test that per-agent additions are applied."""
        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config={"AGENT_MCP_coder_ADD": "linear"}
        )

        # Linear should be added even when linear_enabled=False
        assert "linear" in servers

    def test_applies_per_agent_removals(self):
        """Test that per-agent removals are applied."""
        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config={"AGENT_MCP_coder_REMOVE": "context7"}
        )

        # Context7 should be removed
        assert "context7" not in servers
        assert "auto-claude" in servers

    def test_never_removes_auto_claude(self):
        """Test that auto-claude server can never be removed."""
        # Create a config that tries to remove auto-claude
        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config={"AGENT_MCP_coder_REMOVE": "auto-claude"}
        )

        # auto-claude should still be there (cannot be removed)
        assert "auto-claude" in servers

    def test_multiple_servers_in_add_list(self):
        """Test that multiple servers can be added at once."""
        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config={"AGENT_MCP_coder_ADD": "linear,context7"}
        )

        # Both should be added (context7 is already there, linear is added)
        assert "context7" in servers
        assert "linear" in servers

    def test_multiple_servers_in_remove_list(self):
        """Test that multiple servers can be removed at once."""
        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config={"AGENT_MCP_coder_REMOVE": "context7,graphiti"}
        )

        # Both should be removed
        assert "context7" not in servers

    def test_add_remove_combination(self):
        """Test that add and remove can be used together."""
        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config={
                "AGENT_MCP_coder_ADD": "linear",
                "AGENT_MCP_coder_REMOVE": "context7"
            }
        )

        # linear should be added, context7 should be removed
        assert "linear" in servers
        assert "context7" not in servers

    def test_add_skip_whitespace_in_list(self):
        """Test that whitespace is skipped in server list."""
        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config={"AGENT_MCP_coder_ADD": " linear , context7 , graphiti "}
        )

        assert "linear" in servers
        assert "context7" in servers

    def test_spec_agents_have_minimal_servers(self):
        """Test that spec agents have minimal MCP servers."""
        spec_agents = ["spec_gatherer", "spec_writer", "spec_critic"]

        for agent_type in spec_agents:
            servers = get_required_mcp_servers(
                agent_type,
                project_capabilities=None,
                linear_enabled=False,
                mcp_config=None
            )

            # Should have very few servers
            assert len(servers) <= 2  # Only context7 for researcher

    def test_utility_agents_have_no_servers(self):
        """Test that utility agents have no MCP servers."""
        utility_agents = ["merge_resolver", "commit_message", "ideation"]

        for agent_type in utility_agents:
            servers = get_required_mcp_servers(
                agent_type,
                project_capabilities=None,
                linear_enabled=False,
                mcp_config=None
            )

            assert len(servers) == 0

    def test_returns_list_not_reference_to_config(self):
        """Test that returned list is a copy, not a reference."""
        servers1 = get_required_mcp_servers("coder")
        servers2 = get_required_mcp_servers("coder")

        # Modifying one shouldn't affect the other
        servers1.append("fake-server")
        assert "fake-server" not in servers2


class TestGetDefaultThinkingLevel:
    """Test get_default_thinking_level function."""

    def test_returns_thinking_for_coder(self):
        """Test that correct thinking level is returned for coder."""
        level = get_default_thinking_level("coder")
        assert level == "none"

    def test_returns_thinking_for_planner(self):
        """Test that correct thinking level is returned for planner."""
        level = get_default_thinking_level("planner")
        assert level == "high"

    def test_returns_thinking_for_qa_reviewer(self):
        """Test that correct thinking level is returned for QA reviewer."""
        level = get_default_thinking_level("qa_reviewer")
        assert level == "high"

    def test_returns_thinking_for_qa_fixer(self):
        """Test that correct thinking level is returned for QA fixer."""
        level = get_default_thinking_level("qa_fixer")
        assert level == "medium"

    def test_returns_thinking_for_spec_critic(self):
        """Test that correct thinking level is returned for spec critic."""
        level = get_default_thinking_level("spec_critic")
        assert level == "ultrathink"

    def test_returns_thinking_for_spec_gatherer(self):
        """Test that correct thinking level is returned for spec gatherer."""
        level = get_default_thinking_level("spec_gatherer")
        assert level == "medium"

    def test_returns_thinking_for_spec_writer(self):
        """Test that correct thinking level is returned for spec writer."""
        level = get_default_thinking_level("spec_writer")
        assert level == "high"

    def test_returns_thinking_for_insights(self):
        """Test that correct thinking level is returned for insights."""
        level = get_default_thinking_level("insights")
        # Insights uses Haiku which doesn't support thinking
        assert level == "none"

    def test_returns_thinking_for_merge_resolver(self):
        """Test that correct thinking level is returned for merge resolver."""
        level = get_default_thinking_level("merge_resolver")
        assert level == "low"

    def test_returns_thinking_for_pr_template_filler(self):
        """Test that correct thinking level is returned for PR template filler."""
        level = get_default_thinking_level("pr_template_filler")
        assert level == "low"

    def test_returns_thinking_for_roadmap_discovery(self):
        """Test that correct thinking level is returned for roadmap discovery."""
        level = get_default_thinking_level("roadmap_discovery")
        assert level == "high"

    def test_returns_thinking_for_all_agent_types(self):
        """Test that all agent types have valid thinking levels."""
        valid_levels = {"none", "low", "medium", "high", "ultrathink"}

        for agent_type in AGENT_CONFIGS.keys():
            level = get_default_thinking_level(agent_type)
            assert level in valid_levels, f"Agent '{agent_type}' has invalid level: {level}"

    def test_raises_error_for_unknown_agent_type(self):
        """Test that ValueError is raised for unknown agent type."""
        with pytest.raises(ValueError, match="Unknown agent type"):
            get_default_thinking_level("unknown_agent")


class TestMapMcpServerName:
    """Test _map_mcp_server_name function."""

    def test_maps_context7_variations(self):
        """Test that various Context7 name variations are mapped."""
        assert _map_mcp_server_name("context7") == "context7"
        assert _map_mcp_server_name("Context7") == "context7"
        assert _map_mcp_server_name("CONTEXT7") == "context7"
        assert _map_mcp_server_name("  context7  ") == "context7"

    def test_maps_graphiti_variations(self):
        """Test that various Graphiti name variations are mapped."""
        assert _map_mcp_server_name("graphiti") == "graphiti"
        assert _map_mcp_server_name("graphiti-memory") == "graphiti"
        assert _map_mcp_server_name("Graphiti") == "graphiti"
        assert _map_mcp_server_name("GRAPHITI-MEMORY") == "graphiti"

    def test_maps_linear(self):
        """Test Linear server mapping."""
        assert _map_mcp_server_name("linear") == "linear"
        assert _map_mcp_server_name("Linear") == "linear"

    def test_maps_electron(self):
        """Test Electron server mapping."""
        assert _map_mcp_server_name("electron") == "electron"
        assert _map_mcp_server_name("Electron") == "electron"

    def test_maps_puppeteer(self):
        """Test Puppeteer server mapping."""
        assert _map_mcp_server_name("puppeteer") == "puppeteer"
        assert _map_mcp_server_name("Puppeteer") == "puppeteer"

    def test_maps_auto_claude(self):
        """Test auto-claude server mapping."""
        assert _map_mcp_server_name("auto-claude") == "auto-claude"
        assert _map_mcp_server_name("Auto-Claude") == "auto-claude"

    def test_returns_none_for_unknown_server(self):
        """Test that None is returned for unknown server."""
        assert _map_mcp_server_name("unknown-server") is None
        assert _map_mcp_server_name("random-name") is None

    def test_returns_none_for_empty_string(self):
        """Test that None is returned for empty string."""
        assert _map_mcp_server_name("") is None

    def test_returns_none_for_whitespace(self):
        """Test that None is returned for whitespace."""
        assert _map_mcp_server_name("  ") is None
        assert _map_mcp_server_name("\t") is None
        assert _map_mcp_server_name("\n") is None

    def test_returns_none_for_none_input(self):
        """Test that None is returned for None input."""
        assert _map_mcp_server_name(None) is None

    def test_accepts_custom_server_id(self):
        """Test that custom server IDs are accepted."""
        custom_servers = ["my-custom-server", "another-custom"]
        assert _map_mcp_server_name("my-custom-server", custom_servers) == "my-custom-server"
        assert _map_mcp_server_name("another-custom", custom_servers) == "another-custom"

    def test_custom_server_id_case_sensitive(self):
        """Test that custom server IDs are case-sensitive."""
        custom_servers = ["My-Server"]
        # Exact match should work
        assert _map_mcp_server_name("My-Server", custom_servers) == "My-Server"
        # Case mismatch should not
        assert _map_mcp_server_name("my-server", custom_servers) is None

    def test_returns_none_for_unlisted_custom_server(self):
        """Test that unlisted custom server returns None."""
        custom_servers = ["my-custom-server"]
        assert _map_mcp_server_name("unlisted-server", custom_servers) is None

    def test_known_servers_take_precedence_over_custom(self):
        """Test that known servers map even if in custom list."""
        custom_servers = ["context7"]
        # Should still map to canonical name
        assert _map_mcp_server_name("context7", custom_servers) == "context7"

    def test_custom_servers_with_whitespace(self):
        """Test custom servers with whitespace are handled."""
        custom_servers = ["my-server"]
        # Whitespace is NOT stripped for custom servers (only for known mappings)
        # So this should return None since the names don't match exactly
        assert _map_mcp_server_name("  my-server  ", custom_servers) is None


class TestGetRequiredMcpServersWithCustomMcp:
    """Test get_required_mcp_servers with custom MCP configuration."""

    def test_applies_per_agent_additions_with_known_servers(self):
        """Test that per-agent additions work with known server names."""
        # Note: The key uses lowercase agent_type: "AGENT_MCP_coder_ADD"
        mcp_config = {"AGENT_MCP_coder_ADD": "linear"}

        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config=mcp_config
        )

        # Linear should be added even when linear_enabled=False
        assert "linear" in servers

    def test_applies_per_agent_removals_with_known_servers(self):
        """Test that per-agent removals work with known server names."""
        # Note: The key uses lowercase agent_type: "AGENT_MCP_coder_REMOVE"
        mcp_config = {"AGENT_MCP_coder_REMOVE": "context7"}

        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config=mcp_config
        )

        # Context7 should be removed
        assert "context7" not in servers
        # But auto-claude should still be there
        assert "auto-claude" in servers

    def test_addition_of_unknown_custom_server(self):
        """Test adding unknown custom server that's not in mappings."""
        mcp_config = {
            "AGENT_MCP_coder_ADD": "unknown-server"
        }

        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config=mcp_config
        )

        # Unknown server won't be added
        assert "unknown-server" not in servers

    def test_custom_mcp_servers_key_exists_but_empty(self):
        """Test that empty CUSTOM_MCP_SERVERS is handled."""
        mcp_config = {
            "CUSTOM_MCP_SERVERS": [],
            "AGENT_MCP_coder_ADD": "linear"
        }

        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config=mcp_config
        )

        # Should still add known servers like linear
        assert "linear" in servers

    def test_custom_mcp_servers_with_valid_entries(self):
        """Test custom MCP servers are recognized."""
        custom_servers = [
            {"id": "my-custom-server", "name": "My Custom Server"}
        ]
        mcp_config = {
            "CUSTOM_MCP_SERVERS": custom_servers,
            "AGENT_MCP_coder_ADD": "my-custom-server"
        }

        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config=mcp_config
        )

        # Custom server should be added
        assert "my-custom-server" in servers

    def test_custom_server_can_be_removed(self):
        """Test that custom servers can be removed."""
        custom_servers = [{"id": "my-custom"}]
        mcp_config = {
            "CUSTOM_MCP_SERVERS": custom_servers,
            "AGENT_MCP_coder_ADD": "my-custom",
            "AGENT_MCP_coder_REMOVE": "my-custom"
        }

        servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config=mcp_config
        )

        # Custom server should not be present (removed after being added)
        assert "my-custom" not in servers

    def test_agent_specific_add_does_not_affect_other_agents(self):
        """Test that AGENT_MCP_coder_ADD doesn't affect other agents."""
        mcp_config = {
            "AGENT_MCP_coder_ADD": "linear"
        }

        coder_servers = get_required_mcp_servers(
            "coder",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config=mcp_config
        )

        planner_servers = get_required_mcp_servers(
            "planner",
            project_capabilities=None,
            linear_enabled=False,
            mcp_config=mcp_config
        )

        # Coder should have linear from ADD config
        assert "linear" in coder_servers
        # Planner should not have linear (no ADD config for planner)
        assert "linear" not in planner_servers


class TestConstants:
    """Test module-level constants."""

    def test_base_read_tools_defined(self):
        """Test that BASE_READ_TOOLS is properly defined."""
        assert isinstance(BASE_READ_TOOLS, list)
        assert "Read" in BASE_READ_TOOLS
        assert "Glob" in BASE_READ_TOOLS
        assert "Grep" in BASE_READ_TOOLS

    def test_base_write_tools_defined(self):
        """Test that BASE_WRITE_TOOLS is properly defined."""
        assert isinstance(BASE_WRITE_TOOLS, list)
        assert "Write" in BASE_WRITE_TOOLS
        assert "Edit" in BASE_WRITE_TOOLS
        assert "Bash" in BASE_WRITE_TOOLS

    def test_web_tools_defined(self):
        """Test that WEB_TOOLS is properly defined."""
        assert isinstance(WEB_TOOLS, list)
        assert "WebFetch" in WEB_TOOLS
        assert "WebSearch" in WEB_TOOLS

    def test_context7_tools_defined(self):
        """Test that CONTEXT7_TOOLS is properly defined."""
        assert isinstance(CONTEXT7_TOOLS, list)
        assert len(CONTEXT7_TOOLS) >= 2
        assert any("context7" in tool.lower() for tool in CONTEXT7_TOOLS)

    def test_linear_tools_defined(self):
        """Test that LINEAR_TOOLS is properly defined."""
        assert isinstance(LINEAR_TOOLS, list)
        assert len(LINEAR_TOOLS) > 10  # Linear has many tools

    def test_graphiti_tools_defined(self):
        """Test that GRAPHITI_MCP_TOOLS is properly defined."""
        assert isinstance(GRAPHITI_MCP_TOOLS, list)
        assert len(GRAPHITI_MCP_TOOLS) >= 5
        assert any("graphiti" in tool.lower() for tool in GRAPHITI_MCP_TOOLS)

    def test_puppeteer_tools_defined(self):
        """Test that PUPPETEER_TOOLS is properly defined."""
        assert isinstance(PUPPETEER_TOOLS, list)
        assert "puppeteer" in PUPPETEER_TOOLS[0].lower()

    def test_electron_tools_defined(self):
        """Test that ELECTRON_TOOLS is properly defined."""
        assert isinstance(ELECTRON_TOOLS, list)
        assert len(ELECTRON_TOOLS) >= 4
