"""Tests for phase_executor"""

from ideation.phase_executor import PhaseExecutor
from ideation.types import IdeationPhaseResult
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock, Mock, mock_open
import pytest


def test_PhaseExecutor___init__():
    """Test PhaseExecutor.__init__"""
    output_dir = Path("/tmp/output")
    generator = Mock()
    analyzer = Mock()
    prioritizer = Mock()
    formatter = Mock()
    enabled_types = ["code_improvements", "security_hardening"]
    max_ideas_per_type = 10
    refresh = True
    append = False

    executor = PhaseExecutor(
        output_dir=output_dir,
        generator=generator,
        analyzer=analyzer,
        prioritizer=prioritizer,
        formatter=formatter,
        enabled_types=enabled_types,
        max_ideas_per_type=max_ideas_per_type,
        refresh=refresh,
        append=append,
    )

    assert executor.output_dir == output_dir
    assert executor.generator == generator
    assert executor.analyzer == analyzer
    assert executor.prioritizer == prioritizer
    assert executor.formatter == formatter
    assert executor.enabled_types == enabled_types
    assert executor.max_ideas_per_type == max_ideas_per_type
    assert executor.refresh is refresh
    assert executor.append is append


@pytest.mark.asyncio
@patch("graphiti_providers.is_graphiti_enabled")
@patch("builtins.open", new_callable=mock_open)
@patch("ideation.phase_executor.Path.exists")
async def test_PhaseExecutor_execute_graph_hints_exists(mock_exists, mock_file, mock_graphiti):
    """Test PhaseExecutor.execute_graph_hints when graphiti is disabled"""
    # Make exists() return False to skip early return and trigger the mock for write
    mock_exists.return_value = False
    mock_graphiti.return_value = False

    output_dir = Path("/tmp/output")
    executor = PhaseExecutor(
        output_dir=output_dir,
        generator=Mock(),
        analyzer=Mock(),
        prioritizer=Mock(),
        formatter=Mock(),
        enabled_types=[],
        max_ideas_per_type=5,
        refresh=False,
        append=False,
    )

    result = await executor.execute_graph_hints()

    assert result.phase == "graph_hints"
    assert result.success is True


@pytest.mark.asyncio
@patch("graphiti_providers.is_graphiti_enabled")
@patch("builtins.open", new_callable=mock_open)
@patch("ideation.phase_executor.Path.exists")
async def test_PhaseExecutor_execute_graph_hints_disabled(mock_exists, mock_file, mock_graphiti):
    """Test PhaseExecutor.execute_graph_hints when graphiti is disabled"""
    # File doesn't exist and graphiti is disabled
    mock_exists.return_value = False
    mock_graphiti.return_value = False

    output_dir = Path("/tmp/output")
    executor = PhaseExecutor(
        output_dir=output_dir,
        generator=Mock(),
        analyzer=Mock(),
        prioritizer=Mock(),
        formatter=Mock(),
        enabled_types=[],
        max_ideas_per_type=5,
        refresh=False,
        append=False,
    )

    result = await executor.execute_graph_hints()

    assert result.phase == "graph_hints"
    assert result.success is True
