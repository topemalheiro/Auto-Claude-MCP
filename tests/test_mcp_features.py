"""
Tests for MCP Feature Services: Insights, Roadmap, Ideation, Memory
=====================================================================

Combined tests for InsightsService, RoadmapService, IdeationService,
and MemoryService (singleton pattern).
"""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Setup: add backend to path and pre-mock SDK
_backend = Path(__file__).parent.parent / "apps" / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

if "claude_agent_sdk" not in sys.modules:
    sys.modules["claude_agent_sdk"] = MagicMock()
    sys.modules["claude_agent_sdk.types"] = MagicMock()

import pytest

from mcp_server.services.insights_service import InsightsService
from mcp_server.services.roadmap_service import RoadmapService
from mcp_server.services.ideation_service import IdeationService, VALID_IDEATION_TYPES
import mcp_server.services.memory_service as memory_mod
from mcp_server.services.memory_service import MemoryService, get_memory_service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_dir(tmp_path):
    """Create a temp project dir with .auto-claude structure."""
    ac = tmp_path / ".auto-claude"
    ac.mkdir()
    (ac / "ideation").mkdir()
    (ac / "roadmap").mkdir()
    (ac / "github").mkdir()
    return tmp_path


@pytest.fixture(autouse=True)
def reset_memory_singleton():
    """Reset the MemoryService singleton between every test."""
    memory_mod._instance = None
    yield
    memory_mod._instance = None


# ===========================================================================
# InsightsService Tests
# ===========================================================================


class TestInsightsServiceAsk:
    """Tests for InsightsService.ask() - AI codebase Q&A."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ask_captures_stdout(self, project_dir):
        """ask() captures stdout from run_with_sdk and returns it."""
        service = InsightsService(project_dir)

        mock_run = AsyncMock()

        async def _fake_run(**kwargs):
            print("The answer is 42.")

        with patch.dict(
            "sys.modules",
            {
                "runners.insights_runner": MagicMock(
                    run_with_sdk=_fake_run
                )
            },
        ):
            result = await service.ask("What is the meaning?")

        assert result["success"] is True
        assert "42" in result["response"]

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ask_parses_task_suggestions(self, project_dir):
        """ask() extracts __TASK_SUGGESTION__ lines from output."""
        service = InsightsService(project_dir)

        suggestion = json.dumps({"title": "Add tests", "priority": "high"})

        async def _fake_run(**kwargs):
            print("Some response text")
            print(f"__TASK_SUGGESTION__:{suggestion}")
            print("More text")

        with patch.dict(
            "sys.modules",
            {
                "runners.insights_runner": MagicMock(
                    run_with_sdk=_fake_run
                )
            },
        ):
            result = await service.ask("Suggest improvements")

        assert result["success"] is True
        assert len(result["task_suggestions"]) == 1
        assert result["task_suggestions"][0]["title"] == "Add tests"
        # Task suggestion lines should not appear in response
        assert "__TASK_SUGGESTION__" not in result["response"]

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ask_strips_tool_markers(self, project_dir):
        """ask() removes __TOOL_START__ and __TOOL_END__ markers."""
        service = InsightsService(project_dir)

        async def _fake_run(**kwargs):
            print("__TOOL_START__:search")
            print("Real content here")
            print("__TOOL_END__:search")

        with patch.dict(
            "sys.modules",
            {
                "runners.insights_runner": MagicMock(
                    run_with_sdk=_fake_run
                )
            },
        ):
            result = await service.ask("Question")

        assert "__TOOL_START__" not in result["response"]
        assert "__TOOL_END__" not in result["response"]
        assert "Real content here" in result["response"]

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ask_passes_params_correctly(self, project_dir):
        """ask() forwards all parameters to run_with_sdk."""
        service = InsightsService(project_dir)
        captured_kwargs = {}

        async def _fake_run(**kwargs):
            captured_kwargs.update(kwargs)
            print("ok")

        with patch.dict(
            "sys.modules",
            {
                "runners.insights_runner": MagicMock(
                    run_with_sdk=_fake_run
                )
            },
        ):
            await service.ask(
                "Q",
                history=[{"role": "user", "content": "hi"}],
                model="opus",
                thinking_level="high",
            )

        assert captured_kwargs["project_dir"] == str(project_dir)
        assert captured_kwargs["message"] == "Q"
        assert captured_kwargs["model"] == "opus"
        assert captured_kwargs["thinking_level"] == "high"
        assert len(captured_kwargs["history"]) == 1

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ask_import_error(self, project_dir):
        """When insights runner is unavailable, returns error."""
        service = InsightsService(project_dir)

        with patch.dict("sys.modules", {"runners.insights_runner": None}):
            result = await service.ask("Question")

        assert "error" in result

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ask_exception(self, project_dir):
        """When run_with_sdk raises, returns error."""
        service = InsightsService(project_dir)

        async def _boom(**kwargs):
            raise RuntimeError("Model overloaded")

        with patch.dict(
            "sys.modules",
            {
                "runners.insights_runner": MagicMock(
                    run_with_sdk=_boom
                )
            },
        ):
            result = await service.ask("Question")

        assert "error" in result
        assert "Model overloaded" in result["error"]


class TestInsightsServiceSuggestTasks:
    """Tests for InsightsService.suggest_tasks() - reads ideation data."""

    def test_suggest_tasks_with_ideation_data(self, project_dir):
        """When ideation.json exists, returns task suggestions."""
        service = InsightsService(project_dir)

        ideation_data = {
            "ideas": [
                {
                    "title": "Add caching",
                    "description": "Implement Redis cache",
                    "type": "performance",
                    "impact": "high",
                    "effort": "medium",
                },
                {
                    "title": "Fix typos",
                    "description": "Fix documentation typos",
                    "type": "docs",
                    "impact": "low",
                    "effort": "low",
                },
            ]
        }

        ideation_file = project_dir / ".auto-claude" / "ideation" / "ideation.json"
        ideation_file.write_text(json.dumps(ideation_data))

        result = service.suggest_tasks()

        assert result["success"] is True
        assert len(result["suggestions"]) == 2
        assert result["suggestions"][0]["title"] == "Add caching"
        assert result["suggestions"][0]["category"] == "performance"
        assert result["suggestions"][1]["impact"] == "low"

    def test_suggest_tasks_no_ideation_data(self, project_dir):
        """When ideation.json doesn't exist, returns empty with message."""
        service = InsightsService(project_dir)

        result = service.suggest_tasks()

        assert result["success"] is True
        assert result["suggestions"] == []
        assert "No ideation data" in result["message"]

    def test_suggest_tasks_limits_to_10(self, project_dir):
        """At most 10 suggestions are returned."""
        service = InsightsService(project_dir)

        ideation_data = {
            "ideas": [
                {"title": f"Idea {i}", "description": f"Desc {i}"}
                for i in range(20)
            ]
        }

        ideation_file = project_dir / ".auto-claude" / "ideation" / "ideation.json"
        ideation_file.write_text(json.dumps(ideation_data))

        result = service.suggest_tasks()

        assert result["success"] is True
        assert len(result["suggestions"]) == 10

    def test_suggest_tasks_corrupt_json(self, project_dir):
        """When ideation.json is corrupt, returns error."""
        service = InsightsService(project_dir)

        ideation_file = project_dir / ".auto-claude" / "ideation" / "ideation.json"
        ideation_file.write_text("not valid json{{{")

        result = service.suggest_tasks()

        assert "error" in result


# ===========================================================================
# RoadmapService Tests
# ===========================================================================


class TestRoadmapServiceGetRoadmap:
    """Tests for RoadmapService.get_roadmap() - reads roadmap from disk."""

    def test_get_roadmap_exists(self, project_dir):
        """When roadmap.json exists, returns it."""
        service = RoadmapService(project_dir)

        roadmap_data = {
            "vision": "World domination",
            "phases": [{"name": "Phase 1", "features": []}],
        }

        roadmap_file = project_dir / ".auto-claude" / "roadmap" / "roadmap.json"
        roadmap_file.write_text(json.dumps(roadmap_data))

        result = service.get_roadmap()

        assert result["success"] is True
        assert result["data"]["vision"] == "World domination"

    def test_get_roadmap_not_found(self, project_dir):
        """When roadmap.json does not exist, returns None with message."""
        service = RoadmapService(project_dir)

        result = service.get_roadmap()

        assert result["success"] is True
        assert result["data"] is None
        assert "No roadmap generated" in result["message"]

    def test_get_roadmap_corrupt_json(self, project_dir):
        """When roadmap.json is corrupt, returns error."""
        service = RoadmapService(project_dir)

        roadmap_file = project_dir / ".auto-claude" / "roadmap" / "roadmap.json"
        roadmap_file.write_text("{bad json")

        result = service.get_roadmap()

        assert "error" in result
        assert "Failed to load roadmap" in result["error"]


class TestRoadmapServiceGenerate:
    """Tests for RoadmapService.generate() - wraps RoadmapOrchestrator."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_generate_success(self, project_dir):
        """Successful generation calls orchestrator and returns roadmap."""
        service = RoadmapService(project_dir)

        mock_orchestrator = MagicMock()
        mock_orchestrator.run = AsyncMock(return_value=True)

        # Write roadmap data that get_roadmap() will read after generation
        roadmap_data = {"vision": "Built", "phases": []}
        roadmap_file = project_dir / ".auto-claude" / "roadmap" / "roadmap.json"
        roadmap_file.write_text(json.dumps(roadmap_data))

        with patch.dict(
            "sys.modules",
            {
                "runners.roadmap.orchestrator": MagicMock(
                    RoadmapOrchestrator=MagicMock(return_value=mock_orchestrator)
                )
            },
        ):
            result = await service.generate(refresh=True, model="opus")

        assert result["success"] is True
        assert result["data"]["vision"] == "Built"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_generate_failure(self, project_dir):
        """When orchestrator returns False, returns error."""
        service = RoadmapService(project_dir)

        mock_orchestrator = MagicMock()
        mock_orchestrator.run = AsyncMock(return_value=False)

        with patch.dict(
            "sys.modules",
            {
                "runners.roadmap.orchestrator": MagicMock(
                    RoadmapOrchestrator=MagicMock(return_value=mock_orchestrator)
                )
            },
        ):
            result = await service.generate()

        assert "error" in result
        assert "failed" in result["error"].lower()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_generate_import_error(self, project_dir):
        """When roadmap module is unavailable, returns error."""
        service = RoadmapService(project_dir)

        with patch.dict("sys.modules", {"runners.roadmap.orchestrator": None}):
            result = await service.generate()

        assert "error" in result

    @pytest.mark.asyncio(loop_scope="function")
    async def test_generate_exception(self, project_dir):
        """When generate raises, returns error."""
        service = RoadmapService(project_dir)

        mock_orchestrator = MagicMock()
        mock_orchestrator.run = AsyncMock(side_effect=RuntimeError("boom"))

        with patch.dict(
            "sys.modules",
            {
                "runners.roadmap.orchestrator": MagicMock(
                    RoadmapOrchestrator=MagicMock(return_value=mock_orchestrator)
                )
            },
        ):
            result = await service.generate()

        assert "error" in result
        assert "boom" in result["error"]


# ===========================================================================
# IdeationService Tests
# ===========================================================================


class TestIdeationServiceGetIdeation:
    """Tests for IdeationService.get_ideation() - reads from disk."""

    def test_get_ideation_exists(self, project_dir):
        """When ideation.json exists, returns it."""
        service = IdeationService(project_dir)

        ideation_data = {
            "ideas": [{"title": "Cache everything", "type": "performance"}]
        }

        ideation_file = project_dir / ".auto-claude" / "ideation" / "ideation.json"
        ideation_file.write_text(json.dumps(ideation_data))

        result = service.get_ideation()

        assert result["success"] is True
        assert len(result["data"]["ideas"]) == 1

    def test_get_ideation_not_found(self, project_dir):
        """When ideation.json does not exist, returns None with message."""
        service = IdeationService(project_dir)

        result = service.get_ideation()

        assert result["success"] is True
        assert result["data"] is None
        assert "No ideation data" in result["message"]

    def test_get_ideation_corrupt_json(self, project_dir):
        """When ideation.json is corrupt, returns error."""
        service = IdeationService(project_dir)

        ideation_file = project_dir / ".auto-claude" / "ideation" / "ideation.json"
        ideation_file.write_text("{{bad")

        result = service.get_ideation()

        assert "error" in result
        assert "Failed to load" in result["error"]


class TestIdeationServiceGenerate:
    """Tests for IdeationService.generate() - wraps IdeationOrchestrator."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_generate_success(self, project_dir):
        """Successful generation calls orchestrator and returns ideation."""
        service = IdeationService(project_dir)

        mock_orchestrator = MagicMock()
        mock_orchestrator.run = AsyncMock(return_value=True)

        # Write data that get_ideation will read
        ideation_data = {"ideas": [{"title": "Idea 1"}]}
        ideation_file = project_dir / ".auto-claude" / "ideation" / "ideation.json"
        ideation_file.write_text(json.dumps(ideation_data))

        with patch.dict(
            "sys.modules",
            {
                "ideation": MagicMock(
                    IdeationOrchestrator=MagicMock(
                        return_value=mock_orchestrator
                    )
                )
            },
        ):
            result = await service.generate(
                types=["low_hanging_fruit"], refresh=True, model="opus"
            )

        assert result["success"] is True

    @pytest.mark.asyncio(loop_scope="function")
    async def test_generate_invalid_types(self, project_dir):
        """Invalid ideation types return error before calling orchestrator."""
        service = IdeationService(project_dir)

        # Mock the import so we get past it to the validation logic
        mock_module = MagicMock()
        with patch.dict("sys.modules", {"ideation": mock_module}):
            result = await service.generate(types=["invalid_type", "also_bad"])

        assert "error" in result
        assert "Invalid ideation types" in result["error"]

    @pytest.mark.asyncio(loop_scope="function")
    async def test_generate_defaults_to_all_types(self, project_dir):
        """When types is None, all valid types are used."""
        service = IdeationService(project_dir)

        captured_types = []
        mock_orchestrator = MagicMock()
        mock_orchestrator.run = AsyncMock(return_value=True)

        # Write data for get_ideation
        ideation_file = project_dir / ".auto-claude" / "ideation" / "ideation.json"
        ideation_file.write_text(json.dumps({"ideas": []}))

        mock_cls = MagicMock(return_value=mock_orchestrator)

        with patch.dict(
            "sys.modules",
            {"ideation": MagicMock(IdeationOrchestrator=mock_cls)},
        ):
            await service.generate(types=None)

        # Verify all valid types were passed
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["enabled_types"] == VALID_IDEATION_TYPES

    @pytest.mark.asyncio(loop_scope="function")
    async def test_generate_orchestrator_failure(self, project_dir):
        """When orchestrator returns False, returns error."""
        service = IdeationService(project_dir)

        mock_orchestrator = MagicMock()
        mock_orchestrator.run = AsyncMock(return_value=False)

        with patch.dict(
            "sys.modules",
            {
                "ideation": MagicMock(
                    IdeationOrchestrator=MagicMock(
                        return_value=mock_orchestrator
                    )
                )
            },
        ):
            result = await service.generate()

        assert "error" in result
        assert "failed" in result["error"].lower()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_generate_import_error(self, project_dir):
        """When ideation module is unavailable, returns error."""
        service = IdeationService(project_dir)

        with patch.dict("sys.modules", {"ideation": None}):
            result = await service.generate()

        assert "error" in result

    @pytest.mark.asyncio(loop_scope="function")
    async def test_generate_exception(self, project_dir):
        """When generate raises, returns error."""
        service = IdeationService(project_dir)

        mock_orchestrator = MagicMock()
        mock_orchestrator.run = AsyncMock(side_effect=RuntimeError("boom"))

        with patch.dict(
            "sys.modules",
            {
                "ideation": MagicMock(
                    IdeationOrchestrator=MagicMock(
                        return_value=mock_orchestrator
                    )
                )
            },
        ):
            result = await service.generate()

        assert "error" in result


# ===========================================================================
# MemoryService Tests
# ===========================================================================


class TestMemoryServiceSingleton:
    """Tests for the get_memory_service() singleton factory."""

    def test_returns_same_instance(self, project_dir):
        """get_memory_service returns the same instance for same dir."""
        svc1 = get_memory_service(project_dir)
        svc2 = get_memory_service(project_dir)
        assert svc1 is svc2

    def test_creates_new_instance_for_different_dir(self, tmp_path):
        """get_memory_service creates new instance when dir changes."""
        dir1 = tmp_path / "proj1"
        dir1.mkdir()
        dir2 = tmp_path / "proj2"
        dir2.mkdir()

        svc1 = get_memory_service(dir1)
        svc2 = get_memory_service(dir2)
        assert svc1 is not svc2

    def test_singleton_reset_between_tests(self):
        """Verify autouse fixture resets the singleton."""
        assert memory_mod._instance is None


class TestMemoryServiceDisabled:
    """Tests for MemoryService when GRAPHITI_ENABLED is not set."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_search_disabled(self, project_dir):
        """search() returns disabled message when Graphiti is off."""
        service = MemoryService(project_dir)

        with patch.dict("os.environ", {}, clear=True):
            result = await service.search("test query")

        assert "error" in result
        assert "not enabled" in result["error"]

    @pytest.mark.asyncio(loop_scope="function")
    async def test_add_episode_disabled(self, project_dir):
        """add_episode() returns disabled message when Graphiti is off."""
        service = MemoryService(project_dir)

        with patch.dict("os.environ", {}, clear=True):
            result = await service.add_episode("some fact")

        assert "error" in result
        assert "not enabled" in result["error"]

    @pytest.mark.asyncio(loop_scope="function")
    async def test_get_recent_disabled(self, project_dir):
        """get_recent() returns disabled message when Graphiti is off."""
        service = MemoryService(project_dir)

        with patch.dict("os.environ", {}, clear=True):
            result = await service.get_recent()

        assert "error" in result
        assert "not enabled" in result["error"]


class TestMemoryServiceEnabled:
    """Tests for MemoryService when GRAPHITI_ENABLED=true."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_search_calls_get_relevant_context(self, project_dir):
        """search() calls the public get_relevant_context() method."""
        service = MemoryService(project_dir)

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(
            return_value=["result1", "result2"]
        )
        mock_memory.initialize = AsyncMock(return_value=True)

        mock_graphiti_mod = MagicMock()
        mock_graphiti_mod.GraphitiMemory = MagicMock(return_value=mock_memory)
        mock_graphiti_mod.GroupIdMode = MagicMock()
        mock_graphiti_mod.GroupIdMode.PROJECT = "project"

        with patch.dict("os.environ", {"GRAPHITI_ENABLED": "true"}):
            with patch.dict(
                "sys.modules",
                {"integrations.graphiti.memory": mock_graphiti_mod},
            ):
                result = await service.search("test query", limit=5)

        assert result["success"] is True
        assert result["count"] == 2
        mock_memory.get_relevant_context.assert_awaited_once_with(
            query="test query", num_results=5
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_search_caches_memory_instance(self, project_dir):
        """_get_memory() caches the memory instance after first call."""
        service = MemoryService(project_dir)

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.initialize = AsyncMock(return_value=True)

        mock_graphiti_mod = MagicMock()
        mock_graphiti_mod.GraphitiMemory = MagicMock(return_value=mock_memory)
        mock_graphiti_mod.GroupIdMode = MagicMock()
        mock_graphiti_mod.GroupIdMode.PROJECT = "project"

        with patch.dict("os.environ", {"GRAPHITI_ENABLED": "true"}):
            with patch.dict(
                "sys.modules",
                {"integrations.graphiti.memory": mock_graphiti_mod},
            ):
                await service.search("first")
                await service.search("second")

        # GraphitiMemory should be instantiated only once
        assert mock_graphiti_mod.GraphitiMemory.call_count == 1

    @pytest.mark.asyncio(loop_scope="function")
    async def test_add_episode_calls_save_session_insights(self, project_dir):
        """add_episode() calls memory.save_session_insights."""
        service = MemoryService(project_dir)

        mock_memory = MagicMock()
        mock_memory.save_session_insights = AsyncMock(return_value=True)
        mock_memory.initialize = AsyncMock(return_value=True)

        mock_graphiti_mod = MagicMock()
        mock_graphiti_mod.GraphitiMemory = MagicMock(return_value=mock_memory)
        mock_graphiti_mod.GroupIdMode = MagicMock()
        mock_graphiti_mod.GroupIdMode.PROJECT = "project"

        with patch.dict("os.environ", {"GRAPHITI_ENABLED": "true"}):
            with patch.dict(
                "sys.modules",
                {"integrations.graphiti.memory": mock_graphiti_mod},
            ):
                result = await service.add_episode("Important fact", source="test")

        assert result["success"] is True
        mock_memory.save_session_insights.assert_awaited_once()
        call_kwargs = mock_memory.save_session_insights.call_args[1]
        assert call_kwargs["session_num"] == 0
        assert call_kwargs["insights"]["content"] == "Important fact"
        assert call_kwargs["insights"]["source"] == "test"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_add_episode_failure(self, project_dir):
        """add_episode() returns error when save fails."""
        service = MemoryService(project_dir)

        mock_memory = MagicMock()
        mock_memory.save_session_insights = AsyncMock(return_value=False)
        mock_memory.initialize = AsyncMock(return_value=True)

        mock_graphiti_mod = MagicMock()
        mock_graphiti_mod.GraphitiMemory = MagicMock(return_value=mock_memory)
        mock_graphiti_mod.GroupIdMode = MagicMock()
        mock_graphiti_mod.GroupIdMode.PROJECT = "project"

        with patch.dict("os.environ", {"GRAPHITI_ENABLED": "true"}):
            with patch.dict(
                "sys.modules",
                {"integrations.graphiti.memory": mock_graphiti_mod},
            ):
                result = await service.add_episode("fact")

        assert "error" in result
        assert "Failed to save" in result["error"]

    @pytest.mark.asyncio(loop_scope="function")
    async def test_get_recent_uses_broad_search(self, project_dir):
        """get_recent() uses get_relevant_context with a broad query."""
        service = MemoryService(project_dir)

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=["entry1"])
        mock_memory.initialize = AsyncMock(return_value=True)

        mock_graphiti_mod = MagicMock()
        mock_graphiti_mod.GraphitiMemory = MagicMock(return_value=mock_memory)
        mock_graphiti_mod.GroupIdMode = MagicMock()
        mock_graphiti_mod.GroupIdMode.PROJECT = "project"

        with patch.dict("os.environ", {"GRAPHITI_ENABLED": "true"}):
            with patch.dict(
                "sys.modules",
                {"integrations.graphiti.memory": mock_graphiti_mod},
            ):
                result = await service.get_recent(limit=5)

        assert result["success"] is True
        assert result["count"] == 1
        mock_memory.get_relevant_context.assert_awaited_once_with(
            query="recent project activity and insights", num_results=5
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_get_memory_returns_none_on_init_failure(self, project_dir):
        """_get_memory() returns None when initialize fails."""
        service = MemoryService(project_dir)

        mock_memory = MagicMock()
        mock_memory.initialize = AsyncMock(return_value=False)

        mock_graphiti_mod = MagicMock()
        mock_graphiti_mod.GraphitiMemory = MagicMock(return_value=mock_memory)
        mock_graphiti_mod.GroupIdMode = MagicMock()
        mock_graphiti_mod.GroupIdMode.PROJECT = "project"

        with patch.dict("os.environ", {"GRAPHITI_ENABLED": "true"}):
            with patch.dict(
                "sys.modules",
                {"integrations.graphiti.memory": mock_graphiti_mod},
            ):
                result = await service.search("query")

        assert "error" in result
        assert "Could not initialize" in result["error"]

    @pytest.mark.asyncio(loop_scope="function")
    async def test_get_memory_import_error(self, project_dir):
        """_get_memory() returns None when graphiti import fails."""
        service = MemoryService(project_dir)

        with patch.dict("os.environ", {"GRAPHITI_ENABLED": "true"}):
            with patch.dict(
                "sys.modules", {"integrations.graphiti.memory": None}
            ):
                result = await service.search("query")

        assert "error" in result

    @pytest.mark.asyncio(loop_scope="function")
    async def test_search_exception(self, project_dir):
        """search() returns error when memory search raises."""
        service = MemoryService(project_dir)

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(
            side_effect=RuntimeError("connection lost")
        )
        mock_memory.initialize = AsyncMock(return_value=True)

        mock_graphiti_mod = MagicMock()
        mock_graphiti_mod.GraphitiMemory = MagicMock(return_value=mock_memory)
        mock_graphiti_mod.GroupIdMode = MagicMock()
        mock_graphiti_mod.GroupIdMode.PROJECT = "project"

        with patch.dict("os.environ", {"GRAPHITI_ENABLED": "true"}):
            with patch.dict(
                "sys.modules",
                {"integrations.graphiti.memory": mock_graphiti_mod},
            ):
                result = await service.search("query")

        assert "error" in result
        assert "connection lost" in result["error"]


class TestMemoryServiceIsGraphitiEnabled:
    """Tests for the _is_graphiti_enabled() helper."""

    def test_enabled_true(self):
        with patch.dict("os.environ", {"GRAPHITI_ENABLED": "true"}):
            assert memory_mod._is_graphiti_enabled() is True

    def test_enabled_one(self):
        with patch.dict("os.environ", {"GRAPHITI_ENABLED": "1"}):
            assert memory_mod._is_graphiti_enabled() is True

    def test_enabled_TRUE_uppercase(self):
        with patch.dict("os.environ", {"GRAPHITI_ENABLED": "TRUE"}):
            assert memory_mod._is_graphiti_enabled() is True

    def test_disabled_false(self):
        with patch.dict("os.environ", {"GRAPHITI_ENABLED": "false"}):
            assert memory_mod._is_graphiti_enabled() is False

    def test_disabled_empty(self):
        with patch.dict("os.environ", {"GRAPHITI_ENABLED": ""}):
            assert memory_mod._is_graphiti_enabled() is False

    def test_disabled_not_set(self):
        with patch.dict("os.environ", {}, clear=True):
            assert memory_mod._is_graphiti_enabled() is False


# ===========================================================================
# Valid Ideation Types Constant
# ===========================================================================


class TestIdeationConstants:
    """Test that VALID_IDEATION_TYPES is correctly defined."""

    def test_valid_types_list(self):
        assert "low_hanging_fruit" in VALID_IDEATION_TYPES
        assert "ui_ux_improvements" in VALID_IDEATION_TYPES
        assert "high_value_features" in VALID_IDEATION_TYPES
        assert len(VALID_IDEATION_TYPES) == 3
