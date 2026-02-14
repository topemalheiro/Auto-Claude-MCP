"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
  X,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  Plus,
  Image,
  FileText,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import type {
  TaskCategory,
  TaskPriority,
  TaskComplexity,
} from "@auto-claude/types";

interface TaskCreationWizardProps {
  open: boolean;
  onClose: () => void;
  projectId: string;
}

type Step = "details" | "metadata" | "review";

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

const COMPLEXITIES: { id: TaskComplexity; labelKey: string; descKey: string }[] = [
  { id: "trivial", labelKey: "wizard.complexityOption.trivial", descKey: "wizard.complexityOption.trivialDesc" },
  { id: "small", labelKey: "wizard.complexityOption.small", descKey: "wizard.complexityOption.smallDesc" },
  { id: "medium", labelKey: "wizard.complexityOption.medium", descKey: "wizard.complexityOption.mediumDesc" },
  { id: "large", labelKey: "wizard.complexityOption.large", descKey: "wizard.complexityOption.largeDesc" },
  { id: "complex", labelKey: "wizard.complexityOption.complex", descKey: "wizard.complexityOption.complexDesc" },
];

export function TaskCreationWizard({
  open,
  onClose,
  projectId,
}: TaskCreationWizardProps) {
  const { t } = useTranslation("kanban");
  const [step, setStep] = useState<Step>("details");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<TaskCategory | "">("");
  const [priority, setPriority] = useState<TaskPriority | "">("");
  const [complexity, setComplexity] = useState<TaskComplexity | "">("");

  const resetForm = () => {
    setTitle("");
    setDescription("");
    setCategory("");
    setPriority("");
    setComplexity("");
    setStep("details");
  };

  const handleClose = useCallback(() => {
    resetForm();
    onClose();
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") handleClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, handleClose]);

  if (!open) return null;

  const handleSubmit = () => {
    // TODO: API call to create task
    console.log("Creating task:", { title, description, category, priority, complexity, projectId });
    handleClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-background/80 backdrop-blur-sm" onClick={handleClose} />
      <div className="relative z-10 w-full max-w-2xl max-h-[85vh] overflow-hidden rounded-xl border border-border bg-card shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div className="flex items-center gap-2">
            <Plus className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">{t("wizard.newTask")}</h2>
          </div>
          <div className="flex items-center gap-4">
            {/* Step indicators */}
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className={cn("rounded-full px-2 py-0.5", step === "details" ? "bg-primary text-primary-foreground" : "bg-secondary")}>{t("wizard.steps.details")}</span>
              <span className={cn("rounded-full px-2 py-0.5", step === "metadata" ? "bg-primary text-primary-foreground" : "bg-secondary")}>{t("wizard.steps.config")}</span>
              <span className={cn("rounded-full px-2 py-0.5", step === "review" ? "bg-primary text-primary-foreground" : "bg-secondary")}>{t("wizard.steps.review")}</span>
            </div>
            <button
              className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-accent transition-colors"
              onClick={handleClose}
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(85vh-130px)] p-6">
          {step === "details" && (
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium">{t("wizard.taskTitle")}</label>
                <input
                  className="mt-1.5 w-full rounded-lg border border-border bg-background px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  placeholder={t("wizard.titlePlaceholder")}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  autoFocus
                />
              </div>
              <div>
                <label className="text-sm font-medium">{t("wizard.descriptionLabel")}</label>
                <textarea
                  className="mt-1.5 w-full resize-none rounded-lg border border-border bg-background px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  placeholder={t("wizard.descriptionPlaceholder")}
                  rows={6}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
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
                          : "bg-secondary text-muted-foreground hover:text-foreground"
                      )}
                      onClick={() => setCategory(cat.id)}
                    >
                      {t(cat.labelKey)}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step === "metadata" && (
            <div className="space-y-6">
              <div>
                <label className="text-sm font-medium mb-2 block">{t("wizard.priorityLabel")}</label>
                <div className="grid grid-cols-4 gap-2">
                  {PRIORITIES.map((p) => (
                    <button
                      key={p.id}
                      className={cn(
                        "rounded-lg border-2 p-3 text-center text-sm font-medium transition-colors",
                        priority === p.id ? p.color : "border-border hover:border-border/80"
                      )}
                      onClick={() => setPriority(p.id)}
                    >
                      {t(p.labelKey)}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">{t("wizard.complexityLabel")}</label>
                <div className="space-y-2">
                  {COMPLEXITIES.map((c) => (
                    <button
                      key={c.id}
                      className={cn(
                        "w-full rounded-lg border p-3 text-left transition-colors",
                        complexity === c.id ? "border-primary bg-primary/5" : "border-border hover:border-border/80"
                      )}
                      onClick={() => setComplexity(c.id)}
                    >
                      <p className="text-sm font-medium">{t(c.labelKey)}</p>
                      <p className="text-xs text-muted-foreground">{t(c.descKey)}</p>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step === "review" && (
            <div className="space-y-4">
              <h3 className="text-sm font-medium">{t("wizard.reviewTask")}</h3>
              <div className="rounded-lg border border-border bg-card/50 p-4 space-y-3">
                <div>
                  <p className="text-xs text-muted-foreground">{t("detail.title")}</p>
                  <p className="text-sm font-medium">{title || t("wizard.untitled")}</p>
                </div>
                {description && (
                  <div>
                    <p className="text-xs text-muted-foreground">{t("detail.description")}</p>
                    <p className="text-sm whitespace-pre-wrap">{description}</p>
                  </div>
                )}
                <div className="flex items-center gap-3 flex-wrap">
                  {category && (
                    <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">
                      {t(`wizard.category.${category}`)}
                    </span>
                  )}
                  {priority && (
                    <span className={cn(
                      "rounded-full px-2.5 py-0.5 text-xs",
                      PRIORITIES.find((p) => p.id === priority)?.color
                    )}>
                      {t(`wizard.priority.${priority}`)}
                    </span>
                  )}
                  {complexity && (
                    <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">
                      {t(`wizard.complexityOption.${complexity}`)}
                    </span>
                  )}
                </div>
              </div>
              <div className="rounded-lg border border-primary/20 bg-primary/5 p-4">
                <div className="flex items-start gap-2">
                  <Sparkles className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                  <div>
                    <p className="text-sm font-medium">{t("wizard.aiHandlesRest")}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {t("wizard.aiHandlesRestDescription")}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border px-6 py-4">
          <button
            className="flex items-center gap-1.5 rounded-md px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            onClick={() => {
              if (step === "details") handleClose();
              else if (step === "metadata") setStep("details");
              else setStep("metadata");
            }}
          >
            {step === "details" ? (
              t("wizard.cancel")
            ) : (
              <>
                <ArrowLeft className="h-3.5 w-3.5" />
                {t("wizard.back")}
              </>
            )}
          </button>
          <button
            className="flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            disabled={step === "details" && !title.trim()}
            onClick={() => {
              if (step === "details") setStep("metadata");
              else if (step === "metadata") setStep("review");
              else handleSubmit();
            }}
          >
            {step === "review" ? (
              <>
                <Sparkles className="h-3.5 w-3.5" />
                {t("wizard.createTask")}
              </>
            ) : (
              <>
                {t("wizard.continue")}
                <ArrowRight className="h-3.5 w-3.5" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
