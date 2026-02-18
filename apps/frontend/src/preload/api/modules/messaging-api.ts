/**
 * Messaging System Preload API
 *
 * Exposes messaging config and tag management to the renderer.
 */

import { ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '../../../shared/constants/ipc';
import type { IPCResult } from '../../../shared/types/common';
import type { MessagingConfig, TaskTag } from '../../../shared/types/messaging';

export interface MessagingAPI {
  /** Get global messaging tags and configs */
  getMessagingConfigs: () => Promise<IPCResult<{ tags: TaskTag[]; configs: MessagingConfig[] }>>;
  /** Save global messaging tags and configs */
  saveMessagingConfigs: (data: { tags: TaskTag[]; configs: MessagingConfig[] }) => Promise<IPCResult>;
  /** Set tags on a specific task */
  setTaskTags: (projectPath: string, specId: string, tagIds: string[]) => Promise<IPCResult>;
  /** Get tags for a specific task */
  getTaskTags: (projectPath: string, specId: string) => Promise<IPCResult<string[]>>;
  /** Set per-project active messaging config IDs */
  setActiveMessagingConfigs: (projectId: string, configIds: string[]) => Promise<IPCResult>;
  /** Send a test message using a config */
  testMessagingConfig: (config: MessagingConfig) => Promise<IPCResult>;
  /** Listen for messaging triggered events */
  onMessagingTriggered: (callback: (data: { specId: string; configName: string }) => void) => () => void;
}

export function createMessagingAPI(): MessagingAPI {
  return {
    getMessagingConfigs: () =>
      ipcRenderer.invoke(IPC_CHANNELS.MESSAGING_GET_CONFIGS),

    saveMessagingConfigs: (data) =>
      ipcRenderer.invoke(IPC_CHANNELS.MESSAGING_SAVE_CONFIGS, data),

    setTaskTags: (projectPath, specId, tagIds) =>
      ipcRenderer.invoke(IPC_CHANNELS.MESSAGING_SET_TASK_TAGS, projectPath, specId, tagIds),

    getTaskTags: (projectPath, specId) =>
      ipcRenderer.invoke(IPC_CHANNELS.MESSAGING_GET_TASK_TAGS, projectPath, specId),

    setActiveMessagingConfigs: (projectId, configIds) =>
      ipcRenderer.invoke(IPC_CHANNELS.MESSAGING_SET_ACTIVE_CONFIGS, projectId, configIds),

    testMessagingConfig: (config) =>
      ipcRenderer.invoke(IPC_CHANNELS.MESSAGING_TEST_CONFIG, config),

    onMessagingTriggered: (callback) => {
      const handler = (_: unknown, data: { specId: string; configName: string }) => callback(data);
      ipcRenderer.on(IPC_CHANNELS.MESSAGING_TRIGGERED, handler);
      return () => ipcRenderer.removeListener(IPC_CHANNELS.MESSAGING_TRIGGERED, handler);
    },
  };
}
