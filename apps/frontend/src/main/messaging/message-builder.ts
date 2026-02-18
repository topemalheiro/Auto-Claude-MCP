/**
 * Message Builder for MCP Messaging System
 *
 * Renders message templates with task data.
 * Reuses patterns from rdr-handlers.ts:gatherRichTaskInfo().
 */

import { readFileSync, existsSync } from 'fs';
import * as path from 'path';
import type { MessagingConfig } from '../../shared/types/messaging';

interface TaskContext {
  specId: string;
  taskName: string;
  taskStatus: string;
  projectName: string;
  phases: Array<{
    name: string;
    status: string;
    subtasks: Array<{ name?: string; description?: string; status: string }>;
  }>;
}

/**
 * Gather task info from implementation_plan.json (reuses RDR pattern)
 */
export function gatherTaskContext(
  specId: string,
  projectPath: string,
  projectName: string
): TaskContext {
  // Check worktree first (fresher data), then main
  const worktreePlanPath = path.join(
    projectPath, '.auto-claude', 'worktrees', 'tasks', specId,
    '.auto-claude', 'specs', specId, 'implementation_plan.json'
  );
  const mainPlanPath = path.join(
    projectPath, '.auto-claude', 'specs', specId, 'implementation_plan.json'
  );

  const planPath = existsSync(worktreePlanPath) ? worktreePlanPath : mainPlanPath;

  let plan: Record<string, unknown> = {};
  if (existsSync(planPath)) {
    try {
      plan = JSON.parse(readFileSync(planPath, 'utf-8'));
    } catch {
      // Graceful fallback on parse error
    }
  }

  const phases = Array.isArray(plan.phases) ? plan.phases : [];

  return {
    specId,
    taskName: (plan.feature as string) || specId,
    taskStatus: (plan.status as string) || 'unknown',
    projectName,
    phases: phases.map((p: Record<string, unknown>) => ({
      name: (p.name as string) || 'Phase',
      status: (p.status as string) || 'unknown',
      subtasks: (Array.isArray(p.subtasks) ? p.subtasks : (Array.isArray((p as Record<string, unknown>).chunks) ? (p as Record<string, unknown>).chunks : []))
        .map((s: Record<string, unknown>) => ({
          name: s.name as string | undefined,
          description: s.description as string | undefined,
          status: (s.status as string) || 'unknown',
        })),
    })),
  };
}

/**
 * Build a subtask summary string from task context
 */
function buildSubtaskSummary(ctx: TaskContext): string {
  if (ctx.phases.length === 0) {
    return 'No phases/subtasks found.';
  }

  const lines: string[] = [];
  for (const phase of ctx.phases) {
    lines.push(`## ${phase.name} [${phase.status}]`);
    for (const sub of phase.subtasks) {
      const icon = sub.status === 'completed' ? '[x]' : '[ ]';
      const label = sub.name || sub.description || 'Unnamed subtask';
      lines.push(`  ${icon} ${label}`);
    }
  }
  return lines.join('\n');
}

/**
 * Count completed/total subtasks
 */
function countSubtasks(ctx: TaskContext): { completed: number; total: number } {
  const all = ctx.phases.flatMap(p => p.subtasks);
  return {
    completed: all.filter(s => s.status === 'completed').length,
    total: all.length,
  };
}

/**
 * Render a message template with task context variables
 */
export function buildMessage(config: MessagingConfig, ctx: TaskContext): string {
  const { completed, total } = countSubtasks(ctx);

  let message = config.messageTemplate
    .replace(/\{\{taskName\}\}/g, ctx.taskName)
    .replace(/\{\{taskStatus\}\}/g, ctx.taskStatus)
    .replace(/\{\{specId\}\}/g, ctx.specId)
    .replace(/\{\{projectName\}\}/g, ctx.projectName)
    .replace(/\{\{completedCount\}\}/g, String(completed))
    .replace(/\{\{totalCount\}\}/g, String(total));

  // Only include subtask summary if includeTaskInfo is enabled
  if (config.includeTaskInfo) {
    const summary = buildSubtaskSummary(ctx);
    message = message.replace(/\{\{subtaskSummary\}\}/g, summary);
  } else {
    message = message.replace(/\{\{subtaskSummary\}\}/g, '(task info hidden)');
  }

  // Append full subtask details if includeTaskInfo is ON and not in template
  if (config.includeTaskInfo && !config.messageTemplate.includes('{{subtaskSummary}}')) {
    const summary = buildSubtaskSummary(ctx);
    message += `\n\n--- Subtask Details ---\n${summary}`;
  }

  return message;
}
