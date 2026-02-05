"""Tests for graphiti_integration"""

from context.graphiti_integration import fetch_graph_hints, is_graphiti_enabled
from pathlib import Path
import pytest


@pytest.mark.asyncio
async def test_fetch_graph_hints():
    """Test fetch_graph_hints"""

    # Arrange
    query = "Add authentication to API"
    project_id = "/tmp/test_project"

    # Act
    result = await fetch_graph_hints(query, project_id)

    # Assert
    # Should return a list (empty if Graphiti not enabled)
    assert isinstance(result, list)
    # When Graphiti is disabled, returns empty list
    if not is_graphiti_enabled():
        assert result == []
