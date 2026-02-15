"use client";

import { FolderOpen, FolderPlus, Clock, ChevronRight, Folder, Sparkles } from "lucide-react";
import { useProjectStore } from "@/stores/project-store";
import { useUIStore } from "@/stores/ui-store";
import { useTranslation } from "react-i18next";

export function WelcomeScreen() {
  const { t } = useTranslation("layout");
  const projects = useProjectStore((s) => s.projects);
  const openProjectTab = useProjectStore((s) => s.openProjectTab);
  const setActiveView = useUIStore((s) => s.setActiveView);

  // Sort by most recent
  const recentProjects = [...projects]
    .sort(
      (a, b) =>
        new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    )
    .slice(0, 10);

  const formatRelativeTime = (date: string | Date) => {
    const now = new Date();
    const d = new Date(date);
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return t("welcome.time.justNow");
    if (diffMins < 60) return t("welcome.time.minutesAgo", { count: diffMins });
    if (diffHours < 24) return t("welcome.time.hoursAgo", { count: diffHours });
    if (diffDays < 7) return t("welcome.time.daysAgo", { count: diffDays });
    return d.toLocaleDateString();
  };

  const handleSelectProject = (projectId: string) => {
    openProjectTab(projectId);
    setActiveView("kanban");
  };

  const handleNewProject = () => {
    // For web, new project creation is handled via the settings/project management
    setActiveView("settings");
  };

  return (
    <div className="flex h-full items-center justify-center p-8">
      <div className="w-full max-w-2xl">
        {/* Hero Section */}
        <div className="mb-10 text-center">
          <div className="mb-6 flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
              <Sparkles className="h-8 w-8 text-primary" />
            </div>
          </div>
          <h1 className="text-3xl font-bold text-foreground tracking-tight">
            {t("welcome.title")}
          </h1>
          <p className="mt-3 text-muted-foreground">
            {t("welcome.description")}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="mb-10 flex gap-4 justify-center">
          <button
            onClick={handleNewProject}
            className="flex items-center gap-2 rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <FolderPlus className="h-5 w-5" />
            {t("welcome.newProject")}
          </button>
          <button
            onClick={handleNewProject}
            className="flex items-center gap-2 rounded-lg bg-secondary px-6 py-3 text-sm font-medium text-foreground hover:bg-secondary/80 transition-colors"
          >
            <FolderOpen className="h-5 w-5" />
            {t("welcome.connectProject")}
          </button>
        </div>

        {/* Recent Projects */}
        {recentProjects.length > 0 && (
          <div className="rounded-xl border border-border bg-card/50">
            <div className="p-4 pb-3">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Clock className="h-4 w-4" />
                {t("welcome.recentProjects")}
              </div>
            </div>
            <div className="border-t border-border" />
            <div className="max-h-[320px] overflow-y-auto p-2">
              {recentProjects.map((project) => (
                <button
                  key={project.id}
                  onClick={() => handleSelectProject(project.id)}
                  className="group flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left transition-colors hover:bg-accent/50"
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent/20 text-accent-foreground">
                    <Folder className="h-5 w-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <span className="block truncate font-medium text-foreground">
                      {project.name}
                    </span>
                    <span className="block truncate text-xs text-muted-foreground mt-0.5">
                      {project.path}
                    </span>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className="text-xs text-muted-foreground">
                      {formatRelativeTime(project.updatedAt)}
                    </span>
                    <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {projects.length === 0 && (
          <div className="rounded-xl border border-dashed border-border bg-card/30 p-8 text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-accent/20">
              <Folder className="h-6 w-6 text-accent-foreground" />
            </div>
            <h3 className="font-medium text-foreground mb-1">
              {t("welcome.noProjects")}
            </h3>
            <p className="text-sm text-muted-foreground">
              {t("welcome.subtext")}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
