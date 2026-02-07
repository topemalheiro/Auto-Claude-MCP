"""Tests for spec_commands"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli.spec_commands import list_specs, print_specs_list


def test_list_specs_with_no_specs(tmp_path):
    """Test list_specs with no specs directory."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Act
    result = list_specs(project_dir)

    # Assert
    assert result == []


def test_list_specs_with_valid_specs(tmp_path):
    """Test list_specs with valid spec directories."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    specs_dir = project_dir / ".auto-claude" / "specs"
    specs_dir.mkdir(parents=True)
    spec1 = specs_dir / "001-first-spec"
    spec1.mkdir()
    (spec1 / "spec.md").write_text("# First Spec")
    spec2 = specs_dir / "002-second-spec"
    spec2.mkdir()
    (spec2 / "spec.md").write_text("# Second Spec")

    # Act
    result = list_specs(project_dir)

    # Assert
    assert len(result) == 2
    assert result[0]["number"] == "001"
    assert result[0]["name"] == "first-spec"
    assert result[1]["number"] == "002"
    assert result[1]["name"] == "second-spec"


def test_list_specs_with_implementation_plan(tmp_path):
    """Test list_specs with implementation plan."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    specs_dir = project_dir / ".auto-claude" / "specs"
    specs_dir.mkdir(parents=True)
    spec = specs_dir / "001-test"
    spec.mkdir()
    (spec / "spec.md").write_text("# Test Spec")
    (spec / "implementation_plan.json").write_text('{"subtasks": [{"status": "complete"}, {"status": "complete"}, {"status": "pending"}]}')

    with patch("cli.spec_commands.count_subtasks", return_value=(2, 3)):
        # Act
        result = list_specs(project_dir)

    # Assert
    assert len(result) == 1
    assert result[0]["status"] == "in_progress"
    assert result[0]["progress"] == "2/3"


def test_list_specs_ignores_invalid_names(tmp_path):
    """Test list_specs ignores invalid folder names."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    specs_dir = project_dir / ".auto-claude" / "specs"
    specs_dir.mkdir(parents=True)
    (specs_dir / "invalid-name").mkdir()
    (specs_dir / "invalid-name" / "spec.md").write_text("# Invalid")
    (specs_dir / "001-valid").mkdir()
    (specs_dir / "001-valid" / "spec.md").write_text("# Valid")

    # Act
    result = list_specs(project_dir)

    # Assert
    assert len(result) == 1
    assert result[0]["folder"] == "001-valid"


def test_list_specs_with_empty_inputs():
    """Test list_specs with non-existent directory."""
    # Arrange
    project_dir = Path("/tmp/nonexistent")

    # Act
    result = list_specs(project_dir)

    # Assert
    assert result == []


def test_print_specs_list_no_specs(tmp_path, capsys):
    """Test print_specs_list with no specs."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Act
    print_specs_list(project_dir, auto_create=False)

    # Assert
    captured = capsys.readouterr()
    assert "No specs found" in captured.out


def test_print_specs_list_with_specs(tmp_path, capsys):
    """Test print_specs_list with existing specs."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    specs_dir = project_dir / ".auto-claude" / "specs"
    specs_dir.mkdir(parents=True)
    spec = specs_dir / "001-test"
    spec.mkdir()
    (spec / "spec.md").write_text("# Test Spec")

    # Act
    print_specs_list(project_dir, auto_create=False)

    # Assert
    captured = capsys.readouterr()
    assert "AVAILABLE SPECS" in captured.out
    assert "001-test" in captured.out


@pytest.mark.slow
def test_print_specs_list_auto_create(tmp_path, capsys):
    """Test print_specs_list with auto_create disabled when input provided."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    with patch("builtins.input", return_value="test task"):
        # Act
        print_specs_list(project_dir, auto_create=True)

    # Assert
    captured = capsys.readouterr()
    assert "QUICK START" in captured.out


def test_print_specs_list_auto_create_cancelled(tmp_path, capsys):
    """Test print_specs_list with user cancellation."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    with patch("builtins.input", side_effect=KeyboardInterrupt()):
        # Act
        print_specs_list(project_dir, auto_create=True)

    # Assert
    captured = capsys.readouterr()
    assert "Cancelled" in captured.out or "QUICK START" in captured.out


def test_list_specs_with_empty_inputs_empty_dir(tmp_path):
    """Test list_specs with empty specs directory."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    specs_dir = project_dir / ".auto-claude" / "specs"
    specs_dir.mkdir(parents=True)

    # Act
    result = list_specs(project_dir)

    # Assert
    assert result == []


def test_print_specs_list_with_empty_inputs_no_specs(tmp_path, capsys):
    """Test print_specs_list with no specs and auto_create=False."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Act
    print_specs_list(project_dir, auto_create=False)

    # Assert
    captured = capsys.readouterr()
    assert "No specs found" in captured.out


def test_print_specs_list_no_spec_file(tmp_path):
    """Test print_specs_list ignores directories without spec.md."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    specs_dir = project_dir / ".auto-claude" / "specs"
    specs_dir.mkdir(parents=True)
    spec = specs_dir / "001-test"
    spec.mkdir()
    # No spec.md created

    # Act
    result = list_specs(project_dir)

    # Assert
    assert len(result) == 0
