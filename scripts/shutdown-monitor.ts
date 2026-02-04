#!/usr/bin/env npx tsx
/**
 * Shutdown Monitor
 *
 * Watches Auto-Claude tasks and triggers shutdown when all active tasks reach Human Review.
 *
 * Usage:
 *   npx tsx scripts/shutdown-monitor.ts [--task-ids task1,task2] [--delay-seconds 120]
 *
 * If no task-ids provided, monitors ALL non-done tasks.
 */

import * as fs from 'fs';
import * as path from 'path';
import { spawn } from 'child_process';

let SPECS_DIR = path.join(__dirname, '..', '.auto-claude', 'specs');
const POLL_INTERVAL_MS = 5000; // Check every 5 seconds for testing

interface TaskStatus {
  taskId: string;
  status: string;
  feature: string;
}

function getTaskStatuses(taskIds?: string[]): TaskStatus[] {
  const statuses: TaskStatus[] = [];

  if (!fs.existsSync(SPECS_DIR)) {
    console.log('[Monitor] Specs directory not found:', SPECS_DIR);
    return statuses;
  }

  const dirs = fs.readdirSync(SPECS_DIR, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .map(d => d.name);

  for (const dir of dirs) {
    // Filter by taskIds if provided
    if (taskIds && taskIds.length > 0 && !taskIds.includes(dir)) {
      continue;
    }

    const planPath = path.join(SPECS_DIR, dir, 'implementation_plan.json');
    if (fs.existsSync(planPath)) {
      try {
        const content = JSON.parse(fs.readFileSync(planPath, 'utf-8'));
        statuses.push({
          taskId: dir,
          status: content.status || 'unknown',
          feature: content.feature || dir
        });
      } catch (e) {
        console.error(`[Monitor] Failed to read ${planPath}:`, e);
      }
    }
  }

  return statuses;
}

function checkAllReachedTarget(statuses: TaskStatus[], targetStatus: string): boolean {
  // Filter out 'done' tasks - we only care about active tasks
  const activeTasks = statuses.filter(s => s.status !== 'done');

  if (activeTasks.length === 0) {
    console.log('[Monitor] No active tasks to monitor');
    return false;
  }

  console.log(`[Monitor] Checking ${activeTasks.length} active tasks:`);
  for (const task of activeTasks) {
    const reached = task.status === targetStatus;
    console.log(`  - ${task.taskId}: ${task.status} ${reached ? '✓' : '...'}`);
  }

  return activeTasks.every(s => s.status === targetStatus);
}

function triggerShutdown(delaySeconds: number): void {
  console.log(`\n[Monitor] ALL TASKS REACHED HUMAN REVIEW!`);
  console.log(`[Monitor] Triggering shutdown in ${delaySeconds} seconds...`);
  console.log(`[Monitor] Run "shutdown /a" to abort!\n`);

  const isWindows = process.platform === 'win32';

  if (isWindows) {
    spawn('shutdown', ['/s', '/t', String(delaySeconds)], {
      shell: true,
      detached: true,
      stdio: 'ignore'
    }).unref();
  } else {
    spawn('shutdown', ['-h', `+${Math.ceil(delaySeconds / 60)}`], {
      shell: true,
      detached: true,
      stdio: 'ignore'
    }).unref();
  }
}

async function main() {
  const args = process.argv.slice(2);

  // Parse arguments
  let taskIds: string[] | undefined;
  let delaySeconds = 120;
  let projectPath: string | undefined;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--task-ids' && args[i + 1]) {
      taskIds = args[i + 1].split(',').map(s => s.trim());
      i++;
    } else if (args[i] === '--delay-seconds' && args[i + 1]) {
      delaySeconds = parseInt(args[i + 1], 10);
      i++;
    } else if (args[i] === '--project-path' && args[i + 1]) {
      projectPath = args[i + 1];
      i++;
    }
  }

  // Update SPECS_DIR if project path provided
  if (projectPath) {
    SPECS_DIR = path.join(projectPath, '.auto-claude', 'specs');
  }

  console.log('[Monitor] Starting shutdown monitor...');
  console.log('[Monitor] Specs directory:', SPECS_DIR);
  console.log('[Monitor] Monitoring task IDs:', taskIds || 'ALL active tasks');
  console.log('[Monitor] Shutdown delay:', delaySeconds, 'seconds');
  console.log('[Monitor] Poll interval:', POLL_INTERVAL_MS / 1000, 'seconds');
  console.log('');

  const poll = () => {
    const statuses = getTaskStatuses(taskIds);

    if (statuses.length === 0) {
      console.log('[Monitor] No tasks found, waiting...');
      setTimeout(poll, POLL_INTERVAL_MS);
      return;
    }

    if (checkAllReachedTarget(statuses, 'human_review')) {
      triggerShutdown(delaySeconds);
      process.exit(0);
    } else {
      setTimeout(poll, POLL_INTERVAL_MS);
    }
  };

  // Start polling
  poll();
}

main().catch(err => {
  console.error('[Monitor] Fatal error:', err);
  process.exit(1);
});
