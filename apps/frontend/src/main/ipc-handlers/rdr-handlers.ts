/**
 * RDR (Recover Debug Resend) Handlers
 *
 * Handles automatic recovery, debugging, and resending of stuck/errored tasks.
 * Works in conjunction with MCP tools for Claude Manager to analyze and fix tasks.
 *
 * Processing modes:
 * - Batch 1: JSON Errors → Auto-fix JSON structure
 * - Batch 2: Incomplete Tasks → Auto-submit "Request Changes" to resume
 * - Batch 3: QA Rejected / Other Errors → Queue for MCP/Claude Code analysis
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
  subtasks?: Array<{ status: string; name?: string }>;
}

interface RdrBatch {
  type: 'json_error' | 'incomplete' | 'qa_rejected' | 'errors';
  taskIds: string[];
  tasks: TaskInfo[];
}

interface RdrProcessingSummary {
  processed: number;
  jsonFixed: number;
  fixSubmitted: number;
  queuedForMcp: number;
  results: RdrProcessResult[];
  batches: Array<{ type: string; count: number }>;
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
 * Get all task info for multiple tasks from project store
 */
async function getAllTaskInfo(projectId: string, taskIds: string[]): Promise<TaskInfo[]> {
  const tasksResult = await projectStore.getTasks(projectId);

  if (!tasksResult.success || !tasksResult.data) {
    return [];
  }

  return tasksResult.data
    .filter(t => taskIds.includes(t.specId) || taskIds.includes(t.id))
    .map(task => ({
      specId: task.specId,
      status: task.status,
      reviewReason: task.reviewReason,
      description: task.description,
      subtasks: task.subtasks
    }));
}

/**
 * Get implementation plan path for a task
 */
function getPlanPath(projectPath: string, specId: string): string {
  return path.join(projectPath, '.auto-claude', 'specs', specId, 'implementation_plan.json');
}

/**
 * Categorize tasks into batches by problem type
 */
function categorizeTasks(tasks: TaskInfo[]): RdrBatch[] {
  const batches: RdrBatch[] = [];

  // Batch 1: JSON Errors (tasks with JSON parse error in description)
  const jsonErrors = tasks.filter(t => t.description?.startsWith(JSON_ERROR_PREFIX));
  if (jsonErrors.length > 0) {
    batches.push({ type: 'json_error', taskIds: jsonErrors.map(t => t.specId), tasks: jsonErrors });
    console.log(`[RDR] Batch 1 - JSON Errors: ${jsonErrors.length} tasks`);
  }

  // Batch 2: Incomplete Tasks (has subtasks but not all completed, NOT an error state)
  const incomplete = tasks.filter(t =>
    t.status === 'human_review' &&
    t.reviewReason !== 'errors' &&
    !t.description?.startsWith(JSON_ERROR_PREFIX) &&
    t.subtasks &&
    t.subtasks.length > 0 &&
    t.subtasks.some(s => s.status !== 'completed')
  );
  if (incomplete.length > 0) {
    batches.push({ type: 'incomplete', taskIds: incomplete.map(t => t.specId), tasks: incomplete });
    console.log(`[RDR] Batch 2 - Incomplete Tasks: ${incomplete.length} tasks`);
  }

  // Batch 3: QA Rejected
  const qaRejected = tasks.filter(t =>
    t.reviewReason === 'qa_rejected' &&
    !t.description?.startsWith(JSON_ERROR_PREFIX)
  );
  if (qaRejected.length > 0) {
    batches.push({ type: 'qa_rejected', taskIds: qaRejected.map(t => t.specId), tasks: qaRejected });
    console.log(`[RDR] Batch 3 - QA Rejected: ${qaRejected.length} tasks`);
  }

  // Batch 4: Other Errors (not JSON errors)
  const errors = tasks.filter(t =>
    t.reviewReason === 'errors' &&
    !t.description?.startsWith(JSON_ERROR_PREFIX)
  );
  if (errors.length > 0) {
    batches.push({ type: 'errors', taskIds: errors.map(t => t.specId), tasks: errors });
    console.log(`[RDR] Batch 4 - Other Errors: ${errors.length} tasks`);
  }

  return batches;
}

/**
 * Submit "Request Changes" for a task (auto-resume with feedback)
 * This writes QA_FIX_REQUEST.md and sets status to start_requested
 */
async function submitRequestChanges(
  projectPath: string,
  taskId: string,
  feedback: string
): Promise<RdrProcessResult> {
  try {
    const specDir = path.join(projectPath, '.auto-claude', 'specs', taskId);
    const fixRequestPath = path.join(specDir, 'QA_FIX_REQUEST.md');
    const planPath = path.join(specDir, 'implementation_plan.json');

    if (!existsSync(specDir)) {
      return { taskId, action: 'error', error: 'Spec directory not found' };
    }

    // Write fix request file
    const content = `# Fix Request (RDR Auto-Generated)

${feedback}

---
Generated at: ${new Date().toISOString()}
Source: RDR Auto-Recovery System
`;
    writeFileSync(fixRequestPath, content);
    console.log(`[RDR] Wrote fix request to ${fixRequestPath}`);

    // Update implementation_plan.json to trigger restart
    if (existsSync(planPath)) {
      const plan = JSON.parse(readFileSync(planPath, 'utf-8'));
      plan.status = 'start_requested';
      plan.start_requested_at = new Date().toISOString();
      plan.rdr_feedback = feedback;
      plan.rdr_iteration = (plan.rdr_iteration || 0) + 1;
      writeFileSync(planPath, JSON.stringify(plan, null, 2));
      console.log(`[RDR] Set status=start_requested for task ${taskId}`);
    }

    return { taskId, action: 'fix_submitted', reason: feedback };
  } catch (error) {
    console.error(`[RDR] Failed to submit fix request for ${taskId}:`, error);
    return { taskId, action: 'error', error: error instanceof Error ? error.message : String(error) };
  }
}

/**
 * Process JSON error batch - auto-fix JSON files
 */
async function processJsonErrorBatch(
  batch: RdrBatch,
  projectPath: string,
  mainWindow: BrowserWindow | null,
  projectId: string
): Promise<RdrProcessResult[]> {
  const results: RdrProcessResult[] = [];

  for (const task of batch.tasks) {
    const planPath = getPlanPath(projectPath, task.specId);

    if (existsSync(planPath)) {
      const rawContent = readFileSync(planPath, 'utf-8');
      const fixedContent = attemptJsonFix(rawContent);

      if (fixedContent && fixedContent !== rawContent) {
        writeFileSync(planPath, fixedContent);
        console.log(`[RDR] Fixed JSON for task ${task.specId}`);

        // Notify renderer to refresh task list
        if (mainWindow) {
          mainWindow.webContents.send(IPC_CHANNELS.TASK_LIST_REFRESH, projectId);
        }

        results.push({ taskId: task.specId, action: 'json_fixed' });
      } else if (!fixedContent) {
        results.push({ taskId: task.specId, action: 'json_unfixable', reason: 'Could not auto-fix JSON structure' });
      } else {
        results.push({ taskId: task.specId, action: 'json_fixed', reason: 'JSON was already valid' });
      }
    } else {
      results.push({ taskId: task.specId, action: 'json_unfixable', reason: 'Plan file not found' });
    }
  }

  return results;
}

/**
 * Process incomplete tasks batch - auto-submit Request Changes to resume
 */
async function processIncompleteBatch(
  batch: RdrBatch,
  projectPath: string,
  mainWindow: BrowserWindow | null,
  projectId: string
): Promise<RdrProcessResult[]> {
  const results: RdrProcessResult[] = [];

  for (const task of batch.tasks) {
    const completedCount = task.subtasks?.filter(s => s.status === 'completed').length || 0;
    const totalCount = task.subtasks?.length || 0;
    const percentage = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

    const feedback = `## Resume Task (RDR Auto-Recovery)

**Progress:** ${completedCount}/${totalCount} subtasks completed (${percentage}%)

**Action Required:** Continue implementation from where it stopped. Complete the remaining ${totalCount - completedCount} subtasks.

**Note:** This task was automatically resumed by the RDR system because it had incomplete subtasks.`;

    const result = await submitRequestChanges(projectPath, task.specId, feedback);
    results.push(result);

    // Notify renderer
    if (mainWindow) {
      mainWindow.webContents.send(IPC_CHANNELS.RDR_TASK_PROCESSED, {
        projectId,
        taskId: task.specId,
        result
      });
    }
  }

  return results;
}

/**
 * Process QA rejected / error batches - queue for MCP/Claude Code analysis
 */
async function processMcpBatch(
  batch: RdrBatch,
  projectPath: string,
  mainWindow: BrowserWindow | null,
  projectId: string
): Promise<RdrProcessResult[]> {
  const results: RdrProcessResult[] = [];

  // These batches need intelligent analysis - emit event for MCP/Claude Code
  console.log(`[RDR] Batch type=${batch.type} queued for MCP/Claude Code analysis: ${batch.taskIds.length} tasks`);

  // Emit event for MCP consumers to pick up
  if (mainWindow) {
    mainWindow.webContents.send(IPC_CHANNELS.RDR_BATCH_READY, {
      projectId,
      batchType: batch.type,
      taskIds: batch.taskIds,
      taskCount: batch.tasks.length,
      tasks: batch.tasks.map(t => ({
        specId: t.specId,
        reviewReason: t.reviewReason,
        description: t.description?.substring(0, 200), // Truncate for event
        subtasksTotal: t.subtasks?.length || 0,
        subtasksCompleted: t.subtasks?.filter(s => s.status === 'completed').length || 0
      }))
    });
  }

  for (const task of batch.tasks) {
    results.push({
      taskId: task.specId,
      action: 'no_action',
      reason: `Queued for Claude Code analysis via MCP (batch: ${batch.type})`
    });
  }

  return results;
}

/**
 * Register RDR IPC handlers
 */
export function registerRdrHandlers(): void {
  console.log('[RDR] Registering RDR handlers');

  ipcMain.handle(
    IPC_CHANNELS.TRIGGER_RDR_PROCESSING,
    async (event, projectId: string, taskIds: string[]): Promise<IPCResult<RdrProcessingSummary>> => {
      console.log(`[RDR] Processing ${taskIds.length} tasks for project ${projectId}`);

      // Get project path
      const project = projectStore.getProject(projectId);

      if (!project) {
        return {
          success: false,
          error: 'Project not found'
        };
      }

      // Get main window for sending events
      const mainWindow = BrowserWindow.getAllWindows()[0] || null;

      // Get all task info
      const tasks = await getAllTaskInfo(projectId, taskIds);
      if (tasks.length === 0) {
        return {
          success: false,
          error: 'No tasks found'
        };
      }

      // Categorize tasks into batches
      const batches = categorizeTasks(tasks);
      console.log(`[RDR] Categorized into ${batches.length} batches`);

      // Process each batch
      const allResults: RdrProcessResult[] = [];
      let jsonFixedCount = 0;
      let fixSubmittedCount = 0;
      let queuedForMcpCount = 0;
      const batchSummaries: Array<{ type: string; count: number }> = [];

      for (const batch of batches) {
        let results: RdrProcessResult[] = [];

        switch (batch.type) {
          case 'json_error':
            // Auto-fix JSON errors
            results = await processJsonErrorBatch(batch, project.path, mainWindow, projectId);
            jsonFixedCount += results.filter(r => r.action === 'json_fixed').length;
            break;

          case 'incomplete':
            // Auto-submit Request Changes for incomplete tasks
            results = await processIncompleteBatch(batch, project.path, mainWindow, projectId);
            fixSubmittedCount += results.filter(r => r.action === 'fix_submitted').length;
            break;

          case 'qa_rejected':
          case 'errors':
            // Queue for MCP/Claude Code analysis
            results = await processMcpBatch(batch, project.path, mainWindow, projectId);
            queuedForMcpCount += results.length;
            break;
        }

        allResults.push(...results);
        batchSummaries.push({ type: batch.type, count: results.length });

        // Emit batch processed event
        if (mainWindow) {
          mainWindow.webContents.send(IPC_CHANNELS.RDR_BATCH_PROCESSED, {
            projectId,
            batchType: batch.type,
            results
          });
        }
      }

      // Emit completion event
      if (mainWindow) {
        mainWindow.webContents.send(IPC_CHANNELS.RDR_PROCESSING_COMPLETE, {
          projectId,
          processed: taskIds.length,
          jsonFixed: jsonFixedCount,
          fixSubmitted: fixSubmittedCount,
          queuedForMcp: queuedForMcpCount,
          batches: batchSummaries,
          results: allResults
        });
      }

      console.log(`[RDR] Processing complete: ${taskIds.length} tasks`);
      console.log(`[RDR]   - JSON fixed: ${jsonFixedCount}`);
      console.log(`[RDR]   - Fix submitted (incomplete): ${fixSubmittedCount}`);
      console.log(`[RDR]   - Queued for MCP: ${queuedForMcpCount}`);

      return {
        success: true,
        data: {
          processed: taskIds.length,
          jsonFixed: jsonFixedCount,
          fixSubmitted: fixSubmittedCount,
          queuedForMcp: queuedForMcpCount,
          results: allResults,
          batches: batchSummaries
        }
      };
    }
  );
}
