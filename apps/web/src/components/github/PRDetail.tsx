"use client";

import {
  ExternalLink,
  CheckCircle2,
  XCircle,
  Clock,
  Eye,
  User,
  Calendar,
  GitPullRequest,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useTranslation } from "react-i18next";
import type { PRReviewResult } from "../../stores/github/pr-review-store";

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

interface PRDetailProps {
  pr: PullRequest;
  reviewResult: PRReviewResult | null;
  isReviewing: boolean;
  onStartReview: () => void;
  onOpenExternal?: () => void;
}

const REVIEW_STATUS_KEYS: Record<string, string> = {
  pending: "github.prs.reviews.pending",
  approved: "github.prs.reviews.approved",
  changes_requested: "github.prs.reviews.changesRequested",
  reviewing: "github.prs.reviews.inReview",
};

export function PRDetail({
  pr,
  reviewResult,
  isReviewing,
  onStartReview,
  onOpenExternal,
}: PRDetailProps) {
  const { t } = useTranslation("integrations");

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <h2 className="min-w-0 flex-1 truncate text-sm font-semibold">
          #{pr.number} {pr.title}
        </h2>
        <div className="flex shrink-0 items-center gap-2">
          <button
            onClick={onStartReview}
            disabled={isReviewing}
            className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors disabled:opacity-50"
          >
            <Eye className="h-3 w-3" />
            {t("github.prs.aiReview")}
          </button>
          {onOpenExternal && (
            <button
              onClick={onOpenExternal}
              className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-accent transition-colors"
            >
              <ExternalLink className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl space-y-4">
          {/* Meta info */}
          <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <User className="h-3 w-3" />
              {pr.author}
            </span>
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {pr.createdAt}
            </span>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-4 gap-3">
            <div className="rounded-md border border-border p-3 text-center">
              <p className="text-lg font-semibold text-green-600">+{pr.additions}</p>
              <p className="text-[10px] text-muted-foreground">{t("github.prs.stats.additions")}</p>
            </div>
            <div className="rounded-md border border-border p-3 text-center">
              <p className="text-lg font-semibold text-red-600">-{pr.deletions}</p>
              <p className="text-[10px] text-muted-foreground">{t("github.prs.stats.deletions")}</p>
            </div>
            <div className="rounded-md border border-border p-3 text-center">
              <p className="text-lg font-semibold">{pr.files}</p>
              <p className="text-[10px] text-muted-foreground">{t("github.prs.stats.files")}</p>
            </div>
            <div className="rounded-md border border-border p-3 text-center">
              <p className="text-lg font-semibold capitalize">{pr.state}</p>
              <p className="text-[10px] text-muted-foreground">{t("github.prs.status")}</p>
            </div>
          </div>

          {/* Review status */}
          <div className="rounded-lg border border-border p-4">
            <h3 className="text-sm font-medium mb-2">{t("github.prs.reviewStatus")}</h3>
            <div className="flex items-center gap-2">
              {pr.reviewStatus === "approved" ? (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              ) : pr.reviewStatus === "changes_requested" ? (
                <XCircle className="h-4 w-4 text-red-500" />
              ) : (
                <Clock className="h-4 w-4 text-yellow-500" />
              )}
              <span className="text-sm">
                {t(REVIEW_STATUS_KEYS[pr.reviewStatus])}
              </span>
            </div>
          </div>

          {/* AI Review Result */}
          {reviewResult && (
            <div className="rounded-lg border border-border bg-secondary/30 p-4 space-y-3">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <Eye className="h-4 w-4 text-blue-500" />
                {t("github.prs.aiReviewResult", "AI Review Result")}
              </h3>
              <p className="text-sm text-muted-foreground">{reviewResult.summary}</p>
              {reviewResult.findings.length > 0 && (
                <div className="space-y-2">
                  {reviewResult.findings.map((finding, idx) => (
                    <div
                      key={`${finding.file}-${finding.line}-${idx}`}
                      className={cn(
                        "rounded-md border p-3 text-xs",
                        finding.severity === "critical"
                          ? "border-red-500/30 bg-red-500/5"
                          : finding.severity === "warning"
                            ? "border-yellow-500/30 bg-yellow-500/5"
                            : finding.severity === "praise"
                              ? "border-green-500/30 bg-green-500/5"
                              : "border-border",
                      )}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className={cn(
                          "rounded-full px-1.5 py-0.5 text-[10px] font-medium",
                          finding.severity === "critical" ? "bg-red-500/10 text-red-600" :
                          finding.severity === "warning" ? "bg-yellow-500/10 text-yellow-600" :
                          finding.severity === "praise" ? "bg-green-500/10 text-green-600" :
                          "bg-blue-500/10 text-blue-600",
                        )}>
                          {finding.severity}
                        </span>
                        <span className="font-mono text-muted-foreground">
                          {finding.file}{finding.line ? `:${finding.line}` : ""}
                        </span>
                      </div>
                      <p className="text-muted-foreground">{finding.message}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Start AI Review button */}
          <button
            onClick={onStartReview}
            disabled={isReviewing}
            className="w-full flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            <Eye className="h-4 w-4" />
            {isReviewing
              ? t("github.prs.reviewing", "Reviewing...")
              : t("github.prs.startAiReview")}
          </button>
        </div>
      </div>
    </div>
  );
}
