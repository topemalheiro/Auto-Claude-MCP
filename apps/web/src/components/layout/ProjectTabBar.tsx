"use client";

import { X, Plus } from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useProjectStore } from "@/stores/project-store";
import { useTranslation } from "react-i18next";

export function ProjectTabBar() {
  const projects = useProjectStore((s) => s.projects);
  const openProjectIds = useProjectStore((s) => s.openProjectIds);
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const setActiveProject = useProjectStore((s) => s.setActiveProject);
  const closeProjectTab = useProjectStore((s) => s.closeProjectTab);
  const { t } = useTranslation("layout");

  const projectTabs = openProjectIds
    .map((id) => projects.find((p) => p.id === id))
    .filter(Boolean);

  if (projectTabs.length === 0) return null;

  return (
    <div className="flex items-center border-b border-border bg-card/50">
      <div className="flex flex-1 items-center overflow-x-auto">
        {projectTabs.map((project) => {
          if (!project) return null;
          const isActive = project.id === activeProjectId;

          return (
            <div
              key={project.id}
              className={cn(
                "group flex items-center gap-2 border-r border-border px-4 py-2 text-sm cursor-pointer transition-colors min-w-0",
                isActive
                  ? "bg-background text-foreground"
                  : "bg-card/50 text-muted-foreground hover:bg-accent/50"
              )}
              onClick={() => setActiveProject(project.id)}
            >
              <div className="w-1.5 h-4 rounded-full bg-muted-foreground/30 shrink-0" />
              <span className="truncate max-w-[150px]">{project.name}</span>
              <button
                className="opacity-0 group-hover:opacity-100 transition-opacity ml-1 hover:bg-accent rounded-sm p-0.5"
                onClick={(e) => {
                  e.stopPropagation();
                  closeProjectTab(project.id);
                }}
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          );
        })}
      </div>
      <button
        className="flex h-full items-center px-3 text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors"
        aria-label={t("projectTabBar.addProject")}
      >
        <Plus className="h-4 w-4" />
      </button>
    </div>
  );
}
