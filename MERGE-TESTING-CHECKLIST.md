# Merge Testing Checklist: Main -> Develop

Use this checklist to verify all features work after resolving the 33 merge conflicts.

## Build & Launch

- [x] `npm install` in `apps/frontend` -- no errors
- [x] `npm run build` -- TypeScript compiles with no errors
- [x] `npm run dev` -- app launches without crashes
- [x] No console errors on startup

---

## Critical -- Our Mod Features (conflict-affected)

### RDR System
- [x] Start 2+ tasks on CV Project
- [x] Wait for a task to get stuck -> RDR detects it and sends recovery message
- [x] RDR does NOT flag actively running tasks (backlog false positive fix)
- [ ] RDR priority escalation works (P1 -> P3 after 3 attempts)
- **Files:** `rdr-handlers.ts`, `KanbanBoard.tsx`, `ipc-handlers/index.ts`

### Auto-Shutdown
- [x] Enable auto-shutdown in settings
- [x] Start tasks -> auto-shutdown detects when all reach human_review/done
- [x] Shutdown monitor spawns correctly (no terminal popup on Windows)
- **Files:** `auto-shutdown-handlers.ts`, `index.ts`, `shutdown-monitor.ts`

### MCP Server
- [x] Claude Code connects to Auto-Claude MCP server
- [x] `list_tasks` returns correct task list
- [x] `create_task` creates a task (appears on Kanban within 2-3s)
- [x] `process_rdr_batch` restarts stuck tasks
- [x] `recover_stuck_task` removes yellow outline and restarts
- **Files:** `mcp-server/index.ts`, `project-store.ts`

### Task Crash Recovery
- [x] Kill a task agent process manually
- [x] Crash is detected (exit code != 0)
- [ ] Auto-restart triggers if enabled
- [x] Crash info persisted to `implementation_plan.json`
- **Files:** `agent-process.ts`, `agent-events-handlers.ts`

### Rate Limit Detection
- [ ] Rate limit crash is detected (distinct from normal errors)
- [ ] Rate-limited tasks show correct status
- **Files:** `rate-limit-detector.ts`, `agent-events-handlers.ts`

### File Watcher
- [x] Create a new spec directory -> UI auto-refreshes within 2-3s
- [x] Modify `implementation_plan.json` -> board updates automatically
- [x] `start_requested` status triggers agent start
- **Files:** `file-watcher.ts`, `project-store.ts`

### Exit Reason Persistence
- [x] Run a task to completion -> `exitReason: "success"` in plan
- [x] Task crashes -> `exitReason: "error"` saved
- **Files:** `coder.py`, `planner.py`

---

## High -- Upstream Features (must not break)

### Queue Management
- [x] Open queue settings modal from Kanban
- [x] Set queue capacity limits
- [x] Queue enforces capacity (no more than N concurrent tasks)
- **Files:** `KanbanBoard.tsx`

### Kanban Column Sizing
- [ ] Collapse/expand Kanban columns
- [ ] Resize column widths
- [ ] Column sizes persist across app restart
- **Files:** `KanbanBoard.tsx`, `project-store.ts`

### State Machine Transitions
- [x] Task lifecycle: backlog -> planning -> in_progress -> ai_review -> human_review
- [x] No stuck transitions or missing state updates
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
- [x] Worktree tasks correctly deduplicated with main tasks
- [ ] Atomic file writes (no corrupt JSON on crash)
- **Files:** `project-store.ts`

### Task Card UI
- [x] Start/stop task from card
- [ ] Archive/unarchive task
- [x] Drag task between columns
- [x] Task progress displays correctly
- **Files:** `TaskCard.tsx`

### Sidebar Navigation
- [ ] All sidebar items render correctly
- [ ] Navigation works for all sections
- **Files:** `Sidebar.tsx`

### Worktree Operations
- [x] Create worktree for a task
- [x] Delete worktree
- [ ] Review worktree changes
- **Files:** `worktree-handlers.ts` (both task/ and terminal/)

### Settings UI
- [ ] All settings panels render
- [ ] Settings save correctly
- [ ] Display settings (fonts, themes) apply
- **Files:** `DisplaySettings.tsx`, `settings.ts`

---

## Notes

_Issues found and fixed during testing:_

- **WinError 206** (fixed `e41b64e7`): System prompt too long for Windows CreateProcessW limit. Externalized to `system_prompt_cache.md`.
- **MCP config crash** (fixed `efa37e6f`): `json.dump()` on SDK Server instance. Removed caching.
- **writeFileSync missing** (fixed `efa37e6f`): Import dropped in merge.
- **shouldSkipStuckCheck missing** (fixed `b292cee4`): Function dropped in merge.
- **XState MARK_DONE** (fixed `914698af`): Only accepted from 3 states, added to all non-terminal states.
- **MCP phase name mapping** (fixed `5a3e01e0`): `specCreation` not mapped to `spec` in `utils.ts`.
- **OutputMonitor false idle** (fixed `5a3e01e0`): Added `hasUnresolvedToolUse()` dynamic check.
- **processQueue merge regression** (fixed `d458073e`): Andy's fix lost in merge, restored + added settings change trigger.
