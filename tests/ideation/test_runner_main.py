"""Tests for runner"""

from ideation.runner import IdeationOrchestrator
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


@patch("ideation.config.init_auto_claude_dir")
def test_IdeationOrchestrator___init__(mock_init):
    """Test IdeationOrchestrator.__init__"""
    mock_init.return_value = (Path("/tmp/test/.auto-claude"), False)

    project_dir = Path("/tmp/test")
    output_dir = Path("/tmp/output")
    enabled_types = ["code_improvements"]
    max_ideas_per_type = 10
    model = "sonnet"

    with patch("ideation.config.IdeationGenerator") as mock_gen, \
         patch("ideation.config.ProjectAnalyzer") as mock_analyzer, \
         patch("ideation.config.IdeaPrioritizer") as mock_prioritizer, \
         patch("ideation.config.IdeationFormatter") as mock_formatter:

        orchestrator = IdeationOrchestrator(
            project_dir=project_dir,
            output_dir=output_dir,
            enabled_types=enabled_types,
            include_roadmap_context=True,
            include_kanban_context=False,
            max_ideas_per_type=max_ideas_per_type,
            model=model,
            thinking_level="high",
            refresh=True,
            append=False,
        )

        assert orchestrator.project_dir == project_dir
        assert orchestrator.output_dir == output_dir
        assert orchestrator.model == model
        assert orchestrator.enabled_types == enabled_types
        assert orchestrator.max_ideas_per_type == max_ideas_per_type
        assert orchestrator.refresh is True
        assert orchestrator.append is False
