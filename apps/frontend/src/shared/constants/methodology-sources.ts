/**
 * Methodology plugin source definitions for multiple distribution types.
 *
 * This mirrors the backend sources.py configuration, enabling consistent
 * handling of methodology sources across frontend and backend.
 *
 * Plugin Classification:
 * - Native: The built-in AutoClaude methodology (not a plugin, always available)
 * - Verified: Plugins maintained and tested by Auto Claude team
 * - Community: Third-party/user-created plugins without verification guarantee
 */

/**
 * Distribution source types for methodology plugins.
 */
export type SourceType = 'native' | 'npm' | 'github' | 'local';

/**
 * Verification status for methodology plugins.
 */
export type VerificationStatus = 'native' | 'verified' | 'community';

/**
 * Configuration for a methodology's distribution source.
 */
export interface MethodologySource {
  /** Distribution source type */
  type: SourceType;
  /** Verification status */
  verification: VerificationStatus;
  /** Package identifier (NPM: package name, GitHub: owner/repo) */
  packageName?: string;
  /** Override default install command */
  installCommand?: string;
  /** Command to check installed version */
  versionCommand?: string;
  /** Minimum supported version for verified plugins */
  minVersion: string;
  /** Maximum supported version (exclusive) */
  maxVersion?: string;
}

/**
 * Registry of known methodologies and their sources.
 * Verified plugins are maintained by Auto Claude and tested for compatibility.
 */
export const METHODOLOGY_SOURCES: Record<string, MethodologySource> = {
  native: {
    type: 'native',
    verification: 'native',
    minVersion: '1.0.0',
  },
  bmad: {
    type: 'npm',
    verification: 'verified',
    packageName: 'bmad-method',
    installCommand: 'npx bmad-method@alpha install',
    versionCommand: 'npx bmad-method@alpha --version',
    minVersion: '1.0.0',
  },
};

/**
 * Get the source configuration for a methodology.
 */
export function getMethodologySource(name: string): MethodologySource | undefined {
  return METHODOLOGY_SOURCES[name];
}

/**
 * Check if a methodology is verified (maintained by Auto Claude team).
 */
export function isVerifiedMethodology(name: string): boolean {
  const source = getMethodologySource(name);
  if (!source) return false;
  return source.verification === 'native' || source.verification === 'verified';
}

/**
 * Check if a methodology is the native (built-in) methodology.
 */
export function isNativeMethodology(name: string): boolean {
  const source = getMethodologySource(name);
  if (!source) return false;
  return source.verification === 'native';
}

/**
 * Get the install command for a methodology.
 */
export function getInstallCommand(name: string): string | undefined {
  const source = getMethodologySource(name);
  if (!source || source.type === 'native') return undefined;
  return source.installCommand;
}

/**
 * List all registered methodology names.
 */
export function listAvailableMethodologyNames(): string[] {
  return Object.keys(METHODOLOGY_SOURCES);
}

/**
 * User-friendly display names for verification statuses.
 */
export const VERIFICATION_DISPLAY_NAMES: Record<VerificationStatus, string> = {
  native: 'Built-in',
  verified: 'Verified',
  community: 'Community',
};

/**
 * User-friendly display names for source types.
 */
export const SOURCE_TYPE_DISPLAY_NAMES: Record<SourceType, string> = {
  native: 'Built-in',
  npm: 'NPM Package',
  github: 'GitHub',
  local: 'Local',
};
