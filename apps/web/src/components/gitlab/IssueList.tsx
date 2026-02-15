"use client";

import { useCallback, useRef, useEffect } from "react";
import {
  AlertCircle,
  CheckCircle2,
  MessageSquare,
  Loader2,
  Search as SearchIcon,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useTranslation } from "react-i18next";

interface GitLabIssue {
  iid: number;
  title: string;
  state: "opened" | "closed";
  labels: string[];
  author: string;
  comments: number;
  createdAt: string;
  description: string;
}

interface IssueListProps {
  issues: GitLabIssue[];
  selectedIssueIid: number | null;
  isLoading: boolean;
  error: string | null;
  onSelectIssue: (iid: number) => void;
  onInvestigate?: (issue: GitLabIssue) => void;
  onRetry?: () => void;
}

export function IssueList({
  issues,
  selectedIssueIid,
  isLoading,
  error,
  onSelectIssue,
  onInvestigate,
  onRetry,
}: IssueListProps) {
  const { t } = useTranslation("integrations");

  if (isLoading && issues.length === 0) {
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

  if (issues.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="text-center">
          <SearchIcon className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">
            {t("gitlab.issues.noIssues", "No issues found")}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      {issues.map((issue) => (
        <div
          key={issue.iid}
          className={cn(
            "flex items-start gap-3 border-b border-border px-4 py-3 cursor-pointer transition-colors group",
            selectedIssueIid === issue.iid ? "bg-accent" : "hover:bg-accent/50",
          )}
          onClick={() => onSelectIssue(issue.iid)}
        >
          {issue.state === "opened" ? (
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-green-500" />
          ) : (
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-purple-500" />
          )}
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium leading-tight">
              #{issue.iid} {issue.title}
            </p>
            {issue.labels.length > 0 && (
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                {issue.labels.map((label) => (
                  <span
                    key={label}
                    className="rounded-full bg-secondary px-2 py-0.5 text-[10px] text-muted-foreground"
                  >
                    {label}
                  </span>
                ))}
              </div>
            )}
            <div className="mt-1 flex items-center gap-3 text-[10px] text-muted-foreground">
              <span>{issue.author}</span>
              <span>{issue.createdAt}</span>
              {issue.comments > 0 && (
                <span className="flex items-center gap-0.5">
                  <MessageSquare className="h-2.5 w-2.5" />
                  {issue.comments}
                </span>
              )}
            </div>
          </div>
          {onInvestigate && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onInvestigate(issue);
              }}
              className="shrink-0 rounded-md px-2 py-1 text-[10px] text-muted-foreground opacity-0 transition-all hover:bg-accent group-hover:opacity-100"
            >
              {t("gitlab.issues.investigate", "Investigate")}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
