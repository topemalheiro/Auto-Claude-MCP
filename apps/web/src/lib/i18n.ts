import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

// Import English translation resources
import enCommon from "../locales/en/common.json";
import enNavigation from "../locales/en/navigation.json";
import enPages from "../locales/en/pages.json";
import enSettings from "../locales/en/settings.json";
import enAuth from "../locales/en/auth.json";
import enKanban from "../locales/en/kanban.json";
import enViews from "../locales/en/views.json";
import enIntegrations from "../locales/en/integrations.json";
import enLayout from "../locales/en/layout.json";
import enOnboarding from "../locales/en/onboarding.json";

// Import French translation resources
import frCommon from "../locales/fr/common.json";
import frNavigation from "../locales/fr/navigation.json";
import frPages from "../locales/fr/pages.json";
import frSettings from "../locales/fr/settings.json";
import frAuth from "../locales/fr/auth.json";
import frKanban from "../locales/fr/kanban.json";
import frViews from "../locales/fr/views.json";
import frIntegrations from "../locales/fr/integrations.json";
import frLayout from "../locales/fr/layout.json";
import frOnboarding from "../locales/fr/onboarding.json";

export const defaultNS = "common";

export const resources = {
  en: {
    common: enCommon,
    navigation: enNavigation,
    pages: enPages,
    settings: enSettings,
    auth: enAuth,
    kanban: enKanban,
    views: enViews,
    integrations: enIntegrations,
    layout: enLayout,
    onboarding: enOnboarding,
  },
  fr: {
    common: frCommon,
    navigation: frNavigation,
    pages: frPages,
    settings: frSettings,
    auth: frAuth,
    kanban: frKanban,
    views: frViews,
    integrations: frIntegrations,
    layout: frLayout,
    onboarding: frOnboarding,
  },
} as const;

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: "en",
    defaultNS,
    ns: [
      "common",
      "navigation",
      "pages",
      "settings",
      "auth",
      "kanban",
      "views",
      "integrations",
      "layout",
      "onboarding",
    ],
    interpolation: {
      escapeValue: false, // React already escapes values
    },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
    },
  });

export default i18n;
