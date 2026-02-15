"use client";

import {
  GitBranch,
  FileCode,
  Plus,
  Minus,
  AlertCircle,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import type { WorktreeListItem } from "@auto-claude/types";

interface WorktreeCardProps {
  worktree: WorktreeListItem;
  isSelected?: boolean;
  onSelect?: () => void;
}

export function WorktreeCard({ worktree, isSelected, onSelect }: WorktreeCardProps) {
  return (
    <div
      className={cn(
        "cursor-pointer rounded-lg border border-border bg-card p-4 transition-colors hover:bg-accent/50",
        isSelected && "border-primary bg-accent/30",
        worktree.isOrphaned && "border-destructive/50 opacity-75",
      )}
      onClick={onSelect}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <GitBranch className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="truncate text-sm font-medium">{worktree.specName}</span>
            {worktree.isOrphaned && (
              <AlertCircle className="h-3.5 w-3.5 shrink-0 text-destructive" />
            )}
          </div>
          <p className="mt-1 truncate text-xs text-muted-foreground">
            {worktree.branch} → {worktree.baseBranch}
          </p>
        </div>

        {/* Stats */}
        <div className="flex shrink-0 items-center gap-3 text-xs text-muted-foreground">
          {worktree.filesChanged != null && (
            <span className="flex items-center gap-1">
              <FileCode className="h-3 w-3" />
              {worktree.filesChanged}
            </span>
          )}
          {worktree.additions != null && (
            <span className="flex items-center gap-0.5 text-green-600 dark:text-green-400">
              <Plus className="h-3 w-3" />
              {worktree.additions}
            </span>
          )}
          {worktree.deletions != null && (
            <span className="flex items-center gap-0.5 text-red-600 dark:text-red-400">
              <Minus className="h-3 w-3" />
              {worktree.deletions}
            </span>
          )}
        </div>
      </div>

      {worktree.commitCount != null && worktree.commitCount > 0 && (
        <p className="mt-2 text-xs text-muted-foreground">
          {worktree.commitCount} commit{worktree.commitCount !== 1 ? "s" : ""} ahead
        </p>
      )}
    </div>
  );
}
