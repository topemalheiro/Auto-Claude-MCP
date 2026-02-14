"use client";

import { useQuery, useMutation } from "convex/react";

/**
 * Hook for managing specs via Convex.
 * Used by @auto-claude/ui components.
 */
export function useSpecs() {
  // TODO: Uncomment when Convex API is generated
  // const specs = useQuery(api.specs.getUserSpecs);
  // const createSpec = useMutation(api.specs.createSpec);
  // const updateSpec = useMutation(api.specs.updateSpec);
  // const deleteSpec = useMutation(api.specs.deleteSpec);

  const specs: never[] = [];

  return {
    specs,
    isLoading: false,
    createSpec: async (name: string, content: string) => {
      // TODO: return createSpec({ name, content });
    },
    updateSpec: async (id: string, updates: { name?: string; content?: string }) => {
      // TODO: return updateSpec({ specId: id, ...updates });
    },
    deleteSpec: async (id: string) => {
      // TODO: return deleteSpec({ specId: id });
    },
  };
}

export function useSpec(specId: string) {
  // TODO: Uncomment when Convex API is generated
  // const spec = useQuery(api.specs.getSpec, { specId });

  return {
    spec: null,
    isLoading: false,
  };
}
