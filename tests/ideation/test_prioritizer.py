"""Tests for prioritizer"""

from ideation.prioritizer import IdeaPrioritizer
from pathlib import Path
from unittest.mock import patch, MagicMock
import json
import pytest


def test_IdeaPrioritizer___init__():
    """Test IdeaPrioritizer.__init__"""
    output_dir = Path("/tmp/output")
    prioritizer = IdeaPrioritizer(output_dir)
    assert prioritizer.output_dir == output_dir


@patch("ideation.prioritizer.Path.exists")
def test_IdeaPrioritizer_validate_ideation_output_not_found(mock_exists):
    """Test IdeaPrioritizer.validate_ideation_output when file doesn't exist"""
    mock_exists.return_value = False
    output_dir = Path("/tmp/output")
    prioritizer = IdeaPrioritizer(output_dir)

    result = prioritizer.validate_ideation_output(
        output_dir / "code_improvements_ideas.json",
        "code_improvements"
    )

    assert result["success"] is False
    assert "does not exist" in result["error"]
    assert result["count"] == 0


@patch("ideation.prioritizer.Path.exists")
@patch("ideation.prioritizer.Path.read_text")
def test_IdeaPrioritizer_validate_ideation_output_valid(mock_read_text, mock_exists):
    """Test IdeaPrioritizer.validate_ideation_output with valid data"""
    mock_exists.return_value = True
    valid_data = {"code_improvements": [{"title": "Fix bug"}]}
    mock_read_text.return_value = json.dumps(valid_data)

    output_dir = Path("/tmp/output")
    prioritizer = IdeaPrioritizer(output_dir)

    result = prioritizer.validate_ideation_output(
        output_dir / "code_improvements_ideas.json",
        "code_improvements"
    )

    assert result["success"] is True
    assert result["error"] is None
    assert result["count"] == 1


@patch("ideation.prioritizer.Path.exists")
@patch("ideation.prioritizer.Path.read_text")
def test_IdeaPrioritizer_validate_ideation_output_wrong_key(mock_read_text, mock_exists):
    """Test IdeaPrioritizer.validate_ideation_output with wrong JSON key"""
    mock_exists.return_value = True
    wrong_data = {"ideas": [{"title": "Fix bug"}]}  # Should be code_improvements
    mock_read_text.return_value = json.dumps(wrong_data)

    output_dir = Path("/tmp/output")
    prioritizer = IdeaPrioritizer(output_dir)

    result = prioritizer.validate_ideation_output(
        output_dir / "code_improvements_ideas.json",
        "code_improvements"
    )

    assert result["success"] is False
    assert "Wrong JSON key" in result["error"]


@patch("ideation.prioritizer.Path.exists")
@patch("ideation.prioritizer.Path.read_text")
def test_IdeaPrioritizer_validate_ideation_output_invalid_json(mock_read_text, mock_exists):
    """Test IdeaPrioritizer.validate_ideation_output with invalid JSON"""
    mock_exists.return_value = True
    mock_read_text.return_value = "invalid json"

    output_dir = Path("/tmp/output")
    prioritizer = IdeaPrioritizer(output_dir)

    result = prioritizer.validate_ideation_output(
        output_dir / "code_improvements_ideas.json",
        "code_improvements"
    )

    assert result["success"] is False
    assert "Invalid JSON" in result["error"]


@patch("ideation.prioritizer.Path.exists")
@patch("ideation.prioritizer.Path.read_text")
def test_IdeaPrioritizer_validate_ideation_output_empty_ideas(mock_read_text, mock_exists):
    """Test IdeaPrioritizer.validate_ideation_output with empty ideas list"""
    mock_exists.return_value = True
    empty_data = {"code_improvements": []}
    mock_read_text.return_value = json.dumps(empty_data)

    output_dir = Path("/tmp/output")
    prioritizer = IdeaPrioritizer(output_dir)

    result = prioritizer.validate_ideation_output(
        output_dir / "code_improvements_ideas.json",
        "code_improvements"
    )

    assert result["success"] is False
    assert "ideas found" in result["error"]
