"""Tests for insights_runner.py

Comprehensive tests for the Insights Runner which provides AI chat for codebase insights.
"""

from runners.insights_runner import (
    build_system_prompt,
    load_project_context,
    main,
    run_simple,
    run_with_sdk,
)
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import subprocess
import json


@pytest.fixture
def mock_project_dir(tmp_path):
    """Create a mock project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create .auto-claude directory structure
    auto_claude_dir = project_dir / ".auto-claude"
    auto_claude_dir.mkdir(parents=True, exist_ok=True)

    # Create project_index.json
    project_index = {
        "project_root": str(project_dir),
        "project_type": "python",
        "services": {
            "backend": {"type": "backend"},
            "frontend": {"type": "frontend"},
        },
        "infrastructure": {"database": "postgresql"},
    }
    (auto_claude_dir / "project_index.json").write_text(
        json.dumps(project_index), encoding="utf-8"
    )

    # Create specs directory
    specs_dir = auto_claude_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / "001-test-spec").mkdir(parents=True, exist_ok=True)

    # Create roadmap directory
    roadmap_dir = auto_claude_dir / "roadmap"
    roadmap_dir.mkdir(parents=True, exist_ok=True)
    roadmap = {
        "features": [
            {"title": "Feature 1", "status": "pending"},
            {"title": "Feature 2", "status": "completed"},
        ]
    }
    (roadmap_dir / "roadmap.json").write_text(json.dumps(roadmap), encoding="utf-8")

    return project_dir


def test_load_project_context(mock_project_dir):
    """Test load_project_context loads project data."""

    result = load_project_context(str(mock_project_dir))

    assert result is not None
    assert "Project Structure" in result
    assert "Roadmap Features" in result
    assert "Existing Tasks/Specs" in result
    assert "python" in result
    assert "backend" in result


def test_load_project_context_with_empty_inputs(tmp_path):
    """Test load_project_context with empty project directory."""

    empty_dir = tmp_path / "empty_project"
    empty_dir.mkdir(parents=True, exist_ok=True)

    result = load_project_context(str(empty_dir))

    # Should return default message when no context available
    assert result == "No project context available yet."


def test_load_project_context_with_invalid_json(tmp_path):
    """Test load_project_context handles invalid JSON gracefully."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    auto_claude_dir = project_dir / ".auto-claude"
    auto_claude_dir.mkdir(parents=True, exist_ok=True)

    # Create invalid JSON file
    (auto_claude_dir / "project_index.json").write_text("{ invalid json", encoding="utf-8")

    result = load_project_context(str(project_dir))

    # Should skip invalid JSON and return partial or no context
    assert "Project Structure" not in result or result == "No project context available yet."


def test_load_project_context_with_roadmap_only(tmp_path):
    """Test load_project_context with only roadmap file."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    auto_claude_dir = project_dir / ".auto-claude"
    auto_claude_dir.mkdir(parents=True, exist_ok=True)

    # Only create roadmap, no index or specs
    roadmap_dir = auto_claude_dir / "roadmap"
    roadmap_dir.mkdir(parents=True, exist_ok=True)
    roadmap = {"features": [{"title": "Feature 1", "status": "pending"}]}
    (roadmap_dir / "roadmap.json").write_text(json.dumps(roadmap), encoding="utf-8")

    result = load_project_context(str(project_dir))

    # Should have roadmap but no other context
    assert "Roadmap Features" in result
    assert "Feature 1" in result


def test_build_system_prompt(mock_project_dir):
    """Test build_system_prompt creates a valid system prompt."""

    result = build_system_prompt(str(mock_project_dir))

    assert result is not None
    assert "AI assistant" in result
    assert "codebase" in result
    assert "__TASK_SUGGESTION__" in result
    assert "Project Structure" in result


def test_build_system_prompt_task_categories(mock_project_dir):
    """Test build_system_prompt includes valid task categories."""
    result = build_system_prompt(str(mock_project_dir))

    # Check for task suggestion format
    assert "__TASK_SUGGESTION__" in result

    # Check for valid categories mentioned in prompt
    assert "feature" in result or "bug_fix" in result


@patch("runners.insights_runner.SDK_AVAILABLE", False)
@patch("runners.insights_runner.run_simple")
def test_run_with_sdk_fallback_to_simple(mock_run_simple, mock_project_dir):
    """Test run_with_sdk falls back to simple mode when SDK unavailable."""
    import asyncio

    # run_with_sdk is async, need to await it
    async def test_async():
        await run_with_sdk(
            str(mock_project_dir), "test message", [], "sonnet", "medium"
        )

    asyncio.run(test_async())

    # Should have called run_simple as fallback
    mock_run_simple.assert_called_once()


@patch("runners.insights_runner.SDK_AVAILABLE", True)
@patch("runners.insights_runner.get_auth_token", return_value=None)
@patch("runners.insights_runner.run_simple")
def test_run_with_sdk_fallback_no_auth(mock_run_simple, mock_get_token, mock_project_dir):
    """Test run_with_sdk falls back to simple mode when no auth token."""
    import asyncio

    async def test_async():
        await run_with_sdk(
            str(mock_project_dir), "test message", [], "sonnet", "medium"
        )

    asyncio.run(test_async())

    mock_run_simple.assert_called_once()


@patch("subprocess.run")
def test_run_simple(mock_subprocess_run, mock_project_dir):
    """Test run_simple calls claude CLI."""

    # Mock successful subprocess call
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "AI response here"
    mock_subprocess_run.return_value = mock_result

    # run_simple returns None but prints output
    result = run_simple(str(mock_project_dir), "test message", [])

    # Function returns None (it prints directly)
    assert result is None
    mock_subprocess_run.assert_called_once()


@patch("subprocess.run")
def test_run_simple_with_cli_error(mock_subprocess_run, mock_project_dir):
    """Test run_simple handles CLI errors gracefully."""

    # Mock subprocess failure
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_subprocess_run.return_value = mock_result

    # Should not raise exception, just print fallback message
    result = run_simple(str(mock_project_dir), "test message", [])

    assert result is None


@patch("subprocess.run")
def test_run_simple_timeout(mock_subprocess_run, mock_project_dir):
    """Test run_simple handles timeout."""
    mock_subprocess_run.side_effect = subprocess.TimeoutExpired("claude", 120)

    # Should not raise, print timeout message
    result = run_simple(str(mock_project_dir), "test message", [])

    assert result is None


@patch("subprocess.run")
def test_run_simple_file_not_found(mock_subprocess_run, mock_project_dir):
    """Test run_simple handles FileNotFoundError."""
    mock_subprocess_run.side_effect = FileNotFoundError()

    result = run_simple(str(mock_project_dir), "test message", [])

    assert result is None


@patch("subprocess.run")
def test_run_simple_with_history(mock_subprocess_run, mock_project_dir):
    """Test run_simple includes conversation history."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Response"
    mock_subprocess_run.return_value = mock_result

    history = [
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "First answer"},
    ]

    run_simple(str(mock_project_dir), "Second question", history)

    # Verify subprocess was called
    mock_subprocess_run.assert_called_once()


@patch("runners.insights_runner.asyncio.run")
def test_main(mock_asyncio_run, mock_project_dir):
    """Test main with valid arguments."""

    with patch(
        "sys.argv",
        ["insights_runner.py", "--project-dir", str(mock_project_dir), "--message", "test message"],
    ):
        # main() doesn't return or call sys.exit, so just run it
        main()

    # Should have called asyncio.run
    mock_asyncio_run.assert_called_once()


def test_main_with_empty_inputs(tmp_path):
    """Test main handles missing required arguments."""

    empty_project = tmp_path / "empty"

    with patch(
        "sys.argv",
        ["insights_runner.py", "--project-dir", str(empty_project), "--message", ""],
    ):
        # Should not raise, just run with empty message
        main()


def test_main_with_missing_required_args():
    """Test main exits with error when required args missing."""

    with patch("sys.argv", ["insights_runner.py"]):
        with pytest.raises(SystemExit):
            main()


@patch("runners.insights_runner.asyncio.run")
def test_main_with_history_file(mock_asyncio_run, tmp_path):
    """Test main loads history from file."""
    history_file = tmp_path / "history.json"
    history = [{"role": "user", "content": "Question"}]
    history_file.write_text(json.dumps(history), encoding="utf-8")

    with patch(
        "sys.argv",
        [
            "insights_runner.py",
            "--project-dir",
            str(tmp_path),
            "--message",
            "test",
            "--history-file",
            str(history_file),
        ],
    ):
        main()

    mock_asyncio_run.assert_called_once()


@patch("runners.insights_runner.asyncio.run")
def test_main_with_invalid_history_json(mock_asyncio_run):
    """Test main handles invalid history JSON gracefully."""
    with patch(
        "sys.argv",
        ["insights_runner.py", "--project-dir", "/tmp", "--message", "test", "--history", "{invalid"],
    ):
        # Should default to empty list
        main()

    mock_asyncio_run.assert_called_once()


@patch("runners.insights_runner.asyncio.run")
def test_main_with_custom_model(mock_asyncio_run, mock_project_dir):
    """Test main with custom model argument."""
    with patch(
        "sys.argv",
        [
            "insights_runner.py",
            "--project-dir",
            str(mock_project_dir),
            "--message",
            "test",
            "--model",
            "opus",
        ],
    ):
        main()

    mock_asyncio_run.assert_called_once()


@patch("runners.insights_runner.asyncio.run")
def test_main_with_thinking_level(mock_asyncio_run, mock_project_dir):
    """Test main with thinking level argument."""
    with patch(
        "sys.argv",
        [
            "insights_runner.py",
            "--project-dir",
            str(mock_project_dir),
            "--message",
            "test",
            "--thinking-level",
            "high",
        ],
    ):
        main()

    mock_asyncio_run.assert_called_once()


@patch("runners.insights_runner.asyncio.run")
def test_main_with_nonexistent_history_file(mock_asyncio_run, tmp_path):
    """Test main handles missing history file gracefully."""
    with patch(
        "sys.argv",
        [
            "insights_runner.py",
            "--project-dir",
            str(tmp_path),
            "--message",
            "test",
            "--history-file",
            "/nonexistent/file.json",
        ],
    ):
        # Should default to empty list
        main()

    mock_asyncio_run.assert_called_once()
