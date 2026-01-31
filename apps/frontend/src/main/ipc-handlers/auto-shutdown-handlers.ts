/**
 * Auto-Shutdown IPC Handlers
 *
 * Manages the shutdown monitor script that watches tasks and triggers
 * system shutdown when all active tasks reach Human Review.
 */

import { ipcMain } from 'electron';
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
 * Get all active task IDs for a project
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
    const planPath = path.join(specsDir, dir, 'implementation_plan.json');
    if (fs.existsSync(planPath)) {
      try {
        const content = JSON.parse(fs.readFileSync(planPath, 'utf-8'));
        // Only monitor active tasks (not done)
        if (content.status && content.status !== 'done') {
          taskIds.push(dir);
        }
      } catch (e) {
        console.error(`[AutoShutdown] Failed to read ${planPath}:`, e);
      }
    }
  }

  return taskIds;
}

/**
 * Count tasks in each status
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
    const planPath = path.join(specsDir, dir, 'implementation_plan.json');
    if (fs.existsSync(planPath)) {
      try {
        const content = JSON.parse(fs.readFileSync(planPath, 'utf-8'));
        if (content.status && content.status !== 'done') {
          total++;
          if (content.status === 'human_review') {
            humanReview++;
          }
        }
      } catch (e) {
        // Ignore parse errors
      }
    }
  }

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

        // Get script path
        const scriptPath = path.join(__dirname, '..', '..', '..', '..', 'scripts', 'shutdown-monitor.ts');

        // Spawn monitoring process
        const args = [
          scriptPath,
          '--task-ids', activeTaskIds.join(','),
          '--delay-seconds', '120'
        ];

        const monitorProcess = spawn('npx', ['tsx', ...args], {
          cwd: projectPath,
          detached: true,
          stdio: ['ignore', 'pipe', 'pipe']
        });

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
import { app } from 'electron';
app.on('before-quit', () => {
  for (const process of monitorProcesses.values()) {
    process.kill();
  }
  monitorProcesses.clear();
});
