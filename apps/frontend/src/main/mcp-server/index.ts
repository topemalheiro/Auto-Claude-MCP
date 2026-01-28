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
  'Wait for tasks to reach Human Review status, then optionally execute a command (like shutdown)',
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

    // Execute on-complete command if provided and all tasks completed
    if (pollResult.completed && onComplete?.command) {
      console.warn(`[MCP] All tasks reached Human Review, scheduling command: ${onComplete.command}`);

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
