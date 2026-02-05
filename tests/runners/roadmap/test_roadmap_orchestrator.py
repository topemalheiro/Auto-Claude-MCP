"""Tests for orchestrator"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from runners.roadmap.orchestrator import RoadmapOrchestrator


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True)
    return project_dir


@pytest.fixture
def mock_create_client():
    """Create a mock create_client function."""
    return MagicMock()


def test_RoadmapOrchestrator___init__(temp_project_dir, mock_create_client):
    """Test RoadmapOrchestrator.__init__"""
    # Arrange
    project_dir = temp_project_dir
    output_dir = None
    model = "sonnet"
    thinking_level = "medium"
    refresh = False
    enable_competitor_analysis = True
    refresh_competitor_analysis = False

    # Act
    instance = RoadmapOrchestrator(
        project_dir,
        output_dir,
        model,
        thinking_level,
        refresh,
        enable_competitor_analysis,
        refresh_competitor_analysis,
    )

    # Assert
    assert instance is not None
    assert instance.project_dir == project_dir
    assert instance.model == model
    assert instance.thinking_level == thinking_level
    assert instance.refresh is refresh
    assert instance.enable_competitor_analysis is enable_competitor_analysis
    assert instance.refresh_competitor_analysis is refresh_competitor_analysis
    assert instance.output_dir.exists()
    assert instance.script_executor is not None
    assert instance.agent_executor is not None
    assert instance.graph_hints_provider is not None
    assert instance.competitor_analyzer is not None
    assert instance.project_index_phase is not None
    assert instance.discovery_phase is not None
    assert instance.features_phase is not None


def test_RoadmapOrchestrator___init__with_custom_output_dir(
    temp_project_dir, mock_create_client, tmp_path
):
    """Test RoadmapOrchestrator.__init__ with custom output directory"""
    # Arrange
    project_dir = temp_project_dir
    output_dir = tmp_path / "custom_output"
    model = "opus"
    thinking_level = "high"
    refresh = True
    enable_competitor_analysis = False
    refresh_competitor_analysis = False

    # Act
    instance = RoadmapOrchestrator(
        project_dir,
        output_dir,
        model,
        thinking_level,
        refresh,
        enable_competitor_analysis,
        refresh_competitor_analysis,
    )

    # Assert
    assert instance is not None
    assert instance.output_dir == output_dir
    assert instance.output_dir.exists()


@pytest.mark.asyncio
@patch("runners.roadmap.orchestrator.init_auto_claude_dir")
async def test_RoadmapOrchestrator_run_project_index_failure(
    mock_init, temp_project_dir, mock_create_client
):
    """Test RoadmapOrchestrator.run when project index phase fails"""
    # Arrange
    instance = RoadmapOrchestrator(temp_project_dir)

    # Mock project index phase to fail
    async def mock_execute():
        from runners.roadmap.models import RoadmapPhaseResult

        return RoadmapPhaseResult(
            "project_index", False, [], ["Index failed"], 1
        )

    instance.project_index_phase.execute = mock_execute

    # Act
    result = await instance.run()

    # Assert
    assert result is False


@pytest.mark.asyncio
@patch("runners.roadmap.orchestrator.init_auto_claude_dir")
async def test_RoadmapOrchestrator_run_discovery_failure(
    mock_init, temp_project_dir, mock_create_client
):
    """Test RoadmapOrchestrator.run when discovery phase fails"""
    # Arrange
    instance = RoadmapOrchestrator(temp_project_dir)

    # Mock project index to succeed
    async def mock_index_execute():
        from runners.roadmap.models import RoadmapPhaseResult

        return RoadmapPhaseResult("project_index", True, ["index.json"], [], 0)

    # Mock hints to succeed
    async def mock_hints_retrieve():
        from runners.roadmap.models import RoadmapPhaseResult

        return RoadmapPhaseResult("graph_hints", True, ["hints.json"], [], 0)

    # Mock discovery to fail
    async def mock_discovery_execute():
        from runners.roadmap.models import RoadmapPhaseResult

        return RoadmapPhaseResult("discovery", False, [], ["Discovery failed"], 1)

    instance.project_index_phase.execute = mock_index_execute
    instance.graph_hints_provider.retrieve_hints = mock_hints_retrieve
    instance.discovery_phase.execute = mock_discovery_execute

    # Act
    result = await instance.run()

    # Assert
    assert result is False


@pytest.mark.asyncio
@patch("runners.roadmap.orchestrator.init_auto_claude_dir")
async def test_RoadmapOrchestrator_run_features_failure(
    mock_init, temp_project_dir, mock_create_client
):
    """Test RoadmapOrchestrator.run when features phase fails"""
    # Arrange
    instance = RoadmapOrchestrator(temp_project_dir)

    # Mock all phases to succeed except features
    async def mock_success_result(phase_name, file_name):
        from runners.roadmap.models import RoadmapPhaseResult

        return RoadmapPhaseResult(phase_name, True, [file_name], [], 0)

    async def mock_features_execute():
        from runners.roadmap.models import RoadmapPhaseResult

        return RoadmapPhaseResult("features", False, [], ["Features failed"], 1)

    instance.project_index_phase.execute = lambda: mock_success_result(
        "project_index", "index.json"
    )
    instance.graph_hints_provider.retrieve_hints = lambda: mock_success_result(
        "graph_hints", "hints.json"
    )
    instance.discovery_phase.execute = lambda: mock_success_result(
        "discovery", "discovery.json"
    )
    instance.competitor_analyzer.analyze = lambda enabled=False: mock_success_result(
        "competitor_analysis", "competitor.json"
    )
    instance.features_phase.execute = mock_features_execute

    # Act
    result = await instance.run()

    # Assert
    assert result is False


@pytest.mark.asyncio
@patch("runners.roadmap.orchestrator.init_auto_claude_dir")
async def test_RoadmapOrchestrator_run_success(
    mock_init, temp_project_dir, mock_create_client
):
    """Test RoadmapOrchestrator.run with all phases succeeding"""
    # Arrange
    instance = RoadmapOrchestrator(temp_project_dir)

    # Create a valid roadmap file for summary printing
    roadmap_file = instance.output_dir / "roadmap.json"
    import json

    roadmap_data = {
        "vision": "A great vision",
        "phases": [{"id": "phase-1", "name": "Phase 1"}],
        "features": [
            {"id": "f1", "title": "Feature 1", "priority": "high"},
            {"id": "f2", "title": "Feature 2", "priority": "medium"},
            {"id": "f3", "title": "Feature 3", "priority": "low"},
        ],
        "target_audience": {"primary": "developers"},
    }
    with open(roadmap_file, "w", encoding="utf-8") as f:
        json.dump(roadmap_data, f)

    # Mock all phases to succeed
    async def mock_success_result(phase_name, file_name):
        from runners.roadmap.models import RoadmapPhaseResult

        return RoadmapPhaseResult(phase_name, True, [file_name], [], 0)

    instance.project_index_phase.execute = lambda: mock_success_result(
        "project_index", "index.json"
    )
    instance.graph_hints_provider.retrieve_hints = lambda: mock_success_result(
        "graph_hints", "hints.json"
    )
    instance.discovery_phase.execute = lambda: mock_success_result(
        "discovery", "discovery.json"
    )
    instance.competitor_analyzer.analyze = lambda enabled=False: mock_success_result(
        "competitor_analysis", "competitor.json"
    )
    instance.features_phase.execute = lambda: mock_success_result(
        "features", "roadmap.json"
    )

    # Act
    result = await instance.run()

    # Assert
    assert result is True
