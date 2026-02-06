#!/usr/bin/env npx tsx
/**
 * Shutdown Monitor (Global)
 *
 * Watches Auto-Claude tasks across MULTIPLE projects and triggers shutdown
 * when ALL active tasks across ALL projects reach Human Review.
 *
 * Usage:
 *   npx tsx scripts/shutdown-monitor.ts --project-path /path/to/project1 --project-path /path/to/project2 [--delay-seconds 120]
 *
 * Monitors ALL non-done tasks across all specified projects.
 */

import * as fs from 'fs';
import * as path from 'path';
import { spawn } from 'child_process';

const POLL_INTERVAL_MS = 5000; // Check every 5 seconds for testing

interface TaskStatus {
  taskId: string;
  status: string;
  feature: string;
  projectPath: string;
  source: 'worktree' | 'main';
}

/**
 * Get worktree plan if it exists (agent writes progress to worktree).
 * Worktree path: <project>/.auto-claude/worktrees/tasks/<taskId>/.auto-claude/specs/<taskId>/implementation_plan.json
 */
function getWorktreePlan(projectPath: string, taskId: string): any | null {
  const worktreePlanPath = path.join(
    projectPath, '.auto-claude', 'worktrees', 'tasks', taskId,
    '.auto-claude', 'specs', taskId, 'implementation_plan.json'
  );

  if (!fs.existsSync(worktreePlanPath)) {
    return null;
  }

  try {
    return JSON.parse(fs.readFileSync(worktreePlanPath, 'utf-8'));
  } catch (e) {
    console.error(`[Monitor] Failed to read worktree plan for ${taskId}:`, e);
    return null;
  }
}

/**
 * Get task statuses across MULTIPLE projects.
 * Prefers worktree plans over main plans (worktrees have actual agent progress).
 */
function getTaskStatuses(projectPaths: string[]): TaskStatus[] {
  const statuses: TaskStatus[] = [];

  for (const projectPath of projectPaths) {
    const specsDir = path.join(projectPath, '.auto-claude', 'specs');

    if (!fs.existsSync(specsDir)) {
      console.log(`[Monitor] Specs directory not found: ${specsDir}`);
      continue;
    }

    const dirs = fs.readdirSync(specsDir, { withFileTypes: true })
      .filter(d => d.isDirectory())
      .map(d => d.name);

    for (const dir of dirs) {
      const planPath = path.join(specsDir, dir, 'implementation_plan.json');
      if (fs.existsSync(planPath)) {
        try {
          const mainContent = JSON.parse(fs.readFileSync(planPath, 'utf-8'));

          // Prefer worktree plan (has actual agent progress) over main (may be stale)
          const worktreeContent = getWorktreePlan(projectPath, dir);
          const content = worktreeContent || mainContent;
          const source: 'worktree' | 'main' = worktreeContent ? 'worktree' : 'main';

          statuses.push({
            taskId: dir,
            status: content.status || 'unknown',
            feature: content.feature || dir,
            projectPath,
            source
          });
        } catch (e) {
          console.error(`[Monitor] Failed to read ${planPath}:`, e);
        }
      }
    }
  }

  return statuses;
}

function checkAllReachedTarget(statuses: TaskStatus[], targetStatus: string): boolean {
  // Filter out 'done' and 'pr_created' tasks - we only care about active tasks
  const activeTasks = statuses.filter(s => s.status !== 'done' && s.status !== 'pr_created');

  if (activeTasks.length === 0) {
    console.log('[Monitor] No active tasks to monitor across all projects');
    return false;
  }

  // Group by project for better logging
  const byProject = new Map<string, TaskStatus[]>();
  for (const task of activeTasks) {
    const projectName = path.basename(task.projectPath);
    if (!byProject.has(projectName)) {
      byProject.set(projectName, []);
    }
    byProject.get(projectName)!.push(task);
  }

  console.log(`[Monitor] Checking ${activeTasks.length} active tasks across ${byProject.size} projects:`);
  for (const [projectName, tasks] of byProject) {
    console.log(`  Project: ${projectName}`);
    for (const task of tasks) {
      const reached = task.status === targetStatus;
      console.log(`    - ${task.taskId}: ${task.status} [${task.source}] ${reached ? '✓' : '...'}`);
    }
  }

  const allReached = activeTasks.every(s => s.status === targetStatus);
  if (allReached) {
    console.log(`[Monitor] ✓ ALL ${activeTasks.length} tasks reached ${targetStatus}!`);
  }

  return allReached;
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

  // Parse arguments - support MULTIPLE --project-path arguments
  const projectPaths: string[] = [];
  let delaySeconds = 120;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--delay-seconds' && args[i + 1]) {
      delaySeconds = parseInt(args[i + 1], 10);
      i++;
    } else if (args[i] === '--project-path' && args[i + 1]) {
      projectPaths.push(args[i + 1]);
      i++; // Skip the next arg (the path value)
    }
  }

  if (projectPaths.length === 0) {
    console.error('[Monitor] No project paths provided! Use --project-path <path>');
    process.exit(1);
  }

  console.log('[Monitor] Starting GLOBAL shutdown monitor...');
  console.log('[Monitor] Monitoring projects:');
  for (const projectPath of projectPaths) {
    console.log(`  - ${projectPath}`);
  }
  console.log('[Monitor] Shutdown delay:', delaySeconds, 'seconds');
  console.log('[Monitor] Poll interval:', POLL_INTERVAL_MS / 1000, 'seconds');
  console.log('');

  const poll = () => {
    const statuses = getTaskStatuses(projectPaths);

    if (statuses.length === 0) {
      console.log('[Monitor] No tasks found across all projects, waiting...');
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
