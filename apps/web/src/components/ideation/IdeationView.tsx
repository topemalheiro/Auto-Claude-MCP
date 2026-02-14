"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Lightbulb,
  Sparkles,
  RefreshCw,
  Shield,
  Zap,
  Code,
  Paintbrush,
  Bug,
  ArrowRight,
  ThumbsUp,
  ThumbsDown,
} from "lucide-react";
import { cn } from "@auto-claude/ui";

interface IdeationViewProps {
  projectId: string;
}

type IdeaCategory =
  | "code_improvements"
  | "security_hardening"
  | "performance_optimization"
  | "ui_ux_improvements"
  | "bug_predictions"
  | "new_features";

const CATEGORY_ICONS: Record<IdeaCategory, React.ElementType> = {
  code_improvements: Code,
  security_hardening: Shield,
  performance_optimization: Zap,
  ui_ux_improvements: Paintbrush,
  bug_predictions: Bug,
  new_features: Sparkles,
};

const CATEGORY_KEYS: Record<IdeaCategory, string> = {
  code_improvements: "ideation.categories.codeImprovements",
  security_hardening: "ideation.categories.securityHardening",
  performance_optimization: "ideation.categories.performanceOptimization",
  ui_ux_improvements: "ideation.categories.uiUxImprovements",
  bug_predictions: "ideation.categories.bugPredictions",
  new_features: "ideation.categories.newFeatures",
};

const CATEGORY_IDS: IdeaCategory[] = [
  "code_improvements",
  "security_hardening",
  "performance_optimization",
  "ui_ux_improvements",
  "bug_predictions",
  "new_features",
];

interface Idea {
  id: string;
  title: string;
  description: string;
  category: IdeaCategory;
  impact: "low" | "medium" | "high";
  effort: "small" | "medium" | "large";
}

const PLACEHOLDER_IDEAS: Idea[] = [
  { id: "1", title: "Add input validation to user forms", description: "Several user-facing forms lack proper input validation which could lead to data integrity issues.", category: "code_improvements", impact: "high", effort: "small" },
  { id: "2", title: "Rate limit API endpoints", description: "Public API endpoints should have rate limiting to prevent abuse and ensure fair usage.", category: "security_hardening", impact: "high", effort: "medium" },
  { id: "3", title: "Optimize database queries on dashboard", description: "The dashboard page makes N+1 queries that could be batched for better performance.", category: "performance_optimization", impact: "medium", effort: "small" },
  { id: "4", title: "Add loading skeletons", description: "Replace loading spinners with skeleton loaders for a smoother perceived loading experience.", category: "ui_ux_improvements", impact: "medium", effort: "small" },
];

export function IdeationView({ projectId }: IdeationViewProps) {
  const { t } = useTranslation("views");
  const [selectedCategory, setSelectedCategory] = useState<IdeaCategory | null>(null);
  const [ideas] = useState<Idea[]>(PLACEHOLDER_IDEAS);
  const [isEmpty] = useState(false);

  const filteredIdeas = selectedCategory
    ? ideas.filter((i) => i.category === selectedCategory)
    : ideas;

  if (isEmpty) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8">
        <div className="max-w-md text-center">
          <div className="mb-6 flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
              <Lightbulb className="h-8 w-8 text-primary" />
            </div>
          </div>
          <h2 className="mb-3 text-xl font-semibold">{t("ideation.empty.title")}</h2>
          <p className="mb-6 text-sm text-muted-foreground">
            {t("ideation.empty.description")}
          </p>
          <button className="flex items-center gap-2 mx-auto rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors">
            <Sparkles className="h-4 w-4" />
            {t("ideation.empty.generate")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <h1 className="text-lg font-semibold">{t("ideation.title")}</h1>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors">
            <RefreshCw className="h-3.5 w-3.5" />
            {t("ideation.regenerate")}
          </button>
          <button className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 transition-colors">
            <Sparkles className="h-3.5 w-3.5" />
            {t("ideation.analyzeCodebase")}
          </button>
        </div>
      </div>

      {/* Category filters */}
      <div className="border-b border-border px-6 py-3">
        <div className="flex items-center gap-2 overflow-x-auto">
          <button
            className={cn(
              "shrink-0 rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
              !selectedCategory ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"
            )}
            onClick={() => setSelectedCategory(null)}
          >
            {t("ideation.allFilter", { count: ideas.length })}
          </button>
          {CATEGORY_IDS.map((catId) => {
            const Icon = CATEGORY_ICONS[catId];
            const count = ideas.filter((i) => i.category === catId).length;
            return (
              <button
                key={catId}
                className={cn(
                  "shrink-0 flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
                  selectedCategory === catId ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"
                )}
                onClick={() => setSelectedCategory(catId)}
              >
                <Icon className="h-3 w-3" />
                {t("ideation.categoryCount", { label: t(`${CATEGORY_KEYS[catId]}.label`), count })}
              </button>
            );
          })}
        </div>
      </div>

      {/* Ideas list */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="space-y-3 max-w-3xl">
          {filteredIdeas.map((idea) => {
            const Icon = CATEGORY_ICONS[idea.category] || Lightbulb;

            return (
              <div
                key={idea.id}
                className="rounded-lg border border-border bg-card p-4 hover:shadow-md transition-all"
              >
                <div className="flex items-start gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary shrink-0">
                    <Icon className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-medium">{idea.title}</h3>
                    <p className="mt-1 text-xs text-muted-foreground">{idea.description}</p>
                    <div className="mt-3 flex items-center gap-2 flex-wrap">
                      <span className={cn(
                        "rounded-full px-2 py-0.5 text-[10px] font-medium",
                        idea.impact === "high" && "bg-red-500/10 text-red-600",
                        idea.impact === "medium" && "bg-yellow-500/10 text-yellow-600",
                        idea.impact === "low" && "bg-blue-500/10 text-blue-600"
                      )}>
                        {t("ideation.impact", { level: idea.impact })}
                      </span>
                      <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                        {t("ideation.effort", { level: idea.effort })}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-accent transition-colors text-muted-foreground hover:text-green-500">
                      <ThumbsUp className="h-3.5 w-3.5" />
                    </button>
                    <button className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-accent transition-colors text-muted-foreground hover:text-red-500">
                      <ThumbsDown className="h-3.5 w-3.5" />
                    </button>
                    <button className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-accent transition-colors text-muted-foreground hover:text-primary">
                      <ArrowRight className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
