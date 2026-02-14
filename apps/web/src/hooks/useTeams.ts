"use client";

import { useQuery, useMutation } from "convex/react";

/**
 * Hook for managing teams via Convex.
 * Used by @auto-claude/ui components.
 */
export function useTeams() {
  // TODO: Uncomment when Convex API is generated
  // const teams = useQuery(api.teams.getUserTeams);
  // const createTeam = useMutation(api.teams.createTeam);

  const teams: never[] = [];

  return {
    teams,
    isLoading: false,
    createTeam: async (name: string) => {
      // TODO: return createTeam({ name });
    },
  };
}

export function useTeam(teamId: string) {
  // TODO: Uncomment when Convex API is generated
  // const team = useQuery(api.teams.getTeam, { teamId });
  // const members = useQuery(api.teams.getTeamMembers, { teamId });

  return {
    team: null,
    members: [],
    isLoading: false,
  };
}

export function useTeamMembers(teamId: string) {
  // TODO: Uncomment when Convex API is generated
  // const members = useQuery(api.teams.getTeamMembers, { teamId });
  // const inviteMember = useMutation(api.teams.inviteMember);
  // const removeMember = useMutation(api.teams.removeMember);

  return {
    members: [],
    isLoading: false,
    inviteMember: async (email: string, role: "admin" | "member") => {
      // TODO: return inviteMember({ teamId, email, role });
    },
    removeMember: async (userId: string) => {
      // TODO: return removeMember({ teamId, userId });
    },
  };
}
