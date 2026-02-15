"use client";

import {
  RefreshCw,
  AlertCircle,
  FolderTree,
  Server,
  Globe,
  Box,
  Code,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useTranslation } from "react-i18next";
import type { ProjectIndex } from "@/stores/context-store";

interface ServiceInfo {
  name: string;
  language: string;
  framework: string;
  type: string;
  path: string;
}

interface ProjectIndexTabProps {
  projectIndex: ProjectIndex | null;
  indexLoading: boolean;
  indexError: string | null;
  onRefresh: () => void;
}

const TYPE_ICONS: Record<string, React.ElementType> = {
  frontend: Globe,
  backend: Server,
  library: Box,
  worker: Code,
};

export function ProjectIndexTab({
  projectIndex,
  indexLoading,
  indexError,
  onRefresh,
}: ProjectIndexTabProps) {
  const { t } = useTranslation("integrations");

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header with refresh */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-foreground">
            {t("context.fields.projectStructure")}
          </h2>
          <p className="text-xs text-muted-foreground">
            {t("context.projectIndex.description", { defaultValue: "AI-discovered knowledge about your codebase" })}
          </p>
        </div>
        <button
          className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors disabled:opacity-50"
          onClick={onRefresh}
          disabled={indexLoading}
        >
          <RefreshCw className={cn("h-3.5 w-3.5", indexLoading && "animate-spin")} />
          {t("context.reindex")}
        </button>
      </div>

      {/* Error state */}
      {indexError && (
        <div className="flex items-center gap-3 p-4 rounded-lg bg-destructive/10 text-destructive">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <div>
            <p className="text-sm font-medium">{t("context.errors.indexFailed", { defaultValue: "Failed to load project index" })}</p>
            <p className="text-xs opacity-80">{indexError}</p>
          </div>
        </div>
      )}

      {/* Loading state */}
      {indexLoading && !projectIndex && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* No index state */}
      {!indexLoading && !projectIndex && !indexError && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <FolderTree className="h-12 w-12 text-muted-foreground/50 mb-4" />
          <h3 className="text-sm font-semibold mb-1">
            {t("context.empty.noIndex", { defaultValue: "No Project Index Found" })}
          </h3>
          <p className="text-xs text-muted-foreground max-w-sm">
            {t("context.empty.noIndexDescription", { defaultValue: "Click Refresh to analyze your project structure and create an index." })}
          </p>
          <button
            onClick={onRefresh}
            className="mt-4 flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            {t("context.reindex")}
          </button>
        </div>
      )}

      {/* Project index content */}
      {projectIndex && (
        <div className="space-y-6">
          {/* Overview Card */}
          <div className="rounded-lg border border-border bg-card p-5">
            <div className="flex items-center gap-2 mb-4">
              <FolderTree className="h-4 w-4 text-primary" />
              <h2 className="text-sm font-semibold">{t("context.fields.projectStructure")}</h2>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-md border border-border p-3">
                <p className="text-xs text-muted-foreground">{t("context.fields.files", { defaultValue: "Files" })}</p>
                <p className="text-sm font-medium">{projectIndex.files}</p>
              </div>
              <div className="rounded-md border border-border p-3">
                <p className="text-xs text-muted-foreground">{t("context.fields.languages", { defaultValue: "Languages" })}</p>
                <div className="flex flex-wrap gap-1 mt-0.5">
                  {projectIndex.languages.map((lang) => (
                    <span
                      key={lang}
                      className="rounded-full bg-secondary px-2 py-0.5 text-[10px] text-muted-foreground"
                    >
                      {lang}
                    </span>
                  ))}
                </div>
              </div>
            </div>
            {projectIndex.frameworks.length > 0 && (
              <div className="mt-4 rounded-md border border-border p-3">
                <p className="text-xs text-muted-foreground mb-1">{t("context.fields.frameworks", { defaultValue: "Frameworks" })}</p>
                <div className="flex flex-wrap gap-1">
                  {projectIndex.frameworks.map((fw) => (
                    <span
                      key={fw}
                      className="rounded-full bg-secondary px-2 py-0.5 text-[10px] text-muted-foreground"
                    >
                      {fw}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Analyzed timestamp */}
          {projectIndex.analyzedAt && (
            <p className="text-[10px] text-muted-foreground text-right">
              {t("context.fields.lastAnalyzed", { defaultValue: "Last analyzed" })}:{" "}
              {new Date(projectIndex.analyzedAt).toLocaleString()}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
