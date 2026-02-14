"use client";

import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  X,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileText,
  GitPullRequest,
  ExternalLink,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import type { Task } from "@auto-claude/types";

interface TaskDetailModalProps {
  task: Task;
  onClose: () => void;
}

export function TaskDetailModal({ task, onClose }: TaskDetailModalProps) {
  const { t } = useTranslation("kanban");

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-3xl max-h-[85vh] overflow-hidden rounded-xl border border-border bg-card shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-border p-6">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <span
                className={cn(
                  "rounded-full px-2.5 py-0.5 text-xs font-medium",
                  task.status === "done" && "bg-green-500/10 text-green-600",
                  task.status === "in_progress" && "bg-yellow-500/10 text-yellow-600",
                  task.status === "error" && "bg-red-500/10 text-red-600",
                  task.status === "human_review" && "bg-orange-500/10 text-orange-600",
                  !["done", "in_progress", "error", "human_review"].includes(task.status) &&
                    "bg-secondary text-muted-foreground"
                )}
              >
                {t(`columns.${task.status}`, task.status)}
              </span>
              {task.metadata?.category && (
                <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs text-muted-foreground">
                  {task.metadata.category}
                </span>
              )}
            </div>
            <h2 className="text-xl font-semibold">{task.title}</h2>
          </div>
          <button
            className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-accent transition-colors"
            onClick={onClose}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(85vh-80px)] p-6 space-y-6">
          {/* Description */}
          {task.description && (
            <div>
              <h3 className="text-sm font-medium mb-2">{t("detail.description")}</h3>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                {task.description}
              </p>
            </div>
          )}

          {/* Execution Progress */}
          {task.executionProgress && (
            <div>
              <h3 className="text-sm font-medium mb-2">{t("detail.executionProgress")}</h3>
              <div className="rounded-lg border border-border p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-muted-foreground capitalize">
                    {t("detail.phase", { phase: task.executionProgress.phase })}
                  </span>
                  <span className="text-sm font-medium">
                    {task.executionProgress.overallProgress}%
                  </span>
                </div>
                <div className="h-2 w-full rounded-full bg-secondary">
                  <div
                    className="h-2 rounded-full bg-primary transition-all"
                    style={{
                      width: `${task.executionProgress.overallProgress}%`,
                    }}
                  />
                </div>
                {task.executionProgress.message && (
                  <p className="mt-2 text-xs text-muted-foreground">
                    {task.executionProgress.message}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Subtasks */}
          {task.subtasks && task.subtasks.length > 0 && (
            <div>
              <h3 className="text-sm font-medium mb-2">
                {t("detail.subtasks", {
                  completed: task.subtasks.filter((s) => s.status === "completed").length,
                  total: task.subtasks.length,
                })}
              </h3>
              <div className="space-y-2">
                {task.subtasks.map((subtask) => (
                  <div
                    key={subtask.id}
                    className="flex items-start gap-2 rounded-md border border-border p-3"
                  >
                    {subtask.status === "completed" ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                    ) : subtask.status === "failed" ? (
                      <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
                    ) : subtask.status === "in_progress" ? (
                      <Clock className="h-4 w-4 text-yellow-500 mt-0.5 shrink-0 animate-pulse" />
                    ) : (
                      <Clock className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{subtask.title}</p>
                      {subtask.description && (
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {subtask.description}
                        </p>
                      )}
                      {subtask.files && subtask.files.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {subtask.files.map((file) => (
                            <span
                              key={file}
                              className="inline-flex items-center gap-1 rounded bg-secondary px-1.5 py-0.5 text-[10px] text-muted-foreground"
                            >
                              <FileText className="h-2.5 w-2.5" />
                              {file.split("/").pop()}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* QA Report */}
          {task.qaReport && (
            <div>
              <h3 className="text-sm font-medium mb-2">{t("detail.qaReport")}</h3>
              <div
                className={cn(
                  "rounded-lg border p-4",
                  task.qaReport.status === "passed" &&
                    "border-green-500/30 bg-green-500/5",
                  task.qaReport.status === "failed" &&
                    "border-red-500/30 bg-red-500/5",
                  task.qaReport.status === "pending" &&
                    "border-border bg-card"
                )}
              >
                <p className="text-sm font-medium capitalize">
                  {t("detail.qaStatus", { status: task.qaReport.status })}
                </p>
                {task.qaReport.issues && task.qaReport.issues.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {task.qaReport.issues.map((issue) => (
                      <li
                        key={issue.id}
                        className="text-xs text-muted-foreground flex items-start gap-1"
                      >
                        <span
                          className={cn(
                            "shrink-0 mt-0.5 h-1.5 w-1.5 rounded-full",
                            issue.severity === "critical" && "bg-red-500",
                            issue.severity === "major" && "bg-orange-500",
                            issue.severity === "minor" && "bg-yellow-500"
                          )}
                        />
                        {issue.description}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}

          {/* Metadata */}
          {task.metadata && (
            <div>
              <h3 className="text-sm font-medium mb-2">{t("detail.details")}</h3>
              <div className="grid grid-cols-2 gap-3">
                {task.metadata.priority && (
                  <div className="rounded-md border border-border p-3">
                    <p className="text-xs text-muted-foreground">{t("detail.priority")}</p>
                    <p className="text-sm font-medium capitalize">
                      {task.metadata.priority}
                    </p>
                  </div>
                )}
                {task.metadata.complexity && (
                  <div className="rounded-md border border-border p-3">
                    <p className="text-xs text-muted-foreground">{t("detail.complexity")}</p>
                    <p className="text-sm font-medium capitalize">
                      {task.metadata.complexity}
                    </p>
                  </div>
                )}
                {task.metadata.impact && (
                  <div className="rounded-md border border-border p-3">
                    <p className="text-xs text-muted-foreground">{t("detail.impact")}</p>
                    <p className="text-sm font-medium capitalize">
                      {task.metadata.impact}
                    </p>
                  </div>
                )}
                {task.metadata.model && (
                  <div className="rounded-md border border-border p-3">
                    <p className="text-xs text-muted-foreground">{t("detail.model")}</p>
                    <p className="text-sm font-medium capitalize">
                      {task.metadata.model}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* PR Link */}
          {task.metadata?.prUrl && (
            <div>
              <a
                href={task.metadata.prUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 rounded-lg border border-border p-3 hover:bg-accent transition-colors"
              >
                <GitPullRequest className="h-4 w-4 text-green-500" />
                <span className="text-sm">{t("detail.viewPullRequest")}</span>
                <ExternalLink className="h-3 w-3 text-muted-foreground ml-auto" />
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
