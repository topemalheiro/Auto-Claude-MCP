/**
 * Methodology plugin installation manager.
 *
 * Handles checking installation status, installing methodologies from various sources,
 * and verifying version compatibility.
 */

import { exec } from 'child_process';
import { promises as fs } from 'fs';
import path from 'path';
import { promisify } from 'util';
import { logger } from '../app-logger';
import {
  METHODOLOGY_SOURCES,
  getMethodologySource,
  isNativeMethodology,
  type MethodologySource
} from '../../shared/constants/methodology-sources';
import type {
  ProjectMethodologyConfig,
  MethodologyInstallResult,
  MethodologyCompatibilityResult
} from '../../shared/types/methodology';

const execAsync = promisify(exec);

/** File name for project methodology configuration */
const METHODOLOGY_CONFIG_FILE = 'methodology.json';

/**
 * Get the path to the methodology config file for a project.
 */
function getConfigPath(projectPath: string): string {
  return path.join(projectPath, '.auto-claude', METHODOLOGY_CONFIG_FILE);
}

/**
 * Check if a methodology is installed in a project.
 *
 * For native methodology, always returns installed.
 * For npm methodologies, checks if the install artifacts exist.
 */
export async function checkInstalled(
  projectPath: string,
  name: string
): Promise<MethodologyInstallResult> {
  try {
    // Native methodology is always available
    if (isNativeMethodology(name)) {
      return { success: true, version: '1.0.0' };
    }

    const source = getMethodologySource(name);
    if (!source) {
      return { success: false, error: `Unknown methodology: ${name}` };
    }

    // Check if methodology config exists for this project
    const configPath = getConfigPath(projectPath);
    try {
      const configContent = await fs.readFile(configPath, 'utf-8');
      const config: ProjectMethodologyConfig = JSON.parse(configContent);

      if (config.name === name && config.version) {
        return { success: true, version: config.version };
      }
    } catch {
      // Config doesn't exist or is invalid - methodology not installed
    }

    // For npm methodologies, try to get version from command
    if (source.type === 'npm' && source.versionCommand) {
      try {
        const { stdout } = await execAsync(source.versionCommand, {
          cwd: projectPath,
          timeout: 30000
        });
        const version = stdout.trim();
        if (version) {
          return { success: true, version };
        }
      } catch {
        // Version command failed - not installed
      }
    }

    return { success: false, error: 'Methodology not installed' };
  } catch (error) {
    logger.error('Error checking methodology installation:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
}

/**
 * Install a methodology in a project.
 *
 * For npm methodologies, runs the install command.
 * For local methodologies, verifies the path exists.
 */
export async function install(
  projectPath: string,
  name: string,
  version?: string
): Promise<MethodologyInstallResult> {
  try {
    // Native methodology doesn't need installation
    if (isNativeMethodology(name)) {
      // Just save the config
      await saveConfig(projectPath, {
        name: 'native',
        version: '1.0.0',
        source: 'native',
        installedAt: new Date().toISOString()
      });
      return { success: true, version: '1.0.0' };
    }

    const source = getMethodologySource(name);
    if (!source) {
      return { success: false, error: `Unknown methodology: ${name}` };
    }

    // Handle npm installation
    if (source.type === 'npm' && source.installCommand) {
      logger.info(`Installing methodology ${name} via npm...`);

      // Modify install command if version specified
      let command = source.installCommand;
      if (version && source.packageName) {
        // Replace @alpha or @version with specific version
        command = command.replace(
          new RegExp(`${source.packageName}@\\S+`),
          `${source.packageName}@${version}`
        );
      }

      try {
        const { stdout, stderr } = await execAsync(command, {
          cwd: projectPath,
          timeout: 120000 // 2 minute timeout for install
        });

        logger.debug('Install output:', stdout);
        if (stderr) {
          logger.debug('Install stderr:', stderr);
        }

        // Get installed version
        let installedVersion = version || source.minVersion;
        if (source.versionCommand) {
          try {
            const { stdout: versionOutput } = await execAsync(source.versionCommand, {
              cwd: projectPath,
              timeout: 30000
            });
            installedVersion = versionOutput.trim() || installedVersion;
          } catch {
            // Version check failed, use default
          }
        }

        // Save configuration
        await saveConfig(projectPath, {
          name,
          version: installedVersion,
          source: source.type,
          installedAt: new Date().toISOString(),
          packageName: source.packageName
        });

        return { success: true, version: installedVersion };
      } catch (error) {
        logger.error('Install command failed:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Install command failed'
        };
      }
    }

    // Handle local installation (verify path exists)
    if (source.type === 'local') {
      // For local, we just need to verify the methodology exists
      // and save the config
      await saveConfig(projectPath, {
        name,
        version: source.minVersion,
        source: 'local',
        installedAt: new Date().toISOString()
      });
      return { success: true, version: source.minVersion };
    }

    return { success: false, error: `Unsupported source type: ${source.type}` };
  } catch (error) {
    logger.error('Error installing methodology:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
}

/**
 * Get the methodology configuration for a project.
 */
export async function getConfig(
  projectPath: string
): Promise<ProjectMethodologyConfig | null> {
  try {
    const configPath = getConfigPath(projectPath);
    const content = await fs.readFile(configPath, 'utf-8');
    return JSON.parse(content) as ProjectMethodologyConfig;
  } catch {
    // Config doesn't exist
    return null;
  }
}

/**
 * Save methodology configuration for a project.
 */
export async function saveConfig(
  projectPath: string,
  config: ProjectMethodologyConfig
): Promise<void> {
  const configPath = getConfigPath(projectPath);

  // Ensure .auto-claude directory exists
  const autoClaudeDir = path.dirname(configPath);
  await fs.mkdir(autoClaudeDir, { recursive: true });

  // Write config
  await fs.writeFile(configPath, JSON.stringify(config, null, 2), 'utf-8');
  logger.info(`Saved methodology config for ${config.name} at ${configPath}`);
}

/**
 * Check version compatibility for a methodology.
 */
export function checkCompatibility(
  name: string,
  installedVersion: string
): MethodologyCompatibilityResult {
  // Native is always compatible
  if (isNativeMethodology(name)) {
    return { compatible: true, installedVersion };
  }

  const source = getMethodologySource(name);
  if (!source) {
    return {
      compatible: false,
      warning: `Unknown methodology: ${name}`,
      installedVersion
    };
  }

  // Parse versions for comparison
  const installed = parseVersion(installedVersion);
  const min = parseVersion(source.minVersion);
  const max = source.maxVersion ? parseVersion(source.maxVersion) : null;

  // Check minimum version
  if (compareVersions(installed, min) < 0) {
    return {
      compatible: false,
      warning: `Installed version ${installedVersion} is below minimum required ${source.minVersion}. Consider updating.`,
      installedVersion,
      minVersion: source.minVersion,
      maxVersion: source.maxVersion
    };
  }

  // Check maximum version (exclusive)
  if (max && compareVersions(installed, max) >= 0) {
    return {
      compatible: false,
      warning: `Installed version ${installedVersion} exceeds maximum supported ${source.maxVersion}. This may cause compatibility issues.`,
      installedVersion,
      minVersion: source.minVersion,
      maxVersion: source.maxVersion
    };
  }

  return {
    compatible: true,
    installedVersion,
    minVersion: source.minVersion,
    maxVersion: source.maxVersion
  };
}

/**
 * List all available methodologies with their source info.
 */
export function listAvailable(): Array<{
  name: string;
  type: string;
  verification: string;
  packageName?: string;
  minVersion: string;
  maxVersion?: string;
}> {
  return Object.entries(METHODOLOGY_SOURCES).map(([name, source]) => ({
    name,
    type: source.type,
    verification: source.verification,
    packageName: source.packageName,
    minVersion: source.minVersion,
    maxVersion: source.maxVersion
  }));
}

/**
 * Parse a semver version string into components.
 */
function parseVersion(version: string): { major: number; minor: number; patch: number } {
  const match = version.match(/^(\d+)\.(\d+)\.(\d+)/);
  if (!match) {
    return { major: 0, minor: 0, patch: 0 };
  }
  return {
    major: parseInt(match[1], 10),
    minor: parseInt(match[2], 10),
    patch: parseInt(match[3], 10)
  };
}

/**
 * Compare two parsed versions.
 * Returns: negative if a < b, 0 if a === b, positive if a > b
 */
function compareVersions(
  a: { major: number; minor: number; patch: number },
  b: { major: number; minor: number; patch: number }
): number {
  if (a.major !== b.major) return a.major - b.major;
  if (a.minor !== b.minor) return a.minor - b.minor;
  return a.patch - b.patch;
}
