/**
 * Hook for fetching available methodology plugins
 *
 * Currently returns static methodology data. Future implementation will
 * fetch from the methodology registry via IPC (Epic 6).
 */

import { useState, useEffect, useCallback } from 'react';
import type { MethodologyInfo } from '../../../shared/types/methodology';

/**
 * Static methodology data for initial implementation.
 * Will be replaced with IPC call to methodology registry in Epic 6.
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
      // Epic 6 will replace this with: await window.electronAPI.getMethodologies()
      setMethodologies(STATIC_METHODOLOGIES);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load methodologies');
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
