"""Tests for config"""

from ideation.config import IdeationConfigManager
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
import pytest


@patch("ideation.config.init_auto_claude_dir")
def test_IdeationConfigManager___init__(mock_init):
    """Test IdeationConfigManager.__init__"""
    mock_init.return_value = (Path("/tmp/test/.auto-claude"), False)

    project_dir = Path("/tmp/test")
    output_dir = Path("/tmp/output")
    enabled_types = ["code_improvements", "security_hardening"]
    max_ideas_per_type = 10
    model = "sonnet"
    thinking_level = "high"

    with patch("ideation.config.IdeationGenerator") as mock_gen, \
         patch("ideation.config.ProjectAnalyzer") as mock_analyzer, \
         patch("ideation.config.IdeaPrioritizer") as mock_prioritizer, \
         patch("ideation.config.IdeationFormatter") as mock_formatter:

        config = IdeationConfigManager(
            project_dir=project_dir,
            output_dir=output_dir,
            enabled_types=enabled_types,
            include_roadmap_context=True,
            include_kanban_context=False,
            max_ideas_per_type=max_ideas_per_type,
            model=model,
            thinking_level=thinking_level,
            refresh=True,
            append=False,
        )

        # Compare paths without resolve() since the implementation stores paths as-is
        # On Windows, /tmp/test doesn't resolve to D:/tmp/test in the implementation
        assert str(config.project_dir) == str(project_dir)
        assert config.model == model
        assert config.thinking_level == thinking_level
        assert config.refresh is True
        assert config.append is False
        assert config.enabled_types == enabled_types
        assert config.include_roadmap_context is True
        assert config.include_kanban_context is False
        assert config.max_ideas_per_type == max_ideas_per_type
        assert str(config.output_dir) == str(output_dir)


@patch("ideation.config.init_auto_claude_dir")
def test_IdeationConfigManager_default_values(mock_init):
    """Test IdeationConfigManager with default values"""
    mock_init.return_value = (Path("/tmp/test/.auto-claude"), False)

    project_dir = Path("/tmp/test")

    with patch("ideation.config.IdeationGenerator") as mock_gen, \
         patch("ideation.config.ProjectAnalyzer") as mock_analyzer, \
         patch("ideation.config.IdeaPrioritizer") as mock_prioritizer, \
         patch("ideation.config.IdeationFormatter") as mock_formatter:

        config = IdeationConfigManager(project_dir=project_dir)

        # Use resolve() for cross-platform compatibility (macOS /tmp -> /private/tmp)
        assert config.project_dir == project_dir.resolve()
        assert config.model == "sonnet"
        assert config.thinking_level == "medium"
        assert config.refresh is False
        assert config.append is False
        assert config.max_ideas_per_type == 5
        assert config.include_roadmap_context is True
        assert config.include_kanban_context is True
