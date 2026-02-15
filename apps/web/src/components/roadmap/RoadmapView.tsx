"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
  Map,
  Sparkles,
  Target,
  TrendingUp,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useRoadmapStore } from "@/stores/roadmap-store";
import type { RoadmapFeature } from "@/stores/roadmap-store";
import { apiClient } from "@/lib/data/api-client";
import { RoadmapHeader } from "./RoadmapHeader";
import { PhaseCard } from "./PhaseCard";
import { FeatureCard } from "./FeatureCard";
import { FeatureDetailPanel } from "./FeatureDetailPanel";

interface RoadmapViewProps {
  projectId: string;
}

type ViewMode = "kanban" | "timeline" | "list";

export function RoadmapView({ projectId }: RoadmapViewProps) {
  const { t } = useTranslation("views");
  const [activeTab, setActiveTab] = useState<ViewMode>("kanban");
  const [selectedFeature, setSelectedFeature] =
    useState<RoadmapFeature | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const {
    roadmap,
    generationStatus,
    setRoadmap,
    setGenerationStatus,
    deleteFeature,
  } = useRoadmapStore();

  // Fetch roadmap data on mount
  const fetchRoadmap = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.getRoadmap(projectId);
      if (response.roadmap) {
        setRoadmap(response.roadmap as ReturnType<typeof useRoadmapStore.getState>["roadmap"]);
      }
    } catch {
      // Roadmap may not exist yet — this is expected
    } finally {
      setIsLoading(false);
    }
  }, [projectId, setRoadmap]);

  useEffect(() => {
    fetchRoadmap();
  }, [fetchRoadmap]);

  const handleGenerate = async () => {
    setGenerationStatus({
      phase: "generating",
      progress: 0,
      message: t("roadmap.generating"),
    });
    try {
      const response = await apiClient.generateRoadmap(projectId);
      if (response.roadmap) {
        setRoadmap(response.roadmap as ReturnType<typeof useRoadmapStore.getState>["roadmap"]);
      }
      setGenerationStatus({
        phase: "complete",
        progress: 100,
        message: t("roadmap.generateComplete"),
      });
    } catch {
      setGenerationStatus({
        phase: "error",
        progress: 0,
        message: t("roadmap.generateError"),
      });
    }
  };

  const handleRefresh = () => {
    fetchRoadmap();
  };

  const handleDeleteFeature = (featureId: string) => {
    deleteFeature(featureId);
    if (selectedFeature?.id === featureId) {
      setSelectedFeature(null);
    }
  };

  // Group features by phase
  const featuresByPhase = (phaseId: string) =>
    roadmap?.features.filter((f) => f.phaseId === phaseId) ?? [];

  const allFeatures = roadmap?.features ?? [];
  const sortedPhases = [...(roadmap?.phases ?? [])].sort(
    (a, b) => a.order - b.order,
  );

  // Status helpers
  const statusLabel = (status: string) => {
    if (status === "in_progress") return t("roadmap.status.inProgress");
    if (status === "done") return t("roadmap.status.completed");
    if (status === "under_review") return t("roadmap.status.underReview");
    return t("roadmap.status.planned");
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="mt-4 text-sm text-muted-foreground">
          {t("roadmap.loading")}
        </p>
      </div>
    );
  }

  // Generation in progress
  if (
    generationStatus.phase !== "idle" &&
    generationStatus.phase !== "complete" &&
    generationStatus.phase !== "error"
  ) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8">
        <div className="max-w-md text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
          <h2 className="mt-4 text-lg font-semibold">
            {t("roadmap.generatingTitle")}
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {generationStatus.message}
          </p>
          <div className="mt-4 h-2 w-full rounded-full bg-secondary">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${generationStatus.progress}%` }}
            />
          </div>
        </div>
      </div>
    );
  }

  // Empty state
  if (!roadmap) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8">
        <div className="max-w-md text-center">
          <div className="mb-6 flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
              <Map className="h-8 w-8 text-primary" />
            </div>
          </div>
          <h2 className="mb-3 text-xl font-semibold">
            {t("roadmap.empty.title")}
          </h2>
          <p className="mb-6 text-sm text-muted-foreground">
            {t("roadmap.empty.description")}
          </p>
          <button
            className="flex items-center gap-2 mx-auto rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            onClick={handleGenerate}
          >
            <Sparkles className="h-4 w-4" />
            {t("roadmap.empty.generate")}
          </button>
        </div>
      </div>
    );
  }

  // Main roadmap view
  return (
    <div className="flex h-full flex-col overflow-hidden">
      <RoadmapHeader
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onRefresh={handleRefresh}
        onAddFeature={() => {
          /* TODO: add feature dialog */
        }}
        onGenerate={handleGenerate}
        featureCount={allFeatures.length}
        phaseCount={sortedPhases.length}
      />

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {activeTab === "kanban" && (
          <div className="space-y-8">
            {sortedPhases.map((phase) => (
              <PhaseCard
                key={phase.id}
                phase={phase}
                features={featuresByPhase(phase.id)}
                onFeatureSelect={setSelectedFeature}
                onGoToTask={() => {
                  /* TODO: navigate to task */
                }}
              />
            ))}
          </div>
        )}

        {activeTab === "timeline" && (
          <div className="space-y-4">
            {sortedPhases.map((phase, idx) => (
              <div key={phase.id} className="flex gap-4">
                <div className="flex flex-col items-center">
                  <div
                    className={cn(
                      "flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold",
                      idx === 0 && "bg-green-500/10 text-green-600",
                      idx === 1 && "bg-yellow-500/10 text-yellow-600",
                      idx >= 2 && "bg-blue-500/10 text-blue-600",
                    )}
                  >
                    {phase.order}
                  </div>
                  {idx < sortedPhases.length - 1 && (
                    <div className="my-2 flex-1 w-px bg-border" />
                  )}
                </div>
                <div className="flex-1 pb-6">
                  <h3 className="text-sm font-semibold mb-2">{phase.title}</h3>
                  <div className="space-y-2">
                    {featuresByPhase(phase.id).map((feature) => (
                      <div
                        key={feature.id}
                        className="flex items-center gap-2 rounded-md border border-border bg-card/50 p-2.5 cursor-pointer hover:bg-accent/50 transition-colors"
                        onClick={() => setSelectedFeature(feature)}
                      >
                        <TrendingUp className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                        <span className="text-sm flex-1">{feature.title}</span>
                        <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === "list" && (
          <div className="rounded-lg border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-card/50">
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">
                    {t("roadmap.table.feature")}
                  </th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">
                    {t("roadmap.table.phase")}
                  </th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">
                    {t("roadmap.table.priority")}
                  </th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">
                    {t("roadmap.table.status")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedPhases.flatMap((phase) =>
                  featuresByPhase(phase.id).map((feature) => (
                    <tr
                      key={feature.id}
                      className="border-b border-border hover:bg-accent/50 cursor-pointer transition-colors"
                      onClick={() => setSelectedFeature(feature)}
                    >
                      <td className="px-4 py-2.5 font-medium">
                        {feature.title}
                      </td>
                      <td className="px-4 py-2.5 text-muted-foreground">
                        {phase.title}
                      </td>
                      <td className="px-4 py-2.5">
                        <span
                          className={cn(
                            "rounded-full px-2 py-0.5 text-[10px] font-medium",
                            feature.priority !== undefined &&
                              feature.priority <= 1 &&
                              "bg-red-500/10 text-red-600",
                            feature.priority !== undefined &&
                              feature.priority === 2 &&
                              "bg-yellow-500/10 text-yellow-600",
                            (feature.priority === undefined ||
                              feature.priority > 2) &&
                              "bg-blue-500/10 text-blue-600",
                          )}
                        >
                          {feature.priority !== undefined
                            ? feature.priority <= 1
                              ? "high"
                              : feature.priority <= 2
                                ? "medium"
                                : "low"
                            : "—"}
                        </span>
                      </td>
                      <td className="px-4 py-2.5">
                        <span
                          className={cn(
                            "rounded-full px-2 py-0.5 text-[10px] font-medium",
                            feature.status === "done" &&
                              "bg-green-500/10 text-green-600",
                            feature.status === "in_progress" &&
                              "bg-yellow-500/10 text-yellow-600",
                            feature.status === "planned" &&
                              "bg-secondary text-muted-foreground",
                            feature.status === "under_review" &&
                              "bg-purple-500/10 text-purple-600",
                          )}
                        >
                          {statusLabel(feature.status)}
                        </span>
                      </td>
                    </tr>
                  )),
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Feature Detail Panel */}
      {selectedFeature && (
        <FeatureDetailPanel
          feature={selectedFeature}
          onClose={() => setSelectedFeature(null)}
          onDelete={handleDeleteFeature}
        />
      )}
    </div>
  );
}
