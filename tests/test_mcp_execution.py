"""
Tests for mcp_server/services/execution_service.py
====================================================

Tests the ExecutionService singleton, event parsing, build lifecycle,
progress tracking, and log retrieval.
"""

import sys
from pathlib import Path

# Add backend to sys.path
_backend = Path(__file__).parent.parent / "apps" / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

# Pre-mock SDK modules before any mcp_server imports
from unittest.mock import MagicMock

if "claude_agent_sdk" not in sys.modules:
    sys.modules["claude_agent_sdk"] = MagicMock()
    sys.modules["claude_agent_sdk.types"] = MagicMock()

import json

import pytest

import mcp_server.services.execution_service as exec_mod
from mcp_server.services.execution_service import ExecutionService, get_execution_service


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the module-level singleton between tests."""
    exec_mod._instance = None
    yield
    exec_mod._instance = None


class TestGetExecutionService:
    """Tests for the singleton factory function."""

    def test_returns_instance(self, tmp_path):
        """get_execution_service creates an ExecutionService."""
        svc = get_execution_service(tmp_path)
        assert isinstance(svc, ExecutionService)
        assert svc.project_dir == tmp_path

    def test_returns_same_instance(self, tmp_path):
        """Repeated calls with the same path return the cached singleton."""
        svc1 = get_execution_service(tmp_path)
        svc2 = get_execution_service(tmp_path)
        assert svc1 is svc2

    def test_recreates_on_different_project(self, tmp_path):
        """Switching project_dir creates a fresh instance."""
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()

        svc_a = get_execution_service(dir_a)
        svc_b = get_execution_service(dir_b)
        assert svc_a is not svc_b
        assert svc_b.project_dir == dir_b


class TestParseEvent:
    """Tests for ExecutionService.parse_event()."""

    def test_parses_valid_event_line(self, tmp_path):
        """parse_event returns dict for a valid __TASK_EVENT__: JSON line."""
        svc = ExecutionService(tmp_path)
        payload = {"type": "subtask_complete", "index": 1}
        line = f"__TASK_EVENT__:{json.dumps(payload)}"
        result = svc.parse_event(line)
        assert result == payload

    def test_returns_none_for_non_event_line(self, tmp_path):
        """parse_event returns None for a regular log line."""
        svc = ExecutionService(tmp_path)
        assert svc.parse_event("INFO: Starting build...") is None

    def test_returns_none_for_empty_string(self, tmp_path):
        """parse_event returns None for empty input."""
        svc = ExecutionService(tmp_path)
        assert svc.parse_event("") is None

    def test_returns_none_for_malformed_json(self, tmp_path):
        """parse_event returns None when JSON after prefix is invalid."""
        svc = ExecutionService(tmp_path)
        assert svc.parse_event("__TASK_EVENT__:{not valid json}") is None

    def test_parses_nested_json(self, tmp_path):
        """parse_event handles nested JSON structures."""
        svc = ExecutionService(tmp_path)
        payload = {"type": "progress", "data": {"completed": [1, 2], "total": 5}}
        line = f"__TASK_EVENT__:{json.dumps(payload)}"
        assert svc.parse_event(line) == payload


class TestStopBuild:
    """Tests for ExecutionService.stop_build()."""

    def test_stop_unknown_spec_returns_error(self, tmp_path):
        """stop_build returns error dict for a spec not being tracked."""
        svc = ExecutionService(tmp_path)
        result = svc.stop_build("999-missing")
        assert result["success"] is False
        assert "No build found" in result["error"]

    def test_stop_already_finished_process(self, tmp_path):
        """stop_build returns error when process already exited."""
        svc = ExecutionService(tmp_path)
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        svc._processes["001-feat"] = mock_proc
        result = svc.stop_build("001-feat")
        assert result["success"] is False
        assert "already finished" in result["error"]

    def test_stop_running_process(self, tmp_path):
        """stop_build terminates a running process and returns success."""
        svc = ExecutionService(tmp_path)
        mock_proc = MagicMock()
        mock_proc.returncode = None  # still running
        svc._processes["001-feat"] = mock_proc
        result = svc.stop_build("001-feat")
        assert result["success"] is True
        mock_proc.terminate.assert_called_once()

    def test_stop_process_lookup_error(self, tmp_path):
        """stop_build handles ProcessLookupError (race condition)."""
        svc = ExecutionService(tmp_path)
        mock_proc = MagicMock()
        mock_proc.returncode = None
        mock_proc.terminate.side_effect = ProcessLookupError
        svc._processes["001-feat"] = mock_proc
        result = svc.stop_build("001-feat")
        assert result["success"] is False
        assert "already exited" in result["error"]


class TestGetProgress:
    """Tests for ExecutionService.get_progress()."""

    def test_progress_with_running_process(self, tmp_path):
        """get_progress reports running status and event info."""
        svc = ExecutionService(tmp_path)
        mock_proc = MagicMock()
        mock_proc.returncode = None
        svc._processes["001"] = mock_proc
        svc._logs["001"] = ["line1", "line2"]
        svc._events["001"] = [{"type": "start"}, {"type": "subtask_complete"}]

        result = svc.get_progress("001")
        assert result["running"] is True
        assert result["event_count"] == 2
        assert result["latest_event"] == {"type": "subtask_complete"}
        assert result["log_lines"] == 2

    def test_progress_with_finished_process(self, tmp_path):
        """get_progress reports finished status with exit code."""
        svc = ExecutionService(tmp_path)
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        svc._processes["001"] = mock_proc
        svc._events["001"] = []
        svc._logs["001"] = []

        result = svc.get_progress("001")
        assert result["running"] is False
        assert result["exit_code"] == 1

    def test_progress_falls_back_to_disk(self, tmp_path):
        """get_progress checks disk state when no process is tracked."""
        specs_dir = tmp_path / ".auto-claude" / "specs" / "001-feat"
        specs_dir.mkdir(parents=True)
        plan = {"subtasks": [{"status": "completed"}, {"status": "pending"}]}
        (specs_dir / "implementation_plan.json").write_text(json.dumps(plan))

        svc = ExecutionService(tmp_path)
        result = svc.get_progress("001-feat")
        assert result["running"] is False
        assert result["status"] == "building"
        assert result["subtasks_completed"] == 1
        assert result["subtasks_total"] == 2

    def test_progress_disk_no_plan(self, tmp_path):
        """get_progress returns no_plan when spec dir has no plan file."""
        specs_dir = tmp_path / ".auto-claude" / "specs" / "002-feat"
        specs_dir.mkdir(parents=True)

        svc = ExecutionService(tmp_path)
        result = svc.get_progress("002-feat")
        assert result["status"] == "no_plan"

    def test_progress_disk_spec_not_found(self, tmp_path):
        """get_progress returns error when spec directory doesn't exist."""
        (tmp_path / ".auto-claude" / "specs").mkdir(parents=True)
        svc = ExecutionService(tmp_path)
        result = svc.get_progress("999-missing")
        assert "error" in result

    def test_progress_disk_qa_approved(self, tmp_path):
        """get_progress identifies qa_approved status from plan."""
        specs_dir = tmp_path / ".auto-claude" / "specs" / "001-feat"
        specs_dir.mkdir(parents=True)
        plan = {
            "subtasks": [{"status": "completed"}],
            "qa_signoff": {"status": "approved"},
        }
        (specs_dir / "implementation_plan.json").write_text(json.dumps(plan))

        svc = ExecutionService(tmp_path)
        result = svc.get_progress("001-feat")
        assert result["status"] == "qa_approved"

    def test_progress_disk_qa_rejected(self, tmp_path):
        """get_progress identifies qa_rejected status."""
        specs_dir = tmp_path / ".auto-claude" / "specs" / "001-feat"
        specs_dir.mkdir(parents=True)
        plan = {
            "subtasks": [{"status": "completed"}],
            "qa_signoff": {"status": "rejected"},
        }
        (specs_dir / "implementation_plan.json").write_text(json.dumps(plan))

        svc = ExecutionService(tmp_path)
        result = svc.get_progress("001-feat")
        assert result["status"] == "qa_rejected"

    def test_progress_disk_build_complete(self, tmp_path):
        """get_progress shows build_complete when all subtasks done, no QA."""
        specs_dir = tmp_path / ".auto-claude" / "specs" / "001-feat"
        specs_dir.mkdir(parents=True)
        plan = {"subtasks": [{"status": "completed"}, {"status": "completed"}]}
        (specs_dir / "implementation_plan.json").write_text(json.dumps(plan))

        svc = ExecutionService(tmp_path)
        result = svc.get_progress("001-feat")
        assert result["status"] == "build_complete"

    def test_progress_disk_not_started(self, tmp_path):
        """get_progress shows not_started when no subtasks completed."""
        specs_dir = tmp_path / ".auto-claude" / "specs" / "001-feat"
        specs_dir.mkdir(parents=True)
        plan = {"subtasks": [{"status": "pending"}, {"status": "pending"}]}
        (specs_dir / "implementation_plan.json").write_text(json.dumps(plan))

        svc = ExecutionService(tmp_path)
        result = svc.get_progress("001-feat")
        assert result["status"] == "not_started"

    def test_progress_disk_invalid_plan_json(self, tmp_path):
        """get_progress handles corrupt plan file gracefully."""
        specs_dir = tmp_path / ".auto-claude" / "specs" / "001-feat"
        specs_dir.mkdir(parents=True)
        (specs_dir / "implementation_plan.json").write_text("not json!")

        svc = ExecutionService(tmp_path)
        result = svc.get_progress("001-feat")
        assert result["status"] == "error"


class TestGetLogs:
    """Tests for ExecutionService.get_logs()."""

    def test_get_logs_from_memory(self, tmp_path):
        """get_logs returns in-memory log lines."""
        svc = ExecutionService(tmp_path)
        svc._logs["001"] = [f"line-{i}" for i in range(100)]
        result = svc.get_logs("001", tail=10)
        assert result["total_lines"] == 100
        assert len(result["lines"]) == 10
        assert result["lines"][0] == "line-90"

    def test_get_logs_falls_back_to_disk(self, tmp_path):
        """get_logs reads disk logs when in-memory is empty."""
        specs_dir = tmp_path / ".auto-claude" / "specs" / "001-feat"
        specs_dir.mkdir(parents=True)
        log_lines = [f'{{"event": {i}}}' for i in range(20)]
        (specs_dir / "task_log.jsonl").write_text("\n".join(log_lines))

        svc = ExecutionService(tmp_path)
        result = svc.get_logs("001-feat", tail=5)
        assert result["total_lines"] == 20
        assert len(result["lines"]) == 5

    def test_get_logs_disk_no_log_file(self, tmp_path):
        """get_logs returns empty when no log file exists on disk."""
        specs_dir = tmp_path / ".auto-claude" / "specs" / "001-feat"
        specs_dir.mkdir(parents=True)

        svc = ExecutionService(tmp_path)
        result = svc.get_logs("001-feat")
        assert result["lines"] == []
        assert "No build logs" in result.get("message", "")

    def test_get_logs_disk_spec_not_found(self, tmp_path):
        """get_logs returns error when spec doesn't exist."""
        (tmp_path / ".auto-claude" / "specs").mkdir(parents=True)
        svc = ExecutionService(tmp_path)
        result = svc.get_logs("999-missing")
        assert "error" in result


class TestResolveSpecDir:
    """Tests for ExecutionService._resolve_spec_dir()."""

    def test_exact_match(self, tmp_path):
        """_resolve_spec_dir finds exact directory match."""
        specs_dir = tmp_path / "specs"
        target = specs_dir / "001-feature"
        target.mkdir(parents=True)

        svc = ExecutionService(tmp_path)
        assert svc._resolve_spec_dir(specs_dir, "001-feature") == target

    def test_prefix_match(self, tmp_path):
        """_resolve_spec_dir finds directory by prefix."""
        specs_dir = tmp_path / "specs"
        target = specs_dir / "001-my-feature"
        target.mkdir(parents=True)

        svc = ExecutionService(tmp_path)
        assert svc._resolve_spec_dir(specs_dir, "001") == target

    def test_no_match(self, tmp_path):
        """_resolve_spec_dir returns None when no directory matches."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()

        svc = ExecutionService(tmp_path)
        assert svc._resolve_spec_dir(specs_dir, "999") is None

    def test_no_specs_dir(self, tmp_path):
        """_resolve_spec_dir returns None when specs dir doesn't exist."""
        svc = ExecutionService(tmp_path)
        assert svc._resolve_spec_dir(tmp_path / "nonexistent", "001") is None


class TestStartBuild:
    """Tests for ExecutionService.start_build()."""

    @pytest.mark.asyncio
    async def test_start_build_raises_if_already_running(self, tmp_path):
        """start_build raises RuntimeError if build already in progress."""
        svc = ExecutionService(tmp_path)
        mock_proc = MagicMock()
        mock_proc.returncode = None  # still running
        svc._processes["001"] = mock_proc

        with pytest.raises(RuntimeError, match="already running"):
            await svc.start_build("001")

    @pytest.mark.asyncio
    async def test_start_build_raises_if_run_py_missing(self, tmp_path, monkeypatch):
        """start_build raises FileNotFoundError when run.py not found."""
        svc = ExecutionService(tmp_path)
        # Patch Path.exists to return False for the run.py check
        original_exists = Path.exists
        def fake_exists(self):
            if self.name == "run.py":
                return False
            return original_exists(self)
        monkeypatch.setattr(Path, "exists", fake_exists)

        with pytest.raises(FileNotFoundError, match="run.py not found"):
            await svc.start_build("001")

    @pytest.mark.asyncio
    async def test_start_build_allows_restart_after_completion(self, tmp_path, monkeypatch):
        """start_build allows restarting after a previous process completed."""
        svc = ExecutionService(tmp_path)
        old_proc = MagicMock()
        old_proc.returncode = 0  # already finished
        svc._processes["001"] = old_proc

        # Patch run.py to not exist so we get FileNotFoundError
        # (proving it got past the "already running" check)
        original_exists = Path.exists
        def fake_exists(self):
            if self.name == "run.py":
                return False
            return original_exists(self)
        monkeypatch.setattr(Path, "exists", fake_exists)

        with pytest.raises(FileNotFoundError, match="run.py not found"):
            await svc.start_build("001")
