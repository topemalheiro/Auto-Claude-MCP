"""Tests for project_index_phase"""

from ideation.project_index_phase import ProjectIndexPhase
from ideation.script_runner import ScriptRunner
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock, Mock
import pytest


def test_ProjectIndexPhase___init__():
    """Test ProjectIndexPhase.__init__"""
    project_dir = Path("/tmp/test")
    output_dir = Path("/tmp/output")
    refresh = True

    phase = ProjectIndexPhase(project_dir, output_dir, refresh)

    assert phase.project_dir == project_dir
    assert phase.output_dir == output_dir
    assert phase.refresh is refresh
    assert isinstance(phase.script_runner, ScriptRunner)


@pytest.mark.asyncio
@patch("ideation.project_index_phase.shutil.copy")
@patch("pathlib.Path.exists")
async def test_ProjectIndexPhase_execute_auto_build_exists(mock_exists, mock_copy):
    """Test ProjectIndexPhase.execute when auto_build index exists"""
    # Auto build index exists - make exists() return True for the auto_build path
    # We need to track which path is being checked

    call_count = [0]  # Use list to allow modification in closure

    def exists_side_effect():
        call_count[0] += 1
        # First call is auto_build_index.exists() - should return True
        # Second call is project_index.exists() - should return False
        return call_count[0] == 1

    mock_exists.side_effect = exists_side_effect

    project_dir = Path("/tmp/test")
    output_dir = Path("/tmp/output")
    phase = ProjectIndexPhase(project_dir, output_dir, refresh=False)

    result = await phase.execute()

    assert result.phase == "project_index"
    assert result.success is True
    assert len(result.output_files) > 0


@pytest.mark.asyncio
@patch("pathlib.Path.exists")
async def test_ProjectIndexPhase_execute_exists_no_refresh(mock_exists):
    """Test ProjectIndexPhase.execute when index exists and no refresh"""
    # Auto build doesn't exist, output project_index exists
    call_count = [0]

    def exists_side_effect():
        call_count[0] += 1
        # First call is auto_build_index.exists() - return False
        # Second call is project_index.exists() - return True
        return call_count[0] == 2

    mock_exists.side_effect = exists_side_effect

    project_dir = Path("/tmp/test")
    output_dir = Path("/tmp/output")
    phase = ProjectIndexPhase(project_dir, output_dir, refresh=False)

    result = await phase.execute()

    assert result.phase == "project_index"
    assert result.success is True
