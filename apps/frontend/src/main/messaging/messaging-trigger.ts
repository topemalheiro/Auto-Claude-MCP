/**
 * Messaging Trigger for MCP Messaging System
 *
 * Called when a task transitions status. Matches task tags against
 * active messaging configs and delivers messages via existing
 * RDR infrastructure (sendRdrMessage / sendMessageToWindow).
 */

import { readFileSync, existsSync } from 'fs';
import * as path from 'path';
import type { BrowserWindow } from 'electron';
import type { TaskStatus } from '../../shared/types';
import type { MessagingConfig, MessagingTriggerStatus } from '../../shared/types/messaging';
import { IPC_CHANNELS } from '../../shared/constants/ipc';
import { readSettingsFile } from '../settings-utils';
import { projectStore } from '../project-store';
import { buildMessage, gatherTaskContext } from './message-builder';
import { safeSendToRenderer } from '../ipc-handlers/utils';
import { DEFAULT_MESSAGE_TEMPLATE } from '../../shared/types/messaging';

/**
 * Read task tags from task_metadata.json
 */
function getTaskTags(projectPath: string, specId: string): string[] {
  const worktreeMeta = path.join(
    projectPath, '.auto-claude', 'worktrees', 'tasks', specId,
    '.auto-claude', 'specs', specId, 'task_metadata.json'
  );
  const mainMeta = path.join(
    projectPath, '.auto-claude', 'specs', specId, 'task_metadata.json'
  );

  const metaPath = existsSync(worktreeMeta) ? worktreeMeta : mainMeta;
  if (!existsSync(metaPath)) return [];

  try {
    const meta = JSON.parse(readFileSync(metaPath, 'utf-8'));
    return Array.isArray(meta.tags) ? meta.tags : [];
  } catch {
    return [];
  }
}

/**
 * Deliver a message using an RDR mechanism
 */
async function deliverViaRdrMechanism(
  message: string,
  mechanismId: string | undefined
): Promise<void> {
  const settings = readSettingsFile() ?? {};
  const mechanisms = (settings.rdrMechanisms as Array<{ id: string; template: string }>) ?? [];

  // Find the mechanism (or use active/first)
  const mechanism = mechanismId
    ? mechanisms.find(m => m.id === mechanismId)
    : mechanisms.find(m => m.id === (settings.activeMechanismId as string)) ?? mechanisms[0];

  if (!mechanism) {
    console.warn('[Messaging] No RDR mechanism found for delivery');
    return;
  }

  const { sendRdrMessage } = await import('../platform/rdr-message-sender');
  const result = await sendRdrMessage('messaging', message, mechanism.template);

  if (result.success) {
    console.log('[Messaging] Message delivered via RDR mechanism');
  } else {
    console.error('[Messaging] RDR delivery failed:', result.error);
  }
}

/**
 * Deliver a message to a specific window by title
 */
async function deliverToWindow(
  message: string,
  windowTitle: string
): Promise<void> {
  try {
    const { sendMessageToWindow } = await import('../platform/windows/window-manager');
    const result = await sendMessageToWindow(windowTitle, message);
    if (result.success) {
      console.log(`[Messaging] Message delivered to window: ${windowTitle}`);
    } else {
      console.error(`[Messaging] Window delivery failed: ${result.error}`);
    }
  } catch (error) {
    console.error('[Messaging] Window delivery error:', error);
  }
}

/**
 * Check and trigger messages when a task transitions to a matching status.
 *
 * Called from TaskStateManager.emitStatus() subscriber.
 */
export async function checkAndTriggerMessages(
  specId: string,
  newStatus: TaskStatus,
  projectId: string,
  projectPath: string,
  projectName: string,
  getMainWindow?: () => BrowserWindow | null
): Promise<void> {
  try {
    // Get global configs
    const settings = readSettingsFile() ?? {};
    const allConfigs = (settings.messagingConfigs as MessagingConfig[]) ?? [];

    if (allConfigs.length === 0) return;

    // Get project's active config IDs
    const project = projectStore.getProjects?.()?.find(p => p.id === projectId);
    const activeConfigIds = project?.settings?.activeMessagingConfigIds ?? [];

    if (activeConfigIds.length === 0) return;

    // Get task tags
    const taskTags = getTaskTags(projectPath, specId);
    if (taskTags.length === 0) return;

    // Find matching configs: enabled + active for project + matching tag + matching status
    const matchingConfigs = allConfigs.filter(config =>
      config.enabled &&
      activeConfigIds.includes(config.id) &&
      taskTags.includes(config.triggerTag) &&
      config.triggerStatus === (newStatus as MessagingTriggerStatus)
    );

    if (matchingConfigs.length === 0) return;

    console.log(`[Messaging] ${matchingConfigs.length} config(s) matched for ${specId} -> ${newStatus}`);

    // Gather task context once for all matching configs
    const ctx = gatherTaskContext(specId, projectPath, projectName);

    // Deliver each matching config's message
    for (const config of matchingConfigs) {
      const message = buildMessage(config, ctx);

      if (config.receiver.type === 'rdr_mechanism') {
        await deliverViaRdrMechanism(message, config.receiver.mechanismId);
      } else if (config.receiver.type === 'specific_window') {
        if (config.receiver.windowTitle) {
          await deliverToWindow(message, config.receiver.windowTitle);
        }
      }

      // Notify renderer that a message was triggered
      if (getMainWindow) {
        safeSendToRenderer(
          getMainWindow,
          IPC_CHANNELS.MESSAGING_TRIGGERED,
          { specId, configName: config.name }
        );
      }

      console.log(`[Messaging] Triggered "${config.name}" for ${specId}`);
    }
  } catch (error) {
    console.error('[Messaging] Trigger check failed:', error);
  }
}

/**
 * Send a test message using a config (for the Test button in settings)
 */
export async function sendTestMessage(config: MessagingConfig): Promise<void> {
  const testCtx = {
    specId: 'test-001',
    taskName: 'Test Task',
    taskStatus: config.triggerStatus,
    projectName: 'Test Project',
    phases: [
      {
        name: 'Phase 1',
        status: 'completed',
        subtasks: [
          { name: 'Subtask A', status: 'completed' },
          { name: 'Subtask B', status: 'completed' },
          { name: 'Subtask C', status: 'in_progress' },
        ],
      },
    ],
  };

  const message = buildMessage(config, testCtx);

  if (config.receiver.type === 'rdr_mechanism') {
    await deliverViaRdrMechanism(message, config.receiver.mechanismId);
  } else if (config.receiver.type === 'specific_window' && config.receiver.windowTitle) {
    await deliverToWindow(message, config.receiver.windowTitle);
  } else {
    throw new Error('No valid receiver configured');
  }
}
