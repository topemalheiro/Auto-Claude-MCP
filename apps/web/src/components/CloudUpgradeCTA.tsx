"use client";

import { useTranslation } from "react-i18next";

export function CloudUpgradeCTA({ title, description }: { title: string; description: string }) {
  const { t } = useTranslation("pages");

  return (
    <div className="flex h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-2xl font-bold">{title}</h1>
      <p className="text-gray-600">{description}</p>
      <a href="https://autoclaude.com" className="rounded-lg bg-blue-600 px-6 py-3 text-white hover:bg-blue-700">
        {t("cloudUpgrade.learnMore")}
      </a>
    </div>
  );
}
