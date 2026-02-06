# RDR & Archive System Fixes - 2026-02-06

## Session 1: RDR Message Pipeline (commit 01020cb0)

### Problem
RDR (Recover, Debug, Resend) was not sending messages to Claude Code.

### Fixes Applied

| File | Fix |
|------|-----|
| `apps/frontend/src/main/claude-code/output-monitor.ts` | Added `processingRecheckTimer` (15s) to re-check state after entering PROCESSING. Without this, after Claude's last file write, no more file changes trigger `updateState()`, so state stays PROCESSING forever and idle event never fires. Also added `isUpdatingState` concurrency guard to prevent timer+watcher race condition. |
| `apps/frontend/src/main/platform/windows/window-manager.ts` | Only block PROCESSING in `isClaudeCodeBusy()`, allow AT_PROMPT. Also skip minimum idle time check when state is already IDLE (was returning ~0ms right after transitioning). |
| `apps/frontend/src/renderer/components/KanbanBoard.tsx` | Changed RDR_INTERVAL_MS from 60s to 30s. |

---

## Session 2: RDR Toggle Safety (commits 44bd859a, 490d3d12)

### Problem
Toggling RDR ON caused `autoRecoverAllTasks` to write `status: 'start_requested'` to ALL 22 tasks with zero filtering. Tasks moved chaotically between boards. Previously hidden because call used wrong API surface (`window.api.task` instead of `window.electronAPI`).

### Fixes Applied

| File | Fix |
|------|-----|
| `apps/frontend/src/renderer/components/KanbanBoard.tsx` | Removed entire `autoRecoverAllTasks` call from `handleRdrToggle`. Toggle now only enables/disables RDR monitoring - no automatic task modification. |
| `apps/frontend/src/main/ipc-handlers/rdr-handlers.ts` | Added 4-layer safety filtering to `autoRecoverAllTasks` handler: (1) NEVER_RECOVER status set (`done`, `pr_created`, `backlog`, `pending`), (2) archived task check, (3) rdrDisabled per-task check, (4) `determineInterventionType` filter. Also added `pending` to `determineInterventionType`'s early return to prevent false-positive on new tasks. |

---

## Session 3: Archive Button Task Movement (current, uncommitted)

### Problem
Clicking the archive button caused tasks to move between boards. The archive system itself is clean (only writes `archivedAt` to metadata), but cache invalidation exposed 3 pre-existing bugs.

### Root Causes

1. **`start_requested` not in statusMap** - The previous `autoRecoverAllTasks` bug left residual `start_requested` status in many tasks' `implementation_plan.json`. This status wasn't mapped in `determineTaskStatusAndReason()`, so on cache reload tasks fell through to subtask calculation and got random board assignments.

2. **`updateTaskStatus()` auto-unarchived** - Any code path calling `updateTaskStatus()` silently cleared `archivedAt` from metadata, causing archived tasks to reappear on the board.

3. **File watcher processed archived tasks** - When detecting `start_requested` in a plan file, the file watcher didn't check if the task was archived before calling `updateTaskStatus()` and emitting start events.

### Fixes Applied

| File | Change |
|------|--------|
| `apps/frontend/src/main/project-store.ts` (line 634) | Added `'start_requested': 'backlog'` to `statusMap` in `determineTaskStatusAndReason()`. Prevents tasks with residual `start_requested` from falling through to subtask calculation. |
| `apps/frontend/src/main/project-store.ts` (lines 395-412 removed) | Removed auto-unarchive block from `updateTaskStatus()`. Unarchiving now only happens via explicit `unarchiveTasks()` call or drag-drop (which already calls `TASK_UNARCHIVE` IPC separately). |
| `apps/frontend/src/main/file-watcher.ts` (add handler, line 240) | Added archived task guard before processing `start_requested` in the `add` handler. Skips archived tasks entirely. |
| `apps/frontend/src/main/file-watcher.ts` (change handler, line 296) | Added same archived task guard in the `change` handler. Prevents archived tasks from being auto-started by file system events. |

### Diff Summary

```
 apps/frontend/src/main/file-watcher.ts  | 18 +++++++++++++++---
 apps/frontend/src/main/project-store.ts | 20 +-------------------
 2 files changed, 17 insertions(+), 21 deletions(-)
```
