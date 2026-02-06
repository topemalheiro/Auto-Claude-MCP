import chokidar, { FSWatcher } from 'chokidar';
import { readFileSync, existsSync } from 'fs';
import path from 'path';
import { EventEmitter } from 'events';
import type { ImplementationPlan, Task, TaskStatus } from '../shared/types';
import { projectStore } from './project-store';

interface WatcherInfo {
  taskId: string;
  watcher: FSWatcher;
  planPath: string;
}

interface SpecsWatcherInfo {
  projectId: string;
  projectPath: string;
  watcher: FSWatcher;
}

/**
 * Determine which board (status) a task should resume to based on its progress
 */
function determineResumeStatus(task: Task, plan: ImplementationPlan): TaskStatus {
  // Priority 1: Check if task has subtasks
  if (!plan.phases || plan.phases.length === 0 || !plan.phases.some(p => p.subtasks && p.subtasks.length > 0)) {
    // No subtasks = task never ran planner = start from beginning
    console.log(`[FileWatcher] determineResumeStatus: No subtasks found for ${task.specId} - returning 'backlog' (start fresh)`);
    return 'backlog';
  }

  // Count subtasks
  const allSubtasks = plan.phases.flatMap(p => p.subtasks || []);
  const completedSubtasks = allSubtasks.filter(s => s.status === 'completed').length;
  const totalSubtasks = allSubtasks.length;

  console.log(`[FileWatcher] determineResumeStatus: Task ${task.specId}: ${completedSubtasks}/${totalSubtasks} subtasks complete`);

  // Priority 2: Check which phase has incomplete work
  if (completedSubtasks < totalSubtasks) {
    // Check if Implementation phase is fully complete
    const implPhase = plan.phases.find(p => p.name === 'Implementation');
    const validationPhase = plan.phases.find(p => p.name === 'Validation');

    const implSubtasks = implPhase?.subtasks || [];
    const implComplete = implSubtasks.length > 0 && implSubtasks.every(s => s.status === 'completed');

    const validationSubtasks = validationPhase?.subtasks || [];
    const hasIncompleteValidation = validationSubtasks.some(s => s.status !== 'completed');

    // If Implementation is done but Validation has incomplete work → ai_review
    if (implComplete && hasIncompleteValidation) {
      console.log(`[FileWatcher] determineResumeStatus: Implementation complete, validation incomplete - returning 'ai_review' (resume QA)`);
      return 'ai_review';
    }

    console.log(`[FileWatcher] determineResumeStatus: Incomplete subtasks in coding - returning 'in_progress' (resume work)`);
    return 'in_progress';
  }

  // Priority 3: All subtasks complete but in human_review → re-run QA
  console.log(`[FileWatcher] determineResumeStatus: All subtasks complete - returning 'ai_review' (re-validate)`);
  return 'ai_review';
}

/**
 * Watches implementation_plan.json files for real-time progress updates
 */
export class FileWatcher extends EventEmitter {
  private watchers: Map<string, WatcherInfo> = new Map();
  private specsWatchers: Map<string, SpecsWatcherInfo> = new Map();

  /**
   * Start watching a task's implementation plan
   */
  async watch(taskId: string, specDir: string): Promise<void> {
    // Stop any existing watcher for this task
    await this.unwatch(taskId);

    const planPath = path.join(specDir, 'implementation_plan.json');

    // Check if plan file exists
    if (!existsSync(planPath)) {
      this.emit('error', taskId, `Plan file not found: ${planPath}`);
      return;
    }

    // Create watcher with settings to handle frequent writes
    const watcher = chokidar.watch(planPath, {
      persistent: true,
      ignoreInitial: true,
      awaitWriteFinish: {
        stabilityThreshold: 300,
        pollInterval: 100
      }
    });

    // Store watcher info
    this.watchers.set(taskId, {
      taskId,
      watcher,
      planPath
    });

    // Handle file changes
    watcher.on('change', () => {
      try {
        const content = readFileSync(planPath, 'utf-8');
        const plan: ImplementationPlan = JSON.parse(content);
        this.emit('progress', taskId, plan);
      } catch {
        // File might be in the middle of being written
        // Ignore parse errors, next change event will have complete file
      }
    });

    // Handle errors
    watcher.on('error', (error: unknown) => {
      const message = error instanceof Error ? error.message : String(error);
      this.emit('error', taskId, message);
    });

    // Read and emit initial state
    try {
      const content = readFileSync(planPath, 'utf-8');
      const plan: ImplementationPlan = JSON.parse(content);
      this.emit('progress', taskId, plan);
    } catch {
      // Initial read failed - not critical
    }
  }

  /**
   * Stop watching a task
   */
  async unwatch(taskId: string): Promise<void> {
    const watcherInfo = this.watchers.get(taskId);
    if (watcherInfo) {
      await watcherInfo.watcher.close();
      this.watchers.delete(taskId);
    }
  }

  /**
   * Stop all watchers
   */
  async unwatchAll(): Promise<void> {
    const closePromises = Array.from(this.watchers.values()).map(
      async (info) => {
        await info.watcher.close();
      }
    );
    await Promise.all(closePromises);
    this.watchers.clear();
  }

  /**
   * Check if a task is being watched
   */
  isWatching(taskId: string): boolean {
    return this.watchers.has(taskId);
  }

  /**
   * Get current plan state for a task
   */
  getCurrentPlan(taskId: string): ImplementationPlan | null {
    const watcherInfo = this.watchers.get(taskId);
    if (!watcherInfo) return null;

    try {
      const content = readFileSync(watcherInfo.planPath, 'utf-8');
      return JSON.parse(content);
    } catch {
      return null;
    }
  }

  /**
   * Watch a project's specs directory for new task folders
   * Emits 'specs-changed' when new spec directories are created
   */
  watchSpecsDirectory(projectId: string, projectPath: string, specsDir: string): void {
    // Stop any existing watcher for this project
    this.unwatchSpecsDirectory(projectId);

    const specsPath = path.join(projectPath, specsDir);
    console.log(`[FileWatcher] Setting up specs watcher for project ${projectId}`);
    console.log(`[FileWatcher] Specs path: ${specsPath}`);

    // Check if specs directory exists
    if (!existsSync(specsPath)) {
      console.log(`[FileWatcher] Specs directory does not exist yet: ${specsPath}`);
      return;
    }

    // Create watcher for the specs directory
    // depth: 2 to watch specs/*/implementation_plan.json
    const watcher = chokidar.watch(specsPath, {
      persistent: true,
      ignoreInitial: true,
      depth: 2,
      awaitWriteFinish: {
        stabilityThreshold: 500,
        pollInterval: 100
      }
    });

    // Store watcher info
    this.specsWatchers.set(projectId, {
      projectId,
      projectPath,
      watcher
    });

    // Log when watcher is ready
    watcher.on('ready', () => {
      console.log(`[FileWatcher] Specs watcher READY for project ${projectId} at ${specsPath}`);
    });

    // Handle new directory creation (new spec)
    watcher.on('addDir', (dirPath: string) => {
      // Only emit for direct children of specs directory
      const relativePath = path.relative(specsPath, dirPath);
      console.log(`[FileWatcher] addDir event: ${dirPath} (relative: ${relativePath})`);
      if (relativePath && !relativePath.includes(path.sep)) {
        console.log(`[FileWatcher] New spec folder detected: ${relativePath} - emitting specs-changed`);
        this.emit('specs-changed', {
          projectId,
          projectPath,
          specDir: dirPath,
          specId: path.basename(dirPath)
        });
      }
    });

    // Handle new file creation (implementation_plan.json)
    watcher.on('add', (filePath: string) => {
      console.log(`[FileWatcher] add event: ${filePath}`);
      // Emit when implementation_plan.json is created
      if (path.basename(filePath) === 'implementation_plan.json') {
        const specDir = path.dirname(filePath);
        const specId = path.basename(specDir);
        console.log(`[FileWatcher] implementation_plan.json detected in ${specDir} - emitting specs-changed`);
        this.emit('specs-changed', {
          projectId,
          projectPath,
          specDir,
          specId
        });

        // Check for start_requested status on new file creation (Bug #2 fix)
        try {
          const content = readFileSync(filePath, 'utf-8');
          const plan = JSON.parse(content);
          if (plan.status === 'start_requested') {
            // SAFETY: Skip archived tasks - they should not be auto-started
            const taskForArchiveCheck = projectStore.getTaskBySpecId(projectId, specId);
            if (taskForArchiveCheck?.metadata?.archivedAt) {
              console.log(`[FileWatcher] Skipping archived task ${specId} - not processing start_requested`);
              return;
            }

            // NEW: Move task back to correct board based on progress BEFORE auto-starting
            const task = taskForArchiveCheck;
            if (task && task.status === 'human_review') {
              // Prefer worktree plan for accurate progress (main plan may be stale)
              const worktreePlanPath = path.join(
                projectPath, '.auto-claude', 'worktrees', 'tasks', specId,
                '.auto-claude', 'specs', specId, 'implementation_plan.json'
              );
              let planForRouting = plan;
              if (existsSync(worktreePlanPath)) {
                try {
                  const worktreePlan = JSON.parse(readFileSync(worktreePlanPath, 'utf-8'));
                  planForRouting = worktreePlan;
                  console.log(`[FileWatcher] Using worktree plan for ${specId} routing (has real progress)`);
                } catch {
                  console.warn(`[FileWatcher] Failed to read worktree plan for ${specId}, using main`);
                }
              }

              // Determine where to send task based on subtask progress
              const targetStatus = determineResumeStatus(task, planForRouting);

              console.log(`[FileWatcher] Moving task ${specId} from human_review → ${targetStatus}`);

              // Update task status in project store
              const success = projectStore.updateTaskStatus(projectId, task.id, targetStatus);

              if (success) {
                // Emit event for UI refresh
                this.emit('task-status-changed', {
                  projectId,
                  taskId: task.id,
                  specId,
                  oldStatus: 'human_review',
                  newStatus: targetStatus
                });
              }
            }

            console.log(`[FileWatcher] start_requested status detected in NEW file for ${specId} - emitting task-start-requested`);
            this.emit('task-start-requested', {
              projectId,
              projectPath,
              specDir,
              specId
            });
          }
        } catch (err) {
          // Ignore parse errors - file might not be fully written yet
        }
      }
    });

    // Handle file changes (for start_requested status from MCP)
    watcher.on('change', (filePath: string) => {
      if (path.basename(filePath) === 'implementation_plan.json') {
        try {
          const content = readFileSync(filePath, 'utf-8');
          const plan = JSON.parse(content);

          // Check if status is 'start_requested' (set by MCP start_task)
          if (plan.status === 'start_requested') {
            const specDir = path.dirname(filePath);
            const specId = path.basename(specDir);

            // SAFETY: Skip archived tasks - they should not be auto-started
            const taskForArchiveCheck = projectStore.getTaskBySpecId(projectId, specId);
            if (taskForArchiveCheck?.metadata?.archivedAt) {
              console.log(`[FileWatcher] Skipping archived task ${specId} - not processing start_requested`);
              return;
            }

            // NEW: Move task back to correct board based on progress BEFORE auto-starting
            const task = taskForArchiveCheck;
            if (task && task.status === 'human_review') {
              // Prefer worktree plan for accurate progress (main plan may be stale)
              const worktreePlanPath = path.join(
                projectPath, '.auto-claude', 'worktrees', 'tasks', specId,
                '.auto-claude', 'specs', specId, 'implementation_plan.json'
              );
              let planForRouting = plan;
              if (existsSync(worktreePlanPath)) {
                try {
                  const worktreePlan = JSON.parse(readFileSync(worktreePlanPath, 'utf-8'));
                  planForRouting = worktreePlan;
                  console.log(`[FileWatcher] Using worktree plan for ${specId} routing (has real progress)`);
                } catch {
                  console.warn(`[FileWatcher] Failed to read worktree plan for ${specId}, using main`);
                }
              }

              // Determine where to send task based on subtask progress
              const targetStatus = determineResumeStatus(task, planForRouting);

              console.log(`[FileWatcher] Moving task ${specId} from human_review → ${targetStatus}`);

              // Update task status in project store
              const success = projectStore.updateTaskStatus(projectId, task.id, targetStatus);

              if (success) {
                // Emit event for UI refresh
                this.emit('task-status-changed', {
                  projectId,
                  taskId: task.id,
                  specId,
                  oldStatus: 'human_review',
                  newStatus: targetStatus
                });
              }
            }

            // THEN emit task-start-requested (existing code)
            console.log(`[FileWatcher] start_requested status detected for ${specId} - emitting task-start-requested`);
            this.emit('task-start-requested', {
              projectId,
              projectPath,
              specDir,
              specId
            });
          }
        } catch (err) {
          // Ignore parse errors - file might be mid-write
          console.warn(`[FileWatcher] Could not parse ${filePath}:`, err);
        }
      }
    });

    // Handle errors
    watcher.on('error', (error: unknown) => {
      const message = error instanceof Error ? error.message : String(error);
      console.error(`[FileWatcher] Error for project ${projectId}:`, message);
      this.emit('specs-error', projectId, message);
    });
  }

  /**
   * Stop watching a project's specs directory
   */
  async unwatchSpecsDirectory(projectId: string): Promise<void> {
    const watcherInfo = this.specsWatchers.get(projectId);
    if (watcherInfo) {
      await watcherInfo.watcher.close();
      this.specsWatchers.delete(projectId);
    }
  }

  /**
   * Stop all specs watchers
   */
  async unwatchAllSpecs(): Promise<void> {
    const closePromises = Array.from(this.specsWatchers.values()).map(
      async (info) => {
        await info.watcher.close();
      }
    );
    await Promise.all(closePromises);
    this.specsWatchers.clear();
  }

  /**
   * Check if a project's specs directory is being watched
   */
  isWatchingSpecs(projectId: string): boolean {
    return this.specsWatchers.has(projectId);
  }
}

// Singleton instance
export const fileWatcher = new FileWatcher();
