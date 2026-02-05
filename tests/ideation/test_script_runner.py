"""Tests for script_runner"""

from ideation.script_runner import ScriptRunner
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
import subprocess
import pytest


def test_ScriptRunner___init__():
    """Test ScriptRunner.__init__"""
    project_dir = Path("/tmp/test")
    runner = ScriptRunner(project_dir)
    assert runner.project_dir == project_dir


@patch("ideation.script_runner.subprocess.run")
@patch("ideation.script_runner.Path.exists")
def test_ScriptRunner_run_script_success(mock_exists, mock_run):
    """Test ScriptRunner.run_script with successful execution"""
    # Setup
    project_dir = Path("/tmp/test")
    runner = ScriptRunner(project_dir)
    mock_exists.return_value = True
    mock_run.return_value = Mock(
        returncode=0,
        stdout="Script output",
        stderr=""
    )

    # Act
    success, output = runner.run_script("test_script.py", ["arg1", "arg2"])

    # Assert
    assert success is True
    assert output == "Script output"


@patch("ideation.script_runner.subprocess.run")
@patch("ideation.script_runner.Path.exists")
def test_ScriptRunner_run_script_failure(mock_exists, mock_run):
    """Test ScriptRunner.run_script with script failure"""
    # Setup
    project_dir = Path("/tmp/test")
    runner = ScriptRunner(project_dir)
    mock_exists.return_value = True
    mock_run.return_value = Mock(
        returncode=1,
        stdout="",
        stderr="Script error"
    )

    # Act
    success, output = runner.run_script("test_script.py", [])

    # Assert
    assert success is False
    assert output == "Script error"


@patch("ideation.script_runner.Path.exists")
def test_ScriptRunner_run_script_not_found(mock_exists):
    """Test ScriptRunner.run_script when script doesn't exist"""
    # Setup
    project_dir = Path("/tmp/test")
    runner = ScriptRunner(project_dir)
    mock_exists.return_value = False

    # Act
    success, output = runner.run_script("nonexistent.py", [])

    # Assert
    assert success is False
    assert "Script not found" in output


@patch("ideation.script_runner.subprocess.run")
@patch("ideation.script_runner.Path.exists")
def test_ScriptRunner_run_script_timeout(mock_exists, mock_run):
    """Test ScriptRunner.run_script with timeout"""
    # Setup
    project_dir = Path("/tmp/test")
    runner = ScriptRunner(project_dir)
    mock_exists.return_value = True
    mock_run.side_effect = subprocess.TimeoutExpired("test.py", 30)

    # Act
    success, output = runner.run_script("test.py", [], timeout=30)

    # Assert
    assert success is False
    assert output == "Script timed out"
