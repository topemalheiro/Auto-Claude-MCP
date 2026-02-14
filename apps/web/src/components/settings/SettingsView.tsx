"use client";

import { useState } from "react";
import {
  Settings,
  User,
  Palette,
  Globe,
  Shield,
  Bell,
  Github,
  Key,
  Database,
  Monitor,
  Moon,
  Sun,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useSettingsStore, saveSettings } from "@/stores/settings-store";
import { useTranslation } from "react-i18next";

type SettingsSection =
  | "general"
  | "appearance"
  | "accounts"
  | "github"
  | "notifications"
  | "advanced";

const SECTION_IDS: { id: SettingsSection; icon: React.ElementType }[] = [
  { id: "general", icon: Settings },
  { id: "appearance", icon: Palette },
  { id: "accounts", icon: Key },
  { id: "github", icon: Github },
  { id: "notifications", icon: Bell },
  { id: "advanced", icon: Database },
];

export function SettingsView() {
  const [activeSection, setActiveSection] = useState<SettingsSection>("general");
  const settings = useSettingsStore((s) => s.settings);
  const { t } = useTranslation("settings");

  const SECTIONS = SECTION_IDS.map((s) => ({
    ...s,
    label: t(`sections.${s.id}.title`),
  }));

  return (
    <div className="flex h-full overflow-hidden">
      {/* Sidebar */}
      <div className="w-56 border-r border-border bg-card/50 p-4">
        <h1 className="text-sm font-semibold mb-4 px-3">{t("title")}</h1>
        <nav className="space-y-1">
          {SECTIONS.map((section) => {
            const Icon = section.icon;
            return (
              <button
                key={section.id}
                className={cn(
                  "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors",
                  activeSection === section.id
                    ? "bg-accent text-foreground"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
                )}
                onClick={() => setActiveSection(section.id)}
              >
                <Icon className="h-4 w-4" />
                {section.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-2xl">
          {activeSection === "general" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-1">{t("sections.general.title")}</h2>
                <p className="text-sm text-muted-foreground">
                  {t("sections.general.description")}
                </p>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between rounded-lg border border-border p-4">
                  <div>
                    <p className="text-sm font-medium">{t("fields.language")}</p>
                    <p className="text-xs text-muted-foreground">
                      {t("fields.languageDescription")}
                    </p>
                  </div>
                  <select className="rounded-md border border-border bg-background px-3 py-1.5 text-sm">
                    <option value="en">{t("languages.en")}</option>
                    <option value="fr">{t("languages.fr")}</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {activeSection === "appearance" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-1">{t("sections.appearance.title")}</h2>
                <p className="text-sm text-muted-foreground">
                  {t("sections.appearance.description")}
                </p>
              </div>

              <div className="space-y-4">
                {/* Theme */}
                <div className="rounded-lg border border-border p-4">
                  <p className="text-sm font-medium mb-3">{t("fields.theme")}</p>
                  <div className="grid grid-cols-3 gap-3">
                    {(["light", "dark", "system"] as const).map((theme) => {
                      const Icon = theme === "light" ? Sun : theme === "dark" ? Moon : Monitor;
                      return (
                        <button
                          key={theme}
                          className={cn(
                            "flex flex-col items-center gap-2 rounded-lg border p-4 transition-colors",
                            settings.theme === theme
                              ? "border-primary bg-primary/5"
                              : "border-border hover:border-border/80"
                          )}
                          onClick={() => saveSettings({ theme })}
                        >
                          <Icon className="h-5 w-5" />
                          <span className="text-xs font-medium capitalize">
                            {t(`themes.${theme}`)}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeSection === "accounts" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-1">{t("sections.accounts.title")}</h2>
                <p className="text-sm text-muted-foreground">
                  {t("sections.accounts.description")}
                </p>
              </div>

              <div className="space-y-4">
                <div className="rounded-lg border border-border p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Key className="h-4 w-4 text-primary" />
                    <p className="text-sm font-medium">{t("fields.claudeApi")}</p>
                  </div>
                  <p className="text-xs text-muted-foreground mb-3">
                    {t("fields.claudeApiDescription")}
                  </p>
                  <button className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 transition-colors">
                    {t("actions.configure")}
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeSection === "github" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-1">{t("sections.github.title")}</h2>
                <p className="text-sm text-muted-foreground">
                  {t("sections.github.description")}
                </p>
              </div>

              <div className="space-y-4">
                <div className="rounded-lg border border-border p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Github className="h-4 w-4" />
                    <p className="text-sm font-medium">{t("fields.repository")}</p>
                  </div>
                  <div className="space-y-3">
                    <div>
                      <label className="text-xs text-muted-foreground">{t("fields.repositoryLabel")}</label>
                      <input
                        className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                        placeholder={t("placeholders.ownerRepo")}
                      />
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">{t("fields.mainBranch")}</label>
                      <input
                        className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                        placeholder={t("placeholders.main")}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeSection === "notifications" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-1">{t("sections.notifications.title")}</h2>
                <p className="text-sm text-muted-foreground">
                  {t("sections.notifications.description")}
                </p>
              </div>

              <div className="space-y-4">
                {(["taskCompleted", "taskFailed", "reviewNeeded"] as const).map((key) => (
                  <div
                    key={key}
                    className="flex items-center justify-between rounded-lg border border-border p-4"
                  >
                    <div>
                      <p className="text-sm font-medium">{t(`notifications.${key}.label`)}</p>
                      <p className="text-xs text-muted-foreground">{t(`notifications.${key}.description`)}</p>
                    </div>
                    <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-primary transition-colors">
                      <span className="inline-block h-4 w-4 transform rounded-full bg-white transition-transform translate-x-6" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeSection === "advanced" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-1">{t("sections.advanced.title")}</h2>
                <p className="text-sm text-muted-foreground">
                  {t("sections.advanced.description")}
                </p>
              </div>

              <div className="space-y-4">
                <div className="rounded-lg border border-border p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Database className="h-4 w-4 text-primary" />
                    <p className="text-sm font-medium">{t("fields.memorySystem")}</p>
                  </div>
                  <p className="text-xs text-muted-foreground mb-3">
                    {t("fields.memorySystemDescription")}
                  </p>
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-green-500/10 text-green-600 px-2 py-0.5 text-xs">
                      {t("status.active")}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {t("status.usingLadybugDb")}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
