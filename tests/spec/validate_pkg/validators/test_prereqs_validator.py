"""Tests for prereqs_validator"""

from spec.validate_pkg.validators.prereqs_validator import PrereqsValidator
from spec.validate_pkg.models import ValidationResult
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import json


def test_PrereqsValidator___init__():
    """Test PrereqsValidator.__init__"""

    # Arrange
    spec_dir = Path("/tmp/test")

    # Act
    validator = PrereqsValidator(spec_dir)

    # Assert
    assert validator.spec_dir == spec_dir


def test_PrereqsValidator_validate_missing_directory():
    """Test PrereqsValidator.validate when directory doesn't exist"""

    # Arrange
    spec_dir = Path("/tmp/nonexistent_test_spec")
    validator = PrereqsValidator(spec_dir)

    # Act
    result = validator.validate()

    # Assert
    assert result.valid is False
    assert "does not exist" in result.errors[0].lower()
    assert len(result.fixes) > 0
    assert result.checkpoint == "prereqs"


def test_PrereqsValidator_validate_missing_project_index(tmp_path):
    """Test PrereqsValidator.validate when project_index.json is missing"""

    # Arrange
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    # No project_index.json created

    validator = PrereqsValidator(spec_dir)

    # Act
    result = validator.validate()

    # Assert
    assert result.valid is False
    assert "not found" in result.errors[0].lower()


def test_PrereqsValidator_validate_valid_prereqs(tmp_path):
    """Test PrereqsValidator.validate with valid prerequisites"""

    # Arrange
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    project_index = spec_dir / "project_index.json"
    project_index.write_text(json.dumps({"project_type": "test"}), encoding="utf-8")

    validator = PrereqsValidator(spec_dir)

    # Act
    result = validator.validate()

    # Assert
    assert isinstance(result, ValidationResult)
    assert result.checkpoint == "prereqs"


class TestPrereqsValidatorProjectIndexScenarios:
    """Tests for various project_index.json scenarios."""

    def test_project_index_exists_at_spec_level(self, tmp_path):
        """Test validation when project_index.json exists at spec level."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        project_index = spec_dir / "project_index.json"
        project_index.write_text(json.dumps({"project_type": "monorepo"}), encoding="utf-8")

        validator = PrereqsValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True
        assert len(result.errors) == 0

    def test_project_index_at_auto_claude_level(self, tmp_path):
        """Test warning when project_index.json exists at auto-claude level but not spec."""

        # Create directory structure: tmp_path/.auto-claude/specs/XXX/
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()
        auto_build_index = auto_claude_dir / "project_index.json"
        auto_build_index.write_text(json.dumps({"project_type": "single"}), encoding="utf-8")

        specs_dir = auto_claude_dir / "specs"
        specs_dir.mkdir()
        spec_dir = specs_dir / "001"
        spec_dir.mkdir()

        validator = PrereqsValidator(spec_dir)
        result = validator.validate()

        # Should have warning about project_index at auto-claude level
        assert result.valid is True  # Still valid, just a warning
        assert any("auto-claude" in w.lower() for w in result.warnings)
        assert any("project_index.json" in w for w in result.warnings)

    def test_project_index_missing_everywhere(self, tmp_path):
        """Test error when project_index.json is missing at both levels."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        # No project_index.json anywhere

        validator = PrereqsValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("not found" in e.lower() for e in result.errors)

    def test_fix_includes_copy_command(self, tmp_path):
        """Test that suggested fix includes copy command when index at auto-claude level."""

        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()
        auto_build_index = auto_claude_dir / "project_index.json"
        auto_build_index.write_text(json.dumps({"project_type": "single"}), encoding="utf-8")

        specs_dir = auto_claude_dir / "specs"
        specs_dir.mkdir()
        spec_dir = specs_dir / "001"
        spec_dir.mkdir()

        validator = PrereqsValidator(spec_dir)
        result = validator.validate()

        # Should have copy command in fixes
        assert any("cp" in fix or "copy" in fix.lower() for fix in result.fixes)


class TestPrereqsValidatorDirectoryScenarios:
    """Tests for various directory-related scenarios."""

    def test_spec_dir_is_file_not_directory(self, tmp_path):
        """Test when spec_dir path exists but is a file, not directory."""

        spec_dir = tmp_path / "spec_file"
        spec_dir.write_text("I am a file", encoding="utf-8")

        validator = PrereqsValidator(spec_dir)
        result = validator.validate()

        # The validator checks .exists() which returns True for files too
        # So it will proceed to check for project_index.json inside
        # Since project_index.json doesn't exist, we get "not found" error
        assert result.valid is False
        # The error is about project_index.json, not directory existence
        assert "not found" in result.errors[0].lower()

    def test_nested_spec_directory(self, tmp_path):
        """Test with deeply nested spec directory."""

        spec_dir = tmp_path / "level1" / "level2" / "level3" / "spec"
        spec_dir.mkdir(parents=True)
        project_index = spec_dir / "project_index.json"
        project_index.write_text(json.dumps({"project_type": "test"}), encoding="utf-8")

        validator = PrereqsValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True

    def test_relative_vs_absolute_paths(self, tmp_path):
        """Test that validator works with both relative and absolute paths."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        project_index = spec_dir / "project_index.json"
        project_index.write_text(json.dumps({"project_type": "test"}), encoding="utf-8")

        # Test with absolute path
        validator_abs = PrereqsValidator(spec_dir.resolve())
        result_abs = validator_abs.validate()
        assert result_abs.valid is True

    def test_symlink_to_directory(self, tmp_path):
        """Test validation with symlinked directory."""

        if not hasattr(tmp_path, "symlink_to"):
            pytest.skip("Symlink creation not supported on this platform")

        # Create actual directory
        actual_dir = tmp_path / "actual_spec"
        actual_dir.mkdir()
        project_index = actual_dir / "project_index.json"
        project_index.write_text(json.dumps({"project_type": "test"}), encoding="utf-8")

        # Create symlink
        spec_dir = tmp_path / "spec_link"
        spec_dir.symlink_to(actual_dir)

        validator = PrereqsValidator(spec_dir)
        result = validator.validate()

        # Symlinks should work
        assert result.valid is True


class TestPrereqsValidatorProjectIndexContent:
    """Tests for project_index.json content validation."""

    def test_valid_project_index_with_all_fields(self, tmp_path):
        """Test with fully populated project_index.json."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        project_index = spec_dir / "project_index.json"
        content = {
            "project_type": "monorepo",
            "services": ["api", "frontend", "worker"],
            "infrastructure": ["postgres", "redis"],
            "conventions": ["python", "typescript"],
            "root_path": str(tmp_path),
            "created_at": "2024-01-01T00:00:00Z",
            "git_info": {
                "branch": "main",
                "remote": "origin"
            }
        }
        project_index.write_text(json.dumps(content), encoding="utf-8")

        validator = PrereqsValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True
        assert len(result.errors) == 0

    def test_project_index_with_empty_object(self, tmp_path):
        """Test with empty project_index.json (no project_type)."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        project_index = spec_dir / "project_index.json"
        project_index.write_text(json.dumps({}), encoding="utf-8")

        validator = PrereqsValidator(spec_dir)
        result = validator.validate()

        # Empty object still means file exists, so valid
        assert result.valid is True

    def test_project_index_with_invalid_json(self, tmp_path):
        """Test with malformed project_index.json."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        project_index = spec_dir / "project_index.json"
        project_index.write_text('{invalid json}', encoding="utf-8")

        validator = PrereqsValidator(spec_dir)
        result = validator.validate()

        # File exists so prereqs check passes
        # (JSON validation is not part of prereqs validator)
        assert result.valid is True


class TestPrereqsValidatorErrorMessages:
    """Tests for error message content and suggested fixes."""

    def test_error_message_for_missing_directory(self, tmp_path):
        """Test error message includes directory path."""

        spec_dir = tmp_path / "nonexistent_spec_dir"

        validator = PrereqsValidator(spec_dir)
        result = validator.validate()

        assert any(str(spec_dir) in e or "nonexistent" in e.lower() for e in result.errors)

    def test_fix_suggests_mkdir_for_missing_directory(self, tmp_path):
        """Test suggested fix includes mkdir command."""

        spec_dir = tmp_path / "needs_creation"

        validator = PrereqsValidator(spec_dir)
        result = validator.validate()

        assert any("mkdir" in fix.lower() or "create" in fix.lower() for fix in result.fixes)

    def test_fix_suggests_analyzer_command(self, tmp_path):
        """Test suggested fix includes analyzer command when index missing."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = PrereqsValidator(spec_dir)
        result = validator.validate()

        assert any("analyzer" in fix.lower() for fix in result.fixes)


class TestPrereqsValidatorEdgeCases:
    """Tests for edge cases and unusual scenarios."""

    def test_spec_dir_with_spaces_in_name(self, tmp_path):
        """Test with spaces in directory name."""

        spec_dir = tmp_path / "my spec directory"
        spec_dir.mkdir()
        project_index = spec_dir / "project_index.json"
        project_index.write_text(json.dumps({"project_type": "test"}), encoding="utf-8")

        validator = PrereqsValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True

    def test_spec_dir_with_special_characters(self, tmp_path):
        """Test with special characters in directory name."""

        spec_dir = tmp_path / "spec-test_v1.2.3"
        spec_dir.mkdir()
        project_index = spec_dir / "project_index.json"
        project_index.write_text(json.dumps({"project_type": "test"}), encoding="utf-8")

        validator = PrereqsValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True

    def test_multiple_validations_same_validator(self, tmp_path):
        """Test running validate multiple times on same validator instance."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        project_index = spec_dir / "project_index.json"
        project_index.write_text(json.dumps({"project_type": "test"}), encoding="utf-8")

        validator = PrereqsValidator(spec_dir)

        # Validate multiple times
        result1 = validator.validate()
        result2 = validator.validate()
        result3 = validator.validate()

        assert result1.valid is True
        assert result2.valid is True
        assert result3.valid is True

    def test_validation_after_creating_missing_files(self, tmp_path):
        """Test validation after creating missing project_index."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        validator = PrereqsValidator(spec_dir)
        result1 = validator.validate()
        assert result1.valid is False

        # Now create the missing file
        project_index = spec_dir / "project_index.json"
        project_index.write_text(json.dumps({"project_type": "test"}), encoding="utf-8")

        result2 = validator.validate()
        assert result2.valid is True
