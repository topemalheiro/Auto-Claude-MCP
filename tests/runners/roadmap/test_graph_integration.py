"""Tests for graph_integration"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from runners.roadmap.graph_integration import GraphHintsProvider
from runners.roadmap.models import RoadmapPhaseResult


@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary output and project directories."""
    output_dir = tmp_path / "roadmap"
    project_dir = tmp_path / "project"
    output_dir.mkdir(parents=True)
    project_dir.mkdir(parents=True)
    return output_dir, project_dir


def test_GraphHintsProvider___init__(temp_dirs):
    """Test GraphHintsProvider.__init__"""
    # Arrange
    output_dir, project_dir = temp_dirs

    # Act
    refresh = True
    instance = GraphHintsProvider(output_dir, project_dir, refresh)

    # Assert
    assert instance is not None
    assert instance.output_dir == output_dir
    assert instance.project_dir == project_dir
    assert instance.refresh is refresh
    assert instance.hints_file == output_dir / "graph_hints.json"


@pytest.mark.asyncio
async def test_GraphHintsProvider_retrieve_hints_file_exists(temp_dirs):
    """Test GraphHintsProvider.retrieve_hints when file already exists"""
    # Arrange
    output_dir, project_dir = temp_dirs
    refresh = False
    instance = GraphHintsProvider(output_dir, project_dir, refresh)

    # Create an existing hints file
    hints_data = {"enabled": True, "hints": [{"hint": "test"}]}
    with open(instance.hints_file, "w", encoding="utf-8") as f:
        json.dump(hints_data, f)

    # Act
    result = await instance.retrieve_hints()

    # Assert
    assert result is not None
    assert isinstance(result, RoadmapPhaseResult)
    assert result.phase == "graph_hints"
    assert result.success is True
    assert result.retries == 0


@pytest.mark.asyncio
@patch("runners.roadmap.graph_integration.is_graphiti_enabled", return_value=False)
async def test_GraphHintsProvider_retrieve_hints_graphiti_disabled(mock_is_enabled, temp_dirs):
    """Test GraphHintsProvider.retrieve_hints when Graphiti is disabled"""
    # Arrange
    output_dir, project_dir = temp_dirs
    refresh = True
    instance = GraphHintsProvider(output_dir, project_dir, refresh)

    # Act
    result = await instance.retrieve_hints()

    # Assert
    assert result is not None
    assert isinstance(result, RoadmapPhaseResult)
    assert result.phase == "graph_hints"
    assert result.success is True
    assert result.retries == 0

    # Verify the hints file was created with disabled flag
    assert instance.hints_file.exists()
    with open(instance.hints_file, encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("enabled") is False
    assert "not configured" in data.get("reason", "")


@pytest.mark.asyncio
@patch("runners.roadmap.graph_integration.is_graphiti_enabled", return_value=True)
@patch("runners.roadmap.graph_integration.get_graph_hints", new_callable=AsyncMock)
async def test_GraphHintsProvider_retrieve_hints_with_results(
    mock_get_hints, mock_is_enabled, temp_dirs
):
    """Test GraphHintsProvider.retrieve_hints with successful retrieval"""
    # Arrange
    output_dir, project_dir = temp_dirs
    refresh = True
    instance = GraphHintsProvider(output_dir, project_dir, refresh)

    # Mock graph hints response
    mock_get_hints.return_value = [
        {"hint": "Consider adding feature X"},
        {"hint": "Prioritize feature Y"},
    ]

    # Act
    result = await instance.retrieve_hints()

    # Assert
    assert result is not None
    assert isinstance(result, RoadmapPhaseResult)
    assert result.phase == "graph_hints"
    assert result.success is True
    assert result.retries == 0
    assert len(result.errors) == 0

    # Verify the hints file was created
    assert instance.hints_file.exists()
    with open(instance.hints_file, encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("enabled") is True
    assert data.get("hint_count") == 2
    assert len(data.get("hints", [])) == 2


@pytest.mark.asyncio
@patch("runners.roadmap.graph_integration.is_graphiti_enabled", return_value=True)
@patch("runners.roadmap.graph_integration.get_graph_hints", new_callable=AsyncMock)
async def test_GraphHintsProvider_retrieve_hints_with_error(
    mock_get_hints, mock_is_enabled, temp_dirs
):
    """Test GraphHintsProvider.retrieve_hints when query fails"""
    # Arrange
    output_dir, project_dir = temp_dirs
    refresh = True
    instance = GraphHintsProvider(output_dir, project_dir, refresh)

    # Mock graph hints to raise an error
    mock_get_hints.side_effect = Exception("Graph query failed")

    # Act
    result = await instance.retrieve_hints()

    # Assert
    assert result is not None
    assert isinstance(result, RoadmapPhaseResult)
    assert result.phase == "graph_hints"
    # Should succeed with graceful degradation
    assert result.success is True
    assert len(result.errors) == 1
    assert "Graph query failed" in result.errors[0]

    # Verify error information was saved to file
    assert instance.hints_file.exists()
    with open(instance.hints_file, encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("enabled") is True
    assert "error" in data


@pytest.mark.asyncio
@patch("runners.roadmap.graph_integration.is_graphiti_enabled", return_value=True)
@patch("runners.roadmap.graph_integration.get_graph_hints", new_callable=AsyncMock)
async def test_GraphHintsProvider_retrieve_hints_empty_results(
    mock_get_hints, mock_is_enabled, temp_dirs
):
    """Test GraphHintsProvider.retrieve_hints with no hints found"""
    # Arrange
    output_dir, project_dir = temp_dirs
    refresh = True
    instance = GraphHintsProvider(output_dir, project_dir, refresh)

    # Mock empty graph hints response
    mock_get_hints.return_value = []

    # Act
    result = await instance.retrieve_hints()

    # Assert
    assert result is not None
    assert isinstance(result, RoadmapPhaseResult)
    assert result.phase == "graph_hints"
    assert result.success is True
    assert result.retries == 0

    # Verify the hints file was created with empty hints
    assert instance.hints_file.exists()
    with open(instance.hints_file, encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("enabled") is True
    assert data.get("hint_count") == 0
    assert len(data.get("hints", [])) == 0
