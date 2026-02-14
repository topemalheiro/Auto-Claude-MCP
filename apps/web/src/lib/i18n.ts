import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

// Import all translation files
import enCommon from "../locales/en/common.json";
import enPages from "../locales/en/pages.json";
import enSettings from "../locales/en/settings.json";
import enAuth from "../locales/en/auth.json";
import enKanban from "../locales/en/kanban.json";
import enViews from "../locales/en/views.json";
import enIntegrations from "../locales/en/integrations.json";
import enLayout from "../locales/en/layout.json";

import frCommon from "../locales/fr/common.json";
import frPages from "../locales/fr/pages.json";
import frSettings from "../locales/fr/settings.json";
import frAuth from "../locales/fr/auth.json";
import frKanban from "../locales/fr/kanban.json";
import frViews from "../locales/fr/views.json";
import frIntegrations from "../locales/fr/integrations.json";
import frLayout from "../locales/fr/layout.json";

const resources = {
  en: {
    common: enCommon,
    pages: enPages,
    settings: enSettings,
    auth: enAuth,
    kanban: enKanban,
    views: enViews,
    integrations: enIntegrations,
    layout: enLayout,
  },
  fr: {
    common: frCommon,
    pages: frPages,
    settings: frSettings,
    auth: frAuth,
    kanban: frKanban,
    views: frViews,
    integrations: frIntegrations,
    layout: frLayout,
  },
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: "en",
    defaultNS: "common",
    ns: ["common", "pages", "settings", "auth", "kanban", "views", "integrations", "layout"],
    interpolation: {
      escapeValue: false, // React already escapes values
    },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
    },
  });

export default i18n;
