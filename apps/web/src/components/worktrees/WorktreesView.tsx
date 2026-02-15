"use client";

import { useState, useEffect, useCallback } from "react";
import { GitBranch, RefreshCw, Plus, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { apiClient } from "@/lib/data/api-client";
import type { WorktreeListItem } from "@auto-claude/types";
import { WorktreeList } from "./WorktreeList";
import { CreateWorktreeDialog } from "./CreateWorktreeDialog";

interface WorktreesViewProps {
  projectId: string;
}

export function WorktreesView({ projectId }: WorktreesViewProps) {
  const { t } = useTranslation("views");
  const [worktrees, setWorktrees] = useState<WorktreeListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedSpecName, setSelectedSpecName] = useState<string | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const loadWorktrees = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.listWorktrees(projectId);
      setWorktrees(response.worktrees || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load worktrees");
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadWorktrees();
  }, [loadWorktrees]);

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <div className="flex items-center gap-3">
          <GitBranch className="h-5 w-5 text-muted-foreground" />
          <h1 className="text-lg font-semibold">{t("worktrees.title")}</h1>
          {worktrees.length > 0 && (
            <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs text-muted-foreground">
              {worktrees.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-50"
            onClick={loadWorktrees}
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" />
            )}
            {t("worktrees.refresh")}
          </button>
          <button
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90"
            onClick={() => setShowCreateDialog(true)}
          >
            <Plus className="h-3.5 w-3.5" />
            {t("worktrees.create.button")}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <WorktreeList
          worktrees={worktrees}
          isLoading={isLoading}
          error={error}
          projectId={projectId}
          selectedSpecName={selectedSpecName}
          onSelect={setSelectedSpecName}
          onRefresh={loadWorktrees}
        />
      </div>

      {/* Create Dialog */}
      <CreateWorktreeDialog
        projectId={projectId}
        isOpen={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onCreated={loadWorktrees}
      />
    </div>
  );
}
