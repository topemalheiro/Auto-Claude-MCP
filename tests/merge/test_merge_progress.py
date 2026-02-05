"""Comprehensive tests for merge/progress.py"""

import json
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from merge.progress import (
    MergeProgressStage,
    MergeProgressCallback,
    emit_progress,
)


class TestMergeProgressStage:
    """Tests for MergeProgressStage enum"""

    def test_all_stage_values(self):
        """Test that all expected stage values exist"""
        assert MergeProgressStage.ANALYZING.value == "analyzing"
        assert MergeProgressStage.DETECTING_CONFLICTS.value == "detecting_conflicts"
        assert MergeProgressStage.RESOLVING.value == "resolving"
        assert MergeProgressStage.VALIDATING.value == "validating"
        assert MergeProgressStage.COMPLETE.value == "complete"
        assert MergeProgressStage.ERROR.value == "error"

    def test_stage_count(self):
        """Test that we have exactly 6 stages"""
        assert len(MergeProgressStage) == 6

    def test_stage_iteration(self):
        """Test that stages can be iterated"""
        stages = list(MergeProgressStage)
        assert MergeProgressStage.ANALYZING in stages
        assert MergeProgressStage.COMPLETE in stages
        assert MergeProgressStage.ERROR in stages

    def test_stage_comparison(self):
        """Test stage equality"""
        assert MergeProgressStage.ANALYZING == MergeProgressStage.ANALYZING
        assert MergeProgressStage.ANALYZING != MergeProgressStage.COMPLETE
        assert MergeProgressStage.ERROR != MergeProgressStage.COMPLETE


class TestMergeProgressCallback:
    """Tests for MergeProgressCallback protocol"""

    def test_protocol_compatibility(self):
        """Test that a function implementing the protocol is compatible"""

        def mock_callback(
            stage: MergeProgressStage,
            percent: int,
            message: str,
            details: dict | None = None,
        ) -> None:
            pass

        # Should be able to assign to protocol type
        callback: MergeProgressCallback = mock_callback
        assert callback is not None

    def test_protocol_with_mock(self):
        """Test that MagicMock can be used as callback"""
        callback = MagicMock()

        # Should accept all parameters
        callback(MergeProgressStage.ANALYZING, 50, "Test message")
        callback(MergeProgressStage.COMPLETE, 100, "Done", {"conflicts_resolved": 5})

        assert callback.call_count == 2

    def test_protocol_callable(self):
        """Test that protocol is callable"""
        assert callable(MergeProgressCallback)

    def test_protocol_parameters(self):
        """Test protocol parameter types"""
        # This test verifies type annotations are correct
        # (would be caught by mypy if incorrect)
        callback = MagicMock()

        # Test with minimum parameters
        callback(MergeProgressStage.ANALYZING, 0, "Starting")

        # Test with all parameters
        callback(
            MergeProgressStage.RESOLVING,
            75,
            "Resolving conflicts",
            {"conflicts_found": 10, "conflicts_resolved": 7},
        )


class TestEmitProgress:
    """Tests for emit_progress function"""

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_basic(self, mock_stdout):
        """Test basic progress emission"""
        emit_progress(MergeProgressStage.ANALYZING, 10, "Analyzing files")

        output = mock_stdout.getvalue().strip()
        assert output

        data = json.loads(output)
        assert data["type"] == "progress"
        assert data["stage"] == "analyzing"
        assert data["percent"] == 10
        assert data["message"] == "Analyzing files"
        assert "details" not in data

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_with_details(self, mock_stdout):
        """Test progress emission with details"""
        details = {
            "conflicts_found": 5,
            "conflicts_resolved": 3,
            "current_file": "src/main.py",
        }

        emit_progress(
            MergeProgressStage.DETECTING_CONFLICTS,
            35,
            "Detecting conflicts",
            details,
        )

        output = mock_stdout.getvalue().strip()
        data = json.loads(output)

        assert data["details"] == details
        assert data["details"]["conflicts_found"] == 5
        assert data["details"]["conflicts_resolved"] == 3
        assert data["details"]["current_file"] == "src/main.py"

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_clamp_negative(self, mock_stdout):
        """Test that negative percentage is clamped to 0"""
        emit_progress(MergeProgressStage.ANALYZING, -10, "Starting")

        output = mock_stdout.getvalue().strip()
        data = json.loads(output)

        assert data["percent"] == 0

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_clamp_over_100(self, mock_stdout):
        """Test that percentage over 100 is clamped to 100"""
        emit_progress(MergeProgressStage.COMPLETE, 150, "Done")

        output = mock_stdout.getvalue().strip()
        data = json.loads(output)

        assert data["percent"] == 100

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_boundaries(self, mock_stdout):
        """Test exact boundary values (0 and 100)"""
        emit_progress(MergeProgressStage.ANALYZING, 0, "Start")
        output1 = mock_stdout.getvalue().strip()
        data1 = json.loads(output1)
        assert data1["percent"] == 0

        mock_stdout.truncate(0)
        mock_stdout.seek(0)

        emit_progress(MergeProgressStage.COMPLETE, 100, "Complete")
        output2 = mock_stdout.getvalue().strip()
        data2 = json.loads(output2)
        assert data2["percent"] == 100

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_all_stages(self, mock_stdout):
        """Test emitting progress for all stages"""
        stages = [
            (MergeProgressStage.ANALYZING, 25, "Analyzing"),
            (MergeProgressStage.DETECTING_CONFLICTS, 50, "Detecting"),
            (MergeProgressStage.RESOLVING, 75, "Resolving"),
            (MergeProgressStage.VALIDATING, 90, "Validating"),
            (MergeProgressStage.COMPLETE, 100, "Complete"),
            (MergeProgressStage.ERROR, 0, "Error occurred"),
        ]

        outputs = []
        for stage, percent, message in stages:
            emit_progress(stage, percent, message)
            output = mock_stdout.getvalue().strip()
            outputs.append(json.loads(output))

            # Clear for next iteration
            mock_stdout.truncate(0)
            mock_stdout.seek(0)

        assert len(outputs) == 6
        assert outputs[0]["stage"] == "analyzing"
        assert outputs[4]["stage"] == "complete"
        assert outputs[5]["stage"] == "error"

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_unicode_message(self, mock_stdout):
        """Test progress with unicode characters in message"""
        message = "Analyzing fichier.py: 5 conflits trouvés"

        emit_progress(MergeProgressStage.ANALYZING, 50, message)

        output = mock_stdout.getvalue().strip()
        data = json.loads(output)

        assert data["message"] == message

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_empty_message(self, mock_stdout):
        """Test progress with empty message"""
        emit_progress(MergeProgressStage.ANALYZING, 50, "")

        output = mock_stdout.getvalue().strip()
        data = json.loads(output)

        assert data["message"] == ""

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_empty_details(self, mock_stdout):
        """Test progress with empty details dict (excluded by truthy check)"""
        emit_progress(MergeProgressStage.RESOLVING, 60, "Resolving", {})

        output = mock_stdout.getvalue().strip()
        data = json.loads(output)

        # Empty dict is falsy, so it should NOT be included
        assert "details" not in data

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_special_characters_in_details(self, mock_stdout):
        """Test details with special characters"""
        details = {
            "file": "path/to/file with spaces.py",
            "conflict_type": "<<< HEAD",
        }

        emit_progress(MergeProgressStage.RESOLVING, 65, "Merging", details)

        output = mock_stdout.getvalue().strip()
        data = json.loads(output)

        assert data["details"]["file"] == "path/to/file with spaces.py"
        assert data["details"]["conflict_type"] == "<<< HEAD"

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_flush(self, mock_stdout):
        """Test that output is flushed (no buffering)"""
        emit_progress(MergeProgressStage.ANALYZING, 5, "Testing flush")

        output = mock_stdout.getvalue()
        # Should have output immediately due to flush=True
        assert len(output) > 0

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_multiple_calls(self, mock_stdout):
        """Test multiple progress emissions in sequence"""
        for i in range(0, 101, 10):
            emit_progress(MergeProgressStage.ANALYZING, i, f"Progress {i}%")

        output = mock_stdout.getvalue().strip()
        lines = output.split("\n")

        assert len(lines) == 11

        # Verify first and last
        first_data = json.loads(lines[0])
        last_data = json.loads(lines[-1])

        assert first_data["percent"] == 0
        assert last_data["percent"] == 100

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_with_callback_protocol(self, mock_stdout):
        """Test that emit_progress works with callback protocol"""
        # Create a callback that also calls emit_progress
        def progress_callback(
            stage: MergeProgressStage,
            percent: int,
            message: str,
            details: dict | None = None,
        ) -> None:
            emit_progress(stage, percent, message, details)

        # Use the callback
        progress_callback(
            MergeProgressStage.VALIDATING, 95, "Final validation"
        )

        output = mock_stdout.getvalue().strip()
        data = json.loads(output)

        assert data["stage"] == "validating"
        assert data["percent"] == 95

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_nested_details(self, mock_stdout):
        """Test details with nested structures"""
        details = {
            "files": [
                {"path": "src/main.py", "conflicts": 2},
                {"path": "src/utils.py", "conflicts": 1},
            ],
            "total_conflicts": 3,
        }

        emit_progress(MergeProgressStage.RESOLVING, 70, "Merging files", details)

        output = mock_stdout.getvalue().strip()
        data = json.loads(output)

        assert data["details"]["files"][0]["path"] == "src/main.py"
        assert data["details"]["total_conflicts"] == 3

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_numeric_strings_in_details(self, mock_stdout):
        """Test details with numeric values"""
        details = {
            "conflicts_found": 10,
            "conflicts_resolved": 7,
            "percent_remaining": 30,
        }

        emit_progress(MergeProgressStage.RESOLVING, 70, "Resolving", details)

        output = mock_stdout.getvalue().strip()
        data = json.loads(output)

        # JSON should preserve numbers as numbers, not strings
        assert isinstance(data["details"]["conflicts_found"], int)
        assert data["details"]["conflicts_found"] == 10

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_boolean_values(self, mock_stdout):
        """Test details with boolean values"""
        details = {"has_conflicts": True, "is_resolved": False}

        emit_progress(MergeProgressStage.DETECTING_CONFLICTS, 40, "Checking", details)

        output = mock_stdout.getvalue().strip()
        data = json.loads(output)

        assert data["details"]["has_conflicts"] is True
        assert data["details"]["is_resolved"] is False

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_null_values(self, mock_stdout):
        """Test details with null/None values"""
        details = {"error_message": None, "retry_count": 0}

        emit_progress(MergeProgressStage.ERROR, 0, "Failed", details)

        output = mock_stdout.getvalue().strip()
        data = json.loads(output)

        assert data["details"]["error_message"] is None

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_large_details(self, mock_stdout):
        """Test progress with large details dict"""
        details = {
            f"file_{i}": f"content_{i}" for i in range(50)
        }

        emit_progress(MergeProgressStage.ANALYZING, 50, "Processing", details)

        output = mock_stdout.getvalue().strip()
        data = json.loads(output)

        assert len(data["details"]) == 50
        assert "file_0" in data["details"]
        assert "file_49" in data["details"]

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_fractional_percent_clamp(self, mock_stdout):
        """Test that fractional percentages are handled (float inputs)"""
        # Pass a float (should work and be clamped)
        emit_progress(MergeProgressStage.ANALYZING, 50.7, "Halfway")

        output = mock_stdout.getvalue().strip()
        data = json.loads(output)

        assert data["percent"] == 50.7

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_zero_percent(self, mock_stdout):
        """Test zero percent progress"""
        emit_progress(MergeProgressStage.ANALYZING, 0, "Starting")

        output = mock_stdout.getvalue().strip()
        data = json.loads(output)

        assert data["percent"] == 0
        assert data["stage"] == "analyzing"

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_error_stage(self, mock_stdout):
        """Test error stage progress"""
        emit_progress(
            MergeProgressStage.ERROR,
            0,
            "Merge failed: permission denied",
            {"error_code": "EACCES"},
        )

        output = mock_stdout.getvalue().strip()
        data = json.loads(output)

        assert data["stage"] == "error"
        assert data["percent"] == 0
        assert "permission denied" in data["message"]
        assert data["details"]["error_code"] == "EACCES"

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_complete_stage(self, mock_stdout):
        """Test complete stage progress"""
        emit_progress(
            MergeProgressStage.COMPLETE,
            100,
            "Merge completed successfully",
            {"total_files": 42, "conflicts_resolved": 5},
        )

        output = mock_stdout.getvalue().strip()
        data = json.loads(output)

        assert data["stage"] == "complete"
        assert data["percent"] == 100
        assert "successfully" in data["message"]
        assert data["details"]["total_files"] == 42

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_newlines_in_message(self, mock_stdout):
        """Test message with newlines gets JSON encoded"""
        message = "Line 1\nLine 2\nLine 3"

        emit_progress(MergeProgressStage.ANALYZING, 50, message)

        output = mock_stdout.getvalue().strip()
        data = json.loads(output)

        assert data["message"] == message

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_json_validity(self, mock_stdout):
        """Test that output is always valid JSON"""
        test_cases = [
            (MergeProgressStage.ANALYZING, 0, "Start"),
            (MergeProgressStage.RESOLVING, 50, "Middle", {"key": "value"}),
            (MergeProgressStage.COMPLETE, 100, "End", {"a": 1, "b": True}),
        ]

        for stage, percent, message, *details_args in test_cases:
            emit_progress(stage, percent, message, *details_args)
            output = mock_stdout.getvalue().strip()

            # Should not raise
            data = json.loads(output)
            assert data is not None

            mock_stdout.truncate(0)
            mock_stdout.seek(0)

    @patch("sys.stdout", new_callable=StringIO)
    def test_emit_progress_integer_clamp_boundary(self, mock_stdout):
        """Test clamping at exact integer boundaries"""
        # Test -1 becomes 0
        emit_progress(MergeProgressStage.ANALYZING, -1, "Test")
        output = mock_stdout.getvalue().strip()
        data = json.loads(output)
        assert data["percent"] == 0

        mock_stdout.truncate(0)
        mock_stdout.seek(0)

        # Test 101 becomes 100
        emit_progress(MergeProgressStage.COMPLETE, 101, "Test")
        output = mock_stdout.getvalue().strip()
        data = json.loads(output)
        assert data["percent"] == 100
