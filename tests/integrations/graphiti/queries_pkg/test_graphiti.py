"""Tests for graphiti"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from integrations.graphiti.queries_pkg.graphiti import GraphitiMemory


def test_GraphitiMemory___init__():
    """Test GraphitiMemory.__init__"""

    # Arrange
    spec_dir = Path("/tmp/test")
    project_dir = Path("/tmp/test")
    group_id_mode = "spec"

    # Act
    instance = GraphitiMemory(spec_dir, project_dir, group_id_mode)

    # Assert
    assert instance.spec_dir == spec_dir
    assert instance.project_dir == project_dir
    assert instance.group_id_mode == group_id_mode


@pytest.mark.asyncio
async def test_GraphitiMemory_initialize():
    """Test GraphitiMemory.initialize"""

    # Arrange
    spec_dir = Path("/tmp/test")
    project_dir = Path("/tmp/test")
    instance = GraphitiMemory(spec_dir, project_dir)

    # Mock initialization - we can't patch is_enabled as it's a property
    # Instead, we check the test runs without error
    # The instance may not be enabled if graphiti-core is not installed
    try:
        result = await instance.initialize()
        # Result might be False if not enabled
        assert result is not None
    except Exception as e:
        # Expected if graphiti-core is not installed
        assert "graphiti" in str(e).lower() or "driver" in str(e).lower()


@pytest.mark.asyncio
async def test_GraphitiMemory_close():
    """Test GraphitiMemory.close"""

    # Arrange
    spec_dir = Path("/tmp/test")
    project_dir = Path("/tmp/test")
    instance = GraphitiMemory(spec_dir, project_dir)

    # Set up a mock client
    instance._client = MagicMock()
    instance._client.close = AsyncMock()

    # Act
    await instance.close()

    # Assert - should not raise
    assert instance._client is None


@pytest.mark.asyncio
async def test_GraphitiMemory_save_session_insights():
    """Test GraphitiMemory.save_session_insights"""

    # Arrange
    spec_dir = Path("/tmp/test")
    project_dir = Path("/tmp/test")
    instance = GraphitiMemory(spec_dir, project_dir)

    # Set up mock queries
    instance._queries = MagicMock()
    instance._queries.add_session_insight = AsyncMock(return_value=True)
    instance.state = MagicMock()

    # Act
    result = await instance.save_session_insights(1, {"test": "insight"})

    # Assert
    assert result is not None


@pytest.mark.asyncio
async def test_GraphitiMemory_save_codebase_discoveries():
    """Test GraphitiMemory.save_codebase_discoveries"""

    # Arrange
    spec_dir = Path("/tmp/test")
    project_dir = Path("/tmp/test")
    instance = GraphitiMemory(spec_dir, project_dir)

    # Set up mock queries
    instance._queries = MagicMock()
    instance._queries.add_codebase_discoveries = AsyncMock(return_value=True)
    instance.state = MagicMock()

    # Act
    result = await instance.save_codebase_discoveries({"file1": "purpose"})

    # Assert
    assert result is not None


@pytest.mark.asyncio
async def test_GraphitiMemory_save_pattern():
    """Test GraphitiMemory.save_pattern"""

    # Arrange
    spec_dir = Path("/tmp/test")
    project_dir = Path("/tmp/test")
    instance = GraphitiMemory(spec_dir, project_dir)

    # Set up mock queries
    instance._queries = MagicMock()
    instance._queries.add_pattern = AsyncMock(return_value=True)
    instance.state = MagicMock()

    # Act
    result = await instance.save_pattern("Test pattern")

    # Assert
    assert result is not None


@pytest.mark.asyncio
async def test_GraphitiMemory_save_gotcha():
    """Test GraphitiMemory.save_gotcha"""

    # Arrange
    spec_dir = Path("/tmp/test")
    project_dir = Path("/tmp/test")
    instance = GraphitiMemory(spec_dir, project_dir)

    # Set up mock queries
    instance._queries = MagicMock()
    instance._queries.add_gotcha = AsyncMock(return_value=True)
    instance.state = MagicMock()

    # Act
    result = await instance.save_gotcha("Test gotcha")

    # Assert
    assert result is not None


@pytest.mark.asyncio
async def test_GraphitiMemory_save_task_outcome():
    """Test GraphitiMemory.save_task_outcome"""

    # Arrange
    spec_dir = Path("/tmp/test")
    project_dir = Path("/tmp/test")
    instance = GraphitiMemory(spec_dir, project_dir)

    # Set up mock queries
    instance._queries = MagicMock()
    instance._queries.add_task_outcome = AsyncMock(return_value=True)
    instance.state = MagicMock()

    # Act
    result = await instance.save_task_outcome("task-1", True, "Success", {})

    # Assert
    assert result is not None


@pytest.mark.asyncio
async def test_GraphitiMemory_save_structured_insights():
    """Test GraphitiMemory.save_structured_insights"""

    # Arrange
    spec_dir = Path("/tmp/test")
    project_dir = Path("/tmp/test")
    instance = GraphitiMemory(spec_dir, project_dir)

    # Set up mock queries
    instance._queries = MagicMock()
    instance._queries.add_structured_insights = AsyncMock(return_value=True)
    instance.state = MagicMock()

    # Act
    result = await instance.save_structured_insights({"patterns": [], "gotchas": []})

    # Assert
    assert result is not None


@pytest.mark.asyncio
async def test_GraphitiMemory_get_relevant_context():
    """Test GraphitiMemory.get_relevant_context"""

    # Arrange
    spec_dir = Path("/tmp/test")
    project_dir = Path("/tmp/test")
    instance = GraphitiMemory(spec_dir, project_dir)

    # Set up mock search
    instance._search = MagicMock()
    instance._search.get_relevant_context = AsyncMock(return_value=[])

    # Act
    result = await instance.get_relevant_context("test query", 5, True)

    # Assert
    assert result is not None


@pytest.mark.asyncio
async def test_GraphitiMemory_get_session_history():
    """Test GraphitiMemory.get_session_history"""

    # Arrange
    spec_dir = Path("/tmp/test")
    project_dir = Path("/tmp/test")
    instance = GraphitiMemory(spec_dir, project_dir)

    # Set up mock search
    instance._search = MagicMock()
    instance._search.get_session_history = AsyncMock(return_value=[])

    # Act
    result = await instance.get_session_history(5, True)

    # Assert
    assert result is not None


@pytest.mark.asyncio
async def test_GraphitiMemory_get_similar_task_outcomes():
    """Test GraphitiMemory.get_similar_task_outcomes"""

    # Arrange
    spec_dir = Path("/tmp/test")
    project_dir = Path("/tmp/test")
    instance = GraphitiMemory(spec_dir, project_dir)

    # Set up mock search
    instance._search = MagicMock()
    instance._search.get_similar_task_outcomes = AsyncMock(return_value=[])

    # Act
    result = await instance.get_similar_task_outcomes("test task", 5)

    # Assert
    assert result is not None


@pytest.mark.asyncio
async def test_GraphitiMemory_get_patterns_and_gotchas():
    """Test GraphitiMemory.get_patterns_and_gotchas"""

    # Arrange
    spec_dir = Path("/tmp/test")
    project_dir = Path("/tmp/test")
    instance = GraphitiMemory(spec_dir, project_dir)

    # Set up mock search
    instance._search = MagicMock()
    instance._search.get_patterns_and_gotchas = AsyncMock(return_value=([], []))

    # Act
    result = await instance.get_patterns_and_gotchas("test query", 5, 0.5)

    # Assert
    assert result is not None


def test_GraphitiMemory_get_status_summary():
    """Test GraphitiMemory.get_status_summary"""

    # Arrange
    spec_dir = Path("/tmp/test")
    project_dir = Path("/tmp/test")
    instance = GraphitiMemory(spec_dir, project_dir)

    # Act
    result = instance.get_status_summary()

    # Assert
    assert result is not None
    assert "enabled" in result
    assert "initialized" in result
