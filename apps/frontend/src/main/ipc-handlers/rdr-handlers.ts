/**
 * RDR (Recover Debug Resend) Handlers
 *
 * Handles automatic recovery, debugging, and resending of stuck/errored tasks.
 * Works in conjunction with MCP tools for Claude Manager to analyze and fix tasks.
 */

import { ipcMain, BrowserWindow } from 'electron';
import { readFileSync, writeFileSync, existsSync } from 'fs';
import * as path from 'path';
import { IPC_CHANNELS } from '../../shared/constants/ipc';
import type { IPCResult } from '../../shared/types';
import { JSON_ERROR_PREFIX } from '../../shared/constants/task';
import { projectStore } from '../project-store';

// Types for RDR processing
interface RdrProcessResult {
  taskId: string;
  action: 'json_fixed' | 'json_unfixable' | 'recovery_triggered' | 'fix_submitted' | 'resumed' | 'no_action' | 'error';
  reason?: string;
  error?: string;
}

interface TaskInfo {
  specId: string;
  status: string;
  reviewReason?: string;
  description?: string;
  subtasks?: Array<{ status: string }>;
}

/**
 * Attempt to fix common JSON errors in implementation_plan.json
 */
function attemptJsonFix(rawContent: string): string | null {
  try {
    // First, try parsing as-is
    JSON.parse(rawContent);
    return rawContent; // Already valid
  } catch {
    // Attempt fixes
    let fixed = rawContent;

    // Remove trailing commas before } or ]
    fixed = fixed.replace(/,(\s*[}\]])/g, '$1');

    // Count braces and add missing ones
    const openBraces = (fixed.match(/{/g) || []).length;
    const closeBraces = (fixed.match(/}/g) || []).length;
    if (openBraces > closeBraces) {
      fixed += '}'.repeat(openBraces - closeBraces);
    }

    // Count brackets
    const openBrackets = (fixed.match(/\[/g) || []).length;
    const closeBrackets = (fixed.match(/]/g) || []).length;
    if (openBrackets > closeBrackets) {
      fixed += ']'.repeat(openBrackets - closeBrackets);
    }

    try {
      JSON.parse(fixed);
      return fixed;
    } catch {
      return null; // Could not fix
    }
  }
}

/**
 * Get task info from project store
 */
async function getTaskInfo(projectId: string, taskId: string): Promise<TaskInfo | null> {
  const tasks = await projectStore.getTasks(projectId);

  if (!tasks.success || !tasks.data) {
    return null;
  }

  const task = tasks.data.find(t => t.specId === taskId || t.id === taskId);
  if (!task) {
    return null;
  }

  return {
    specId: task.specId,
    status: task.status,
    reviewReason: task.reviewReason,
    description: task.description,
    subtasks: task.subtasks
  };
}

/**
 * Get implementation plan path for a task
 */
function getPlanPath(projectPath: string, specId: string): string {
  return path.join(projectPath, '.auto-claude', 'specs', specId, 'implementation_plan.json');
}

/**
 * Process a single task for RDR intervention
 */
async function processTaskForRdr(
  projectId: string,
  projectPath: string,
  taskId: string,
  mainWindow: BrowserWindow | null
): Promise<RdrProcessResult> {
  try {
    const taskInfo = await getTaskInfo(projectId, taskId);

    if (!taskInfo) {
      return { taskId, action: 'error', error: 'Task not found' };
    }

    // Check for JSON parse error
    if (taskInfo.description?.startsWith(JSON_ERROR_PREFIX)) {
      const planPath = getPlanPath(projectPath, taskInfo.specId);

      if (existsSync(planPath)) {
        const rawContent = readFileSync(planPath, 'utf-8');
        const fixedContent = attemptJsonFix(rawContent);

        if (fixedContent && fixedContent !== rawContent) {
          writeFileSync(planPath, fixedContent);
          console.log(`[RDR] Fixed JSON for task ${taskId}`);

          // Notify renderer to refresh task list
          if (mainWindow) {
            mainWindow.webContents.send(IPC_CHANNELS.TASK_LIST_REFRESH, projectId);
          }

          return { taskId, action: 'json_fixed' };
        } else if (!fixedContent) {
          return { taskId, action: 'json_unfixable', reason: 'Could not auto-fix JSON structure' };
        }
      }

      return { taskId, action: 'json_unfixable', reason: 'Plan file not found' };
    }

    // Check for incomplete task (subtasks not all completed)
    const hasIncompleteSubtasks = taskInfo.subtasks?.some(s => s.status !== 'completed');
    if (hasIncompleteSubtasks && taskInfo.status === 'human_review') {
      // For now, log that this task needs MCP intervention
      // The actual fix request will be submitted via MCP tools
      console.log(`[RDR] Task ${taskId} has incomplete subtasks - needs MCP intervention`);
      return {
        taskId,
        action: 'no_action',
        reason: 'Task has incomplete subtasks - use MCP tools to analyze and submit fix request'
      };
    }

    // Check for QA rejected
    if (taskInfo.reviewReason === 'qa_rejected') {
      console.log(`[RDR] Task ${taskId} was QA rejected - needs MCP intervention`);
      return {
        taskId,
        action: 'no_action',
        reason: 'Task was QA rejected - use MCP tools to analyze and submit fix request'
      };
    }

    // Check for error state
    if (taskInfo.reviewReason === 'errors') {
      console.log(`[RDR] Task ${taskId} has errors - needs MCP intervention`);
      return {
        taskId,
        action: 'no_action',
        reason: 'Task has errors - use MCP tools to analyze and submit fix request'
      };
    }

    return { taskId, action: 'no_action', reason: 'Task does not need intervention' };
  } catch (error) {
    console.error(`[RDR] Error processing task ${taskId}:`, error);
    return {
      taskId,
      action: 'error',
      error: error instanceof Error ? error.message : String(error)
    };
  }
}

/**
 * Register RDR IPC handlers
 */
export function registerRdrHandlers(): void {
  console.log('[RDR] Registering RDR handlers');

  ipcMain.handle(
    IPC_CHANNELS.TRIGGER_RDR_PROCESSING,
    async (event, projectId: string, taskIds: string[]): Promise<IPCResult<{ processed: number; results: RdrProcessResult[] }>> => {
      console.log(`[RDR] Processing ${taskIds.length} tasks for project ${projectId}`);

      // Get project path
      const project = projectStore.getProject(projectId);

      if (!project) {
        return {
          success: false,
          error: 'Project not found'
        };
      }

      // Get main window for sending refresh events
      const mainWindow = BrowserWindow.getAllWindows()[0] || null;

      // Process each task
      const results: RdrProcessResult[] = [];
      let jsonFixedCount = 0;

      for (const taskId of taskIds) {
        const result = await processTaskForRdr(projectId, project.path, taskId, mainWindow);
        results.push(result);

        if (result.action === 'json_fixed') {
          jsonFixedCount++;
        }

        // Emit progress event
        if (mainWindow) {
          mainWindow.webContents.send(IPC_CHANNELS.RDR_TASK_PROCESSED, {
            projectId,
            taskId,
            result
          });
        }
      }

      // Emit completion event
      if (mainWindow) {
        mainWindow.webContents.send(IPC_CHANNELS.RDR_PROCESSING_COMPLETE, {
          projectId,
          processed: taskIds.length,
          jsonFixed: jsonFixedCount,
          results
        });
      }

      console.log(`[RDR] Processing complete: ${taskIds.length} tasks, ${jsonFixedCount} JSON fixed`);

      return {
        success: true,
        data: {
          processed: taskIds.length,
          results
        }
      };
    }
  );
}
