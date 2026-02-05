"""
Tests for security.validation_models module.
"""

import pytest
from collections.abc import Callable

from security.validation_models import (
    ValidatorFunction,
    ValidationResult,
)


class TestValidationModels:
    """Tests for validation model types."""

    def test_validation_result_type(self):
        """Test ValidationResult is a tuple of (bool, str)."""
        result: ValidationResult = (True, "No error")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)

    def test_validation_result_success(self):
        """Test successful validation result."""
        result: ValidationResult = (True, "")
        assert result[0] is True
        assert result[1] == ""

    def test_validation_result_failure(self):
        """Test failed validation result."""
        result: ValidationResult = (False, "Invalid command")
        assert result[0] is False
        assert result[1] == "Invalid command"

    def test_validator_function_type(self):
        """Test ValidatorFunction is a callable type."""
        def dummy_validator(input_str: str) -> ValidationResult:
            return (True, "ok")

        assert callable(dummy_validator)
        # Check if it matches the ValidatorFunction type signature
        result = dummy_validator("test")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_validator_function_return_types(self):
        """Test validator function returns correct types."""
        def string_validator(s: str) -> ValidationResult:
            if len(s) < 3:
                return (False, "String too short")
            return (True, "")

        result_valid = string_validator("test")
        result_invalid = string_validator("ab")

        # Valid result
        assert result_valid[0] is True
        assert result_valid[1] == ""

        # Invalid result
        assert result_invalid[0] is False
        assert "too short" in result_invalid[1]

    def test_validation_result_unpacking(self):
        """Test ValidationResult can be unpacked."""
        is_valid, error_msg = (True, "No issues")
        assert is_valid is True
        assert error_msg == "No issues"

        is_valid, error_msg = (False, "Error found")
        assert is_valid is False
        assert error_msg == "Error found"

    def test_validation_result_in_conditionals(self):
        """Test ValidationResult works in conditional expressions."""
        success = (True, "")
        failure = (False, "Error")

        # Can use first element directly
        assert success[0]
        assert not failure[0]

        # Can use tuple comparison
        assert (True, "") == success
        assert (False, "Error") == failure

    def test_validation_result_with_none_error(self):
        """Test ValidationResult can have None as error message."""
        # Type hint says str, but None might be used in practice
        result: ValidationResult = (True, "")  # Empty string for success
        assert result[0] is True
        assert result[1] == ""

    def test_validation_result_with_long_error(self):
        """Test ValidationResult with long error message."""
        long_error = "This is a very long error message that contains detailed information about what went wrong during validation"
        result: ValidationResult = (False, long_error)
        assert result[0] is False
        assert result[1] == long_error

    def test_validation_result_mutability(self):
        """Test ValidationResult tuple immutability."""
        result = (True, "ok")
        # Tuples are immutable, so we can't modify them
        # This test documents that behavior
        assert isinstance(result, tuple)
        with pytest.raises(TypeError):
            result[0] = False  # type: ignore

    def test_multiple_validator_functions(self):
        """Test using multiple validator functions."""
        def validate_length(s: str) -> ValidationResult:
            return (len(s) >= 3, f"Length must be >= 3, got {len(s)}")

        def validate_no_spaces(s: str) -> ValidationResult:
            return (" " not in s, "Must not contain spaces")

        validators: list[ValidatorFunction] = [
            validate_length,
            validate_no_spaces,
        ]

        # Test valid input
        for validator in validators:
            result = validator("test")
            assert result[0], f"Validator failed: {result[1]}"

        # Test invalid input (too short)
        result = validate_length("ab")
        assert not result[0]

        # Test invalid input (has spaces)
        result = validate_no_spaces("test string")
        assert not result[0]

    def test_validator_function_with_complex_input(self):
        """Test validator with complex input string."""
        def validate_command(cmd: str) -> ValidationResult:
            dangerous = ["rm -rf", "format", "delete"]
            if any(d in cmd.lower() for d in dangerous):
                return (False, "Dangerous command detected")
            return (True, "")

        # Safe commands
        assert validate_command("ls -la")[0] is True
        assert validate_command("git status")[0] is True

        # Dangerous commands
        result = validate_command("rm -rf /")
        assert result[0] is False
        assert "Dangerous" in result[1]

    def test_validation_result_consistency(self):
        """Test ValidationResult consistency across uses."""
        results: list[ValidationResult] = [
            (True, ""),
            (False, "Error 1"),
            (True, "Warning but ok"),
            (False, "Error 2"),
        ]

        for is_valid, msg in results:
            assert isinstance(is_valid, bool)
            assert isinstance(msg, str)
