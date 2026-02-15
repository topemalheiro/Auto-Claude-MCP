"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { apiClient } from "@/lib/data/api-client";

interface CreateWorktreeDialogProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export function CreateWorktreeDialog({
  projectId,
  isOpen,
  onClose,
  onCreated,
}: CreateWorktreeDialogProps) {
  const { t } = useTranslation("views");
  const [specName, setSpecName] = useState("");
  const [baseBranch, setBaseBranch] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!specName.trim()) return;
    setIsCreating(true);
    setError(null);
    try {
      await apiClient.createWorktree(projectId, specName.trim(), baseBranch.trim() || undefined);
      setSpecName("");
      setBaseBranch("");
      onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create worktree");
    } finally {
      setIsCreating(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold">{t("worktrees.create.title")}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{t("worktrees.create.description")}</p>

        <div className="mt-4 space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              {t("worktrees.create.specName")}
            </label>
            <input
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
              value={specName}
              onChange={(e) => setSpecName(e.target.value)}
              placeholder="e.g., 001-my-feature"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              {t("worktrees.create.baseBranch")}
            </label>
            <input
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
              value={baseBranch}
              onChange={(e) => setBaseBranch(e.target.value)}
              placeholder="main"
            />
          </div>
        </div>

        {error && <p className="mt-3 text-xs text-destructive">{error}</p>}

        <div className="mt-5 flex justify-end gap-2">
          <button
            className="rounded-md border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-accent"
            onClick={onClose}
          >
            {t("worktrees.create.cancel")}
          </button>
          <button
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            onClick={handleCreate}
            disabled={!specName.trim() || isCreating}
          >
            {isCreating && <Loader2 className="h-4 w-4 animate-spin" />}
            {t("worktrees.create.submit")}
          </button>
        </div>
      </div>
    </div>
  );
}
