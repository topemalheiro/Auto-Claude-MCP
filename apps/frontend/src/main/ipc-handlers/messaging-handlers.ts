/**
 * MCP Messaging System IPC Handlers
 *
 * CRUD for global messaging configs/tags (stored in AppSettings)
 * and per-task tag assignments (stored in task_metadata.json).
 */

import { ipcMain } from 'electron';
import { readFileSync, writeFileSync, existsSync } from 'fs';
import * as path from 'path';
import { IPC_CHANNELS } from '../../shared/constants/ipc';
import type { IPCResult } from '../../shared/types/common';
import type { MessagingConfig, TaskTag } from '../../shared/types/messaging';
import { readSettingsFile, writeSettingsFile } from '../settings-utils';
import { projectStore } from '../project-store';

/**
 * Read task_metadata.json from a spec directory
 */
function readTaskMetadata(specDir: string): Record<string, unknown> | null {
  const metaPath = path.join(specDir, 'task_metadata.json');
  if (!existsSync(metaPath)) {
    return null;
  }
  try {
    return JSON.parse(readFileSync(metaPath, 'utf-8'));
  } catch {
    return null;
  }
}

/**
 * Write task_metadata.json to a spec directory
 */
function writeTaskMetadata(specDir: string, metadata: Record<string, unknown>): void {
  const metaPath = path.join(specDir, 'task_metadata.json');
  writeFileSync(metaPath, JSON.stringify(metadata, null, 2), 'utf-8');
}

/**
 * Resolve the spec directory for a task (checks both main and worktree)
 */
function resolveSpecDir(projectPath: string, specId: string): string {
  const mainDir = path.join(projectPath, '.auto-claude', 'specs', specId);
  const worktreeDir = path.join(
    projectPath, '.auto-claude', 'worktrees', 'tasks', specId,
    '.auto-claude', 'specs', specId
  );
  // Prefer worktree if it exists
  if (existsSync(worktreeDir)) {
    return worktreeDir;
  }
  return mainDir;
}

export function registerMessagingHandlers(): void {
  // ── Get global messaging configs + tags ──
  ipcMain.handle(
    IPC_CHANNELS.MESSAGING_GET_CONFIGS,
    async (): Promise<IPCResult<{ tags: TaskTag[]; configs: MessagingConfig[] }>> => {
      try {
        const settings = readSettingsFile() ?? {};
        return {
          success: true,
          data: {
            tags: (settings.messagingTags as TaskTag[]) ?? [],
            configs: (settings.messagingConfigs as MessagingConfig[]) ?? [],
          },
        };
      } catch (error) {
        console.error('[Messaging] Failed to get configs:', error);
        return { success: false, error: String(error) };
      }
    }
  );

  // ── Save global messaging configs + tags ──
  ipcMain.handle(
    IPC_CHANNELS.MESSAGING_SAVE_CONFIGS,
    async (
      _,
      data: { tags: TaskTag[]; configs: MessagingConfig[] }
    ): Promise<IPCResult> => {
      try {
        const settings = readSettingsFile() ?? {};
        const updated = {
          ...settings,
          messagingTags: data.tags,
          messagingConfigs: data.configs,
        };
        writeSettingsFile(updated);
        console.log(`[Messaging] Saved ${data.tags.length} tags, ${data.configs.length} configs`);
        return { success: true };
      } catch (error) {
        console.error('[Messaging] Failed to save configs:', error);
        return { success: false, error: String(error) };
      }
    }
  );

  // ── Set tags on a task ──
  ipcMain.handle(
    IPC_CHANNELS.MESSAGING_SET_TASK_TAGS,
    async (
      _,
      projectPath: string,
      specId: string,
      tagIds: string[]
    ): Promise<IPCResult> => {
      try {
        const specDir = resolveSpecDir(projectPath, specId);
        const metadata = readTaskMetadata(specDir) ?? {};
        const updated = { ...metadata, tags: tagIds };
        writeTaskMetadata(specDir, updated);

        // Also update main specs dir if worktree was used
        const mainDir = path.join(projectPath, '.auto-claude', 'specs', specId);
        if (specDir !== mainDir && existsSync(mainDir)) {
          const mainMeta = readTaskMetadata(mainDir) ?? {};
          writeTaskMetadata(mainDir, { ...mainMeta, tags: tagIds });
        }

        console.log(`[Messaging] Set tags for ${specId}: [${tagIds.join(', ')}]`);
        return { success: true };
      } catch (error) {
        console.error('[Messaging] Failed to set task tags:', error);
        return { success: false, error: String(error) };
      }
    }
  );

  // ── Get tags for a task ──
  ipcMain.handle(
    IPC_CHANNELS.MESSAGING_GET_TASK_TAGS,
    async (
      _,
      projectPath: string,
      specId: string
    ): Promise<IPCResult<string[]>> => {
      try {
        const specDir = resolveSpecDir(projectPath, specId);
        const metadata = readTaskMetadata(specDir);
        return {
          success: true,
          data: (metadata?.tags as string[]) ?? [],
        };
      } catch (error) {
        console.error('[Messaging] Failed to get task tags:', error);
        return { success: false, error: String(error) };
      }
    }
  );

  // ── Set per-project active messaging config IDs ──
  ipcMain.handle(
    IPC_CHANNELS.MESSAGING_SET_ACTIVE_CONFIGS,
    async (
      _,
      projectId: string,
      configIds: string[]
    ): Promise<IPCResult> => {
      try {
        const project = projectStore.updateProjectSettings(projectId, {
          activeMessagingConfigIds: configIds,
        });
        if (!project) {
          return { success: false, error: 'Project not found' };
        }
        console.log(`[Messaging] Set active configs for project ${projectId}: [${configIds.join(', ')}]`);
        return { success: true };
      } catch (error) {
        console.error('[Messaging] Failed to set active configs:', error);
        return { success: false, error: String(error) };
      }
    }
  );

  // ── Test a messaging config (send test message) ──
  ipcMain.handle(
    IPC_CHANNELS.MESSAGING_TEST_CONFIG,
    async (
      _,
      config: MessagingConfig
    ): Promise<IPCResult> => {
      try {
        // Lazy import to avoid circular deps
        const { sendTestMessage } = await import('../messaging/messaging-trigger');
        await sendTestMessage(config);
        return { success: true };
      } catch (error) {
        console.error('[Messaging] Test message failed:', error);
        return { success: false, error: String(error) };
      }
    }
  );

  console.log('[Messaging] IPC handlers registered');
}
