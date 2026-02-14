"use client";

import { useSpecs } from "@/hooks";
import { useTranslation } from "react-i18next";

export default function SpecsPage() {
  const { specs, isLoading, createSpec } = useSpecs();
  const { t } = useTranslation(["pages", "common"]);

  if (isLoading) {
    return <div className="p-8">{t("common:loadingData", { dataType: t("common:navigation.specs") })}</div>;
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("pages:specs.title")}</h1>
        <button
          onClick={() => createSpec("New Spec", "# New Spec\n\nDescription here...")}
          className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
        >
          {t("pages:specs.createButton")}
        </button>
      </div>
      <div className="mt-8">
        {specs.length === 0 ? (
          <p className="text-gray-500">{t("pages:specs.empty")}</p>
        ) : (
          <ul className="space-y-2">
            {specs.map((spec: any) => (
              <li key={spec._id}>
                <a
                  href={`/specs/${spec._id}`}
                  className="block rounded-lg border p-4 hover:bg-gray-50"
                >
                  {spec.name}
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
