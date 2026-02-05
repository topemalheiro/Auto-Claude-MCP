"""
Tests for spec.validate_pkg.models module
Comprehensive tests for ValidationResult class.
"""

from spec.validate_pkg.models import ValidationResult


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_create_valid_result(self):
        """Test creating a valid validation result."""
        result = ValidationResult(
            valid=True,
            checkpoint="test",
            errors=[],
            warnings=[],
            fixes=[],
        )

        assert result.valid is True
        assert result.checkpoint == "test"
        assert result.errors == []
        assert result.warnings == []
        assert result.fixes == []

    def test_create_invalid_result(self):
        """Test creating an invalid validation result with errors."""
        result = ValidationResult(
            valid=False,
            checkpoint="context",
            errors=["File not found", "Invalid JSON"],
            warnings=["Minor issue"],
            fixes=["Create the file", "Fix JSON syntax"],
        )

        assert result.valid is False
        assert result.checkpoint == "context"
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert len(result.fixes) == 2

    def test_str_pass_result(self):
        """Test __str__ method with passing result."""
        result = ValidationResult(
            valid=True,
            checkpoint="prereqs",
            errors=[],
            warnings=[],
            fixes=[],
        )

        output = str(result)

        assert "Checkpoint: prereqs" in output
        assert "Status: PASS" in output
        assert "Errors:" not in output
        assert "Warnings:" not in output

    def test_str_fail_result_with_errors(self):
        """Test __str__ method with failing result and errors."""
        result = ValidationResult(
            valid=False,
            checkpoint="context",
            errors=["Missing required field: task_description"],
            warnings=[],
            fixes=[],
        )

        output = str(result)

        assert "Checkpoint: context" in output
        assert "Status: FAIL" in output
        assert "Errors:" in output
        assert "[X] Missing required field: task_description" in output
        assert "Warnings:" not in output

    def test_str_fail_result_with_warnings(self):
        """Test __str__ method with result containing warnings."""
        result = ValidationResult(
            valid=True,
            checkpoint="spec",
            errors=[],
            warnings=["Content is below minimum length", "Missing recommended section"],
            fixes=[],
        )

        output = str(result)

        assert "Checkpoint: spec" in output
        assert "Status: PASS" in output
        assert "Warnings:" in output
        assert "[!] Content is below minimum length" in output
        assert "[!] Missing recommended section" in output

    def test_str_fail_result_with_fixes(self):
        """Test __str__ method with failing result that has fixes."""
        result = ValidationResult(
            valid=False,
            checkpoint="implementation_plan",
            errors=["No phases defined"],
            warnings=[],
            fixes=["Add at least one phase to the plan"],
        )

        output = str(result)

        assert "Checkpoint: implementation_plan" in output
        assert "Status: FAIL" in output
        assert "Errors:" in output
        assert "[X] No phases defined" in output
        assert "Suggested Fixes:" in output
        assert "-> Add at least one phase to the plan" in output

    def test_str_with_multiple_errors(self):
        """Test __str__ method with multiple errors."""
        result = ValidationResult(
            valid=False,
            checkpoint="plan",
            errors=["Error 1", "Error 2", "Error 3"],
            warnings=[],
            fixes=[],
        )

        output = str(result)

        assert "[X] Error 1" in output
        assert "[X] Error 2" in output
        assert "[X] Error 3" in output

    def test_str_with_multiple_warnings(self):
        """Test __str__ method with multiple warnings."""
        result = ValidationResult(
            valid=True,
            checkpoint="context",
            errors=[],
            warnings=["Warning 1", "Warning 2"],
            fixes=[],
        )

        output = str(result)

        assert "[!] Warning 1" in output
        assert "[!] Warning 2" in output

    def test_str_with_multiple_fixes(self):
        """Test __str__ method with multiple fixes."""
        result = ValidationResult(
            valid=False,
            checkpoint="spec",
            errors=["Missing sections"],
            warnings=[],
            fixes=["Fix 1", "Fix 2", "Fix 3"],
        )

        output = str(result)

        assert "-> Fix 1" in output
        assert "-> Fix 2" in output
        assert "-> Fix 3" in output

    def test_str_with_all_components(self):
        """Test __str__ method with errors, warnings, and fixes."""
        result = ValidationResult(
            valid=False,
            checkpoint="context",
            errors=["Invalid JSON structure"],
            warnings=["Deprecated field found"],
            fixes=["Update JSON schema", "Remove deprecated field"],
        )

        output = str(result)

        assert "Checkpoint: context" in output
        assert "Status: FAIL" in output
        assert "Errors:" in output
        assert "[X] Invalid JSON structure" in output
        assert "Warnings:" in output
        assert "[!] Deprecated field found" in output
        assert "Suggested Fixes:" in output
        assert "-> Update JSON schema" in output
        assert "-> Remove deprecated field" in output

    def test_str_pass_no_fixes_shown(self):
        """Test that fixes are not shown when result is valid."""
        result = ValidationResult(
            valid=True,
            checkpoint="prereqs",
            errors=[],
            warnings=[],
            fixes=["This fix should not appear"],
        )

        output = str(result)

        assert "Suggested Fixes:" not in output
        assert "-> This fix should not appear" not in output

    def test_str_fail_fixes_only_when_invalid(self):
        """Test that fixes are only shown when result is invalid."""
        # Valid result - fixes should not show
        valid_result = ValidationResult(
            valid=True,
            checkpoint="test",
            errors=[],
            warnings=[],
            fixes=["Fix for valid case"],
        )

        valid_output = str(valid_result)
        assert "Suggested Fixes:" not in valid_output

        # Invalid result - fixes should show
        invalid_result = ValidationResult(
            valid=False,
            checkpoint="test",
            errors=["Error"],
            warnings=[],
            fixes=["Fix for invalid case"],
        )

        invalid_output = str(invalid_result)
        assert "Suggested Fixes:" in invalid_output
        assert "-> Fix for invalid case" in invalid_output

    def test_str_empty_errors_warnings_fixes(self):
        """Test __str__ method with empty lists."""
        result = ValidationResult(
            valid=True,
            checkpoint="test",
            errors=[],
            warnings=[],
            fixes=[],
        )

        output = str(result)

        # Should only have checkpoint and status
        lines = output.strip().split("\n")
        assert len(lines) == 2
        assert "Checkpoint: test" in lines[0]
        assert "Status: PASS" in lines[1]

    def test_dataclass_immutability(self):
        """Test that ValidationResult behaves like a dataclass."""
        result = ValidationResult(
            valid=True,
            checkpoint="test",
            errors=[],
            warnings=[],
            fixes=[],
        )

        # Should have all fields
        assert hasattr(result, "valid")
        assert hasattr(result, "checkpoint")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")
        assert hasattr(result, "fixes")
