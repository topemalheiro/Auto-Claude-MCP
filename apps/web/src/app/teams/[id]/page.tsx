"use client";

import { useTeam, useTeamMembers } from "@/hooks";
import { useParams } from "next/navigation";

export default function TeamPage() {
  const params = useParams();
  const teamId = params.id as string;
  const { team, isLoading } = useTeam(teamId);
  const { members, inviteMember, removeMember } = useTeamMembers(teamId);

  if (isLoading) {
    return <div className="p-8">Loading team...</div>;
  }

  if (!team) {
    return <div className="p-8">Team not found</div>;
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold">{(team as any).name}</h1>
      <h2 className="mt-8 text-xl font-semibold">Members</h2>
      <ul className="mt-4 space-y-2">
        {members.map((member: any) => (
          <li key={member._id} className="flex items-center justify-between rounded-lg border p-4">
            <span>{member.userId}</span>
            <span className="text-gray-500">{member.role}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
