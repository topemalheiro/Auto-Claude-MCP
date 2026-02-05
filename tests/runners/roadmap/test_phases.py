"""Tests for phases"""

import json
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from runners.roadmap.models import RoadmapPhaseResult
from runners.roadmap.phases import DiscoveryPhase, FeaturesPhase, ProjectIndexPhase


@pytest.fixture
def mock_script_executor():
    """Create a mock script executor."""
    executor = MagicMock()
    executor.run_script = MagicMock(return_value=(True, "Success"))
    return executor


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


# ProjectIndexPhase Tests


def test_ProjectIndexPhase___init__(mock_script_executor, temp_output_dir):
    """Test ProjectIndexPhase.__init__"""
    # Arrange & Act
    refresh = True
    instance = ProjectIndexPhase(temp_output_dir, refresh, mock_script_executor)

    # Assert
    assert instance is not None
    assert instance.output_dir == temp_output_dir
    assert instance.refresh is refresh
    assert instance.script_executor == mock_script_executor
    assert instance.project_index == temp_output_dir / "project_index.json"


@pytest.mark.asyncio
async def test_ProjectIndexPhase_execute_copies_existing_index(
    mock_script_executor, temp_output_dir, tmp_path
):
    """Test ProjectIndexPhase.execute when auto-claude index exists"""
    # Arrange
    refresh = False
    instance = ProjectIndexPhase(temp_output_dir, refresh, mock_script_executor)

    # Create an existing auto-claude project index at the expected location
    # The auto_build_index is calculated as parent.parent / project_index.json
    # which would be: roadmap -> runners -> backend / project_index.json
    # We need to create the file where the code expects it
    runners_dir = Path(__file__).parent.parent.parent  # Goes up from roadmap/ to runners/
    auto_build_index = runners_dir / "project_index.json"

    # Create a temporary auto-claude structure for this test
    # We'll mock the auto_build_index path to point to a temp location
    test_index_file = tmp_path / "runners" / "project_index.json"
    test_index_file.parent.mkdir(parents=True)
    test_index_file.write_text('{"test": "data"}')

    # Patch the auto_build_index to use our test file
    instance.auto_build_index = test_index_file

    # Act
    result = await instance.execute()

    # Assert
    assert result is not None
    assert isinstance(result, RoadmapPhaseResult)
    assert result.phase == "project_index"
    assert result.success is True
    assert instance.project_index.exists()
    mock_script_executor.run_script.assert_not_called()


@pytest.mark.asyncio
async def test_ProjectIndexPhase_execute_file_exists_no_refresh(
    mock_script_executor, temp_output_dir
):
    """Test ProjectIndexPhase.execute when index file exists and not refreshing"""
    # Arrange
    refresh = False
    instance = ProjectIndexPhase(temp_output_dir, refresh, mock_script_executor)

    # Create existing index
    instance.project_index.write_text('{"test": "data"}')

    # Act
    result = await instance.execute()

    # Assert
    assert result is not None
    assert result.success is True
    assert result.retries == 0
    mock_script_executor.run_script.assert_not_called()


@pytest.mark.asyncio
async def test_ProjectIndexPhase_execute_runs_analyzer(
    mock_script_executor, temp_output_dir
):
    """Test ProjectIndexPhase.execute runs analyzer when needed"""
    # Arrange
    refresh = True
    instance = ProjectIndexPhase(temp_output_dir, refresh, mock_script_executor)

    # Act
    result = await instance.execute()

    # Assert
    assert result is not None
    assert isinstance(result, RoadmapPhaseResult)
    assert result.phase == "project_index"
    mock_script_executor.run_script.assert_called_once()


# DiscoveryPhase Tests


def test_DiscoveryPhase___init__(mock_agent_executor, temp_output_dir):
    """Test DiscoveryPhase.__init__"""
    # Arrange & Act
    refresh = True
    instance = DiscoveryPhase(temp_output_dir, refresh, mock_agent_executor)

    # Assert
    assert instance is not None
    assert instance.output_dir == temp_output_dir
    assert instance.refresh is refresh
    assert instance.agent_executor == mock_agent_executor
    assert instance.discovery_file == temp_output_dir / "roadmap_discovery.json"
    assert instance.project_index_file == temp_output_dir / "project_index.json"


@pytest.mark.asyncio
async def test_DiscoveryPhase_execute_file_exists_no_refresh(
    mock_agent_executor, temp_output_dir
):
    """Test DiscoveryPhase.execute when file exists and not refreshing"""
    # Arrange
    refresh = False
    instance = DiscoveryPhase(temp_output_dir, refresh, mock_agent_executor)

    # Create existing discovery file
    discovery_data = {
        "project_name": "Test",
        "target_audience": {"primary": "developers"},
        "product_vision": "A vision",
    }
    with open(instance.discovery_file, "w", encoding="utf-8") as f:
        json.dump(discovery_data, f)

    # Act
    result = await instance.execute()

    # Assert
    assert result is not None
    assert isinstance(result, RoadmapPhaseResult)
    assert result.phase == "discovery"
    assert result.success is True
    assert result.retries == 0
    mock_agent_executor.run_agent.assert_not_called()


@pytest.mark.asyncio
async def test_DiscoveryPhase_execute_creates_valid_file(
    mock_agent_executor, temp_output_dir
):
    """Test DiscoveryPhase.execute creates valid discovery file"""
    # Arrange
    refresh = True
    instance = DiscoveryPhase(temp_output_dir, refresh, mock_agent_executor)

    # Mock agent to create a valid discovery file
    async def mock_run_agent(prompt_file, additional_context=""):
        discovery_data = {
            "project_name": "Test Project",
            "target_audience": {"primary": "developers"},
            "product_vision": "A great product",
        }
        with open(instance.discovery_file, "w", encoding="utf-8") as f:
            json.dump(discovery_data, f)
        return True, "Discovery complete"

    mock_agent_executor.run_agent = mock_run_agent

    # Act
    result = await instance.execute()

    # Assert
    assert result is not None
    assert result.success is True
    assert result.retries == 0
    assert len(result.errors) == 0


# FeaturesPhase Tests


def test_FeaturesPhase___init__(mock_agent_executor, temp_output_dir):
    """Test FeaturesPhase.__init__"""
    # Arrange & Act
    refresh = True
    instance = FeaturesPhase(temp_output_dir, refresh, mock_agent_executor)

    # Assert
    assert instance is not None
    assert instance.output_dir == temp_output_dir
    assert instance.refresh is refresh
    assert instance.agent_executor == mock_agent_executor
    assert instance.roadmap_file == temp_output_dir / "roadmap.json"
    assert instance.discovery_file == temp_output_dir / "roadmap_discovery.json"
    assert instance.project_index_file == temp_output_dir / "project_index.json"
    assert instance._preserved_features == []


@pytest.mark.asyncio
async def test_FeaturesPhase_execute_no_discovery_file(
    mock_agent_executor, temp_output_dir
):
    """Test FeaturesPhase.execute when discovery file is missing"""
    # Arrange
    refresh = True
    instance = FeaturesPhase(temp_output_dir, refresh, mock_agent_executor)

    # Act
    result = await instance.execute()

    # Assert
    assert result is not None
    assert isinstance(result, RoadmapPhaseResult)
    assert result.phase == "features"
    assert result.success is False
    assert len(result.errors) == 1
    assert "Discovery file not found" in result.errors[0]


@pytest.mark.asyncio
async def test_FeaturesPhase_execute_file_exists_no_refresh(
    mock_agent_executor, temp_output_dir
):
    """Test FeaturesPhase.execute when roadmap exists and not refreshing"""
    # Arrange
    refresh = False
    instance = FeaturesPhase(temp_output_dir, refresh, mock_agent_executor)

    # Create existing roadmap file
    # Need to create the directory first
    temp_output_dir.mkdir(parents=True, exist_ok=True)

    # ALSO need to create the discovery file (checked first in execute())
    discovery_data = {
        "project_name": "Test",
        "target_audience": {"primary": "developers"},
        "product_vision": "A vision",
    }
    with open(instance.discovery_file, "w", encoding="utf-8") as f:
        json.dump(discovery_data, f)

    roadmap_data = {
        "phases": [],
        "features": [],
        "vision": "A vision",
        "target_audience": {"primary": "developers"},
    }
    with open(instance.roadmap_file, "w", encoding="utf-8") as f:
        json.dump(roadmap_data, f)

    # Act
    result = await instance.execute()

    # Assert
    assert result is not None
    assert result.success is True
    assert result.retries == 0
    mock_agent_executor.run_agent.assert_not_called()


@pytest.mark.asyncio
async def test_FeaturesPhase_execute_creates_valid_roadmap(
    mock_agent_executor, temp_output_dir
):
    """Test FeaturesPhase.execute creates valid roadmap"""
    # Arrange
    refresh = True
    instance = FeaturesPhase(temp_output_dir, refresh, mock_agent_executor)

    # Create required discovery file
    discovery_data = {
        "project_name": "Test Project",
        "target_audience": {"primary": "developers"},
        "product_vision": "A great product",
    }
    with open(instance.discovery_file, "w", encoding="utf-8") as f:
        json.dump(discovery_data, f)

    # Mock agent to create a valid roadmap file
    async def mock_run_agent(prompt_file, additional_context=""):
        roadmap_data = {
            "phases": [
                {"id": "phase-1", "name": "Phase 1", "features": ["feature-1", "feature-2"]}
            ],
            "features": [
                {
                    "id": "feature-1",
                    "title": "Feature 1",
                    "priority": "high",
                    "status": "pending",
                    "source": {"provider": "ai", "suggestions": []},
                },
                {
                    "id": "feature-2",
                    "title": "Feature 2",
                    "priority": "medium",
                    "status": "pending",
                    "source": {"provider": "ai", "suggestions": []},
                },
                {
                    "id": "feature-3",
                    "title": "Feature 3",
                    "priority": "low",
                    "status": "pending",
                    "source": {"provider": "ai", "suggestions": []},
                },
            ],
            "vision": "A great product",
            "target_audience": {"primary": "developers"},
        }
        with open(instance.roadmap_file, "w", encoding="utf-8") as f:
            json.dump(roadmap_data, f)
        return True, "Features generated"

    mock_agent_executor.run_agent = mock_run_agent

    # Act
    result = await instance.execute()

    # Assert
    assert result is not None
    assert result.success is True
    assert result.retries == 0
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_FeaturesPhase_load_existing_features_preserves_internal(
    mock_agent_executor, temp_output_dir
):
    """Test FeaturesPhase._load_existing_features preserves internal source features"""
    # Arrange
    refresh = True
    instance = FeaturesPhase(temp_output_dir, refresh, mock_agent_executor)

    # Create existing roadmap with internal features
    # Ensure the directory exists
    temp_output_dir.mkdir(parents=True, exist_ok=True)
    roadmap_data = {
        "phases": [],
        "features": [
            {
                "id": "feature-1",
                "title": "Internal Feature",
                "priority": "high",
                "status": "planned",
                "source": {"provider": "internal"},
            },
            {
                "id": "feature-2",
                "title": "AI Feature",
                "priority": "medium",
                "status": "pending",
                "source": {"provider": "ai"},
            },
        ],
        "vision": "A vision",
        "target_audience": {"primary": "developers"},
    }
    with open(instance.roadmap_file, "w", encoding="utf-8") as f:
        json.dump(roadmap_data, f)

    # Create discovery file
    discovery_data = {
        "project_name": "Test",
        "target_audience": {"primary": "developers"},
        "product_vision": "A vision",
    }
    with open(instance.discovery_file, "w", encoding="utf-8") as f:
        json.dump(discovery_data, f)

    # Mock agent to create new roadmap with at least 3 features (required for validation)
    async def mock_run_agent(prompt_file, additional_context=""):
        roadmap_data = {
            "phases": [],
            "features": [
                {
                    "id": "feature-3",
                    "title": "New Feature 1",
                    "priority": "high",
                    "status": "pending",
                    "source": {"provider": "ai"},
                },
                {
                    "id": "feature-4",
                    "title": "New Feature 2",
                    "priority": "medium",
                    "status": "pending",
                    "source": {"provider": "ai"},
                },
                {
                    "id": "feature-5",
                    "title": "New Feature 3",
                    "priority": "low",
                    "status": "pending",
                    "source": {"provider": "ai"},
                },
            ],
            "vision": "A vision",
            "target_audience": {"primary": "developers"},
        }
        with open(instance.roadmap_file, "w", encoding="utf-8") as f:
            json.dump(roadmap_data, f)
        return True, "Features generated"

    mock_agent_executor.run_agent = mock_run_agent

    # Act
    result = await instance.execute()

    # Assert
    assert result is not None
    assert result.success is True

    # Verify preserved features were merged
    with open(instance.roadmap_file, encoding="utf-8") as f:
        final_roadmap = json.load(f)
    # Should have internal feature preserved + new features
    feature_ids = [f.get("id") for f in final_roadmap.get("features", [])]
    assert "feature-1" in feature_ids  # Internal preserved
    assert "feature-3" in feature_ids  # New added
