import { create } from "zustand";
import type { Task } from "@auto-claude/types";

/**
 * Sidebar view types matching the Electron app's navigation.
 * Excludes Electron-specific views: terminals, worktrees, agent-tools.
 */
export type SidebarView =
  | "kanban"
  | "roadmap"
  | "context"
  | "ideation"
  | "insights"
  | "github-issues"
  | "github-prs"
  | "gitlab-issues"
  | "gitlab-merge-requests"
  | "changelog"
  | "settings";

interface UIState {
  activeView: SidebarView;
  selectedTask: Task | null;
  isNewTaskDialogOpen: boolean;
  isSettingsDialogOpen: boolean;
  isOnboardingOpen: boolean;

  // Actions
  setActiveView: (view: SidebarView) => void;
  setSelectedTask: (task: Task | null) => void;
  setNewTaskDialogOpen: (open: boolean) => void;
  setSettingsDialogOpen: (open: boolean) => void;
  setOnboardingOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  activeView: "kanban",
  selectedTask: null,
  isNewTaskDialogOpen: false,
  isSettingsDialogOpen: false,
  isOnboardingOpen: false,

  setActiveView: (view) => set({ activeView: view }),
  setSelectedTask: (task) => set({ selectedTask: task }),
  setNewTaskDialogOpen: (open) => set({ isNewTaskDialogOpen: open }),
  setSettingsDialogOpen: (open) => set({ isSettingsDialogOpen: open }),
  setOnboardingOpen: (open) => set({ isOnboardingOpen: open }),
}));
