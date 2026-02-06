"""Tests for spec/phases/utils.py module"""

from pathlib import Path
from unittest.mock import MagicMock, patch
from concurrent.futures import TimeoutError

import pytest

from spec.phases.utils import run_script


class TestRunScript:
    """Tests for run_script utility function"""

    def test_run_script_success(self, tmp_path):
        """Test successful script execution"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        # Create a simple test script
        script_path = auto_claude / "test_script.py"
        script_path.write_text('print("Hello, World!")', encoding="utf-8")

        success, output = run_script(project_dir, "test_script.py", [])

        assert success is True
        assert "Hello, World!" in output
        assert output.strip() == "Hello, World!"

    def test_run_script_with_arguments(self, tmp_path):
        """Test script execution with command-line arguments"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        # Create a script that uses arguments
        script_path = auto_claude / "args_script.py"
        script_path.write_text(
            'import sys\nprint(" ".join(sys.argv[1:]))', encoding="utf-8"
        )

        success, output = run_script(project_dir, "args_script.py", ["arg1", "arg2"])

        assert success is True
        assert "arg1 arg2" in output

    def test_run_script_file_not_found(self, tmp_path):
        """Test script not found error"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        success, output = run_script(project_dir, "nonexistent.py", [])

        assert success is False
        assert "Script not found" in output
        assert "nonexistent.py" in output

    def test_run_script_non_zero_exit_code(self, tmp_path):
        """Test script execution with non-zero exit code"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        # Create a script that exits with error
        script_path = auto_claude / "error_script.py"
        script_path.write_text('import sys\nsys.exit(1)', encoding="utf-8")

        success, output = run_script(project_dir, "error_script.py", [])

        assert success is False
        # stderr or stdout should be captured (empty in this case)

    def test_run_script_stderr_captured(self, tmp_path):
        """Test that stderr is captured when script fails"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        # Create a script that writes to stderr and exits with error
        script_path = auto_claude / "stderr_script.py"
        script_path.write_text(
            'import sys\nsys.stderr.write("Error message\\n")\nsys.exit(1)',
            encoding="utf-8"
        )

        success, output = run_script(project_dir, "stderr_script.py", [])

        assert success is False
        assert "Error message" in output

    def test_run_script_stdout_on_error(self, tmp_path):
        """Test that stdout is captured when script fails with no stderr"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        # Create a script that writes to stdout but exits with error
        script_path = auto_claude / "stdout_error_script.py"
        script_path.write_text(
            'print("Error output")\nimport sys\nsys.exit(2)',
            encoding="utf-8"
        )

        success, output = run_script(project_dir, "stdout_error_script.py", [])

        assert success is False
        assert "Error output" in output

    def test_run_script_timeout(self, tmp_path):
        """Test script execution timeout"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        # Create a script that runs indefinitely
        script_path = auto_claude / "timeout_script.py"
        script_path.write_text(
            'import time\ntime.sleep(400)', encoding="utf-8"
        )

        # Mock subprocess.run to raise TimeoutExpired
        from subprocess import TimeoutExpired

        mock_result = MagicMock()
        mock_result.stdout = "partial output"

        with patch("subprocess.run", side_effect=TimeoutExpired("cmd", 300)):
            success, output = run_script(project_dir, "timeout_script.py", [])

        assert success is False
        assert "timed out" in output

    def test_run_script_exception_handling(self, tmp_path):
        """Test that general exceptions are handled"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        # Create a test script
        script_path = auto_claude / "test.py"
        script_path.write_text('print("test")', encoding="utf-8")

        # Mock subprocess.run to raise an exception
        with patch("subprocess.run", side_effect=PermissionError("Access denied")):
            success, output = run_script(project_dir, "test.py", [])

        assert success is False
        assert "Access denied" in output

    def test_run_script_uses_python_executable(self, tmp_path):
        """Test that the correct Python executable is used"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        # Create a test script that outputs the executable path
        script_path = auto_claude / "exe_script.py"
        script_path.write_text(
            'import sys\nprint(sys.executable)', encoding="utf-8"
        )

        success, output = run_script(project_dir, "exe_script.py", [])

        assert success is True
        # Output should contain the path to python executable
        # The path can be python, python3, python3.12, etc.
        output_path = output.strip()
        assert "python" in output_path.lower()

    def test_run_script_correct_command_construction(self, tmp_path):
        """Test that the command is constructed correctly"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "test.py"
        script_path.write_text('print("test")', encoding="utf-8")

        cmd_called = []

        def mock_run(cmd, *args, **kwargs):
            cmd_called.append(cmd)
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "test"
            return mock_result

        with patch("subprocess.run", side_effect=mock_run) as mock_run_obj:
            success, output = run_script(
                project_dir, "test.py", ["--arg1", "--arg2"]
            )

        assert success is True
        assert len(cmd_called) == 1
        cmd = cmd_called[0]
        # Command should be: [python_executable, script_path, arg1, arg2]
        assert len(cmd) == 4
        assert "python" in str(cmd[0])
        assert str(script_path) in cmd[1]
        assert cmd[2] == "--arg1"
        assert cmd[3] == "--arg2"

    def test_run_script_working_directory(self, tmp_path):
        """Test that the script runs in the correct working directory"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "cwd_script.py"
        script_path.write_text(
            'import os\nprint(os.getcwd())', encoding="utf-8"
        )

        success, output = run_script(project_dir, "cwd_script.py", [])

        assert success is True
        # Output should contain the project directory path
        assert str(project_dir) in output

    def test_run_script_empty_arguments(self, tmp_path):
        """Test script execution with empty arguments list"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        script_path = auto_claude / "test.py"
        script_path.write_text('print("No args")', encoding="utf-8")

        success, output = run_script(project_dir, "test.py", [])

        assert success is True
        assert "No args" in output
