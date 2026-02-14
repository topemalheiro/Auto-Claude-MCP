"use client";

import { usePRQueue } from "@/hooks";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useCloudMode } from "@/hooks/useCloudMode";
import { CloudUpgradeCTA } from "@/components/CloudUpgradeCTA";
import { hasTierAccess } from "@/lib/tiers";
import { formatPrice } from "@/lib/pricing";
import { useTranslation } from "react-i18next";

function CloudPRQueue() {
  const user = useCurrentUser();
  const { t } = useTranslation(["pages", "common"]);

  // PR Queue requires Team tier or higher
  const hasTeamAccess = hasTierAccess(user?.tier, "team");

  if (!hasTeamAccess) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 p-8">
        <h1 className="text-2xl font-bold">{t("pages:prQueue.title")}</h1>
        <p className="text-gray-600">
          {t("pages:prQueue.description")}
        </p>
        <a
          href="/settings"
          className="rounded-lg bg-blue-600 px-6 py-3 text-white hover:bg-blue-700"
        >
          {t("common:buttons.upgrade", { tier: t("common:tiers.team") })} - {formatPrice("team")}
        </a>
      </div>
    );
  }

  // TODO: Get teamId from user's active team
  const teamId = "";
  const { prs, isLoading, updateStatus, assignPR } = usePRQueue(teamId);

  if (isLoading) {
    return <div className="p-8">{t("common:loadingData", { dataType: t("common:navigation.prQueue") })}</div>;
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold">{t("pages:prQueue.title")}</h1>
      <div className="mt-8">
        {prs.length === 0 ? (
          <p className="text-gray-500">{t("pages:prQueue.empty")}</p>
        ) : (
          <ul className="space-y-2">
            {prs.map((pr: any) => (
              <li key={pr._id} className="rounded-lg border p-4">
                <div className="flex items-center justify-between">
                  <span className="font-semibold">{t("pages:prQueue.prNumber", { number: pr.prNumber })} {pr.title}</span>
                  <span className="rounded bg-gray-100 px-2 py-1 text-sm">{pr.status}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default function PRQueuePage() {
  const { isCloud } = useCloudMode();
  const { t } = useTranslation("pages");

  if (!isCloud) {
    return <CloudUpgradeCTA title={t("prQueue.title")} description={t("prQueue.cloudFeature")} />;
  }

  return <CloudPRQueue />;
}
