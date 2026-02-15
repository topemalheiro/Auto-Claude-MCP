"use client";

import { useState } from "react";
import {
  CheckCircle2,
  XCircle,
  MessageSquare,
  Send,
  Loader2,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useTranslation } from "react-i18next";
import type { PRReviewResult, PRReviewProgress } from "../../stores/github/pr-review-store";

interface PRReviewPanelProps {
  prNumber: number;
  isReviewing: boolean;
  progress: PRReviewProgress | null;
  reviewResult: PRReviewResult | null;
  onApprove?: () => void;
  onRequestChanges?: () => void;
  onPostComment?: (body: string) => Promise<boolean>;
}

export function PRReviewPanel({
  prNumber,
  isReviewing,
  progress,
  reviewResult,
  onApprove,
  onRequestChanges,
  onPostComment,
}: PRReviewPanelProps) {
  const { t } = useTranslation("integrations");
  const [comment, setComment] = useState("");
  const [isPosting, setIsPosting] = useState(false);

  const handlePostComment = async () => {
    if (!comment.trim() || !onPostComment) return;
    setIsPosting(true);
    try {
      const success = await onPostComment(comment.trim());
      if (success) {
        setComment("");
      }
    } finally {
      setIsPosting(false);
    }
  };

  return (
    <div className="flex flex-col border-t border-border">
      {/* Review Progress */}
      {isReviewing && progress && (
        <div className="border-b border-border px-4 py-3">
          <div className="flex items-center gap-2 mb-2">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
            <span className="text-xs font-medium">{progress.phase}</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all duration-300"
              style={{ width: `${progress.progress}%` }}
            />
          </div>
          <p className="mt-1 text-[10px] text-muted-foreground">{progress.message}</p>
        </div>
      )}

      {/* Review Actions */}
      {reviewResult && !isReviewing && (
        <div className="border-b border-border px-4 py-3">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs font-medium">
              {t("github.prs.reviewActions", "Review Actions")}
            </span>
            <span className={cn(
              "rounded-full px-2 py-0.5 text-[10px] font-medium",
              reviewResult.approved ? "bg-green-500/10 text-green-600" : "bg-yellow-500/10 text-yellow-600",
            )}>
              {reviewResult.approved
                ? t("github.prs.reviews.approved")
                : t("github.prs.reviews.changesRequested")}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {onApprove && (
              <button
                onClick={onApprove}
                className="flex items-center gap-1.5 rounded-md bg-green-600 px-3 py-1.5 text-xs text-white hover:bg-green-700 transition-colors"
              >
                <CheckCircle2 className="h-3 w-3" />
                {t("github.prs.approve", "Approve")}
              </button>
            )}
            {onRequestChanges && (
              <button
                onClick={onRequestChanges}
                className="flex items-center gap-1.5 rounded-md bg-red-600 px-3 py-1.5 text-xs text-white hover:bg-red-700 transition-colors"
              >
                <XCircle className="h-3 w-3" />
                {t("github.prs.requestChanges", "Request Changes")}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Comment Input */}
      <div className="px-4 py-3">
        <div className="flex items-start gap-2">
          <MessageSquare className="mt-2 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <div className="flex-1">
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder={t("github.prs.addComment", "Add a comment...")}
              className="w-full resize-none rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary/20"
              rows={2}
            />
          </div>
          <button
            onClick={handlePostComment}
            disabled={!comment.trim() || isPosting}
            className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {isPosting ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Send className="h-3 w-3" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
