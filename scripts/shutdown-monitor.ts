#!/usr/bin/env npx tsx
/**
 * Shutdown Monitor (Global)
 *
 * Watches Auto-Claude tasks across MULTIPLE projects and triggers shutdown
 * when ALL active tasks across ALL projects are complete.
 *
 * A task is "complete" when:
 * - status is 'done' or 'pr_created' (terminal)
 * - ANY non-initial status at 100% subtask completion (agents may finish but not transition)
 * - task is archived (has archivedAt in task_metadata.json)
 *
 * Usage:
 *   npx tsx scripts/shutdown-monitor.ts --project-path /path/to/project1 --project-path /path/to/project2 [--delay-seconds 120]
 *
 * Monitors ALL non-done tasks across all specified projects.
 */

import * as fs from 'fs';
import * as path from 'path';
import { spawn } from 'child_process';

const POLL_INTERVAL_MS = 5000; // Check every 5 seconds

interface TaskStatus {
  taskId: string;
  status: string;
  feature: string;
  projectPath: string;
  source: 'worktree' | 'main';
  progress: number;
}

// (hasSeenActiveTasks state is tracked in poll() and passed to areAllTasksComplete)

/**
 * Check if a task is archived by reading task_metadata.json.
 * Archived tasks have an archivedAt field set to an ISO date string.
 */
function isTaskArchived(projectPath: string, taskId: string): boolean {
  const metadataPath = path.join(projectPath, '.auto-claude', 'specs', taskId, 'task_metadata.json');
  try {
    if (!fs.existsSync(metadataPath)) return false;
    const metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf-8'));
    if (metadata.archivedAt) {
      console.log(`[Monitor] Task ${taskId}: ARCHIVED at ${metadata.archivedAt} (skipped)`);
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

/**
 * Calculate task completion percentage from phases/subtasks.
 * Returns 100 if all subtasks are completed, 0 if no subtasks.
 * Matches the logic in auto-shutdown-handlers.ts.
 */
function calculateTaskProgress(plan: any): number {
  if (!plan.phases || plan.phases.length === 0) return 0;

  const allSubtasks = plan.phases.flatMap((phase: any) =>
    phase.subtasks || phase.chunks || []
  ).filter(Boolean);

  if (allSubtasks.length === 0) {
    return plan.phases.every((p: any) => p.status === 'completed') ? 100 : 0;
  }

  const completed = allSubtasks.filter((s: any) => s.status === 'completed').length;
  return Math.round((completed / allSubtasks.length) * 100);
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
 * Skips archived tasks. Prefers worktree plans over main plans.
 * Includes progress calculation for each task.
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
      // Skip archived tasks - they shouldn't be monitored
      if (isTaskArchived(projectPath, dir)) continue;

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
            source,
            progress: calculateTaskProgress(content),
          });
        } catch (e) {
          console.error(`[Monitor] Failed to read ${planPath}:`, e);
        }
      }
    }
  }

  return statuses;
}

/**
 * Check if all tasks are complete.
 *
 * A task is complete if:
 * - status is 'done' or 'pr_created' (terminal)
 * - status is 'human_review' with 100% progress (all subtasks done)
 *
 * Returns true when no active (incomplete) tasks remain AND we've seen tasks before.
 * This prevents triggering on an empty project with no tasks.
 */
function areAllTasksComplete(statuses: TaskStatus[], hasSeenActiveTasks: boolean): { complete: boolean; hasActive: boolean } {
  // Terminal statuses - task is completely done
  const terminalTasks = statuses.filter(s =>
    s.status === 'done' || s.status === 'pr_created'
  );

  // Complete tasks - any non-terminal, non-initial status at 100% subtask completion
  // Agents may finish all subtasks but not transition status (crash, exit, etc.)
  // So we treat any 100% task as "complete" unless it's still in backlog/pending
  const completeTasks = statuses.filter(s =>
    s.progress === 100 &&
    s.status !== 'done' && s.status !== 'pr_created' &&  // already in terminalTasks
    s.status !== 'backlog' && s.status !== 'pending'
  );

  // Active tasks - everything NOT terminal and NOT complete
  const activeTasks = statuses.filter(s =>
    s.status !== 'done' && s.status !== 'pr_created' &&
    !(s.progress === 100 && s.status !== 'backlog' && s.status !== 'pending')
  );

  const hasActive = activeTasks.length > 0;

  // Log status grouped by project
  const byProject = new Map<string, TaskStatus[]>();
  for (const task of statuses) {
    const name = path.basename(task.projectPath);
    if (!byProject.has(name)) byProject.set(name, []);
    byProject.get(name)!.push(task);
  }

  console.log(`[Monitor] ${statuses.length} tasks: ${terminalTasks.length} done, ${completeTasks.length} complete (review 100%), ${activeTasks.length} active`);
  Array.from(byProject.entries()).forEach(([projectName, tasks]) => {
    console.log(`  Project: ${projectName}`);
    tasks.forEach(task => {
      const isComplete = task.status === 'done' || task.status === 'pr_created' ||
        ((task.status === 'human_review' || task.status === 'ai_review') && task.progress === 100);
      console.log(`    - ${task.taskId}: ${task.status} ${task.progress}% [${task.source}] ${isComplete ? 'DONE' : '...'}`);
    });
  });

  // All active tasks gone AND we've seen tasks before → all work complete
  if (activeTasks.length === 0 && (hasSeenActiveTasks || statuses.length > 0)) {
    console.log(`[Monitor] ALL tasks complete! (${terminalTasks.length} done + ${completeTasks.length} at review 100%)`);
    return { complete: true, hasActive };
  }

  return { complete: false, hasActive };
}

function triggerShutdown(delaySeconds: number): void {
  console.log(`\n[Monitor] ALL TASKS COMPLETE!`);
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

  let seenActive = false;

  const poll = () => {
    const statuses = getTaskStatuses(projectPaths);

    if (statuses.length === 0) {
      console.log('[Monitor] No tasks found across all projects, waiting...');
      setTimeout(poll, POLL_INTERVAL_MS);
      return;
    }

    const result = areAllTasksComplete(statuses, seenActive);
    if (result.hasActive) {
      seenActive = true;
    }

    if (result.complete) {
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
