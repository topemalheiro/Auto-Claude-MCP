"use client";

import {
  FileText,
  History,
  GitBranch,
  Tag,
  Calendar,
  RefreshCw,
  Loader2,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useTranslation } from "react-i18next";
import type {
  ChangelogSourceMode,
  GitBranchInfo,
  GitTagInfo,
} from "@/stores/changelog-store";

interface ChangelogFiltersProps {
  sourceMode: ChangelogSourceMode;
  onSourceModeChange: (mode: ChangelogSourceMode) => void;
  doneTasksCount: number;
  branches: GitBranchInfo[];
  tags: GitTagInfo[];
  defaultBranch: string;
  isLoadingGitData: boolean;
  isLoadingCommits: boolean;
  gitHistoryType: "recent" | "since-date" | "tag-range" | "since-version";
  gitHistoryCount: number;
  gitHistorySinceDate: string;
  gitHistoryFromTag: string;
  gitHistoryToTag: string;
  gitHistorySinceVersion: string;
  includeMergeCommits: boolean;
  onGitHistoryTypeChange: (
    type: "recent" | "since-date" | "tag-range" | "since-version",
  ) => void;
  onGitHistoryCountChange: (count: number) => void;
  onGitHistorySinceDateChange: (date: string) => void;
  onGitHistoryFromTagChange: (tag: string) => void;
  onGitHistoryToTagChange: (tag: string) => void;
  onGitHistorySinceVersionChange: (version: string) => void;
  onIncludeMergeCommitsChange: (include: boolean) => void;
  baseBranch: string;
  compareBranch: string;
  onBaseBranchChange: (branch: string) => void;
  onCompareBranchChange: (branch: string) => void;
  onLoadCommitsPreview: () => void;
}

const SOURCE_MODES = [
  {
    value: "tasks" as const,
    icon: FileText,
    label: "Completed Tasks",
    description: "Generate from completed task specs",
  },
  {
    value: "git-history" as const,
    icon: History,
    label: "Git History",
    description: "Generate from commit history",
  },
  {
    value: "branch-diff" as const,
    icon: GitBranch,
    label: "Branch Diff",
    description: "Compare two branches",
  },
];

export function ChangelogFilters({
  sourceMode,
  onSourceModeChange,
  doneTasksCount,
  branches,
  tags,
  defaultBranch,
  isLoadingGitData,
  isLoadingCommits,
  gitHistoryType,
  gitHistoryCount,
  gitHistorySinceDate,
  gitHistoryFromTag,
  gitHistoryToTag,
  gitHistorySinceVersion,
  includeMergeCommits,
  onGitHistoryTypeChange,
  onGitHistoryCountChange,
  onGitHistorySinceDateChange,
  onGitHistoryFromTagChange,
  onGitHistoryToTagChange,
  onGitHistorySinceVersionChange,
  onIncludeMergeCommitsChange,
  baseBranch,
  compareBranch,
  onBaseBranchChange,
  onCompareBranchChange,
  onLoadCommitsPreview,
}: ChangelogFiltersProps) {
  const { t } = useTranslation("views");
  const localBranches = branches.filter((b) => !b.isRemote);

  return (
    <div className="w-80 shrink-0 border-r border-border overflow-y-auto">
      <div className="p-6 space-y-6">
        {/* Source Mode Selection */}
        <div className="space-y-3">
          <label className="text-sm font-medium">
            {t("changelog.filters.source")}
          </label>
          <div className="space-y-2">
            {SOURCE_MODES.map((mode) => {
              const Icon = mode.icon;
              return (
                <button
                  key={mode.value}
                  type="button"
                  className={cn(
                    "flex items-start gap-3 rounded-lg border p-3 cursor-pointer transition-all w-full text-left",
                    sourceMode === mode.value
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/50",
                  )}
                  onClick={() => onSourceModeChange(mode.value)}
                >
                  <div
                    className={cn(
                      "mt-0.5 h-4 w-4 rounded-full border-2 flex items-center justify-center shrink-0",
                      sourceMode === mode.value
                        ? "border-primary"
                        : "border-muted-foreground/50",
                    )}
                  >
                    {sourceMode === mode.value && (
                      <div className="h-2 w-2 rounded-full bg-primary" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <Icon className="h-4 w-4" />
                      <span className="font-medium text-sm">{mode.label}</span>
                      {mode.value === "tasks" && (
                        <span className="ml-auto rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                          {doneTasksCount}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {mode.description}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Git History Options */}
        {sourceMode === "git-history" && (
          <div className="rounded-lg border border-border p-4 space-y-4">
            <h3 className="text-sm font-medium">
              {t("changelog.filters.gitHistory")}
            </h3>

            <div className="space-y-2">
              <label className="text-xs text-muted-foreground">
                History Type
              </label>
              <select
                value={gitHistoryType}
                onChange={(e) =>
                  onGitHistoryTypeChange(e.target.value as typeof gitHistoryType)
                }
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              >
                <option value="since-version">Since Version</option>
                <option value="recent">Recent Commits</option>
                <option value="since-date">Since Date</option>
                <option value="tag-range">Tag Range</option>
              </select>
            </div>

            {gitHistoryType === "recent" && (
              <div className="space-y-2">
                <label className="text-xs text-muted-foreground">
                  Number of Commits
                </label>
                <input
                  type="number"
                  min={1}
                  max={500}
                  value={gitHistoryCount}
                  onChange={(e) =>
                    onGitHistoryCountChange(
                      Number.parseInt(e.target.value, 10) || 25,
                    )
                  }
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                />
              </div>
            )}

            {gitHistoryType === "since-date" && (
              <div className="space-y-2">
                <label className="text-xs text-muted-foreground">
                  Since Date
                </label>
                <input
                  type="date"
                  value={gitHistorySinceDate}
                  onChange={(e) => onGitHistorySinceDateChange(e.target.value)}
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                />
              </div>
            )}

            {gitHistoryType === "tag-range" && (
              <>
                <div className="space-y-2">
                  <label className="text-xs text-muted-foreground">
                    From Tag
                  </label>
                  <select
                    value={gitHistoryFromTag}
                    onChange={(e) => onGitHistoryFromTagChange(e.target.value)}
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                  >
                    <option value="">Select tag...</option>
                    {tags.map((tag) => (
                      <option key={tag.name} value={tag.name}>
                        {tag.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-muted-foreground">
                    To Tag
                  </label>
                  <select
                    value={gitHistoryToTag || "HEAD"}
                    onChange={(e) =>
                      onGitHistoryToTagChange(
                        e.target.value === "HEAD" ? "" : e.target.value,
                      )
                    }
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                  >
                    <option value="HEAD">HEAD (latest)</option>
                    {tags.map((tag) => (
                      <option key={tag.name} value={tag.name}>
                        {tag.name}
                      </option>
                    ))}
                  </select>
                </div>
              </>
            )}

            {gitHistoryType === "since-version" && (
              <div className="space-y-2">
                <label className="text-xs text-muted-foreground">
                  Last Version
                </label>
                <select
                  value={gitHistorySinceVersion}
                  onChange={(e) =>
                    onGitHistorySinceVersionChange(e.target.value)
                  }
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                >
                  <option value="">Select version...</option>
                  {tags.map((tag) => (
                    <option key={tag.name} value={tag.name}>
                      {tag.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="merge-commits"
                checked={includeMergeCommits}
                onChange={(e) => onIncludeMergeCommitsChange(e.target.checked)}
                className="h-4 w-4 rounded border-border"
              />
              <label
                htmlFor="merge-commits"
                className="text-xs cursor-pointer text-muted-foreground"
              >
                Include merge commits
              </label>
            </div>

            <button
              type="button"
              className="w-full flex items-center justify-center gap-2 rounded-md border border-border px-3 py-2 text-sm hover:bg-accent transition-colors disabled:opacity-50"
              onClick={onLoadCommitsPreview}
              disabled={isLoadingCommits || isLoadingGitData}
            >
              {isLoadingCommits ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4" />
                  Load Commits
                </>
              )}
            </button>
          </div>
        )}

        {/* Branch Diff Options */}
        {sourceMode === "branch-diff" && (
          <div className="rounded-lg border border-border p-4 space-y-4">
            <h3 className="text-sm font-medium">
              {t("changelog.filters.branchComparison")}
            </h3>

            <div className="space-y-2">
              <label className="text-xs text-muted-foreground">
                Base Branch
              </label>
              <select
                value={baseBranch}
                onChange={(e) => onBaseBranchChange(e.target.value)}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              >
                <option value="">Select base branch...</option>
                {localBranches.map((branch) => (
                  <option key={branch.name} value={branch.name}>
                    {branch.name}
                    {branch.name === defaultBranch ? " (default)" : ""}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-xs text-muted-foreground">
                Compare Branch
              </label>
              <select
                value={compareBranch}
                onChange={(e) => onCompareBranchChange(e.target.value)}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              >
                <option value="">Select compare branch...</option>
                {localBranches.map((branch) => (
                  <option key={branch.name} value={branch.name}>
                    {branch.name}
                    {branch.isCurrent ? " (current)" : ""}
                  </option>
                ))}
              </select>
            </div>

            {baseBranch && compareBranch && baseBranch === compareBranch && (
              <p className="text-xs text-destructive">
                Branches must be different
              </p>
            )}

            <button
              type="button"
              className="w-full flex items-center justify-center gap-2 rounded-md border border-border px-3 py-2 text-sm hover:bg-accent transition-colors disabled:opacity-50"
              onClick={onLoadCommitsPreview}
              disabled={
                isLoadingCommits ||
                isLoadingGitData ||
                !baseBranch ||
                !compareBranch ||
                baseBranch === compareBranch
              }
            >
              {isLoadingCommits ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4" />
                  Load Commits
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
