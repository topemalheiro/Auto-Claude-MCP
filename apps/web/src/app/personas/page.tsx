"use client";

import { usePersonas } from "@/hooks";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useCloudMode } from "@/hooks/useCloudMode";
import { CloudUpgradeCTA } from "@/components/CloudUpgradeCTA";
import { hasTierAccess } from "@/lib/tiers";
import { formatPrice } from "@/lib/pricing";
import { useTranslation } from "react-i18next";

function CloudPersonas() {
  const user = useCurrentUser();
  const { personas, isLoading, createPersona } = usePersonas();
  const { t } = useTranslation(["pages", "common"]);

  // Personas require Pro tier or higher
  const hasPersonaAccess = hasTierAccess(user?.tier, "pro");

  if (!hasPersonaAccess) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 p-8">
        <h1 className="text-2xl font-bold">{t("pages:personas.title")}</h1>
        <p className="text-gray-600">
          {t("pages:personas.description")}
        </p>
        <a
          href="/settings"
          className="rounded-lg bg-blue-600 px-6 py-3 text-white hover:bg-blue-700"
        >
          {t("common:buttons.upgrade", { tier: t("common:tiers.pro") })} - {formatPrice("pro")}
        </a>
      </div>
    );
  }

  if (isLoading) {
    return <div className="p-8">{t("common:loadingData", { dataType: t("common:navigation.personas") })}</div>;
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("pages:personas.title")}</h1>
        <button
          onClick={() => createPersona("New Persona", "A helpful coding assistant", [])}
          className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
        >
          {t("pages:personas.createButton")}
        </button>
      </div>
      <div className="mt-8">
        {personas.length === 0 ? (
          <p className="text-gray-500">{t("pages:personas.empty")}</p>
        ) : (
          <ul className="space-y-2">
            {personas.map((persona: any) => (
              <li key={persona._id} className="rounded-lg border p-4">
                <h3 className="font-semibold">{persona.name}</h3>
                <p className="text-gray-600">{persona.description}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default function PersonasPage() {
  const { isCloud } = useCloudMode();
  const { t } = useTranslation("pages");

  if (!isCloud) {
    return <CloudUpgradeCTA title={t("personas.title")} description={t("personas.cloudFeature")} />;
  }

  return <CloudPersonas />;
}
