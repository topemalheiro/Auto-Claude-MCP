"""Tests for phase utilities"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from spec.phases.utils import run_script


class TestRunScript:
    """Tests for run_script function"""

    def test_run_script_success(self, tmp_path):
        """Test successful script execution"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        # Create a simple Python script that succeeds
        script_path = auto_claude / "test_script.py"
        script_path.write_text('print("Success output")', encoding="utf-8")

        success, output = run_script(project_dir, "test_script.py", [])

        assert success is True
        assert "Success output" in output

    def test_run_script_with_args(self, tmp_path):
        """Test script execution with arguments"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        # Create script that prints arguments
        script_path = auto_claude / "args_script.py"
        script_path.write_text(
            'import sys\nprint("Args:", sys.argv[1:])',
            encoding="utf-8"
        )

        success, output = run_script(project_dir, "args_script.py", ["--arg1", "value1"])

        assert success is True
        assert "--arg1" in output
        assert "value1" in output

    def test_run_script_not_found(self, tmp_path):
        """Test handling when script doesn't exist"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        # Don't create the script
        success, output = run_script(project_dir, "nonexistent.py", [])

        assert success is False
        assert "Script not found" in output
        assert "nonexistent.py" in output

    def test_run_script_nonzero_exit_code(self, tmp_path):
        """Test handling script with non-zero exit code"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        # Create script that exits with error
        script_path = auto_claude / "failing_script.py"
        script_path.write_text('import sys\nsys.exit(1)', encoding="utf-8")

        success, output = run_script(project_dir, "failing_script.py", [])

        assert success is False

    def test_run_script_stderr_captured(self, tmp_path):
        """Test that stderr is captured on failure"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        # Create script that writes to stderr and exits
        script_path = auto_claude / "stderr_script.py"
        script_path.write_text(
            'import sys\nsys.stderr.write("Error message\\n")\nsys.exit(2)',
            encoding="utf-8"
        )

        success, output = run_script(project_dir, "stderr_script.py", [])

        assert success is False
        assert "Error message" in output

    def test_run_script_timeout(self, tmp_path):
        """Test handling script timeout"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        # Create script that runs longer than timeout
        script_path = auto_claude / "timeout_script.py"
        script_path.write_text(
            'import time\ntime.sleep(400)\nprint("Should not see this")',
            encoding="utf-8"
        )

        with patch("spec.phases.utils.subprocess.run") as mock_run:
            from subprocess import TimeoutExpired
            mock_run.side_effect = TimeoutExpired("python", 300)

            success, output = run_script(project_dir, "timeout_script.py", [])

        assert success is False
        assert "timed out" in output.lower()

    def test_run_script_exception(self, tmp_path):
        """Test handling general exception during script run"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        # Create a script
        script_path = auto_claude / "test.py"
        script_path.write_text('print("test")', encoding="utf-8")

        with patch("spec.phases.utils.subprocess.run", side_effect=Exception("Unexpected error")):
            success, output = run_script(project_dir, "test.py", [])

        assert success is False
        assert "Unexpected error" in output

    def test_run_script_working_directory(self, tmp_path):
        """Test script runs in project directory"""
        project_dir = tmp_path / "my_project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        # Create script that prints current directory
        script_path = auto_claude / "cwd_script.py"
        script_path.write_text(
            'import os\nprint(os.getcwd())',
            encoding="utf-8"
        )

        success, output = run_script(project_dir, "cwd_script.py", [])

        assert success is True
        assert str(project_dir) in output

    def test_run_script_stdout_on_success(self, tmp_path):
        """Test stdout is captured on success"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "stdout_script.py"
        script_path.write_text('print("Line 1")\nprint("Line 2")', encoding="utf-8")

        success, output = run_script(project_dir, "stdout_script.py", [])

        assert success is True
        assert "Line 1" in output
        assert "Line 2" in output

    def test_run_script_empty_args(self, tmp_path):
        """Test script with empty arguments list"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "noargs.py"
        script_path.write_text('print("No args")', encoding="utf-8")

        success, output = run_script(project_dir, "noargs.py", [])

        assert success is True
        assert "No args" in output

    def test_run_script_unicode_output(self, tmp_path):
        """Test script with unicode output"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "unicode.py"
        script_path.write_text('print("Unicode: ñ, é, 🎉")', encoding="utf-8")

        success, output = run_script(project_dir, "unicode.py", [])

        assert success is True
        assert "ñ" in output
        assert "é" in output
        assert "🎉" in output

    def test_run_script_with_syntax_error(self, tmp_path):
        """Test script with syntax error"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "syntax_error.py"
        script_path.write_text('invalid python syntax here', encoding="utf-8")

        success, output = run_script(project_dir, "syntax_error.py", [])

        assert success is False

    def test_run_script_runtime_error(self, tmp_path):
        """Test script with runtime error"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "runtime_error.py"
        script_path.write_text(
            'raise ValueError("Runtime error occurred")',
            encoding="utf-8"
        )

        success, output = run_script(project_dir, "runtime_error.py", [])

        assert success is False
        assert "Runtime error occurred" in output


class TestRunScriptEdgeCases:
    """Edge case tests for run_script function"""

    def test_run_script_with_many_args(self, tmp_path):
        """Test script with many arguments"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "many_args.py"
        script_path.write_text(
            'import sys\nprint(len(sys.argv[1:]))',
            encoding="utf-8"
        )

        args = [f"arg{i}" for i in range(100)]
        success, output = run_script(project_dir, "many_args.py", args)

        assert success is True
        assert "100" in output

    def test_run_script_with_special_chars_in_args(self, tmp_path):
        """Test script with special characters in arguments"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "special_args.py"
        script_path.write_text(
            'import sys\nprint(sys.argv[1])',
            encoding="utf-8"
        )

        success, output = run_script(project_dir, "special_args.py", ["--arg=value with spaces"])

        assert success is True
        assert "--arg=value with spaces" in output

    def test_run_script_output_truncation(self, tmp_path):
        """Test that large output is captured"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "large_output.py"
        script_path.write_text(
            'for i in range(1000):\n    print(f"Line {i}")',
            encoding="utf-8"
        )

        success, output = run_script(project_dir, "large_output.py", [])

        assert success is True
        assert "Line 0" in output
        assert "Line 999" in output

    def test_run_script_zero_exit_code(self, tmp_path):
        """Test explicit exit code 0"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "exit_zero.py"
        script_path.write_text('import sys\nsys.exit(0)', encoding="utf-8")

        success, output = run_script(project_dir, "exit_zero.py", [])

        assert success is True

    def test_run_script_different_exit_codes(self, tmp_path):
        """Test various non-zero exit codes"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        for exit_code in [1, 2, 127, 255]:
            script_path = auto_claude / f"exit_{exit_code}.py"
            script_path.write_text(f'import sys\nsys.exit({exit_code})', encoding="utf-8")

            success, output = run_script(project_dir, f"exit_{exit_code}.py", [])

            assert success is False

    def test_run_script_stderr_only(self, tmp_path):
        """Test script that only writes to stderr"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "stderr_only.py"
        script_path.write_text(
            'import sys\nsys.stderr.write("Only stderr")\nsys.exit(0)',
            encoding="utf-8"
        )

        success, output = run_script(project_dir, "stderr_only.py", [])

        assert success is True

    def test_run_script_mixed_stdout_stderr(self, tmp_path):
        """Test script with mixed stdout and stderr"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "mixed.py"
        script_path.write_text(
            'import sys\nprint("stdout")\nsys.stderr.write("stderr\\n")\nsys.exit(0)',
            encoding="utf-8"
        )

        success, output = run_script(project_dir, "mixed.py", [])

        assert success is True

    def test_run_script_with_newline_args(self, tmp_path):
        """Test script with newline characters in args"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "newline_args.py"
        script_path.write_text(
            'import sys\nprint(repr(sys.argv[1]))',
            encoding="utf-8"
        )

        success, output = run_script(project_dir, "newline_args.py", ["line1\nline2"])

        assert success is True

    def test_run_script_absolute_path_project_dir(self, tmp_path):
        """Test with absolute path for project_dir"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "abs_path.py"
        script_path.write_text('print("test")', encoding="utf-8")

        # Use absolute path
        success, output = run_script(project_dir.resolve(), "abs_path.py", [])

        assert success is True

    def test_run_script_script_name_with_extension(self, tmp_path):
        """Test script names with various extensions"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        # Test .py extension
        script_path = auto_claude / "test.py"
        script_path.write_text('print("py")', encoding="utf-8")

        success, output = run_script(project_dir, "test.py", [])

        assert success is True
        assert "py" in output

    def test_run_script_returns_tuple(self, tmp_path):
        """Test that return value is a tuple of (bool, str)"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "typecheck.py"
        script_path.write_text('print("output")', encoding="utf-8")

        result = run_script(project_dir, "typecheck.py", [])

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)

    def test_run_script_timeout_value_is_300_seconds(self, tmp_path):
        """Test that the timeout is set to 300 seconds (5 minutes)"""
        # This is a unit test for the hardcoded timeout value
        # We verify by checking the subprocess.run call
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "test.py"
        script_path.write_text('print("test")', encoding="utf-8")

        with patch("spec.phases.utils.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "test"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            run_script(project_dir, "test.py", [])

            # Check that timeout=300 was passed
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs.get("timeout") == 300

    def test_run_script_capture_output(self, tmp_path):
        """Test that capture_output=True is set for subprocess.run"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "test.py"
        script_path.write_text('print("test")', encoding="utf-8")

        with patch("spec.phases.utils.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "test"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            run_script(project_dir, "test.py", [])

            # Check that capture_output=True was passed
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs.get("capture_output") is True

    def test_run_script_text_mode(self, tmp_path):
        """Test that text=True is set for subprocess.run"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "test.py"
        script_path.write_text('print("test")', encoding="utf-8")

        with patch("spec.phases.utils.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "test"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            run_script(project_dir, "test.py", [])

            # Check that text=True was passed
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs.get("text") is True

    def test_run_script_uses_sys_executable(self, tmp_path):
        """Test that sys.executable is used for Python interpreter"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "test.py"
        script_path.write_text('print("test")', encoding="utf-8")

        with patch("spec.phases.utils.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "test"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            run_script(project_dir, "test.py", [])

            # Check that sys.executable was used
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == sys.executable
