import chokidar, { FSWatcher } from 'chokidar';
import { readFileSync, existsSync } from 'fs';
import path from 'path';
import { EventEmitter } from 'events';
import type { ImplementationPlan } from '../shared/types';

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
        console.log(`[FileWatcher] implementation_plan.json detected in ${specDir} - emitting specs-changed`);
        this.emit('specs-changed', {
          projectId,
          projectPath,
          specDir,
          specId: path.basename(specDir)
        });
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
