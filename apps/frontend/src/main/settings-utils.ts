/**
 * Shared settings utilities for main process
 *
 * This module provides low-level settings file operations used by both
 * the main process startup (index.ts) and the IPC handlers (settings-handlers.ts).
 *
 * NOTE: This module intentionally does NOT perform migrations or auto-detection.
 * Those are handled by the IPC handlers where they have full context.
 */

import { app } from 'electron';
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs';
import { promises as fsPromises } from 'fs';
import path from 'path';

/**
 * Get the path to the settings file
 */
export function getSettingsPath(): string {
  return path.join(app.getPath('userData'), 'settings.json');
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

  try {
    const content = readFileSync(settingsPath, 'utf-8');
    return JSON.parse(content);
  } catch (error: unknown) {
    // ENOENT (file not found) or parse error - return undefined so caller uses defaults
    const errorCode = (error as NodeJS.ErrnoException)?.code;
    if (errorCode !== 'ENOENT') {
      // Log unexpected errors but don't crash
      console.error('Settings file read error:', error instanceof Error ? error.message : String(error));
    }
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
    const content = await fsPromises.readFile(settingsPath, 'utf-8');
    return JSON.parse(content);
  } catch (error: unknown) {
    // ENOENT (file not found) or parse error - return undefined so caller uses defaults
    // Use a type guard to check error code without triggering TOCTOU alerts
    const err = error as NodeJS.ErrnoException;
    if (err?.code === 'ENOENT') {
      // File not found is expected - return undefined
      return undefined;
    }
    // Log unexpected errors but don't crash
    console.error('Settings file async read error:', error instanceof Error ? error.message : String(error));
    return undefined;
  }
}
