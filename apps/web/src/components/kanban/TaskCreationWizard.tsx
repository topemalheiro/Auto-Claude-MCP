"use client";

import { useState } from "react";
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

const CATEGORIES: { id: TaskCategory; label: string }[] = [
  { id: "feature", label: "Feature" },
  { id: "bug_fix", label: "Bug Fix" },
  { id: "refactoring", label: "Refactoring" },
  { id: "documentation", label: "Documentation" },
  { id: "security", label: "Security" },
  { id: "performance", label: "Performance" },
  { id: "ui_ux", label: "UI/UX" },
  { id: "infrastructure", label: "Infrastructure" },
  { id: "testing", label: "Testing" },
];

const PRIORITIES: { id: TaskPriority; label: string; color: string }[] = [
  { id: "urgent", label: "Urgent", color: "border-red-500 bg-red-500/10 text-red-600" },
  { id: "high", label: "High", color: "border-orange-500 bg-orange-500/10 text-orange-600" },
  { id: "medium", label: "Medium", color: "border-yellow-500 bg-yellow-500/10 text-yellow-600" },
  { id: "low", label: "Low", color: "border-blue-500 bg-blue-500/10 text-blue-600" },
];

const COMPLEXITIES: { id: TaskComplexity; label: string; description: string }[] = [
  { id: "trivial", label: "Trivial", description: "Quick fix, single file" },
  { id: "small", label: "Small", description: "Few files, straightforward" },
  { id: "medium", label: "Medium", description: "Multiple files, some complexity" },
  { id: "large", label: "Large", description: "Many files, cross-cutting" },
  { id: "complex", label: "Complex", description: "Architectural changes" },
];

type Step = "details" | "metadata" | "review";

export function TaskCreationWizard({
  open,
  onClose,
  projectId,
}: TaskCreationWizardProps) {
  const [step, setStep] = useState<Step>("details");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<TaskCategory | "">("");
  const [priority, setPriority] = useState<TaskPriority | "">("");
  const [complexity, setComplexity] = useState<TaskComplexity | "">("");

  if (!open) return null;

  const handleSubmit = () => {
    // TODO: API call to create task
    console.log("Creating task:", { title, description, category, priority, complexity, projectId });
    onClose();
    resetForm();
  };

  const resetForm = () => {
    setTitle("");
    setDescription("");
    setCategory("");
    setPriority("");
    setComplexity("");
    setStep("details");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-background/80 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 w-full max-w-2xl max-h-[85vh] overflow-hidden rounded-xl border border-border bg-card shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div className="flex items-center gap-2">
            <Plus className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">New Task</h2>
          </div>
          <div className="flex items-center gap-4">
            {/* Step indicators */}
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className={cn("rounded-full px-2 py-0.5", step === "details" ? "bg-primary text-primary-foreground" : "bg-secondary")}>1. Details</span>
              <span className={cn("rounded-full px-2 py-0.5", step === "metadata" ? "bg-primary text-primary-foreground" : "bg-secondary")}>2. Config</span>
              <span className={cn("rounded-full px-2 py-0.5", step === "review" ? "bg-primary text-primary-foreground" : "bg-secondary")}>3. Review</span>
            </div>
            <button
              className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-accent transition-colors"
              onClick={onClose}
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
                <label className="text-sm font-medium">Task Title</label>
                <input
                  className="mt-1.5 w-full rounded-lg border border-border bg-background px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  placeholder="What needs to be done?"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  autoFocus
                />
              </div>
              <div>
                <label className="text-sm font-medium">Description</label>
                <textarea
                  className="mt-1.5 w-full resize-none rounded-lg border border-border bg-background px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  placeholder="Describe the task in detail. What's the expected outcome? Any specific requirements?"
                  rows={6}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Category</label>
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
                      {cat.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step === "metadata" && (
            <div className="space-y-6">
              <div>
                <label className="text-sm font-medium mb-2 block">Priority</label>
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
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Complexity</label>
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
                      <p className="text-sm font-medium">{c.label}</p>
                      <p className="text-xs text-muted-foreground">{c.description}</p>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step === "review" && (
            <div className="space-y-4">
              <h3 className="text-sm font-medium">Review Task</h3>
              <div className="rounded-lg border border-border bg-card/50 p-4 space-y-3">
                <div>
                  <p className="text-xs text-muted-foreground">Title</p>
                  <p className="text-sm font-medium">{title || "Untitled"}</p>
                </div>
                {description && (
                  <div>
                    <p className="text-xs text-muted-foreground">Description</p>
                    <p className="text-sm whitespace-pre-wrap">{description}</p>
                  </div>
                )}
                <div className="flex items-center gap-3 flex-wrap">
                  {category && (
                    <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">
                      {CATEGORIES.find((c) => c.id === category)?.label}
                    </span>
                  )}
                  {priority && (
                    <span className={cn(
                      "rounded-full px-2.5 py-0.5 text-xs",
                      PRIORITIES.find((p) => p.id === priority)?.color
                    )}>
                      {PRIORITIES.find((p) => p.id === priority)?.label}
                    </span>
                  )}
                  {complexity && (
                    <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">
                      {complexity}
                    </span>
                  )}
                </div>
              </div>
              <div className="rounded-lg border border-primary/20 bg-primary/5 p-4">
                <div className="flex items-start gap-2">
                  <Sparkles className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                  <div>
                    <p className="text-sm font-medium">AI will handle the rest</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Auto Claude will analyze the task, create a plan, write
                      code, and run tests automatically.
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
              if (step === "details") onClose();
              else if (step === "metadata") setStep("details");
              else setStep("metadata");
            }}
          >
            {step === "details" ? (
              "Cancel"
            ) : (
              <>
                <ArrowLeft className="h-3.5 w-3.5" />
                Back
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
                Create Task
              </>
            ) : (
              <>
                Continue
                <ArrowRight className="h-3.5 w-3.5" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
