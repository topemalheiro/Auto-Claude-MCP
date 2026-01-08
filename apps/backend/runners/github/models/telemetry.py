"""
PR Review Loop Telemetry
========================

Telemetry dataclass for collecting and persisting PR review loop iteration metrics.
Provides file-based persistence for observability and debugging.

Example:
    # Create telemetry
    telemetry = PRReviewLoopTelemetry(
        pr_number=123,
        repo="owner/repo",
        correlation_id="abc123",
    )

    # Record iteration metrics
    telemetry.start_iteration()
    telemetry.record_check_metrics(ci_checks_count=5, ci_passed=4, bot_responses=2)
    telemetry.record_fix_metrics(findings_count=3, fixes_applied=2, fixes_failed=1)
    telemetry.complete_iteration()

    # Save to disk
    telemetry.save(github_dir)

    # Load existing telemetry
    loaded = PRReviewLoopTelemetry.load(github_dir, 123)
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class CheckMetrics:
    """Metrics for CI and external bot checks during an iteration."""

    # CI check metrics
    ci_checks_count: int = 0
    ci_checks_passed: int = 0
    ci_checks_failed: int = 0
    ci_checks_pending: int = 0
    ci_wait_duration_seconds: float = 0.0

    # External bot metrics
    bot_responses_count: int = 0
    bot_responses_verified: int = 0
    bot_findings_count: int = 0
    bot_wait_duration_seconds: float = 0.0

    # Circuit breaker metrics
    circuit_breaker_trips: int = 0
    api_calls_count: int = 0
    api_errors_count: int = 0

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "ci_checks_count": self.ci_checks_count,
            "ci_checks_passed": self.ci_checks_passed,
            "ci_checks_failed": self.ci_checks_failed,
            "ci_checks_pending": self.ci_checks_pending,
            "ci_wait_duration_seconds": self.ci_wait_duration_seconds,
            "bot_responses_count": self.bot_responses_count,
            "bot_responses_verified": self.bot_responses_verified,
            "bot_findings_count": self.bot_findings_count,
            "bot_wait_duration_seconds": self.bot_wait_duration_seconds,
            "circuit_breaker_trips": self.circuit_breaker_trips,
            "api_calls_count": self.api_calls_count,
            "api_errors_count": self.api_errors_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CheckMetrics:
        """Deserialize from dictionary."""
        return cls(
            ci_checks_count=data.get("ci_checks_count", 0),
            ci_checks_passed=data.get("ci_checks_passed", 0),
            ci_checks_failed=data.get("ci_checks_failed", 0),
            ci_checks_pending=data.get("ci_checks_pending", 0),
            ci_wait_duration_seconds=data.get("ci_wait_duration_seconds", 0.0),
            bot_responses_count=data.get("bot_responses_count", 0),
            bot_responses_verified=data.get("bot_responses_verified", 0),
            bot_findings_count=data.get("bot_findings_count", 0),
            bot_wait_duration_seconds=data.get("bot_wait_duration_seconds", 0.0),
            circuit_breaker_trips=data.get("circuit_breaker_trips", 0),
            api_calls_count=data.get("api_calls_count", 0),
            api_errors_count=data.get("api_errors_count", 0),
        )


@dataclass
class FixMetrics:
    """Metrics for fix application during an iteration."""

    # Finding metrics
    findings_count: int = 0
    findings_from_ci: int = 0
    findings_from_bots: int = 0
    findings_trusted: int = 0

    # Fix application metrics
    fixes_attempted: int = 0
    fixes_applied: int = 0
    fixes_failed: int = 0
    fixes_skipped: int = 0

    # File operation metrics
    files_modified: int = 0
    files_blocked: int = 0  # Files outside PR scope

    # Timing metrics
    fix_duration_seconds: float = 0.0

    # Validation metrics
    syntax_validations: int = 0
    syntax_failures: int = 0

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "findings_count": self.findings_count,
            "findings_from_ci": self.findings_from_ci,
            "findings_from_bots": self.findings_from_bots,
            "findings_trusted": self.findings_trusted,
            "fixes_attempted": self.fixes_attempted,
            "fixes_applied": self.fixes_applied,
            "fixes_failed": self.fixes_failed,
            "fixes_skipped": self.fixes_skipped,
            "files_modified": self.files_modified,
            "files_blocked": self.files_blocked,
            "fix_duration_seconds": self.fix_duration_seconds,
            "syntax_validations": self.syntax_validations,
            "syntax_failures": self.syntax_failures,
        }

    @classmethod
    def from_dict(cls, data: dict) -> FixMetrics:
        """Deserialize from dictionary."""
        return cls(
            findings_count=data.get("findings_count", 0),
            findings_from_ci=data.get("findings_from_ci", 0),
            findings_from_bots=data.get("findings_from_bots", 0),
            findings_trusted=data.get("findings_trusted", 0),
            fixes_attempted=data.get("fixes_attempted", 0),
            fixes_applied=data.get("fixes_applied", 0),
            fixes_failed=data.get("fixes_failed", 0),
            fixes_skipped=data.get("fixes_skipped", 0),
            files_modified=data.get("files_modified", 0),
            files_blocked=data.get("files_blocked", 0),
            fix_duration_seconds=data.get("fix_duration_seconds", 0.0),
            syntax_validations=data.get("syntax_validations", 0),
            syntax_failures=data.get("syntax_failures", 0),
        )


@dataclass
class IterationMetrics:
    """Metrics for a single iteration of the PR review loop."""

    iteration_number: int
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None
    duration_seconds: float = 0.0

    # Status
    status: str = "in_progress"  # in_progress, completed, failed, cancelled
    outcome: str | None = None  # checks_passed, fixes_applied, no_findings, error

    # Sub-metrics
    check_metrics: CheckMetrics = field(default_factory=CheckMetrics)
    fix_metrics: FixMetrics = field(default_factory=FixMetrics)

    # Head SHA tracking
    start_sha: str | None = None
    end_sha: str | None = None
    sha_changed: bool = False  # Force push detected

    # Error tracking
    error_message: str | None = None

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "iteration_number": self.iteration_number,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "outcome": self.outcome,
            "check_metrics": self.check_metrics.to_dict(),
            "fix_metrics": self.fix_metrics.to_dict(),
            "start_sha": self.start_sha,
            "end_sha": self.end_sha,
            "sha_changed": self.sha_changed,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> IterationMetrics:
        """Deserialize from dictionary."""
        return cls(
            iteration_number=data["iteration_number"],
            started_at=data.get("started_at", datetime.now(timezone.utc).isoformat()),
            completed_at=data.get("completed_at"),
            duration_seconds=data.get("duration_seconds", 0.0),
            status=data.get("status", "in_progress"),
            outcome=data.get("outcome"),
            check_metrics=CheckMetrics.from_dict(data.get("check_metrics", {})),
            fix_metrics=FixMetrics.from_dict(data.get("fix_metrics", {})),
            start_sha=data.get("start_sha"),
            end_sha=data.get("end_sha"),
            sha_changed=data.get("sha_changed", False),
            error_message=data.get("error_message"),
        )


@dataclass
class PRReviewLoopTelemetry:
    """
    Telemetry data for PR review loop execution.

    Collects iteration metrics, timing information, and error tracking
    for observability and debugging. Supports file-based persistence
    for crash recovery and post-mortem analysis.

    Attributes:
        pr_number: The PR being reviewed
        repo: Repository in owner/repo format
        correlation_id: Unique ID for log correlation
        started_at: When the review loop started
        completed_at: When the review loop completed (if finished)
        status: Current status (pending, running, completed, failed, cancelled)
        iterations: List of iteration metrics
        total_duration_seconds: Total elapsed time
        outcome: Final outcome of the review loop
    """

    # PR identification
    pr_number: int
    repo: str
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Timestamps
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Status tracking
    status: str = "pending"  # pending, running, completed, failed, cancelled
    outcome: str | None = None  # ready_to_merge, max_iterations, ci_failed, cancelled, error

    # Configuration snapshot
    max_iterations: int = 5
    ci_timeout_seconds: float = 1800.0
    bot_timeout_seconds: float = 900.0

    # Iteration metrics
    iterations: list[IterationMetrics] = field(default_factory=list)
    current_iteration: int = 0

    # Aggregate metrics
    total_duration_seconds: float = 0.0
    total_ci_checks: int = 0
    total_bot_responses: int = 0
    total_findings: int = 0
    total_fixes_applied: int = 0
    total_fixes_failed: int = 0
    total_api_calls: int = 0
    total_api_errors: int = 0

    # Error tracking
    error_count: int = 0
    last_error: str | None = None

    # Triggered by
    triggered_by: str | None = None

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def start_iteration(self, head_sha: str | None = None) -> IterationMetrics:
        """
        Start a new iteration and return its metrics object.

        Args:
            head_sha: Current HEAD SHA of the PR

        Returns:
            IterationMetrics for the new iteration
        """
        self.current_iteration += 1
        self.status = "running"

        iteration = IterationMetrics(
            iteration_number=self.current_iteration,
            start_sha=head_sha,
        )
        self.iterations.append(iteration)
        self.update_timestamp()

        return iteration

    def get_current_iteration(self) -> IterationMetrics | None:
        """Get the current iteration metrics, if any."""
        if self.iterations:
            return self.iterations[-1]
        return None

    def record_check_metrics(
        self,
        ci_checks_count: int = 0,
        ci_passed: int = 0,
        ci_failed: int = 0,
        bot_responses: int = 0,
        bot_verified: int = 0,
        bot_findings: int = 0,
        ci_wait_duration: float = 0.0,
        bot_wait_duration: float = 0.0,
        api_calls: int = 0,
        api_errors: int = 0,
        circuit_breaker_trips: int = 0,
    ) -> None:
        """
        Record check metrics for the current iteration.

        Args:
            ci_checks_count: Total number of CI checks
            ci_passed: Number of passed CI checks
            ci_failed: Number of failed CI checks
            bot_responses: Number of bot responses received
            bot_verified: Number of verified bot responses
            bot_findings: Number of findings from bots
            ci_wait_duration: Time spent waiting for CI
            bot_wait_duration: Time spent waiting for bots
            api_calls: Number of API calls made
            api_errors: Number of API errors
            circuit_breaker_trips: Number of circuit breaker trips
        """
        current = self.get_current_iteration()
        if current is None:
            return

        current.check_metrics.ci_checks_count = ci_checks_count
        current.check_metrics.ci_checks_passed = ci_passed
        current.check_metrics.ci_checks_failed = ci_failed
        current.check_metrics.ci_checks_pending = ci_checks_count - ci_passed - ci_failed
        current.check_metrics.ci_wait_duration_seconds = ci_wait_duration
        current.check_metrics.bot_responses_count = bot_responses
        current.check_metrics.bot_responses_verified = bot_verified
        current.check_metrics.bot_findings_count = bot_findings
        current.check_metrics.bot_wait_duration_seconds = bot_wait_duration
        current.check_metrics.api_calls_count = api_calls
        current.check_metrics.api_errors_count = api_errors
        current.check_metrics.circuit_breaker_trips = circuit_breaker_trips

        # Update totals
        self.total_ci_checks += ci_checks_count
        self.total_bot_responses += bot_responses
        self.total_api_calls += api_calls
        self.total_api_errors += api_errors

        self.update_timestamp()

    def record_fix_metrics(
        self,
        findings_count: int = 0,
        findings_from_ci: int = 0,
        findings_from_bots: int = 0,
        findings_trusted: int = 0,
        fixes_attempted: int = 0,
        fixes_applied: int = 0,
        fixes_failed: int = 0,
        fixes_skipped: int = 0,
        files_modified: int = 0,
        files_blocked: int = 0,
        fix_duration: float = 0.0,
        syntax_validations: int = 0,
        syntax_failures: int = 0,
    ) -> None:
        """
        Record fix metrics for the current iteration.

        Args:
            findings_count: Total number of findings
            findings_from_ci: Findings from CI failures
            findings_from_bots: Findings from external bots
            findings_trusted: Number of trusted findings
            fixes_attempted: Number of fix attempts
            fixes_applied: Successfully applied fixes
            fixes_failed: Failed fix attempts
            fixes_skipped: Skipped fixes
            files_modified: Number of modified files
            files_blocked: Number of blocked files (outside PR scope)
            fix_duration: Time spent fixing
            syntax_validations: Number of syntax validations
            syntax_failures: Number of syntax validation failures
        """
        current = self.get_current_iteration()
        if current is None:
            return

        current.fix_metrics.findings_count = findings_count
        current.fix_metrics.findings_from_ci = findings_from_ci
        current.fix_metrics.findings_from_bots = findings_from_bots
        current.fix_metrics.findings_trusted = findings_trusted
        current.fix_metrics.fixes_attempted = fixes_attempted
        current.fix_metrics.fixes_applied = fixes_applied
        current.fix_metrics.fixes_failed = fixes_failed
        current.fix_metrics.fixes_skipped = fixes_skipped
        current.fix_metrics.files_modified = files_modified
        current.fix_metrics.files_blocked = files_blocked
        current.fix_metrics.fix_duration_seconds = fix_duration
        current.fix_metrics.syntax_validations = syntax_validations
        current.fix_metrics.syntax_failures = syntax_failures

        # Update totals
        self.total_findings += findings_count
        self.total_fixes_applied += fixes_applied
        self.total_fixes_failed += fixes_failed

        self.update_timestamp()

    def complete_iteration(
        self,
        outcome: str = "completed",
        end_sha: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """
        Complete the current iteration.

        Args:
            outcome: Outcome of the iteration (checks_passed, fixes_applied, no_findings, error)
            end_sha: Final HEAD SHA after the iteration
            error_message: Error message if iteration failed
        """
        current = self.get_current_iteration()
        if current is None:
            return

        now = datetime.now(timezone.utc).isoformat()
        current.completed_at = now
        current.status = "failed" if error_message else "completed"
        current.outcome = outcome
        current.end_sha = end_sha
        current.error_message = error_message

        # Check for SHA change (force push)
        if current.start_sha and end_sha and current.start_sha != end_sha:
            current.sha_changed = True

        # Calculate duration
        try:
            start = datetime.fromisoformat(current.started_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(now.replace("Z", "+00:00"))
            current.duration_seconds = (end - start).total_seconds()
        except (ValueError, TypeError):
            pass

        if error_message:
            self.error_count += 1
            self.last_error = error_message

        self.update_timestamp()

    def complete(
        self,
        outcome: str,
        error_message: str | None = None,
    ) -> None:
        """
        Complete the entire review loop.

        Args:
            outcome: Final outcome (ready_to_merge, max_iterations, ci_failed, cancelled, error)
            error_message: Error message if loop failed
        """
        now = datetime.now(timezone.utc).isoformat()
        self.completed_at = now
        self.outcome = outcome

        if error_message:
            self.status = "failed"
            self.last_error = error_message
            self.error_count += 1
        elif outcome == "cancelled":
            self.status = "cancelled"
        else:
            self.status = "completed"

        # Calculate total duration
        try:
            start = datetime.fromisoformat(self.started_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(now.replace("Z", "+00:00"))
            self.total_duration_seconds = (end - start).total_seconds()
        except (ValueError, TypeError):
            pass

        self.update_timestamp()

    def to_dict(self) -> dict:
        """Serialize telemetry to dictionary for JSON storage."""
        return {
            # PR identification
            "pr_number": self.pr_number,
            "repo": self.repo,
            "correlation_id": self.correlation_id,
            # Timestamps
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "updated_at": self.updated_at,
            # Status
            "status": self.status,
            "outcome": self.outcome,
            # Configuration
            "max_iterations": self.max_iterations,
            "ci_timeout_seconds": self.ci_timeout_seconds,
            "bot_timeout_seconds": self.bot_timeout_seconds,
            # Iterations
            "iterations": [i.to_dict() for i in self.iterations],
            "current_iteration": self.current_iteration,
            # Aggregates
            "total_duration_seconds": self.total_duration_seconds,
            "total_ci_checks": self.total_ci_checks,
            "total_bot_responses": self.total_bot_responses,
            "total_findings": self.total_findings,
            "total_fixes_applied": self.total_fixes_applied,
            "total_fixes_failed": self.total_fixes_failed,
            "total_api_calls": self.total_api_calls,
            "total_api_errors": self.total_api_errors,
            # Errors
            "error_count": self.error_count,
            "last_error": self.last_error,
            # Trigger info
            "triggered_by": self.triggered_by,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PRReviewLoopTelemetry:
        """Deserialize telemetry from dictionary."""
        return cls(
            # PR identification
            pr_number=data["pr_number"],
            repo=data["repo"],
            correlation_id=data.get("correlation_id", str(uuid.uuid4())),
            # Timestamps
            started_at=data.get("started_at", datetime.now(timezone.utc).isoformat()),
            completed_at=data.get("completed_at"),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
            # Status
            status=data.get("status", "pending"),
            outcome=data.get("outcome"),
            # Configuration
            max_iterations=data.get("max_iterations", 5),
            ci_timeout_seconds=data.get("ci_timeout_seconds", 1800.0),
            bot_timeout_seconds=data.get("bot_timeout_seconds", 900.0),
            # Iterations
            iterations=[
                IterationMetrics.from_dict(i) for i in data.get("iterations", [])
            ],
            current_iteration=data.get("current_iteration", 0),
            # Aggregates
            total_duration_seconds=data.get("total_duration_seconds", 0.0),
            total_ci_checks=data.get("total_ci_checks", 0),
            total_bot_responses=data.get("total_bot_responses", 0),
            total_findings=data.get("total_findings", 0),
            total_fixes_applied=data.get("total_fixes_applied", 0),
            total_fixes_failed=data.get("total_fixes_failed", 0),
            total_api_calls=data.get("total_api_calls", 0),
            total_api_errors=data.get("total_api_errors", 0),
            # Errors
            error_count=data.get("error_count", 0),
            last_error=data.get("last_error"),
            # Trigger info
            triggered_by=data.get("triggered_by"),
        )

    def save(self, github_dir: Path) -> None:
        """
        Save telemetry to disk.

        Telemetry is saved to .auto-claude/github/telemetry/pr_{number}.json

        Args:
            github_dir: Path to the github state directory
        """
        telemetry_dir = Path(github_dir) / "telemetry"
        telemetry_dir.mkdir(parents=True, exist_ok=True)

        telemetry_file = telemetry_dir / f"pr_{self.pr_number}.json"

        # Update timestamp before saving
        self.update_timestamp()

        # Write to file
        with open(telemetry_file, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, github_dir: Path, pr_number: int) -> PRReviewLoopTelemetry | None:
        """
        Load telemetry from disk.

        Args:
            github_dir: Path to the github state directory
            pr_number: PR number to load telemetry for

        Returns:
            PRReviewLoopTelemetry instance or None if not found
        """
        telemetry_file = Path(github_dir) / "telemetry" / f"pr_{pr_number}.json"

        if not telemetry_file.exists():
            return None

        with open(telemetry_file) as f:
            data = json.load(f)

        return cls.from_dict(data)

    @classmethod
    def load_all(cls, github_dir: Path) -> list[PRReviewLoopTelemetry]:
        """
        Load all telemetry records from disk.

        Args:
            github_dir: Path to the github state directory

        Returns:
            List of PRReviewLoopTelemetry instances
        """
        telemetry_dir = Path(github_dir) / "telemetry"

        if not telemetry_dir.exists():
            return []

        records = []
        for telemetry_file in telemetry_dir.glob("pr_*.json"):
            try:
                with open(telemetry_file) as f:
                    data = json.load(f)
                records.append(cls.from_dict(data))
            except (json.JSONDecodeError, KeyError):
                # Skip invalid files
                continue

        return records

    def get_summary(self) -> dict[str, Any]:
        """
        Get a summary of the telemetry for logging/display.

        Returns:
            Dictionary with key metrics
        """
        return {
            "pr_number": self.pr_number,
            "repo": self.repo,
            "status": self.status,
            "outcome": self.outcome,
            "iterations_completed": self.current_iteration,
            "total_duration_seconds": round(self.total_duration_seconds, 2),
            "total_fixes_applied": self.total_fixes_applied,
            "total_fixes_failed": self.total_fixes_failed,
            "total_api_calls": self.total_api_calls,
            "error_count": self.error_count,
        }
