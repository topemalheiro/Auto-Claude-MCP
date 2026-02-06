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

---

## Session 3b: Task Deduplication Fix (upstream PR #1710)

### Problem
Tasks still moved between boards on ANY cache invalidation (archive, create task, project switch). The root cause: task deduplication blindly preferred worktree version over main project. Worktrees contain stale data (e.g., `in_progress`) while main has the correct status (e.g., `done`).

### Source
Upstream fix: [AndyMik90/Auto-Claude PR #1710](https://github.com/AndyMik90/Auto-Claude/pull/1710) (merged), fixing [issue #1709](https://github.com/AndyMik90/Auto-Claude/issues/1709).

### Root Cause
```typescript
// OLD: Worktree always wins (WRONG - worktree may be stale)
if (!existing || task.location === 'worktree') {
  taskMap.set(task.id, task);
}
```

### Fixes Applied

| File | Change |
|------|--------|
| `apps/frontend/src/shared/constants/task.ts` | Added `TASK_STATUS_PRIORITY` constant mapping each status to a numeric priority (backlog=20 through done=100). Used as tiebreaker when both tasks are from same location. |
| `apps/frontend/src/main/project-store.ts` (deduplication, line 318) | Main project version now wins over worktree. Status priority only used as tiebreaker for same-location duplicates. Prevents stale worktree data from overriding correct user changes. |

---

## Session 4: Auto-Shutdown Task Count Mismatch (current, uncommitted)

### Problem
Auto-shutdown reported only 2 tasks remaining instead of ~8. The KanbanBoard showed 8 tasks in human_review, but auto-shutdown skipped 6 of them.

### Root Cause
`getActiveTaskIds()` and `countTasksByStatus()` used `calculateTaskProgress()` to skip tasks at 100% subtask completion. Tasks in `human_review` with all subtasks completed were treated as "done" even though they still need human action. The KanbanBoard uses `determineTaskStatusAndReason()` which respects the explicit status field.

### Fix Applied

| File | Change |
|------|--------|
| `apps/frontend/src/main/ipc-handlers/auto-shutdown-handlers.ts` | Changed `getActiveTaskIds()` and `countTasksByStatus()` to filter by **status** (`done`, `pr_created` = skip) instead of subtask progress (100% = skip). A task's completion is determined by reaching `done` status, not by subtask progress. |
