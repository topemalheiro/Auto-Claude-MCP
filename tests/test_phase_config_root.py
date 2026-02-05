"""Tests for phase_config"""

from phase_config import (
    get_phase_config,
    get_phase_model,
    get_phase_thinking,
    get_phase_thinking_budget,
    get_spec_phase_thinking_budget,
    get_thinking_budget,
    load_task_metadata,
    resolve_model_id,
)
from pathlib import Path
from unittest.mock import MagicMock, patch
import json
import pytest


@pytest.fixture
def temp_spec_dir(tmp_path):
    """Create a temporary spec directory for testing."""
    return tmp_path / "spec"


@pytest.fixture
def spec_dir_with_metadata(temp_spec_dir):
    """Create a spec directory with task_metadata.json."""
    metadata = {
        "isAutoProfile": True,
        "phaseModels": {
            "spec": "sonnet",
            "planning": "opus",
            "coding": "sonnet",
            "qa": "opus"
        },
        "phaseThinking": {
            "spec": "medium",
            "planning": "high",
            "coding": "medium",
            "qa": "high"
        },
        "model": "haiku",
        "thinkingLevel": "medium"
    }
    temp_spec_dir.mkdir(parents=True, exist_ok=True)
    with open(temp_spec_dir / "task_metadata.json", "w") as f:
        json.dump(metadata, f)
    return temp_spec_dir


def test_resolve_model_id():
    """Test resolve_model_id with shorthand and full model IDs."""

    # Clear any environment variables that might affect the test
    import os
    env_backup = {}
    for key in ["ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL"]:
        if key in os.environ:
            env_backup[key] = os.environ[key]
            del os.environ[key]

    try:
        # Test shorthand mappings
        assert resolve_model_id("opus") == "claude-opus-4-5-20251101"
        assert resolve_model_id("sonnet") == "claude-sonnet-4-5-20250929"
        assert resolve_model_id("haiku") == "claude-haiku-4-5-20251001"

        # Test full model ID passthrough
        full_id = "custom-model-123"
        assert resolve_model_id(full_id) == full_id
    finally:
        # Restore environment variables
        os.environ.update(env_backup)


def test_get_thinking_budget():
    """Test get_thinking_budget with various thinking levels."""

    assert get_thinking_budget("none") is None
    assert get_thinking_budget("low") == 1024
    assert get_thinking_budget("medium") == 4096
    assert get_thinking_budget("high") == 16384
    assert get_thinking_budget("ultrathink") == 63999

    # Test invalid level defaults to medium
    assert get_thinking_budget("invalid") == 4096


def test_load_task_metadata(temp_spec_dir):
    """Test load_task_metadata with non-existent file."""
    result = load_task_metadata(temp_spec_dir)
    assert result is None


def test_load_task_metadata_with_file(spec_dir_with_metadata):
    """Test load_task_metadata with existing file."""
    result = load_task_metadata(spec_dir_with_metadata)
    assert result is not None
    assert result.get("isAutoProfile") is True
    assert result.get("model") == "haiku"


def test_get_phase_model_with_cli_override():
    """Test get_phase_model with CLI override."""
    import os
    # Clear environment variables
    env_backup = {}
    for key in ["ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL"]:
        if key in os.environ:
            env_backup[key] = os.environ[key]
            del os.environ[key]

    try:
        spec_dir = Path("/tmp/test")
        result = get_phase_model(spec_dir, "coding", cli_model="opus")
        assert result == "claude-opus-4-5-20251101"
    finally:
        os.environ.update(env_backup)


def test_get_phase_model_default():
    """Test get_phase_model with defaults."""
    import os
    # Clear environment variables
    env_backup = {}
    for key in ["ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL"]:
        if key in os.environ:
            env_backup[key] = os.environ[key]
            del os.environ[key]

    try:
        spec_dir = Path("/tmp/test")
        result = get_phase_model(spec_dir, "planning")
        assert result == "claude-sonnet-4-5-20250929"  # Default for planning
    finally:
        os.environ.update(env_backup)


def test_get_phase_model_with_metadata(spec_dir_with_metadata):
    """Test get_phase_model with metadata."""
    import os
    # Clear environment variables
    env_backup = {}
    for key in ["ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL"]:
        if key in os.environ:
            env_backup[key] = os.environ[key]
            del os.environ[key]

    try:
        result = get_phase_model(spec_dir_with_metadata, "planning")
        assert result == "claude-opus-4-5-20251101"
    finally:
        os.environ.update(env_backup)


def test_get_phase_thinking_with_cli_override():
    """Test get_phase_thinking with CLI override."""
    spec_dir = Path("/tmp/test")
    result = get_phase_thinking(spec_dir, "coding", cli_thinking="ultrathink")
    assert result == "ultrathink"


def test_get_phase_thinking_default():
    """Test get_phase_thinking with defaults."""
    spec_dir = Path("/tmp/test")
    result = get_phase_thinking(spec_dir, "qa")
    assert result == "high"


def test_get_phase_thinking_with_metadata(spec_dir_with_metadata):
    """Test get_phase_thinking with metadata."""
    result = get_phase_thinking(spec_dir_with_metadata, "qa")
    assert result == "high"


def test_get_phase_thinking_budget():
    """Test get_phase_thinking_budget combines thinking level and budget."""
    spec_dir = Path("/tmp/test")
    result = get_phase_thinking_budget(spec_dir, "qa", cli_thinking="ultrathink")
    assert result == 63999


def test_get_phase_config():
    """Test get_phase_config returns tuple of model, thinking level, and budget."""
    import os
    # Clear environment variables
    env_backup = {}
    for key in ["ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL"]:
        if key in os.environ:
            env_backup[key] = os.environ[key]
            del os.environ[key]

    try:
        spec_dir = Path("/tmp/test")
        model, thinking_level, budget = get_phase_config(
            spec_dir, "coding", cli_model="sonnet", cli_thinking="high"
        )
        assert model == "claude-sonnet-4-5-20250929"
        assert thinking_level == "high"
        assert budget == 16384
    finally:
        os.environ.update(env_backup)


def test_get_spec_phase_thinking_budget():
    """Test get_spec_phase_thinking_budget for various phases."""

    # Heavy phases use ultrathink
    assert get_spec_phase_thinking_budget("discovery") == 63999
    assert get_spec_phase_thinking_budget("spec_writing") == 63999
    assert get_spec_phase_thinking_budget("self_critique") == 63999

    # Light phases use medium
    assert get_spec_phase_thinking_budget("requirements") == 4096
    assert get_spec_phase_thinking_budget("research") == 4096
    assert get_spec_phase_thinking_budget("planning") == 4096

    # Unknown phases default to medium
    assert get_spec_phase_thinking_budget("unknown") == 4096
