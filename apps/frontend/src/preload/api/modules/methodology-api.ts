/**
 * Methodology Plugin API
 *
 * Exposes methodology installation, configuration, and compatibility checking
 * to the renderer for project-level methodology settings.
 */

import { ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '../../../shared/constants/ipc';
import type { IPCResult } from '../../../shared/types/common';
import type {
  ProjectMethodologyConfig,
  MethodologyInstallResult,
  MethodologyCompatibilityResult
} from '../../../shared/types/methodology';

export interface MethodologyAPI {
  /** Check if a methodology is installed in a project */
  checkMethodologyInstalled: (
    projectPath: string,
    name: string
  ) => Promise<IPCResult<MethodologyInstallResult>>;

  /** Install a methodology in a project */
  installMethodology: (
    projectPath: string,
    name: string,
    version?: string
  ) => Promise<IPCResult<MethodologyInstallResult>>;

  /** Get project's methodology configuration */
  getMethodologyConfig: (
    projectPath: string
  ) => Promise<IPCResult<ProjectMethodologyConfig | null>>;

  /** Save project's methodology configuration */
  saveMethodologyConfig: (
    projectPath: string,
    config: ProjectMethodologyConfig
  ) => Promise<IPCResult<void>>;

  /** List available methodologies with their sources */
  listAvailableMethodologies: () => Promise<IPCResult<Array<{
    name: string;
    type: string;
    verification: string;
    packageName?: string;
    minVersion: string;
    maxVersion?: string;
  }>>>;

  /** Check version compatibility for a methodology */
  checkMethodologyCompatibility: (
    name: string,
    version: string
  ) => Promise<IPCResult<MethodologyCompatibilityResult>>;
}

export function createMethodologyAPI(): MethodologyAPI {
  return {
    checkMethodologyInstalled: (projectPath: string, name: string) =>
      ipcRenderer.invoke(IPC_CHANNELS.METHODOLOGY_CHECK_INSTALLED, projectPath, name),

    installMethodology: (projectPath: string, name: string, version?: string) =>
      ipcRenderer.invoke(IPC_CHANNELS.METHODOLOGY_INSTALL, projectPath, name, version),

    getMethodologyConfig: (projectPath: string) =>
      ipcRenderer.invoke(IPC_CHANNELS.METHODOLOGY_GET_CONFIG, projectPath),

    saveMethodologyConfig: (projectPath: string, config: ProjectMethodologyConfig) =>
      ipcRenderer.invoke(IPC_CHANNELS.METHODOLOGY_SAVE_CONFIG, projectPath, config),

    listAvailableMethodologies: () =>
      ipcRenderer.invoke(IPC_CHANNELS.METHODOLOGY_LIST_AVAILABLE),

    checkMethodologyCompatibility: (name: string, version: string) =>
      ipcRenderer.invoke(IPC_CHANNELS.METHODOLOGY_CHECK_COMPATIBILITY, name, version),
  };
}
