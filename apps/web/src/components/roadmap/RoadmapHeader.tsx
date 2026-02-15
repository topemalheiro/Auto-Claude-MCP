"use client";

import { useTranslation } from "react-i18next";
import {
  LayoutGrid,
  List,
  Calendar,
  RefreshCw,
  Plus,
  Sparkles,
  Target,
} from "lucide-react";
import { cn } from "@auto-claude/ui";

type ViewMode = "kanban" | "timeline" | "list";

interface RoadmapHeaderProps {
  activeTab: ViewMode;
  onTabChange: (tab: ViewMode) => void;
  onRefresh: () => void;
  onAddFeature: () => void;
  onGenerate: () => void;
  featureCount: number;
  phaseCount: number;
}

export function RoadmapHeader({
  activeTab,
  onTabChange,
  onRefresh,
  onAddFeature,
  onGenerate,
  featureCount,
  phaseCount,
}: RoadmapHeaderProps) {
  const { t } = useTranslation("views");

  return (
    <div className="flex items-center justify-between border-b border-border px-6 py-3">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold">{t("roadmap.title")}</h1>
        <div className="flex items-center rounded-lg border border-border bg-card/50">
          <button
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors rounded-l-lg",
              activeTab === "kanban"
                ? "bg-accent text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
            onClick={() => onTabChange("kanban")}
          >
            <LayoutGrid className="h-3 w-3" />
            {t("roadmap.tabs.board")}
          </button>
          <button
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors",
              activeTab === "timeline"
                ? "bg-accent text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
            onClick={() => onTabChange("timeline")}
          >
            <Calendar className="h-3 w-3" />
            {t("roadmap.tabs.timeline")}
          </button>
          <button
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors rounded-r-lg",
              activeTab === "list"
                ? "bg-accent text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
            onClick={() => onTabChange("list")}
          >
            <List className="h-3 w-3" />
            {t("roadmap.tabs.list")}
          </button>
        </div>
        {featureCount > 0 && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Target className="h-3.5 w-3.5" />
            <span>
              {featureCount} {t("roadmap.features")} · {phaseCount}{" "}
              {t("roadmap.phases")}
            </span>
          </div>
        )}
      </div>
      <div className="flex items-center gap-2">
        <button
          className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
          onClick={onGenerate}
        >
          <Sparkles className="h-3.5 w-3.5" />
          {t("roadmap.generate")}
        </button>
        <button
          className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
          onClick={onRefresh}
        >
          <RefreshCw className="h-3.5 w-3.5" />
          {t("roadmap.refresh")}
        </button>
        <button
          className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 transition-colors"
          onClick={onAddFeature}
        >
          <Plus className="h-3.5 w-3.5" />
          {t("roadmap.addFeature")}
        </button>
      </div>
    </div>
  );
}
