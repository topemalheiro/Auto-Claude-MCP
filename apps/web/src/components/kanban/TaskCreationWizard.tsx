"use client";

/**
 * TaskCreationWizard - Full-screen multi-step dialog for creating new tasks
 *
 * Steps:
 * 1. Description - Title and description with markdown preview
 * 2. File Selection - Browse and select relevant files via FileExplorerPanel
 * 3. Classification - Complexity, priority, impact, category
 * 4. Additional Context - Image attachments, referenced files, review settings
 *
 * Features:
 * - Draft auto-save to localStorage
 * - Form validation per step
 * - Submission via API client
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  X,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  Plus,
  Check,
  FileText,
  FolderTree,
  Settings2,
  Paperclip,
  RotateCcw,
  Loader2,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import type {
  TaskCategory,
  TaskPriority,
  TaskComplexity,
  TaskImpact,
  TaskMetadata,
  ReferencedFile,
} from "@auto-claude/types";
import { useTaskStore } from "@/stores/task-store";
import { apiClient } from "@/lib/data";
import { FileExplorerPanel } from "@/components/common/FileExplorerPanel";
import type { FileNode } from "@/hooks/useFileExplorer";
import { ImageUpload } from "@/components/common/ImageUpload";

interface TaskCreationWizardProps {
  open: boolean;
  onClose: () => void;
  projectId: string;
}

type WizardStep = "description" | "files" | "classification" | "context";

const STEPS: { id: WizardStep; iconKey: string }[] = [
  { id: "description", iconKey: "FileText" },
  { id: "files", iconKey: "FolderTree" },
  { id: "classification", iconKey: "Settings2" },
  { id: "context", iconKey: "Paperclip" },
];

const STEP_ICONS: Record<WizardStep, React.ReactNode> = {
  description: <FileText className="h-3.5 w-3.5" />,
  files: <FolderTree className="h-3.5 w-3.5" />,
  classification: <Settings2 className="h-3.5 w-3.5" />,
  context: <Paperclip className="h-3.5 w-3.5" />,
};

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
  {
    id: "urgent",
    labelKey: "wizard.priority.urgent",
    color: "border-red-500 bg-red-500/10 text-red-600",
  },
  {
    id: "high",
    labelKey: "wizard.priority.high",
    color: "border-orange-500 bg-orange-500/10 text-orange-600",
  },
  {
    id: "medium",
    labelKey: "wizard.priority.medium",
    color: "border-yellow-500 bg-yellow-500/10 text-yellow-600",
  },
  {
    id: "low",
    labelKey: "wizard.priority.low",
    color: "border-blue-500 bg-blue-500/10 text-blue-600",
  },
];

const COMPLEXITIES: {
  id: TaskComplexity;
  labelKey: string;
  descKey: string;
}[] = [
  {
    id: "trivial",
    labelKey: "wizard.complexityOption.trivial",
    descKey: "wizard.complexityOption.trivialDesc",
  },
  {
    id: "small",
    labelKey: "wizard.complexityOption.small",
    descKey: "wizard.complexityOption.smallDesc",
  },
  {
    id: "medium",
    labelKey: "wizard.complexityOption.medium",
    descKey: "wizard.complexityOption.mediumDesc",
  },
  {
    id: "large",
    labelKey: "wizard.complexityOption.large",
    descKey: "wizard.complexityOption.largeDesc",
  },
  {
    id: "complex",
    labelKey: "wizard.complexityOption.complex",
    descKey: "wizard.complexityOption.complexDesc",
  },
];

const IMPACTS: { id: TaskImpact; labelKey: string; color: string }[] = [
  {
    id: "low",
    labelKey: "wizard.impact.low",
    color: "border-slate-400 bg-slate-400/10 text-slate-600",
  },
  {
    id: "medium",
    labelKey: "wizard.impact.medium",
    color: "border-yellow-500 bg-yellow-500/10 text-yellow-600",
  },
  {
    id: "high",
    labelKey: "wizard.impact.high",
    color: "border-orange-500 bg-orange-500/10 text-orange-600",
  },
  {
    id: "critical",
    labelKey: "wizard.impact.critical",
    color: "border-red-500 bg-red-500/10 text-red-600",
  },
];

const DRAFT_KEY_PREFIX = "task-creation-draft";

interface DraftData {
  title: string;
  description: string;
  category: TaskCategory | "";
  priority: TaskPriority | "";
  complexity: TaskComplexity | "";
  impact: TaskImpact | "";
  referencedFiles: ReferencedFile[];
  requireReviewBeforeCoding: boolean;
}

function getDraftKey(projectId: string): string {
  return `${DRAFT_KEY_PREFIX}-${projectId}`;
}

function saveDraft(projectId: string, draft: DraftData): void {
  try {
    localStorage.setItem(getDraftKey(projectId), JSON.stringify(draft));
  } catch {
    // localStorage may be full or unavailable
  }
}

function loadDraft(projectId: string): DraftData | null {
  try {
    const raw = localStorage.getItem(getDraftKey(projectId));
    if (!raw) return null;
    return JSON.parse(raw) as DraftData;
  } catch {
    return null;
  }
}

function clearDraft(projectId: string): void {
  try {
    localStorage.removeItem(getDraftKey(projectId));
  } catch {
    // ignore
  }
}

function isDraftEmpty(draft: DraftData): boolean {
  return (
    !draft.title.trim() &&
    !draft.description.trim() &&
    !draft.category &&
    !draft.priority &&
    !draft.complexity &&
    !draft.impact
  );
}

export function TaskCreationWizard({
  open,
  onClose,
  projectId,
}: TaskCreationWizardProps) {
  const { t } = useTranslation("kanban");
  const addTask = useTaskStore((s) => s.addTask);

  // Wizard step
  const [step, setStep] = useState<WizardStep>("description");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDraftRestored, setIsDraftRestored] = useState(false);

  // Form state
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [showMarkdownPreview, setShowMarkdownPreview] = useState(false);
  const [category, setCategory] = useState<TaskCategory | "">("");
  const [priority, setPriority] = useState<TaskPriority | "">("");
  const [complexity, setComplexity] = useState<TaskComplexity | "">("");
  const [impact, setImpact] = useState<TaskImpact | "">("");
  const [referencedFiles, setReferencedFiles] = useState<ReferencedFile[]>([]);
  const [images, setImages] = useState<File[]>([]);
  const [requireReviewBeforeCoding, setRequireReviewBeforeCoding] =
    useState(false);

  const stepIndex = STEPS.findIndex((s) => s.id === step);

  // Load draft on open
  useEffect(() => {
    if (!open || !projectId) return;
    const draft = loadDraft(projectId);
    if (draft && !isDraftEmpty(draft)) {
      setTitle(draft.title);
      setDescription(draft.description);
      setCategory(draft.category);
      setPriority(draft.priority);
      setComplexity(draft.complexity);
      setImpact(draft.impact);
      setReferencedFiles(draft.referencedFiles ?? []);
      setRequireReviewBeforeCoding(draft.requireReviewBeforeCoding ?? false);
      setIsDraftRestored(true);
    } else {
      resetForm();
    }
  }, [open, projectId]);

  // Auto-save draft
  useEffect(() => {
    if (!open || !projectId) return;
    const timeout = setTimeout(() => {
      saveDraft(projectId, {
        title,
        description,
        category,
        priority,
        complexity,
        impact,
        referencedFiles,
        requireReviewBeforeCoding,
      });
    }, 500);
    return () => clearTimeout(timeout);
  }, [
    open,
    projectId,
    title,
    description,
    category,
    priority,
    complexity,
    impact,
    referencedFiles,
    requireReviewBeforeCoding,
  ]);

  // Escape key
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") handleClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  const resetForm = useCallback(() => {
    setTitle("");
    setDescription("");
    setCategory("");
    setPriority("");
    setComplexity("");
    setImpact("");
    setReferencedFiles([]);
    setImages([]);
    setRequireReviewBeforeCoding(false);
    setShowMarkdownPreview(false);
    setStep("description");
    setError(null);
    setIsDraftRestored(false);
  }, []);

  const handleClose = useCallback(() => {
    resetForm();
    onClose();
  }, [onClose, resetForm]);

  const handleClearDraft = useCallback(() => {
    clearDraft(projectId);
    resetForm();
  }, [projectId, resetForm]);

  const handleFileSelect = useCallback(
    (node: FileNode) => {
      if (!node.isDirectory) {
        setReferencedFiles((prev) => {
          if (prev.some((f) => f.path === node.path)) return prev;
          const newRef: ReferencedFile = {
            id: crypto.randomUUID(),
            path: node.path,
            name: node.name,
            isDirectory: false,
            addedAt: new Date(),
          };
          return [...prev, newRef];
        });
      }
    },
    [],
  );

  const handleRemoveFile = useCallback((path: string) => {
    setReferencedFiles((prev) => prev.filter((f) => f.path !== path));
  }, []);

  const canProceed = useMemo(() => {
    switch (step) {
      case "description":
        return title.trim().length > 0;
      case "files":
        return true; // optional
      case "classification":
        return true; // optional
      case "context":
        return true; // optional
    }
  }, [step, title]);

  const handleSubmit = useCallback(async () => {
    if (!title.trim()) return;
    setIsSubmitting(true);
    setError(null);

    try {
      const metadata: Partial<TaskMetadata> = {};
      if (category) metadata.category = category;
      if (priority) metadata.priority = priority;
      if (complexity) metadata.complexity = complexity;
      if (impact) metadata.impact = impact;
      if (referencedFiles.length > 0)
        metadata.referencedFiles = referencedFiles;
      if (requireReviewBeforeCoding)
        metadata.requireReviewBeforeCoding = true;

      const response = await apiClient.createTask(projectId, {
        title: title.trim(),
        description: description.trim(),
        metadata: metadata as TaskMetadata,
      });

      if (response.task) {
        addTask(response.task);
      }

      clearDraft(projectId);
      handleClose();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : t("wizard.createError"),
      );
    } finally {
      setIsSubmitting(false);
    }
  }, [
    title,
    description,
    category,
    priority,
    complexity,
    impact,
    referencedFiles,
    requireReviewBeforeCoding,
    projectId,
    addTask,
    handleClose,
    t,
  ]);

  const goNext = useCallback(() => {
    const idx = STEPS.findIndex((s) => s.id === step);
    if (idx < STEPS.length - 1) {
      setStep(STEPS[idx + 1].id);
    } else {
      handleSubmit();
    }
  }, [step, handleSubmit]);

  const goBack = useCallback(() => {
    const idx = STEPS.findIndex((s) => s.id === step);
    if (idx > 0) {
      setStep(STEPS[idx - 1].id);
    } else {
      handleClose();
    }
  }, [step, handleClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={handleClose}
      />
      <div className="relative z-10 w-full max-w-3xl max-h-[90vh] overflow-hidden rounded-xl border border-border bg-card shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div className="flex items-center gap-2">
            <Plus className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">
              {t("wizard.newTask")}
            </h2>
          </div>
          <div className="flex items-center gap-4">
            {/* Step indicators */}
            <div className="flex items-center gap-1">
              {STEPS.map((s, i) => (
                <button
                  key={s.id}
                  className={cn(
                    "flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
                    step === s.id
                      ? "bg-primary text-primary-foreground"
                      : i < stepIndex
                        ? "bg-primary/20 text-primary"
                        : "bg-secondary text-muted-foreground",
                  )}
                  onClick={() => {
                    // Allow navigating to completed steps
                    if (i <= stepIndex || canProceed) setStep(s.id);
                  }}
                >
                  {i < stepIndex ? (
                    <Check className="h-3 w-3" />
                  ) : (
                    STEP_ICONS[s.id]
                  )}
                  <span className="hidden sm:inline">
                    {t(`wizard.steps.${s.id}`)}
                  </span>
                </button>
              ))}
            </div>
            {isDraftRestored && (
              <button
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                onClick={handleClearDraft}
                title={t("wizard.clearDraft")}
              >
                <RotateCcw className="h-3 w-3" />
              </button>
            )}
            <button
              className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-accent transition-colors"
              onClick={handleClose}
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Step 1: Description */}
          {step === "description" && (
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium">
                  {t("wizard.taskTitle")}
                </label>
                <input
                  className="mt-1.5 w-full rounded-lg border border-border bg-background px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  placeholder={t("wizard.titlePlaceholder")}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  autoFocus
                />
              </div>
              <div>
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">
                    {t("wizard.descriptionLabel")}
                  </label>
                  <button
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                    onClick={() =>
                      setShowMarkdownPreview(!showMarkdownPreview)
                    }
                  >
                    {showMarkdownPreview
                      ? t("wizard.editMode")
                      : t("wizard.previewMode")}
                  </button>
                </div>
                {showMarkdownPreview ? (
                  <div className="mt-1.5 min-h-[180px] rounded-lg border border-border bg-background px-4 py-2.5 text-sm whitespace-pre-wrap">
                    {description || (
                      <span className="text-muted-foreground">
                        {t("wizard.noDescription")}
                      </span>
                    )}
                  </div>
                ) : (
                  <textarea
                    className="mt-1.5 w-full resize-none rounded-lg border border-border bg-background px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                    placeholder={t("wizard.descriptionPlaceholder")}
                    rows={8}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                  />
                )}
              </div>
            </div>
          )}

          {/* Step 2: File Selection */}
          {step === "files" && (
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-medium mb-1">
                  {t("wizard.fileSelection")}
                </h3>
                <p className="text-xs text-muted-foreground mb-3">
                  {t("wizard.fileSelectionDesc")}
                </p>
              </div>

              {/* Selected files list */}
              {referencedFiles.length > 0 && (
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">
                    {t("wizard.selectedFiles")} ({referencedFiles.length})
                  </label>
                  <div className="flex flex-wrap gap-1.5">
                    {referencedFiles.map((f) => (
                      <span
                        key={f.path}
                        className="flex items-center gap-1 rounded-md bg-secondary px-2 py-1 text-xs"
                      >
                        <FileText className="h-3 w-3 text-muted-foreground" />
                        {f.path.split("/").pop()}
                        <button
                          className="ml-0.5 hover:text-destructive transition-colors"
                          onClick={() => handleRemoveFile(f.path)}
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* File explorer */}
              <div className="h-[400px] rounded-lg border border-border overflow-hidden">
                <FileExplorerPanel
                  projectId={projectId}
                  onFileSelect={handleFileSelect}
                />
              </div>
            </div>
          )}

          {/* Step 3: Classification */}
          {step === "classification" && (
            <div className="space-y-6">
              <div>
                <label className="text-sm font-medium mb-2 block">
                  {t("wizard.categoryLabel")}
                </label>
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
                      onClick={() =>
                        setCategory(category === cat.id ? "" : cat.id)
                      }
                    >
                      {t(cat.labelKey)}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">
                  {t("wizard.priorityLabel")}
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {PRIORITIES.map((p) => (
                    <button
                      key={p.id}
                      className={cn(
                        "rounded-lg border-2 p-3 text-center text-sm font-medium transition-colors",
                        priority === p.id
                          ? p.color
                          : "border-border hover:border-border/80",
                      )}
                      onClick={() =>
                        setPriority(priority === p.id ? "" : p.id)
                      }
                    >
                      {t(p.labelKey)}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">
                  {t("wizard.complexityLabel")}
                </label>
                <div className="space-y-2">
                  {COMPLEXITIES.map((c) => (
                    <button
                      key={c.id}
                      className={cn(
                        "w-full rounded-lg border p-3 text-left transition-colors",
                        complexity === c.id
                          ? "border-primary bg-primary/5"
                          : "border-border hover:border-border/80",
                      )}
                      onClick={() =>
                        setComplexity(complexity === c.id ? "" : c.id)
                      }
                    >
                      <p className="text-sm font-medium">{t(c.labelKey)}</p>
                      <p className="text-xs text-muted-foreground">
                        {t(c.descKey)}
                      </p>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">
                  {t("wizard.impactLabel")}
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {IMPACTS.map((imp) => (
                    <button
                      key={imp.id}
                      className={cn(
                        "rounded-lg border-2 p-3 text-center text-sm font-medium transition-colors",
                        impact === imp.id
                          ? imp.color
                          : "border-border hover:border-border/80",
                      )}
                      onClick={() =>
                        setImpact(impact === imp.id ? "" : imp.id)
                      }
                    >
                      {t(imp.labelKey)}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Additional Context */}
          {step === "context" && (
            <div className="space-y-6">
              {/* Image attachments */}
              <div>
                <label className="text-sm font-medium mb-2 block">
                  {t("wizard.imageAttachments")}
                </label>
                <ImageUpload
                  onChange={setImages}
                  maxImages={5}
                  accept="image/*"
                />
              </div>

              {/* Referenced files summary */}
              {referencedFiles.length > 0 && (
                <div>
                  <label className="text-sm font-medium mb-2 block">
                    {t("wizard.referencedFiles")} ({referencedFiles.length})
                  </label>
                  <div className="rounded-lg border border-border bg-background p-3 space-y-1">
                    {referencedFiles.map((f) => (
                      <div
                        key={f.path}
                        className="flex items-center gap-2 text-xs text-muted-foreground"
                      >
                        <FileText className="h-3 w-3 shrink-0" />
                        <span className="truncate">{f.path}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Review setting */}
              <div className="flex items-center gap-3 rounded-lg border border-border p-4">
                <input
                  type="checkbox"
                  id="requireReview"
                  checked={requireReviewBeforeCoding}
                  onChange={(e) =>
                    setRequireReviewBeforeCoding(e.target.checked)
                  }
                  className="h-4 w-4 rounded border-border"
                />
                <label htmlFor="requireReview" className="text-sm">
                  <span className="font-medium">
                    {t("wizard.requireReview")}
                  </span>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {t("wizard.requireReviewDesc")}
                  </p>
                </label>
              </div>

              {/* Review summary */}
              <div className="rounded-lg border border-primary/20 bg-primary/5 p-4">
                <div className="flex items-start gap-2">
                  <Sparkles className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                  <div>
                    <p className="text-sm font-medium">
                      {t("wizard.aiHandlesRest")}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {t("wizard.aiHandlesRestDescription")}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/5 p-3 text-sm text-red-600">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border px-6 py-4">
          <button
            className="flex items-center gap-1.5 rounded-md px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            onClick={goBack}
          >
            {stepIndex === 0 ? (
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
            disabled={!canProceed || isSubmitting}
            onClick={goNext}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                {t("wizard.creating")}
              </>
            ) : stepIndex === STEPS.length - 1 ? (
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
