"""Tests for output_streamer"""

from ideation.output_streamer import OutputStreamer
from ideation.types import IdeationPhaseResult
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock, Mock
import pytest
import sys


@patch("builtins.print")
def test_OutputStreamer_stream_ideation_complete(mock_print):
    """Test OutputStreamer.stream_ideation_complete"""
    ideation_type = "code_improvements"
    ideas_count = 5

    OutputStreamer.stream_ideation_complete(ideation_type, ideas_count)

    mock_print.assert_called_once_with(f"IDEATION_TYPE_COMPLETE:{ideation_type}:{ideas_count}")


@patch("builtins.print")
def test_OutputStreamer_stream_ideation_failed(mock_print):
    """Test OutputStreamer.stream_ideation_failed"""
    ideation_type = "security_hardening"

    OutputStreamer.stream_ideation_failed(ideation_type)

    mock_print.assert_called_once_with(f"IDEATION_TYPE_FAILED:{ideation_type}")


@pytest.mark.asyncio
async def test_OutputStreamer_stream_ideation_result():
    """Test OutputStreamer.stream_ideation_result"""
    ideation_type = "code_improvements"
    max_retries = 3

    # Mock phase executor
    phase_executor = Mock()
    phase_executor.execute_ideation_type = AsyncMock(
        return_value=IdeationPhaseResult(
            phase="code_improvements",
            ideation_type=ideation_type,
            success=True,
            output_files=["/tmp/output/code_improvements_ideas.json"],
            ideas_count=3,
            errors=[],
            retries=0,
        )
    )

    streamer = OutputStreamer()

    with patch("builtins.print") as mock_print:
        result = await streamer.stream_ideation_result(ideation_type, phase_executor, max_retries)

        assert result.success is True
        assert result.ideas_count == 3
        mock_print.assert_called()


@pytest.mark.asyncio
async def test_OutputStreamer_stream_ideation_result_failure():
    """Test OutputStreamer.stream_ideation_result with failure"""
    ideation_type = "security_hardening"
    max_retries = 3

    # Mock phase executor returning failure
    phase_executor = Mock()
    phase_executor.execute_ideation_type = AsyncMock(
        return_value=IdeationPhaseResult(
            phase=ideation_type,
            ideation_type=ideation_type,
            success=False,
            output_files=[],
            ideas_count=0,
            errors=["Generation failed"],
            retries=1,
        )
    )

    streamer = OutputStreamer()

    with patch("builtins.print") as mock_print:
        result = await streamer.stream_ideation_result(ideation_type, phase_executor, max_retries)

        assert result.success is False
        mock_print.assert_called()
