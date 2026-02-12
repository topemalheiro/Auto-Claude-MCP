# Auto-Claude MCP Skill

Use this skill when the user wants to:
- Queue coding tasks for Auto-Claude to implement
- Run multiple tasks overnight with shutdown-on-complete
- Create tasks with specific model/thinking configurations
- Delegate implementation work to autonomous agents

## When to Use Auto-Claude vs Direct Coding

| Scenario | Use Auto-Claude | Code Directly |
|----------|-----------------|---------------|
| Complex multi-file feature | ✅ Yes | |
| Quick typo fix | | ✅ Yes |
| User says "overnight" / "batch" | ✅ Yes | |
| User wants to review before coding | ✅ Yes | |
| Needs isolated git worktree | ✅ Yes | |
| Simple single-file change | | ✅ Yes |

## Agent Profiles - When to Use Each

| Profile | Thinking Budget | Best For |
|---------|-----------------|----------|
| **auto** | Smart allocation (ultrathink→high→low→low) | Default choice, most tasks |
| **complex** | Maximum everywhere (63,999 tokens/phase) | Multi-step features, deep analysis, architectural changes |
| **balanced** | Medium everywhere (4,096 tokens/phase) | Good speed/quality, overnight batches |
| **quick** | Low everywhere (1,024 tokens/phase) | Simple fixes, fast iterations, typos |
| **custom** | User-specified | When user knows exactly what they want |

### Profile Selection Logic

1. User says **"simple"**, **"quick"**, **"fast"**, **"typo"** → `quick`
2. User says **"complex"**, **"deep"**, **"architectural"**, **"multi-step"** → `complex`
3. User says **"overnight"**, **"batch"**, **"multiple tasks"** → `balanced` (cost-efficient)
4. User specifies **models or thinking levels** → `custom`
5. **No preference** → `auto` (smart defaults)

## MCP Tools Reference

### create_task - Single Task

```json
{
  "projectId": "uuid-from-auto-claude",
  "description": "Detailed task description...",
  "title": "Optional - auto-generated if empty",
  "options": {
    "model": "opus",
    "requireReviewBeforeCoding": false,
    "baseBranch": "MCD",
    "referencedFiles": ["src/relevant-file.ts"],
    "category": "feature",
    "complexity": "medium",
    "priority": "high"
  }
}
```

### list_tasks - List Project Tasks

```json
{
  "projectId": "uuid",
  "status": "backlog"
}
```

Returns: Array of task summaries with taskId, title, description, status, createdAt.

### start_task - Start a Single Task

```json
{
  "projectId": "uuid",
  "taskId": "001-feature-name",
  "options": {
    "model": "opus",
    "baseBranch": "main"
  }
}
```

### get_task_status - Check Task Progress

```json
{
  "projectId": "uuid",
  "taskId": "001-feature-name"
}
```

Returns: taskId, title, status, phase, progress, subtaskCount, completedSubtasks, error, reviewReason.

### start_batch - Multiple Tasks

```json
{
  "projectId": "uuid",
  "tasks": [
    { "description": "First task...", "options": { "priority": "high" } },
    { "description": "Second task..." },
    { "description": "Third task...", "options": { "category": "bug_fix" } }
  ],
  "options": {
    "model": "sonnet",
    "requireReviewBeforeCoding": false
  },
  "startImmediately": true
}
```

### wait_for_human_review - With Shutdown

```json
{
  "projectId": "uuid",
  "taskIds": ["001-feature", "002-bugfix", "003-refactor"],
  "onComplete": {
    "command": "shutdown",
    "args": ["/s", "/t", "120"],
    "delaySeconds": 60
  },
  "pollIntervalMs": 30000
}
```

## Custom Phase Configuration

For fine-grained control, specify per-phase models and thinking:

```json
{
  "options": {
    "phaseModels": {
      "specCreation": "opus",
      "planning": "opus",
      "coding": "sonnet",
      "qaReview": "haiku"
    },
    "phaseThinking": {
      "specCreation": 63999,
      "planning": 16384,
      "coding": 4096,
      "qaReview": 1024
    }
  }
}
```

### Thinking Token Levels

| Level | Tokens | Use Case |
|-------|--------|----------|
| None | 0 | Fast, no extended thinking |
| Low | 1,024 | Quick edits, simple tasks |
| Medium | 4,096 | Balanced speed/quality |
| High | 16,384 | Complex reasoning |
| Ultra Think | 63,999 | Maximum depth, architectural decisions |

## Task Status Flow

```
backlog → in_progress → ai_review → human_review → pr_created → done
                            ↓
                         error
```

- **backlog** - Task created, not started
- **in_progress** - Agent actively working
- **ai_review** - QA agent reviewing
- **human_review** - Ready for human review (code committed to worktree)
- **pr_created** - PR has been created
- **done** - Merged and complete
- **error** - Something went wrong

## RDR (Recover, Debug, Resend) Troubleshooting

**CRITICAL: Auto-Claude must automatically recover from errors and resume stuck tasks.**

### RDR 5-Tier Priority System

**Priority 1 (95%): Task Recovery - Auto-Resume**
- Tasks with incomplete subtasks stuck in `plan_review` or `human_review`
- **Action**: Change status to `"start_requested"` in implementation_plan.json
- File watcher auto-detects within 2-3 seconds
- **No MCP tools needed** - just file writes to trigger resume

**Priority 2 (4%): Debug & Fix**
- Tasks showing errors with logs available
- **Action**: Analyze error logs, fix root cause, trigger resume

**Priority 3 (<1%): Auto-fix JSON Errors**
- Empty or malformed `implementation_plan.json` files
- **Action**: Create minimal valid JSON:
  ```json
  {
    "feature": "Auto-recovery task",
    "description": "Task recovered by RDR system",
    "created_at": "2026-01-31T00:00:00Z",
    "updated_at": "2026-01-31T00:00:00Z",
    "status": "start_requested",
    "phases": []
  }
  ```

**Priority 4 (RARE): Manual Edits**
- Only when auto-fix fails repeatedly

**Priority 5 (LAST RESORT): Delete & Recreate**
- Only for completely corrupted worktrees

### Common RDR Scenarios

**Scenario 1: Tasks stuck in "plan_review" with incomplete subtasks**
```bash
# Main project
sed -i 's/"status": "plan_review"/"status": "start_requested"/' \
  "/path/to/project/.auto-claude/specs/TASK-ID/implementation_plan.json"

# Worktree (CRITICAL: Auto-Claude prefers worktree versions!)
sed -i 's/"status": "plan_review"/"status": "start_requested"/' \
  "/path/to/project/.auto-claude/worktrees/tasks/TASK-ID/.auto-claude/specs/TASK-ID/implementation_plan.json"
```

**Scenario 2: JSON Parse Errors (empty/malformed files)**
```bash
# Fix main version
cat > "/path/to/project/.auto-claude/specs/TASK-ID/implementation_plan.json" << 'EOF'
{
  "feature": "Auto-recovery task",
  "description": "Task recovered by RDR system",
  "created_at": "2026-01-31T00:00:00Z",
  "updated_at": "2026-01-31T00:00:00Z",
  "status": "start_requested",
  "phases": []
}
EOF

# Fix worktree version (if exists)
if [ -d "/path/to/project/.auto-claude/worktrees/tasks/TASK-ID" ]; then
  cat > "/path/to/project/.auto-claude/worktrees/tasks/TASK-ID/.auto-claude/specs/TASK-ID/implementation_plan.json" << 'EOF'
{
  "feature": "Auto-recovery task",
  "description": "Task recovered by RDR system",
  "created_at": "2026-01-31T00:00:00Z",
  "updated_at": "2026-01-31T00:00:00Z",
  "status": "start_requested",
  "phases": []
}
EOF
fi
```

**Scenario 3: Tasks showing "Needs Recovery" button**
- These tasks are stuck and need status change to resume
- UI shows yellow "Recover" button
- **Action**: Same as Scenario 1 - change status to `"start_requested"`

**Scenario 4: Tasks showing "Stuck" status**
- Agent interrupted mid-execution
- **Action**: Change status from current state to `"start_requested"`

### RDR Troubleshooting Checklist

**RDR not sending auto-prompts:**
1. Check startup logs for module resolution errors
2. Verify OutputMonitor is working: `[OutputMonitor] AT_PROMPT` in logs
3. Verify MCP monitor loaded: `[RDR] MCP monitor check...` in logs
4. Check if Claude Code is busy: `[RDR] BUSY: Claude Code is processing...`

**Tasks not resuming after status change:**
1. Verify BOTH main AND worktree JSON files updated
2. Check file watcher is active: `[FileWatcher] Specs watcher READY`
3. Verify status changed to `"start_requested"` (not `"backlog"` or `"in_progress"`)
4. Check ProjectStore logs for cache invalidation

**Auto-Claude UI not updating:**
1. Auto-refresh triggers within 2-3 seconds of file changes
2. Check browser console for errors
3. Verify file watcher detected changes in logs
4. Manually refresh if needed (rarely required)

### Recovery Decision Tree

```
Task needs recovery?
├─ JSON Parse Error → Priority 3: Create minimal JSON with status="start_requested"
├─ Stuck in plan_review → Priority 1: Change status to "start_requested"
├─ Stuck in human_review → Priority 1: Change status to "start_requested"
├─ Shows "Needs Recovery" → Priority 1: Change status to "start_requested"
├─ Error with logs → Priority 2: Debug logs, fix issue, set status="start_requested"
└─ Completely corrupted → Priority 5: Delete worktree, recreate task
```

### Critical Recovery Rules

1. **ALWAYS fix BOTH main and worktree versions**
   - Auto-Claude ProjectStore prefers worktree over main
   - Fixing only main will NOT work if worktree exists

2. **Use `"start_requested"` status to trigger**
   - NOT `"backlog"` (won't start)
   - NOT `"in_progress"` (won't trigger planning)
   - `"start_requested"` tells Auto-Claude to begin/resume

3. **File watcher triggers automatically**
   - No need to manually refresh UI
   - Changes detected within 2-3 seconds
   - Task cards update automatically

4. **Check worktree location**
   ```
   .auto-claude/
   ├── specs/           # Main project specs
   └── worktrees/
       └── tasks/
           └── TASK-ID/  # Worktree for this task
               └── .auto-claude/
                   └── specs/
                       └── TASK-ID/
                           └── implementation_plan.json  # THIS ONE takes precedence!
   ```

## Overnight Workflow Example

User: "Queue these tasks and shutdown when all done"

1. **Create batch** with `balanced` profile (cost-efficient for batch)
2. **Start all tasks** immediately
3. **Wait for human_review** status on all tasks
4. **Execute shutdown** command with 2-minute delay

```
→ start_batch({
    projectId: "uuid",
    tasks: [...],
    options: { model: "sonnet" },
    startImmediately: true
  })
→ wait_for_human_review({
    projectId: "uuid",
    taskIds: [...],
    onComplete: {
      command: "shutdown",
      args: ["/s", "/t", "120"],
      delaySeconds: 60
    }
  })
```

## Important Notes

- **requireReviewBeforeCoding: true** = Task pauses after spec creation for human approval
- **requireReviewBeforeCoding: false** = Task runs fully autonomous until Human Review
- Human Review = All code is written, committed to worktree, ready for merge
- Tasks run in **isolated git worktrees** - safe from main branch
- User can **merge or discard** each worktree after review

## Reference Files

Include relevant files to give the agent context:

```json
{
  "options": {
    "referencedFiles": [
      "src/components/Auth.tsx",
      "src/hooks/useAuth.ts",
      "src/types/user.ts"
    ]
  }
}
```

These files are read by the agent during spec creation for better context.

## Categories

| Category | When to Use |
|----------|-------------|
| `feature` | New functionality |
| `bug_fix` | Fixing broken behavior |
| `refactoring` | Code restructuring |
| `documentation` | Docs and comments |
| `security` | Security improvements |
| `performance` | Speed/efficiency |
| `ui_ux` | UI/UX changes |
| `infrastructure` | Build, CI, config |
| `testing` | Test coverage |

## Complexity Levels

| Level | Description |
|-------|-------------|
| `trivial` | One-liner, typo fix |
| `small` | Single file, simple logic |
| `medium` | Multiple files, moderate logic |
| `large` | Many files, complex logic |
| `complex` | Architectural changes |

## Priority Levels

| Priority | When to Use |
|----------|-------------|
| `low` | Nice to have |
| `medium` | Normal priority |
| `high` | Important, do soon |
| `urgent` | Critical, do first |
