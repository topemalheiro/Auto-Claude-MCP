"use client";

import {
  ExternalLink,
  CheckCircle2,
  Clock,
  Eye,
  User,
  Calendar,
  GitMerge,
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

interface MRDetailProps {
  mr: MergeRequest;
  isReviewing?: boolean;
  onStartReview?: () => void;
  onOpenExternal?: () => void;
}

export function MRDetail({
  mr,
  isReviewing = false,
  onStartReview,
  onOpenExternal,
}: MRDetailProps) {
  const { t } = useTranslation("integrations");

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <h2 className="min-w-0 flex-1 truncate text-sm font-semibold">
          !{mr.iid} {mr.title}
        </h2>
        <div className="flex shrink-0 items-center gap-2">
          {onStartReview && (
            <button
              onClick={onStartReview}
              disabled={isReviewing}
              className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors disabled:opacity-50"
            >
              <Eye className="h-3 w-3" />
              {t("gitlab.mrs.aiReview")}
            </button>
          )}
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
              {mr.author}
            </span>
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {mr.createdAt}
            </span>
            {mr.draft && (
              <span className="rounded-full bg-yellow-500/10 text-yellow-600 px-2 py-0.5 text-[10px] font-medium">
                {t("gitlab.mrs.draft")}
              </span>
            )}
          </div>

          {/* Stats */}
          <div className="grid grid-cols-4 gap-3">
            <div className="rounded-md border border-border p-3 text-center">
              <p className="text-lg font-semibold text-green-600">+{mr.additions}</p>
              <p className="text-[10px] text-muted-foreground">{t("gitlab.mrs.stats.additions")}</p>
            </div>
            <div className="rounded-md border border-border p-3 text-center">
              <p className="text-lg font-semibold text-red-600">-{mr.deletions}</p>
              <p className="text-[10px] text-muted-foreground">{t("gitlab.mrs.stats.deletions")}</p>
            </div>
            <div className="rounded-md border border-border p-3 text-center">
              <p className="text-lg font-semibold">{mr.changedFiles}</p>
              <p className="text-[10px] text-muted-foreground">{t("gitlab.mrs.stats.files")}</p>
            </div>
            <div className="rounded-md border border-border p-3 text-center">
              <p className="text-lg font-semibold capitalize">{mr.state}</p>
              <p className="text-[10px] text-muted-foreground">{t("gitlab.mrs.status")}</p>
            </div>
          </div>

          {/* Approvals */}
          <div className="rounded-lg border border-border p-4">
            <h3 className="text-sm font-medium mb-2">{t("gitlab.mrs.approvals")}</h3>
            <div className="flex items-center gap-2">
              {mr.approvals >= mr.approvalsRequired ? (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              ) : (
                <Clock className="h-4 w-4 text-yellow-500" />
              )}
              <span className="text-sm">
                {t("gitlab.mrs.approvalsCount", { current: mr.approvals, required: mr.approvalsRequired })}
              </span>
            </div>
          </div>

          {/* Labels */}
          {mr.labels.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              {mr.labels.map((label) => (
                <span
                  key={label}
                  className="rounded-full bg-secondary px-2.5 py-0.5 text-xs text-muted-foreground"
                >
                  {label}
                </span>
              ))}
            </div>
          )}

          {/* Start AI Review button */}
          {onStartReview && (
            <button
              onClick={onStartReview}
              disabled={isReviewing}
              className="w-full flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              <Eye className="h-4 w-4" />
              {isReviewing
                ? t("gitlab.mrs.reviewing", "Reviewing...")
                : t("gitlab.mrs.startAiReview")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
