/**
 * Shared settings utilities for main process
 *
 * This module provides low-level settings file operations used by both
 * the main process startup (index.ts) and the IPC handlers (settings-handlers.ts).
 *
 * NOTE: This module intentionally does NOT perform migrations or auto-detection.
 * Those are handled by the IPC handlers where they have full context.
 */

import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs';
import { promises as fsPromises } from 'fs';
import path from 'path';
import os from 'os';

// Try to import Electron app, but handle standalone MCP mode gracefully
let electronApp: { getPath: (name: string) => string } | undefined;
try {
  // Dynamic import to handle cases where electron mock isn't fully functional
  const electron = require('electron');
  electronApp = electron?.app;
} catch {
  // Running in standalone mode without Electron
  electronApp = undefined;
}

/**
 * Get the user data directory, with fallback for standalone MCP mode
 */
function getUserDataPath(): string {
  // Try Electron app first
  if (electronApp?.getPath) {
    try {
      return electronApp.getPath('userData');
    } catch {
      // Fall through to manual calculation
    }
  }

  // Fallback: Calculate userData path manually (same logic as Electron)
  const homedir = os.homedir();
  if (process.platform === 'win32') {
    return path.join(homedir, 'AppData', 'Roaming', 'auto-claude-ui');
  } else if (process.platform === 'darwin') {
    return path.join(homedir, 'Library', 'Application Support', 'auto-claude-ui');
  } else {
    return path.join(homedir, '.config', 'auto-claude-ui');
  }
}

/**
 * Get the path to the settings file
 */
export function getSettingsPath(): string {
  return path.join(getUserDataPath(), 'settings.json');
}

/**
 * Read and parse settings from disk.
 * Returns the raw parsed settings object, or undefined if the file doesn't exist or fails to parse.
 *
 * This function does NOT merge with defaults or perform any migrations.
 * Callers are responsible for merging with DEFAULT_APP_SETTINGS.
 */
export function readSettingsFile(): Record<string, unknown> | undefined {
  const settingsPath = getSettingsPath();

  if (!existsSync(settingsPath)) {
    return undefined;
  }

  try {
    const content = readFileSync(settingsPath, 'utf-8');
    return JSON.parse(content);
  } catch {
    // Return undefined on parse error - caller will use defaults
    return undefined;
  }
}

/**
 * Write settings to disk.
 *
 * @param settings - The settings object to write
 */
export function writeSettingsFile(settings: Record<string, unknown>): void {
  const settingsPath = getSettingsPath();

  // Ensure the directory exists
  const dir = path.dirname(settingsPath);
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }

  writeFileSync(settingsPath, JSON.stringify(settings, null, 2), 'utf-8');
}

/**
 * Read and parse settings from disk asynchronously.
 * Returns the raw parsed settings object, or undefined if the file doesn't exist or fails to parse.
 *
 * This is the non-blocking version of readSettingsFile, safe to use in Electron main process
 * without blocking the event loop.
 *
 * This function does NOT merge with defaults or perform any migrations.
 * Callers are responsible for merging with DEFAULT_APP_SETTINGS.
 */
export async function readSettingsFileAsync(): Promise<Record<string, unknown> | undefined> {
  const settingsPath = getSettingsPath();

  try {
    await fsPromises.access(settingsPath);
  } catch {
    return undefined;
  }

  try {
    const content = await fsPromises.readFile(settingsPath, 'utf-8');
    return JSON.parse(content);
  } catch {
    // Return undefined on parse error - caller will use defaults
    return undefined;
  }
}
