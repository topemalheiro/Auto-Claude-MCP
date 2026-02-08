#!/usr/bin/env node
/**
 * Auto-Claude MCP Server
 *
 * This MCP server exposes Auto-Claude task management to Claude Code and other MCP clients.
 * It enables:
 * - Task creation with full configuration (models, thinking levels, review settings)
 * - Batch task creation
 * - Task status monitoring
 * - Shutdown hook when tasks reach Human Review
 *
 * Usage:
 * - Run as standalone: node index.js
 * - Configure in Claude Code MCP settings
 */

// CRITICAL: Mock Electron environment before any imports
// Sentry's electron integration checks process.versions.electron at module load time
// If it's undefined (i.e., we're not running in Electron), it crashes
// So we fake it to prevent the crash
if (!process.versions.electron) {
  (process.versions as any).electron = '30.0.0'; // Mock version
}

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

import {
  createTask,
  listTasks,
  getTaskStatus,
  startTask,
  executeCommand,
  pollTaskStatuses,
  resolveProjectPath
} from './utils.js';
import { projectStore } from '../project-store.js';
import { readAndClearSignalFile } from '../ipc-handlers/rdr-handlers.js';
import { existsSync, readFileSync, unlinkSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';
import type {
  TaskOptions,
  TaskCategory,
  TaskComplexity,
  TaskPriority,
  TaskStatus,
  ModelType,
  BatchTaskDefinition,
  BatchResult,
  WaitResult
} from './types.js';

// ─────────────────────────────────────────────────────────────────────────────
// Zod Schemas for Tool Parameters
// ─────────────────────────────────────────────────────────────────────────────

const ModelTypeSchema = z.enum(['haiku', 'sonnet', 'opus']);

const TaskCategorySchema = z.enum([
  'feature',
  'bug_fix',
  'refactoring',
  'documentation',
  'security',
  'performance',
  'ui_ux',
  'infrastructure',
  'testing'
]);

const TaskComplexitySchema = z.enum(['trivial', 'small', 'medium', 'large', 'complex']);

const TaskPrioritySchema = z.enum(['low', 'medium', 'high', 'urgent']);

const TaskStatusSchema = z.enum([
  'backlog',
  'in_progress',
  'ai_review',
  'human_review',
  'pr_created',
  'done',
  'error'
]);

const PhaseModelsSchema = z.object({
  specCreation: ModelTypeSchema.optional(),
  planning: ModelTypeSchema.optional(),
  coding: ModelTypeSchema.optional(),
  qaReview: ModelTypeSchema.optional()
}).optional();

const PhaseThinkingSchema = z.object({
  specCreation: z.number().optional(),
  planning: z.number().optional(),
  coding: z.number().optional(),
  qaReview: z.number().optional()
}).optional();

const TaskOptionsSchema = z.object({
  model: ModelTypeSchema.optional(),
  phaseModels: PhaseModelsSchema,
  phaseThinking: PhaseThinkingSchema,
  requireReviewBeforeCoding: z.boolean().optional(),
  baseBranch: z.string().optional(),
  referencedFiles: z.array(z.string()).optional(),
  category: TaskCategorySchema.optional(),
  complexity: TaskComplexitySchema.optional(),
  priority: TaskPrioritySchema.optional()
}).optional();

const OnCompleteSchema = z.object({
  command: z.string(),
  args: z.array(z.string()).optional(),
  delaySeconds: z.number().optional()
}).optional();

// ─────────────────────────────────────────────────────────────────────────────
// MCP Connection Monitor - Track Activity for Busy Detection
// ─────────────────────────────────────────────────────────────────────────────

class MCPConnectionMonitor {
  private lastRequestTime: number = 0;
  private isProcessing: boolean = false;
  private activeToolName: string | null = null;

  onRequestStart(toolName: string): void {
    this.isProcessing = true;
    this.lastRequestTime = Date.now();
    this.activeToolName = toolName;
    console.log(`[MCP] 📨 Request started: ${toolName}`);
  }

  onRequestEnd(toolName: string): void {
    this.isProcessing = false;
    this.lastRequestTime = Date.now();
    this.activeToolName = null;
    console.log(`[MCP] ✅ Request completed: ${toolName}`);
  }

  isBusy(): boolean {
    const recentThreshold = Date.now() - 30000; // 30 seconds (extended from 3s to prevent false "idle" during Claude thinking time)

    // If actively processing OR had activity in last 30 seconds
    return this.isProcessing || (this.lastRequestTime > recentThreshold);
  }

  getStatus() {
    return {
      isBusy: this.isBusy(),
      isProcessing: this.isProcessing,
      activeToolName: this.activeToolName,
      lastRequestTime: this.lastRequestTime,
      timeSinceLastRequest: Date.now() - this.lastRequestTime
    };
  }
}

export const mcpMonitor = new MCPConnectionMonitor();

// Helper to wrap tool handlers with monitoring
function withMonitoring<T extends (...args: any[]) => Promise<any>>(
  toolName: string,
  handler: T
): T {
  return (async (...args: any[]) => {
    mcpMonitor.onRequestStart(toolName);
    try {
      const result = await handler(...args);
      return result;
    } finally {
      mcpMonitor.onRequestEnd(toolName);
    }
  }) as T;
}

// ─────────────────────────────────────────────────────────────────────────────
// MCP Server Setup
// ─────────────────────────────────────────────────────────────────────────────

const server = new McpServer({
  name: 'auto-claude',
  version: '1.0.0'
}, {
  capabilities: {
    tools: {
      listChanged: true
    }
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// Tool: create_task
// ─────────────────────────────────────────────────────────────────────────────

server.tool(
  'create_task',
  'Create a new task in Auto-Claude with optional configuration for models, thinking levels, and review settings',
  {
    projectId: z.string().describe('The project ID (UUID) to create the task in'),
    projectPath: z.string().optional().describe('Fallback filesystem path if projectId UUID not found'),
    description: z.string().describe('Detailed description of the task to implement'),
    title: z.string().optional().describe('Optional title for the task (auto-generated if empty)'),
    options: TaskOptionsSchema.describe('Optional configuration for models, thinking, review, and classification')
  },
  withMonitoring('create_task', async ({ projectId, projectPath, description, title, options }) => {
    const result = await createTask(projectId, description, title, options as TaskOptions, projectPath);

    if (!result.success) {
      return {
        content: [{ type: 'text' as const, text: `Error: ${result.error}` }],
        isError: true
      };
    }

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          taskId: result.data!.taskId,
          title: result.data!.title,
          specPath: result.data!.specPath,
          status: result.data!.status
        }, null, 2)
      }]
    };
  })
);

// ─────────────────────────────────────────────────────────────────────────────
// Tool: list_tasks
// ─────────────────────────────────────────────────────────────────────────────

server.tool(
  'list_tasks',
  'List all tasks for a project, optionally filtered by status',
  {
    projectId: z.string().describe('The project ID (UUID) to list tasks from'),
    projectPath: z.string().optional().describe('Fallback filesystem path if projectId UUID not found'),
    status: TaskStatusSchema.optional().describe('Optional status filter')
  },
  async ({ projectId, projectPath, status }) => {
    const result = listTasks(projectId, status as TaskStatus | undefined, projectPath);

    if (!result.success) {
      return {
        content: [{ type: 'text' as const, text: `Error: ${result.error}` }],
        isError: true
      };
    }

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify(result.data, null, 2)
      }]
    };
  }
);

// ─────────────────────────────────────────────────────────────────────────────
// Tool: get_task_status
// ─────────────────────────────────────────────────────────────────────────────

server.tool(
  'get_task_status',
  'Get detailed status of a specific task including progress and phase information',
  {
    projectId: z.string().describe('The project ID (UUID)'),
    projectPath: z.string().optional().describe('Fallback filesystem path if projectId UUID not found'),
    taskId: z.string().describe('The task ID (spec folder name)')
  },
  async ({ projectId, projectPath, taskId }) => {
    const result = getTaskStatus(projectId, taskId, projectPath);

    if (!result.success) {
      return {
        content: [{ type: 'text' as const, text: `Error: ${result.error}` }],
        isError: true
      };
    }

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify(result.data, null, 2)
      }]
    };
  }
);

// ─────────────────────────────────────────────────────────────────────────────
// Tool: start_task
// ─────────────────────────────────────────────────────────────────────────────

server.tool(
  'start_task',
  'Start execution of a task. This writes a start_requested status that the Electron app detects and begins execution.',
  {
    projectId: z.string().describe('The project ID (UUID)'),
    projectPath: z.string().optional().describe('Fallback filesystem path if projectId UUID not found'),
    taskId: z.string().describe('The task ID (spec folder name) to start')
  },
  async ({ projectId, projectPath, taskId }) => {
    const result = startTask(projectId, taskId, projectPath);

    if (!result.success) {
      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({ error: result.error }, null, 2)
        }],
        isError: true
      };
    }

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          success: true,
          taskId,
          projectId,
          message: result.data?.message
        }, null, 2)
      }]
    };
  }
);

// ─────────────────────────────────────────────────────────────────────────────
// Tool: start_batch
// ─────────────────────────────────────────────────────────────────────────────

server.tool(
  'start_batch',
  'Create and optionally start multiple tasks at once',
  {
    projectId: z.string().describe('The project ID (UUID)'),
    projectPath: z.string().optional().describe('Fallback filesystem path if projectId UUID not found'),
    tasks: z.array(z.object({
      description: z.string(),
      title: z.string().optional(),
      options: TaskOptionsSchema
    })).describe('Array of task definitions to create'),
    options: TaskOptionsSchema.describe('Default options applied to all tasks'),
    startImmediately: z.boolean().optional().default(true).describe('Whether to start tasks after creation')
  },
  async ({ projectId, projectPath, tasks, options, startImmediately }) => {
    const results: BatchResult = {
      taskIds: [],
      created: 0,
      started: 0,
      errors: []
    };

    // Create each task
    for (const taskDef of tasks) {
      // Merge default options with task-specific options
      const mergedOptions = {
        ...options,
        ...taskDef.options
      } as TaskOptions;

      const result = await createTask(
        projectId,
        taskDef.description,
        taskDef.title,
        mergedOptions,
        projectPath
      );

      if (result.success && result.data) {
        results.taskIds.push(result.data.taskId);
        results.created++;
      } else {
        results.errors.push({
          description: taskDef.description,
          error: result.error || 'Unknown error'
        });
      }
    }

    // Note about starting tasks
    if (startImmediately && results.created > 0) {
      // Starting requires IPC - provide guidance
      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({
            ...results,
            note: 'Tasks created successfully. Use the Auto-Claude UI to start them, or ensure the MCP server is running within the Electron app context.'
          }, null, 2)
        }]
      };
    }

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify(results, null, 2)
      }]
    };
  }
);

// ─────────────────────────────────────────────────────────────────────────────
// Tool: wait_for_human_review
// ─────────────────────────────────────────────────────────────────────────────

server.tool(
  'wait_for_human_review',
  'Wait for tasks to reach Human Review status, then optionally execute a command (like shutdown). IMPORTANT: Will NOT execute command if any tasks crashed due to rate limit - those tasks will auto-resume when limit resets.',
  {
    projectId: z.string().describe('The project ID (UUID)'),
    projectPath: z.string().optional().describe('Fallback filesystem path if projectId UUID not found'),
    taskIds: z.array(z.string()).describe('Array of task IDs to monitor'),
    onComplete: OnCompleteSchema.describe('Optional command to execute when all tasks reach Human Review'),
    pollIntervalMs: z.number().optional().default(30000).describe('How often to check status (default: 30000ms)'),
    timeoutMs: z.number().optional().describe('Maximum time to wait (no default = wait indefinitely)')
  },
  async ({ projectId, projectPath: _projectPath, taskIds, onComplete, pollIntervalMs, timeoutMs }) => {
    console.warn(`[MCP] Starting wait for ${taskIds.length} tasks to reach Human Review`);

    const pollResult = await pollTaskStatuses(
      projectId,
      taskIds,
      'human_review',
      pollIntervalMs,
      timeoutMs
    );

    const result: WaitResult = {
      completed: pollResult.completed,
      taskStatuses: pollResult.statuses,
      timedOut: pollResult.timedOut
    };

    // Bug #5: Check for rate limit crashes before executing command
    // If any tasks crashed due to rate limit, DON'T execute the command (like shutdown)
    // Those tasks will auto-resume when the rate limit resets
    const rateLimitCrashes = pollResult.rateLimitCrashes || [];
    if (rateLimitCrashes.length > 0) {
      console.warn(`[MCP] ${rateLimitCrashes.length} tasks crashed due to rate limit - blocking command execution`);
      console.warn(`[MCP] Rate-limited tasks: ${rateLimitCrashes.join(', ')}`);

      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({
            ...result,
            shutdownBlocked: true,
            rateLimitCrashes,
            message: `${rateLimitCrashes.length} task(s) crashed due to rate limit and are waiting to auto-resume. Command (${onComplete?.command || 'none'}) was NOT executed. Tasks will auto-resume when rate limit resets.`
          }, null, 2)
        }]
      };
    }

    // Execute on-complete command if provided and all tasks completed (without rate limit crashes)
    if (pollResult.completed && onComplete?.command) {
      console.warn(`[MCP] All tasks reached Human Review (no rate limit crashes), scheduling command: ${onComplete.command}`);

      const delaySeconds = onComplete.delaySeconds ?? 60;
      const cmdResult = await executeCommand(
        onComplete.command,
        onComplete.args || [],
        delaySeconds
      );

      result.commandExecuted = cmdResult.executed;
      result.commandOutput = cmdResult.output || cmdResult.error;
    }

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify(result, null, 2)
      }]
    };
  }
);

// ─────────────────────────────────────────────────────────────────────────────
// Tool: get_tasks_needing_intervention
// ─────────────────────────────────────────────────────────────────────────────

server.tool(
  'get_tasks_needing_intervention',
  'Get all tasks that need intervention (errors, stuck, incomplete subtasks, QA rejected)',
  {
    projectId: z.string().describe('The project ID (UUID)'),
    projectPath: z.string().optional().describe('Fallback filesystem path if projectId UUID not found')
  },
  async ({ projectId, projectPath }) => {
    const result = await listTasks(projectId, undefined, projectPath);

    if (!result.success || !result.data) {
      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({ success: false, error: result.error || 'Failed to list tasks' })
        }]
      };
    }

    // Filter tasks that need intervention
    const tasksNeedingHelp = result.data.filter(task => {
      // Check both human_review AND in_progress tasks (stuck tasks can be in either state)
      if (task.status !== 'human_review' && task.status !== 'in_progress') return false;

      // JSON error tasks
      if (task.description?.startsWith('__JSON_ERROR__:')) return true;

      // Tasks with errors or QA rejected
      if (task.reviewReason === 'errors' || task.reviewReason === 'qa_rejected') return true;

      // Incomplete tasks (subtasks not all completed)
      if (task.subtasks && task.subtasks.some((s: { status: string }) => s.status !== 'completed')) return true;

      // For in_progress tasks, also check for stale timestamp (no activity in 5+ minutes)
      if (task.status === 'in_progress' && task.updatedAt) {
        const lastUpdate = new Date(task.updatedAt).getTime();
        const now = Date.now();
        const fiveMinutesAgo = now - (5 * 60 * 1000);

        // If task is in_progress but hasn't been updated in 5+ minutes AND has incomplete subtasks, flag it
        if (lastUpdate < fiveMinutesAgo && task.subtasks && task.subtasks.some((s: { status: string }) => s.status !== 'completed')) {
          return true;
        }
      }

      return false;
    });

    const interventionTasks = tasksNeedingHelp.map(task => ({
      taskId: task.specId || task.id,
      title: task.title,
      interventionType: task.description?.startsWith('__JSON_ERROR__:') ? 'json_error' :
                        task.reviewReason === 'qa_rejected' ? 'qa_rejected' :
                        task.reviewReason === 'errors' ? 'error' : 'incomplete_subtasks',
      errorSummary: task.description?.startsWith('__JSON_ERROR__:')
        ? task.description.slice('__JSON_ERROR__:'.length)
        : task.reviewReason || 'Incomplete subtasks',
      subtasksCompleted: task.subtasks?.filter((s: { status: string }) => s.status === 'completed').length || 0,
      subtasksTotal: task.subtasks?.length || 0,
      lastActivity: task.updatedAt
    }));

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          success: true,
          count: interventionTasks.length,
          tasks: interventionTasks
        }, null, 2)
      }]
    };
  }
);

// ─────────────────────────────────────────────────────────────────────────────
// Tool: get_task_error_details
// ─────────────────────────────────────────────────────────────────────────────

server.tool(
  'get_task_error_details',
  'Get detailed error information for a task including logs, QA report, and context',
  {
    projectId: z.string().describe('The project ID (UUID)'),
    projectPath: z.string().optional().describe('Fallback filesystem path if projectId UUID not found'),
    taskId: z.string().describe('The task/spec ID')
  },
  withMonitoring('get_task_error_details', async ({ projectId, projectPath, taskId }) => {
    const statusResult = await getTaskStatus(projectId, taskId, projectPath);

    if (!statusResult.success || !statusResult.data) {
      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({ success: false, error: statusResult.error || 'Task not found' })
        }]
      };
    }

    const task = statusResult.data;

    // Build error details
    const errorDetails: Record<string, unknown> = {};

    // Check for JSON error
    if (task.description?.startsWith('__JSON_ERROR__:')) {
      errorDetails.jsonError = task.description.slice('__JSON_ERROR__:'.length);
    }

    // Get failed subtasks
    if (task.subtasks) {
      const failedSubtasks = task.subtasks.filter((s: { status: string }) => s.status === 'failed');
      if (failedSubtasks.length > 0) {
        errorDetails.failedSubtasks = failedSubtasks;
      }
    }

    // Include QA report if available
    if (task.qaReport) {
      errorDetails.qaReport = task.qaReport;
    }

    // Include exit reason and rate limit info
    if (task.exitReason) {
      errorDetails.exitReason = task.exitReason;
    }
    if (task.rateLimitInfo) {
      errorDetails.rateLimitInfo = task.rateLimitInfo;
    }

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          success: true,
          taskId: task.specId || task.id,
          status: task.status,
          reviewReason: task.reviewReason,
          exitReason: task.exitReason,
          errorDetails,
          context: {
            title: task.title,
            description: task.description,
            subtasksTotal: task.subtasks?.length || 0,
            subtasksCompleted: task.subtasks?.filter((s: { status: string }) => s.status === 'completed').length || 0
          }
        }, null, 2)
      }]
    };
  })
);

// ─────────────────────────────────────────────────────────────────────────────
// Tool: recover_stuck_task
// ─────────────────────────────────────────────────────────────────────────────

server.tool(
  'recover_stuck_task',
  'Trigger recovery for a stuck task (equivalent to clicking Recover button). Uses file-based recovery.',
  {
    projectId: z.string().describe('The project ID (UUID)'),
    projectPath: z.string().optional().describe('Fallback filesystem path if projectId UUID not found'),
    taskId: z.string().describe('The task/spec ID'),
    autoRestart: z.boolean().optional().default(true).describe('Whether to auto-restart after recovery')
  },
  withMonitoring('recover_stuck_task', async ({ projectId, projectPath, taskId, autoRestart }) => {
    // File-based recovery: Read plan, remove stuckSince, set start_requested if autoRestart
    const { existsSync, writeFileSync, readFileSync } = await import('fs');
    const path = await import('path');

    // Get project path via UUID or fallback path
    const resolved = resolveProjectPath(projectId, projectPath);
    if ('error' in resolved) {
      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({ success: false, error: resolved.error })
        }]
      };
    }

    const resolvedProjectPath = resolved.projectPath;
    const specDir = path.join(resolvedProjectPath, '.auto-claude', 'specs', taskId);
    const planPath = path.join(specDir, 'implementation_plan.json');

    if (!existsSync(planPath)) {
      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({ success: false, error: 'Task plan file not found: ' + planPath })
        }]
      };
    }

    try {
      // Read plan
      const plan = JSON.parse(readFileSync(planPath, 'utf-8'));
      let recovered = false;
      let action = '';

      // Remove stuckSince timestamp (exits recovery mode)
      if (plan.metadata?.stuckSince) {
        delete plan.metadata.stuckSince;
        recovered = true;
        action = 'removed_stuck_timestamp';
      }

      // If autoRestart, also set start_requested (triggers Priority 1 auto-resume)
      if (autoRestart) {
        plan.status = 'start_requested';
        plan.start_requested_at = new Date().toISOString();
        plan.rdr_batch_type = 'recovery';
        plan.rdr_priority = 1;
        plan.rdr_iteration = (plan.rdr_iteration || 0) + 1;
        action += (action ? ' + ' : '') + 'set_start_requested';
      } else {
        // Update lastActivity to refresh task (without restarting)
        plan.updated_at = new Date().toISOString();
        if (!plan.metadata) plan.metadata = {};
        plan.metadata.lastActivity = new Date().toISOString();
        action += (action ? ' + ' : '') + 'updated_last_activity';
      }

      // Write to main plan
      writeFileSync(planPath, JSON.stringify(plan, null, 2));

      // Also update worktree plan (if it exists)
      const worktreePlanPath = path.join(
        resolvedProjectPath, '.auto-claude', 'worktrees', 'tasks', taskId,
        '.auto-claude', 'specs', taskId, 'implementation_plan.json'
      );
      if (existsSync(worktreePlanPath)) {
        try {
          const worktreePlan = JSON.parse(readFileSync(worktreePlanPath, 'utf-8'));

          if (worktreePlan.metadata?.stuckSince) {
            delete worktreePlan.metadata.stuckSince;
          }

          if (autoRestart) {
            worktreePlan.status = 'start_requested';
            worktreePlan.start_requested_at = new Date().toISOString();
            worktreePlan.rdr_batch_type = 'recovery';
            worktreePlan.rdr_priority = 1;
            worktreePlan.rdr_iteration = (worktreePlan.rdr_iteration || 0) + 1;
          } else {
            worktreePlan.updated_at = new Date().toISOString();
            if (!worktreePlan.metadata) worktreePlan.metadata = {};
            worktreePlan.metadata.lastActivity = new Date().toISOString();
          }

          writeFileSync(worktreePlanPath, JSON.stringify(worktreePlan, null, 2));
          console.log(`[MCP] Also updated worktree plan for ${taskId}`);
        } catch (err) {
          console.warn(`[MCP] Failed to update worktree plan for ${taskId}:`, err);
        }
      }

      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({
            success: true,
            taskId,
            recovered,
            autoRestart,
            action,
            message: autoRestart
              ? `Task ${taskId} recovered and set to restart. File watcher will auto-start within 2-3 seconds.`
              : `Task ${taskId} recovered (exit recovery mode). Task will not auto-restart - manually start if needed.`
          }, null, 2)
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : String(error),
            taskId
          })
        }]
      };
    }
  })
);

// ─────────────────────────────────────────────────────────────────────────────
// Tool: submit_task_fix_request
// ─────────────────────────────────────────────────────────────────────────────

server.tool(
  'submit_task_fix_request',
  `Submit a fix request for a task (Priority 2: Request Changes).

  This writes QA_FIX_REQUEST.md with detailed context and sets status='start_requested' to trigger the 4-tier recovery system:
  - Priority 1 (AUTO): File watcher moves task to correct board based on subtask progress
  - Priority 2 (THIS TOOL): Writes detailed fix request with context
  - Task auto-restarts and resumes from where it left off`,
  {
    projectId: z.string().describe('The project ID (UUID)'),
    projectPath: z.string().optional().describe('Fallback filesystem path if projectId UUID not found'),
    taskId: z.string().describe('The task/spec ID'),
    feedback: z.string().describe('Description of what needs to be fixed (include context from Overview, Subtasks, Logs, Files tabs)')
  },
  withMonitoring('submit_task_fix_request', async ({ projectId, projectPath, taskId, feedback }) => {
    // Import fs functions
    const { existsSync, writeFileSync, readFileSync } = await import('fs');
    const path = await import('path');

    // Resolve project path via UUID or fallback path
    const resolved = resolveProjectPath(projectId, projectPath);
    if ('error' in resolved) {
      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({ success: false, error: resolved.error })
        }]
      };
    }

    const resolvedProjectPath = resolved.projectPath;
    const specDir = path.join(resolvedProjectPath, '.auto-claude', 'specs', taskId);
    const fixRequestPath = path.join(specDir, 'QA_FIX_REQUEST.md');
    const planPath = path.join(specDir, 'implementation_plan.json');

    if (!existsSync(specDir)) {
      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({ success: false, error: 'Spec directory not found: ' + specDir })
        }]
      };
    }

    try {
      // Write fix request file (Priority 2: Request Changes)
      const content = `# Fix Request (Claude Code via MCP)

**Issues to Address:**

${feedback}

**Action Required:**
1. Review the feedback above
2. Check relevant tabs for more context:
   - **Overview**: Error messages, JSON errors, build status
   - **Subtasks**: Which subtasks are pending/incomplete
   - **Logs**: Execution logs, validation errors, stack traces
   - **Files**: What was created/modified
3. Fix the issues and continue from where the task left off

**Recovery Process:**
- This fix request triggers the 4-tier recovery system
- File watcher will automatically move task to the correct board (backlog/in_progress/ai_review) based on subtask progress
- Task will auto-restart and resume work

---
Generated at: ${new Date().toISOString()}
Source: Claude Code MCP Tool (Priority 2: Request Changes)
`;
      writeFileSync(fixRequestPath, content);

      // Also write QA_FIX_REQUEST.md to worktree (agent runs there, needs to see it)
      const worktreeSpecDir = path.join(
        resolvedProjectPath, '.auto-claude', 'worktrees', 'tasks', taskId,
        '.auto-claude', 'specs', taskId
      );
      if (existsSync(worktreeSpecDir)) {
        try {
          writeFileSync(path.join(worktreeSpecDir, 'QA_FIX_REQUEST.md'), content);
          console.log(`[MCP] Also wrote QA_FIX_REQUEST.md to worktree for ${taskId}`);
        } catch (err) {
          console.warn(`[MCP] Failed to write worktree QA_FIX_REQUEST.md for ${taskId}:`, err);
        }
      }

      // Update implementation_plan.json to trigger Priority 1 (automatic board movement)
      if (existsSync(planPath)) {
        const plan = JSON.parse(readFileSync(planPath, 'utf-8'));
        plan.status = 'start_requested';
        plan.start_requested_at = new Date().toISOString();
        plan.rdr_priority = 2; // Priority 2: Request Changes
        plan.mcp_feedback = feedback;
        plan.mcp_iteration = (plan.mcp_iteration || 0) + 1;
        writeFileSync(planPath, JSON.stringify(plan, null, 2));
      }

      // Also update worktree plan status (agent runs there, needs to see start_requested)
      const worktreePlanPath = path.join(worktreeSpecDir, 'implementation_plan.json');
      if (existsSync(worktreePlanPath)) {
        try {
          const worktreePlan = JSON.parse(readFileSync(worktreePlanPath, 'utf-8'));
          worktreePlan.status = 'start_requested';
          worktreePlan.start_requested_at = new Date().toISOString();
          worktreePlan.rdr_priority = 2;
          worktreePlan.mcp_feedback = feedback;
          worktreePlan.mcp_iteration = (worktreePlan.mcp_iteration || 0) + 1;
          writeFileSync(worktreePlanPath, JSON.stringify(worktreePlan, null, 2));
          console.log(`[MCP] Also updated worktree plan for ${taskId}`);
        } catch (err) {
          console.warn(`[MCP] Failed to update worktree plan for ${taskId}:`, err);
        }
      }

      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({
            success: true,
            priority: 2,
            message: `Fix request submitted for task ${taskId}. Priority 2 (Request Changes) triggered. Task will auto-restart and file watcher will move to correct board.`,
            taskId,
            feedback,
            fixRequestPath
          }, null, 2)
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : String(error),
            taskId
          })
        }]
      };
    }
  })
);

// ─────────────────────────────────────────────────────────────────────────────
// Tool: get_task_logs
// ─────────────────────────────────────────────────────────────────────────────

server.tool(
  'get_task_logs',
  'Get detailed phase logs for a task (planning, coding, validation)',
  {
    projectId: z.string().describe('The project ID (UUID)'),
    projectPath: z.string().optional().describe('Fallback filesystem path if projectId UUID not found'),
    taskId: z.string().describe('The task/spec ID'),
    phase: z.enum(['planning', 'coding', 'validation']).optional().describe('Specific phase to get logs for (all phases if not specified)'),
    lastN: z.number().optional().default(50).describe('Number of recent log entries to return')
  },
  async ({ projectId, projectPath, taskId, phase, lastN }) => {
    // Note: Full log access requires IPC which is only available within Electron context
    // When running as standalone MCP server, we provide limited info
    const statusResult = await getTaskStatus(projectId, taskId, projectPath);

    if (!statusResult.success || !statusResult.data) {
      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({ success: false, error: statusResult.error || 'Task not found' })
        }]
      };
    }

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          success: true,
          taskId,
          phase: phase || 'all',
          note: 'Full task logs are available in the Auto-Claude UI. ' +
                'Open the task detail modal and navigate to the "Logs" tab. ' +
                'For programmatic access to logs, the MCP server must run within the Electron app context.',
          taskStatus: statusResult.data.status,
          executionPhase: statusResult.data.executionProgress?.phase || 'unknown',
          subtasksStatus: statusResult.data.subtasks?.map((s: { id: string; title: string; status: string }) => ({
            id: s.id,
            title: s.title,
            status: s.status
          }))
        }, null, 2)
      }]
    };
  }
);

// ─────────────────────────────────────────────────────────────────────────────
// Tool: get_rdr_batches
// ─────────────────────────────────────────────────────────────────────────────

server.tool(
  'get_rdr_batches',
  'Get all pending RDR (Recover Debug Resend) batches categorized by problem type. Returns tasks grouped into: json_error, incomplete, qa_rejected, errors. Also reads and clears any pending signal file from the Electron app.',
  {
    projectId: z.string().describe('The project ID (UUID)'),
    projectPath: z.string().optional().describe('Fallback filesystem path if projectId UUID not found')
  },
  withMonitoring('get_rdr_batches', async ({ projectId, projectPath }) => {
    // Resolve project path via UUID or fallback
    const resolved = resolveProjectPath(projectId, projectPath);
    let signalData = null;

    if (!('error' in resolved)) {
      // Check for and read signal file (clears it after reading)
      signalData = readAndClearSignalFile(resolved.projectPath);
      if (signalData) {
        console.log(`[MCP] Found and cleared RDR signal file with ${signalData.batches?.length || 0} batches`);
      }
    }

    const tasksResult = await listTasks(projectId, undefined, projectPath);

    if (!tasksResult.success || !tasksResult.data) {
      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({
            success: false,
            error: tasksResult.error || 'Failed to list tasks',
            signal: signalData // Include signal even if task list fails
          })
        }]
      };
    }

    const tasks = tasksResult.data.tasks || [];
    const humanReviewTasks = tasks.filter((t: { status: string }) => t.status === 'human_review');

    // Categorize into batches
    const batches: Array<{
      type: string;
      taskIds: string[];
      tasks: Array<{
        taskId: string;
        title: string;
        description: string;
        reviewReason: string;
        progress: { completed: number; total: number; percentage: number };
      }>;
    }> = [];

    // Batch 1: JSON Errors
    const jsonErrors = humanReviewTasks.filter((t: { description?: string }) =>
      t.description?.startsWith('__JSON_ERROR__:')
    );
    if (jsonErrors.length > 0) {
      batches.push({
        type: 'json_error',
        taskIds: jsonErrors.map((t: { specId: string }) => t.specId),
        tasks: jsonErrors.map((t: { specId: string; title: string; description?: string; reviewReason?: string; subtasks?: Array<{ status: string }> }) => ({
          taskId: t.specId,
          title: t.title,
          description: t.description?.substring(0, 200) || '',
          reviewReason: t.reviewReason || 'errors',
          progress: {
            completed: t.subtasks?.filter((s: { status: string }) => s.status === 'completed').length || 0,
            total: t.subtasks?.length || 0,
            percentage: t.subtasks?.length ? Math.round((t.subtasks.filter((s: { status: string }) => s.status === 'completed').length / t.subtasks.length) * 100) : 0
          }
        }))
      });
    }

    // Batch 2: Incomplete Tasks (subtasks not all completed, NOT an error)
    const incomplete = humanReviewTasks.filter((t: { reviewReason?: string; description?: string; subtasks?: Array<{ status: string }> }) =>
      t.reviewReason !== 'errors' &&
      !t.description?.startsWith('__JSON_ERROR__:') &&
      t.subtasks &&
      t.subtasks.length > 0 &&
      t.subtasks.some((s: { status: string }) => s.status !== 'completed')
    );
    if (incomplete.length > 0) {
      batches.push({
        type: 'incomplete',
        taskIds: incomplete.map((t: { specId: string }) => t.specId),
        tasks: incomplete.map((t: { specId: string; title: string; description?: string; reviewReason?: string; subtasks?: Array<{ status: string }> }) => ({
          taskId: t.specId,
          title: t.title,
          description: t.description?.substring(0, 200) || '',
          reviewReason: t.reviewReason || 'incomplete',
          progress: {
            completed: t.subtasks?.filter((s: { status: string }) => s.status === 'completed').length || 0,
            total: t.subtasks?.length || 0,
            percentage: t.subtasks?.length ? Math.round((t.subtasks.filter((s: { status: string }) => s.status === 'completed').length / t.subtasks.length) * 100) : 0
          }
        }))
      });
    }

    // Batch 3: QA Rejected
    const qaRejected = humanReviewTasks.filter((t: { reviewReason?: string; description?: string }) =>
      t.reviewReason === 'qa_rejected' &&
      !t.description?.startsWith('__JSON_ERROR__:')
    );
    if (qaRejected.length > 0) {
      batches.push({
        type: 'qa_rejected',
        taskIds: qaRejected.map((t: { specId: string }) => t.specId),
        tasks: qaRejected.map((t: { specId: string; title: string; description?: string; reviewReason?: string; subtasks?: Array<{ status: string }> }) => ({
          taskId: t.specId,
          title: t.title,
          description: t.description?.substring(0, 200) || '',
          reviewReason: t.reviewReason || 'qa_rejected',
          progress: {
            completed: t.subtasks?.filter((s: { status: string }) => s.status === 'completed').length || 0,
            total: t.subtasks?.length || 0,
            percentage: t.subtasks?.length ? Math.round((t.subtasks.filter((s: { status: string }) => s.status === 'completed').length / t.subtasks.length) * 100) : 0
          }
        }))
      });
    }

    // Batch 4: Other Errors (not JSON)
    const errors = humanReviewTasks.filter((t: { reviewReason?: string; description?: string }) =>
      t.reviewReason === 'errors' &&
      !t.description?.startsWith('__JSON_ERROR__:')
    );
    if (errors.length > 0) {
      batches.push({
        type: 'errors',
        taskIds: errors.map((t: { specId: string }) => t.specId),
        tasks: errors.map((t: { specId: string; title: string; description?: string; reviewReason?: string; subtasks?: Array<{ status: string }> }) => ({
          taskId: t.specId,
          title: t.title,
          description: t.description?.substring(0, 200) || '',
          reviewReason: t.reviewReason || 'errors',
          progress: {
            completed: t.subtasks?.filter((s: { status: string }) => s.status === 'completed').length || 0,
            total: t.subtasks?.length || 0,
            percentage: t.subtasks?.length ? Math.round((t.subtasks.filter((s: { status: string }) => s.status === 'completed').length / t.subtasks.length) * 100) : 0
          }
        }))
      });
    }

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          success: true,
          totalTasksInHumanReview: humanReviewTasks.length,
          batchCount: batches.length,
          batches,
          signal: signalData ? {
            timestamp: signalData.timestamp,
            prompt: signalData.prompt,
            batchesFromSignal: signalData.batches
          } : null,
          instructions: batches.length > 0 ?
            'Use process_rdr_batch tool to process each batch. For json_error batch, RDR auto-fixes are applied. For incomplete batch, submit_task_fix_request auto-resumes. For qa_rejected/errors, analyze and submit fixes.' :
            signalData ?
              `Signal file contained prompt:\n\n${signalData.prompt}` :
              'No tasks need intervention.'
        }, null, 2)
      }]
    };
  })
);

// ─────────────────────────────────────────────────────────────────────────────
// Tool: process_rdr_batch
// ─────────────────────────────────────────────────────────────────────────────

server.tool(
  'process_rdr_batch',
  `Process a batch of tasks using the 4-tier priority recovery system:

  Priority 1 (AUTO): File watcher moves tasks to correct board (backlog/in_progress/ai_review) based on subtask progress
  Priority 2 (REQUEST CHANGES): Write detailed QA_FIX_REQUEST.md with context from Overview/Subtasks/Logs/Files
  Priority 3 (FIX TECHNICAL): Auto-fix JSON syntax errors, missing dependencies, build errors
  Priority 4 (MANUAL NUDGE): Minimal intervention (rare cases only)

  For each batch type:
  - json_error: Auto-fix JSON syntax (Priority 3), then trigger Priority 1 via status='start_requested'
  - incomplete: Just trigger Priority 1 (file watcher handles board movement based on subtasks)
  - qa_rejected: Write detailed fix request (Priority 2), then trigger Priority 1
  - errors: Analyze and write fix request (Priority 2), then trigger Priority 1`,
  {
    projectId: z.string().describe('The project ID (UUID)'),
    projectPath: z.string().optional().describe('Fallback filesystem path if projectId UUID not found'),
    batchType: z.enum(['json_error', 'incomplete', 'qa_rejected', 'errors']).describe('The type of batch to process'),
    fixes: z.array(z.object({
      taskId: z.string().describe('The task/spec ID'),
      feedback: z.string().optional().describe('Fix description for this task (optional for incomplete/json_error batches)')
    })).describe('Array of task fixes to submit')
  },
  withMonitoring('process_rdr_batch', async ({ projectId, projectPath, batchType, fixes }) => {
    // Import fs functions
    const { existsSync, writeFileSync, readFileSync } = await import('fs');
    const path = await import('path');

    // Resolve project path via UUID or fallback path
    const resolved = resolveProjectPath(projectId, projectPath);
    if ('error' in resolved) {
      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({ success: false, error: resolved.error })
        }]
      };
    }

    const resolvedProjectPath = resolved.projectPath;
    const results: Array<{ taskId: string; success: boolean; action: string; priority: number; error?: string }> = [];

    for (const fix of fixes) {
      const specDir = path.join(resolvedProjectPath, '.auto-claude', 'specs', fix.taskId);
      const fixRequestPath = path.join(specDir, 'QA_FIX_REQUEST.md');
      const planPath = path.join(specDir, 'implementation_plan.json');

      if (!existsSync(specDir)) {
        results.push({ taskId: fix.taskId, success: false, action: 'error', priority: 0, error: 'Spec directory not found' });
        continue;
      }

      try {
        let action = '';
        let priority = 1; // Default: Priority 1 (automatic board movement)
        let feedbackWrittenToMain = false; // Track if we wrote QA_FIX_REQUEST.md

        // ─────────────────────────────────────────────────────────────────
        // BATCH TYPE SPECIFIC LOGIC (4-Tier Priority System)
        // ─────────────────────────────────────────────────────────────────

        if (batchType === 'json_error') {
          // PRIORITY 3: Fix technical blocker (JSON syntax error)
          // Try to auto-fix JSON syntax errors in implementation_plan.json
          priority = 3;
          action = 'json_auto_fix';

          try {
            const planContent = readFileSync(planPath, 'utf-8');
            // Try to parse - if it fails, we'll catch and report
            JSON.parse(planContent);
            // If parse succeeds, JSON is already valid - just trigger restart
            action = 'json_already_valid';
            priority = 1;
          } catch (jsonError) {
            // JSON parse failed - try to fix it
            // For now, just report the error and let the AI handle it
            // A future enhancement could attempt auto-fix (remove trailing commas, fix quotes, etc.)
            const errorMsg = jsonError instanceof Error ? jsonError.message : String(jsonError);
            const feedbackContent = `# Fix Request (RDR Batch: json_error)

**JSON Parse Error Detected:**
\`\`\`
${errorMsg}
\`\`\`

**Action Required:**
1. Fix the JSON syntax error in implementation_plan.json
2. Ensure all JSON is valid before continuing

---
Generated at: ${new Date().toISOString()}
Source: RDR Batch Processing (Priority 3: Technical Blocker Fix)
Batch Type: ${batchType}
`;
            writeFileSync(fixRequestPath, feedbackContent);
            feedbackWrittenToMain = true;
            action = 'json_fix_requested';
          }

        } else if (batchType === 'incomplete') {
          // PRIORITY 1: Send back to correct board (automatic via file watcher)
          // No QA_FIX_REQUEST.md needed - file watcher handles everything
          priority = 1;
          action = 'auto_resume';

          // Optional: Write minimal context if feedback was provided
          if (fix.feedback) {
            const feedbackContent = `# Auto-Resume (RDR Batch: incomplete)

Task was incomplete when it hit Human Review. Automatically resuming from where it left off.

**Context:**
${fix.feedback}

---
Generated at: ${new Date().toISOString()}
Source: RDR Batch Processing (Priority 1: Automatic Board Movement)
Batch Type: ${batchType}
`;
            writeFileSync(fixRequestPath, feedbackContent);
            feedbackWrittenToMain = true;
          }

        } else if (batchType === 'qa_rejected') {
          // PRIORITY 2: Request changes with detailed context
          priority = 2;
          action = 'detailed_fix_request';

          const feedbackContent = `# Fix Request (RDR Batch: qa_rejected)

**QA Rejected - Issues Found:**

${fix.feedback || 'See validation errors in logs and failed acceptance criteria.'}

**Action Required:**
1. Review QA validation errors in the logs
2. Fix the issues identified
3. Ensure all acceptance criteria are met

**Tip:** Check the Subtasks tab to see which subtasks may need attention.

---
Generated at: ${new Date().toISOString()}
Source: RDR Batch Processing (Priority 2: Request Changes)
Batch Type: ${batchType}
`;
          writeFileSync(fixRequestPath, feedbackContent);
          feedbackWrittenToMain = true;

        } else if (batchType === 'errors') {
          // PRIORITY 2-3: Request changes or fix technical blockers
          priority = 2;
          action = 'error_fix_request';

          const feedbackContent = `# Fix Request (RDR Batch: errors)

**Errors Detected:**

${fix.feedback || 'See error logs for details.'}

**Action Required:**
1. Check the Logs tab for error stack traces
2. Review the Overview tab for error messages
3. Fix the issues and continue

**Tip:** If this is a build/compilation error, it may be a technical blocker (Priority 3).

---
Generated at: ${new Date().toISOString()}
Source: RDR Batch Processing (Priority 2-3: Fix Errors)
Batch Type: ${batchType}
`;
          writeFileSync(fixRequestPath, feedbackContent);
          feedbackWrittenToMain = true;
        }

        // Also copy QA_FIX_REQUEST.md to worktree (agent runs there, needs to see it)
        if (feedbackWrittenToMain) {
          const worktreeFixPath = path.join(
            resolvedProjectPath, '.auto-claude', 'worktrees', 'tasks', fix.taskId,
            '.auto-claude', 'specs', fix.taskId, 'QA_FIX_REQUEST.md'
          );
          if (existsSync(path.dirname(worktreeFixPath))) {
            try {
              const fixContent = readFileSync(fixRequestPath, 'utf-8');
              writeFileSync(worktreeFixPath, fixContent);
              console.log(`[MCP] Also wrote QA_FIX_REQUEST.md to worktree for ${fix.taskId}`);
            } catch (err) {
              console.warn(`[MCP] Failed to write worktree QA_FIX_REQUEST.md for ${fix.taskId}:`, err);
            }
          }
        }

        // ─────────────────────────────────────────────────────────────────
        // TRIGGER PRIORITY 1: Set status='start_requested'
        // This triggers the file watcher, which:
        // 1. Calls determineResumeStatus() to get target status
        // 2. Moves task from human_review → backlog/in_progress/ai_review
        // 3. Emits task-status-changed event for UI refresh
        // 4. Auto-starts the task
        // ─────────────────────────────────────────────────────────────────

        if (existsSync(planPath)) {
          const plan = JSON.parse(readFileSync(planPath, 'utf-8'));
          plan.status = 'start_requested';
          plan.start_requested_at = new Date().toISOString();
          plan.rdr_batch_type = batchType;
          plan.rdr_priority = priority;
          plan.rdr_iteration = (plan.rdr_iteration || 0) + 1;
          writeFileSync(planPath, JSON.stringify(plan, null, 2));
        }

        // Also update worktree plan status (agent runs in worktree, needs to see start_requested)
        const worktreePlanPath = path.join(
          resolvedProjectPath, '.auto-claude', 'worktrees', 'tasks', fix.taskId,
          '.auto-claude', 'specs', fix.taskId, 'implementation_plan.json'
        );
        if (existsSync(worktreePlanPath)) {
          try {
            const worktreePlan = JSON.parse(readFileSync(worktreePlanPath, 'utf-8'));
            worktreePlan.status = 'start_requested';
            worktreePlan.start_requested_at = new Date().toISOString();
            worktreePlan.rdr_batch_type = batchType;
            worktreePlan.rdr_priority = priority;
            worktreePlan.rdr_iteration = (worktreePlan.rdr_iteration || 0) + 1;
            writeFileSync(worktreePlanPath, JSON.stringify(worktreePlan, null, 2));
            console.log(`[MCP] Also updated worktree plan for ${fix.taskId}`);
          } catch (err) {
            console.warn(`[MCP] Failed to update worktree plan for ${fix.taskId}:`, err);
          }
        }

        results.push({ taskId: fix.taskId, success: true, action, priority });
      } catch (error) {
        results.push({
          taskId: fix.taskId,
          success: false,
          action: 'error',
          priority: 0,
          error: error instanceof Error ? error.message : String(error)
        });
      }
    }

    const successCount = results.filter(r => r.success).length;
    const failCount = results.filter(r => !r.success).length;
    const priorityBreakdown = {
      priority1: results.filter(r => r.priority === 1).length,
      priority2: results.filter(r => r.priority === 2).length,
      priority3: results.filter(r => r.priority === 3).length
    };

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          success: failCount === 0,
          batchType,
          processed: fixes.length,
          succeeded: successCount,
          failed: failCount,
          priorityBreakdown,
          results,
          message: `Processed ${fixes.length} tasks in batch '${batchType}': ${successCount} succeeded, ${failCount} failed. Priority 1 (auto): ${priorityBreakdown.priority1}, Priority 2 (request): ${priorityBreakdown.priority2}, Priority 3 (fix): ${priorityBreakdown.priority3}.`
        }, null, 2)
      }]
    };
  })
);

// ─────────────────────────────────────────────────────────────────────────────
// Tool: trigger_auto_restart
// ─────────────────────────────────────────────────────────────────────────────

server.tool(
  'trigger_auto_restart',
  'Trigger automatic restart with build when prompt loop, crash, or error detected. Only works if auto-restart feature is enabled in settings.',
  {
    reason: z.enum(['stuckRetry_loop', 'crash', 'manual', 'error']).describe('Reason for restart'),
    buildCommand: z.string().optional().describe('Custom build command (default: from settings or "npm run build")')
  },
  withMonitoring('trigger_auto_restart', async ({ reason, buildCommand }) => {
    try {
      // Import dynamically to avoid circular dependencies
      const { readSettingsFile } = await import('../settings-utils.js');
      const { writeFileSync } = await import('fs');
      const { app } = await import('electron');
      const path = await import('path');

      const settings = readSettingsFile();

      if (!settings.autoRestartOnFailure?.enabled) {
        return {
          content: [{
            type: 'text' as const,
            text: JSON.stringify({
              success: false,
              error: 'Auto-restart feature is disabled in settings. Enable it in Settings > General > Auto-Restart on Loop/Crash.'
            })
          }]
        };
      }

      // Write restart marker file
      const restartMarkerPath = path.join(app.getPath('userData'), '.restart-requested');
      writeFileSync(restartMarkerPath, JSON.stringify({
        reason,
        timestamp: new Date().toISOString(),
        triggeredBy: 'mcp_tool'
      }));

      console.log('[MCP] Restart marker written:', restartMarkerPath);

      // Import and call buildAndRestart
      const { buildAndRestart } = await import('../ipc-handlers/restart-handlers.js');
      const cmd = buildCommand || settings.autoRestartOnFailure.buildCommand || 'npm run build';

      // Note: Task state will be saved by checkAndHandleRestart when app restarts and detects marker file
      console.log('[MCP] Triggering build and restart with command:', cmd);

      // Execute build and restart
      const result = await buildAndRestart(cmd);

      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({
            success: result.success,
            error: result.error,
            reason,
            buildCommand: cmd,
            message: result.success
              ? `Build and restart initiated. App will restart after successful build.`
              : `Build failed: ${result.error}`
          }, null, 2)
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : String(error)
          })
        }]
      };
    }
  })
);

// ─────────────────────────────────────────────────────────────────────────────
// Tool: test_force_recovery
// ─────────────────────────────────────────────────────────────────────────────

server.tool(
  'test_force_recovery',
  'Force tasks into recovery mode (yellow stuck outline) for testing RDR detection. Sets forceRecovery flag in task_metadata.json and optionally sets task status to in_progress or ai_review.',
  {
    projectId: z.string().describe('The project ID (UUID)'),
    projectPath: z.string().optional().describe('Fallback filesystem path if projectId UUID not found'),
    taskIds: z.array(z.string()).describe('Array of task/spec IDs to force into recovery'),
    targetBoard: z.enum(['in_progress', 'ai_review']).default('in_progress').describe('Which board the tasks should appear on (in_progress or ai_review)'),
    enable: z.boolean().optional().default(true).describe('Set to false to remove forceRecovery flag (exit recovery mode)')
  },
  withMonitoring('test_force_recovery', async ({ projectId, projectPath, taskIds, targetBoard, enable }) => {
    const { existsSync, writeFileSync, readFileSync, mkdirSync } = await import('fs');
    const path = await import('path');

    const resolved = resolveProjectPath(projectId, projectPath);
    if ('error' in resolved) {
      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({ success: false, error: resolved.error })
        }]
      };
    }

    const resolvedProjectPath = resolved.projectPath;
    const results: Array<{ taskId: string; success: boolean; action: string; error?: string }> = [];

    for (const taskId of taskIds) {
      try {
        const specDir = path.join(resolvedProjectPath, '.auto-claude', 'specs', taskId);

        if (!existsSync(specDir)) {
          results.push({ taskId, success: false, action: 'skip', error: 'Spec directory not found' });
          continue;
        }

        // 1. Update task_metadata.json with forceRecovery flag
        const metadataPath = path.join(specDir, 'task_metadata.json');
        let metadata: Record<string, unknown> = {};
        if (existsSync(metadataPath)) {
          try {
            metadata = JSON.parse(readFileSync(metadataPath, 'utf-8'));
          } catch {
            // Start fresh if parse fails
          }
        }

        if (enable) {
          metadata = { ...metadata, forceRecovery: true };
        } else {
          const { forceRecovery: _, ...rest } = metadata as Record<string, unknown> & { forceRecovery?: boolean };
          metadata = rest;
        }
        writeFileSync(metadataPath, JSON.stringify(metadata, null, 2));

        // 2. Update implementation_plan.json status + metadata.forceRecovery (RDR reads this)
        const planPath = path.join(specDir, 'implementation_plan.json');
        if (existsSync(planPath)) {
          try {
            const plan = JSON.parse(readFileSync(planPath, 'utf-8'));
            if (enable) {
              plan.status = targetBoard;
              // Set old timestamp so RDR recency check doesn't skip (>10 min ago)
              plan.updated_at = new Date(Date.now() - 15 * 60 * 1000).toISOString();
              // Write forceRecovery into plan metadata (RDR reads metadata from plan JSON)
              if (!plan.metadata) plan.metadata = {};
              plan.metadata.forceRecovery = true;
            } else {
              if (plan.metadata) delete plan.metadata.forceRecovery;
            }
            writeFileSync(planPath, JSON.stringify(plan, null, 2));
          } catch {
            // Plan update is best-effort
          }
        }

        // 3. Also update worktree plan if it exists
        const worktreePlanPath = path.join(
          resolvedProjectPath, '.auto-claude', 'worktrees', 'tasks', taskId,
          '.auto-claude', 'specs', taskId, 'implementation_plan.json'
        );
        if (existsSync(worktreePlanPath)) {
          try {
            const worktreePlan = JSON.parse(readFileSync(worktreePlanPath, 'utf-8'));
            if (enable) {
              worktreePlan.status = targetBoard;
              worktreePlan.updated_at = new Date(Date.now() - 15 * 60 * 1000).toISOString();
              if (!worktreePlan.metadata) worktreePlan.metadata = {};
              worktreePlan.metadata.forceRecovery = true;
            } else {
              if (worktreePlan.metadata) delete worktreePlan.metadata.forceRecovery;
            }
            writeFileSync(worktreePlanPath, JSON.stringify(worktreePlan, null, 2));
          } catch {
            // Worktree update is best-effort
          }
        }

        // 4. Also update worktree task_metadata.json if it exists
        const worktreeMetadataPath = path.join(
          resolvedProjectPath, '.auto-claude', 'worktrees', 'tasks', taskId,
          '.auto-claude', 'specs', taskId, 'task_metadata.json'
        );
        if (existsSync(worktreeMetadataPath)) {
          try {
            let worktreeMeta: Record<string, unknown> = {};
            worktreeMeta = JSON.parse(readFileSync(worktreeMetadataPath, 'utf-8'));
            if (enable) {
              worktreeMeta = { ...worktreeMeta, forceRecovery: true };
            } else {
              const { forceRecovery: _, ...rest } = worktreeMeta as Record<string, unknown> & { forceRecovery?: boolean };
              worktreeMeta = rest;
            }
            writeFileSync(worktreeMetadataPath, JSON.stringify(worktreeMeta, null, 2));
          } catch {
            // Worktree metadata update is best-effort
          }
        }

        results.push({
          taskId,
          success: true,
          action: enable
            ? `forceRecovery=true, status=${targetBoard}`
            : 'forceRecovery removed'
        });
      } catch (error) {
        results.push({
          taskId,
          success: false,
          action: 'error',
          error: error instanceof Error ? error.message : String(error)
        });
      }
    }

    const successCount = results.filter(r => r.success).length;

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          success: successCount > 0,
          message: enable
            ? `Forced ${successCount}/${taskIds.length} tasks into recovery mode on ${targetBoard} board. File watcher will pick up changes within 2-3s.`
            : `Removed forceRecovery from ${successCount}/${taskIds.length} tasks.`,
          results
        }, null, 2)
      }]
    };
  })
);

// ─────────────────────────────────────────────────────────────────────────────
// Crash Notification Polling
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Get the crash notification file path based on OS
 */
function getCrashNotificationPath(): string {
  const appDataPath = process.env.APPDATA ||
    (process.platform === 'darwin'
      ? join(homedir(), 'Library', 'Application Support')
      : join(homedir(), '.config'));
  return join(appDataPath, 'auto-claude', 'crash-notification.json');
}

/**
 * Check for crash notification file and send to Claude Code if found
 * This runs periodically to detect crashes reported by the external watchdog
 */
async function checkCrashNotification(): Promise<void> {
  const notificationPath = getCrashNotificationPath();

  if (!existsSync(notificationPath)) {
    return;
  }

  try {
    const content = readFileSync(notificationPath, 'utf-8');
    const notification = JSON.parse(content);

    console.warn('[MCP] 🚨 Crash notification found!');
    console.warn('[MCP] Type:', notification.type);
    console.warn('[MCP] Timestamp:', notification.timestamp);

    // Build the crash message for Claude Code
    const isCrashLoop = notification.type === 'crash_loop';
    const lines: string[] = [];

    if (isCrashLoop) {
      lines.push('[Auto-Claude Crash Recovery] 🔥 CRASH LOOP DETECTED');
      lines.push('');
      lines.push(`**Crash Count:** ${notification.crashCount} crashes in rapid succession`);
      lines.push(`**Restart Attempts:** ${notification.restartCount}`);
      lines.push('**Status:** Restart attempts stopped to prevent infinite loop');
      lines.push('');
      lines.push('**⚠️ IMMEDIATE ACTION REQUIRED:**');
      lines.push('1. Check recent logs below for error patterns');
      lines.push('2. Investigate root cause of crashes');
      lines.push('3. Fix underlying issue before restarting');
      lines.push('4. Manually restart Auto-Claude after fixing the issue');
    } else {
      lines.push('[Auto-Claude Crash Recovery] ⚠️ APP CRASHED');
      lines.push('');
      lines.push(`**Exit Code:** ${notification.exitCode ?? 'N/A'}`);
      lines.push(`**Signal:** ${notification.signal ?? 'N/A'}`);
      lines.push(`**Timestamp:** ${notification.timestamp}`);
      lines.push(`**Auto-Restart:** ${notification.autoRestart ? 'Yes (restarting in 2s)' : 'No'}`);
      lines.push(`**Restart Attempt:** ${notification.restartCount}`);
    }

    lines.push('');
    lines.push('---');
    lines.push('');
    lines.push('**Recent Logs (Last 20 lines):**');
    lines.push('```');
    if (notification.logs && Array.isArray(notification.logs)) {
      notification.logs.slice(-20).forEach((log: string) => lines.push(log));
    } else {
      lines.push('No logs available');
    }
    lines.push('```');
    lines.push('');
    lines.push('---');
    lines.push('');
    lines.push('**Recovery Actions:**');
    if (isCrashLoop) {
      lines.push('- ❌ Auto-restart disabled due to crash loop');
      lines.push('- 🔍 Investigate the root cause in the logs above');
      lines.push('- 🔧 Fix the issue in Auto-Claude code');
      lines.push('- 🔄 Use Priority 5 (Build & Restart) if needed');
    } else {
      lines.push('- ✅ Auto-Claude should restart automatically');
      lines.push('- 🔍 Use RDR to check task status and resume interrupted tasks');
      lines.push('- 📋 Check if any tasks were in progress when crash occurred');
    }
    lines.push('');
    lines.push('**Settings Location:**');
    lines.push('- Windows: `%APPDATA%\\auto-claude\\settings.json`');
    lines.push('- macOS: `~/Library/Application Support/auto-claude/settings.json`');
    lines.push('- Linux: `~/.config/auto-claude/settings.json`');

    const message = lines.join('\n');

    // Log the full message to stderr so it appears in Claude Code's MCP logs
    console.warn('[MCP] Crash notification content:');
    console.warn(message);

    // Send as a server notification (if the SDK supports it)
    // For now, we'll log it and the message will be visible in MCP logs
    // The user can also use get_rdr_batches which will show crash info

    // Delete the notification file after processing
    unlinkSync(notificationPath);
    console.warn('[MCP] ✅ Crash notification processed and deleted');

  } catch (error) {
    console.error('[MCP] Failed to process crash notification:', error);
    // Try to delete the file even on error to avoid repeated failures
    try {
      unlinkSync(notificationPath);
    } catch {
      // Ignore deletion errors
    }
  }
}

/**
 * Start polling for crash notifications
 */
let crashPollInterval: ReturnType<typeof setInterval> | null = null;

function startCrashNotificationPolling(): void {
  // Check immediately on startup
  checkCrashNotification().catch(console.error);

  // Then poll every 10 seconds
  crashPollInterval = setInterval(() => {
    checkCrashNotification().catch(console.error);
  }, 10000);

  console.warn('[MCP] Crash notification polling started (every 10s)');
}

function stopCrashNotificationPolling(): void {
  if (crashPollInterval) {
    clearInterval(crashPollInterval);
    crashPollInterval = null;
    console.warn('[MCP] Crash notification polling stopped');
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Start Server
// ─────────────────────────────────────────────────────────────────────────────

async function main() {
  console.warn('[MCP] Auto-Claude MCP Server starting...');

  const transport = new StdioServerTransport();

  await server.connect(transport);

  console.warn('[MCP] Auto-Claude MCP Server connected via stdio');

  // Start crash notification polling for LLM Manager
  startCrashNotificationPolling();

  // Handle graceful shutdown
  process.on('SIGINT', async () => {
    console.warn('[MCP] Received SIGINT, shutting down...');
    stopCrashNotificationPolling();
    await server.close();
    process.exit(0);
  });

  process.on('SIGTERM', async () => {
    console.warn('[MCP] Received SIGTERM, shutting down...');
    stopCrashNotificationPolling();
    await server.close();
    process.exit(0);
  });
}

main().catch((error) => {
  console.error('[MCP] Fatal error:', error);
  process.exit(1);
});
