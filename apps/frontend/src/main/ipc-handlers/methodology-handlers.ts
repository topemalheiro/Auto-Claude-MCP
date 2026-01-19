/**
 * IPC handlers for methodology plugin operations.
 *
 * Handles methodology checking, installation, configuration,
 * and version compatibility checks for project-level methodology settings.
 */

import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult } from '../../shared/types';
import type {
  ProjectMethodologyConfig,
  MethodologyInstallResult,
  MethodologyCompatibilityResult
} from '../../shared/types/methodology';
import {
  checkInstalled,
  install,
  getConfig,
  saveConfig,
  checkCompatibility,
  listAvailable
} from '../methodology';

/**
 * Register all methodology-related IPC handlers.
 */
export function registerMethodologyHandlers(): void {
  // Check if methodology is installed in project
  ipcMain.handle(
    IPC_CHANNELS.METHODOLOGY_CHECK_INSTALLED,
    async (
      _,
      projectPath: string,
      name: string
    ): Promise<IPCResult<MethodologyInstallResult>> => {
      try {
        const result = await checkInstalled(projectPath, name);
        return { success: true, data: result };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to check installation'
        };
      }
    }
  );

  // Install methodology
  ipcMain.handle(
    IPC_CHANNELS.METHODOLOGY_INSTALL,
    async (
      _,
      projectPath: string,
      name: string,
      version?: string
    ): Promise<IPCResult<MethodologyInstallResult>> => {
      try {
        const result = await install(projectPath, name, version);
        return { success: true, data: result };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to install methodology'
        };
      }
    }
  );

  // Get project's methodology config
  ipcMain.handle(
    IPC_CHANNELS.METHODOLOGY_GET_CONFIG,
    async (
      _,
      projectPath: string
    ): Promise<IPCResult<ProjectMethodologyConfig | null>> => {
      try {
        const config = await getConfig(projectPath);
        return { success: true, data: config };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get config'
        };
      }
    }
  );

  // Save project's methodology config
  ipcMain.handle(
    IPC_CHANNELS.METHODOLOGY_SAVE_CONFIG,
    async (
      _,
      projectPath: string,
      config: ProjectMethodologyConfig
    ): Promise<IPCResult<void>> => {
      try {
        await saveConfig(projectPath, config);
        return { success: true, data: undefined };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to save config'
        };
      }
    }
  );

  // List available methodologies with their sources
  ipcMain.handle(
    IPC_CHANNELS.METHODOLOGY_LIST_AVAILABLE,
    async (): Promise<IPCResult<ReturnType<typeof listAvailable>>> => {
      try {
        const methodologies = listAvailable();
        return { success: true, data: methodologies };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to list methodologies'
        };
      }
    }
  );

  // Check version compatibility
  ipcMain.handle(
    IPC_CHANNELS.METHODOLOGY_CHECK_COMPATIBILITY,
    async (
      _,
      name: string,
      version: string
    ): Promise<IPCResult<MethodologyCompatibilityResult>> => {
      try {
        const result = checkCompatibility(name, version);
        return { success: true, data: result };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to check compatibility'
        };
      }
    }
  );
}
