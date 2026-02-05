"""Tests for process_validators"""

import pytest
from security.process_validators import (
    validate_pkill_command,
    validate_kill_command,
    validate_killall_command,
)


class TestValidatePkillCommand:
    """Tests for validate_pkill_command"""

    def test_allowed_process_names(self):
        """Test pkill with allowed process names is permitted"""
        allowed_processes = [
            "pkill node",
            "pkill npm",
            "pkill python",
            "pkill python3",
            "pkill flask",
            "pkill uvicorn",
            "pkill gunicorn",
            "pkill pytest",
            "pkill vite",
            "pkill next",
            "pkill webpack",
            "pkill cargo",
            "pkill rustc",
            "pkill go",
            "pkill ruby",
            "pkill redis-server",
        ]
        for cmd in allowed_processes:
            is_valid, error = validate_pkill_command(cmd)
            assert is_valid, f"Command should be allowed: {cmd}"
            assert error == ""

    def test_disallowed_process_names(self):
        """Test pkill with disallowed process names is blocked"""
        disallowed_processes = [
            "pkill systemd",
            "pkill init",
            "pkill sshd",
            "pkill apache",
        ]
        for cmd in disallowed_processes:
            is_valid, error = validate_pkill_command(cmd)
            assert not is_valid, f"Command should be blocked: {cmd}"
            assert "dev processes" in error.lower()

    def test_pkill_with_flags(self):
        """Test pkill with various flags"""
        is_valid, _ = validate_pkill_command("pkill -f node")
        assert is_valid

        is_valid, _ = validate_pkill_command("pkill -9 python")
        assert is_valid

        is_valid, _ = validate_pkill_command("pkill - signal node")
        assert is_valid

    def test_pkill_empty_command(self):
        """Test empty pkill command is rejected"""
        is_valid, error = validate_pkill_command("")
        assert not is_valid
        assert "empty" in error.lower()

    def test_pkill_parse_error(self):
        """Test pkill with unparseable input is rejected"""
        is_valid, error = validate_pkill_command('pkill "node')
        assert not is_valid
        assert "parse" in error.lower()

    def test_pkill_full_command_match(self):
        """Test pkill -f with full command line"""
        is_valid, _ = validate_pkill_command("pkill -f 'python server.py'")
        assert is_valid

        # First word should be extracted for validation
        is_valid, _ = validate_pkill_command("pkill -f 'node server.js'")
        assert is_valid

    def test_pkill_with_no_process_name(self):
        """Test pkill without process name is rejected"""
        is_valid, error = validate_pkill_command("pkill")
        assert not is_valid
        assert "process name" in error.lower()

        is_valid, error = validate_pkill_command("pkill -f")
        assert not is_valid
        assert "process name" in error.lower()


class TestValidateKillCommand:
    """Tests for validate_kill command"""

    def test_safe_pids_allowed(self):
        """Test kill with safe PIDs is allowed"""
        safe_commands = [
            "kill 1234",
            "kill 1",
            "kill 9999",
            "kill -9 1234",
            "kill -15 5678",
            "kill -TERM 9012",
            "kill -SIGKILL 3456",
        ]
        for cmd in safe_commands:
            is_valid, error = validate_kill_command(cmd)
            assert is_valid, f"Command should be allowed: {cmd}"
            assert error == ""

    def test_dangerous_pids_blocked(self):
        """Test kill with dangerous PIDs is blocked"""
        dangerous_commands = [
            "kill -1",
            "kill 0",
            "kill -0",
            "kill -9 -1",
            "kill -1 1234",
        ]
        for cmd in dangerous_commands:
            is_valid, error = validate_kill_command(cmd)
            assert not is_valid, f"Command should be blocked: {cmd}"
            assert "not allowed" in error.lower() or "affects all processes" in error.lower()

    def test_kill_with_signals(self):
        """Test kill with various signal options"""
        is_valid, _ = validate_kill_command("kill -HUP 1234")
        assert is_valid

        is_valid, _ = validate_kill_command("kill -INT 5678")
        assert is_valid

        is_valid, _ = validate_kill_command("kill -QUIT 9012")
        assert is_valid

        is_valid, _ = validate_kill_command("kill -KILL 3456")
        assert is_valid

    def test_kill_parse_error(self):
        """Test kill with unparseable input is rejected"""
        is_valid, error = validate_kill_command('kill "1234')
        assert not is_valid
        assert "parse" in error.lower()

    def test_kill_empty_command(self):
        """Test empty kill command is allowed (no PIDs specified)"""
        is_valid, _ = validate_kill_command("kill")
        assert is_valid

    def test_kill_multiple_pids(self):
        """Test kill with multiple PIDs"""
        is_valid, _ = validate_kill_command("kill 1234 5678 9012")
        assert is_valid


class TestValidateKillallCommand:
    """Tests for validate_killall_command"""

    def test_delegates_to_pkill(self):
        """Test that killall uses the same validation as pkill"""
        # Safe processes
        safe_commands = [
            "killall node",
            "killall python",
            "killall npm",
        ]
        for cmd in safe_commands:
            is_valid, error = validate_killall_command(cmd)
            assert is_valid, f"Command should be allowed: {cmd}"

    def test_blocks_dangerous_processes(self):
        """Test that killall blocks dangerous processes"""
        dangerous_commands = [
            "killall systemd",
            "killall init",
            "killall sshd",
        ]
        for cmd in dangerous_commands:
            is_valid, error = validate_killall_command(cmd)
            assert not is_valid, f"Command should be blocked: {cmd}"
            assert "dev processes" in error.lower()

    def test_killall_with_flags(self):
        """Test killall with various flags"""
        is_valid, _ = validate_killall_command("killall -9 node")
        assert is_valid

        is_valid, _ = validate_killall_command("killall -e python")
        assert is_valid

    def test_killall_empty_command(self):
        """Test empty killall command is rejected"""
        is_valid, error = validate_killall_command("")
        assert not is_valid
        assert "empty" in error.lower()

    def test_killall_parse_error(self):
        """Test killall with unparseable input is rejected"""
        is_valid, error = validate_killall_command('killall "node')
        assert not is_valid
        assert "parse" in error.lower()

    def test_killall_no_process_name(self):
        """Test killall without process name is rejected"""
        is_valid, error = validate_killall_command("killall")
        assert not is_valid
        assert "process name" in error.lower()

    def test_killall_full_command_match(self):
        """Test killall -f with full command line"""
        is_valid, _ = validate_killall_command("killall -f 'python server.py'")
        assert is_valid

        # First word should be extracted for validation
        is_valid, _ = validate_killall_command("killall -f 'node server.js'")
        assert is_valid
