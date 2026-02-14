"use client";

import { useEffect } from "react";
import { Sidebar } from "./Sidebar";
import { ProjectTabBar } from "./ProjectTabBar";
import { useUIStore } from "@/stores/ui-store";
import { useProjectStore } from "@/stores/project-store";
import { useTaskStore } from "@/stores/task-store";
import { loadTasks } from "@/stores/task-store";
import { useSettingsStore } from "@/stores/settings-store";
import { KanbanBoard } from "@/components/kanban/KanbanBoard";
import { TaskCreationWizard } from "@/components/kanban/TaskCreationWizard";
import { RoadmapView } from "@/components/roadmap/RoadmapView";
import { IdeationView } from "@/components/ideation/IdeationView";
import { InsightsView } from "@/components/insights/InsightsView";
import { ChangelogView } from "@/components/changelog/ChangelogView";
import { ContextView } from "@/components/context/ContextView";
import { GitHubIssuesView } from "@/components/github/GitHubIssuesView";
import { GitHubPRsView } from "@/components/github/GitHubPRsView";
import { GitLabIssuesView } from "@/components/gitlab/GitLabIssuesView";
import { GitLabMRsView } from "@/components/gitlab/GitLabMRsView";
import { SettingsView } from "@/components/settings/SettingsView";
import { OnboardingWizard } from "@/components/onboarding/OnboardingWizard";
import { WelcomeScreen } from "./WelcomeScreen";

export function AppShell() {
  const activeView = useUIStore((s) => s.activeView);
  const isNewTaskDialogOpen = useUIStore((s) => s.isNewTaskDialogOpen);
  const setNewTaskDialogOpen = useUIStore((s) => s.setNewTaskDialogOpen);
  const isOnboardingOpen = useUIStore((s) => s.isOnboardingOpen);
  const setOnboardingOpen = useUIStore((s) => s.setOnboardingOpen);
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const selectedProjectId = useProjectStore((s) => s.selectedProjectId);
  const projects = useProjectStore((s) => s.projects);
  const settings = useSettingsStore((s) => s.settings);

  const currentProjectId = activeProjectId || selectedProjectId;
  const selectedProject = projects.find((p) => p.id === currentProjectId);

  // Load tasks when project changes
  useEffect(() => {
    if (currentProjectId) {
      loadTasks(currentProjectId);
    } else {
      useTaskStore.getState().clearTasks();
    }
  }, [currentProjectId]);

  // Apply theme from settings
  useEffect(() => {
    const root = document.documentElement;
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)");

    const applyTheme = () => {
      if (settings.theme === "dark") {
        root.classList.add("dark");
      } else if (settings.theme === "light") {
        root.classList.remove("dark");
      } else {
        // System preference
        if (prefersDark.matches) {
          root.classList.add("dark");
        } else {
          root.classList.remove("dark");
        }
      }
    };

    applyTheme();
    prefersDark.addEventListener("change", applyTheme);
    return () => prefersDark.removeEventListener("change", applyTheme);
  }, [settings.theme]);

  // Keyboard shortcuts for navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in inputs
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        (e.target as HTMLElement)?.isContentEditable
      ) {
        return;
      }

      if (!currentProjectId) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const key = e.key.toUpperCase();
      const viewMap: Record<string, typeof activeView> = {
        K: "kanban",
        N: "insights",
        D: "roadmap",
        I: "ideation",
        L: "changelog",
        C: "context",
        G: "github-issues",
        P: "github-prs",
        B: "gitlab-issues",
        R: "gitlab-merge-requests",
      };

      if (viewMap[key]) {
        e.preventDefault();
        useUIStore.getState().setActiveView(viewMap[key]);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentProjectId]);

  const renderContent = () => {
    if (!selectedProject) {
      return <WelcomeScreen />;
    }

    switch (activeView) {
      case "kanban":
        return <KanbanBoard />;
      case "roadmap":
        return <RoadmapView projectId={currentProjectId!} />;
      case "ideation":
        return <IdeationView projectId={currentProjectId!} />;
      case "insights":
        return <InsightsView projectId={currentProjectId!} />;
      case "changelog":
        return <ChangelogView projectId={currentProjectId!} />;
      case "context":
        return <ContextView projectId={currentProjectId!} />;
      case "github-issues":
        return <GitHubIssuesView projectId={currentProjectId!} />;
      case "github-prs":
        return <GitHubPRsView projectId={currentProjectId!} />;
      case "gitlab-issues":
        return <GitLabIssuesView projectId={currentProjectId!} />;
      case "gitlab-merge-requests":
        return <GitLabMRsView projectId={currentProjectId!} />;
      case "settings":
        return <SettingsView />;
      default:
        return <KanbanBoard />;
    }
  };

  return (
    <div className="flex h-screen bg-background text-foreground">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Project Tabs */}
        <ProjectTabBar />

        {/* Main content area */}
        <main className="flex-1 overflow-hidden">{renderContent()}</main>
      </div>

      {/* Task Creation Wizard */}
      {currentProjectId && (
        <TaskCreationWizard
          open={isNewTaskDialogOpen}
          onClose={() => setNewTaskDialogOpen(false)}
          projectId={currentProjectId}
        />
      )}

      {/* Onboarding Wizard */}
      <OnboardingWizard
        open={isOnboardingOpen}
        onClose={() => setOnboardingOpen(false)}
      />
    </div>
  );
}
