"""Tests for memory_loader"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from prediction.memory_loader import MemoryLoader


@pytest.fixture
def memory_dir(tmp_path):
    """Create a temporary memory directory with test files."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    # Create gotchas.md
    (memory_dir / "gotchas.md").write_text(
        "# Gotchas from Previous Sessions\n"
        "\n"
        "- Never log sensitive data like passwords or tokens\n"
        "* Always validate user input before database operations\n"
        "- Remember to handle edge cases with None values\n"
        "* Use transactions for multi-step database operations\n"
        "\n"
        "## Additional Notes\n"
        "- Check for race conditions in concurrent operations\n"
        "* Always clean up temporary files\n"
    )

    # Create patterns.md
    (memory_dir / "patterns.md").write_text(
        "# Successful Patterns\n"
        "\n"
        "## Authentication\n"
        "- Use bcrypt for password hashing with proper salt rounds\n"
        "* Store tokens in HTTP-only cookies\n"
        "- Implement rate limiting on auth endpoints\n"
        "\n"
        "## Database\n"
        "- Use Alembic for all database migrations\n"
        "* Always add created_at and updated_at timestamps\n"
        "- Add indexes on foreign keys for better performance\n"
        "\n"
        "## API\n"
        "- Return consistent response format with data and error fields\n"
        "* Use proper HTTP status codes\n"
    )

    # Create attempt_history.json
    history_data = {
        "attempts": [
            {
                "subtask_id": "auth-001",
                "subtask_description": "Implement user authentication",
                "status": "failed",
                "error_message": "Token validation failed due to missing secret key",
                "files_modified": ["apps/backend/auth.py", "apps/backend/models/user.py"],
            },
            {
                "subtask_id": "db-002",
                "subtask_description": "Create database migration for users table",
                "status": "success",
                "error_message": "",
                "files_modified": ["alembic/versions/001_create_users.py"],
            },
            {
                "subtask_id": "api-003",
                "subtask_description": "Add user profile API endpoint",
                "status": "failed",
                "error_message": "N+1 query problem causing slow responses",
                "files_modified": ["apps/backend/api/users.py"],
            },
        ]
    }
    (memory_dir / "attempt_history.json").write_text(json.dumps(history_data))

    return memory_dir


@pytest.fixture
def empty_memory_dir(tmp_path):
    """Create a temporary memory directory without files."""
    memory_dir = tmp_path / "empty_memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir


def test_MemoryLoader_init(memory_dir):
    """Test MemoryLoader initialization."""
    loader = MemoryLoader(memory_dir)

    assert loader.memory_dir == memory_dir
    assert loader.gotchas_file == memory_dir / "gotchas.md"
    assert loader.patterns_file == memory_dir / "patterns.md"
    assert loader.history_file == memory_dir / "attempt_history.json"


def test_MemoryLoader_init_with_path_string(tmp_path):
    """Test MemoryLoader initialization with string path."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    loader = MemoryLoader(str(memory_dir))

    assert loader.memory_dir == memory_dir


def test_MemoryLoader_load_gotchas_success(memory_dir):
    """Test loading gotchas from a valid file."""
    loader = MemoryLoader(memory_dir)
    gotchas = loader.load_gotchas()

    assert len(gotchas) == 6
    assert "Never log sensitive data like passwords or tokens" in gotchas
    assert "Always validate user input before database operations" in gotchas
    assert "Remember to handle edge cases with None values" in gotchas
    assert "Use transactions for multi-step database operations" in gotchas
    assert "Check for race conditions in concurrent operations" in gotchas
    assert "Always clean up temporary files" in gotchas


def test_MemoryLoader_load_gotchas_empty_file(empty_memory_dir):
    """Test loading gotchas when file doesn't exist."""
    loader = MemoryLoader(empty_memory_dir)
    gotchas = loader.load_gotchas()

    assert gotchas == []


def test_MemoryLoader_load_gotches_mixed_formats(tmp_path):
    """Test loading gotchas with various markdown list formats."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    # Create gotchas.md with mixed formats
    (memory_dir / "gotchas.md").write_text(
        "- Dash style gotcha 1\n"
        "* Asterisk style gotcha 2\n"
        "- Gotcha with extra spaces\n"
        "  - Indented gotcha\n"
        "* Gotcha with **markdown** formatting\n"
        "-\n"  # Empty item
        "*\n"  # Empty item
        "- Valid gotcha after empty ones\n"
    )

    loader = MemoryLoader(memory_dir)
    gotchas = loader.load_gotchas()

    # Note: Empty lines starting with "-" or "*" are not included
    assert len(gotchas) == 6
    assert "Dash style gotcha 1" in gotchas
    assert "Asterisk style gotcha 2" in gotchas
    assert "Gotcha with extra spaces" in gotchas
    assert "Indented gotcha" in gotchas
    assert "Gotcha with **markdown** formatting" in gotchas
    assert "Valid gotcha after empty ones" in gotchas


def test_MemoryLoader_load_patterns_success(memory_dir):
    """Test loading patterns from a valid file."""
    loader = MemoryLoader(memory_dir)
    patterns = loader.load_patterns()

    # Check that patterns were loaded (actual count depends on fixture)
    assert len(patterns) >= 8

    # Check authentication patterns
    auth_patterns = [p for p in patterns if p.startswith("Authentication:")]
    assert len(auth_patterns) >= 3
    assert any("bcrypt" in p.lower() for p in auth_patterns)
    assert any("http-only" in p.lower() or "http only" in p.lower() for p in auth_patterns)
    assert any("rate limiting" in p.lower() for p in auth_patterns)

    # Check database patterns
    db_patterns = [p for p in patterns if p.startswith("Database:")]
    assert len(db_patterns) >= 3
    assert any("alembic" in p.lower() for p in db_patterns)
    assert any("timestamps" in p.lower() for p in db_patterns)
    assert any("indexes" in p.lower() or "foreign keys" in p.lower() for p in db_patterns)

    # Check API patterns
    api_patterns = [p for p in patterns if p.startswith("API:")]
    assert len(api_patterns) >= 2
    assert any("response format" in p.lower() or "status codes" in p.lower() for p in api_patterns)


def test_MemoryLoader_load_patterns_empty_file(empty_memory_dir):
    """Test loading patterns when file doesn't exist."""
    loader = MemoryLoader(empty_memory_dir)
    patterns = loader.load_patterns()

    assert patterns == []


def test_MemoryLoader_load_patterns_without_headings(tmp_path):
    """Test loading patterns without section headings."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    # Create patterns.md without headings
    (memory_dir / "patterns.md").write_text(
        "- Pattern without heading\n"
        "* Another pattern without heading\n"
    )

    loader = MemoryLoader(memory_dir)
    patterns = loader.load_patterns()

    assert patterns == []  # No patterns without headings


def test_MemoryLoader_load_patterns_empty_sections(tmp_path):
    """Test loading patterns with empty sections."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    # Create patterns.md with empty sections
    (memory_dir / "patterns.md").write_text(
        "## Empty Section\n"
        "\n"
        "## Section With Content\n"
        "- Actual pattern content\n"
        "* Another pattern\n"
    )

    loader = MemoryLoader(memory_dir)
    patterns = loader.load_patterns()

    assert len(patterns) == 2
    assert all(p.startswith("Section With Content:") for p in patterns)


def test_MemoryLoader_load_attempt_history_success(memory_dir):
    """Test loading attempt history from a valid file."""
    loader = MemoryLoader(memory_dir)
    history = loader.load_attempt_history()

    assert len(history) == 3

    # Check failed attempt
    failed_attempts = [a for a in history if a.get("status") == "failed"]
    assert len(failed_attempts) == 2
    assert failed_attempts[0]["subtask_id"] == "auth-001"
    assert "Token validation failed" in failed_attempts[0]["error_message"]

    # Check success attempt
    success_attempts = [a for a in history if a.get("status") == "success"]
    assert len(success_attempts) == 1
    assert success_attempts[0]["subtask_id"] == "db-002"


def test_MemoryLoader_load_attempt_history_empty_file(empty_memory_dir):
    """Test loading attempt history when file doesn't exist."""
    loader = MemoryLoader(empty_memory_dir)
    history = loader.load_attempt_history()

    assert history == []


def test_MemoryLoader_load_attempt_history_invalid_json(tmp_path):
    """Test loading attempt history with invalid JSON."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    # Create invalid JSON file
    (memory_dir / "attempt_history.json").write_text("{ invalid json }")

    loader = MemoryLoader(memory_dir)
    history = loader.load_attempt_history()

    assert history == []


def test_MemoryLoader_load_attempt_history_missing_attempts_key(tmp_path):
    """Test loading attempt history when 'attempts' key is missing."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    # Create JSON without 'attempts' key
    (memory_dir / "attempt_history.json").write_text('{"other_key": "value"}')

    loader = MemoryLoader(memory_dir)
    history = loader.load_attempt_history()

    assert history == []


def test_MemoryLoader_load_attempt_history_empty_attempts(tmp_path):
    """Test loading attempt history with empty attempts list."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    # Create JSON with empty attempts
    (memory_dir / "attempt_history.json").write_text('{"attempts": []}')

    loader = MemoryLoader(memory_dir)
    history = loader.load_attempt_history()

    assert history == []


def test_MemoryLoader_load_attempt_history_unicode_content(tmp_path):
    """Test loading attempt history with unicode characters."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    # Create JSON with unicode
    history_data = {
        "attempts": [
            {
                "subtask_id": "utf8-001",
                "subtask_description": "Test with émojis 🎉 and spëcial çharacters",
                "status": "success",
                "error_message": "",
                "files_modified": ["apps/backend/test.py"],
            }
        ]
    }
    (memory_dir / "attempt_history.json").write_text(
        json.dumps(history_data), encoding="utf-8"
    )

    loader = MemoryLoader(memory_dir)
    history = loader.load_attempt_history()

    assert len(history) == 1
    assert "émojis 🎉" in history[0]["subtask_description"]


def test_MemoryLoader_all_files_missing(empty_memory_dir):
    """Test MemoryLoader when all files are missing."""
    loader = MemoryLoader(empty_memory_dir)

    assert loader.load_gotchas() == []
    assert loader.load_patterns() == []
    assert loader.load_attempt_history() == []
