import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

// Import all translation files
import enCommon from "../locales/en/common.json";
import enPages from "../locales/en/pages.json";
import enSettings from "../locales/en/settings.json";
import enAuth from "../locales/en/auth.json";

import frCommon from "../locales/fr/common.json";
import frPages from "../locales/fr/pages.json";
import frSettings from "../locales/fr/settings.json";
import frAuth from "../locales/fr/auth.json";

const resources = {
  en: {
    common: enCommon,
    pages: enPages,
    settings: enSettings,
    auth: enAuth,
  },
  fr: {
    common: frCommon,
    pages: frPages,
    settings: frSettings,
    auth: frAuth,
  },
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: "en",
    defaultNS: "common",
    ns: ["common", "pages", "settings", "auth"],
    interpolation: {
      escapeValue: false, // React already escapes values
    },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
    },
  });

export default i18n;
