"""Tests for competitor_analyzer"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from runners.roadmap.competitor_analyzer import CompetitorAnalyzer
from runners.roadmap.models import RoadmapPhaseResult


@pytest.fixture
def mock_agent_executor():
    """Create a mock agent executor."""
    executor = MagicMock()
    executor.run_agent = AsyncMock(return_value=(True, "Success"))
    return executor


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "roadmap"
    output_dir.mkdir(parents=True)
    return output_dir


def test_CompetitorAnalyzer___init__(mock_agent_executor, temp_output_dir):
    """Test CompetitorAnalyzer.__init__"""
    # Arrange & Act
    refresh = True
    instance = CompetitorAnalyzer(temp_output_dir, refresh, mock_agent_executor)

    # Assert
    assert instance is not None
    assert instance.output_dir == temp_output_dir
    assert instance.refresh is True
    assert instance.agent_executor == mock_agent_executor
    assert instance.analysis_file == temp_output_dir / "competitor_analysis.json"
    assert instance.discovery_file == temp_output_dir / "roadmap_discovery.json"
    assert instance.project_index_file == temp_output_dir / "project_index.json"


@pytest.mark.asyncio
async def test_CompetitorAnalyzer_analyze_disabled(mock_agent_executor, temp_output_dir):
    """Test CompetitorAnalyzer.analyze when disabled"""
    # Arrange
    refresh = True
    instance = CompetitorAnalyzer(temp_output_dir, refresh, mock_agent_executor)

    # Act
    result = await instance.analyze(enabled=False)

    # Assert
    assert result is not None
    assert isinstance(result, RoadmapPhaseResult)
    assert result.phase == "competitor_analysis"
    assert result.success is True
    assert result.retries == 0

    # Verify the analysis file was created with disabled flag
    assert instance.analysis_file.exists()
    with open(instance.analysis_file, encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("enabled") is False


@pytest.mark.asyncio
async def test_CompetitorAnalyzer_analyze_file_exists(mock_agent_executor, temp_output_dir):
    """Test CompetitorAnalyzer.analyze when file already exists"""
    # Arrange
    refresh = False
    instance = CompetitorAnalyzer(temp_output_dir, refresh, mock_agent_executor)

    # Create an existing analysis file
    with open(instance.analysis_file, "w", encoding="utf-8") as f:
        json.dump({"competitors": []}, f)

    # Act
    result = await instance.analyze(enabled=True)

    # Assert
    assert result is not None
    assert result.success is True
    assert result.retries == 0
    # Agent should not be called when file exists and not refreshing
    mock_agent_executor.run_agent.assert_not_called()


@pytest.mark.asyncio
async def test_CompetitorAnalyzer_analyze_no_discovery_file(mock_agent_executor, temp_output_dir):
    """Test CompetitorAnalyzer.analyze when discovery file is missing"""
    # Arrange
    refresh = True
    instance = CompetitorAnalyzer(temp_output_dir, refresh, mock_agent_executor)

    # Act
    result = await instance.analyze(enabled=True)

    # Assert
    assert result is not None
    assert isinstance(result, RoadmapPhaseResult)
    assert result.phase == "competitor_analysis"
    # Should succeed with graceful degradation
    assert result.success is True
    assert len(result.errors) == 1
    assert "Discovery file not found" in result.errors[0]


@pytest.mark.asyncio
async def test_CompetitorAnalyzer_analyze_with_valid_analysis(mock_agent_executor, temp_output_dir):
    """Test CompetitorAnalyzer.analyze with successful analysis"""
    # Arrange
    refresh = True
    instance = CompetitorAnalyzer(temp_output_dir, refresh, mock_agent_executor)

    # Create discovery file
    discovery_data = {
        "project_name": "Test Project",
        "target_audience": {"primary": "developers"},
        "product_vision": "A great product",
    }
    with open(instance.discovery_file, "w", encoding="utf-8") as f:
        json.dump(discovery_data, f)

    # Mock agent to create a valid analysis file
    async def mock_run_agent(prompt_file, additional_context=""):
        # Create a valid analysis file
        analysis_data = {
            "enabled": True,
            "competitors": [
                {
                    "name": "Competitor 1",
                    "pain_points": ["Issue 1", "Issue 2"],
                }
            ],
            "market_gaps": [],
            "insights_summary": {
                "top_pain_points": [],
                "differentiator_opportunities": [],
                "market_trends": [],
            },
        }
        with open(instance.analysis_file, "w", encoding="utf-8") as f:
            json.dump(analysis_data, f)
        return True, "Analysis complete"

    mock_agent_executor.run_agent = mock_run_agent

    # Act
    result = await instance.analyze(enabled=True)

    # Assert
    assert result is not None
    assert result.success is True
    assert result.retries == 0
    assert len(result.errors) == 0
