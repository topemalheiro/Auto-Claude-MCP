"use client";

import { useTeams } from "@/hooks";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useCloudMode } from "@/hooks/useCloudMode";
import { CloudUpgradeCTA } from "@/components/CloudUpgradeCTA";
import { hasTierAccess } from "@/lib/tiers";
import { formatPrice } from "@/lib/pricing";
import { useTranslation } from "react-i18next";

function CloudTeams() {
  const user = useCurrentUser();
  const { teams, isLoading, createTeam } = useTeams();
  const { t } = useTranslation(["pages", "common"]);

  // Team feature requires Team tier or higher
  const hasTeamAccess = hasTierAccess(user?.tier, "team");

  if (!hasTeamAccess) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 p-8">
        <h1 className="text-2xl font-bold">{t("pages:teams.singleTitle")}</h1>
        <p className="text-gray-600">{t("pages:teams.description")}</p>
        <a
          href="/settings"
          className="rounded-lg bg-blue-600 px-6 py-3 text-white hover:bg-blue-700"
        >
          {t("common:buttons.upgrade", { tier: t("common:tiers.team") })} - {formatPrice("team")}
        </a>
      </div>
    );
  }

  if (isLoading) {
    return <div className="p-8">{t("common:loadingData", { dataType: t("common:navigation.teams") })}</div>;
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("pages:teams.title")}</h1>
        <button
          onClick={() => createTeam("New Team")}
          className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
        >
          {t("pages:teams.createButton")}
        </button>
      </div>
      <div className="mt-8">
        {teams.length === 0 ? (
          <p className="text-gray-500">{t("pages:teams.empty")}</p>
        ) : (
          <ul className="space-y-2">
            {teams.map((team: any) => (
              <li key={team._id}>
                <a
                  href={`/teams/${team._id}`}
                  className="block rounded-lg border p-4 hover:bg-gray-50"
                >
                  {team.name}
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default function TeamsPage() {
  const { isCloud } = useCloudMode();
  const { t } = useTranslation("pages");

  if (!isCloud) {
    return <CloudUpgradeCTA title={t("teams.singleTitle")} description={t("teams.cloudFeature")} />;
  }

  return <CloudTeams />;
}
