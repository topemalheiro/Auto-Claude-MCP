"use client";

import { CloudAuthenticated } from "@/providers/AuthGate";
import { useCloudMode } from "@/hooks/useCloudMode";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";

export default function LoginPage() {
  const { isCloud } = useCloudMode();
  const router = useRouter();
  const { t } = useTranslation(["pages", "common", "auth"]);

  // Self-hosted mode: no login needed, redirect home
  if (!isCloud) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4">
        <h1 className="text-2xl font-bold">{t("pages:login.selfHosted.title")}</h1>
        <p className="text-gray-600">{t("pages:login.selfHosted.noLoginRequired")}</p>
        <a
          href="/"
          className="rounded-lg bg-blue-600 px-6 py-3 text-white hover:bg-blue-700"
        >
          {t("common:buttons.goToDashboard")}
        </a>
        <div className="mt-8 rounded-lg border border-blue-200 bg-blue-50 p-4 text-center">
          <p className="text-sm text-gray-600">
            {t("pages:login.selfHosted.cloudPromo")}
          </p>
          <a href="https://autoclaude.com" className="text-sm text-blue-600 hover:underline">
            {t("pages:login.selfHosted.tryCloud")}
          </a>
        </div>
      </div>
    );
  }

  const signIn = async () => {
    const { authClient } = await import("@/lib/auth-client");
    authClient.signIn.social({ provider: "github", callbackURL: "/" });
  };

  return (
    <>
      <CloudAuthenticated>
        <RedirectHome />
      </CloudAuthenticated>
      <div className="flex h-screen flex-col items-center justify-center gap-4">
        <h1 className="text-2xl font-bold">{t("auth:signInTitle")}</h1>
        <button
          onClick={signIn}
          className="rounded-lg bg-gray-900 px-6 py-3 text-white hover:bg-gray-800"
        >
          {t("auth:signIn")}
        </button>
      </div>
    </>
  );
}

function RedirectHome() {
  const router = useRouter();
  useEffect(() => { router.push("/"); }, [router]);
  return null;
}
