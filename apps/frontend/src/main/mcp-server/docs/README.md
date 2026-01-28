# Auto-Claude MCP Server

MCP (Model Context Protocol) server that exposes Auto-Claude task management to Claude Code and other MCP clients.

## Features

- **Task Creation**: Create tasks with full configuration (models, thinking, review settings)
- **Batch Operations**: Queue multiple tasks at once
- **Status Monitoring**: Track task progress through the pipeline
- **Shutdown Hook**: Execute commands when tasks reach Human Review

## Installation

### 1. Install Dependencies

The MCP server is included with Auto-Claude. Ensure you have the latest version installed.

### 2. Configure Claude Code

Add to your Claude Code MCP configuration (`~/.claude/claude_desktop_config.json` or similar):

```json
{
  "mcpServers": {
    "auto-claude": {
      "command": "node",
      "args": ["C:/path/to/Auto-Claude Mod/apps/frontend/dist/mcp-server/index.js"],
      "env": {
        "AUTO_CLAUDE_PROJECT": "C:/Users/you/Desktop/YourProject"
      }
    }
  }
}
```

### 3. Install Skill File (Optional)

For better Claude Code integration, symlink or copy the skill file:

**Windows (PowerShell as Admin):**
```powershell
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.claude\skills\auto-claude-mcp.md" -Target "C:\path\to\Auto-Claude Mod\apps\frontend\src\main\mcp-server\docs\skill.md"
```

**macOS/Linux:**
```bash
ln -s "/path/to/Auto-Claude Mod/apps/frontend/src/main/mcp-server/docs/skill.md" ~/.claude/skills/auto-claude-mcp.md
```

## MCP Tools

### create_task

Create a new task with optional configuration.

**Parameters:**
- `projectId` (required): Project UUID from Auto-Claude
- `description` (required): Detailed task description
- `title` (optional): Task title (auto-generated if empty)
- `options` (optional): Task configuration options

**Options:**
```typescript
{
  model?: 'haiku' | 'sonnet' | 'opus',
  phaseModels?: {
    specCreation?: 'haiku' | 'sonnet' | 'opus',
    planning?: 'haiku' | 'sonnet' | 'opus',
    coding?: 'haiku' | 'sonnet' | 'opus',
    qaReview?: 'haiku' | 'sonnet' | 'opus'
  },
  phaseThinking?: {
    specCreation?: number,  // 0, 1024, 4096, 16384, or 63999
    planning?: number,
    coding?: number,
    qaReview?: number
  },
  requireReviewBeforeCoding?: boolean,
  baseBranch?: string,
  referencedFiles?: string[],
  category?: 'feature' | 'bug_fix' | 'refactoring' | 'documentation' | 'security' | 'performance' | 'ui_ux' | 'infrastructure' | 'testing',
  complexity?: 'trivial' | 'small' | 'medium' | 'large' | 'complex',
  priority?: 'low' | 'medium' | 'high' | 'urgent'
}
```

### list_tasks

List all tasks for a project.

**Parameters:**
- `projectId` (required): Project UUID
- `status` (optional): Filter by status

### start_task

Start execution of a task.

**Parameters:**
- `projectId` (required): Project UUID
- `taskId` (required): Task ID (spec folder name)
- `options` (optional): Override model or base branch

### get_task_status

Get detailed status of a task.

**Parameters:**
- `projectId` (required): Project UUID
- `taskId` (required): Task ID

**Returns:**
- `taskId`: Task identifier
- `title`: Task title
- `status`: Current status
- `phase`: Current execution phase
- `progress`: Completion percentage
- `subtaskCount`: Total subtasks
- `completedSubtasks`: Completed subtasks
- `error`: Error message if failed
- `reviewReason`: Why human review is needed

### start_batch

Create and start multiple tasks.

**Parameters:**
- `projectId` (required): Project UUID
- `tasks` (required): Array of task definitions
- `options` (optional): Default options for all tasks
- `startImmediately` (optional): Start tasks after creation (default: true)

### wait_for_human_review

Wait for tasks to reach Human Review status, then optionally execute a command.

**Parameters:**
- `projectId` (required): Project UUID
- `taskIds` (required): Array of task IDs to monitor
- `onComplete` (optional): Command to execute when all reach Human Review
- `pollIntervalMs` (optional): How often to check status (default: 30000)
- `timeoutMs` (optional): Maximum wait time

**onComplete Options:**
```typescript
{
  command: string,      // e.g., "shutdown"
  args?: string[],      // e.g., ["/s", "/t", "120"]
  delaySeconds?: number // Grace period before executing (default: 60)
}
```

## Architecture

```
┌──────────────┐       MCP Protocol        ┌──────────────────────┐
│ Claude Code  │ ◄────────────────────────► │ Auto-Claude MCP     │
│ (MCP Client) │                           │ Server              │
└──────────────┘                           └──────────┬───────────┘
                                                      │
                                                      ▼
                                           ┌──────────────────────┐
                                           │ Auto-Claude Core     │
                                           │ (Task Management)    │
                                           └──────────────────────┘
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AUTO_CLAUDE_PROJECT` | Default project path | None |
| `MCP_SERVER_PORT` | Port for HTTP transport | stdio |

## Examples

### Create a Feature Task

```json
{
  "tool": "create_task",
  "arguments": {
    "projectId": "abc123",
    "description": "Add user authentication with OAuth2 support for Google and GitHub providers",
    "options": {
      "model": "opus",
      "category": "feature",
      "complexity": "large",
      "priority": "high",
      "referencedFiles": ["src/auth/", "src/config/oauth.ts"]
    }
  }
}
```

### Batch Overnight Run

```json
{
  "tool": "start_batch",
  "arguments": {
    "projectId": "abc123",
    "tasks": [
      { "description": "Add dark mode toggle" },
      { "description": "Fix mobile responsive layout", "options": { "category": "bug_fix" } },
      { "description": "Add unit tests for auth module", "options": { "category": "testing" } }
    ],
    "options": {
      "model": "sonnet",
      "requireReviewBeforeCoding": false
    }
  }
}
```

Then wait for completion with shutdown:

```json
{
  "tool": "wait_for_human_review",
  "arguments": {
    "projectId": "abc123",
    "taskIds": ["001-add-dark-mode", "002-fix-mobile-layout", "003-add-auth-tests"],
    "onComplete": {
      "command": "shutdown",
      "args": ["/s", "/t", "120"],
      "delaySeconds": 60
    }
  }
}
```

## Troubleshooting

### MCP Server Not Starting

1. Check that Auto-Claude is installed and working
2. Verify the path to `index.js` is correct
3. Check logs in Auto-Claude's log directory

### Tasks Not Appearing

1. Ensure `projectId` matches a registered project in Auto-Claude
2. Check that the project path exists and is accessible

### Shutdown Not Executing

1. Verify the command syntax for your OS
2. Check that appropriate permissions exist (admin may be required)
3. Review the delay settings

## License

Part of Auto-Claude Mod. See main project for license.
