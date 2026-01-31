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

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

import {
  createTask,
  listTasks,
  getTaskStatus,
  startTask,
  executeCommand,
  pollTaskStatuses
} from './utils.js';
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
    description: z.string().describe('Detailed description of the task to implement'),
    title: z.string().optional().describe('Optional title for the task (auto-generated if empty)'),
    options: TaskOptionsSchema.describe('Optional configuration for models, thinking, review, and classification')
  },
  async ({ projectId, description, title, options }) => {
    const result = await createTask(projectId, description, title, options as TaskOptions);

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
  }
);

// ─────────────────────────────────────────────────────────────────────────────
// Tool: list_tasks
// ─────────────────────────────────────────────────────────────────────────────

server.tool(
  'list_tasks',
  'List all tasks for a project, optionally filtered by status',
  {
    projectId: z.string().describe('The project ID (UUID) to list tasks from'),
    status: TaskStatusSchema.optional().describe('Optional status filter')
  },
  async ({ projectId, status }) => {
    const result = listTasks(projectId, status as TaskStatus | undefined);

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
    taskId: z.string().describe('The task ID (spec folder name)')
  },
  async ({ projectId, taskId }) => {
    const result = getTaskStatus(projectId, taskId);

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
    taskId: z.string().describe('The task ID (spec folder name) to start')
  },
  async ({ projectId, taskId }) => {
    const result = startTask(projectId, taskId);

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
    tasks: z.array(z.object({
      description: z.string(),
      title: z.string().optional(),
      options: TaskOptionsSchema
    })).describe('Array of task definitions to create'),
    options: TaskOptionsSchema.describe('Default options applied to all tasks'),
    startImmediately: z.boolean().optional().default(true).describe('Whether to start tasks after creation')
  },
  async ({ projectId, tasks, options, startImmediately }) => {
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
        mergedOptions
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
    taskIds: z.array(z.string()).describe('Array of task IDs to monitor'),
    onComplete: OnCompleteSchema.describe('Optional command to execute when all tasks reach Human Review'),
    pollIntervalMs: z.number().optional().default(30000).describe('How often to check status (default: 30000ms)'),
    timeoutMs: z.number().optional().describe('Maximum time to wait (no default = wait indefinitely)')
  },
  async ({ projectId, taskIds, onComplete, pollIntervalMs, timeoutMs }) => {
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
    projectId: z.string().describe('The project ID (UUID)')
  },
  async ({ projectId }) => {
    const result = await listTasks(projectId);

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
      if (task.status !== 'human_review') return false;

      // JSON error tasks
      if (task.description?.startsWith('__JSON_ERROR__:')) return true;

      // Tasks with errors or QA rejected
      if (task.reviewReason === 'errors' || task.reviewReason === 'qa_rejected') return true;

      // Incomplete tasks (subtasks not all completed)
      if (task.subtasks && task.subtasks.some((s: { status: string }) => s.status !== 'completed')) return true;

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
    taskId: z.string().describe('The task/spec ID')
  },
  async ({ projectId, taskId }) => {
    const statusResult = await getTaskStatus(projectId, taskId);

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
  }
);

// ─────────────────────────────────────────────────────────────────────────────
// Tool: recover_stuck_task
// ─────────────────────────────────────────────────────────────────────────────

server.tool(
  'recover_stuck_task',
  'Trigger recovery for a stuck task (equivalent to clicking Recover button)',
  {
    projectId: z.string().describe('The project ID (UUID)'),
    taskId: z.string().describe('The task/spec ID'),
    autoRestart: z.boolean().optional().default(true).describe('Whether to auto-restart after recovery')
  },
  async ({ projectId, taskId, autoRestart }) => {
    // Note: Recovery requires IPC access which is only available within Electron context
    // When running as standalone MCP server, we can only provide guidance
    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          success: false,
          note: 'Task recovery requires the MCP server to run within the Electron app context. ' +
                'To recover this task: ' +
                '1. Open the Auto-Claude UI ' +
                '2. Find task ' + taskId + ' in Human Review ' +
                '3. Click the "Recover Task" button ' +
                'Alternatively, enable RDR toggle in the Kanban header to auto-recover stuck tasks.',
          taskId,
          autoRestart
        }, null, 2)
      }]
    };
  }
);

// ─────────────────────────────────────────────────────────────────────────────
// Tool: submit_task_fix_request
// ─────────────────────────────────────────────────────────────────────────────

server.tool(
  'submit_task_fix_request',
  'Submit a fix request for a task (equivalent to Request Changes)',
  {
    projectId: z.string().describe('The project ID (UUID)'),
    taskId: z.string().describe('The task/spec ID'),
    feedback: z.string().describe('Description of what needs to be fixed')
  },
  async ({ projectId, taskId, feedback }) => {
    // Note: Submitting fix requests requires IPC access which is only available within Electron context
    // When running as standalone MCP server, we can only provide guidance
    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          success: false,
          note: 'Submitting fix requests requires the MCP server to run within the Electron app context. ' +
                'To submit this fix request: ' +
                '1. Open the Auto-Claude UI ' +
                '2. Find task ' + taskId + ' in Human Review ' +
                '3. Enter the following in the Request Changes field: ' +
                feedback,
          taskId,
          feedback
        }, null, 2)
      }]
    };
  }
);

// ─────────────────────────────────────────────────────────────────────────────
// Tool: get_task_logs
// ─────────────────────────────────────────────────────────────────────────────

server.tool(
  'get_task_logs',
  'Get detailed phase logs for a task (planning, coding, validation)',
  {
    projectId: z.string().describe('The project ID (UUID)'),
    taskId: z.string().describe('The task/spec ID'),
    phase: z.enum(['planning', 'coding', 'validation']).optional().describe('Specific phase to get logs for (all phases if not specified)'),
    lastN: z.number().optional().default(50).describe('Number of recent log entries to return')
  },
  async ({ projectId, taskId, phase, lastN }) => {
    // Note: Full log access requires IPC which is only available within Electron context
    // When running as standalone MCP server, we provide limited info
    const statusResult = await getTaskStatus(projectId, taskId);

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
// Start Server
// ─────────────────────────────────────────────────────────────────────────────

async function main() {
  console.warn('[MCP] Auto-Claude MCP Server starting...');

  const transport = new StdioServerTransport();

  await server.connect(transport);

  console.warn('[MCP] Auto-Claude MCP Server connected via stdio');

  // Handle graceful shutdown
  process.on('SIGINT', async () => {
    console.warn('[MCP] Received SIGINT, shutting down...');
    await server.close();
    process.exit(0);
  });

  process.on('SIGTERM', async () => {
    console.warn('[MCP] Received SIGTERM, shutting down...');
    await server.close();
    process.exit(0);
  });
}

main().catch((error) => {
  console.error('[MCP] Fatal error:', error);
  process.exit(1);
});
