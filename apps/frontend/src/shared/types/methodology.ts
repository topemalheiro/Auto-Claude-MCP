/**
 * Methodology plugin types for task execution
 */

import type { SourceType, VerificationStatus } from '../constants/methodology-sources';

/**
 * Information about an available methodology plugin
 */
export interface MethodologyInfo {
  /** Unique identifier for the methodology (e.g., 'native', 'bmad') */
  name: string;
  /** Semver version string */
  version: string;
  /** Human-readable description */
  description: string;
  /** Author name or organization */
  author: string;
  /** Supported complexity levels (e.g., ['quick', 'standard', 'complex']) */
  complexity_levels: string[];
  /** Supported execution modes (e.g., ['full_auto', 'semi_auto']) */
  execution_modes: string[];
  /** Whether this is a verified (bundled) plugin */
  is_verified: boolean;
  /** Install path of the methodology */
  install_path?: string;
}

/**
 * Project-level methodology configuration.
 * Stored in .auto-claude/methodology.json
 */
export interface ProjectMethodologyConfig {
  /** Name of the methodology (e.g., 'native', 'bmad') */
  name: string;
  /** Installed version of the methodology */
  version: string;
  /** How the methodology was installed */
  source: SourceType;
  /** ISO timestamp when the methodology was installed/configured */
  installedAt?: string;
  /** Package identifier for npm/github sources */
  packageName?: string;
}

/**
 * Result of a methodology installation operation
 */
export interface MethodologyInstallResult {
  /** Whether the installation was successful */
  success: boolean;
  /** Installed version (on success) */
  version?: string;
  /** Error message (on failure) */
  error?: string;
}

/**
 * Result of a methodology version compatibility check
 */
export interface MethodologyCompatibilityResult {
  /** Whether the version is compatible */
  compatible: boolean;
  /** Warning message if not fully compatible */
  warning?: string;
  /** Installed version being checked */
  installedVersion?: string;
  /** Minimum required version */
  minVersion?: string;
  /** Maximum supported version */
  maxVersion?: string;
}

/**
 * Extended methodology info with installation status
 */
export interface MethodologyWithStatus extends MethodologyInfo {
  /** Whether this methodology is installed in the current project */
  isInstalled: boolean;
  /** Source type (native, npm, github, local) */
  sourceType: SourceType;
  /** Verification status (native, verified, community) */
  verification: VerificationStatus;
  /** Compatibility status if version checked */
  compatibility?: MethodologyCompatibilityResult;
}
