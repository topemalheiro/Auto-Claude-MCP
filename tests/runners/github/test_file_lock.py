"""Tests for file_lock"""

import asyncio
import json
import os
import tempfile
from pathlib import Path

import pytest

from runners.github.file_lock import (
    FileLock,
    FileLockTimeout,
    atomic_write,
    locked_json_read,
    locked_json_update,
    locked_json_write,
    locked_read,
    locked_write,
)


def test_atomic_write(tmp_path):
    """Test atomic_write writes content correctly"""

    # Arrange
    filepath = tmp_path / "test.txt"
    test_content = "Hello, World!"

    # Act
    with atomic_write(filepath, mode="w", encoding="utf-8") as f:
        f.write(test_content)

    # Assert
    assert filepath.exists()
    assert filepath.read_text(encoding="utf-8") == test_content


def test_atomic_write_creates_directory(tmp_path):
    """Test atomic_write creates parent directories"""

    # Arrange
    filepath = tmp_path / "subdir" / "test.txt"
    test_content = "Nested content"

    # Act
    with atomic_write(filepath, mode="w", encoding="utf-8") as f:
        f.write(test_content)

    # Assert
    assert filepath.exists()
    assert filepath.read_text(encoding="utf-8") == test_content


def test_atomic_write_with_json(tmp_path):
    """Test atomic_write with JSON data"""

    # Arrange
    filepath = tmp_path / "data.json"
    test_data = {"key": "value", "number": 42}

    # Act
    with atomic_write(filepath, mode="w", encoding="utf-8") as f:
        json.dump(test_data, f)

    # Assert
    assert filepath.exists()
    with open(filepath, encoding="utf-8") as f:
        result = json.load(f)
    assert result == test_data


def test_atomic_write_rolls_back_on_error(tmp_path):
    """Test atomic_write doesn't create file if write fails"""

    # Arrange
    filepath = tmp_path / "test.txt"

    # Act & Assert
    try:
        with atomic_write(filepath, mode="w", encoding="utf-8") as f:
            f.write("Partial")
            raise ValueError("Simulated error")
    except ValueError:
        pass

    # File should not exist due to rollback
    assert not filepath.exists()


def test_FileLock___init__(tmp_path):
    """Test FileLock.__init__"""

    # Arrange & Act
    filepath = tmp_path / "test.txt"
    timeout = 10.0
    exclusive = True
    instance = FileLock(filepath, timeout, exclusive)

    # Assert
    assert instance.filepath == filepath
    assert instance.timeout == timeout
    assert instance.exclusive == exclusive
    assert instance._fd is None
    assert instance._lock_file is None


@pytest.mark.asyncio
async def test_FileLock___aenter__(tmp_path):
    """Test FileLock.__aenter__"""

    # Arrange
    filepath = tmp_path / "test.txt"
    instance = FileLock(filepath, timeout=5.0, exclusive=True)

    # Act
    result = await instance.__aenter__()

    # Assert
    assert result is instance
    assert instance._lock_file is not None
    assert instance._fd is not None
    assert instance._lock_file.exists()

    # Cleanup
    await instance.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_FileLock___aexit__(tmp_path):
    """Test FileLock.__aexit__"""

    # Arrange
    filepath = tmp_path / "test.txt"
    instance = FileLock(filepath, timeout=5.0, exclusive=True)
    await instance.__aenter__()
    lock_file = instance._lock_file

    # Act
    result = await instance.__aexit__(None, None, None)

    # Assert
    assert result is False
    # The fd should be closed
    assert instance._fd is None
    # The lock file cleanup is best-effort, just check it was created
    assert lock_file is not None


def test_FileLock___enter__(tmp_path):
    """Test FileLock.__enter__"""

    # Arrange
    filepath = tmp_path / "test.txt"
    instance = FileLock(filepath, timeout=5.0, exclusive=True)

    # Act
    result = instance.__enter__()

    # Assert
    assert result is instance
    assert instance._lock_file is not None
    assert instance._fd is not None

    # Cleanup
    instance.__exit__(None, None, None)


def test_FileLock___exit__(tmp_path):
    """Test FileLock.__exit__"""

    # Arrange
    filepath = tmp_path / "test.txt"
    instance = FileLock(filepath, timeout=5.0, exclusive=True)
    instance.__enter__()
    lock_file = instance._lock_file

    # Act
    result = instance.__exit__(None, None, None)

    # Assert
    assert result is False
    # The lock file cleanup is best-effort, so we just check that the fd is closed
    assert instance._fd is None


@pytest.mark.asyncio
async def test_locked_json_write(tmp_path):
    """Test locked_json_write"""

    # Arrange
    filepath = tmp_path / "data.json"
    data = {"key": "value", "number": 42}

    # Act
    await locked_json_write(filepath, data, timeout=5.0, indent=2)

    # Assert
    assert filepath.exists()
    with open(filepath, encoding="utf-8") as f:
        result = json.load(f)
    assert result == data


@pytest.mark.asyncio
async def test_locked_json_read(tmp_path):
    """Test locked_json_read"""

    # Arrange
    filepath = tmp_path / "data.json"
    data = {"key": "value", "number": 42}
    await locked_json_write(filepath, data)

    # Act
    result = await locked_json_read(filepath, timeout=5.0)

    # Assert
    assert result == data


@pytest.mark.asyncio
async def test_locked_json_read_file_not_found(tmp_path):
    """Test locked_json_read raises FileNotFoundError"""

    # Arrange
    filepath = tmp_path / "nonexistent.json"

    # Act & Assert
    with pytest.raises(FileNotFoundError):
        await locked_json_read(filepath, timeout=5.0)


@pytest.mark.asyncio
async def test_locked_json_update(tmp_path):
    """Test locked_json_update"""

    # Arrange
    filepath = tmp_path / "data.json"
    initial_data = {"count": 0}

    await locked_json_write(filepath, initial_data)

    def updater(data):
        if data is None:
            data = {"count": 0}
        data["count"] += 1
        return data

    # Act
    result = await locked_json_update(filepath, updater, timeout=5.0)

    # Assert
    assert result == {"count": 1}
    with open(filepath, encoding="utf-8") as f:
        saved_data = json.load(f)
    assert saved_data == {"count": 1}


@pytest.mark.asyncio
async def test_locked_json_update_creates_file(tmp_path):
    """Test locked_json_update creates file if it doesn't exist"""

    # Arrange
    filepath = tmp_path / "new.json"

    def updater(data):
        return {"new": "data"}

    # Act
    result = await locked_json_update(filepath, updater, timeout=5.0)

    # Assert
    assert result == {"new": "data"}
    assert filepath.exists()


@pytest.mark.asyncio
async def test_locked_write(tmp_path):
    """Test locked_write context manager"""

    # Arrange
    filepath = tmp_path / "test.txt"
    test_content = "Locked content"

    # Act
    async with locked_write(filepath, timeout=5.0, mode="w", encoding="utf-8") as f:
        f.write(test_content)

    # Assert
    assert filepath.exists()
    assert filepath.read_text(encoding="utf-8") == test_content


@pytest.mark.asyncio
async def test_locked_read(tmp_path):
    """Test locked_read context manager"""

    # Arrange
    filepath = tmp_path / "test.txt"
    test_content = "Read content"
    filepath.write_text(test_content, encoding="utf-8")

    # Act
    async with locked_read(filepath, timeout=5.0) as f:
        result = f.read()

    # Assert
    assert result == test_content


@pytest.mark.asyncio
async def test_locked_read_file_not_found(tmp_path):
    """Test locked_read raises FileNotFoundError"""

    # Arrange
    filepath = tmp_path / "nonexistent.txt"

    # Act & Assert
    with pytest.raises(FileNotFoundError):
        async with locked_read(filepath, timeout=5.0):
            pass


def test_FileLock_get_lock_file(tmp_path):
    """Test FileLock._get_lock_file"""

    # Arrange
    filepath = tmp_path / "test.txt"
    instance = FileLock(filepath, timeout=5.0)

    # Act
    lock_file = instance._get_lock_file()

    # Assert
    assert lock_file.name == "test.txt.lock"
    assert lock_file.parent == filepath.parent
