"use client";

import { useQuery, useMutation } from "convex/react";

/**
 * Hook for managing agent sessions via Convex.
 * Provides real-time terminal streaming via Convex subscriptions.
 * Used by @auto-claude/ui Terminal component.
 */
export function useAgentSession(sessionId: string) {
  // TODO: Uncomment when Convex API is generated
  // This automatically subscribes to real-time updates!
  // const session = useQuery(api.agentSessions.getSession, { sessionId });

  return {
    session: null,
    output: "",
    lastChunk: "",
    status: "completed" as const,
    isLoading: false,
  };
}

export function useSpecSessions(specId: string) {
  // TODO: Uncomment when Convex API is generated
  // const sessions = useQuery(api.agentSessions.getSpecSessions, { specId });
  // const startSession = useMutation(api.agentSessions.startSession);

  const sessions: never[] = [];

  return {
    sessions,
    isLoading: false,
    startSession: async () => {
      // TODO: return startSession({ specId });
    },
  };
}
