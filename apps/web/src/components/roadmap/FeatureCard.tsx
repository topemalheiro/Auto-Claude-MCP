"use client";

import { useTranslation } from "react-i18next";
import { CheckCircle2, ExternalLink, Play } from "lucide-react";
import { cn } from "@auto-claude/ui";
import type { RoadmapFeature } from "@/stores/roadmap-store";

interface FeatureCardProps {
  feature: RoadmapFeature;
  onSelect: (feature: RoadmapFeature) => void;
  onConvertToSpec?: (feature: RoadmapFeature) => void;
  onGoToTask?: (specId: string) => void;
}

const PRIORITY_COLORS: Record<string, string> = {
  high: "bg-red-500/10 text-red-600",
  medium: "bg-yellow-500/10 text-yellow-600",
  low: "bg-blue-500/10 text-blue-600",
};

const STATUS_COLORS: Record<string, string> = {
  done: "bg-green-500/10 text-green-600",
  in_progress: "bg-yellow-500/10 text-yellow-600",
  planned: "bg-secondary text-muted-foreground",
  under_review: "bg-purple-500/10 text-purple-600",
};

export function FeatureCard({
  feature,
  onSelect,
  onConvertToSpec,
  onGoToTask,
}: FeatureCardProps) {
  const { t } = useTranslation("views");

  const statusLabel = (status: string) => {
    if (status === "in_progress") return t("roadmap.status.inProgress");
    if (status === "done") return t("roadmap.status.completed");
    if (status === "under_review") return t("roadmap.status.underReview");
    return t("roadmap.status.planned");
  };

  return (
    <div
      className="rounded-lg border border-border bg-card p-4 cursor-pointer hover:shadow-md transition-all"
      onClick={() => onSelect(feature)}
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-medium">{feature.title}</h3>
        <span
          className={cn(
            "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium",
            STATUS_COLORS[feature.status] ?? STATUS_COLORS.planned,
          )}
        >
          {statusLabel(feature.status)}
        </span>
      </div>
      <p className="mt-1.5 text-xs text-muted-foreground line-clamp-2">
        {feature.description}
      </p>
      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {feature.priority !== undefined && (
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-[10px] font-medium",
                PRIORITY_COLORS[
                  feature.priority <= 1
                    ? "high"
                    : feature.priority <= 2
                      ? "medium"
                      : "low"
                ] ?? PRIORITY_COLORS.medium,
              )}
            >
              {feature.priority <= 1
                ? "high"
                : feature.priority <= 2
                  ? "medium"
                  : "low"}
            </span>
          )}
          {feature.taskOutcome && (
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-[10px] font-medium",
                feature.taskOutcome === "completed"
                  ? "bg-green-500/10 text-green-600"
                  : feature.taskOutcome === "failed"
                    ? "bg-red-500/10 text-red-600"
                    : "bg-yellow-500/10 text-yellow-600",
              )}
            >
              {feature.taskOutcome}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {feature.status === "done" ? (
            <CheckCircle2 className="h-4 w-4 text-green-500" />
          ) : feature.linkedSpecId ? (
            <button
              className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                onGoToTask?.(feature.linkedSpecId!);
              }}
            >
              <ExternalLink className="h-3 w-3" />
              {t("roadmap.viewTask")}
            </button>
          ) : (
            onConvertToSpec && (
              <button
                className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                onClick={(e) => {
                  e.stopPropagation();
                  onConvertToSpec(feature);
                }}
              >
                <Play className="h-3 w-3" />
                {t("roadmap.build")}
              </button>
            )
          )}
        </div>
      </div>
    </div>
  );
}
