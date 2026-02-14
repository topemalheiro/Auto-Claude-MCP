"use client";

import { useQuery, useMutation } from "convex/react";

type PRStatus = "open" | "reviewing" | "approved" | "merged";

/**
 * Hook for managing PR queue via Convex.
 * Team+ feature - used by @auto-claude/ui components.
 */
export function usePRQueue(teamId: string, status?: PRStatus) {
  // TODO: Uncomment when Convex API is generated
  // const prs = useQuery(api.prQueue.getTeamPRs, { teamId, status });
  // const updateStatus = useMutation(api.prQueue.updatePRStatus);
  // const assignPR = useMutation(api.prQueue.assignPR);

  const prs: never[] = [];

  return {
    prs,
    isLoading: false,
    updateStatus: async (prId: string, newStatus: PRStatus) => {
      // TODO: return updateStatus({ prId, status: newStatus });
    },
    assignPR: async (prId: string, assigneeId: string | null) => {
      // TODO: return assignPR({ prId, assigneeId: assigneeId ?? undefined });
    },
  };
}

export function usePR(prId: string) {
  // TODO: Uncomment when Convex API is generated
  // const pr = useQuery(api.prQueue.getPR, { prId });

  return {
    pr: null,
    isLoading: false,
  };
}
