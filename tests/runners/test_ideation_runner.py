"""Tests for ideation_runner.py

Tests the ideation runner facade that provides backward compatibility
while delegating to modular ideation components.
"""

from runners.ideation_runner import main
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture
def mock_project_dir(tmp_path):
    """Create a mock project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


@patch("runners.ideation_runner.IdeationOrchestrator")
@patch("runners.ideation_runner.asyncio.run")
def test_main(mock_asyncio_run, mock_orchestrator_class, mock_project_dir):
    """Test main with valid arguments."""

    # Arrange
    mock_orchestrator = MagicMock()
    mock_orchestrator.run.return_value = True
    mock_orchestrator_class.return_value = mock_orchestrator
    mock_asyncio_run.return_value = True

    with patch(
        "sys.argv", ["ideation_runner.py", "--project", str(mock_project_dir)]
    ):
        # Act & Assert - main() calls sys.exit(), expect SystemExit(0)
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    # Assert - orchestrator was created correctly
    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["project_dir"] == mock_project_dir.resolve()


@patch("runners.ideation_runner.asyncio.run")
def test_main_with_nonexistent_project(mock_asyncio_run, tmp_path):
    """Test main with nonexistent project directory exits with error."""

    # Mock asyncio.run to prevent it from actually running anything
    mock_asyncio_run.return_value = True

    # Use a path that definitely doesn't exist (within tmp_path for safety)
    nonexistent_path = tmp_path / "this_does_not_exist_xyz123"

    with patch("sys.argv", ["ideation_runner.py", "--project", str(nonexistent_path)]):
        # Act & Assert - should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    # asyncio.run should NOT have been called since we exit early
    mock_asyncio_run.assert_not_called()


@patch("runners.ideation_runner.IdeationOrchestrator")
@patch("runners.ideation_runner.asyncio.run")
def test_main_with_invalid_types(mock_asyncio_run, mock_orchestrator_class, mock_project_dir):
    """Test main with invalid ideation types exits with error."""

    with patch(
        "sys.argv",
        ["ideation_runner.py", "--project", str(mock_project_dir), "--types", "invalid_type"],
    ):
        # Act & Assert - should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    # Should not create orchestrator with invalid types
    mock_orchestrator_class.assert_not_called()


@patch("runners.ideation_runner.IdeationOrchestrator")
@patch("runners.ideation_runner.asyncio.run")
def test_main_with_valid_types(mock_asyncio_run, mock_orchestrator_class, mock_project_dir):
    """Test main with valid ideation types."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run.return_value = True
    mock_orchestrator_class.return_value = mock_orchestrator
    mock_asyncio_run.return_value = True

    with patch(
        "sys.argv",
        [
            "ideation_runner.py",
            "--project",
            str(mock_project_dir),
            "--types",
            "code_improvements,security_hardening",
        ],
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    # Assert - orchestrator created with enabled types
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["enabled_types"] == ["code_improvements", "security_hardening"]


@patch("runners.ideation_runner.IdeationOrchestrator")
@patch("runners.ideation_runner.asyncio.run")
def test_main_with_no_roadmap(mock_asyncio_run, mock_orchestrator_class, mock_project_dir):
    """Test main with --no-roadmap flag."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run.return_value = True
    mock_orchestrator_class.return_value = mock_orchestrator
    mock_asyncio_run.return_value = True

    with patch(
        "sys.argv",
        ["ideation_runner.py", "--project", str(mock_project_dir), "--no-roadmap"],
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["include_roadmap_context"] is False


@patch("runners.ideation_runner.IdeationOrchestrator")
@patch("runners.ideation_runner.asyncio.run")
def test_main_with_no_kanban(mock_asyncio_run, mock_orchestrator_class, mock_project_dir):
    """Test main with --no-kanban flag."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run.return_value = True
    mock_orchestrator_class.return_value = mock_orchestrator
    mock_asyncio_run.return_value = True

    with patch(
        "sys.argv",
        ["ideation_runner.py", "--project", str(mock_project_dir), "--no-kanban"],
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["include_kanban_context"] is False


@patch("runners.ideation_runner.IdeationOrchestrator")
@patch("runners.ideation_runner.asyncio.run")
def test_main_with_max_ideas(mock_asyncio_run, mock_orchestrator_class, mock_project_dir):
    """Test main with custom max-ideas argument."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run.return_value = True
    mock_orchestrator_class.return_value = mock_orchestrator
    mock_asyncio_run.return_value = True

    with patch(
        "sys.argv",
        ["ideation_runner.py", "--project", str(mock_project_dir), "--max-ideas", "10"],
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["max_ideas_per_type"] == 10


@patch("runners.ideation_runner.IdeationOrchestrator")
@patch("runners.ideation_runner.asyncio.run")
def test_main_with_custom_model(mock_asyncio_run, mock_orchestrator_class, mock_project_dir):
    """Test main with custom model argument."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run.return_value = True
    mock_orchestrator_class.return_value = mock_orchestrator
    mock_asyncio_run.return_value = True

    with patch(
        "sys.argv",
        ["ideation_runner.py", "--project", str(mock_project_dir), "--model", "opus"],
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["model"] == "opus"


@patch("runners.ideation_runner.IdeationOrchestrator")
@patch("runners.ideation_runner.asyncio.run")
def test_main_with_thinking_level(mock_asyncio_run, mock_orchestrator_class, mock_project_dir):
    """Test main with thinking level argument."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run.return_value = True
    mock_orchestrator_class.return_value = mock_orchestrator
    mock_asyncio_run.return_value = True

    with patch(
        "sys.argv",
        ["ideation_runner.py", "--project", str(mock_project_dir), "--thinking-level", "high"],
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["thinking_level"] == "high"


@patch("runners.ideation_runner.IdeationOrchestrator")
@patch("runners.ideation_runner.asyncio.run")
def test_main_with_refresh(mock_asyncio_run, mock_orchestrator_class, mock_project_dir):
    """Test main with --refresh flag."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run.return_value = True
    mock_orchestrator_class.return_value = mock_orchestrator
    mock_asyncio_run.return_value = True

    with patch(
        "sys.argv",
        ["ideation_runner.py", "--project", str(mock_project_dir), "--refresh"],
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["refresh"] is True


@patch("runners.ideation_runner.IdeationOrchestrator")
@patch("runners.ideation_runner.asyncio.run")
def test_main_with_append(mock_asyncio_run, mock_orchestrator_class, mock_project_dir):
    """Test main with --append flag."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run.return_value = True
    mock_orchestrator_class.return_value = mock_orchestrator
    mock_asyncio_run.return_value = True

    with patch(
        "sys.argv",
        ["ideation_runner.py", "--project", str(mock_project_dir), "--append"],
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["append"] is True


@patch("runners.ideation_runner.IdeationOrchestrator")
@patch("runners.ideation_runner.asyncio.run")
def test_main_with_output_dir(mock_asyncio_run, mock_orchestrator_class, mock_project_dir, tmp_path):
    """Test main with custom output directory."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run.return_value = True
    mock_orchestrator_class.return_value = mock_orchestrator
    mock_asyncio_run.return_value = True

    output_dir = tmp_path / "custom_output"

    with patch(
        "sys.argv",
        [
            "ideation_runner.py",
            "--project",
            str(mock_project_dir),
            "--output",
            str(output_dir),
        ],
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["output_dir"] == output_dir


@patch("runners.ideation_runner.IdeationOrchestrator")
@patch("runners.ideation_runner.asyncio.run")
def test_main_with_keyboard_interrupt(mock_asyncio_run, mock_orchestrator_class, mock_project_dir):
    """Test main handles KeyboardInterrupt gracefully."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run.side_effect = KeyboardInterrupt()
    mock_orchestrator_class.return_value = mock_orchestrator
    mock_asyncio_run.side_effect = KeyboardInterrupt()

    with patch(
        "sys.argv", ["ideation_runner.py", "--project", str(mock_project_dir)]
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


@patch("runners.ideation_runner.IdeationOrchestrator")
@patch("runners.ideation_runner.asyncio.run")
def test_main_orchestrator_failure(mock_asyncio_run, mock_orchestrator_class, mock_project_dir):
    """Test main when orchestrator run returns False."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run.return_value = False
    mock_orchestrator_class.return_value = mock_orchestrator
    mock_asyncio_run.return_value = False

    with patch(
        "sys.argv", ["ideation_runner.py", "--project", str(mock_project_dir)]
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


def test_module_reexports():
    """Test that ideation_runner re-exports expected symbols."""
    from runners.ideation_runner import (
        IDEATION_TYPES,
        IDEATION_TYPE_LABELS,
        IdeationConfig,
        IdeationOrchestrator,
        IdeationPhaseResult,
    )

    # Verify re-exports exist
    assert IdeationOrchestrator is not None
    assert IdeationConfig is not None
    assert IdeationPhaseResult is not None
    assert IDEATION_TYPES is not None
    assert IDEATION_TYPE_LABELS is not None

    # Verify IDEATION_TYPES has expected values
    assert "code_improvements" in IDEATION_TYPES
    assert "security_hardening" in IDEATION_TYPES


def test_ideation_type_labels():
    """Test that ideation type labels are properly defined."""
    from runners.ideation_runner import IDEATION_TYPE_LABELS

    # Check some expected labels
    assert "code_improvements" in IDEATION_TYPE_LABELS
    assert "ui_ux_improvements" in IDEATION_TYPE_LABELS
    assert "security_hardening" in IDEATION_TYPE_LABELS

    # Check labels are human-readable
    assert "Code" in IDEATION_TYPE_LABELS["code_improvements"]
    assert "UI" in IDEATION_TYPE_LABELS["ui_ux_improvements"] or "UX" in IDEATION_TYPE_LABELS["ui_ux_improvements"]
