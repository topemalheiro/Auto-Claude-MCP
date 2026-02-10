# Auto Claude MCP development fork
[![License](https://img.shields.io/badge/license-AGPL--3.0-green?style=flat-square)](./agpl-3.0.txt)
[![Discord](https://img.shields.io/badge/Discord-Join%20Community-5865F2?style=flat-square&logo=discord&logoColor=white)](https://discord.gg/KCXaPBr4Dj)
[![YouTube](https://img.shields.io/badge/YouTube-Subscribe-FF0000?style=flat-square&logo=youtube&logoColor=white)](https://www.youtube.com/@AndreMikalsen)
[![CI](https://img.shields.io/github/actions/workflow/status/AndyMik90/Auto-Claude/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/AndyMik90/Auto-Claude/actions)
Fork of [Auto-Claude](https://github.com/AndyMik90/Auto-Claude) with a custom MCP system, automatic recovery, and infrastructure for autonomous overnight batch runs. **22,000+ lines** across 114 files.

> **Note:** The MCP server and all task management tools are standard MCP protocol and work with any MCP client. The RDR message **delivery pipeline** (how recovery prompts physically reach the LLM) currently targets: **Windows** (PowerShell + Win32 API for clipboard paste + keyboard simulation), **VS Code** (process-level window detection, not extension-specific), and **Claude Code** (JSONL transcript reading for busy-state). The delivery is blind "focus window, paste, enter" — it works when the target chat input is focused but is not tied to any extension API. Each layer can be swapped independently. Contributions for macOS/Linux, other VS Code forks (Cursor, etc.), or other LLM CLIs are welcome.

## What This Fork Adds

### MCP Server (Claude Code Integration)

A full MCP (Model Context Protocol) server that lets Claude Code interact with Auto-Claude directly. Create, manage, monitor, and recover tasks programmatically instead of through the UI.

**15 MCP Tools:**

| Tool                               | Purpose                                                        |
| ---------------------------------- | -------------------------------------------------------------- |
| `create_task`                    | Create a single task with full configuration                   |
| `list_tasks`                     | List all tasks, filterable by status                           |
| `get_task_status`                | Detailed status including phase/subtask progress               |
| `start_task`                     | Start task execution                                           |
| `start_batch`                    | Create and start multiple tasks at once                        |
| `wait_for_human_review`          | Monitor tasks, execute callback (e.g., shutdown) when complete |
| `get_tasks_needing_intervention` | Get all tasks needing recovery                                 |
| `get_task_error_details`         | Detailed error info with logs and QA reports                   |
| `recover_stuck_task`             | Recover tasks stuck in recovery mode                           |
| `submit_task_fix_request`        | Submit fix guidance for failing tasks                          |
| `get_task_logs`                  | Phase-specific logs (planning, coding, validation)             |
| `get_rdr_batches`                | Get pending recovery batches by problem type                   |
| `process_rdr_batch`              | Process a batch of tasks through the recovery system           |
| `trigger_auto_restart`           | Restart app with build on crash/error detection                |
| `test_force_recovery`            | Force tasks into recovery mode for testing                     |

### RDR System (Recover, Debug, Resend)

Automatic 6-priority recovery system that detects stuck/failed tasks and recovers them without manual intervention:

| Priority | Name              | When                     | Action                                          |
| -------- | ----------------- | ------------------------ | ----------------------------------------------- |
| P1       | Auto-CONTINUE     | Default (95% of cases)   | Sets `start_requested`, task self-recovers    |
| P2       | Auto-RECOVER      | Task in recovery mode    | Clears stuck state, restarts                    |
| P3       | Request Changes   | P1 failed 3+ times       | Writes detailed fix request with error analysis |
| P4       | Auto-fix JSON     | Corrupted plan files     | Rebuilds valid JSON structure                   |
| P5       | Manual Debug      | Pattern detection needed | Root cause investigation                        |
| P6       | Delete & Recreate | Last resort              | Clean rebuild or app restart                    |

Automatic escalation: P1 failures become P2, then P3 after 3 attempts. Attempt counters reset on app startup.

### Auto-Shutdown Monitor

Monitors all running tasks and automatically shuts down the computer when all tasks reach completion. Start 20 tasks, go to sleep, computer powers off when done.

- Status-based completion detection (`done` / `pr_created` / `human_review`)
- Worktree-aware (reads real progress, not stale main copies)
- Configurable via UI toggle or MCP `wait_for_human_review` tool

### Auto-Refresh (Real-Time UI Updates)

File watcher detects all plan status changes and pushes updates to the Kanban board in real-time (~1 second). No manual refresh needed when MCP tools modify task files.

### Task Chaining (CI/CD-Style Pipelines)

Chain tasks to auto-start sequentially on task creation with the status start_requested on tasks:

```
Task A (creates and starts) --> Task B (creates and starts) --> Task C (creates and starts)
```

Configurable per-task with optional human approval gates between steps.

### Output Monitor

Monitors Claude Code session state via JSONL transcripts. Distinguishes between user sessions and task agent sessions to prevent false busy-state detection.

### Watchdog Process

External watchdog that monitors Auto-Claude health, detects crashes, and auto-restart.

### Window Manager (Windows)

PowerShell-based message delivery that sends RDR recovery prompts directly to Claude Code's terminal via clipboard paste. Handles VS Code window detection, focus management, and busy-state checking.

### Additional Features

- **Crash Recovery** - Automatic recovery from app crashes with state preservation
- **Graceful Restart** - Clean restart with build when errors detected
- **Rate Limit Handling** - Detection and intelligent waiting for API rate limits
- **HuggingFace Integration** - OAuth flow and repository management
- **Worktree-Aware Architecture** - All subsystems prefer worktree data over stale main project data

---

**Autonomous multi-agent coding framework that plans, builds, and validates software for you. Check the original repo:** https://github.com/AndyMik90/Auto-Claude

![Auto Claude Kanban Board](.github/assets/Auto-Claude-Kanban.png)

---

## Requirements

- **Claude Pro/Max subscription** - [Get one here](https://claude.ai/upgrade)
- **Claude Code CLI** - `npm install -g @anthropic-ai/claude-code`
- **Git repository** - Your project must be initialized as a git repo

---

## Project Structure

```
Auto-Claude/
├── apps/
│   ├── backend/     # Python agents, specs, QA pipeline
│   └── frontend/    # Electron desktop application
├── guides/          # Additional documentation
├── tests/           # Test suite
└── scripts/         # Build utilities
```

---

## License

**AGPL-3.0** - GNU Affero General Public License v3.0

Auto Claude is free to use. If you modify and distribute it, or run it as a service, your code must also be open source under AGPL-3.0.

Commercial licensing available for closed-source use cases.

---
