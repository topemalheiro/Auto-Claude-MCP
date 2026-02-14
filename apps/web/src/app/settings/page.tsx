"use client";

import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useCloudMode } from "@/hooks/useCloudMode";
import { getConvexReact, getConvexApi } from "@/lib/convex-imports";
import { useState } from "react";
import { hasTierAccess } from "@/lib/tiers";
import { formatPrice, PRICING } from "@/lib/pricing";
import { useTranslation } from "react-i18next";

type Tier = "pro" | "team" | "enterprise";

function SelfHostedSettings() {
  const { t } = useTranslation(["settings", "common"]);

  return (
    <div className="p-8 max-w-3xl">
      <h1 className="text-2xl font-bold">{t("settings:title")}</h1>
      <section className="mt-8">
        <h2 className="text-xl font-semibold">{t("settings:selfHosted.mode")}</h2>
        <p className="mt-2 text-gray-600">
          {t("settings:selfHosted.description")}
        </p>
      </section>
      <section className="mt-8 rounded-lg border border-blue-200 bg-blue-50 p-6">
        <h2 className="text-lg font-semibold">{t("settings:selfHosted.unlockFeatures")}</h2>
        <p className="mt-2 text-gray-600">
          {t("settings:selfHosted.featuresDescription")}
        </p>
        <a
          href="https://autoclaude.com"
          className="mt-4 inline-block rounded-lg bg-blue-600 px-6 py-3 text-white hover:bg-blue-700"
        >
          {t("common:buttons.learnMore")}
        </a>
      </section>
    </div>
  );
}

function CloudSettings() {
  const { useAction, useQuery } = getConvexReact();
  const { api } = getConvexApi();
  const { t } = useTranslation(["settings", "common", "auth"]);

  const user = useCurrentUser();
  const tierInfo = useQuery(api.billing.getTierInfo);
  const createCheckout = useAction(api.stripe.createCheckoutSession);
  const createPortal = useAction(api.stripe.createPortalSession);
  const [loading, setLoading] = useState<Tier | "portal" | null>(null);

  const logout = async () => {
    const { authClient } = await import("@/lib/auth-client");
    authClient.signOut();
  };

  const handleUpgrade = async (tier: Tier) => {
    setLoading(tier);
    try {
      const url = await createCheckout({ tier });
      window.location.href = url;
    } catch (error) {
      console.error("Checkout error:", error);
      alert(t("common:errors.checkoutFailed"));
      setLoading(null);
    }
  };

  const handleManageSubscription = async () => {
    setLoading("portal");
    try {
      const url = await createPortal();
      window.location.href = url;
    } catch (error) {
      console.error("Portal error:", error);
      alert(t("common:errors.portalFailed"));
      setLoading(null);
    }
  };

  if (!user) {
    return <div className="p-8">{t("common:errors.loginRequired")}</div>;
  }

  return (
    <div className="p-8 max-w-3xl">
      <h1 className="text-2xl font-bold">{t("settings:title")}</h1>

      {/* Profile Section */}
      <section className="mt-8">
        <h2 className="text-xl font-semibold">{t("settings:profile.title")}</h2>
        <div className="mt-4 space-y-2">
          <p><strong>{t("settings:profile.name")}</strong> {user.name}</p>
          <p><strong>{t("settings:profile.email")}</strong> {user.email}</p>
        </div>
      </section>

      {/* Billing Section */}
      <section className="mt-8">
        <h2 className="text-xl font-semibold">{t("settings:subscription.title")}</h2>
        <div className="mt-4">
          <p>
            <strong>{t("settings:subscription.currentPlan")}</strong>{" "}
            {tierInfo?.tierName ?? (user.tier ? user.tier.charAt(0).toUpperCase() + user.tier.slice(1) : t("common:tiers.free"))}
            {tierInfo?.price ? ` — ${t("settings:subscription.price", { price: tierInfo.price })}` : ""}
          </p>

          {/* Usage */}
          {tierInfo && (
            <div className="mt-4 space-y-1 text-sm text-gray-600">
              <p>
                {t("settings:subscription.usage.specs", {
                  current: tierInfo.usage.specs,
                  limit: tierInfo.limits.specs === -1 ? t("settings:subscription.usage.unlimited") : tierInfo.limits.specs
                })}
              </p>
              <p>
                {t("settings:subscription.usage.personas", {
                  current: tierInfo.usage.personas,
                  limit: tierInfo.limits.personas === -1 ? t("settings:subscription.usage.unlimited") : tierInfo.limits.personas
                })}
              </p>
              <p>
                {t("settings:subscription.usage.teamMembers", {
                  current: tierInfo.usage.teamMembers,
                  limit: tierInfo.limits.teamMembers === -1 ? t("settings:subscription.usage.unlimited") : tierInfo.limits.teamMembers
                })}
              </p>
            </div>
          )}

          {/* Upgrade buttons */}
          <div className="mt-4 flex gap-4">
            {!hasTierAccess(user.tier, "pro") && (
              <button
                onClick={() => handleUpgrade("pro")}
                disabled={loading !== null}
                className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {loading === "pro" ? t("common:buttons.redirecting") : `${t("common:buttons.upgrade", { tier: t("common:tiers.pro") })} - ${formatPrice("pro")}`}
              </button>
            )}
            {!hasTierAccess(user.tier, "team") && (
              <button
                onClick={() => handleUpgrade("team")}
                disabled={loading !== null}
                className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {loading === "team" ? t("common:buttons.redirecting") : `${t("common:buttons.upgrade", { tier: t("common:tiers.team") })} - ${formatPrice("team")}`}
              </button>
            )}
            {!hasTierAccess(user.tier, "enterprise") && (
              <button
                onClick={() => handleUpgrade("enterprise")}
                disabled={loading !== null}
                className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {loading === "enterprise" ? t("common:buttons.redirecting") : `${t("common:tiers.enterprise")} - ${formatPrice("enterprise")}`}
              </button>
            )}
            {hasTierAccess(user.tier, "pro") && (
              <button
                onClick={handleManageSubscription}
                disabled={loading !== null}
                className="rounded-lg border px-4 py-2 hover:bg-gray-50 disabled:opacity-50"
              >
                {loading === "portal" ? t("common:buttons.redirecting") : t("common:buttons.manageSubscription")}
              </button>
            )}
          </div>
        </div>
      </section>

      {/* Sign Out */}
      <section className="mt-8">
        <button
          onClick={logout}
          className="rounded-lg border border-red-600 px-4 py-2 text-red-600 hover:bg-red-50"
        >
          {t("auth:signOut")}
        </button>
      </section>
    </div>
  );
}

export default function SettingsPage() {
  const { isCloud } = useCloudMode();

  if (!isCloud) {
    return <SelfHostedSettings />;
  }

  return <CloudSettings />;
}
