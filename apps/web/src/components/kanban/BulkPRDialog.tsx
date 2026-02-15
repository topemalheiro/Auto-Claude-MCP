"use client";

/**
 * BulkPRDialog - Dialog for creating pull requests for multiple completed tasks
 *
 * Allows users to select completed tasks and create PRs in bulk.
 * Shows task details, branch info, and PR creation status.
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  X,
  GitPullRequest,
  Loader2,
  Check,
  AlertCircle,
  Square,
  CheckSquare,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import type { Task } from "@auto-claude/types";
import { useTaskStore } from "@/stores/task-store";
import { apiClient } from "@/lib/data";

interface BulkPRDialogProps {
  open: boolean;
  onClose: () => void;
  projectId: string;
}

type PRStatus = "pending" | "creating" | "created" | "error";

interface TaskPRState {
  taskId: string;
  selected: boolean;
  status: PRStatus;
  prUrl?: string;
  error?: string;
}

export function BulkPRDialog({
  open,
  onClose,
  projectId,
}: BulkPRDialogProps) {
  const { t } = useTranslation("kanban");
  const tasks = useTaskStore((s) => s.tasks);

  // Filter to tasks eligible for PR creation (done status, no existing PR)
  const eligibleTasks = useMemo(
    () =>
      tasks.filter(
        (task) =>
          task.projectId === projectId &&
          task.status === "done" &&
          !task.metadata?.prUrl,
      ),
    [tasks, projectId],
  );

  const [taskStates, setTaskStates] = useState<Map<string, TaskPRState>>(
    new Map(),
  );
  const [isCreating, setIsCreating] = useState(false);

  // Initialize task states when dialog opens
  useEffect(() => {
    if (open) {
      const states = new Map<string, TaskPRState>();
      for (const task of eligibleTasks) {
        states.set(task.id, {
          taskId: task.id,
          selected: true,
          status: "pending",
        });
      }
      setTaskStates(states);
      setIsCreating(false);
    }
  }, [open, eligibleTasks]);

  // Escape key
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !isCreating) onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose, isCreating]);

  const selectedCount = useMemo(
    () => Array.from(taskStates.values()).filter((s) => s.selected).length,
    [taskStates],
  );

  const toggleTask = useCallback((taskId: string) => {
    setTaskStates((prev) => {
      const next = new Map(prev);
      const state = next.get(taskId);
      if (state && state.status === "pending") {
        next.set(taskId, { ...state, selected: !state.selected });
      }
      return next;
    });
  }, []);

  const toggleAll = useCallback(() => {
    setTaskStates((prev) => {
      const allSelected = Array.from(prev.values()).every(
        (s) => s.selected || s.status !== "pending",
      );
      const next = new Map(prev);
      for (const [id, state] of next) {
        if (state.status === "pending") {
          next.set(id, { ...state, selected: !allSelected });
        }
      }
      return next;
    });
  }, []);

  const handleCreatePRs = useCallback(async () => {
    setIsCreating(true);

    const selectedTasks = Array.from(taskStates.entries())
      .filter(([_, state]) => state.selected && state.status === "pending")
      .map(([id]) => id);

    for (const taskId of selectedTasks) {
      setTaskStates((prev) => {
        const next = new Map(prev);
        const state = next.get(taskId);
        if (state) next.set(taskId, { ...state, status: "creating" });
        return next;
      });

      try {
        const response = await apiClient.createPR(projectId, taskId);
        setTaskStates((prev) => {
          const next = new Map(prev);
          const state = next.get(taskId);
          if (state) {
            next.set(taskId, {
              ...state,
              status: "created",
              prUrl: response.data?.url,
            });
          }
          return next;
        });
      } catch (err) {
        setTaskStates((prev) => {
          const next = new Map(prev);
          const state = next.get(taskId);
          if (state) {
            next.set(taskId, {
              ...state,
              status: "error",
              error: err instanceof Error ? err.message : "Failed to create PR",
            });
          }
          return next;
        });
      }
    }

    setIsCreating(false);
  }, [taskStates, projectId]);

  const createdCount = useMemo(
    () => Array.from(taskStates.values()).filter((s) => s.status === "created").length,
    [taskStates],
  );

  const errorCount = useMemo(
    () => Array.from(taskStates.values()).filter((s) => s.status === "error").length,
    [taskStates],
  );

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={isCreating ? undefined : onClose}
      />
      <div className="relative z-10 w-full max-w-2xl max-h-[85vh] overflow-hidden rounded-xl border border-border bg-card shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div className="flex items-center gap-2">
            <GitPullRequest className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">
              {t("bulkPR.title")}
            </h2>
          </div>
          <button
            className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-accent transition-colors disabled:opacity-50"
            onClick={onClose}
            disabled={isCreating}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {eligibleTasks.length === 0 ? (
            <div className="text-center py-12">
              <GitPullRequest className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">
                {t("bulkPR.noEligibleTasks")}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {/* Select all */}
              <div className="flex items-center justify-between pb-2 border-b border-border">
                <button
                  className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                  onClick={toggleAll}
                  disabled={isCreating}
                >
                  {selectedCount === eligibleTasks.length ? (
                    <CheckSquare className="h-4 w-4 text-primary" />
                  ) : (
                    <Square className="h-4 w-4" />
                  )}
                  {t("bulkPR.selectAll")}
                </button>
                <span className="text-xs text-muted-foreground">
                  {t("bulkPR.selectedCount", { count: selectedCount })}
                </span>
              </div>

              {/* Task list */}
              {eligibleTasks.map((task) => {
                const state = taskStates.get(task.id);
                if (!state) return null;

                return (
                  <div
                    key={task.id}
                    className={cn(
                      "flex items-center gap-3 rounded-lg border p-3 transition-colors",
                      state.status === "created" && "border-green-500/30 bg-green-500/5",
                      state.status === "error" && "border-red-500/30 bg-red-500/5",
                      state.status === "creating" && "border-primary/30 bg-primary/5",
                      state.status === "pending" && "border-border",
                    )}
                  >
                    <button
                      className="shrink-0"
                      onClick={() => toggleTask(task.id)}
                      disabled={isCreating || state.status !== "pending"}
                    >
                      {state.selected ? (
                        <CheckSquare className="h-4 w-4 text-primary" />
                      ) : (
                        <Square className="h-4 w-4 text-muted-foreground" />
                      )}
                    </button>

                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {task.title}
                      </p>
                      {task.specId && (
                        <p className="text-xs text-muted-foreground">
                          #{task.specId}
                        </p>
                      )}
                    </div>

                    {/* Status indicator */}
                    <div className="shrink-0">
                      {state.status === "creating" && (
                        <Loader2 className="h-4 w-4 text-primary animate-spin" />
                      )}
                      {state.status === "created" && (
                        <div className="flex items-center gap-1">
                          <Check className="h-4 w-4 text-green-500" />
                          {state.prUrl && (
                            <a
                              href={state.prUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-primary hover:underline"
                            >
                              {t("bulkPR.viewPR")}
                            </a>
                          )}
                        </div>
                      )}
                      {state.status === "error" && (
                        <div className="flex items-center gap-1" title={state.error}>
                          <AlertCircle className="h-4 w-4 text-red-500" />
                          <span className="text-xs text-red-500">
                            {t("bulkPR.failed")}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Summary after completion */}
          {!isCreating && (createdCount > 0 || errorCount > 0) && (
            <div className="mt-4 rounded-lg border border-border bg-card/50 p-3 text-sm">
              {createdCount > 0 && (
                <p className="text-green-600">
                  {t("bulkPR.createdCount", { count: createdCount })}
                </p>
              )}
              {errorCount > 0 && (
                <p className="text-red-600">
                  {t("bulkPR.errorCount", { count: errorCount })}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border px-6 py-4">
          <button
            className="rounded-md px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            onClick={onClose}
            disabled={isCreating}
          >
            {createdCount > 0 ? t("bulkPR.done") : t("wizard.cancel")}
          </button>
          {eligibleTasks.length > 0 && selectedCount > 0 && createdCount === 0 && (
            <button
              className="flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
              disabled={isCreating || selectedCount === 0}
              onClick={handleCreatePRs}
            >
              {isCreating ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  {t("bulkPR.creating")}
                </>
              ) : (
                <>
                  <GitPullRequest className="h-3.5 w-3.5" />
                  {t("bulkPR.createPRs", { count: selectedCount })}
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
