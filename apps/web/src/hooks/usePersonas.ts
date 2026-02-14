"use client";

import { useQuery, useMutation } from "convex/react";

/**
 * Hook for managing personas via Convex.
 * Pro+ feature - used by @auto-claude/ui components.
 */
export function usePersonas() {
  // TODO: Uncomment when Convex API is generated
  // const personas = useQuery(api.personas.getUserPersonas);
  // const createPersona = useMutation(api.personas.createPersona);
  // const updatePersona = useMutation(api.personas.updatePersona);
  // const deletePersona = useMutation(api.personas.deletePersona);

  const personas: never[] = [];

  return {
    personas,
    isLoading: false,
    createPersona: async (name: string, description: string, traits: string[]) => {
      // TODO: return createPersona({ name, description, traits });
    },
    updatePersona: async (
      id: string,
      updates: { name?: string; description?: string; traits?: string[] }
    ) => {
      // TODO: return updatePersona({ personaId: id, ...updates });
    },
    deletePersona: async (id: string) => {
      // TODO: return deletePersona({ personaId: id });
    },
  };
}

export function usePersona(personaId: string) {
  // TODO: Uncomment when Convex API is generated
  // const persona = useQuery(api.personas.getPersona, { personaId });

  return {
    persona: null,
    isLoading: false,
  };
}
