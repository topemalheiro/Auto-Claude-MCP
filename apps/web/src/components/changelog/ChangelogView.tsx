"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  FileText,
  RefreshCw,
  Sparkles,
  Tag,
  Calendar,
  ChevronDown,
  ChevronRight,
  Plus,
  CheckCircle2,
  GitPullRequest,
} from "lucide-react";
import { cn } from "@auto-claude/ui";

interface ChangelogViewProps {
  projectId: string;
}

interface ChangelogEntry {
  id: string;
  version: string;
  date: string;
  title: string;
  changes: {
    type: "added" | "changed" | "fixed" | "removed";
    description: string;
  }[];
  isExpanded: boolean;
}

const CHANGE_TYPE_COLORS = {
  added: "bg-green-500/10 text-green-600",
  changed: "bg-blue-500/10 text-blue-600",
  fixed: "bg-orange-500/10 text-orange-600",
  removed: "bg-red-500/10 text-red-600",
};

const CHANGE_TYPE_KEYS: Record<string, string> = {
  added: "changelog.changeTypes.added",
  changed: "changelog.changeTypes.changed",
  fixed: "changelog.changeTypes.fixed",
  removed: "changelog.changeTypes.removed",
};

const PLACEHOLDER_ENTRIES: ChangelogEntry[] = [
  {
    id: "1",
    version: "2.7.7",
    date: "2025-02-14",
    title: "Cloud Platform Preparation",
    changes: [
      { type: "added", description: "Shared UI component library extracted to @auto-claude/ui" },
      { type: "added", description: "Shared TypeScript types package @auto-claude/types" },
      { type: "added", description: "Web application foundation with Next.js 16" },
      { type: "changed", description: "Migrated from libs/ to packages/ directory structure" },
    ],
    isExpanded: true,
  },
  {
    id: "2",
    version: "2.7.6",
    date: "2025-02-10",
    title: "Stability Improvements",
    changes: [
      { type: "fixed", description: "PR review recovery for structured output validation" },
      { type: "fixed", description: "Sentry integration for Python subprocesses" },
      { type: "changed", description: "Improved task execution progress tracking" },
    ],
    isExpanded: false,
  },
  {
    id: "3",
    version: "2.7.5",
    date: "2025-02-05",
    title: "OAuth and Security Updates",
    changes: [
      { type: "added", description: "Claude OAuth authentication support" },
      { type: "fixed", description: "Session management for multi-profile setups" },
      { type: "changed", description: "Re-authentication flow for improved security" },
    ],
    isExpanded: false,
  },
];

export function ChangelogView({ projectId }: ChangelogViewProps) {
  const { t } = useTranslation("views");
  const [entries, setEntries] = useState(PLACEHOLDER_ENTRIES);
  const [isEmpty] = useState(false);

  const toggleEntry = (id: string) => {
    setEntries((prev) =>
      prev.map((e) => (e.id === id ? { ...e, isExpanded: !e.isExpanded } : e))
    );
  };

  if (isEmpty) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8">
        <div className="max-w-md text-center">
          <div className="mb-6 flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
              <FileText className="h-8 w-8 text-primary" />
            </div>
          </div>
          <h2 className="mb-3 text-xl font-semibold">{t("changelog.empty.title")}</h2>
          <p className="mb-6 text-sm text-muted-foreground">
            {t("changelog.empty.description")}
          </p>
          <button className="flex items-center gap-2 mx-auto rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors">
            <Sparkles className="h-4 w-4" />
            {t("changelog.empty.generate")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <h1 className="text-lg font-semibold">{t("changelog.title")}</h1>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors">
            <RefreshCw className="h-3.5 w-3.5" />
            {t("changelog.refresh")}
          </button>
          <button className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 transition-colors">
            <Plus className="h-3.5 w-3.5" />
            {t("changelog.newRelease")}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto space-y-4">
          {entries.map((entry) => (
            <div
              key={entry.id}
              className="rounded-lg border border-border bg-card overflow-hidden"
            >
              <button
                className="w-full flex items-center gap-3 px-5 py-4 hover:bg-accent/50 transition-colors text-left"
                onClick={() => toggleEntry(entry.id)}
              >
                {entry.isExpanded ? (
                  <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                )}
                <div className="flex items-center gap-2.5 flex-1">
                  <Tag className="h-4 w-4 text-primary shrink-0" />
                  <span className="font-mono text-sm font-semibold">
                    v{entry.version}
                  </span>
                  <span className="text-sm text-muted-foreground">
                    {entry.title}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground shrink-0">
                  <Calendar className="h-3 w-3" />
                  {entry.date}
                </div>
              </button>

              {entry.isExpanded && (
                <div className="border-t border-border px-5 py-4">
                  <div className="space-y-2">
                    {entry.changes.map((change, idx) => {
                      const color = CHANGE_TYPE_COLORS[change.type];
                      return (
                        <div key={idx} className="flex items-start gap-2">
                          <span
                            className={cn(
                              "shrink-0 mt-0.5 rounded-full px-2 py-0.5 text-[10px] font-semibold",
                              color
                            )}
                          >
                            {t(CHANGE_TYPE_KEYS[change.type])}
                          </span>
                          <p className="text-sm text-muted-foreground">
                            {change.description}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
