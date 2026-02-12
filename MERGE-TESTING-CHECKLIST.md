# Merge Testing Checklist: Main -> Develop

Use this checklist to verify all features work after resolving the 33 merge conflicts.

## Build & Launch

- [ ] `npm install` in `apps/frontend` -- no errors
- [ ] `npm run build` -- TypeScript compiles with no errors
- [ ] `npm run dev` -- app launches without crashes
- [ ] No console errors on startup

---

## Critical -- Our Mod Features (conflict-affected)

### RDR System
- [ ] Start 2+ tasks on CV Project
- [ ] Wait for a task to get stuck -> RDR detects it and sends recovery message
- [ ] RDR does NOT flag actively running tasks (backlog false positive fix)
- [ ] RDR priority escalation works (P1 -> P3 after 3 attempts)
- **Files:** `rdr-handlers.ts`, `KanbanBoard.tsx`, `ipc-handlers/index.ts`

### Auto-Shutdown
- [ ] Enable auto-shutdown in settings
- [ ] Start tasks -> auto-shutdown detects when all reach human_review/done
- [ ] Shutdown monitor spawns correctly (no terminal popup on Windows)
- **Files:** `auto-shutdown-handlers.ts`, `index.ts`, `shutdown-monitor.ts`

### MCP Server
- [ ] Claude Code connects to Auto-Claude MCP server
- [ ] `list_tasks` returns correct task list
- [ ] `create_task` creates a task (appears on Kanban within 2-3s)
- [ ] `process_rdr_batch` restarts stuck tasks
- [ ] `recover_stuck_task` removes yellow outline and restarts
- **Files:** `mcp-server/index.ts`, `project-store.ts`

### Task Crash Recovery
- [ ] Kill a task agent process manually
- [ ] Crash is detected (exit code != 0)
- [ ] Auto-restart triggers if enabled
- [ ] Crash info persisted to `implementation_plan.json`
- **Files:** `agent-process.ts`, `agent-events-handlers.ts`

### Rate Limit Detection
- [ ] Rate limit crash is detected (distinct from normal errors)
- [ ] Rate-limited tasks show correct status
- **Files:** `rate-limit-detector.ts`, `agent-events-handlers.ts`

### File Watcher
- [ ] Create a new spec directory -> UI auto-refreshes within 2-3s
- [ ] Modify `implementation_plan.json` -> board updates automatically
- [ ] `start_requested` status triggers agent start
- **Files:** `file-watcher.ts`, `project-store.ts`

### Exit Reason Persistence
- [ ] Run a task to completion -> `exitReason: "success"` in plan
- [ ] Task crashes -> `exitReason: "error"` saved
- **Files:** `coder.py`, `planner.py`

---

## High -- Upstream Features (must not break)

### Queue Management
- [ ] Open queue settings modal from Kanban
- [ ] Set queue capacity limits
- [ ] Queue enforces capacity (no more than N concurrent tasks)
- **Files:** `KanbanBoard.tsx`

### Kanban Column Sizing
- [ ] Collapse/expand Kanban columns
- [ ] Resize column widths
- [ ] Column sizes persist across app restart
- **Files:** `KanbanBoard.tsx`, `project-store.ts`

### State Machine Transitions
- [ ] Task lifecycle: backlog -> planning -> in_progress -> ai_review -> human_review
- [ ] No stuck transitions or missing state updates
- **Files:** `agent-events-handlers.ts`, `execution-handlers.ts`

### Spell Check
- [ ] Spell check works in text inputs
- [ ] Language detection works
- **Files:** `index.ts`

### i18n / Language
- [ ] All UI labels render (no missing translation keys)
- [ ] Settings labels correct (logOrder, terminalFonts, autoShutdown, autoRefresh)
- [ ] No `translation:missing` warnings in console
- **Files:** `en/*.json`, `fr/*.json`

### Terminal Fonts
- [ ] Terminal font settings visible in Display Settings
- [ ] Font changes apply to terminal view
- **Files:** `DisplaySettings.tsx`, `settings.json`

### GitLab CLI (glab)
- [ ] If glab installed, it's detected in agent environment
- **Files:** `agent-process.ts`

### Screenshot Capture
- [ ] Screenshot handler registered and functional
- **Files:** `ipc-handlers/index.ts`

---

## Medium -- Shared Infrastructure (both sides touch)

### Project Store
- [ ] Tasks don't duplicate on Kanban board
- [ ] Worktree tasks correctly deduplicated with main tasks
- [ ] Atomic file writes (no corrupt JSON on crash)
- **Files:** `project-store.ts`

### Task Card UI
- [ ] Start/stop task from card
- [ ] Archive/unarchive task
- [ ] Drag task between columns
- [ ] Task progress displays correctly
- **Files:** `TaskCard.tsx`

### Sidebar Navigation
- [ ] All sidebar items render correctly
- [ ] Navigation works for all sections
- **Files:** `Sidebar.tsx`

### Worktree Operations
- [ ] Create worktree for a task
- [ ] Delete worktree
- [ ] Review worktree changes
- **Files:** `worktree-handlers.ts` (both task/ and terminal/)

### Settings UI
- [ ] All settings panels render
- [ ] Settings save correctly
- [ ] Display settings (fonts, themes) apply
- **Files:** `DisplaySettings.tsx`, `settings.ts`

---

## Notes

_Add any issues found during testing here:_

-
-
-
