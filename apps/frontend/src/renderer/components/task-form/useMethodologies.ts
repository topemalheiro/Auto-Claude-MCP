/**
 * Hook for fetching available methodology plugins
 *
 * Fetches methodologies from the registry via IPC and optionally checks
 * installation status for a specific project.
 */

import { useState, useEffect, useCallback } from 'react';
import type { MethodologyInfo, MethodologyWithStatus } from '../../../shared/types/methodology';
import {
  METHODOLOGY_SOURCES,
  isVerifiedMethodology,
  isNativeMethodology
} from '../../../shared/constants/methodology-sources';

/**
 * Static methodology data as fallback.
 * Used when IPC calls fail or for initial loading.
 */
const STATIC_METHODOLOGIES: MethodologyInfo[] = [
  {
    name: 'native',
    version: '1.0.0',
    description: 'Built-in methodology with spec creation and implementation phases',
    author: 'Auto Claude',
    complexity_levels: ['quick', 'standard', 'complex'],
    execution_modes: ['full_auto', 'semi_auto'],
    is_verified: true,
  },
  {
    name: 'bmad',
    version: '1.0.0',
    description: 'BMAD (Business Model Agile Development) - structured approach with PRD, architecture, and story-driven development',
    author: 'BMad',
    complexity_levels: ['quick', 'standard', 'complex'],
    execution_modes: ['full_auto', 'semi_auto'],
    is_verified: true,
  },
];

export interface UseMethodologiesResult {
  /** List of available methodologies */
  methodologies: MethodologyInfo[];
  /** Whether methodologies are currently loading */
  isLoading: boolean;
  /** Error message if loading failed */
  error: string | null;
  /** Refetch methodologies */
  refetch: () => void;
}

export interface UseMethodologiesWithStatusResult {
  /** List of available methodologies with installation status */
  methodologies: MethodologyWithStatus[];
  /** Whether methodologies are currently loading */
  isLoading: boolean;
  /** Error message if loading failed */
  error: string | null;
  /** Refetch methodologies */
  refetch: () => void;
}

/**
 * Hook to fetch available methodology plugins
 *
 * @returns Object containing methodologies, loading state, and error
 */
export function useMethodologies(): UseMethodologiesResult {
  const [methodologies, setMethodologies] = useState<MethodologyInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadMethodologies = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Try to load from registry via IPC
      const result = await window.electronAPI.listAvailableMethodologies();
      if (result.success && result.data) {
        // Map registry data to MethodologyInfo
        const methodologyList: MethodologyInfo[] = result.data.map(m => ({
          name: m.name,
          version: m.minVersion,
          description: getMethodologyDescription(m.name),
          author: getMethodologyAuthor(m.name),
          complexity_levels: ['quick', 'standard', 'complex'],
          execution_modes: ['full_auto', 'semi_auto'],
          is_verified: m.verification === 'verified' || m.verification === 'native',
        }));
        setMethodologies(methodologyList);
      } else {
        // Fallback to static methodologies
        setMethodologies(STATIC_METHODOLOGIES);
      }
    } catch {
      // Fallback to static methodologies
      setMethodologies(STATIC_METHODOLOGIES);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMethodologies();
  }, [loadMethodologies]);

  return {
    methodologies,
    isLoading,
    error,
    refetch: loadMethodologies,
  };
}

/**
 * Hook to fetch methodologies with installation status for a specific project
 *
 * @param projectPath - Path to the project to check installation status
 * @returns Object containing methodologies with status, loading state, and error
 */
export function useMethodologiesWithStatus(
  projectPath: string | null
): UseMethodologiesWithStatusResult {
  const [methodologies, setMethodologies] = useState<MethodologyWithStatus[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadMethodologies = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Load available methodologies from registry
      const result = await window.electronAPI.listAvailableMethodologies();
      const methodologyList = result.success && result.data ? result.data : [];

      // Build methodology list with installation status
      const methodologiesWithStatus: MethodologyWithStatus[] = await Promise.all(
        methodologyList.map(async (m) => {
          let isInstalled = false;
          let version = m.minVersion;

          // Check installation status if project path provided
          if (projectPath) {
            if (isNativeMethodology(m.name)) {
              isInstalled = true;
            } else {
              const installResult = await window.electronAPI.checkMethodologyInstalled(
                projectPath,
                m.name
              );
              if (installResult.success && installResult.data?.success) {
                isInstalled = true;
                version = installResult.data.version || m.minVersion;
              }
            }
          }

          return {
            name: m.name,
            version,
            description: getMethodologyDescription(m.name),
            author: getMethodologyAuthor(m.name),
            complexity_levels: ['quick', 'standard', 'complex'],
            execution_modes: ['full_auto', 'semi_auto'],
            is_verified: m.verification === 'verified' || m.verification === 'native',
            isInstalled,
            sourceType: m.type as 'native' | 'npm' | 'github' | 'local',
            verification: m.verification as 'native' | 'verified' | 'community',
          };
        })
      );

      setMethodologies(methodologiesWithStatus);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load methodologies');
      // Fallback with basic status
      setMethodologies(STATIC_METHODOLOGIES.map(m => ({
        ...m,
        isInstalled: m.name === 'native',
        sourceType: 'native' as const,
        verification: 'native' as const,
      })));
    } finally {
      setIsLoading(false);
    }
  }, [projectPath]);

  useEffect(() => {
    loadMethodologies();
  }, [loadMethodologies]);

  return {
    methodologies,
    isLoading,
    error,
    refetch: loadMethodologies,
  };
}

/**
 * Get description for a methodology by name
 */
function getMethodologyDescription(name: string): string {
  const descriptions: Record<string, string> = {
    native: 'Built-in methodology with spec creation and implementation phases',
    bmad: 'BMAD (Business Model Agile Development) - structured approach with PRD, architecture, and story-driven development',
  };
  return descriptions[name] || '';
}

/**
 * Get author for a methodology by name
 */
function getMethodologyAuthor(name: string): string {
  const authors: Record<string, string> = {
    native: 'Auto Claude',
    bmad: 'BMad',
  };
  return authors[name] || 'Community';
}
