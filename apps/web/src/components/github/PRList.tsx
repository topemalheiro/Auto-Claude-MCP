"use client";

import { useCallback, useRef, useEffect } from "react";
import {
  GitPullRequest,
  GitMerge,
  XCircle,
  Loader2,
  Search as SearchIcon,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useTranslation } from "react-i18next";

interface PullRequest {
  number: number;
  title: string;
  state: "open" | "closed" | "merged";
  author: string;
  reviewStatus: "pending" | "approved" | "changes_requested" | "reviewing";
  additions: number;
  deletions: number;
  files: number;
  createdAt: string;
  labels: { name: string; color: string }[];
  draft: boolean;
}

interface PRListProps {
  prs: PullRequest[];
  selectedPRNumber: number | null;
  isLoading: boolean;
  isLoadingMore?: boolean;
  hasMore?: boolean;
  error: string | null;
  onSelectPR: (prNumber: number) => void;
  onLoadMore?: () => void;
  onRetry?: () => void;
}

const STATE_ICONS: Record<string, React.ElementType> = {
  open: GitPullRequest,
  merged: GitMerge,
  closed: XCircle,
};

const STATE_COLORS: Record<string, string> = {
  open: "text-green-500",
  merged: "text-purple-500",
  closed: "text-red-500",
};

const REVIEW_STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-500/10 text-yellow-600",
  approved: "bg-green-500/10 text-green-600",
  changes_requested: "bg-red-500/10 text-red-600",
  reviewing: "bg-blue-500/10 text-blue-600",
};

const REVIEW_STATUS_KEYS: Record<string, string> = {
  pending: "github.prs.reviews.pending",
  approved: "github.prs.reviews.approved",
  changes_requested: "github.prs.reviews.changesRequested",
  reviewing: "github.prs.reviews.inReview",
};

export function PRList({
  prs,
  selectedPRNumber,
  isLoading,
  isLoadingMore = false,
  hasMore = false,
  error,
  onSelectPR,
  onLoadMore,
  onRetry,
}: PRListProps) {
  const { t } = useTranslation("integrations");
  const scrollRef = useRef<HTMLDivElement>(null);

  const handleScroll = useCallback(() => {
    if (!scrollRef.current || !hasMore || isLoadingMore || !onLoadMore) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    if (scrollHeight - scrollTop - clientHeight < 200) {
      onLoadMore();
    }
  }, [hasMore, isLoadingMore, onLoadMore]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.addEventListener("scroll", handleScroll);
    return () => el.removeEventListener("scroll", handleScroll);
  }, [handleScroll]);

  if (isLoading && prs.length === 0) {
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

  if (prs.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="text-center">
          <SearchIcon className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">
            {t("github.prs.noPRs", "No pull requests found")}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto">
      {prs.map((pr) => {
        const StateIcon = STATE_ICONS[pr.state] || GitPullRequest;
        const stateColor = STATE_COLORS[pr.state] || "text-muted-foreground";
        const reviewColor = REVIEW_STATUS_COLORS[pr.reviewStatus];
        const reviewKey = REVIEW_STATUS_KEYS[pr.reviewStatus];

        return (
          <div
            key={pr.number}
            className={cn(
              "flex items-start gap-3 border-b border-border px-4 py-3 cursor-pointer transition-colors",
              selectedPRNumber === pr.number ? "bg-accent" : "hover:bg-accent/50",
            )}
            onClick={() => onSelectPR(pr.number)}
          >
            <StateIcon className={cn("h-4 w-4 mt-0.5 shrink-0", stateColor)} />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium leading-tight">
                #{pr.number} {pr.title}
              </p>
              <div className="mt-1 flex items-center gap-2 flex-wrap">
                {pr.draft && (
                  <span className="rounded-full bg-yellow-500/10 text-yellow-600 px-2 py-0.5 text-[10px] font-medium">
                    {t("github.prs.draft", "Draft")}
                  </span>
                )}
                {pr.labels.map((label) => (
                  <span
                    key={label.name}
                    className="rounded-full border px-2 py-0.5 text-[10px]"
                    style={{ borderColor: `#${label.color}40`, color: `#${label.color}` }}
                  >
                    {label.name}
                  </span>
                ))}
                {reviewKey && (
                  <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-medium", reviewColor)}>
                    {t(reviewKey)}
                  </span>
                )}
              </div>
              <div className="mt-1 flex items-center gap-3 text-[10px] text-muted-foreground">
                <span>{pr.author}</span>
                <span>{pr.createdAt}</span>
                <span className="text-green-600">+{pr.additions}</span>
                <span className="text-red-600">-{pr.deletions}</span>
                <span>{t("github.prs.stats.filesCount", { count: pr.files })}</span>
              </div>
            </div>
          </div>
        );
      })}
      {isLoadingMore && (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      )}
    </div>
  );
}
