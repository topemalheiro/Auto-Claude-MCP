/**
 * Methodology plugin types for task execution
 */

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
