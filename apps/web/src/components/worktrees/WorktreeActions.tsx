"use client";

import { useState } from "react";
import {
  GitMerge,
  Trash2,
  FileCode,
  Loader2,
  GitPullRequest,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import type { WorktreeListItem } from "@auto-claude/types";
import { apiClient } from "@/lib/data/api-client";

interface WorktreeActionsProps {
  worktree: WorktreeListItem;
  projectId: string;
  onMerged?: () => void;
  onDeleted?: () => void;
  onDiffView?: () => void;
}

export function WorktreeActions({
  worktree,
  projectId,
  onMerged,
  onDeleted,
  onDiffView,
}: WorktreeActionsProps) {
  const { t } = useTranslation("views");
  const [isMerging, setIsMerging] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const handleMerge = async () => {
    setIsMerging(true);
    try {
      await apiClient.mergeWorktree(projectId, worktree.specName);
      onMerged?.();
    } catch {
      // Error handled by caller
    } finally {
      setIsMerging(false);
    }
  };

  const handleDelete = async () => {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    setIsDeleting(true);
    try {
      await apiClient.discardWorktree(projectId, worktree.specName);
      onDeleted?.();
    } catch {
      // Error handled by caller
    } finally {
      setIsDeleting(false);
      setConfirmDelete(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <button
        className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        onClick={onDiffView}
      >
        <FileCode className="h-3.5 w-3.5" />
        {t("worktrees.actions.diff")}
      </button>

      {!worktree.isOrphaned && (
        <>
          <button
            className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-50"
            onClick={handleMerge}
            disabled={isMerging}
          >
            {isMerging ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <GitMerge className="h-3.5 w-3.5" />
            )}
            {t("worktrees.actions.merge")}
          </button>

          <button
            className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-50"
            onClick={() => {
              // Create PR placeholder
            }}
          >
            <GitPullRequest className="h-3.5 w-3.5" />
            {t("worktrees.actions.createPR")}
          </button>
        </>
      )}

      <button
        className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 ${
          confirmDelete
            ? "border-destructive bg-destructive text-destructive-foreground hover:bg-destructive/90"
            : "border-border text-muted-foreground hover:bg-accent hover:text-foreground"
        }`}
        onClick={handleDelete}
        disabled={isDeleting}
        onBlur={() => setConfirmDelete(false)}
      >
        {isDeleting ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Trash2 className="h-3.5 w-3.5" />
        )}
        {confirmDelete ? t("worktrees.actions.confirmDelete") : t("worktrees.actions.discard")}
      </button>
    </div>
  );
}
