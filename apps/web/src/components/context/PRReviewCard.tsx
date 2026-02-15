"use client";

import { GitPullRequest, CheckCircle, XCircle, Clock } from "lucide-react";
import { cn } from "@auto-claude/ui";

interface PRReviewSummary {
  id: string;
  title: string;
  status: "approved" | "changes_requested" | "pending";
  reviewer: string;
  updatedAt: string;
  summary: string;
}

interface PRReviewCardProps {
  review: PRReviewSummary;
}

const STATUS_CONFIG: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  approved: { icon: CheckCircle, color: "text-green-600 dark:text-green-400", label: "Approved" },
  changes_requested: { icon: XCircle, color: "text-red-600 dark:text-red-400", label: "Changes Requested" },
  pending: { icon: Clock, color: "text-amber-600 dark:text-amber-400", label: "Pending" },
};

export function PRReviewCard({ review }: PRReviewCardProps) {
  const config = STATUS_CONFIG[review.status] || STATUS_CONFIG.pending;
  const StatusIcon = config.icon;

  return (
    <div className="rounded-lg border border-border bg-card p-4 hover:bg-accent/50 transition-colors">
      <div className="flex items-start gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-purple-500/10">
          <GitPullRequest className="h-4 w-4 text-purple-600 dark:text-purple-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-1">
            <p className="text-sm font-medium truncate">{review.title}</p>
            <div className={cn("flex items-center gap-1 shrink-0", config.color)}>
              <StatusIcon className="h-3.5 w-3.5" />
              <span className="text-[10px] font-medium">{config.label}</span>
            </div>
          </div>
          <p className="text-xs text-muted-foreground mb-2">
            Reviewed by {review.reviewer} · {new Date(review.updatedAt).toLocaleDateString()}
          </p>
          <p className="text-xs text-muted-foreground line-clamp-2">{review.summary}</p>
        </div>
      </div>
    </div>
  );
}

export type { PRReviewSummary };
