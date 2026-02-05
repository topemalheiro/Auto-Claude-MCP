"""Tests for context_validator"""

from spec.validate_pkg.validators.context_validator import ContextValidator
from spec.validate_pkg.models import ValidationResult
from spec.validate_pkg.schemas import CONTEXT_SCHEMA
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import json


def test_ContextValidator___init__():
    """Test ContextValidator.__init__"""

    # Arrange
    spec_dir = Path("/tmp/test")

    # Act
    validator = ContextValidator(spec_dir)

    # Assert
    assert validator.spec_dir == spec_dir


def test_ContextValidator_validate(tmp_path):
    """Test ContextValidator.validate with valid context.json"""

    # Arrange
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    context_file = spec_dir / "context.json"
    context_file.write_text('{"task": "test", "project_dir": "/tmp"}', encoding="utf-8")

    validator = ContextValidator(spec_dir)

    # Act
    result = validator.validate()

    # Assert
    assert result is not None
    assert isinstance(result, ValidationResult)
    assert result.checkpoint == "context"


def test_ContextValidator_validate_missing_file(tmp_path):
    """Test ContextValidator.validate when context.json is missing"""

    # Arrange
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    # No context.json created

    validator = ContextValidator(spec_dir)

    # Act
    result = validator.validate()

    # Assert
    assert result.valid is False
    assert "not found" in result.errors[0].lower()
    assert len(result.fixes) > 0
    assert result.checkpoint == "context"


def test_ContextValidator_validate_invalid_json(tmp_path):
    """Test ContextValidator.validate with invalid JSON"""

    # Arrange
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    context_file = spec_dir / "context.json"
    context_file.write_text('{invalid json}', encoding="utf-8")

    validator = ContextValidator(spec_dir)

    # Act
    result = validator.validate()

    # Assert
    assert result.valid is False
    # The error message includes "invalid json" (case-insensitive match)
    assert "invalid" in result.errors[0].lower() and "json" in result.errors[0].lower()
    assert result.checkpoint == "context"


class TestContextValidatorRequiredFields:
    """Tests for required field validation."""

    def test_missing_task_description(self, tmp_path):
        """Test validation when 'task_description' field is missing."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        # Missing task_description
        context = {"project_dir": "/tmp"}
        context_file.write_text(json.dumps(context), encoding="utf-8")

        validator = ContextValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("Missing required field: task_description" in e for e in result.errors)

    def test_valid_context_with_only_required_fields(self, tmp_path):
        """Test validation with only required fields present."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        context = {"task_description": "Build a feature"}
        context_file.write_text(json.dumps(context), encoding="utf-8")

        validator = ContextValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True
        assert len(result.errors) == 0

    def test_valid_context_with_all_fields(self, tmp_path):
        """Test validation with all fields present."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        context = {
            "task_description": "Build a feature",
            "scoped_services": ["api", "frontend"],
            "files_to_modify": ["app.py"],
            "files_to_reference": ["utils.py"],
            "patterns": ["factory"],
            "service_contexts": {
                "api": {"type": "fastapi", "port": 8000}
            },
            "created_at": "2024-01-01T00:00:00Z"
        }
        context_file.write_text(json.dumps(context), encoding="utf-8")

        validator = ContextValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True
        assert len(result.errors) == 0


class TestContextValidatorRecommendedFields:
    """Tests for recommended field validation (warnings)."""

    def test_missing_files_to_modify_warning(self, tmp_path):
        """Test warning when 'files_to_modify' is missing."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        context = {"task_description": "Build a feature"}
        context_file.write_text(json.dumps(context), encoding="utf-8")

        validator = ContextValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True  # Warnings don't make it invalid
        assert any("Missing recommended field: files_to_modify" in w for w in result.warnings)

    def test_missing_files_to_reference_warning(self, tmp_path):
        """Test warning when 'files_to_reference' is missing."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        context = {"task_description": "Build a feature"}
        context_file.write_text(json.dumps(context), encoding="utf-8")

        validator = ContextValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True
        assert any("Missing recommended field: files_to_reference" in w for w in result.warnings)

    def test_missing_scoped_services_warning(self, tmp_path):
        """Test warning when 'scoped_services' is missing."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        context = {"task_description": "Build a feature"}
        context_file.write_text(json.dumps(context), encoding="utf-8")

        validator = ContextValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True
        assert any("Missing recommended field: scoped_services" in w for w in result.warnings)

    def test_empty_recommended_fields_warning(self, tmp_path):
        """Test warning when recommended fields are present but empty."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        context = {
            "task_description": "Build a feature",
            "files_to_modify": [],  # Empty list
            "files_to_reference": [],  # Empty list
            "scoped_services": []  # Empty list
        }
        context_file.write_text(json.dumps(context), encoding="utf-8")

        validator = ContextValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True
        # Empty lists should trigger warnings
        assert any("Missing recommended field: files_to_modify" in w for w in result.warnings)
        assert any("Missing recommended field: files_to_reference" in w for w in result.warnings)
        assert any("Missing recommended field: scoped_services" in w for w in result.warnings)

    def test_no_warnings_with_recommended_fields(self, tmp_path):
        """Test no warnings when recommended fields are present and populated."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        context = {
            "task_description": "Build a feature",
            "files_to_modify": ["app.py"],
            "files_to_reference": ["utils.py"],
            "scoped_services": ["api"]
        }
        context_file.write_text(json.dumps(context), encoding="utf-8")

        validator = ContextValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True
        # No warnings for recommended fields
        assert not any("Missing recommended field" in w for w in result.warnings)


class TestContextValidatorEdgeCases:
    """Tests for edge cases and complex scenarios."""

    def test_context_with_null_values(self, tmp_path):
        """Test validation with explicit null values."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        context = {
            "task_description": "Build a feature",
            "files_to_modify": None
        }
        context_file.write_text(json.dumps(context), encoding="utf-8")

        validator = ContextValidator(spec_dir)
        result = validator.validate()

        # Null should be treated as missing for recommended fields
        assert any("Missing recommended field: files_to_modify" in w for w in result.warnings)

    def test_context_with_complex_data_types(self, tmp_path):
        """Test validation with complex nested data structures."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        context = {
            "task_description": "Build a complex feature",
            "scoped_services": ["api", "frontend", "database"],
            "files_to_modify": [
                "apps/backend/api/main.py",
                "apps/frontend/src/components/Feature.tsx"
            ],
            "files_to_reference": [
                "shared/types.ts",
                "apps/backend/utils/helpers.py"
            ],
            "patterns": ["repository", "factory", "observer"],
            "service_contexts": {
                "api": {
                    "type": "fastapi",
                    "port": 8000,
                    "dependencies": ["database", "redis"]
                },
                "frontend": {
                    "type": "react",
                    "port": 3000,
                    "dependencies": ["api"]
                }
            }
        }
        context_file.write_text(json.dumps(context), encoding="utf-8")

        validator = ContextValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_context_with_special_characters_in_description(self, tmp_path):
        """Test validation with special characters and unicode in task_description."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        context = {
            "task_description": "Build feature with émojis 🎉 and special chars: <>&\"'\\n\\t"
        }
        context_file.write_text(json.dumps(context, ensure_ascii=False), encoding="utf-8")

        validator = ContextValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True

    def test_context_with_empty_task_description(self, tmp_path):
        """Test validation with empty task_description string."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        context = {"task_description": ""}
        context_file.write_text(json.dumps(context), encoding="utf-8")

        validator = ContextValidator(spec_dir)
        result = validator.validate()

        # Empty string is still a valid value (field is present)
        assert result.valid is True
        assert "task_description" not in str(result.errors)

    def test_context_with_large_arrays(self, tmp_path):
        """Test validation with large arrays in recommended fields."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        context = {
            "task_description": "Large refactoring",
            "files_to_modify": [f"file_{i}.py" for i in range(100)],
            "files_to_reference": [f"ref_{i}.py" for i in range(50)],
            "scoped_services": [f"service_{i}" for i in range(10)]
        }
        context_file.write_text(json.dumps(context), encoding="utf-8")

        validator = ContextValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True
        assert len(result.warnings) == 0


class TestContextValidatorJSONErrors:
    """Tests for various JSON parsing errors."""

    def test_json_with_trailing_comma(self, tmp_path):
        """Test JSON with trailing comma (invalid JSON)."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        context_file.write_text('{"task_description": "test",}', encoding="utf-8")

        validator = ContextValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        # Error message includes "invalid json" (case varies by Python version)
        assert "invalid" in result.errors[0].lower() and "json" in result.errors[0].lower()

    def test_json_with_unquoted_keys(self, tmp_path):
        """Test JSON with unquoted keys (invalid JSON)."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        context_file.write_text('{task_description: "test"}', encoding="utf-8")

        validator = ContextValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert "invalid" in result.errors[0].lower() and "json" in result.errors[0].lower()

    def test_json_with_single_quotes(self, tmp_path):
        """Test JSON with single quotes instead of double quotes (invalid JSON)."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        context_file.write_text("{'task_description': 'test'}", encoding="utf-8")

        validator = ContextValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert "invalid" in result.errors[0].lower() and "json" in result.errors[0].lower()

    def test_empty_json_file(self, tmp_path):
        """Test with empty JSON file."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        context_file.write_text("", encoding="utf-8")

        validator = ContextValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert "invalid" in result.errors[0].lower() and "json" in result.errors[0].lower()

    def test_json_array_instead_of_object(self, tmp_path):
        """Test with JSON array instead of object."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        context_file.write_text('["item1", "item2"]', encoding="utf-8")

        validator = ContextValidator(spec_dir)
        result = validator.validate()

        # Arrays don't have the required field
        assert result.valid is False
