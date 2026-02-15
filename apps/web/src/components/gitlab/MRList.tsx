"use client";

import { useCallback, useRef, useEffect } from "react";
import {
  GitMerge,
  Loader2,
  Search as SearchIcon,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useTranslation } from "react-i18next";

interface MergeRequest {
  iid: number;
  title: string;
  state: "opened" | "merged" | "closed";
  author: string;
  additions: number;
  deletions: number;
  changedFiles: number;
  createdAt: string;
  labels: string[];
  draft: boolean;
  approvals: number;
  approvalsRequired: number;
}

interface MRListProps {
  mrs: MergeRequest[];
  selectedMRIid: number | null;
  isLoading: boolean;
  error: string | null;
  onSelectMR: (iid: number) => void;
  onRetry?: () => void;
}

const STATE_COLORS: Record<string, string> = {
  opened: "text-green-500",
  merged: "text-purple-500",
  closed: "text-red-500",
};

export function MRList({
  mrs,
  selectedMRIid,
  isLoading,
  error,
  onSelectMR,
  onRetry,
}: MRListProps) {
  const { t } = useTranslation("integrations");

  if (isLoading && mrs.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8">
        <p className="text-sm text-destructive">{error}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            {t("common:retry", "Retry")}
          </button>
        )}
      </div>
    );
  }

  if (mrs.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="text-center">
          <SearchIcon className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">
            {t("gitlab.mrs.noMRs", "No merge requests found")}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      {mrs.map((mr) => (
        <div
          key={mr.iid}
          className={cn(
            "flex items-start gap-3 border-b border-border px-4 py-3 cursor-pointer transition-colors",
            selectedMRIid === mr.iid ? "bg-accent" : "hover:bg-accent/50",
          )}
          onClick={() => onSelectMR(mr.iid)}
        >
          <GitMerge className={cn("h-4 w-4 mt-0.5 shrink-0", STATE_COLORS[mr.state])} />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium leading-tight">
              !{mr.iid} {mr.title}
            </p>
            <div className="mt-1 flex items-center gap-1.5 flex-wrap">
              {mr.draft && (
                <span className="rounded-full bg-yellow-500/10 text-yellow-600 px-2 py-0.5 text-[10px] font-medium">
                  {t("gitlab.mrs.draft")}
                </span>
              )}
              {mr.labels.map((label) => (
                <span
                  key={label}
                  className="rounded-full bg-secondary px-2 py-0.5 text-[10px] text-muted-foreground"
                >
                  {label}
                </span>
              ))}
            </div>
            <div className="mt-1 flex items-center gap-3 text-[10px] text-muted-foreground">
              <span>{mr.author}</span>
              <span>{mr.createdAt}</span>
              <span className="text-green-600">+{mr.additions}</span>
              <span className="text-red-600">-{mr.deletions}</span>
              <span>{t("gitlab.mrs.stats.filesCount", { count: mr.changedFiles })}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
