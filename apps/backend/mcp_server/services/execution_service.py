"""
Execution Service
==================

Service layer for spawning and managing build processes.
Wraps the run.py subprocess and parses task events from stdout.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Matches core/task_event.py
TASK_EVENT_PREFIX = "__TASK_EVENT__:"


class ExecutionService:
    """Manages build execution as a subprocess of run.py."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self._processes: dict[str, asyncio.subprocess.Process] = {}
        self._logs: dict[str, list[str]] = {}
        self._events: dict[str, list[dict]] = {}

    async def start_build(
        self,
        spec_id: str,
        model: str = "sonnet",
        thinking_level: str = "medium",
    ) -> asyncio.subprocess.Process:
        """Spawn a build subprocess for the given spec.

        Args:
            spec_id: The spec folder name
            model: Model shorthand
            thinking_level: Thinking level

        Returns:
            The subprocess handle

        Raises:
            RuntimeError: If a build is already running for this spec
        """
        if spec_id in self._processes:
            proc = self._processes[spec_id]
            if proc.returncode is None:
                raise RuntimeError(
                    f"Build already running for spec '{spec_id}'. "
                    "Stop it first with build_stop()."
                )

        backend_dir = Path(__file__).parent.parent.parent  # apps/backend/
        run_py = backend_dir / "run.py"
        if not run_py.exists():
            raise FileNotFoundError(f"run.py not found at {run_py}")

        cmd = [
            sys.executable,
            str(run_py),
            "--spec",
            spec_id,
            "--project-dir",
            str(self.project_dir),
            "--model",
            model,
            "--thinking",
            thinking_level,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(backend_dir),
        )

        self._processes[spec_id] = proc
        self._logs[spec_id] = []
        self._events[spec_id] = []

        # Start background reader for stdout
        asyncio.create_task(self._read_output(spec_id, proc))

        return proc

    async def _read_output(
        self, spec_id: str, proc: asyncio.subprocess.Process
    ) -> None:
        """Read stdout from the build process, parsing task events.

        Args:
            spec_id: The spec being built
            proc: The subprocess to read from
        """
        if proc.stdout is None:
            return

        try:
            while True:
                line_bytes = await proc.stdout.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="replace").rstrip("\n")

                # Store the log line
                log_list = self._logs.get(spec_id)
                if log_list is not None:
                    log_list.append(line)
                    # Cap stored logs to prevent unbounded growth
                    if len(log_list) > 5000:
                        del log_list[:1000]

                # Parse task events
                event = self.parse_event(line)
                if event is not None:
                    events_list = self._events.get(spec_id)
                    if events_list is not None:
                        events_list.append(event)
        except Exception as e:
            logger.warning("Error reading build output for %s: %s", spec_id, e)

    def parse_event(self, line: str) -> dict | None:
        """Parse a task event line from build stdout.

        Args:
            line: A line of stdout output

        Returns:
            Parsed event dict or None if not an event line
        """
        if not line.startswith(TASK_EVENT_PREFIX):
            return None
        try:
            return json.loads(line[len(TASK_EVENT_PREFIX) :])
        except (json.JSONDecodeError, ValueError):
            return None

    def stop_build(self, spec_id: str) -> dict:
        """Stop a running build process.

        Args:
            spec_id: The spec being built

        Returns:
            Status dict
        """
        proc = self._processes.get(spec_id)
        if proc is None:
            return {"success": False, "error": f"No build found for spec '{spec_id}'"}

        if proc.returncode is not None:
            return {
                "success": False,
                "error": f"Build for '{spec_id}' already finished (exit code {proc.returncode})",
            }

        try:
            proc.terminate()
            return {"success": True, "message": f"Build for '{spec_id}' terminated"}
        except ProcessLookupError:
            return {"success": False, "error": "Process already exited"}

    def get_progress(self, spec_id: str) -> dict:
        """Get progress of a build by inspecting events and process state.

        Args:
            spec_id: The spec being built

        Returns:
            Dict with status, events, and process info
        """
        proc = self._processes.get(spec_id)
        events = self._events.get(spec_id, [])

        if proc is None:
            # Check if there's a completed implementation plan on disk
            return self._get_disk_progress(spec_id)

        is_running = proc.returncode is None
        latest_event = events[-1] if events else None

        return {
            "spec_id": spec_id,
            "running": is_running,
            "exit_code": proc.returncode,
            "event_count": len(events),
            "latest_event": latest_event,
            "log_lines": len(self._logs.get(spec_id, [])),
        }

    def get_logs(self, spec_id: str, tail: int = 50) -> dict:
        """Get recent build logs.

        Args:
            spec_id: The spec being built
            tail: Number of recent lines to return

        Returns:
            Dict with log lines
        """
        logs = self._logs.get(spec_id, [])
        if not logs:
            # Try to find logs on disk
            return self._get_disk_logs(spec_id, tail)

        return {
            "spec_id": spec_id,
            "total_lines": len(logs),
            "lines": logs[-tail:],
        }

    def _get_disk_progress(self, spec_id: str) -> dict:
        """Check on-disk state for build progress when no process is tracked.

        Args:
            spec_id: The spec folder name

        Returns:
            Progress dict from disk state
        """
        specs_dir = self.project_dir / ".auto-claude" / "specs"
        spec_dir = self._resolve_spec_dir(specs_dir, spec_id)
        if spec_dir is None:
            return {"error": f"Spec '{spec_id}' not found"}

        plan_file = spec_dir / "implementation_plan.json"
        if not plan_file.exists():
            return {
                "spec_id": spec_id,
                "running": False,
                "status": "no_plan",
                "message": "No implementation plan found. Create a spec first.",
            }

        try:
            with open(plan_file, encoding="utf-8") as f:
                plan = json.load(f)
        except (json.JSONDecodeError, OSError):
            return {
                "spec_id": spec_id,
                "running": False,
                "status": "error",
                "message": "Could not read implementation plan",
            }

        subtasks = plan.get("subtasks", [])
        completed = sum(1 for s in subtasks if s.get("status") == "completed")
        total = len(subtasks)

        qa_signoff = plan.get("qa_signoff")
        if qa_signoff and qa_signoff.get("status") == "approved":
            status = "qa_approved"
        elif qa_signoff and qa_signoff.get("status") == "rejected":
            status = "qa_rejected"
        elif completed == total and total > 0:
            status = "build_complete"
        elif completed > 0:
            status = "building"
        else:
            status = "not_started"

        return {
            "spec_id": spec_id,
            "running": False,
            "status": status,
            "subtasks_completed": completed,
            "subtasks_total": total,
            "qa_signoff": qa_signoff,
        }

    def _get_disk_logs(self, spec_id: str, tail: int) -> dict:
        """Try to find build logs on disk.

        Args:
            spec_id: The spec folder name
            tail: Number of lines to return

        Returns:
            Dict with log content
        """
        specs_dir = self.project_dir / ".auto-claude" / "specs"
        spec_dir = self._resolve_spec_dir(specs_dir, spec_id)
        if spec_dir is None:
            return {"error": f"Spec '{spec_id}' not found", "lines": []}

        # Check for task log file
        log_file = spec_dir / "task_log.jsonl"
        if not log_file.exists():
            return {
                "spec_id": spec_id,
                "lines": [],
                "message": "No build logs found",
            }

        try:
            lines = log_file.read_text(encoding="utf-8").strip().split("\n")
            return {
                "spec_id": spec_id,
                "total_lines": len(lines),
                "lines": lines[-tail:],
            }
        except OSError as e:
            return {"error": str(e), "lines": []}

    def _resolve_spec_dir(self, specs_dir: Path, spec_id: str) -> Path | None:
        """Resolve spec_id to directory with prefix matching."""
        exact = specs_dir / spec_id
        if exact.is_dir():
            return exact

        if specs_dir.is_dir():
            for item in specs_dir.iterdir():
                if item.is_dir() and item.name.startswith(spec_id):
                    return item
        return None
