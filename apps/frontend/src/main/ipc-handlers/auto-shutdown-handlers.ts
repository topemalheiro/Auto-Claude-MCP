/**
 * Auto-Shutdown IPC Handlers
 *
 * Manages the shutdown monitor script that watches tasks and triggers
 * system shutdown when all active tasks reach Human Review.
 */

import { ipcMain, app, Notification } from 'electron';
import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult } from '../../shared/types';
import type { AutoShutdownStatus } from '../../shared/types/task';
import { projectStore } from '../project-store';
import { readSettingsFile, writeSettingsFile } from '../settings-utils';

// Track running monitor processes per project
const monitorProcesses = new Map<string, ChildProcess>();
const monitorStatuses = new Map<string, AutoShutdownStatus>();
const monitorProjectPaths = new Map<string, string>(); // projectId → projectPath for live recalculation

/**
 * Get project specs directory
 */
function getProjectSpecsDir(projectPath: string): string {
  return path.join(projectPath, '.auto-claude', 'specs');
}

/**
 * Get the worktree version of a task's plan, if it exists.
 * Worktrees contain the ACTUAL agent progress (ai_review, in_progress, etc.)
 * while the main project directory may have stale status (e.g., human_review).
 * Path: <project>/.auto-claude/worktrees/tasks/<taskId>/.auto-claude/specs/<taskId>/implementation_plan.json
 */
function getWorktreePlan(projectPath: string, taskDir: string): Record<string, unknown> | null {
  const worktreePlanPath = path.join(
    projectPath, '.auto-claude', 'worktrees', 'tasks', taskDir,
    '.auto-claude', 'specs', taskDir, 'implementation_plan.json'
  );

  if (!fs.existsSync(worktreePlanPath)) {
    return null;
  }

  try {
    return JSON.parse(fs.readFileSync(worktreePlanPath, 'utf-8'));
  } catch (e) {
    console.error(`[AutoShutdown] Failed to read worktree plan for ${taskDir}:`, e);
    return null;
  }
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
    status?: string;
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

  // If no subtasks exist, check if all phases are completed
  // This handles the edge case where tasks complete all phases but have no subtasks
  if (allSubtasks.length === 0) {
    const allPhasesComplete = plan.phases.every(p => p.status === 'completed');
    return allPhasesComplete ? 100 : 0;
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
        const mainContent = JSON.parse(fs.readFileSync(planPath, 'utf-8'));

        // Prefer worktree plan (has actual agent progress) over main (may be stale)
        const worktreeContent = getWorktreePlan(projectPath, dir);
        const content = worktreeContent || mainContent;
        const source = worktreeContent ? 'worktree' : 'main';

        // Skip terminal statuses - these tasks are truly finished
        if (content.status === 'done' || content.status === 'pr_created') {
          continue;
        }

        // Skip completed tasks: ANY non-initial status at 100% subtask completion
        // Agents may finish all subtasks but not transition status (crash, exit, etc.)
        // So we treat any 100% task as "complete" unless it's still in backlog/pending
        const progress = calculateTaskProgress(content);
        if (progress === 100 && content.status !== 'backlog' && content.status !== 'pending') {
          continue;
        }

        // Count as active: tasks with incomplete work or non-terminal status
        console.log(`[AutoShutdown] Active task ${dir}: status=${content.status}, progress=${progress}% (from ${source})`);
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
        const mainContent = JSON.parse(fs.readFileSync(planPath, 'utf-8'));

        // Prefer worktree plan (has actual agent progress) over main (may be stale)
        const worktreeContent = getWorktreePlan(projectPath, dir);
        const content = worktreeContent || mainContent;
        const source = worktreeContent ? 'worktree' : 'main';

        // Skip terminal statuses - these tasks are truly finished
        if (content.status === 'done' || content.status === 'pr_created') {
          continue;
        }

        // Skip completed tasks: ANY non-initial status at 100% subtask completion
        // Agents may finish all subtasks but not transition status (crash, exit, etc.)
        // So we treat any 100% task as "complete" unless it's still in backlog/pending
        const progress = calculateTaskProgress(content);
        if (progress === 100 && content.status !== 'backlog' && content.status !== 'pending') {
          console.log(`[AutoShutdown] Task ${dir}: 100% complete, status=${content.status} (NOT counted - complete) [${source}]`);
          continue;
        }

        // Count as active: tasks with incomplete work
        total++;
        if (content.status === 'human_review') {
          humanReview++;
        }
        console.log(`[AutoShutdown] Task ${dir}: ${progress}% complete, status=${content.status} (counted) [${source}]`);
      } catch (e) {
        console.error(`[AutoShutdown] Failed to read ${planPath}:`, e);
      }
    }
  }

  console.log(`[AutoShutdown] Total incomplete tasks: ${total}, in human_review: ${humanReview}`);
  return { total, humanReview };
}

/**
 * Get global auto-shutdown status across ALL projects
 * When monitoring is active, recalculates task count live from disk
 */
ipcMain.handle(
  IPC_CHANNELS.GET_AUTO_SHUTDOWN_STATUS,
  async (_): Promise<IPCResult<AutoShutdownStatus>> => {
    try {
      const cached = monitorStatuses.get('global');

      // If monitoring is active, recalculate task count live from ALL projects
      if (cached?.monitoring) {
        // Verify monitor process is still running
        const monitorProcess = monitorProcesses.get('global');
        if (!monitorProcess || monitorProcess.killed || monitorProcess.exitCode !== null) {
          console.log(`[AutoShutdown] Monitor process died - resetting status (exitCode=${monitorProcess?.exitCode}, killed=${monitorProcess?.killed})`);
          monitorProcesses.delete('global');
          const resetStatus: AutoShutdownStatus = {
            enabled: false,
            monitoring: false,
            tasksRemaining: 0,
            shutdownPending: false
          };
          monitorStatuses.set('global', resetStatus);
          return { success: true, data: resetStatus };
        }

        const projects = projectStore.getProjects();
        let totalTasks = 0;

        for (const project of projects) {
          const { total } = countTasksByStatus(project.path);
          totalTasks += total;
        }

        const updatedStatus: AutoShutdownStatus = {
          ...cached,
          tasksRemaining: totalTasks,
        };
        monitorStatuses.set('global', updatedStatus);
        return { success: true, data: updatedStatus };
      }

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
 * Enable/disable auto-shutdown GLOBALLY across ALL projects
 */
ipcMain.handle(
  IPC_CHANNELS.SET_AUTO_SHUTDOWN,
  async (_, enabled: boolean): Promise<IPCResult<AutoShutdownStatus>> => {
    try {
      if (enabled) {
        // Get ALL projects
        const projects = projectStore.getProjects();

        if (projects.length === 0) {
          return {
            success: false,
            error: 'No projects available to monitor'
          };
        }

        // Count total active tasks across all projects
        const projectPaths = projects.map(p => p.path);
        let totalActiveTasks = 0;

        for (const projectPath of projectPaths) {
          const activeTaskIds = getActiveTaskIds(projectPath);
          totalActiveTasks += activeTaskIds.length;
        }

        if (totalActiveTasks === 0) {
          console.log('[AutoShutdown] No active tasks - monitor will trigger shutdown on first poll');
        }

        // Kill existing global process if any
        const existingProcess = monitorProcesses.get('global');
        if (existingProcess) {
          existingProcess.kill();
          monitorProcesses.delete('global');
        }

        // Get script path
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

        // Build args for monitor script with ALL project paths
        const args = [
          '--import', 'tsx',
          scriptPath,
          '--delay-seconds', '120',
          ...projectPaths.flatMap(p => ['--project-path', p])
        ];

        // Spawn monitoring process
        const monitorProcess = spawn(
          process.execPath,
          args,
          {
            cwd: projectPaths[0], // Use first project as working directory
            detached: true,
            stdio: ['ignore', 'pipe', 'pipe'],
            windowsHide: true,
            env: { ...process.env }
          }
        );

        // Log output
        monitorProcess.stdout?.on('data', (data) => {
          console.log(`[AutoShutdown:global]`, data.toString().trim());
        });

        monitorProcess.stderr?.on('data', (data) => {
          console.error(`[AutoShutdown:global]`, data.toString().trim());
        });

        monitorProcess.on('exit', (code) => {
          console.log(`[AutoShutdown:global] Monitor exited with code ${code}`);
          monitorProcesses.delete('global');

          if (code === 0) {
            // Monitor detected all tasks complete and triggered shutdown
            if (Notification.isSupported()) {
              new Notification({
                title: 'Auto-Shutdown Armed',
                body: 'All tasks complete! System will shut down in 2 minutes. Run "shutdown /a" to abort.',
                urgency: 'critical'
              }).show();
            }
          }

          const status: AutoShutdownStatus = {
            enabled: false,
            monitoring: false,
            tasksRemaining: 0,
            shutdownPending: code === 0
          };
          monitorStatuses.set('global', status);
        });

        monitorProcess.unref();
        monitorProcesses.set('global', monitorProcess);

        // Get initial task count across all projects
        let totalTasks = 0;
        for (const project of projects) {
          const { total } = countTasksByStatus(project.path);
          totalTasks += total;
        }

        const status: AutoShutdownStatus = {
          enabled: true,
          monitoring: true,
          tasksRemaining: totalTasks,
          shutdownPending: false
        };
        monitorStatuses.set('global', status);

        // Persist to settings
        const settings = readSettingsFile() || {};
        writeSettingsFile({
          ...settings,
          autoShutdownEnabled: true
        });

        console.log(`[AutoShutdown] Monitoring ${projects.length} projects with ${totalActiveTasks} active tasks`);

        return { success: true, data: status };
      } else {
        // Stop monitoring
        const process = monitorProcesses.get('global');
        if (process) {
          process.kill();
          monitorProcesses.delete('global');
        }

        const status: AutoShutdownStatus = {
          enabled: false,
          monitoring: false,
          tasksRemaining: 0,
          shutdownPending: false
        };
        monitorStatuses.set('global', status);

        // Persist to settings
        const settings = readSettingsFile() || {};
        writeSettingsFile({
          ...settings,
          autoShutdownEnabled: false
        });

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
 * Cancel pending shutdown (global)
 */
ipcMain.handle(
  IPC_CHANNELS.CANCEL_AUTO_SHUTDOWN,
  async (_): Promise<IPCResult<void>> => {
    try {
      // Kill global monitor process if running
      const process = monitorProcesses.get('global');
      if (process) {
        process.kill();
        monitorProcesses.delete('global');
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
      monitorStatuses.set('global', status);

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
