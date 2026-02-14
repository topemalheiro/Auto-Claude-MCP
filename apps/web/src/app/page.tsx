"use client";

import { CloudAuthenticated, CloudUnauthenticated, CloudAuthLoading } from "@/providers/AuthGate";
import { useCloudMode } from "@/hooks/useCloudMode";
import { getConvexReact, getConvexApi } from "@/lib/convex-imports";
import Link from "next/link";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";

function CloudDashboard() {
  const { useQuery, useMutation } = getConvexReact();
  const { api } = getConvexApi();
  const { t } = useTranslation(["pages", "common"]);

  const user = useQuery(api.users.me);
  const ensureUser = useMutation(api.users.ensureUser);

  // Create user record in app table on first login
  useEffect(() => {
    if (user === null) {
      ensureUser();
    }
  }, [user, ensureUser]);

  if (!user) return <div className="flex h-screen items-center justify-center">{t("common:loading")}</div>;

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold">{t("pages:home.welcome", { name: user.name })}</h1>
      <p className="text-gray-600">{t("pages:home.tier", { tier: user.tier })}</p>
      <nav className="mt-8 flex gap-4">
        <Link href="/specs" className="text-blue-600 hover:underline">{t("common:navigation.specs")}</Link>
        <Link href="/teams" className="text-blue-600 hover:underline">{t("common:navigation.teams")}</Link>
        <Link href="/personas" className="text-blue-600 hover:underline">{t("common:navigation.personas")}</Link>
        <Link href="/pr-queue" className="text-blue-600 hover:underline">{t("common:navigation.prQueue")}</Link>
        <Link href="/settings" className="text-blue-600 hover:underline">{t("common:navigation.settings")}</Link>
      </nav>
    </div>
  );
}

function SelfHostedDashboard() {
  const { t } = useTranslation(["pages", "common"]);

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold">{t("pages:home.selfHosted.title")}</h1>
      <p className="text-gray-600">{t("pages:home.selfHosted.mode")}</p>
      <nav className="mt-8 flex gap-4">
        <Link href="/specs" className="text-blue-600 hover:underline">{t("common:navigation.specs")}</Link>
      </nav>
      <div className="mt-12 rounded-lg border border-blue-200 bg-blue-50 p-6">
        <h2 className="text-lg font-semibold">{t("pages:home.selfHosted.unlockFeatures")}</h2>
        <p className="mt-2 text-gray-600">
          {t("pages:home.selfHosted.featuresDescription")}
        </p>
        <a
          href="https://autoclaude.com"
          className="mt-4 inline-block rounded-lg bg-blue-600 px-6 py-3 text-white hover:bg-blue-700"
        >
          {t("common:buttons.learnMore")}
        </a>
      </div>
    </div>
  );
}

function LandingPage() {
  const { t } = useTranslation(["pages", "common"]);

  return (
    <div className="flex h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-4xl font-bold">{t("pages:home.landing.title")}</h1>
      <p className="text-gray-600">{t("pages:home.landing.subtitle")}</p>
      <Link
        href="/login"
        className="rounded-lg bg-blue-600 px-6 py-3 text-white hover:bg-blue-700"
      >
        {t("common:buttons.getStarted")}
      </Link>
    </div>
  );
}

export default function HomePage() {
  const { isCloud } = useCloudMode();
  const { t } = useTranslation("common");

  if (!isCloud) {
    return (
      <main>
        <SelfHostedDashboard />
      </main>
    );
  }

  return (
    <main>
      <CloudAuthLoading>
        <div className="flex h-screen items-center justify-center">{t("loading")}</div>
      </CloudAuthLoading>
      <CloudUnauthenticated>
        <LandingPage />
      </CloudUnauthenticated>
      <CloudAuthenticated>
        <CloudDashboard />
      </CloudAuthenticated>
    </main>
  );
}
