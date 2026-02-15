"use client";

import { useTranslation } from "react-i18next";
import { CheckCircle2, Target } from "lucide-react";
import { cn } from "@auto-claude/ui";
import { FeatureCard } from "./FeatureCard";
import type { RoadmapFeature, RoadmapPhase } from "@/stores/roadmap-store";

interface PhaseCardProps {
  phase: RoadmapPhase;
  features: RoadmapFeature[];
  onFeatureSelect: (feature: RoadmapFeature) => void;
  onConvertToSpec?: (feature: RoadmapFeature) => void;
  onGoToTask?: (specId: string) => void;
}

export function PhaseCard({
  phase,
  features,
  onFeatureSelect,
  onConvertToSpec,
  onGoToTask,
}: PhaseCardProps) {
  const { t } = useTranslation("views");
  const completedCount = features.filter((f) => f.status === "done").length;
  const progress =
    features.length > 0 ? (completedCount / features.length) * 100 : 0;

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
          <div
            className={cn(
              "flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-bold",
              completedCount === features.length && features.length > 0
                ? "bg-green-500/10 text-green-600"
                : "bg-primary/10 text-primary",
            )}
          >
            {completedCount === features.length && features.length > 0 ? (
              <CheckCircle2 className="h-3.5 w-3.5" />
            ) : (
              phase.order
            )}
          </div>
          {phase.title}
        </h2>
        <span className="text-xs text-muted-foreground">
          {completedCount}/{features.length} {t("roadmap.completed")}
        </span>
      </div>

      {/* Progress bar */}
      <div className="mb-3 h-1.5 w-full rounded-full bg-secondary">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${progress}%` }}
        />
      </div>

      {phase.description && (
        <p className="mb-3 text-xs text-muted-foreground">{phase.description}</p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {features.map((feature) => (
          <FeatureCard
            key={feature.id}
            feature={feature}
            onSelect={onFeatureSelect}
            onConvertToSpec={onConvertToSpec}
            onGoToTask={onGoToTask}
          />
        ))}
      </div>
    </div>
  );
}
