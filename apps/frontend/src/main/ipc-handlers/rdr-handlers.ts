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
import { readFileSync, writeFileSync, existsSync, unlinkSync } from 'fs';
import * as path from 'path';
import { IPC_CHANNELS } from '../../shared/constants/ipc';
import type { IPCResult } from '../../shared/types';
import { JSON_ERROR_PREFIX } from '../../shared/constants/task';
import { projectStore } from '../project-store';

// ============================================================================
// Timer-Based Batching State
// ============================================================================

// Pending tasks collected before timer fires
interface PendingRdrTask {
  projectId: string;
  task: TaskInfo;
}

let pendingTasks: PendingRdrTask[] = [];
let batchTimer: NodeJS.Timeout | null = null;
const BATCH_COLLECTION_WINDOW_MS = 30000; // 30 seconds

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
function getAllTaskInfo(projectId: string, taskIds: string[]): TaskInfo[] {
  const tasks = projectStore.getTasks(projectId);

  if (!tasks || tasks.length === 0) {
    return [];
  }

  return tasks
    .filter((t): t is typeof t & { specId: string } => taskIds.includes(t.specId) || taskIds.includes(t.id))
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
 * Writes a signal file that Claude Code can pick up via the get_rdr_batches MCP tool
 */
async function processMcpBatch(
  batch: RdrBatch,
  projectPath: string,
  mainWindow: BrowserWindow | null,
  projectId: string,
  allMcpBatches?: RdrBatch[]
): Promise<RdrProcessResult[]> {
  const results: RdrProcessResult[] = [];

  // These batches need intelligent analysis
  console.log(`[RDR] Batch type=${batch.type} queued for MCP/Claude Code analysis: ${batch.taskIds.length} tasks`);

  // Write signal file for Claude Code to pick up
  // If allMcpBatches is provided, write all of them (batched call)
  // Otherwise, write just this batch (individual call)
  const batchesToWrite = allMcpBatches || [batch];
  writeRdrSignalFile(projectPath, projectId, batchesToWrite);

  // Emit event for renderer notification
  if (mainWindow) {
    mainWindow.webContents.send(IPC_CHANNELS.RDR_BATCH_READY, {
      projectId,
      batchType: batch.type,
      taskIds: batch.taskIds,
      taskCount: batch.tasks.length,
      signalWritten: true,
      tasks: batch.tasks.map(t => ({
        specId: t.specId,
        reviewReason: t.reviewReason,
        description: t.description?.substring(0, 200),
        subtasksTotal: t.subtasks?.length || 0,
        subtasksCompleted: t.subtasks?.filter(s => s.status === 'completed').length || 0
      }))
    });
  }

  for (const task of batch.tasks) {
    results.push({
      taskId: task.specId,
      action: 'no_action',
      reason: `Queued for Claude Code analysis via MCP (batch: ${batch.type}). Signal file written.`
    });
  }

  return results;
}

// ============================================================================
// Timer-Based Batching Functions
// ============================================================================

/**
 * Generate a prompt for Claude Code to analyze the batch
 */
function generateBatchPrompt(batches: RdrBatch[]): string {
  const lines: string[] = [
    '# RDR Batch Analysis Request',
    '',
    `**Timestamp:** ${new Date().toISOString()}`,
    `**Total Batches:** ${batches.length}`,
    '',
    '## Tasks Needing Analysis',
    ''
  ];

  for (const batch of batches) {
    lines.push(`### Batch: ${batch.type} (${batch.taskIds.length} tasks)`);
    lines.push('');

    for (const task of batch.tasks) {
      lines.push(`- **${task.specId}**: ${task.description?.substring(0, 100) || 'No description'}`);
      if (task.reviewReason) {
        lines.push(`  - Review Reason: ${task.reviewReason}`);
      }
      if (task.subtasks && task.subtasks.length > 0) {
        const completed = task.subtasks.filter(s => s.status === 'completed').length;
        lines.push(`  - Subtasks: ${completed}/${task.subtasks.length} completed`);
      }
    }
    lines.push('');
  }

  lines.push('## Action Required');
  lines.push('');
  lines.push('1. Call `get_rdr_batches` to get full task details');
  lines.push('2. Analyze error logs and QA reports for each task');
  lines.push('3. Call `process_rdr_batch` with fix requests for each batch');
  lines.push('');

  return lines.join('\n');
}

/**
 * Write signal file for Claude Code to pick up via MCP
 */
function writeRdrSignalFile(
  projectPath: string,
  projectId: string,
  batches: RdrBatch[]
): void {
  const signalDir = path.join(projectPath, '.auto-claude');
  const signalPath = path.join(signalDir, 'rdr-pending.json');

  const signal = {
    timestamp: new Date().toISOString(),
    projectId,
    batches: batches.map(b => ({
      type: b.type,
      taskCount: b.taskIds.length,
      taskIds: b.taskIds,
      tasks: b.tasks.map(t => ({
        specId: t.specId,
        description: t.description?.substring(0, 200),
        reviewReason: t.reviewReason,
        subtasksCompleted: t.subtasks?.filter(s => s.status === 'completed').length || 0,
        subtasksTotal: t.subtasks?.length || 0
      }))
    })),
    prompt: generateBatchPrompt(batches)
  };

  writeFileSync(signalPath, JSON.stringify(signal, null, 2));
  console.log(`[RDR] Wrote signal file: ${signalPath}`);
  console.log(`[RDR] Signal contains ${batches.length} batches with ${batches.reduce((sum, b) => sum + b.taskIds.length, 0)} total tasks`);
}

/**
 * Read and clear the RDR signal file if it exists
 * Returns the signal data or null if no file exists
 */
export function readAndClearSignalFile(projectPath: string): {
  timestamp: string;
  projectId: string;
  batches: Array<{
    type: string;
    taskCount: number;
    taskIds: string[];
    tasks: Array<{
      specId: string;
      description?: string;
      reviewReason?: string;
      subtasksCompleted: number;
      subtasksTotal: number;
    }>;
  }>;
  prompt: string;
} | null {
  const signalPath = path.join(projectPath, '.auto-claude', 'rdr-pending.json');

  if (!existsSync(signalPath)) {
    return null;
  }

  try {
    const content = readFileSync(signalPath, 'utf-8');
    const signal = JSON.parse(content);

    // Clear signal file after reading
    unlinkSync(signalPath);
    console.log(`[RDR] Read and cleared signal file: ${signalPath}`);

    return signal;
  } catch (error) {
    console.error(`[RDR] Failed to read signal file:`, error);
    return null;
  }
}

/**
 * Queue a task for RDR processing with timer-based batching
 * Tasks are collected for BATCH_COLLECTION_WINDOW_MS before processing
 */
export function queueTaskForRdr(projectId: string, task: TaskInfo): void {
  console.log(`[RDR] Queuing task ${task.specId} for batched processing`);

  // Add to pending tasks
  pendingTasks.push({ projectId, task });

  // Start or reset timer
  if (batchTimer) {
    clearTimeout(batchTimer);
  }

  batchTimer = setTimeout(async () => {
    await processPendingTasks();
  }, BATCH_COLLECTION_WINDOW_MS);

  console.log(`[RDR] Timer set - will process ${pendingTasks.length} tasks in ${BATCH_COLLECTION_WINDOW_MS}ms`);
}

/**
 * Process all collected pending tasks after timer expires
 */
async function processPendingTasks(): Promise<void> {
  if (pendingTasks.length === 0) {
    console.log(`[RDR] No pending tasks to process`);
    return;
  }

  console.log(`[RDR] Timer expired - processing ${pendingTasks.length} pending tasks`);

  // Group tasks by project
  const tasksByProject = new Map<string, TaskInfo[]>();
  for (const { projectId, task } of pendingTasks) {
    const existing = tasksByProject.get(projectId) || [];
    existing.push(task);
    tasksByProject.set(projectId, existing);
  }

  // Clear pending tasks and timer
  pendingTasks = [];
  batchTimer = null;

  // Process each project's tasks
  for (const [projectId, tasks] of tasksByProject) {
    const project = projectStore.getProject(projectId);
    if (!project) {
      console.error(`[RDR] Project not found: ${projectId}`);
      continue;
    }

    const mainWindow = BrowserWindow.getAllWindows()[0] || null;

    // Categorize tasks into batches
    const batches = categorizeTasks(tasks);
    console.log(`[RDR] Categorized ${tasks.length} tasks into ${batches.length} batches for project ${projectId}`);

    // Process auto-fixable batches immediately
    for (const batch of batches) {
      if (batch.type === 'json_error') {
        await processJsonErrorBatch(batch, project.path, mainWindow, projectId);
      } else if (batch.type === 'incomplete') {
        await processIncompleteBatch(batch, project.path, mainWindow, projectId);
      }
    }

    // Write signal file for batches needing Claude Code analysis
    const mcpBatches = batches.filter(b => b.type === 'qa_rejected' || b.type === 'errors');
    if (mcpBatches.length > 0) {
      writeRdrSignalFile(project.path, projectId, mcpBatches);

      // Also emit event for renderer (optional, signal file is the main mechanism)
      if (mainWindow) {
        mainWindow.webContents.send(IPC_CHANNELS.RDR_BATCH_READY, {
          projectId,
          batchCount: mcpBatches.length,
          taskCount: mcpBatches.reduce((sum, b) => sum + b.taskIds.length, 0),
          signalWritten: true
        });
      }
    }

    console.log(`[RDR] Completed batch processing for project ${projectId}`);
  }
}

/**
 * Immediately process all pending tasks (bypass timer)
 * Useful for testing or when user wants immediate processing
 */
export async function flushPendingTasks(): Promise<void> {
  if (batchTimer) {
    clearTimeout(batchTimer);
    batchTimer = null;
  }
  await processPendingTasks();
}

/**
 * Get the current number of pending tasks
 */
export function getPendingTaskCount(): number {
  return pendingTasks.length;
}

// ============================================================================
// IPC Handlers
// ============================================================================

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
      const tasks = getAllTaskInfo(projectId, taskIds);
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

      // Collect MCP batches to write signal file once (not per-batch)
      const mcpBatches: RdrBatch[] = batches.filter(b => b.type === 'qa_rejected' || b.type === 'errors');

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
            // Pass all MCP batches so signal file includes all of them
            results = await processMcpBatch(batch, project.path, mainWindow, projectId, mcpBatches);
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

  // Immediate RDR ping - writes signal file NOW (no 30s timer)
  // This is triggered by the manual Ping button in the UI
  ipcMain.handle(
    IPC_CHANNELS.PING_RDR_IMMEDIATE,
    async (event, projectId: string, tasks: Array<{
      id: string;
      status: string;
      reviewReason?: string;
      description?: string;
      subtasks?: Array<{ status: string; name?: string }>;
    }>): Promise<IPCResult<{ taskCount: number; signalPath: string }>> => {
      console.log(`[RDR] Ping immediate - ${tasks.length} tasks from project ${projectId}`);

      // Get project path
      const project = projectStore.getProject(projectId);
      if (!project) {
        return {
          success: false,
          error: 'Project not found'
        };
      }

      // Convert renderer Task objects to TaskInfo format
      const taskInfos: TaskInfo[] = tasks.map(t => ({
        specId: t.id,
        status: t.status,
        reviewReason: t.reviewReason,
        description: t.description,
        subtasks: t.subtasks
      }));

      // Categorize tasks into batches
      const batches = categorizeTasks(taskInfos);
      console.log(`[RDR] Categorized ${tasks.length} tasks into ${batches.length} batches:`);
      for (const batch of batches) {
        console.log(`[RDR]   - ${batch.type}: ${batch.taskIds.length} tasks`);
      }

      // Write signal file IMMEDIATELY (no timer)
      const signalDir = path.join(project.path, '.auto-claude');
      const signalPath = path.join(signalDir, 'rdr-pending.json');

      // Create .auto-claude dir if needed
      if (!existsSync(signalDir)) {
        const { mkdirSync } = await import('fs');
        mkdirSync(signalDir, { recursive: true });
      }

      const signal = {
        timestamp: new Date().toISOString(),
        projectId,
        source: 'manual_ping',
        batches: batches.map(b => ({
          type: b.type,
          taskCount: b.taskIds.length,
          taskIds: b.taskIds,
          tasks: b.tasks.map(t => ({
            specId: t.specId,
            description: t.description?.substring(0, 200),
            reviewReason: t.reviewReason,
            subtasksCompleted: t.subtasks?.filter(s => s.status === 'completed').length || 0,
            subtasksTotal: t.subtasks?.length || 0
          }))
        })),
        prompt: generateBatchPrompt(batches)
      };

      writeFileSync(signalPath, JSON.stringify(signal, null, 2));
      console.log(`[RDR] Wrote signal file: ${signalPath}`);
      console.log(`[RDR] Signal contains ${batches.length} batches with ${batches.reduce((sum, b) => sum + b.taskIds.length, 0)} total tasks`);

      return {
        success: true,
        data: {
          taskCount: tasks.length,
          signalPath
        }
      };
    }
  );

  // VS Code Window Management handlers
  // These use PowerShell scripts that mirror ClaudeAutoResponse logic

  // Get list of VS Code windows
  ipcMain.handle(
    IPC_CHANNELS.GET_VSCODE_WINDOWS,
    async (): Promise<IPCResult<Array<{ handle: number; title: string; processId: number }>>> => {
      console.log('[RDR] Getting VS Code windows');

      try {
        // Dynamic import to avoid loading Windows-specific code on other platforms
        const { getVSCodeWindows } = await import('../platform/windows/window-manager');
        const windows = getVSCodeWindows();
        console.log(`[RDR] Found ${windows.length} VS Code windows`);

        return {
          success: true,
          data: windows
        };
      } catch (error) {
        console.error('[RDR] Failed to get VS Code windows:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : String(error)
        };
      }
    }
  );

  // Send RDR message to a specific VS Code window
  ipcMain.handle(
    IPC_CHANNELS.SEND_RDR_TO_WINDOW,
    async (event, handle: number, message: string): Promise<IPCResult<{ success: boolean; error?: string }>> => {
      console.log(`[RDR] Sending message to window handle ${handle}`);

      try {
        const { sendMessageToWindow } = await import('../platform/windows/window-manager');
        const result = await sendMessageToWindow(handle, message);

        if (result.success) {
          console.log('[RDR] Message sent successfully');
        } else {
          console.error('[RDR] Failed to send message:', result.error);
        }

        return {
          success: result.success,
          data: result
        };
      } catch (error) {
        console.error('[RDR] Exception sending message:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : String(error)
        };
      }
    }
  );
}
