"use client";

/**
 * TaskEditDialog - Dialog for editing existing task details
 *
 * Allows users to modify task properties including title, description,
 * classification fields, and review settings.
 *
 * Features:
 * - Pre-populates form with current task values
 * - Form validation (title required)
 * - Editable classification fields (category, priority, complexity, impact)
 * - Saves changes via API client
 * - Prevents save when no changes have been made
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { X, Loader2, Save } from "lucide-react";
import { cn } from "@auto-claude/ui";
import type {
  Task,
  TaskCategory,
  TaskPriority,
  TaskComplexity,
  TaskImpact,
  TaskMetadata,
} from "@auto-claude/types";
import { useTaskStore } from "@/stores/task-store";
import { apiClient } from "@/lib/data";

interface TaskEditDialogProps {
  task: Task;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved?: () => void;
}

const CATEGORIES: { id: TaskCategory; labelKey: string }[] = [
  { id: "feature", labelKey: "wizard.category.feature" },
  { id: "bug_fix", labelKey: "wizard.category.bug_fix" },
  { id: "refactoring", labelKey: "wizard.category.refactoring" },
  { id: "documentation", labelKey: "wizard.category.documentation" },
  { id: "security", labelKey: "wizard.category.security" },
  { id: "performance", labelKey: "wizard.category.performance" },
  { id: "ui_ux", labelKey: "wizard.category.ui_ux" },
  { id: "infrastructure", labelKey: "wizard.category.infrastructure" },
  { id: "testing", labelKey: "wizard.category.testing" },
];

const PRIORITIES: { id: TaskPriority; labelKey: string; color: string }[] = [
  { id: "urgent", labelKey: "wizard.priority.urgent", color: "border-red-500 bg-red-500/10 text-red-600" },
  { id: "high", labelKey: "wizard.priority.high", color: "border-orange-500 bg-orange-500/10 text-orange-600" },
  { id: "medium", labelKey: "wizard.priority.medium", color: "border-yellow-500 bg-yellow-500/10 text-yellow-600" },
  { id: "low", labelKey: "wizard.priority.low", color: "border-blue-500 bg-blue-500/10 text-blue-600" },
];

const COMPLEXITIES: { id: TaskComplexity; labelKey: string }[] = [
  { id: "trivial", labelKey: "wizard.complexityOption.trivial" },
  { id: "small", labelKey: "wizard.complexityOption.small" },
  { id: "medium", labelKey: "wizard.complexityOption.medium" },
  { id: "large", labelKey: "wizard.complexityOption.large" },
  { id: "complex", labelKey: "wizard.complexityOption.complex" },
];

const IMPACTS: { id: TaskImpact; labelKey: string; color: string }[] = [
  { id: "low", labelKey: "wizard.impact.low", color: "border-slate-400 bg-slate-400/10 text-slate-600" },
  { id: "medium", labelKey: "wizard.impact.medium", color: "border-yellow-500 bg-yellow-500/10 text-yellow-600" },
  { id: "high", labelKey: "wizard.impact.high", color: "border-orange-500 bg-orange-500/10 text-orange-600" },
  { id: "critical", labelKey: "wizard.impact.critical", color: "border-red-500 bg-red-500/10 text-red-600" },
];

export function TaskEditDialog({ task, open, onOpenChange, onSaved }: TaskEditDialogProps) {
  const { t } = useTranslation("kanban");
  const updateTask = useTaskStore((s) => s.updateTask);

  // Form state
  const [title, setTitle] = useState(task.title);
  const [description, setDescription] = useState(task.description);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Classification fields
  const [category, setCategory] = useState<TaskCategory | "">(task.metadata?.category || "");
  const [priority, setPriority] = useState<TaskPriority | "">(task.metadata?.priority || "");
  const [complexity, setComplexity] = useState<TaskComplexity | "">(task.metadata?.complexity || "");
  const [impact, setImpact] = useState<TaskImpact | "">(task.metadata?.impact || "");
  const [requireReviewBeforeCoding, setRequireReviewBeforeCoding] = useState(
    task.metadata?.requireReviewBeforeCoding ?? false,
  );

  // Reset form when task changes or dialog opens
  useEffect(() => {
    if (open) {
      setTitle(task.title);
      setDescription(task.description);
      setCategory(task.metadata?.category || "");
      setPriority(task.metadata?.priority || "");
      setComplexity(task.metadata?.complexity || "");
      setImpact(task.metadata?.impact || "");
      setRequireReviewBeforeCoding(task.metadata?.requireReviewBeforeCoding ?? false);
      setError(null);
    }
  }, [open, task]);

  // Escape key
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onOpenChange(false);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onOpenChange]);

  // Detect changes
  const hasChanges = useMemo(() => {
    return (
      title !== task.title ||
      description !== task.description ||
      category !== (task.metadata?.category || "") ||
      priority !== (task.metadata?.priority || "") ||
      complexity !== (task.metadata?.complexity || "") ||
      impact !== (task.metadata?.impact || "") ||
      requireReviewBeforeCoding !== (task.metadata?.requireReviewBeforeCoding ?? false)
    );
  }, [title, description, category, priority, complexity, impact, requireReviewBeforeCoding, task]);

  const handleSave = useCallback(async () => {
    if (!title.trim()) return;
    setIsSaving(true);
    setError(null);

    try {
      const metadata: Partial<TaskMetadata> = { ...task.metadata };
      if (category) metadata.category = category;
      else delete metadata.category;
      if (priority) metadata.priority = priority;
      else delete metadata.priority;
      if (complexity) metadata.complexity = complexity;
      else delete metadata.complexity;
      if (impact) metadata.impact = impact;
      else delete metadata.impact;
      metadata.requireReviewBeforeCoding = requireReviewBeforeCoding;

      const updates: Partial<Task> = {
        title: title.trim(),
        description: description.trim(),
        metadata: metadata as TaskMetadata,
      };

      // Optimistic update
      updateTask(task.id, updates);

      await apiClient.updateTask(task.projectId, task.id, updates);

      onOpenChange(false);
      onSaved?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("edit.saveError"));
    } finally {
      setIsSaving(false);
    }
  }, [
    title, description, category, priority, complexity, impact,
    requireReviewBeforeCoding, task, updateTask, onOpenChange, onSaved, t,
  ]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
      />
      <div className="relative z-10 w-full max-w-2xl max-h-[85vh] overflow-hidden rounded-xl border border-border bg-card shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 className="text-lg font-semibold">{t("edit.title")}</h2>
          <button
            className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-accent transition-colors"
            onClick={() => onOpenChange(false)}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Title */}
          <div>
            <label className="text-sm font-medium">{t("wizard.taskTitle")}</label>
            <input
              className="mt-1.5 w-full rounded-lg border border-border bg-background px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          {/* Description */}
          <div>
            <label className="text-sm font-medium">{t("wizard.descriptionLabel")}</label>
            <textarea
              className="mt-1.5 w-full resize-none rounded-lg border border-border bg-background px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
              rows={6}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          {/* Category */}
          <div>
            <label className="text-sm font-medium mb-2 block">{t("wizard.categoryLabel")}</label>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.id}
                  className={cn(
                    "rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
                    category === cat.id
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-muted-foreground hover:text-foreground",
                  )}
                  onClick={() => setCategory(category === cat.id ? "" : cat.id)}
                >
                  {t(cat.labelKey)}
                </button>
              ))}
            </div>
          </div>

          {/* Priority */}
          <div>
            <label className="text-sm font-medium mb-2 block">{t("wizard.priorityLabel")}</label>
            <div className="grid grid-cols-4 gap-2">
              {PRIORITIES.map((p) => (
                <button
                  key={p.id}
                  className={cn(
                    "rounded-lg border-2 p-3 text-center text-sm font-medium transition-colors",
                    priority === p.id ? p.color : "border-border hover:border-border/80",
                  )}
                  onClick={() => setPriority(priority === p.id ? "" : p.id)}
                >
                  {t(p.labelKey)}
                </button>
              ))}
            </div>
          </div>

          {/* Complexity */}
          <div>
            <label className="text-sm font-medium mb-2 block">{t("wizard.complexityLabel")}</label>
            <div className="flex flex-wrap gap-2">
              {COMPLEXITIES.map((c) => (
                <button
                  key={c.id}
                  className={cn(
                    "rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
                    complexity === c.id
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-muted-foreground hover:text-foreground",
                  )}
                  onClick={() => setComplexity(complexity === c.id ? "" : c.id)}
                >
                  {t(c.labelKey)}
                </button>
              ))}
            </div>
          </div>

          {/* Impact */}
          <div>
            <label className="text-sm font-medium mb-2 block">{t("wizard.impactLabel")}</label>
            <div className="grid grid-cols-4 gap-2">
              {IMPACTS.map((imp) => (
                <button
                  key={imp.id}
                  className={cn(
                    "rounded-lg border-2 p-3 text-center text-sm font-medium transition-colors",
                    impact === imp.id ? imp.color : "border-border hover:border-border/80",
                  )}
                  onClick={() => setImpact(impact === imp.id ? "" : imp.id)}
                >
                  {t(imp.labelKey)}
                </button>
              ))}
            </div>
          </div>

          {/* Review setting */}
          <div className="flex items-center gap-3 rounded-lg border border-border p-4">
            <input
              type="checkbox"
              id="editRequireReview"
              checked={requireReviewBeforeCoding}
              onChange={(e) => setRequireReviewBeforeCoding(e.target.checked)}
              className="h-4 w-4 rounded border-border"
            />
            <label htmlFor="editRequireReview" className="text-sm">
              <span className="font-medium">{t("wizard.requireReview")}</span>
              <p className="text-xs text-muted-foreground mt-0.5">
                {t("wizard.requireReviewDesc")}
              </p>
            </label>
          </div>

          {/* Error */}
          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-3 text-sm text-red-600">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border px-6 py-4">
          <button
            className="rounded-md px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            onClick={() => onOpenChange(false)}
          >
            {t("wizard.cancel")}
          </button>
          <button
            className="flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            disabled={!title.trim() || !hasChanges || isSaving}
            onClick={handleSave}
          >
            {isSaving ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                {t("edit.saving")}
              </>
            ) : (
              <>
                <Save className="h-3.5 w-3.5" />
                {t("edit.save")}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
