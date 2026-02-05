"""Tests for executor"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from runners.roadmap.executor import AgentExecutor, ScriptExecutor


def test_ScriptExecutor___init__(tmp_path):
    """Test ScriptExecutor.__init__"""
    # Arrange & Act
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True)
    instance = ScriptExecutor(project_dir)

    # Assert
    assert instance is not None
    assert instance.project_dir == project_dir
    # scripts_base_dir goes up from roadmap/ -> runners/ -> backend/
    # So the parent's parent name should be 'backend' in this context
    assert instance.scripts_base_dir is not None


def test_ScriptExecutor_run_script_not_found(tmp_path, capsys):
    """Test ScriptExecutor.run_script with non-existent script"""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True)
    instance = ScriptExecutor(project_dir)
    script = "nonexistent.py"
    args = []

    # Act
    success, output = instance.run_script(script, args)

    # Assert
    assert success is False
    assert "not found" in output.lower() or "Script not found" in output


def test_ScriptExecutor_run_script_timeout(tmp_path):
    """Test ScriptExecutor.run_script with timeout"""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True)
    instance = ScriptExecutor(project_dir)

    # Create a script file so it passes the existence check
    scripts_dir = instance.scripts_base_dir
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_file = scripts_dir / "test_timeout.py"
    script_file.write_text("import time; time.sleep(400)")

    # Mock subprocess to raise TimeoutExpired
    import subprocess
    from unittest.mock import patch

    # Patch subprocess.run in the executor module where it's imported
    with patch("runners.roadmap.executor.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test_timeout.py", timeout=300)
        success, output = instance.run_script("test_timeout.py", [])

    # Assert
    assert success is False
    assert "timed out" in output.lower()


def test_AgentExecutor___init__(tmp_path):
    """Test AgentExecutor.__init__"""
    # Arrange
    project_dir = tmp_path / "project"
    output_dir = tmp_path / "output"
    model = "sonnet"
    create_client_func = MagicMock()
    thinking_budget = 16000

    # Act
    instance = AgentExecutor(
        project_dir, output_dir, model, create_client_func, thinking_budget
    )

    # Assert
    assert instance is not None
    assert instance.project_dir == project_dir
    assert instance.output_dir == output_dir
    assert instance.model == model
    assert instance.create_client == create_client_func
    assert instance.thinking_budget == thinking_budget
    assert instance.prompts_dir.name == "prompts"


@pytest.mark.asyncio
async def test_AgentExecutor_run_agent_prompt_not_found(tmp_path):
    """Test AgentExecutor.run_agent with non-existent prompt file"""
    # Arrange
    project_dir = tmp_path / "project"
    output_dir = tmp_path / "output"
    model = "sonnet"
    create_client_func = MagicMock()
    instance = AgentExecutor(project_dir, output_dir, model, create_client_func)
    prompt_file = "nonexistent.md"

    # Act
    success, output = await instance.run_agent(prompt_file)

    # Assert
    assert success is False
    assert "not found" in output.lower() or "Prompt not found" in output


@pytest.mark.asyncio
async def test_AgentExecutor_run_agent_with_valid_prompt(tmp_path):
    """Test AgentExecutor.run_agent with valid prompt file"""
    # Arrange
    project_dir = tmp_path / "project"
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True)
    model = "sonnet"

    # Create mock client
    mock_client = AsyncMock()
    mock_client.query = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()

    # Create mock message blocks
    from unittest.mock import MagicMock

    text_block = MagicMock()
    text_block.text = "Test response"
    type(text_block).__name__ = "TextBlock"

    assistant_msg = MagicMock()
    content_list = [text_block]
    type(assistant_msg).content = content_list
    type(assistant_msg).__name__ = "AssistantMessage"

    # Set up receive_response to yield messages
    async def receive_response_gen():
        yield assistant_msg

    mock_client.receive_response = receive_response_gen

    create_client_func = MagicMock(return_value=mock_client)

    instance = AgentExecutor(project_dir, output_dir, model, create_client_func)

    # Create a valid prompt file at the correct location
    # The prompts_dir is calculated relative to this file's location
    # We need to create the prompt file where the executor expects it
    prompts_dir = instance.prompts_dir
    prompts_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = "test_prompt.md"
    (prompts_dir / prompt_file).write_text("Test prompt content")

    # Act
    success, output = await instance.run_agent(prompt_file)

    # Assert
    assert success is True
    assert output == "Test response"
    mock_client.query.assert_called_once()
