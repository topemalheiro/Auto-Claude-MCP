"use client";

import { FolderGit, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { WorktreeListItem } from "@auto-claude/types";
import { WorktreeCard } from "./WorktreeCard";
import { WorktreeActions } from "./WorktreeActions";

interface WorktreeListProps {
  worktrees: WorktreeListItem[];
  isLoading: boolean;
  error: string | null;
  projectId: string;
  selectedSpecName: string | null;
  onSelect: (specName: string) => void;
  onRefresh: () => void;
}

export function WorktreeList({
  worktrees,
  isLoading,
  error,
  projectId,
  selectedSpecName,
  onSelect,
  onRefresh,
}: WorktreeListProps) {
  const { t } = useTranslation("views");

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-2 text-muted-foreground">
        <p className="text-sm">{error}</p>
        <button
          className="text-xs text-primary underline hover:no-underline"
          onClick={onRefresh}
        >
          {t("worktrees.retry")}
        </button>
      </div>
    );
  }

  if (worktrees.length === 0) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-2 text-muted-foreground">
        <FolderGit className="h-10 w-10 opacity-30" />
        <p className="text-sm">{t("worktrees.empty.title")}</p>
        <p className="text-xs">{t("worktrees.empty.description")}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {worktrees.map((wt) => (
        <div key={wt.specName} className="space-y-2">
          <WorktreeCard
            worktree={wt}
            isSelected={selectedSpecName === wt.specName}
            onSelect={() => onSelect(wt.specName)}
          />
          {selectedSpecName === wt.specName && (
            <div className="pl-4">
              <WorktreeActions
                worktree={wt}
                projectId={projectId}
                onMerged={onRefresh}
                onDeleted={onRefresh}
              />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
