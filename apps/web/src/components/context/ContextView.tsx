"use client";

import { useState } from "react";
import {
  BookOpen,
  FolderTree,
  Database,
  Brain,
  Server,
  Code,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  FileCode,
  Globe,
  Box,
  Search,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useTranslation } from "react-i18next";

interface ContextViewProps {
  projectId: string;
}

interface ServiceInfo {
  name: string;
  language: string;
  framework: string;
  type: string;
  path: string;
}

const PLACEHOLDER_SERVICES: ServiceInfo[] = [
  { name: "frontend", language: "TypeScript", framework: "React", type: "frontend", path: "apps/frontend/" },
  { name: "web", language: "TypeScript", framework: "Next.js", type: "frontend", path: "apps/web/" },
  { name: "backend", language: "Python", framework: "FastAPI", type: "backend", path: "apps/backend/" },
  { name: "types", language: "TypeScript", framework: "N/A", type: "library", path: "packages/types/" },
  { name: "ui", language: "TypeScript", framework: "React", type: "library", path: "packages/ui/" },
];

const TYPE_ICONS: Record<string, React.ElementType> = {
  frontend: Globe,
  backend: Server,
  library: Box,
  worker: Code,
};

export function ContextView({ projectId }: ContextViewProps) {
  const { t } = useTranslation("integrations");
  const [activeTab, setActiveTab] = useState<"overview" | "services" | "memories">("overview");
  const [searchQuery, setSearchQuery] = useState("");

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold">{t("context.title")}</h1>
          <div className="flex items-center rounded-lg border border-border bg-card/50">
            <button
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors rounded-l-lg",
                activeTab === "overview" ? "bg-accent text-foreground" : "text-muted-foreground hover:text-foreground"
              )}
              onClick={() => setActiveTab("overview")}
            >
              <FolderTree className="h-3 w-3" />
              {t("context.tabs.overview")}
            </button>
            <button
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors",
                activeTab === "services" ? "bg-accent text-foreground" : "text-muted-foreground hover:text-foreground"
              )}
              onClick={() => setActiveTab("services")}
            >
              <Server className="h-3 w-3" />
              {t("context.tabs.services")}
            </button>
            <button
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors rounded-r-lg",
                activeTab === "memories" ? "bg-accent text-foreground" : "text-muted-foreground hover:text-foreground"
              )}
              onClick={() => setActiveTab("memories")}
            >
              <Brain className="h-3 w-3" />
              {t("context.tabs.memories")}
            </button>
          </div>
        </div>
        <button className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors">
          <RefreshCw className="h-3.5 w-3.5" />
          {t("context.reindex")}
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === "overview" && (
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Project Type */}
            <div className="rounded-lg border border-border bg-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <FolderTree className="h-4 w-4 text-primary" />
                <h2 className="text-sm font-semibold">{t("context.fields.projectStructure")}</h2>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-md border border-border p-3">
                  <p className="text-xs text-muted-foreground">{t("context.fields.type")}</p>
                  <p className="text-sm font-medium">{t("context.fields.monorepo")}</p>
                </div>
                <div className="rounded-md border border-border p-3">
                  <p className="text-xs text-muted-foreground">{t("context.fields.services")}</p>
                  <p className="text-sm font-medium">{PLACEHOLDER_SERVICES.length}</p>
                </div>
              </div>
            </div>

            {/* Services Summary */}
            <div className="rounded-lg border border-border bg-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Server className="h-4 w-4 text-primary" />
                <h2 className="text-sm font-semibold">{t("context.tabs.services")}</h2>
              </div>
              <div className="space-y-2">
                {PLACEHOLDER_SERVICES.map((service) => {
                  const Icon = TYPE_ICONS[service.type] || Code;
                  return (
                    <div
                      key={service.name}
                      className="flex items-center gap-3 rounded-md border border-border p-3 hover:bg-accent/50 transition-colors cursor-pointer"
                    >
                      <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium">{service.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {service.path}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] text-muted-foreground">
                          {service.language}
                        </span>
                        <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] text-muted-foreground">
                          {service.framework}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Memory Status */}
            <div className="rounded-lg border border-border bg-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Brain className="h-4 w-4 text-primary" />
                <h2 className="text-sm font-semibold">{t("context.fields.memorySystem")}</h2>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="rounded-md border border-border p-3">
                  <p className="text-xs text-muted-foreground">{t("context.fields.status")}</p>
                  <p className="text-sm font-medium text-green-600">{t("context.fields.active")}</p>
                </div>
                <div className="rounded-md border border-border p-3">
                  <p className="text-xs text-muted-foreground">{t("context.fields.episodes")}</p>
                  <p className="text-sm font-medium">0</p>
                </div>
                <div className="rounded-md border border-border p-3">
                  <p className="text-xs text-muted-foreground">{t("context.fields.database")}</p>
                  <p className="text-sm font-medium">{t("context.fields.ladybugDB")}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "services" && (
          <div className="max-w-4xl mx-auto">
            <div className="space-y-4">
              {PLACEHOLDER_SERVICES.map((service) => {
                const Icon = TYPE_ICONS[service.type] || Code;
                return (
                  <div key={service.name} className="rounded-lg border border-border bg-card p-5">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary">
                        <Icon className="h-5 w-5 text-muted-foreground" />
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold">{service.name}</h3>
                        <p className="text-xs text-muted-foreground">{service.path}</p>
                      </div>
                    </div>
                    <div className="grid grid-cols-4 gap-3">
                      <div className="rounded-md border border-border p-2.5">
                        <p className="text-[10px] text-muted-foreground">{t("context.fields.language")}</p>
                        <p className="text-xs font-medium">{service.language}</p>
                      </div>
                      <div className="rounded-md border border-border p-2.5">
                        <p className="text-[10px] text-muted-foreground">{t("context.fields.framework")}</p>
                        <p className="text-xs font-medium">{service.framework}</p>
                      </div>
                      <div className="rounded-md border border-border p-2.5">
                        <p className="text-[10px] text-muted-foreground">{t("context.fields.type")}</p>
                        <p className="text-xs font-medium capitalize">{service.type}</p>
                      </div>
                      <div className="rounded-md border border-border p-2.5">
                        <p className="text-[10px] text-muted-foreground">{t("context.fields.path")}</p>
                        <p className="text-xs font-medium truncate">{service.path}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {activeTab === "memories" && (
          <div className="max-w-3xl mx-auto">
            {/* Search */}
            <div className="mb-6">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  className="w-full rounded-lg border border-border bg-background pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  placeholder={t("context.search.memories")}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>

            {/* Empty state */}
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Brain className="h-12 w-12 text-muted-foreground/50 mb-4" />
              <h3 className="text-sm font-semibold mb-1">{t("context.empty.noMemories")}</h3>
              <p className="text-xs text-muted-foreground max-w-sm">
                {t("context.empty.noMemoriesDescription")}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
