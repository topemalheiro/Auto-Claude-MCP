/**
 * Auto-Shutdown IPC Handlers
 *
 * Manages the shutdown monitor script that watches tasks and triggers
 * system shutdown when all active tasks reach Human Review.
 */

import { ipcMain, app } from 'electron';
import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult } from '../../shared/types';
import type { AutoShutdownStatus } from '../../shared/types/task';

// Track running monitor processes per project
const monitorProcesses = new Map<string, ChildProcess>();
const monitorStatuses = new Map<string, AutoShutdownStatus>();

/**
 * Get project specs directory
 */
function getProjectSpecsDir(projectPath: string): string {
  return path.join(projectPath, '.auto-claude', 'specs');
}

/**
 * Check if a task is archived by reading task_metadata.json
 * Archived tasks have an archivedAt field set to an ISO date string
 */
function isTaskArchived(specsDir: string, taskDir: string): boolean {
  const metadataPath = path.join(specsDir, taskDir, 'task_metadata.json');

  if (!fs.existsSync(metadataPath)) {
    return false;
  }

  try {
    const metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf-8'));
    // Task is archived if archivedAt field exists and is truthy
    if (metadata.archivedAt) {
      console.log(`[AutoShutdown] Task ${taskDir}: ARCHIVED at ${metadata.archivedAt} (skipped)`);
      return true;
    }
    return false;
  } catch (e) {
    // If we can't read metadata, assume not archived
    return false;
  }
}

/**
 * Calculate task completion percentage from phases/subtasks
 * Returns 100 if all subtasks are completed, 0 if no subtasks
 * Matches the green dot indicators in the UI
 */
function calculateTaskProgress(plan: {
  phases?: Array<{
    subtasks?: Array<{ status: string }>;
    chunks?: Array<{ status: string }>;  // Legacy field name
  }>;
}): number {
  if (!plan.phases || plan.phases.length === 0) {
    return 0;
  }

  // Flatten all subtasks from all phases
  // Note: Only 'completed' status counts toward 100%. Tasks with 'failed' subtasks
  // will never reach 100% and will continue to be monitored, which is correct
  // behavior since they require intervention.
  const allSubtasks = plan.phases.flatMap(phase =>
    phase.subtasks || phase.chunks || []
  ).filter(Boolean);

  if (allSubtasks.length === 0) {
    return 0;
  }

  const completed = allSubtasks.filter(s => s.status === 'completed').length;
  return Math.round((completed / allSubtasks.length) * 100);
}

/**
 * Get all active task IDs for a project
 * Returns tasks that are not in terminal status (done, pr_created) and not archived
 */
function getActiveTaskIds(projectPath: string): string[] {
  const specsDir = getProjectSpecsDir(projectPath);

  if (!fs.existsSync(specsDir)) {
    return [];
  }

  const taskIds: string[] = [];
  const dirs = fs.readdirSync(specsDir, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .map(d => d.name);

  for (const dir of dirs) {
    // Skip archived tasks - they shouldn't be monitored for shutdown
    if (isTaskArchived(specsDir, dir)) {
      continue;
    }

    const planPath = path.join(specsDir, dir, 'implementation_plan.json');
    if (fs.existsSync(planPath)) {
      try {
        const content = JSON.parse(fs.readFileSync(planPath, 'utf-8'));

        // Skip terminal statuses - these tasks are truly finished
        if (content.status === 'done' || content.status === 'pr_created') {
          continue;
        }

        // Count ALL non-terminal, non-archived tasks as active
        // Previously this used calculateTaskProgress() and skipped 100% tasks,
        // but that was wrong: a task in 'human_review' with 100% subtask completion
        // is NOT done - it still needs human action. Status determines completion,
        // not subtask progress.
        taskIds.push(dir);
      } catch (e) {
        console.error(`[AutoShutdown] Failed to read ${planPath}:`, e);
      }
    }
  }

  return taskIds;
}

/**
 * Count tasks that are not in terminal status (done, pr_created) and not archived
 * Returns total count and how many are in human_review
 */
function countTasksByStatus(projectPath: string): { total: number; humanReview: number } {
  const specsDir = getProjectSpecsDir(projectPath);

  if (!fs.existsSync(specsDir)) {
    return { total: 0, humanReview: 0 };
  }

  let total = 0;
  let humanReview = 0;

  const dirs = fs.readdirSync(specsDir, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .map(d => d.name);

  for (const dir of dirs) {
    // Skip archived tasks - they shouldn't be counted for shutdown monitoring
    if (isTaskArchived(specsDir, dir)) {
      continue;
    }

    const planPath = path.join(specsDir, dir, 'implementation_plan.json');
    if (fs.existsSync(planPath)) {
      try {
        const content = JSON.parse(fs.readFileSync(planPath, 'utf-8'));

        // Skip terminal statuses - these tasks are truly finished
        if (content.status === 'done' || content.status === 'pr_created') {
          continue;
        }

        // Count ALL non-terminal, non-archived tasks
        // Status determines completion, not subtask progress
        const progress = calculateTaskProgress(content);
        total++;
        if (content.status === 'human_review') {
          humanReview++;
        }
        console.log(`[AutoShutdown] Task ${dir}: ${progress}% complete, status=${content.status} (counted)`);
      } catch (e) {
        console.error(`[AutoShutdown] Failed to read ${planPath}:`, e);
      }
    }
  }

  console.log(`[AutoShutdown] Total incomplete tasks: ${total}, in human_review: ${humanReview}`);
  return { total, humanReview };
}

/**
 * Get auto-shutdown status for a project
 */
ipcMain.handle(
  IPC_CHANNELS.GET_AUTO_SHUTDOWN_STATUS,
  async (_, projectId: string): Promise<IPCResult<AutoShutdownStatus>> => {
    try {
      // Return cached status if available
      const cached = monitorStatuses.get(projectId);
      if (cached) {
        return { success: true, data: cached };
      }

      // Default status
      const status: AutoShutdownStatus = {
        enabled: false,
        monitoring: false,
        tasksRemaining: 0,
        shutdownPending: false
      };

      return { success: true, data: status };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error('[AutoShutdown] Failed to get status:', errorMessage);
      return { success: false, error: errorMessage };
    }
  }
);

/**
 * Enable/disable auto-shutdown for a project
 */
ipcMain.handle(
  IPC_CHANNELS.SET_AUTO_SHUTDOWN,
  async (_, projectId: string, projectPath: string, enabled: boolean): Promise<IPCResult<AutoShutdownStatus>> => {
    try {
      if (!projectPath) {
        return { success: false, error: 'Project path is required' };
      }

      if (enabled) {
        // Start monitoring
        const activeTaskIds = getActiveTaskIds(projectPath);

        if (activeTaskIds.length === 0) {
          return {
            success: false,
            error: 'No active tasks to monitor'
          };
        }

        // Kill existing process if any
        const existingProcess = monitorProcesses.get(projectId);
        if (existingProcess) {
          existingProcess.kill();
          monitorProcesses.delete(projectId);
        }

        // Get script path - use path.resolve for correct parent directory resolution
        // In development: app.getAppPath() returns the compiled output dir (apps/frontend/out/main)
        // Scripts folder is at repo root, so we need to go up 4 levels:
        // out/main -> out -> apps/frontend -> apps -> repo root
        const appPath = app.getAppPath();
        console.log(`[AutoShutdown] App path: ${appPath}`);

        const scriptPath = app.isPackaged
          ? path.join(process.resourcesPath, 'scripts', 'shutdown-monitor.ts')
          : path.resolve(appPath, '..', '..', '..', '..', 'scripts', 'shutdown-monitor.ts');

        console.log(`[AutoShutdown] Script path: ${scriptPath}`);
        console.log(`[AutoShutdown] Script exists: ${fs.existsSync(scriptPath)}`);

        if (!fs.existsSync(scriptPath)) {
          return {
            success: false,
            error: `Shutdown monitor script not found at: ${scriptPath}`
          };
        }

        // Spawn monitoring process
        // Use node directly without shell to avoid terminal window on Windows
        // shell: true causes cmd.exe window to appear even with windowsHide: true
        const monitorProcess = spawn(
          process.execPath,  // Full path to node.exe - no shell needed
          [
            '--import', 'tsx',  // Use tsx as ESM loader (replaces npx tsx)
            scriptPath,
            '--project-path', projectPath,
            '--task-ids', activeTaskIds.join(','),
            '--delay-seconds', '120'
          ],
          {
            cwd: projectPath,
            detached: true,
            stdio: ['ignore', 'pipe', 'pipe'],
            windowsHide: true,  // Works properly without shell
            env: { ...process.env }
          }
        );

        // Log output
        monitorProcess.stdout?.on('data', (data) => {
          console.log(`[AutoShutdown:${projectId}]`, data.toString().trim());
        });

        monitorProcess.stderr?.on('data', (data) => {
          console.error(`[AutoShutdown:${projectId}]`, data.toString().trim());
        });

        monitorProcess.on('exit', (code) => {
          console.log(`[AutoShutdown:${projectId}] Monitor exited with code ${code}`);
          monitorProcesses.delete(projectId);

          // Update status
          const status: AutoShutdownStatus = {
            enabled: false,
            monitoring: false,
            tasksRemaining: 0,
            shutdownPending: code === 0 // Exit 0 means shutdown triggered
          };
          monitorStatuses.set(projectId, status);
        });

        monitorProcess.unref();
        monitorProcesses.set(projectId, monitorProcess);

        // Get initial task count
        const { total } = countTasksByStatus(projectPath);

        const status: AutoShutdownStatus = {
          enabled: true,
          monitoring: true,
          tasksRemaining: total,
          shutdownPending: false
        };
        monitorStatuses.set(projectId, status);

        return { success: true, data: status };
      } else {
        // Stop monitoring
        const process = monitorProcesses.get(projectId);
        if (process) {
          process.kill();
          monitorProcesses.delete(projectId);
        }

        const status: AutoShutdownStatus = {
          enabled: false,
          monitoring: false,
          tasksRemaining: 0,
          shutdownPending: false
        };
        monitorStatuses.set(projectId, status);

        return { success: true, data: status };
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error('[AutoShutdown] Failed to set auto-shutdown:', errorMessage);
      return { success: false, error: errorMessage };
    }
  }
);

/**
 * Cancel pending shutdown
 */
ipcMain.handle(
  IPC_CHANNELS.CANCEL_AUTO_SHUTDOWN,
  async (_, projectId: string): Promise<IPCResult<void>> => {
    try {
      // Kill monitor process if running
      const process = monitorProcesses.get(projectId);
      if (process) {
        process.kill();
        monitorProcesses.delete(projectId);
      }

      // Cancel system shutdown (Windows)
      if (process.platform === 'win32') {
        spawn('shutdown', ['/a'], { shell: true });
      }

      // Update status
      const status: AutoShutdownStatus = {
        enabled: false,
        monitoring: false,
        tasksRemaining: 0,
        shutdownPending: false
      };
      monitorStatuses.set(projectId, status);

      return { success: true };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error('[AutoShutdown] Failed to cancel shutdown:', errorMessage);
      return { success: false, error: errorMessage };
    }
  }
);

// Clean up on app quit
app.on('before-quit', () => {
  for (const process of monitorProcesses.values()) {
    process.kill();
  }
  monitorProcesses.clear();
});
