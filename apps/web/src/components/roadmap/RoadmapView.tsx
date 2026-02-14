"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Map,
  Plus,
  RefreshCw,
  Sparkles,
  LayoutGrid,
  List,
  Calendar,
  Target,
  TrendingUp,
  ChevronRight,
} from "lucide-react";
import { cn } from "@auto-claude/ui";

interface RoadmapViewProps {
  projectId: string;
}

interface Feature {
  id: string;
  title: string;
  description: string;
  phase: string;
  priority: "high" | "medium" | "low";
  status: "planned" | "in_progress" | "completed";
  effort: string;
}

// Placeholder data for UI layout -- will be replaced with API data
const PLACEHOLDER_PHASES = [
  {
    nameKey: "roadmap.phases.phase1" as const,
    features: [
      { id: "1", title: "Core Authentication", description: "User login, registration, and session management", phase: "Phase 1", priority: "high" as const, status: "completed" as const, effort: "Large" },
      { id: "2", title: "Database Schema", description: "Initial database models and migrations", phase: "Phase 1", priority: "high" as const, status: "completed" as const, effort: "Medium" },
    ],
  },
  {
    nameKey: "roadmap.phases.phase2" as const,
    features: [
      { id: "3", title: "Task Management", description: "CRUD operations for tasks and subtasks", phase: "Phase 2", priority: "high" as const, status: "in_progress" as const, effort: "Large" },
      { id: "4", title: "Real-time Updates", description: "WebSocket integration for live updates", phase: "Phase 2", priority: "medium" as const, status: "planned" as const, effort: "Medium" },
    ],
  },
  {
    nameKey: "roadmap.phases.phase3" as const,
    features: [
      { id: "5", title: "GitHub Integration", description: "Issue sync and PR management", phase: "Phase 3", priority: "medium" as const, status: "planned" as const, effort: "Large" },
      { id: "6", title: "CI/CD Pipeline", description: "Automated deployment workflows", phase: "Phase 3", priority: "low" as const, status: "planned" as const, effort: "Small" },
    ],
  },
];

export function RoadmapView({ projectId }: RoadmapViewProps) {
  const { t } = useTranslation("views");
  const [activeTab, setActiveTab] = useState<"kanban" | "timeline" | "list">("kanban");
  const [selectedFeature, setSelectedFeature] = useState<Feature | null>(null);
  const [isEmpty] = useState(false);

  const statusLabel = (status: Feature["status"]) => {
    if (status === "in_progress") return t("roadmap.status.inProgress");
    if (status === "completed") return t("roadmap.status.completed");
    return t("roadmap.status.planned");
  };

  if (isEmpty) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8">
        <div className="max-w-md text-center">
          <div className="mb-6 flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
              <Map className="h-8 w-8 text-primary" />
            </div>
          </div>
          <h2 className="mb-3 text-xl font-semibold">{t("roadmap.empty.title")}</h2>
          <p className="mb-6 text-sm text-muted-foreground">
            {t("roadmap.empty.description")}
          </p>
          <button className="flex items-center gap-2 mx-auto rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors">
            <Sparkles className="h-4 w-4" />
            {t("roadmap.empty.generate")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold">{t("roadmap.title")}</h1>
          <div className="flex items-center rounded-lg border border-border bg-card/50">
            <button
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors rounded-l-lg",
                activeTab === "kanban" ? "bg-accent text-foreground" : "text-muted-foreground hover:text-foreground"
              )}
              onClick={() => setActiveTab("kanban")}
            >
              <LayoutGrid className="h-3 w-3" />
              {t("roadmap.tabs.board")}
            </button>
            <button
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors",
                activeTab === "timeline" ? "bg-accent text-foreground" : "text-muted-foreground hover:text-foreground"
              )}
              onClick={() => setActiveTab("timeline")}
            >
              <Calendar className="h-3 w-3" />
              {t("roadmap.tabs.timeline")}
            </button>
            <button
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors rounded-r-lg",
                activeTab === "list" ? "bg-accent text-foreground" : "text-muted-foreground hover:text-foreground"
              )}
              onClick={() => setActiveTab("list")}
            >
              <List className="h-3 w-3" />
              {t("roadmap.tabs.list")}
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors">
            <RefreshCw className="h-3.5 w-3.5" />
            {t("roadmap.refresh")}
          </button>
          <button className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 transition-colors">
            <Plus className="h-3.5 w-3.5" />
            {t("roadmap.addFeature")}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {activeTab === "kanban" && (
          <div className="space-y-8">
            {PLACEHOLDER_PHASES.map((phase) => (
              <div key={phase.nameKey}>
                <h2 className="text-sm font-semibold text-muted-foreground mb-3 flex items-center gap-2">
                  <Target className="h-4 w-4" />
                  {t(phase.nameKey)}
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {phase.features.map((feature) => (
                    <div
                      key={feature.id}
                      className="rounded-lg border border-border bg-card p-4 cursor-pointer hover:shadow-md transition-all"
                      onClick={() => setSelectedFeature(feature)}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="text-sm font-medium">{feature.title}</h3>
                        <span
                          className={cn(
                            "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium",
                            feature.status === "completed" && "bg-green-500/10 text-green-600",
                            feature.status === "in_progress" && "bg-yellow-500/10 text-yellow-600",
                            feature.status === "planned" && "bg-secondary text-muted-foreground"
                          )}
                        >
                          {statusLabel(feature.status)}
                        </span>
                      </div>
                      <p className="mt-1.5 text-xs text-muted-foreground line-clamp-2">
                        {feature.description}
                      </p>
                      <div className="mt-3 flex items-center gap-2">
                        <span
                          className={cn(
                            "rounded-full px-2 py-0.5 text-[10px] font-medium",
                            feature.priority === "high" && "bg-red-500/10 text-red-600",
                            feature.priority === "medium" && "bg-yellow-500/10 text-yellow-600",
                            feature.priority === "low" && "bg-blue-500/10 text-blue-600"
                          )}
                        >
                          {feature.priority}
                        </span>
                        <span className="text-[10px] text-muted-foreground">
                          {feature.effort}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === "timeline" && (
          <div className="space-y-4">
            {PLACEHOLDER_PHASES.map((phase, idx) => (
              <div key={phase.nameKey} className="flex gap-4">
                <div className="flex flex-col items-center">
                  <div className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold",
                    idx === 0 && "bg-green-500/10 text-green-600",
                    idx === 1 && "bg-yellow-500/10 text-yellow-600",
                    idx === 2 && "bg-blue-500/10 text-blue-600",
                  )}>
                    {idx + 1}
                  </div>
                  {idx < PLACEHOLDER_PHASES.length - 1 && (
                    <div className="flex-1 w-px bg-border my-2" />
                  )}
                </div>
                <div className="flex-1 pb-6">
                  <h3 className="text-sm font-semibold mb-2">{t(phase.nameKey)}</h3>
                  <div className="space-y-2">
                    {phase.features.map((feature) => (
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
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">{t("roadmap.table.feature")}</th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">{t("roadmap.table.phase")}</th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">{t("roadmap.table.priority")}</th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">{t("roadmap.table.status")}</th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">{t("roadmap.table.effort")}</th>
                </tr>
              </thead>
              <tbody>
                {PLACEHOLDER_PHASES.flatMap((phase) =>
                  phase.features.map((feature) => (
                    <tr
                      key={feature.id}
                      className="border-b border-border hover:bg-accent/50 cursor-pointer transition-colors"
                      onClick={() => setSelectedFeature(feature)}
                    >
                      <td className="px-4 py-2.5 font-medium">{feature.title}</td>
                      <td className="px-4 py-2.5 text-muted-foreground">{feature.phase}</td>
                      <td className="px-4 py-2.5">
                        <span className={cn(
                          "rounded-full px-2 py-0.5 text-[10px] font-medium",
                          feature.priority === "high" && "bg-red-500/10 text-red-600",
                          feature.priority === "medium" && "bg-yellow-500/10 text-yellow-600",
                          feature.priority === "low" && "bg-blue-500/10 text-blue-600"
                        )}>
                          {feature.priority}
                        </span>
                      </td>
                      <td className="px-4 py-2.5">
                        <span className={cn(
                          "rounded-full px-2 py-0.5 text-[10px] font-medium",
                          feature.status === "completed" && "bg-green-500/10 text-green-600",
                          feature.status === "in_progress" && "bg-yellow-500/10 text-yellow-600",
                          feature.status === "planned" && "bg-secondary text-muted-foreground"
                        )}>
                          {statusLabel(feature.status)}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-muted-foreground">{feature.effort}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Feature Detail Side Panel */}
      {selectedFeature && (
        <div className="fixed inset-y-0 right-0 z-50 w-96 border-l border-border bg-card shadow-xl">
          <div className="flex items-center justify-between border-b border-border p-4">
            <h2 className="text-sm font-semibold">{t("roadmap.detail.title")}</h2>
            <button
              className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-accent"
              onClick={() => setSelectedFeature(null)}
            >
              <span className="text-lg leading-none">&times;</span>
            </button>
          </div>
          <div className="p-4 space-y-4">
            <div>
              <h3 className="text-lg font-semibold">{selectedFeature.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{selectedFeature.description}</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-md border border-border p-3">
                <p className="text-xs text-muted-foreground">{t("roadmap.detail.priority")}</p>
                <p className="text-sm font-medium capitalize">{selectedFeature.priority}</p>
              </div>
              <div className="rounded-md border border-border p-3">
                <p className="text-xs text-muted-foreground">{t("roadmap.detail.effort")}</p>
                <p className="text-sm font-medium">{selectedFeature.effort}</p>
              </div>
              <div className="rounded-md border border-border p-3">
                <p className="text-xs text-muted-foreground">{t("roadmap.detail.phase")}</p>
                <p className="text-sm font-medium">{selectedFeature.phase}</p>
              </div>
              <div className="rounded-md border border-border p-3">
                <p className="text-xs text-muted-foreground">{t("roadmap.detail.status")}</p>
                <p className="text-sm font-medium capitalize">{selectedFeature.status.replace("_", " ")}</p>
              </div>
            </div>
            <button className="w-full rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 transition-colors">
              {t("roadmap.detail.convertToTask")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
