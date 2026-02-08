/**
 * File system utilities for ideation operations
 */

import { existsSync, readFileSync, writeFileSync } from 'fs';
import path from 'path';
import type { RawIdeationData } from './types';

/**
 * Validate that a path is within the project directory to prevent path traversal attacks.
 * @param targetPath - The path to validate
 * @param basePath - The base directory that the target should be within
 * @throws Error if the target path escapes the base path
 */
function validatePathWithinBase(targetPath: string, basePath: string): void {
  const resolvedTarget = path.resolve(targetPath);
  const resolvedBase = path.resolve(basePath);

  if (!resolvedTarget.startsWith(resolvedBase + path.sep) && resolvedTarget !== resolvedBase) {
    throw new Error('Invalid path: path traversal detected');
  }
}

/**
 * Read ideation data from file
 */
export function readIdeationFile(ideationPath: string, basePath?: string): RawIdeationData | null {
  if (!existsSync(ideationPath)) {
    return null;
  }

  // Validate path stays within base directory if provided
  if (basePath) {
    try {
      validatePathWithinBase(ideationPath, basePath);
    } catch {
      throw new Error('Invalid ideation file path');
    }
  }

  try {
    const content = readFileSync(ideationPath, 'utf-8');
    return JSON.parse(content);
  } catch (error) {
    throw new Error(
      error instanceof Error ? error.message : 'Failed to read ideation file'
    );
  }
}

/**
 * Write ideation data to file
 */
export function writeIdeationFile(ideationPath: string, data: RawIdeationData, basePath?: string): void {
  // Validate path stays within base directory if provided
  if (basePath) {
    try {
      validatePathWithinBase(ideationPath, basePath);
    } catch {
      throw new Error('Invalid ideation file path');
    }
  }

  try {
    writeFileSync(ideationPath, JSON.stringify(data, null, 2), 'utf-8');
  } catch (error) {
    throw new Error(
      error instanceof Error ? error.message : 'Failed to write ideation file'
    );
  }
}

/**
 * Update timestamp for ideation data
 */
export function updateIdeationTimestamp(data: RawIdeationData): void {
  data.updated_at = new Date().toISOString();
}
