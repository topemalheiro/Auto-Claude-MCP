"""Tests for generator"""

from ideation.generator import IdeationGenerator, IDEATION_TYPE_LABELS, IDEATION_TYPE_PROMPTS
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock, Mock
import pytest


def test_IdeationGenerator___init__():
    """Test IdeationGenerator.__init__"""
    project_dir = Path("/tmp/test")
    output_dir = Path("/tmp/output")
    model = "opus"
    thinking_level = "high"
    max_ideas_per_type = 10

    with patch("ideation.generator.get_thinking_budget") as mock_get_budget:
        mock_get_budget.return_value = 10000

        generator = IdeationGenerator(
            project_dir=project_dir,
            output_dir=output_dir,
            model=model,
            thinking_level=thinking_level,
            max_ideas_per_type=max_ideas_per_type,
        )

        # Use resolve() for cross-platform compatibility (macOS /tmp -> /private/tmp)
        assert generator.project_dir == project_dir.resolve()
        assert generator.output_dir == output_dir.resolve()
        assert generator.model == model
        assert generator.thinking_level == thinking_level
        assert generator.max_ideas_per_type == max_ideas_per_type
        assert generator.thinking_budget == 10000


@pytest.mark.asyncio
@patch("ideation.generator.create_client")
async def test_IdeationGenerator_run_agent_success(mock_create_client, tmp_path):
    """Test IdeationGenerator.run_agent with success"""
    # Create a real test prompt file
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    test_prompt_file = prompts_dir / "test_prompt.md"
    test_prompt_file.write_text("# Test Prompt\n\nTest content")

    project_dir = Path("/tmp/test")
    output_dir = Path("/tmp/output")

    with patch("ideation.generator.get_thinking_budget", return_value=10000):
        generator = IdeationGenerator(
            project_dir=project_dir,
            output_dir=output_dir,
        )

    # Override the prompts_dir to use our tmp_path
    generator.prompts_dir = prompts_dir

    # Create mock response message with proper TextBlock
    mock_text_block = Mock()
    mock_text_block.text = "Test response"
    type(mock_text_block).__name__ = "TextBlock"

    mock_message = Mock()
    mock_message.content = [mock_text_block]
    type(mock_message).__name__ = "AssistantMessage"

    # Create async generator for receive_response
    async def async_iter():
        yield mock_message
        # Stop iteration after first message

    # Create a proper async context manager mock
    from unittest.mock import MagicMock

    class MockClientContextManager:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def query(self, prompt):
            pass

        async def receive_response(self):
            async for msg in async_iter():
                yield msg

    mock_client_context = MockClientContextManager()
    mock_create_client.return_value = mock_client_context

    success, output = await generator.run_agent("test_prompt.md", "Additional context")

    assert success is True
    assert output == "Test response"


@pytest.mark.asyncio
@patch("ideation.generator.Path.exists")
async def test_IdeationGenerator_run_agent_not_found(mock_exists):
    """Test IdeationGenerator.run_agent when prompt file not found"""
    mock_exists.return_value = False

    project_dir = Path("/tmp/test")
    output_dir = Path("/tmp/output")

    with patch("ideation.generator.get_thinking_budget", return_value=10000):
        generator = IdeationGenerator(
            project_dir=project_dir,
            output_dir=output_dir,
        )

    success, output = await generator.run_agent("nonexistent.md")

    assert success is False
    assert "Prompt not found" in output


def test_IdeationGenerator_get_prompt_file():
    """Test IdeationGenerator.get_prompt_file (via IDEATION_TYPE_PROMPTS)"""
    assert IDEATION_TYPE_PROMPTS["code_improvements"] == "ideation_code_improvements.md"
    assert IDEATION_TYPE_PROMPTS["ui_ux_improvements"] == "ideation_ui_ux.md"
    assert IDEATION_TYPE_PROMPTS["documentation_gaps"] == "ideation_documentation.md"
    assert IDEATION_TYPE_PROMPTS["security_hardening"] == "ideation_security.md"
    assert IDEATION_TYPE_PROMPTS["performance_optimizations"] == "ideation_performance.md"
    assert IDEATION_TYPE_PROMPTS["code_quality"] == "ideation_code_quality.md"


def test_IdeationGenerator_get_type_label():
    """Test IdeationGenerator.get_type_label (via IDEATION_TYPE_LABELS)"""
    assert IDEATION_TYPE_LABELS["code_improvements"] == "Code Improvements"
    assert IDEATION_TYPE_LABELS["ui_ux_improvements"] == "UI/UX Improvements"
    assert IDEATION_TYPE_LABELS["documentation_gaps"] == "Documentation Gaps"
    assert IDEATION_TYPE_LABELS["security_hardening"] == "Security Hardening"
    assert IDEATION_TYPE_LABELS["performance_optimizations"] == "Performance Optimizations"
    assert IDEATION_TYPE_LABELS["code_quality"] == "Code Quality & Refactoring"
