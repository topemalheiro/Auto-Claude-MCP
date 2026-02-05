"""Tests for recovery"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli.recovery import (
    backup_corrupted_file,
    check_json_file,
    detect_corrupted_files,
    main,
)


def test_check_json_file_valid(tmp_path):
    """Test check_json_file with valid JSON."""
    # Arrange
    filepath = tmp_path / "valid.json"
    filepath.write_text('{"key": "value"}')

    # Act
    result, error = check_json_file(filepath)

    # Assert
    assert result is True
    assert error is None


def test_check_json_file_invalid(tmp_path):
    """Test check_json_file with invalid JSON."""
    # Arrange
    filepath = tmp_path / "invalid.json"
    filepath.write_text('{"key": invalid}')

    # Act
    result, error = check_json_file(filepath)

    # Assert
    assert result is False
    assert error is not None
    assert "Expecting" in error or "JSONDecodeError" in error


def test_check_json_file_nonexistent():
    """Test check_json_file with non-existent file."""
    # Arrange
    filepath = Path("/tmp/nonexistent_file.json")

    # Act
    result, error = check_json_file(filepath)

    # Assert
    assert result is False
    assert error is not None


def test_check_json_file_with_empty_inputs():
    """Test check_json_file with invalid path."""
    # Arrange
    filepath = Path("")

    # Act
    result, error = check_json_file(filepath)

    # Assert
    assert result is False
    assert error is not None


def test_detect_corrupted_files_with_valid_files(tmp_path):
    """Test detect_corrupted_files with only valid JSON files."""
    # Arrange
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    (specs_dir / "valid1.json").write_text('{"key": "value1"}')
    (specs_dir / "valid2.json").write_text('{"key": "value2"}')

    # Act
    result = detect_corrupted_files(specs_dir)

    # Assert
    assert len(result) == 0


def test_detect_corrupted_files_with_invalid_files(tmp_path):
    """Test detect_corrupted_files with corrupted JSON files."""
    # Arrange
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    (specs_dir / "valid.json").write_text('{"key": "value"}')
    (specs_dir / "invalid.json").write_text('{invalid json}')
    nested_dir = specs_dir / "nested"
    nested_dir.mkdir()
    (nested_dir / "corrupted.json").write_text('{bad}')

    # Act
    result = detect_corrupted_files(specs_dir)

    # Assert
    assert len(result) == 2
    assert any("invalid.json" in str(f) for f, _ in result)
    assert any("corrupted.json" in str(f) for f, _ in result)


def test_detect_corrupted_files_nonexistent_dir():
    """Test detect_corrupted_files with non-existent directory."""
    # Arrange
    specs_dir = Path("/tmp/nonexistent_specs")

    # Act
    result = detect_corrupted_files(specs_dir)

    # Assert
    assert result == []


def test_detect_corrupted_files_with_empty_inputs():
    """Test detect_corrupted_files with invalid path."""
    # Arrange
    specs_dir = Path("")

    # Act
    result = detect_corrupted_files(specs_dir)

    # Assert
    assert isinstance(result, list)


def test_backup_corrupted_file_success(tmp_path):
    """Test backup_corrupted_file successfully backs up file."""
    # Arrange
    filepath = tmp_path / "corrupted.json"
    filepath.write_text('{invalid}')

    # Act
    result = backup_corrupted_file(filepath)

    # Assert
    assert result is True
    assert not filepath.exists()
    backup_file = tmp_path / "corrupted.json.corrupted"
    assert backup_file.exists()


def test_backup_corrupted_file_with_existing_backup(tmp_path):
    """Test backup_corrupted_file handles existing backup."""
    # Arrange
    filepath = tmp_path / "corrupted.json"
    filepath.write_text('{invalid}')
    backup_path = tmp_path / "corrupted.json.corrupted"
    backup_path.write_text("previous backup")

    # Act
    result = backup_corrupted_file(filepath)

    # Assert
    assert result is True
    # Original file should be moved
    assert not filepath.exists()
    # New backup should have UUID suffix
    new_backups = list(tmp_path.glob("*.corrupted.*"))
    assert len(new_backups) >= 1


def test_backup_corrupted_file_nonexistent(tmp_path, capsys):
    """Test backup_corrupted_file with non-existent file."""
    # Arrange
    filepath = tmp_path / "nonexistent.json"

    # Act
    result = backup_corrupted_file(filepath)

    # Assert
    assert result is False
    captured = capsys.readouterr()
    assert "ERROR" in captured.out or "Failed" in captured.out


def test_backup_corrupted_file_with_empty_inputs():
    """Test backup_corrupted_file with invalid path."""
    # Arrange
    filepath = Path("")

    # Act
    result = backup_corrupted_file(filepath)

    # Assert
    assert result is False


def test_main_detect_mode_no_corruption(tmp_path, capsys):
    """Test main in detect mode with no corrupted files."""
    # Arrange
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    (specs_dir / "valid.json").write_text('{"key": "value"}')

    with patch("sys.argv", ["recovery.py", "--project-dir", str(tmp_path), "--specs-dir", str(specs_dir), "--detect"]):
        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "No corrupted" in captured.out or "OK" in captured.out


def test_main_detect_mode_with_corruption(tmp_path, capsys):
    """Test main in detect mode with corrupted files."""
    # Arrange
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    (specs_dir / "valid.json").write_text('{"key": "value"}')
    (specs_dir / "invalid.json").write_text('{bad}')

    with patch("sys.argv", ["recovery.py", "--project-dir", str(tmp_path), "--specs-dir", str(specs_dir), "--detect"]):
        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "corrupted" in captured.out.lower() or "FOUND" in captured.out


def test_main_with_empty_inputs(tmp_path, capsys):
    """Test main with default arguments."""
    # Arrange
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()

    with patch("sys.argv", ["recovery.py", "--project-dir", str(tmp_path), "--specs-dir", str(specs_dir)]), \
         patch("pathlib.Path.cwd", return_value=tmp_path):
        # Act & Assert - should default to detect mode
        with pytest.raises(SystemExit) as exc_info:
            main()
        # Exit 0 if no corrupted files, 1 if corrupted files found
        assert exc_info.value.code in (0, 1)


def test_main_all_requires_delete(tmp_path, capsys):
    """Test main validates --all requires --delete."""
    # Arrange
    with patch("sys.argv", ["recovery.py", "--project-dir", str(tmp_path), "--all"]):
        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            main()
        # argparse.error uses SystemExit(2)
        assert exc_info.value.code == 2


def test_main_delete_all_corrupted(tmp_path, capsys):
    """Test main deletes all corrupted files."""
    # Arrange
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    (specs_dir / "valid.json").write_text('{"key": "value"}')
    (specs_dir / "invalid.json").write_text('{bad}')

    with patch("sys.argv", ["recovery.py", "--project-dir", str(tmp_path), "--specs-dir", str(specs_dir), "--delete", "--all"]):
        # Act & Assert
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

    # Verify backup was created
    backup_files = list(specs_dir.glob("*.corrupted*"))
    assert len(backup_files) >= 1


def test_main_delete_specific_spec(tmp_path, capsys):
    """Test main deletes corrupted files from specific spec."""
    # Arrange
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    spec_dir = specs_dir / "001-test"
    spec_dir.mkdir()
    (spec_dir / "valid.json").write_text('{"key": "value"}')
    (spec_dir / "invalid.json").write_text('{bad}')

    with patch("sys.argv", ["recovery.py", "--project-dir", str(tmp_path), "--specs-dir", str(specs_dir), "--delete", "--spec-id", "001-test"]):
        # Act & Assert
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

    # Verify backup was created
    backup_files = list(spec_dir.glob("*.corrupted*"))
    assert len(backup_files) >= 1
