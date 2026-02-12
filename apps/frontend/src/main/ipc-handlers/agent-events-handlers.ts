import type { BrowserWindow } from "electron";
import path from "path";
import { existsSync, readFileSync, writeFileSync } from "fs";
import { IPC_CHANNELS, AUTO_BUILD_PATHS, getSpecsDir } from "../../shared/constants";
import type {
  SDKRateLimitInfo,
  AuthFailureInfo,
  ImplementationPlan,
  TaskExitReason,
  TaskRateLimitInfo,
} from "../../shared/types";
import { XSTATE_SETTLED_STATES, XSTATE_TO_PHASE, mapStateToLegacy } from "../../shared/state-machines";
import { AgentManager } from "../agent";
import type { ProcessType, ExecutionProgressData } from "../agent";
import { titleGenerator } from "../title-generator";
import { fileWatcher } from "../file-watcher";
import { notificationService } from "../notification-service";
import { persistPlanLastEventSync, getPlanPath, persistPlanPhaseSync, persistPlanStatusAndReasonSync } from "./task/plan-file-utils";
import { findTaskWorktree } from "../worktree-paths";
import { findTaskAndProject } from "./task/shared";
import { safeSendToRenderer } from "./utils";
import { getClaudeProfileManager } from "../claude-profile-manager";
import { taskStateManager } from "../task-state-manager";
import {
  getRateLimitForTask,
  clearRateLimitForTask,
  setRateLimitForTask,
} from "../rate-limit-detector";
import { startRateLimitWaitForTask } from "../rate-limit-waiter";
import { readSettingsFile } from "../settings-utils";
import { queueTaskForRdr } from "./rdr-handlers";

/**
 * Register all agent-events-related IPC handlers
 */
export function registerAgenteventsHandlers(
  agentManager: AgentManager,
  getMainWindow: () => BrowserWindow | null
): void {
  taskStateManager.configure(getMainWindow);

  // ============================================
  // Agent Manager Events → Renderer
  // ============================================

  agentManager.on("log", (taskId: string, log: string, projectId?: string) => {
    // Use projectId from event when available; fall back to lookup for backward compatibility
    if (!projectId) {
      const { project } = findTaskAndProject(taskId);
      projectId = project?.id;
    }
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.TASK_LOG, taskId, log, projectId);
  });

  agentManager.on("error", (taskId: string, error: string, projectId?: string) => {
    // Use projectId from event when available; fall back to lookup for backward compatibility
    if (!projectId) {
      const { project } = findTaskAndProject(taskId);
      projectId = project?.id;
    }
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.TASK_ERROR, taskId, error, projectId);
  });

  // Handle SDK rate limit events from agent manager
  agentManager.on("sdk-rate-limit", (rateLimitInfo: SDKRateLimitInfo) => {
    // Store rate limit for task so exit handler can detect rate limit crash
    if (rateLimitInfo.taskId) {
      console.warn(`[AgentEvents] Storing rate limit for task ${rateLimitInfo.taskId}`);
      setRateLimitForTask(rateLimitInfo.taskId, rateLimitInfo);
    }
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.CLAUDE_SDK_RATE_LIMIT, rateLimitInfo);
  });

  // Handle SDK rate limit events from title generator
  titleGenerator.on("sdk-rate-limit", (rateLimitInfo: SDKRateLimitInfo) => {
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.CLAUDE_SDK_RATE_LIMIT, rateLimitInfo);
  });

  // Handle auth failure events (401 errors requiring re-authentication)
  agentManager.on("auth-failure", (taskId: string, authFailure: {
    profileId?: string;
    failureType?: 'missing' | 'invalid' | 'expired' | 'unknown';
    message?: string;
    originalError?: string;
  }) => {
    console.warn(`[AgentEvents] Auth failure detected for task ${taskId}:`, authFailure);

    // Get profile name for display
    const profileManager = getClaudeProfileManager();
    const profile = authFailure.profileId
      ? profileManager.getProfile(authFailure.profileId)
      : profileManager.getActiveProfile();

    const authFailureInfo: AuthFailureInfo = {
      profileId: authFailure.profileId || profile?.id || 'unknown',
      profileName: profile?.name,
      failureType: authFailure.failureType || 'unknown',
      message: authFailure.message || 'Authentication failed. Please re-authenticate.',
      originalError: authFailure.originalError,
      taskId,
      detectedAt: new Date(),
    };

    safeSendToRenderer(getMainWindow, IPC_CHANNELS.CLAUDE_AUTH_FAILURE, authFailureInfo);
  });

  agentManager.on("exit", (taskId: string, code: number | null, processType: ProcessType, projectId?: string) => {
    // Use projectId from event to scope the lookup (prevents cross-project contamination)
    const { task: exitTask, project: exitProject } = findTaskAndProject(taskId, projectId);
    const exitProjectId = exitProject?.id || projectId;

    taskStateManager.handleProcessExited(taskId, code, exitTask, exitProject);

    // Send final plan state to renderer BEFORE unwatching
    // This ensures the renderer has the final subtask data (fixes 0/0 subtask bug)
    const finalPlan = fileWatcher.getCurrentPlan(taskId);
    if (finalPlan) {
      safeSendToRenderer(
        getMainWindow,
        IPC_CHANNELS.TASK_PROGRESS,
        taskId,
        finalPlan,
        exitProjectId
      );
    }

    fileWatcher.unwatch(taskId);

    if (processType === "spec-creation") {
      console.warn(`[Task ${taskId}] Spec creation completed with code ${code}`);
      return;
    }

    const { task, project } = findTaskAndProject(taskId, projectId);
    if (!task || !project) return;

    const taskTitle = task.title || task.specId;
    if (code === 0) {
      notificationService.notifyReviewNeeded(taskTitle, project.id, taskId);
    } else {
      // Non-zero exit code - check if this was a rate limit crash
      const rateLimitInfo = getRateLimitForTask(taskId);

      if (rateLimitInfo) {
        const exitReason: TaskExitReason = 'rate_limit_crash';
        console.warn(`[Task ${taskId}] Task crashed due to rate limit - will auto-resume when limit resets`);

        // Persist rate limit info to plan
        try {
          const mainPlanPath = getPlanPath(project, task);
          const planContent = readFileSync(mainPlanPath, 'utf-8');
          const plan = JSON.parse(planContent);
          plan.exitReason = exitReason;
          plan.rateLimitInfo = {
            resetAt: rateLimitInfo.resetAtDate?.toISOString(),
            limitType: rateLimitInfo.limitType,
            profileId: rateLimitInfo.profileId,
            detectedAt: rateLimitInfo.detectedAt.toISOString(),
          } as TaskRateLimitInfo;
          writeFileSync(mainPlanPath, JSON.stringify(plan, null, 2));
          console.warn(`[Task ${taskId}] Persisted rate limit crash info to plan`);
        } catch (err) {
          console.error(`[Task ${taskId}] Failed to persist rate limit info:`, err);
        }

        // Check if auto-resume is enabled in settings
        const currentSettings = readSettingsFile();
        const autoResumeEnabled = currentSettings?.autoResumeAfterRateLimit === true;

        // Start auto-wait for rate limit reset (only if enabled)
        if (autoResumeEnabled) {
          const capturedProjectId = project.id;
          const mainWindow = getMainWindow();
          startRateLimitWaitForTask(taskId, rateLimitInfo, mainWindow, () => {
            console.warn(`[Task ${taskId}] Rate limit reset - task can now be resumed`);
            clearRateLimitForTask(taskId);

            // Trigger RDR to send prompt to Claude Code for auto-recovery
            console.warn(`[Task ${taskId}] Triggering RDR processing after rate limit reset`);
            const taskInfo = {
              specId: taskId,
              status: 'human_review' as const,
              reviewReason: 'rate_limit_reset',
              description: `Rate limit reset at ${new Date().toISOString()}. Task ready to resume.`,
              subtasks: []
            };
            queueTaskForRdr(capturedProjectId, taskInfo);
          });
          console.warn(`[Task ${taskId}] Auto-resume enabled - waiting for rate limit reset`);
        } else {
          console.warn(`[Task ${taskId}] Auto-resume disabled - task will stay in Human Review until manually resumed`);
          clearRateLimitForTask(taskId);
        }

        // Notify renderer that task crashed due to rate limit
        safeSendToRenderer(
          getMainWindow,
          IPC_CHANNELS.TASK_RATE_LIMIT_CRASH,
          taskId,
          project.id,
          { ...rateLimitInfo, autoResumeEnabled }
        );

        notificationService.notify(
          'Task Paused - Rate Limit',
          autoResumeEnabled
            ? `${taskTitle} paused due to rate limit. Will auto-resume when limit resets.`
            : `${taskTitle} paused due to rate limit. Manual restart required (auto-resume disabled).`,
          { type: 'info' }
        );
      } else {
        // Regular error - not rate limit
        notificationService.notifyTaskFailed(taskTitle, project.id, taskId);

        // Persist exit reason to plan
        try {
          const mainPlanPath = getPlanPath(project, task);
          const planContent = readFileSync(mainPlanPath, 'utf-8');
          const plan = JSON.parse(planContent);
          plan.exitReason = 'error';
          writeFileSync(mainPlanPath, JSON.stringify(plan, null, 2));
        } catch (err) {
          console.error(`[Task ${taskId}] Failed to persist exit reason:`, err);
        }
      }
    }
  });

  agentManager.on("task-event", (taskId: string, event, projectId?: string) => {
    console.debug(`[agent-events-handlers] Received task-event for ${taskId}:`, event.type, event);

    if (taskStateManager.getLastSequence(taskId) === undefined) {
      const { task, project } = findTaskAndProject(taskId, projectId);
      if (task && project) {
        try {
          const planPath = getPlanPath(project, task);
          const planContent = readFileSync(planPath, "utf-8");
          const plan = JSON.parse(planContent);
          const lastSeq = plan?.lastEvent?.sequence;
          if (typeof lastSeq === "number" && lastSeq >= 0) {
            taskStateManager.setLastSequence(taskId, lastSeq);
          }
        } catch {
          // Ignore missing/invalid plan files
        }
      }
    }

    const { task, project } = findTaskAndProject(taskId, projectId);
    if (!task || !project) {
      console.debug(`[agent-events-handlers] No task/project found for ${taskId}`);
      return;
    }

    console.debug(`[agent-events-handlers] Task state before handleTaskEvent:`, {
      status: task.status,
      reviewReason: task.reviewReason,
      phase: task.executionProgress?.phase
    });

    const accepted = taskStateManager.handleTaskEvent(taskId, event, task, project);
    console.debug(`[agent-events-handlers] Event ${event.type} accepted: ${accepted}`);
    if (!accepted) {
      return;
    }

    const mainPlanPath = getPlanPath(project, task);
    persistPlanLastEventSync(mainPlanPath, event);

    const worktreePath = findTaskWorktree(project.path, task.specId);
    if (worktreePath) {
      const specsBaseDir = getSpecsDir(project.autoBuildPath);
      const worktreePlanPath = path.join(
        worktreePath,
        specsBaseDir,
        task.specId,
        AUTO_BUILD_PATHS.IMPLEMENTATION_PLAN
      );
      if (existsSync(worktreePlanPath)) {
        persistPlanLastEventSync(worktreePlanPath, event);
      }
    }
  });

  agentManager.on("execution-progress", (taskId: string, progress: ExecutionProgressData, projectId?: string) => {
    // Use projectId from event to scope the lookup (prevents cross-project contamination)
    const { task, project } = findTaskAndProject(taskId, projectId);
    const taskProjectId = project?.id || projectId;

    // Check if XState has already established a terminal/review state for this task.
    // XState is the source of truth for status. When XState is in a terminal state
    // (e.g., plan_review after PLANNING_COMPLETE), execution-progress events from the
    // agent process are stale and must not overwrite XState's persisted status.
    //
    // Example: When requireReviewBeforeCoding=true, the process exits with code 1 after
    // PLANNING_COMPLETE. The exit handler emits execution-progress with phase='failed',
    // which would incorrectly overwrite status='human_review' with status='error' via
    // persistPlanPhaseSync, and send a 'failed' phase to the renderer overwriting the
    // 'planning' phase that XState already emitted via emitPhaseFromState.
    const currentXState = taskStateManager.getCurrentState(taskId);
    const xstateInTerminalState = currentXState && XSTATE_SETTLED_STATES.has(currentXState);

    // Persist phase to plan file for restoration on app refresh
    // Must persist to BOTH main project and worktree (if exists) since task may be loaded from either
    if (task && project && progress.phase && !xstateInTerminalState) {
      const mainPlanPath = getPlanPath(project, task);
      persistPlanPhaseSync(mainPlanPath, progress.phase, project.id);

      // Also persist to worktree if task has one
      const worktreePath = findTaskWorktree(project.path, task.specId);
      if (worktreePath) {
        const specsBaseDir = getSpecsDir(project.autoBuildPath);
        const worktreePlanPath = path.join(
          worktreePath,
          specsBaseDir,
          task.specId,
          AUTO_BUILD_PATHS.IMPLEMENTATION_PLAN
        );
        if (existsSync(worktreePlanPath)) {
          persistPlanPhaseSync(worktreePlanPath, progress.phase, project.id);
        }
      }
    } else if (xstateInTerminalState && progress.phase) {
      console.debug(`[agent-events-handlers] Skipping persistPlanPhaseSync for ${taskId}: XState in '${currentXState}', not overwriting with phase '${progress.phase}'`);
    }

    // Skip sending execution-progress to renderer when XState has settled.
    // XState's emitPhaseFromState already sent the correct phase to the renderer.
    if (xstateInTerminalState) {
      console.debug(`[agent-events-handlers] Skipping execution-progress to renderer for ${taskId}: XState in '${currentXState}', ignoring phase '${progress.phase}'`);
      return;
    }
    safeSendToRenderer(
      getMainWindow,
      IPC_CHANNELS.TASK_EXECUTION_PROGRESS,
      taskId,
      progress,
      taskProjectId
    );
  });

  // ============================================
  // File Watcher Events → Renderer
  // ============================================

  fileWatcher.on("progress", (taskId: string, plan: ImplementationPlan) => {
    // File watcher events don't carry projectId — fall back to lookup
    const { task, project } = findTaskAndProject(taskId);
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.TASK_PROGRESS, taskId, plan, project?.id);

    // Re-stamp XState status fields if the backend overwrote the plan file without them.
    // The planner agent writes implementation_plan.json via the Write tool, which replaces
    // the entire file and strips the frontend's status/xstateState/executionPhase fields.
    // This causes tasks to snap back to backlog on refresh.
    const planWithStatus = plan as { xstateState?: string; executionPhase?: string; status?: string };
    const currentXState = taskStateManager.getCurrentState(taskId);
    if (currentXState && !planWithStatus.xstateState && task && project) {
      console.debug(`[agent-events-handlers] Re-stamping XState status on plan file for ${taskId} (state: ${currentXState})`);
      const mainPlanPath = getPlanPath(project, task);
      const { status, reviewReason } = mapStateToLegacy(currentXState);
      const phase = XSTATE_TO_PHASE[currentXState] || 'idle';
      persistPlanStatusAndReasonSync(mainPlanPath, status, reviewReason, project.id, currentXState, phase);

      // Also re-stamp worktree copy if it exists
      const worktreePath = findTaskWorktree(project.path, task.specId);
      if (worktreePath) {
        const specsBaseDir = getSpecsDir(project.autoBuildPath);
        const worktreePlanPath = path.join(
          worktreePath,
          specsBaseDir,
          task.specId,
          AUTO_BUILD_PATHS.IMPLEMENTATION_PLAN
        );
        if (existsSync(worktreePlanPath)) {
          persistPlanStatusAndReasonSync(worktreePlanPath, status, reviewReason, project.id, currentXState, phase);
        }
      }
    }
  });

  fileWatcher.on("error", (taskId: string, error: string) => {
    // File watcher events don't carry projectId — fall back to lookup
    const { project } = findTaskAndProject(taskId);
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.TASK_ERROR, taskId, error, project?.id);
  });

  // ============================================
  // Specs Directory Watcher Events → Renderer
  // (For MCP-created tasks to trigger auto-refresh)
  // ============================================

  fileWatcher.on("specs-changed", (data: { projectId: string; projectPath: string; specDir: string; specId: string }) => {
    console.log(`[AgentEvents] specs-changed event received!`);
    console.log(`[AgentEvents] - specId: ${data.specId}`);
    console.log(`[AgentEvents] - projectId: ${data.projectId}`);
    console.log(`[AgentEvents] - specDir: ${data.specDir}`);

    // Invalidate the project's task cache
    projectStore.invalidateTasksCache(data.projectId);
    console.log(`[AgentEvents] Task cache invalidated for project ${data.projectId}`);

    // Notify renderer to refresh task list
    console.log(`[AgentEvents] Sending TASK_LIST_REFRESH to renderer for project ${data.projectId}`);
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.TASK_LIST_REFRESH, data.projectId);

    // Trigger auto-refresh if enabled in settings
    console.log(`[AgentEvents] Sending TASK_AUTO_REFRESH_TRIGGER for specs-changed`);
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.TASK_AUTO_REFRESH_TRIGGER, {
      reason: 'specs-changed',
      projectId: data.projectId,
      specId: data.specId
    });
  });

  // Handle MCP-requested task starts (task-start-requested event from file watcher)
  fileWatcher.on("task-start-requested", (data: { projectId: string; projectPath: string; specDir: string; specId: string }) => {
    console.log(`[AgentEvents] task-start-requested event received!`);
    console.log(`[AgentEvents] - specId: ${data.specId}`);
    console.log(`[AgentEvents] - projectId: ${data.projectId}`);

    // Invalidate the project's task cache
    projectStore.invalidateTasksCache(data.projectId);

    // Notify renderer to auto-start the task
    // The renderer will call TASK_START IPC to begin execution
    console.log(`[AgentEvents] Sending TASK_AUTO_START to renderer for task ${data.specId}`);
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.TASK_AUTO_START, data.projectId, data.specId);

    // Trigger auto-refresh if enabled in settings
    console.log(`[AgentEvents] Sending TASK_AUTO_REFRESH_TRIGGER for task-start-requested`);
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.TASK_AUTO_REFRESH_TRIGGER, {
      reason: 'task-start-requested',
      projectId: data.projectId,
      specId: data.specId
    });
  });

  // Handle task status changes from file watcher (for RDR auto-recovery)
  fileWatcher.on("task-status-changed", (data: {
    projectId: string;
    taskId: string;
    specId: string;
    oldStatus: TaskStatus;
    newStatus: TaskStatus;
  }) => {
    console.log(`[AgentEvents] task-status-changed event received!`);
    console.log(`[AgentEvents] - specId: ${data.specId}`);
    console.log(`[AgentEvents] - projectId: ${data.projectId}`);
    console.log(`[AgentEvents] - status change: ${data.oldStatus} → ${data.newStatus}`);

    // Invalidate the project's task cache to trigger UI refresh
    projectStore.invalidateTasksCache(data.projectId);

    // Notify renderer to refresh task list with animation
    console.log(`[AgentEvents] Sending TASK_STATUS_CHANGED to renderer`);
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.TASK_STATUS_CHANGED, data);

    // Trigger auto-refresh if enabled in settings
    console.log(`[AgentEvents] Sending TASK_AUTO_REFRESH_TRIGGER for task-status-changed`);
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.TASK_AUTO_REFRESH_TRIGGER, {
      reason: 'task-status-changed',
      projectId: data.projectId,
      specId: data.specId
    });

    // Detect task regression: was started/running but went back to backlog
    if (data.newStatus === 'backlog' && data.oldStatus !== 'backlog') {
      console.warn(`[AgentEvents] REGRESSION DETECTED: Task ${data.specId} went ${data.oldStatus} → backlog`);
      safeSendToRenderer(getMainWindow, IPC_CHANNELS.TASK_REGRESSION_DETECTED, {
        projectId: data.projectId,
        specId: data.specId,
        oldStatus: data.oldStatus,
        newStatus: data.newStatus,
        timestamp: new Date().toISOString()
      });
    }
  });

  // Start watching specs directories for all existing projects
  startWatchingAllProjectSpecs();
}

/**
 * Start watching specs directory for all projects.
 * Called on app startup and when projects are added.
 */
export function startWatchingAllProjectSpecs(): void {
  const projects = projectStore.getProjects();
  console.log(`[AgentEvents] startWatchingAllProjectSpecs called - found ${projects.length} projects`);
  for (const project of projects) {
    console.log(`[AgentEvents] Project: ${project.name || project.id}, autoBuildPath: ${project.autoBuildPath || 'NOT SET'}`);
    if (project.autoBuildPath) {
      startWatchingProjectSpecs(project.id, project.path, project.autoBuildPath);
    }
  }
}

/**
 * Start watching specs directory for a single project.
 */
export function startWatchingProjectSpecs(projectId: string, projectPath: string, autoBuildPath: string): void {
  const specsDir = getSpecsDir(autoBuildPath);
  const fullPath = path.join(projectPath, specsDir);
  console.log(`[AgentEvents] startWatchingProjectSpecs called:`);
  console.log(`[AgentEvents] - projectId: ${projectId}`);
  console.log(`[AgentEvents] - projectPath: ${projectPath}`);
  console.log(`[AgentEvents] - autoBuildPath: ${autoBuildPath}`);
  console.log(`[AgentEvents] - specsDir: ${specsDir}`);
  console.log(`[AgentEvents] - fullPath: ${fullPath}`);
  console.log(`[AgentEvents] - isWatchingSpecs: ${fileWatcher.isWatchingSpecs(projectId)}`);

  if (!fileWatcher.isWatchingSpecs(projectId)) {
    console.log(`[AgentEvents] Starting specs watcher for project ${projectId} at ${fullPath}`);
    fileWatcher.watchSpecsDirectory(projectId, projectPath, specsDir);
  } else {
    console.log(`[AgentEvents] Already watching specs for project ${projectId}`);
  }
}
