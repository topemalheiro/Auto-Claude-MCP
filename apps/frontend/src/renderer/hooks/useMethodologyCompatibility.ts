/**
 * Hook for checking methodology version compatibility when a project is activated.
 *
 * This hook monitors project changes and checks if the installed methodology
 * version is compatible with Auto Claude requirements. It returns warning
 * information when incompatibilities are detected.
 */

import { useState, useEffect, useCallback } from 'react';
import { useProjectStore } from '../stores/project-store';
import type { MethodologyCompatibilityResult, ProjectMethodologyConfig } from '../../shared/types/methodology';
import { isNativeMethodology } from '../../shared/constants/methodology-sources';

export interface MethodologyWarningInfo {
  /** Whether a warning should be displayed */
  showWarning: boolean;
  /** The methodology name */
  methodologyName: string;
  /** The installed version */
  installedVersion: string;
  /** Warning message from compatibility check */
  warningMessage: string;
  /** Minimum required version */
  minVersion?: string;
  /** Maximum supported version */
  maxVersion?: string;
}

export interface UseMethodologyCompatibilityResult {
  /** Warning information if incompatibility detected */
  warning: MethodologyWarningInfo | null;
  /** Whether compatibility check is in progress */
  isChecking: boolean;
  /** Dismiss the current warning */
  dismissWarning: () => void;
  /** Choose to continue anyway with current version */
  continueAnyway: () => void;
  /** Switch to native methodology */
  switchToNative: () => Promise<void>;
  /** Recheck compatibility */
  recheckCompatibility: () => void;
}

/**
 * Hook to check methodology compatibility for the active project.
 *
 * Version checking occurs:
 * - On project switch (when activeProjectId changes)
 * - On component mount (app startup)
 * - When explicitly triggered via recheckCompatibility
 *
 * Does NOT check:
 * - On every task creation (too frequent)
 */
export function useMethodologyCompatibility(): UseMethodologyCompatibilityResult {
  const [warning, setWarning] = useState<MethodologyWarningInfo | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [dismissedForSession, setDismissedForSession] = useState<Set<string>>(new Set());

  const activeProjectId = useProjectStore((state) => state.activeProjectId);
  const getActiveProject = useProjectStore((state) => state.getActiveProject);

  const checkCompatibility = useCallback(async () => {
    const project = getActiveProject();
    if (!project) {
      setWarning(null);
      return;
    }

    setIsChecking(true);

    try {
      // Get methodology config for the project
      const configResult = await window.electronAPI.getMethodologyConfig(project.path);

      if (!configResult.success || !configResult.data) {
        // No methodology config - assume native, which is always compatible
        setWarning(null);
        setIsChecking(false);
        return;
      }

      const config: ProjectMethodologyConfig = configResult.data;

      // Native methodology is always compatible
      if (isNativeMethodology(config.name)) {
        setWarning(null);
        setIsChecking(false);
        return;
      }

      // Check if already dismissed for this project+methodology combo in this session
      const dismissKey = `${project.id}:${config.name}:${config.version}`;
      if (dismissedForSession.has(dismissKey)) {
        setWarning(null);
        setIsChecking(false);
        return;
      }

      // Check version compatibility
      const compatResult = await window.electronAPI.checkMethodologyCompatibility(
        config.name,
        config.version
      );

      if (!compatResult.success || !compatResult.data) {
        // Error checking compatibility - don't show warning
        setWarning(null);
        setIsChecking(false);
        return;
      }

      const compatibility: MethodologyCompatibilityResult = compatResult.data;

      if (!compatibility.compatible && compatibility.warning) {
        setWarning({
          showWarning: true,
          methodologyName: config.name,
          installedVersion: config.version,
          warningMessage: compatibility.warning,
          minVersion: compatibility.minVersion,
          maxVersion: compatibility.maxVersion,
        });
      } else {
        setWarning(null);
      }
    } catch (error) {
      console.error('Error checking methodology compatibility:', error);
      setWarning(null);
    } finally {
      setIsChecking(false);
    }
  }, [getActiveProject, dismissedForSession]);

  // Check compatibility when active project changes
  useEffect(() => {
    checkCompatibility();
  }, [activeProjectId, checkCompatibility]);

  const dismissWarning = useCallback(() => {
    const project = getActiveProject();
    if (project && warning) {
      // Remember dismissal for this session
      const dismissKey = `${project.id}:${warning.methodologyName}:${warning.installedVersion}`;
      setDismissedForSession((prev) => new Set(prev).add(dismissKey));
    }
    setWarning(null);
  }, [getActiveProject, warning]);

  const continueAnyway = useCallback(() => {
    dismissWarning();
  }, [dismissWarning]);

  const switchToNative = useCallback(async () => {
    const project = getActiveProject();
    if (!project) return;

    try {
      // Save native methodology config
      await window.electronAPI.saveMethodologyConfig(project.path, {
        name: 'native',
        version: '1.0.0',
        source: 'native',
        installedAt: new Date().toISOString(),
      });

      // Update project settings
      await window.electronAPI.updateProjectSettings(project.id, {
        methodology: 'native',
      });

      // Clear warning
      setWarning(null);
    } catch (error) {
      console.error('Error switching to native methodology:', error);
    }
  }, [getActiveProject]);

  return {
    warning,
    isChecking,
    dismissWarning,
    continueAnyway,
    switchToNative,
    recheckCompatibility: checkCompatibility,
  };
}
