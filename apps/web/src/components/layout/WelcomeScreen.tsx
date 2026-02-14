"use client";

import { Sparkles, ArrowRight } from "lucide-react";
import { useProjectStore } from "@/stores/project-store";
import { useUIStore } from "@/stores/ui-store";
import { useTranslation } from "react-i18next";

export function WelcomeScreen() {
  const { t } = useTranslation("layout");

  const connectDemoProject = () => {
    const demoProject = {
      id: "demo-project",
      name: "Auto Claude",
      path: "/demo",
      repoUrl: "https://github.com/AndyMik90/Auto-Claude",
      description: "Autonomous coding framework",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    useProjectStore.getState().setProjects([demoProject] as any);
    useProjectStore.getState().openProjectTab(demoProject.id);
    useUIStore.getState().setActiveView("kanban");
  };

  return (
    <div className="flex h-full flex-col items-center justify-center p-8">
      <div className="max-w-md text-center">
        <div className="mb-6 flex justify-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
            <Sparkles className="h-8 w-8 text-primary" />
          </div>
        </div>
        <h1 className="mb-3 text-2xl font-bold">{t("welcome.title")}</h1>
        <p className="mb-8 text-muted-foreground">
          {t("welcome.description")}
        </p>
        <div className="space-y-3">
          <button
            onClick={connectDemoProject}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            {t("welcome.connectProject")}
            <ArrowRight className="h-4 w-4" />
          </button>
          <p className="text-xs text-muted-foreground">
            {t("welcome.subtext")}
          </p>
        </div>
      </div>
    </div>
  );
}
