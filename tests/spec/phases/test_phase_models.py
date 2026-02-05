"""Tests for phase models and constants"""

import json

import pytest
from dataclasses import asdict

from spec.phases.models import PhaseResult, MAX_RETRIES


class TestPhaseResult:
    """Tests for PhaseResult dataclass"""

    def test_create_phase_result_success(self):
        """Test creating a successful phase result"""
        result = PhaseResult(
            phase="discovery",
            success=True,
            output_files=["/path/to/file1.json", "/path/to/file2.json"],
            errors=[],
            retries=0
        )

        assert result.phase == "discovery"
        assert result.success is True
        assert len(result.output_files) == 2
        assert result.errors == []
        assert result.retries == 0

    def test_create_phase_result_failure(self):
        """Test creating a failed phase result with errors"""
        result = PhaseResult(
            phase="spec_writing",
            success=False,
            output_files=[],
            errors=["Error 1", "Error 2", "Error 3"],
            retries=2
        )

        assert result.phase == "spec_writing"
        assert result.success is False
        assert result.output_files == []
        assert len(result.errors) == 3
        assert result.retries == 2

    def test_phase_result_with_empty_lists(self):
        """Test phase result with empty output files and errors"""
        result = PhaseResult(
            phase="planning",
            success=True,
            output_files=[],
            errors=[],
            retries=0
        )

        assert result.phase == "planning"
        assert result.success is True
        assert result.output_files == []
        assert result.errors == []

    def test_phase_result_with_single_output_file(self):
        """Test phase result with single output file"""
        result = PhaseResult(
            phase="requirements",
            success=True,
            output_files=["/spec/requirements.json"],
            errors=[],
            retries=0
        )

        assert len(result.output_files) == 1
        assert result.output_files[0] == "/spec/requirements.json"

    def test_phase_result_max_retries(self):
        """Test phase result with maximum retries"""
        result = PhaseResult(
            phase="research",
            success=True,
            output_files=["/spec/research.json"],
            errors=["Attempt 1 failed", "Attempt 2 failed"],
            retries=MAX_RETRIES
        )

        assert result.retries == MAX_RETRIES

    def test_phase_result_to_dict(self):
        """Test converting PhaseResult to dictionary"""
        result = PhaseResult(
            phase="discovery",
            success=True,
            output_files=["/spec/context.json"],
            errors=[],
            retries=0
        )

        result_dict = asdict(result)

        assert result_dict == {
            "phase": "discovery",
            "success": True,
            "output_files": ["/spec/context.json"],
            "errors": [],
            "retries": 0
        }

    def test_phase_result_to_json(self):
        """Test serializing PhaseResult to JSON"""
        result = PhaseResult(
            phase="validation",
            success=True,
            output_files=["/spec/spec.md", "/spec/implementation_plan.json"],
            errors=[],
            retries=1
        )

        # Convert to dict then JSON
        json_str = json.dumps(asdict(result))
        parsed = json.loads(json_str)

        assert parsed["phase"] == "validation"
        assert parsed["success"] is True
        assert len(parsed["output_files"]) == 2
        assert parsed["retries"] == 1

    def test_phase_result_from_dict(self):
        """Test creating PhaseResult from dictionary"""
        data = {
            "phase": "quick_spec",
            "success": True,
            "output_files": ["/spec/spec.md"],
            "errors": [],
            "retries": 0
        }

        result = PhaseResult(**data)

        assert result.phase == "quick_spec"
        assert result.success is True
        assert len(result.output_files) == 1

    def test_phase_result_equality(self):
        """Test PhaseResult equality comparison"""
        result1 = PhaseResult(
            phase="discovery",
            success=True,
            output_files=["/spec/context.json"],
            errors=[],
            retries=0
        )

        result2 = PhaseResult(
            phase="discovery",
            success=True,
            output_files=["/spec/context.json"],
            errors=[],
            retries=0
        )

        assert result1 == result2

    def test_phase_result_inequality(self):
        """Test PhaseResult inequality comparison"""
        result1 = PhaseResult(
            phase="discovery",
            success=True,
            output_files=["/spec/context.json"],
            errors=[],
            retries=0
        )

        result2 = PhaseResult(
            phase="discovery",
            success=False,  # Different
            output_files=["/spec/context.json"],
            errors=[],
            retries=0
        )

        assert result1 != result2

    def test_phase_result_mutable(self):
        """Test that PhaseResult fields are mutable"""
        result = PhaseResult(
            phase="discovery",
            success=False,
            output_files=[],
            errors=["Error"],
            retries=0
        )

        # Modify fields
        result.success = True
        result.output_files.append("/spec/new_file.json")
        result.errors.clear()

        assert result.success is True
        assert len(result.output_files) == 1
        assert len(result.errors) == 0


class TestMAX_RETRIES:
    """Tests for MAX_RETRIES constant"""

    def test_max_retries_is_positive_integer(self):
        """Test MAX_RETRIES is a positive integer"""
        assert isinstance(MAX_RETRIES, int)
        assert MAX_RETRIES > 0

    def test_max_retries_value(self):
        """Test MAX_RETRIES has expected value"""
        assert MAX_RETRIES == 3

    def test_max_retries_not_zero(self):
        """Test MAX_RETRIES is not zero"""
        assert MAX_RETRIES != 0

    def test_max_retries_not_negative(self):
        """Test MAX_RETRIES is not negative"""
        assert MAX_RETRIES >= 0


class TestPhaseResultEdgeCases:
    """Edge case tests for PhaseResult"""

    def test_phase_result_with_unicode_in_errors(self):
        """Test phase result with unicode characters in errors"""
        result = PhaseResult(
            phase="spec_writing",
            success=False,
            output_files=[],
            errors=["Error: caractères spéciaux", "🚫 Forbidden"],
            retries=1
        )

        assert "caractères spéciaux" in result.errors[0]
        assert "🚫" in result.errors[1]

    def test_phase_result_with_long_file_paths(self):
        """Test phase result with very long file paths"""
        long_path = "/a" * 100 + "/file.json"
        result = PhaseResult(
            phase="discovery",
            success=True,
            output_files=[long_path],
            errors=[],
            retries=0
        )

        assert len(result.output_files[0]) > 200

    def test_phase_result_with_many_errors(self):
        """Test phase result with many error messages"""
        errors = [f"Error {i}" for i in range(100)]
        result = PhaseResult(
            phase="planning",
            success=False,
            output_files=[],
            errors=errors,
            retries=5
        )

        assert len(result.errors) == 100

    def test_phase_result_negative_retries(self):
        """Test phase result with negative retries (edge case)"""
        # This shouldn't happen in practice but test dataclass accepts it
        result = PhaseResult(
            phase="discovery",
            success=True,
            output_files=[],
            errors=[],
            retries=-1
        )

        assert result.retries == -1

    def test_phase_result_special_characters_in_phase_name(self):
        """Test phase result with special characters in phase name"""
        result = PhaseResult(
            phase="self_critique",
            success=True,
            output_files=[],
            errors=[],
            retries=0
        )

        assert "self_critique" in result.phase

    def test_phase_result_with_none_equivalent_values(self):
        """Test phase result treats empty strings/lists appropriately"""
        result = PhaseResult(
            phase="validation",
            success=True,
            output_files=[],
            errors=[],
            retries=0
        )

        # Empty lists should be falsy
        assert not result.output_files
        assert not result.errors

    def test_phase_result_immutability_of_fields(self):
        """Test that fields can be reassigned (dataclass is mutable by default)"""
        result = PhaseResult(
            phase="discovery",
            success=True,
            output_files=["/spec/file1.json"],
            errors=[],
            retries=0
        )

        original_phase = result.phase
        result.phase = "planning"

        assert result.phase != original_phase
        assert result.phase == "planning"
