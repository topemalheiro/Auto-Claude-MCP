"""Tests for batch_commands"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli.batch_commands import (
    handle_batch_cleanup_command,
    handle_batch_create_command,
    handle_batch_status_command,
)


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    return tmp_path / "project"


@pytest.fixture
def temp_batch_file(tmp_path):
    """Create a temporary batch file with valid content."""
    batch_file = tmp_path / "batch.json"
    batch_data = {
        "tasks": [
            {
                "title": "Test Task 1",
                "description": "First test task",
                "workflow_type": "feature",
                "services": ["frontend"],
                "priority": 5,
                "complexity": "standard",
                "estimated_hours": 4.0,
                "estimated_days": 0.5,
            },
            {
                "title": "Test Task 2",
                "description": "Second test task",
                "workflow_type": "bugfix",
                "services": ["backend"],
                "priority": 3,
                "complexity": "simple",
                "estimated_hours": 2.0,
                "estimated_days": 0.25,
            },
        ]
    }
    batch_file.write_text(json.dumps(batch_data))
    return batch_file


@pytest.fixture
def empty_batch_file(tmp_path):
    """Create a batch file with empty tasks list."""
    batch_file = tmp_path / "empty_batch.json"
    batch_file.write_text(json.dumps({"tasks": []}))
    return batch_file


@pytest.fixture
def invalid_json_file(tmp_path):
    """Create a batch file with invalid JSON."""
    batch_file = tmp_path / "invalid.json"
    batch_file.write_text("{invalid json content")
    return batch_file


def test_handle_batch_create_command(temp_project_dir, temp_batch_file):
    """Test handle_batch_create_command with valid batch file."""
    # Arrange
    temp_project_dir.mkdir()

    # Act
    result = handle_batch_create_command(str(temp_batch_file), str(temp_project_dir))

    # Assert
    assert result is True
    specs_dir = temp_project_dir / ".auto-claude" / "specs"
    assert specs_dir.exists()
    # Check that spec directories were created
    spec_dirs = [d for d in specs_dir.iterdir() if d.is_dir()]
    assert len(spec_dirs) == 2
    # Check first spec
    first_spec = spec_dirs[0]
    assert (first_spec / "requirements.json").exists()


def test_handle_batch_create_command_with_nonexistent_file(temp_project_dir):
    """Test handle_batch_create_command with non-existent file."""
    # Arrange
    temp_project_dir.mkdir()
    nonexistent_file = "/tmp/nonexistent_batch_file.json"

    # Act
    result = handle_batch_create_command(nonexistent_file, str(temp_project_dir))

    # Assert
    assert result is False


def test_handle_batch_create_command_with_invalid_json(temp_project_dir, invalid_json_file):
    """Test handle_batch_create_command with invalid JSON."""
    # Arrange
    temp_project_dir.mkdir()

    # Act
    result = handle_batch_create_command(str(invalid_json_file), str(temp_project_dir))

    # Assert
    assert result is False


def test_handle_batch_create_command_with_empty_tasks(temp_project_dir, empty_batch_file):
    """Test handle_batch_create_command with empty tasks list."""
    # Arrange
    temp_project_dir.mkdir()

    # Act
    result = handle_batch_create_command(str(empty_batch_file), str(temp_project_dir))

    # Assert
    assert result is False


def test_handle_batch_create_command_with_directory_as_batch_file(temp_project_dir):
    """Test handle_batch_create_command when batch_file is a directory."""
    # Arrange
    temp_project_dir.mkdir()
    # Create a different directory to use as the "batch file"
    other_dir = temp_project_dir / "other"
    other_dir.mkdir()

    # Act & Assert - passing a directory should return False
    result = handle_batch_create_command(str(other_dir), str(temp_project_dir))
    assert result is False


def test_handle_batch_status_command(temp_project_dir):
    """Test handle_batch_status_command with specs."""
    # Arrange
    temp_project_dir.mkdir()
    specs_dir = temp_project_dir / ".auto-claude" / "specs"
    specs_dir.mkdir(parents=True)
    # Create a spec directory
    spec_dir = specs_dir / "001-test-spec"
    spec_dir.mkdir()
    req_file = spec_dir / "requirements.json"
    req_file.write_text(json.dumps({"task_description": "Test task"}))

    # Act
    result = handle_batch_status_command(str(temp_project_dir))

    # Assert
    assert result is True


def test_handle_batch_status_command_with_no_specs_dir(temp_project_dir):
    """Test handle_batch_status_command when no specs directory exists."""
    # Arrange
    temp_project_dir.mkdir()

    # Act
    result = handle_batch_status_command(str(temp_project_dir))

    # Assert
    assert result is True


def test_handle_batch_status_command_with_empty_specs(temp_project_dir):
    """Test handle_batch_status_command with empty specs directory."""
    # Arrange
    temp_project_dir.mkdir()
    specs_dir = temp_project_dir / ".auto-claude" / "specs"
    specs_dir.mkdir(parents=True)

    # Act
    result = handle_batch_status_command(str(temp_project_dir))

    # Assert
    assert result is True


def test_handle_batch_cleanup_command_dry_run(temp_project_dir):
    """Test handle_batch_cleanup_command with dry_run=True."""
    # Arrange
    temp_project_dir.mkdir()
    specs_dir = temp_project_dir / ".auto-claude" / "specs"
    specs_dir.mkdir(parents=True)
    # Create a completed spec (has qa_report.md)
    spec_dir = specs_dir / "001-completed-spec"
    spec_dir.mkdir()
    (spec_dir / "qa_report.md").write_text("# QA Report")

    # Act
    result = handle_batch_cleanup_command(str(temp_project_dir), dry_run=True)

    # Assert
    assert result is True
    # Spec should still exist (dry run)
    assert spec_dir.exists()


def test_handle_batch_cleanup_command_with_no_specs(temp_project_dir):
    """Test handle_batch_cleanup_command when no specs directory."""
    # Arrange
    temp_project_dir.mkdir()

    # Act
    result = handle_batch_cleanup_command(str(temp_project_dir), dry_run=True)

    # Assert
    assert result is True


def test_handle_batch_cleanup_command_with_no_completed_specs(temp_project_dir):
    """Test handle_batch_cleanup_command with no completed specs."""
    # Arrange
    temp_project_dir.mkdir()
    specs_dir = temp_project_dir / ".auto-claude" / "specs"
    specs_dir.mkdir(parents=True)
    # Create an incomplete spec (no qa_report.md)
    spec_dir = specs_dir / "001-incomplete-spec"
    spec_dir.mkdir()
    (spec_dir / "requirements.json").write_text("{}")

    # Act
    result = handle_batch_cleanup_command(str(temp_project_dir), dry_run=True)

    # Assert
    assert result is True
