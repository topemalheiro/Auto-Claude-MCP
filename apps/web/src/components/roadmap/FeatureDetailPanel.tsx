"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  X,
  Zap,
  ExternalLink,
  Trash2,
  CheckCircle2,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import type { RoadmapFeature } from "@/stores/roadmap-store";

interface FeatureDetailPanelProps {
  feature: RoadmapFeature;
  onClose: () => void;
  onConvertToSpec?: (feature: RoadmapFeature) => void;
  onGoToTask?: (specId: string) => void;
  onDelete?: (featureId: string) => void;
}

const STATUS_LABELS: Record<string, string> = {
  under_review: "Under Review",
  planned: "Planned",
  in_progress: "In Progress",
  done: "Done",
};

export function FeatureDetailPanel({
  feature,
  onClose,
  onConvertToSpec,
  onGoToTask,
  onDelete,
}: FeatureDetailPanelProps) {
  const { t } = useTranslation("views");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const handleDelete = () => {
    onDelete?.(feature.id);
    onClose();
  };

  const priorityLabel =
    feature.priority !== undefined
      ? feature.priority <= 1
        ? "High"
        : feature.priority <= 2
          ? "Medium"
          : "Low"
      : "—";

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-96 border-l border-border bg-card shadow-xl flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border p-4">
        <h2 className="text-sm font-semibold">{t("roadmap.detail.title")}</h2>
        <div className="flex items-center gap-1">
          {onDelete && (
            <button
              className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-red-500/10 hover:text-red-500 transition-colors"
              onClick={() => setShowDeleteConfirm(true)}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
          <button
            className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-accent transition-colors"
            onClick={onClose}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div>
          <h3 className="text-lg font-semibold">{feature.title}</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {feature.description}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-md border border-border p-3">
            <p className="text-xs text-muted-foreground">
              {t("roadmap.detail.priority")}
            </p>
            <p className="text-sm font-medium">{priorityLabel}</p>
          </div>
          <div className="rounded-md border border-border p-3">
            <p className="text-xs text-muted-foreground">
              {t("roadmap.detail.status")}
            </p>
            <p className="text-sm font-medium">
              {STATUS_LABELS[feature.status] ?? feature.status}
            </p>
          </div>
        </div>

        {/* Task outcome */}
        {feature.taskOutcome && (
          <div className="flex items-center gap-2 rounded-md border border-border p-3">
            <CheckCircle2
              className={cn(
                "h-4 w-4",
                feature.taskOutcome === "completed"
                  ? "text-green-500"
                  : feature.taskOutcome === "failed"
                    ? "text-red-500"
                    : "text-yellow-500",
              )}
            />
            <span className="text-sm font-medium capitalize">
              {feature.taskOutcome}
            </span>
          </div>
        )}

        {/* Source */}
        {feature.source && (
          <div className="rounded-md border border-border p-3">
            <p className="text-xs text-muted-foreground">
              {t("roadmap.detail.source")}
            </p>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-sm font-medium capitalize">
                {feature.source.provider}
              </span>
              {feature.source.issueUrl && (
                <a
                  href={feature.source.issueUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          </div>
        )}

        {/* Linked task */}
        {feature.linkedSpecId && (
          <div className="rounded-md border border-border p-3">
            <p className="text-xs text-muted-foreground">
              {t("roadmap.detail.linkedTask")}
            </p>
            <button
              className="mt-1 flex items-center gap-1.5 text-sm text-primary hover:underline"
              onClick={() => onGoToTask?.(feature.linkedSpecId!)}
            >
              <ExternalLink className="h-3 w-3" />
              {feature.linkedSpecId}
            </button>
          </div>
        )}
      </div>

      {/* Actions */}
      {!feature.taskOutcome && !feature.linkedSpecId && feature.status !== "done" && onConvertToSpec && (
        <div className="shrink-0 border-t border-border p-4">
          <button
            className="w-full flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 transition-colors"
            onClick={() => onConvertToSpec(feature)}
          >
            <Zap className="h-4 w-4" />
            {t("roadmap.detail.convertToTask")}
          </button>
        </div>
      )}

      {feature.linkedSpecId && !feature.taskOutcome && (
        <div className="shrink-0 border-t border-border p-4">
          <button
            className="w-full flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 transition-colors"
            onClick={() => onGoToTask?.(feature.linkedSpecId!)}
          >
            <ExternalLink className="h-4 w-4" />
            {t("roadmap.detail.goToTask")}
          </button>
        </div>
      )}

      {/* Delete confirmation overlay */}
      {showDeleteConfirm && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/95 p-6">
          <div className="text-center space-y-4">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10">
              <Trash2 className="h-6 w-6 text-red-500" />
            </div>
            <div>
              <h3 className="font-semibold">
                {t("roadmap.detail.deleteConfirmTitle")}
              </h3>
              <p className="mt-1 text-sm text-muted-foreground">
                {t("roadmap.detail.deleteConfirmDescription", {
                  title: feature.title,
                })}
              </p>
            </div>
            <div className="flex justify-center gap-2">
              <button
                className="rounded-md border border-border px-4 py-2 text-sm hover:bg-accent transition-colors"
                onClick={() => setShowDeleteConfirm(false)}
              >
                {t("roadmap.detail.cancel")}
              </button>
              <button
                className="rounded-md bg-red-500 px-4 py-2 text-sm text-white hover:bg-red-600 transition-colors"
                onClick={handleDelete}
              >
                {t("roadmap.detail.delete")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
