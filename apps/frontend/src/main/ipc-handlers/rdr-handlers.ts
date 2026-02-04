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

import { readFileSync, writeFileSync, existsSync, unlinkSync, readdirSync, statSync } from 'fs';
import * as path from 'path';
import * as os from 'os';
import { IPC_CHANNELS } from '../../shared/constants/ipc';
import type { IPCResult } from '../../shared/types';
import { JSON_ERROR_PREFIX } from '../../shared/constants/task';
import { projectStore } from '../project-store';
import { isElectron } from '../electron-compat';
import { outputMonitor } from '../claude-code/output-monitor';

// Conditionally import Electron-specific modules
let ipcMain: any = null;
let BrowserWindow: any = null;

if (isElectron) {
  // Load each module independently so one failure doesn't break everything
  try {
    const electron = require('electron');
    ipcMain = electron.ipcMain;
    BrowserWindow = electron.BrowserWindow;
  } catch (error) {
    console.warn('[RDR] Failed to load Electron modules:', error);
  }

  // Note: window-manager and mcp-server are loaded dynamically when needed
  // to avoid module resolution issues after compilation
}

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
  phases?: Array<{ subtasks?: Array<{ status: string; updated_at?: string }> }>;
  exitReason?: string;
  planStatus?: string;
  created_at?: string;
  updated_at?: string;
  rdrDisabled?: boolean;  // If true, RDR will skip this task
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
  results?: RdrProcessResult[];
  batches: Array<{ type: string; count: number }>;
  message?: string;  // Optional status message for queued tasks
}

// RDR Intervention Types (matches shared/types/task.ts)
type InterventionType = 'recovery' | 'resume' | 'stuck' | 'incomplete';

/**
 * Calculate task progress from phases/subtasks
 * Returns percentage of completed subtasks (0-100)
 * Reused from auto-shutdown-handlers logic
 *
 * NOTE: Handles both 'subtasks' and 'chunks' naming conventions
 * (some implementation_plan.json files use 'chunks' instead of 'subtasks')
 */
function calculateTaskProgress(task: TaskInfo): number {
  if (!task.phases || task.phases.length === 0) {
    return 0;
  }

  // Flatten all subtasks from all phases
  // Handle both 'subtasks' and 'chunks' naming conventions (Bug fix)
  const allSubtasks = task.phases.flatMap(phase =>
    phase.subtasks || (phase as { chunks?: Array<{ status: string }> }).chunks || []
  ).filter(Boolean);

  if (allSubtasks.length === 0) {
    return 0;
  }

  const completed = allSubtasks.filter(s => s.status === 'completed').length;
  return Math.round((completed / allSubtasks.length) * 100);
}

/**
 * Check if task is legitimate human review (shouldn't be flagged by RDR)
 * Tasks at 100% completion + completed reviewReason = waiting for merge approval
 */
function isLegitimateHumanReview(task: TaskInfo): boolean {
  const progress = calculateTaskProgress(task);

  // 100% subtasks complete + completed = waiting for merge approval
  if (progress === 100 && task.reviewReason === 'completed') {
    return true;  // Don't flag - this is normal human review
  }

  // Plan review - waiting for user to approve spec before coding
  if (task.reviewReason === 'plan_review' && task.planStatus === 'review') {
    return true;  // Don't flag - user needs to approve plan (we do flag separately with plan_review)
  }

  return false;
}

/**
 * Determine what type of intervention a task needs
 * Returns null if task doesn't need intervention
 *
 * Types:
 * - 'recovery': Task crashed/errored (exitReason: error, reviewReason: errors/qa_rejected)
 * - 'resume': Task paused mid-work (rate_limit_crash, incomplete_work)
 * - 'stuck': Task bounced to human_review with incomplete subtasks (no clear exit reason)
 * - 'incomplete': Task has pending subtasks in active boards (in_progress, ai_review)
 */
function determineInterventionType(task: TaskInfo): InterventionType | null {
  // Skip completed/archived tasks
  if (task.status === 'done' || task.status === 'pr_created' || task.status === 'backlog') {
    return null;
  }

  // Check if this is legitimate human review (don't flag)
  if (task.status === 'human_review' && isLegitimateHumanReview(task)) {
    return null;
  }

  // RECOVERY: Crashed with error or QA rejected
  if (task.exitReason === 'error' ||
      task.exitReason === 'auth_failure' ||
      task.reviewReason === 'errors' ||
      task.reviewReason === 'qa_rejected') {
    return 'recovery';
  }

  // RESUME: Rate limited or paused mid-task (incomplete_work)
  // NOTE: Removed human_review exclusion - incomplete_work ALWAYS means needs resume
  if (task.exitReason === 'rate_limit_crash' ||
      task.reviewReason === 'incomplete_work') {
    return 'resume';
  }

  // STUCK: In human_review with incomplete subtasks or problematic reviewReason
  if (task.status === 'human_review') {
    const progress = calculateTaskProgress(task);
    if (progress < 100) {
      // Has incomplete work - either incomplete_work review reason or just stuck
      if (task.reviewReason === 'incomplete_work') {
        return 'resume';  // Can be resumed
      }
      return 'stuck';  // Bounced without clear reason
    }
    // NEW: Also flag if 100% but reviewReason indicates a problem
    // (e.g., errors, qa_rejected, or other non-'completed' reasons)
    if (task.reviewReason && task.reviewReason !== 'completed' && task.reviewReason !== 'plan_review') {
      console.log(`[RDR] Task ${task.specId} at 100% but has problematic reviewReason: ${task.reviewReason}`);
      return 'stuck';  // Completed but marked with issue
    }
  }

  // INCOMPLETE: Still has pending subtasks in active boards
  if (task.status === 'in_progress' || task.status === 'ai_review') {
    const progress = calculateTaskProgress(task);
    if (progress < 100) {
      // Check if it has a reviewReason indicating it was interrupted
      if (task.reviewReason === 'incomplete_work' || task.reviewReason === 'errors') {
        return task.reviewReason === 'errors' ? 'recovery' : 'resume';
      }
      return 'incomplete';
    }
  }

  // Empty plan - needs intervention
  if (!task.phases || task.phases.length === 0) {
    return 'recovery';  // Can't continue without a plan
  }

  return null;  // No intervention needed
}

// Interface for rich task info used in RDR messages
interface RichTaskInfo {
  specId: string;
  status: string;
  reviewReason?: string;
  interventionType: InterventionType | null;
  progress: {
    completed: number;
    total: number;
    percentage: number;
    lastSubtaskName?: string;
    lastSubtaskIndex?: number;
  };
  currentPhase?: 'planning' | 'coding' | 'validation';
  lastLogs: Array<{
    timestamp: string;
    phase: string;
    content: string;
  }>;
  errors?: {
    exitReason?: string;
    reviewReason?: string;
    errorSummary?: string;
  };
}

/**
 * Get the last N log entries from task_logs.json
 * Combines entries from all phases and sorts by timestamp
 */
function getLastLogEntries(projectPath: string, specId: string, count: number = 3): Array<{
  timestamp: string;
  phase: string;
  content: string;
}> {
  const logsPath = path.join(projectPath, '.auto-claude', 'specs', specId, 'task_logs.json');

  if (!existsSync(logsPath)) {
    return [];
  }

  try {
    const content = readFileSync(logsPath, 'utf-8');
    const taskLogs = JSON.parse(content);

    if (!taskLogs?.phases) {
      return [];
    }

    const allEntries: Array<{ timestamp: string; phase: string; content: string }> = [];

    // Collect entries from all phases
    for (const phase of ['planning', 'coding', 'validation'] as const) {
      const phaseLog = taskLogs.phases[phase];
      if (phaseLog?.entries) {
        for (const entry of phaseLog.entries) {
          if (entry.content && entry.timestamp) {
            allEntries.push({
              timestamp: entry.timestamp,
              phase,
              content: entry.content.substring(0, 100)  // Truncate long content
            });
          }
        }
      }
    }

    // Sort by timestamp descending and take last N
    return allEntries
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, count);
  } catch (error) {
    console.error(`[RDR] Failed to read task logs for ${specId}:`, error);
    return [];
  }
}

/**
 * Get current active phase from task_logs.json
 */
function getCurrentPhase(projectPath: string, specId: string): 'planning' | 'coding' | 'validation' | undefined {
  const logsPath = path.join(projectPath, '.auto-claude', 'specs', specId, 'task_logs.json');

  if (!existsSync(logsPath)) {
    return undefined;
  }

  try {
    const content = readFileSync(logsPath, 'utf-8');
    const taskLogs = JSON.parse(content);

    if (!taskLogs?.phases) {
      return undefined;
    }

    // Find the active phase
    for (const phase of ['validation', 'coding', 'planning'] as const) {
      if (taskLogs.phases[phase]?.status === 'active') {
        return phase;
      }
    }

    // Find most recent started phase
    for (const phase of ['validation', 'coding', 'planning'] as const) {
      if (taskLogs.phases[phase]?.started_at) {
        return phase;
      }
    }

    return undefined;
  } catch {
    return undefined;
  }
}

/**
 * Gather rich task information for RDR messages
 * Includes progress, logs, errors, and intervention type
 */
function gatherRichTaskInfo(task: TaskInfo, projectPath: string): RichTaskInfo {
  // Calculate progress from subtasks/phases
  const allSubtasks = task.phases?.flatMap(p => p.subtasks || []) || task.subtasks || [];
  const completed = allSubtasks.filter(s => s.status === 'completed').length;
  const total = allSubtasks.length;

  // Find last completed subtask
  let lastSubtaskName: string | undefined;
  let lastSubtaskIndex: number | undefined;
  for (let i = allSubtasks.length - 1; i >= 0; i--) {
    if (allSubtasks[i].status === 'completed') {
      lastSubtaskName = (allSubtasks[i] as any).name || (allSubtasks[i] as any).description?.substring(0, 50);
      lastSubtaskIndex = i + 1;
      break;
    }
  }

  // Get intervention type
  const interventionType = determineInterventionType(task);

  // Get last logs
  const lastLogs = getLastLogEntries(projectPath, task.specId, 3);

  // Get current phase
  const currentPhase = getCurrentPhase(projectPath, task.specId);

  // Build error info if applicable
  let errors: RichTaskInfo['errors'];
  if (task.exitReason || task.reviewReason === 'errors' || task.reviewReason === 'qa_rejected') {
    errors = {
      exitReason: task.exitReason,
      reviewReason: task.reviewReason,
      errorSummary: task.reviewReason === 'qa_rejected'
        ? 'QA found issues with implementation'
        : task.exitReason || 'Task failed during execution'
    };
  }

  return {
    specId: task.specId,
    status: task.status,
    reviewReason: task.reviewReason,
    interventionType,
    progress: {
      completed,
      total,
      percentage: total > 0 ? Math.round((completed / total) * 100) : 0,
      lastSubtaskName,
      lastSubtaskIndex
    },
    currentPhase,
    lastLogs,
    errors
  };
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
 * Increment RDR attempt counter for tasks
 * Updates task_metadata.json with attempt count and timestamp
 */
function incrementRdrAttempts(projectPath: string, taskIds: string[]): void {
  const now = new Date().toISOString();

  for (const specId of taskIds) {
    try {
      const metadataPath = path.join(projectPath, '.auto-claude', 'specs', specId, 'task_metadata.json');
      let metadata: any = {};

      // Read existing metadata if it exists
      if (existsSync(metadataPath)) {
        try {
          metadata = JSON.parse(readFileSync(metadataPath, 'utf-8'));
        } catch (readErr) {
          console.warn(`[RDR] Failed to read metadata for ${specId}, starting fresh:`, readErr);
        }
      }

      // Increment attempts counter
      metadata.rdrAttempts = (metadata.rdrAttempts || 0) + 1;
      metadata.rdrLastAttempt = now;

      // Write back updated metadata
      writeFileSync(metadataPath, JSON.stringify(metadata, null, 2));
      console.log(`[RDR] Incremented RDR attempts for ${specId} to ${metadata.rdrAttempts}`);
    } catch (error) {
      console.error(`[RDR] Failed to increment RDR attempts for ${specId}:`, error);
      // Continue with other tasks even if one fails
    }
  }
}

/**
 * Categorize tasks into batches by problem type
 */
function categorizeTasks(tasks: TaskInfo[]): RdrBatch[] {
  const batches: RdrBatch[] = [];

  // Filter out tasks with RDR disabled
  const rdrEnabledTasks = tasks.filter(t => !t.rdrDisabled);
  if (rdrEnabledTasks.length < tasks.length) {
    console.log(`[RDR] Skipping ${tasks.length - rdrEnabledTasks.length} tasks with RDR disabled`);
  }

  // Batch 1: JSON Errors (tasks with JSON parse error in description)
  const jsonErrors = rdrEnabledTasks.filter(t => t.description?.startsWith(JSON_ERROR_PREFIX));
  if (jsonErrors.length > 0) {
    batches.push({ type: 'json_error', taskIds: jsonErrors.map(t => t.specId), tasks: jsonErrors });
    console.log(`[RDR] Batch 1 - JSON Errors: ${jsonErrors.length} tasks`);
  }

  // Batch 2: Incomplete Tasks (has subtasks but not all completed, NOT an error state)
  const incomplete = rdrEnabledTasks.filter(t =>
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
  const qaRejected = rdrEnabledTasks.filter(t =>
    t.reviewReason === 'qa_rejected' &&
    !t.description?.startsWith(JSON_ERROR_PREFIX)
  );
  if (qaRejected.length > 0) {
    batches.push({ type: 'qa_rejected', taskIds: qaRejected.map(t => t.specId), tasks: qaRejected });
    console.log(`[RDR] Batch 3 - QA Rejected: ${qaRejected.length} tasks`);
  }

  // Batch 4: Other Errors (not JSON errors)
  const errors = rdrEnabledTasks.filter(t =>
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
 * Get intervention type label for display
 */
function getInterventionTypeLabel(type: InterventionType | null): string {
  switch (type) {
    case 'recovery': return 'RECOVERY';
    case 'resume': return 'RESUME';
    case 'stuck': return 'STUCK';
    case 'incomplete': return 'INCOMPLETE';
    default: return 'UNKNOWN';
  }
}

/**
 * Generate a prompt for Claude Code to analyze the batch
 * Enhanced with rich task info including intervention type, progress, and logs
 */
function generateBatchPrompt(batches: RdrBatch[], projectId: string, projectPath: string): string {
  const lines: string[] = [
    '/auto-claude-rdr',
    '',
    `**PROJECT_ID:** ${projectId}`,
    '',
    '# [AUTO-CLAUDE RDR] Recovery Manager Role',
    '',
    '**YOU ARE THE CLAUDE MANAGER** for the Auto-Claude autonomous coding system.',
    '**YOUR ROLE:** Recover stuck tasks using ONLY MCP tools, NOT manual fixes.',
    '',
    `**Timestamp:** ${new Date().toISOString()}`,
    `**Total Batches:** ${batches.length}`,
    '',
    '## CRITICAL: 4-Tier Priority System',
    '',
    '**PRIORITY 1 (AUTO - 95%):** System auto-recovers via file watcher',
    '- Tasks automatically move to correct boards and resume',
    '- **YOU DO NOTHING** - Already handled by MCP tools',
    '',
    '**PRIORITY 2 (REQUEST - 4%):** Request changes only',
    '- Use `process_rdr_batch` to write fix requests',
    '- Let task agent fix issues itself',
    '',
    '**PRIORITY 3 (FIX - <1%):** Auto-fix ONLY JSON errors',
    '- Use `process_rdr_batch` for technical blockers',
    '',
    '**PRIORITY 4 (MANUAL - RARE):** Last resort only',
    '- ONLY when Priorities 1-3 fail',
    '- Minimal intervention',
    '',
    '## ⚠️ STRICT RULES',
    '',
    '1. **ONLY USE** MCP tool: `mcp__auto-claude-manager__process_rdr_batch`',
    '2. **DO NOT** read files (no Read, Grep, Glob)',
    '3. **DO NOT** edit files (no Edit, Write)',
    '4. **DO NOT** try to fix manually',
    '5. **CALL MCP TOOL IMMEDIATELY** - One call per batch type',
    '',
    '## Tasks Detected',
    ''
  ];

  // Enhanced task details with rich info
  for (const batch of batches) {
    lines.push(`### ${batch.type.toUpperCase()}: ${batch.taskIds.length} tasks`);
    lines.push('');

    for (const task of batch.tasks) {
      // Gather rich info for this task
      const richInfo = gatherRichTaskInfo(task, projectPath);
      const typeLabel = getInterventionTypeLabel(richInfo.interventionType);

      lines.push(`#### ${task.specId}`);
      lines.push(`**Status:** ${task.status} | **Reason:** ${task.reviewReason || 'none'} | **Type:** ${typeLabel}`);
      lines.push(`**Progress:** ${richInfo.progress.completed}/${richInfo.progress.total} subtasks (${richInfo.progress.percentage}%)`);

      if (richInfo.currentPhase) {
        lines.push(`**Current Phase:** ${richInfo.currentPhase}`);
      }

      if (richInfo.progress.lastSubtaskName) {
        lines.push(`**Last Subtask:** #${richInfo.progress.lastSubtaskIndex} - ${richInfo.progress.lastSubtaskName}`);
      }

      // Show last logs if available
      if (richInfo.lastLogs.length > 0) {
        lines.push('');
        lines.push('**Recent Activity:**');
        for (const log of richInfo.lastLogs) {
          const time = new Date(log.timestamp).toLocaleTimeString('en-US', { hour12: false });
          lines.push(`- [${time}] (${log.phase}) ${log.content}`);
        }
      }

      // Show errors if applicable
      if (richInfo.errors) {
        lines.push('');
        lines.push('**Errors:**');
        if (richInfo.errors.exitReason) {
          lines.push(`- Exit Reason: ${richInfo.errors.exitReason}`);
        }
        if (richInfo.errors.errorSummary) {
          lines.push(`- Summary: ${richInfo.errors.errorSummary}`);
        }
      }

      lines.push('');
      lines.push('---');
      lines.push('');
    }
  }

  lines.push('## IMMEDIATE ACTION');
  lines.push('');
  lines.push('Call `mcp__auto-claude-manager__process_rdr_batch` NOW for EACH batch:');
  lines.push('');
  for (const batch of batches) {
    lines.push(`  mcp__auto-claude-manager__process_rdr_batch(`);
    lines.push(`    batchType: "${batch.type}",`);
    lines.push(`    fixes: [/* task IDs: ${batch.taskIds.slice(0,3).join(', ')}${batch.taskIds.length > 3 ? '...' : ''} */]`);
    lines.push(`  )`);
    lines.push('');
  }
  lines.push('**REMEMBER:** Call MCP tool ONLY. NO manual fixes. System auto-recovers.');
  lines.push('');

  return lines.join('\n');
}

/**
 * Write signal file for Claude Code to pick up via MCP
 * Enhanced with rich task info including intervention type, progress, and logs
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
      tasks: b.tasks.map(t => {
        // Gather rich info for each task
        const richInfo = gatherRichTaskInfo(t, projectPath);
        return {
          specId: t.specId,
          description: t.description?.substring(0, 200),
          status: t.status,
          reviewReason: t.reviewReason,
          exitReason: t.exitReason,
          interventionType: richInfo.interventionType,
          progress: richInfo.progress,
          currentPhase: richInfo.currentPhase,
          lastLogs: richInfo.lastLogs,
          errors: richInfo.errors
        };
      })
    })),
    prompt: generateBatchPrompt(batches, projectId, projectPath)
  };

  writeFileSync(signalPath, JSON.stringify(signal, null, 2));
  console.log(`[RDR] Wrote signal file: ${signalPath}`);
  console.log(`[RDR] Signal contains ${batches.length} batches with ${batches.reduce((sum, b) => sum + b.taskIds.length, 0)} total tasks`);
}

/**
 * Read and clear the RDR signal file if it exists
 * Returns the signal data or null if no file exists
 * Enhanced with rich task info including intervention type, progress, and logs
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
      status?: string;
      reviewReason?: string;
      exitReason?: string;
      interventionType?: InterventionType | null;
      progress?: {
        completed: number;
        total: number;
        percentage: number;
        lastSubtaskName?: string;
        lastSubtaskIndex?: number;
      };
      currentPhase?: 'planning' | 'coding' | 'validation';
      lastLogs?: Array<{
        timestamp: string;
        phase: string;
        content: string;
      }>;
      errors?: {
        exitReason?: string;
        reviewReason?: string;
        errorSummary?: string;
      };
      // Legacy fields for backwards compatibility
      subtasksCompleted?: number;
      subtasksTotal?: number;
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
 * Check if Claude Code is currently busy
 * Returns true if Claude is at prompt, processing, or session is active
 */
async function checkClaudeCodeBusy(): Promise<boolean> {
  try {
    console.log('[RDR] 🔍 Checking if Claude Code is busy...');

    // PRIMARY: Check if Claude is at prompt OR processing (NOT idle)
    if (outputMonitor) {
      // Update state by reading latest JSONL transcript
      await outputMonitor.isAtPrompt(); // This updates internal state
      const state = outputMonitor.getCurrentState();

      // Block RDR ONLY if Claude is actively processing (thinking/using tools)
      // AT_PROMPT (waiting for input) is fine - RDR notification is just another input
      if (state === 'PROCESSING') {
        console.log('[RDR] ⏸️  BUSY: Claude Code is processing (thinking/using tools)');

        const diagnostics = await outputMonitor.getDiagnostics();
        console.log('[RDR]    📊 Diagnostics:', {
          state: diagnostics.state,
          timeSinceStateChange: `${diagnostics.timeSinceStateChange}ms`,
          recentOutputFiles: diagnostics.recentOutputFiles,
          timestamp: new Date().toISOString()
        });
        return true; // BUSY - reschedule!
      }

      // AT_PROMPT or IDLE is fine for RDR notifications
      if (state === 'AT_PROMPT') {
        console.log('[RDR] ✅ Output Monitor: Claude is AT_PROMPT (waiting for input - OK for RDR)');
      }

      // OutputMonitor determines IDLE state - trust it immediately
      // No additional wait time needed - OutputMonitor already checks for genuine idle state
      console.log('[RDR] ✅ Output Monitor: Claude is IDLE - proceeding with RDR');
    } else {
      console.warn('[RDR] ⚠️  Output Monitor not available');
    }

    // SECONDARY: Check MCP connection activity (dynamically load if on Windows)
    if (process.platform === 'win32') {
      try {
        const { mcpMonitor } = await import('../mcp-server');
        if (mcpMonitor && mcpMonitor.isBusy()) {
          console.log('[RDR] ⏸️  BUSY: MCP connection active');
          const status = mcpMonitor.getStatus();
          console.log('[RDR]    📊 MCP Status:', {
            activeToolName: status.activeToolName,
            timeSinceLastRequest: `${status.timeSinceLastRequest}ms`,
            timestamp: new Date().toISOString()
          });
          return true;
        } else {
          console.log('[RDR] ✅ MCP Monitor: No active connections');
        }
      } catch (error) {
        console.warn('[RDR] ⚠️  MCP monitor check skipped:', error);
        // Continue - don't fail the whole check
      }
    }

    // All checks passed - Claude is truly idle
    console.log('[RDR] ✅ ALL CHECKS PASSED: Claude Code is IDLE (safe to send)');
    return false;
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error('[RDR] ❌ ERROR: Failed to check busy state:', errorMessage);
    console.error('[RDR]        Failing safe - assuming BUSY to prevent interrupting active session');
    // FAIL SAFE: Assume busy on error to prevent interrupting ongoing work
    return true;
  }
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

  // CRITICAL: Check if Claude Code is busy before processing
  const isBusy = await checkClaudeCodeBusy();
  if (isBusy) {
    console.log(`[RDR] ⏸️  Claude Code is BUSY - rescheduling ${pendingTasks.length} tasks for 60s later`);
    console.log(`[RDR]    ⏰ Next retry at: ${new Date(Date.now() + 60000).toISOString()}`);

    // Reschedule for later (retry in 60 seconds)
    if (batchTimer) {
      clearTimeout(batchTimer);
    }
    batchTimer = setTimeout(async () => {
      console.log('[RDR] ⏰ RETRY: Attempting to process pending tasks again...');
      await processPendingTasks();
    }, 60000); // Retry in 60 seconds
    return;
  }

  console.log(`[RDR] ✅ Claude is IDLE - proceeding to process ${pendingTasks.length} tasks`);

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

    // Increment RDR attempt counter for all tasks being processed
    const allTaskIds = batches.flatMap(b => b.taskIds);
    if (allTaskIds.length > 0) {
      incrementRdrAttempts(project.path, allTaskIds);
    }

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
// Event-Driven RDR Processing
// ============================================================================

/**
 * Set up event-driven RDR processing
 * Subscribes to OutputMonitor's 'idle' event to trigger processing immediately
 * when Claude Code finishes its current work, instead of waiting for fixed timers
 */
async function setupEventDrivenProcessing(): Promise<void> {
  if (eventDrivenEnabled) {
    console.log('[RDR] Event-driven processing already enabled');
    return;
  }

  try {
    // Start file watching in OutputMonitor
    await outputMonitor.startWatching();

    // Subscribe to 'idle' event - triggers when Claude Code becomes idle
    idleEventListener = async (event: any) => {
      if (pendingTasks.length === 0) {
        return; // No pending tasks to process
      }

      console.log(`[RDR] 🚀 EVENT: Claude Code became idle - processing ${pendingTasks.length} pending tasks immediately`);
      console.log(`[RDR]    📊 State change: ${event.from} -> ${event.to}`);

      // Cancel any pending timer - we'll process immediately
      if (batchTimer) {
        clearTimeout(batchTimer);
        batchTimer = null;
        console.log('[RDR]    ⏰ Cancelled pending timer - using event-driven processing');
      }

      // Small delay to ensure state is stable (prevents rapid re-triggering)
      await new Promise(resolve => setTimeout(resolve, 500));

      // Process pending tasks immediately
      await processPendingTasks();
    };

    outputMonitor.on('idle', idleEventListener);
    eventDrivenEnabled = true;

    console.log('[RDR] ✅ Event-driven processing enabled - RDR will trigger immediately when Claude Code becomes idle');
    console.log('[RDR]    📡 Subscribed to OutputMonitor "idle" events');
  } catch (error) {
    console.error('[RDR] ❌ Failed to enable event-driven processing:', error);
    console.log('[RDR]    ⏰ Falling back to timer-based processing');
  }
}

/**
 * Disable event-driven processing (cleanup)
 */
export function disableEventDrivenProcessing(): void {
  if (!eventDrivenEnabled) return;

  if (idleEventListener) {
    outputMonitor.removeListener('idle', idleEventListener);
    idleEventListener = null;
  }

  outputMonitor.stopWatching();
  eventDrivenEnabled = false;
  console.log('[RDR] Event-driven processing disabled');
}

// ============================================================================
// IPC Handlers
// ============================================================================

// Track whether event-driven processing is enabled
let eventDrivenEnabled = false;
let idleEventListener: ((event: any) => void) | null = null;

/**
 * Register RDR IPC handlers
 */
export function registerRdrHandlers(): void {
  if (!isElectron || !ipcMain) {
    console.log('[RDR] Skipping handler registration (not in Electron context)');
    return;
  }

  console.log('[RDR] Registering RDR handlers');

  // Start event-driven RDR processing
  setupEventDrivenProcessing();

  ipcMain.handle(
    IPC_CHANNELS.TRIGGER_RDR_PROCESSING,
    async (event, projectId: string, taskIds: string[]): Promise<IPCResult<RdrProcessingSummary>> => {
      console.log(`[RDR] Manual trigger - queueing ${taskIds.length} tasks for project ${projectId}`);

      // Get project path
      const project = projectStore.getProject(projectId);

      if (!project) {
        return {
          success: false,
          error: 'Project not found'
        };
      }

      // Get all task info
      const tasks = getAllTaskInfo(projectId, taskIds);
      if (tasks.length === 0) {
        return {
          success: false,
          error: 'No tasks found'
        };
      }

      // CRITICAL FIX: Queue tasks instead of processing immediately
      // This allows retry when Claude becomes idle
      console.log(`[RDR] Queueing ${tasks.length} tasks for batched processing with busy detection`);
      for (const task of tasks) {
        queueTaskForRdr(projectId, task);
      }

      // Check if Claude Code is busy
      const isBusy = await checkClaudeCodeBusy();
      if (isBusy) {
        console.log(`[RDR] ⏸️  Claude Code is BUSY - tasks queued and will be processed when idle`);
        return {
          success: true,
          data: {
            processed: 0,
            jsonFixed: 0,
            fixSubmitted: 0,
            queuedForMcp: tasks.length,
            batches: [{ type: 'queued', count: tasks.length }],
            message: `Tasks queued - will be processed when Claude Code is idle (currently ${isBusy ? 'busy' : 'idle'})`
          }
        };
      }

      // If Claude is idle, processPendingTasks will be called by the timer
      console.log(`[RDR] ✅ Claude is IDLE - timer will process tasks in ${BATCH_COLLECTION_WINDOW_MS}ms`);

      return {
        success: true,
        data: {
          processed: 0,
          jsonFixed: 0,
          fixSubmitted: 0,
          queuedForMcp: tasks.length,
          batches: [{ type: 'queued', count: tasks.length }],
          message: `Tasks queued for processing in ${BATCH_COLLECTION_WINDOW_MS}ms`
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

      // Increment RDR attempt counter for all tasks being processed
      const allTaskIds = batches.flatMap(b => b.taskIds);
      if (allTaskIds.length > 0) {
        incrementRdrAttempts(project.path, allTaskIds);
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
          tasks: b.tasks.map(t => {
            // Gather rich info for each task
            const richInfo = gatherRichTaskInfo(t, project.path);
            return {
              specId: t.specId,
              description: t.description?.substring(0, 200),
              status: t.status,
              reviewReason: t.reviewReason,
              exitReason: t.exitReason,
              interventionType: richInfo.interventionType,
              progress: richInfo.progress,
              currentPhase: richInfo.currentPhase,
              lastLogs: richInfo.lastLogs,
              errors: richInfo.errors
            };
          })
        })),
        prompt: generateBatchPrompt(batches, projectId, project.path)
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
    async (event, titlePattern: string, message: string): Promise<IPCResult<{ success: boolean; error?: string }>> => {
      console.log(`[RDR] 📤 Preparing to send message to window matching: "${titlePattern}"`);
      console.log(`[RDR]    Message length: ${message.length} characters`);

      try {
        const { sendMessageToWindow } = await import('../platform/windows/window-manager');
        const result = await sendMessageToWindow(titlePattern, message);

        if (result.success) {
          console.log('[RDR] ✅ Message sent successfully');
        } else {
          console.error('[RDR] ❌ Failed to send message:', result.error);
        }

        return {
          success: result.success,
          data: result
        };
      } catch (error) {
        console.error('[RDR] 💥 Exception sending message:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : String(error)
        };
      }
    }
  );

  // Get detailed RDR batch information for auto-send messages
  ipcMain.handle(
    IPC_CHANNELS.GET_RDR_BATCH_DETAILS,
    async (event, projectId: string): Promise<IPCResult<{
      batches: Array<{ type: string; taskIds: string[]; taskCount: number }>;
      taskDetails: Array<{
        specId: string;
        title: string;
        description: string;
        status: string;
        reviewReason?: string;
        exitReason?: string;
        interventionType?: InterventionType | null;  // Type of intervention needed
        progress?: {                                  // Progress info with last subtask
          completed: number;
          total: number;
          percentage: number;
          lastSubtaskName?: string;
          lastSubtaskIndex?: number;
        };
        subtasks?: Array<{ name: string; status: string }>;
        errorSummary?: string;
      }>;
    }>> => {
      console.log(`[RDR] Getting batch details for project ${projectId}`);

      try {
        const tasks = projectStore.getTasks(projectId);

        /**
         * Helper: Check if task needs intervention
         * Delegates to centralized determineInterventionType() which uses calculateTaskProgress()
         * to properly check task.phases (same logic as auto-shutdown detection)
         *
         * Tasks at 100% completion + passed AI review = NOT flagged (legitimate human review)
         */
        const needsIntervention = (task: TaskInfo): boolean => {
          // DEBUG: Log data flow for each task
          const progress = calculateTaskProgress(task);
          const phaseCount = task.phases?.length || 0;
          const subtaskCount = task.phases?.flatMap(p =>
            p.subtasks || (p as { chunks?: Array<{ status: string }> }).chunks || []
          ).length || 0;
          console.log(`[RDR] Task ${task.specId}: status=${task.status}, phases=${phaseCount}, subtasks=${subtaskCount}, progress=${progress}%, reviewReason=${task.reviewReason || 'none'}`);

          const interventionType = determineInterventionType(task);

          if (interventionType) {
            console.log(`[RDR] ✅ Task ${task.specId} needs intervention: type=${interventionType}`);
            return true;
          }

          // Log why task was skipped - be more accurate about the reason
          if (progress === 100 && task.reviewReason === 'completed') {
            console.log(`[RDR] ⏭️  Skipping task ${task.specId} - 100% complete, awaiting merge approval`);
          } else if (progress === 100) {
            console.log(`[RDR] ⏭️  Skipping task ${task.specId} - 100% but reviewReason=${task.reviewReason || 'none'} (should have been caught)`);
          } else if (task.status === 'done' || task.status === 'pr_created' || task.status === 'backlog') {
            console.log(`[RDR] ⏭️  Skipping task ${task.specId} - status=${task.status}`);
          } else {
            console.log(`[RDR] ⏭️  Skipping task ${task.specId} - no intervention needed (progress=${progress}%)`);
          }

          return false;
        };

        // Filter tasks using enhanced detection (uses centralized calculateTaskProgress)
        const tasksNeedingHelp = tasks.filter(needsIntervention);

        if (tasksNeedingHelp.length === 0) {
          return {
            success: true,
            data: {
              batches: [],
              taskDetails: []
            }
          };
        }

        // Convert to TaskInfo format for categorization
        const taskInfos: TaskInfo[] = tasksNeedingHelp.map(t => ({
          specId: t.specId,
          status: t.status,
          reviewReason: t.reviewReason,
          description: t.description,
          subtasks: t.subtasks,
          phases: t.phases,  // Required for calculateTaskProgress()
          exitReason: t.exitReason,
          planStatus: t.planStatus
        }));

        // Categorize into batches
        const batches = categorizeTasks(taskInfos);

        // Build detailed task info for the message
        const taskDetails = tasksNeedingHelp.map(task => {
          // Extract error summary if available
          let errorSummary: string | undefined;
          if (task.reviewReason === 'errors') {
            errorSummary = task.exitReason || 'Task failed during execution';
          } else if (task.reviewReason === 'qa_rejected') {
            errorSummary = 'QA found issues with implementation';
          } else if (task.description?.startsWith(JSON_ERROR_PREFIX)) {
            errorSummary = 'JSON parse error in task data';
          }

          // Convert task to TaskInfo for helper functions
          const taskInfo: TaskInfo = {
            specId: task.specId,
            status: task.status,
            reviewReason: task.reviewReason,
            description: task.description,
            subtasks: task.subtasks,
            phases: task.phases,
            exitReason: task.exitReason,
            planStatus: task.planStatus
          };

          // Calculate progress from subtasks
          const allSubtasks = task.phases?.flatMap((p: any) => p.subtasks || []) || task.subtasks || [];
          const completed = allSubtasks.filter((s: any) => s.status === 'completed').length;
          const total = allSubtasks.length;

          // Find last completed subtask
          let lastSubtaskName: string | undefined;
          let lastSubtaskIndex: number | undefined;
          for (let i = allSubtasks.length - 1; i >= 0; i--) {
            if (allSubtasks[i].status === 'completed') {
              lastSubtaskName = allSubtasks[i].name || allSubtasks[i].description?.substring(0, 50) || allSubtasks[i].title;
              lastSubtaskIndex = i + 1;
              break;
            }
          }

          // Determine intervention type using centralized function
          const interventionType = determineInterventionType(taskInfo);

          return {
            specId: task.specId,
            title: task.title || task.specId,
            description: task.description?.substring(0, 200) || '',
            status: task.status,
            reviewReason: task.reviewReason,
            exitReason: task.exitReason,
            interventionType,  // Type of intervention needed
            progress: {        // Progress info with last subtask
              completed,
              total,
              percentage: total > 0 ? Math.round((completed / total) * 100) : 0,
              lastSubtaskName,
              lastSubtaskIndex
            },
            subtasks: task.subtasks?.map((s) => ({
              name: s.title || s.id,
              status: s.status
            })),
            errorSummary
          };
        });

        console.log(`[RDR] Found ${taskDetails.length} tasks needing intervention, ${batches.length} batches`);

        return {
          success: true,
          data: {
            batches: batches.map(b => ({
              type: b.type,
              taskIds: b.taskIds,
              taskCount: b.taskIds.length
            })),
            taskDetails
          }
        };
      } catch (error) {
        console.error('[RDR] Failed to get batch details:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : String(error)
        };
      }
    }
  );

  // Fallback: Check for recent session file modifications
  async function isClaudeSessionActive(): Promise<boolean> {
    const claudeDir = path.join(os.homedir(), '.claude');
    const sessionsDir = path.join(claudeDir, '.sessions');

    if (!existsSync(sessionsDir)) {
      return false;
    }

    const recentThreshold = Date.now() - 5000; // 5 seconds
    const files = readdirSync(sessionsDir);

    for (const file of files) {
      const filePath = path.join(sessionsDir, file);
      try {
        const stats = statSync(filePath);

        // If session file modified in last 5 seconds, Claude is active
        if (stats.mtimeMs > recentThreshold) {
          return true;
        }
      } catch (err) {
        // Ignore files we can't stat
        continue;
      }
    }

    return false;
  }

  // Check if Claude Code is currently busy (in a prompt loop)
  ipcMain.handle(
    IPC_CHANNELS.IS_CLAUDE_CODE_BUSY,
    async (event, titlePattern: string): Promise<IPCResult<boolean>> => {
      try {
        const { isClaudeCodeBusy } = await import('../platform/windows/window-manager');
        const busy = await isClaudeCodeBusy(titlePattern);
        return { success: true, data: busy };
      } catch (error) {
        console.error('[RDR] Error checking busy state:', error);
        return { success: false, error: String(error) };
      }
    }
  );

  // Auto-recover all tasks with status="start_requested" (programmatic recover button press)
  ipcMain.handle(
    IPC_CHANNELS.AUTO_RECOVER_ALL_TASKS,
    async (event, projectId: string): Promise<IPCResult<{ recovered: number; taskIds: string[] }>> => {
      try {
        console.log('[RDR] Auto-recovering ALL tasks (setting status to start_requested)');

        // Get all tasks for the project (use projectStore singleton)
        const tasks = projectStore.getTasks(projectId);

        if (tasks.length === 0) {
          console.log('[RDR] No tasks found in project');
          return { success: true, data: { recovered: 0, taskIds: [] } };
        }

        console.log(`[RDR] Processing ${tasks.length} tasks for auto-recovery`);

        console.log(`[RDR] Tasks to recover:`, tasks.map(t => t.specId).join(', '));

        // Get project to access path
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        // Priority 1: Update status to "start_requested" in implementation_plan.json
        // This triggers the file watcher which auto-starts tasks
        const recovered: string[] = [];
        for (const task of tasks) {
          try {
            const planPath = getPlanPath(project.path, task.specId);

            if (!existsSync(planPath)) {
              console.warn(`[RDR] ⚠️  Plan not found: ${planPath}`);
              continue;
            }

            // Read current plan
            const planContent = readFileSync(planPath, 'utf-8');
            const plan = JSON.parse(planContent);

            // Update status to trigger auto-restart
            plan.status = 'start_requested';
            plan.updated_at = new Date().toISOString();

            // Write back
            writeFileSync(planPath, JSON.stringify(plan, null, 2), 'utf-8');

            console.log(`[RDR] ✅ Auto-recovered task: ${task.specId} (status → start_requested)`);
            recovered.push(task.specId);
          } catch (error) {
            console.error(`[RDR] ❌ Error auto-recovering ${task.specId}:`, error);
          }
        }

        console.log(`[RDR] Auto-recovery complete: ${recovered.length}/${tasks.length} tasks recovered`);
        console.log(`[RDR] File watcher will detect changes and auto-start tasks within 2-3 seconds`);

        return {
          success: true,
          data: { recovered: recovered.length, taskIds: recovered }
        };
      } catch (error) {
        console.error('[RDR] Auto-recovery failed:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : String(error)
        };
      }
    }
  );
}
