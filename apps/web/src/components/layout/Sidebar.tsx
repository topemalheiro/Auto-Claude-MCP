"use client";

import { useMemo } from "react";
import {
  Plus,
  Settings,
  LayoutGrid,
  Map,
  BookOpen,
  Lightbulb,
  Sparkles,
  FileText,
  Github,
  GitPullRequest,
  GitMerge,
  HelpCircle,
  PanelLeft,
  PanelLeftClose,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useSettingsStore, saveSettings } from "@/stores/settings-store";
import { useUIStore, type SidebarView } from "@/stores/ui-store";
import { useProjectStore } from "@/stores/project-store";
import { useTranslation } from "react-i18next";

interface NavItem {
  id: SidebarView;
  labelKey: string;
  icon: React.ElementType;
  shortcut?: string;
}

const baseNavItems: NavItem[] = [
  { id: "kanban", labelKey: "sidebar.nav.tasks", icon: LayoutGrid, shortcut: "K" },
  { id: "insights", labelKey: "sidebar.nav.insights", icon: Sparkles, shortcut: "N" },
  { id: "roadmap", labelKey: "sidebar.nav.roadmap", icon: Map, shortcut: "D" },
  { id: "ideation", labelKey: "sidebar.nav.ideation", icon: Lightbulb, shortcut: "I" },
  { id: "changelog", labelKey: "sidebar.nav.changelog", icon: FileText, shortcut: "L" },
  { id: "context", labelKey: "sidebar.nav.context", icon: BookOpen, shortcut: "C" },
];

const githubNavItems: NavItem[] = [
  { id: "github-issues", labelKey: "sidebar.nav.githubIssues", icon: Github, shortcut: "G" },
  { id: "github-prs", labelKey: "sidebar.nav.githubPrs", icon: GitPullRequest, shortcut: "P" },
];

const gitlabNavItems: NavItem[] = [
  { id: "gitlab-issues", labelKey: "sidebar.nav.gitlabIssues", icon: Github, shortcut: "B" },
  { id: "gitlab-merge-requests", labelKey: "sidebar.nav.gitlabMrs", icon: GitMerge, shortcut: "R" },
];

export function Sidebar() {
  const settings = useSettingsStore((s) => s.settings);
  const activeView = useUIStore((s) => s.activeView);
  const setActiveView = useUIStore((s) => s.setActiveView);
  const setNewTaskDialogOpen = useUIStore((s) => s.setNewTaskDialogOpen);
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const { t } = useTranslation("layout");

  const isCollapsed = settings.sidebarCollapsed ?? false;

  const toggleSidebar = () => {
    saveSettings({ sidebarCollapsed: !isCollapsed });
  };

  // Show GitHub and GitLab items by default (env config will drive this later)
  const visibleNavItems = useMemo(() => {
    return [...baseNavItems, ...githubNavItems, ...gitlabNavItems];
  }, []);

  const renderNavItem = (item: NavItem) => {
    const isActive = activeView === item.id;
    const Icon = item.icon;

    return (
      <button
        key={item.id}
        onClick={() => setActiveView(item.id)}
        disabled={!activeProjectId}
        className={cn(
          "flex w-full items-center rounded-lg text-sm transition-all duration-200",
          "hover:bg-accent hover:text-accent-foreground",
          "disabled:pointer-events-none disabled:opacity-50",
          isActive && "bg-accent text-accent-foreground",
          isCollapsed ? "justify-center px-2 py-2.5" : "gap-3 px-3 py-2.5"
        )}
      >
        <Icon className="h-4 w-4 shrink-0" />
        {!isCollapsed && (
          <>
            <span className="flex-1 text-left">{t(item.labelKey)}</span>
            {item.shortcut && (
              <kbd className="pointer-events-none hidden h-5 select-none items-center gap-1 rounded-md border border-border bg-secondary px-1.5 font-mono text-[10px] font-medium text-muted-foreground sm:flex">
                {item.shortcut}
              </kbd>
            )}
          </>
        )}
      </button>
    );
  };

  return (
    <div
      className={cn(
        "flex h-full flex-col bg-sidebar border-r border-border transition-all duration-300",
        isCollapsed ? "w-16" : "w-64"
      )}
    >
      {/* Header */}
      <div
        className={cn(
          "flex h-14 items-center transition-all duration-300",
          isCollapsed ? "justify-center px-2" : "px-4"
        )}
      >
        {!isCollapsed && (
          <span className="text-lg font-bold text-primary">{t("sidebar.brand")}</span>
        )}
        {isCollapsed && (
          <span className="text-lg font-bold text-primary">{t("sidebar.brandShort")}</span>
        )}
      </div>

      <div className="h-px bg-border" />

      {/* Toggle button */}
      <div
        className={cn(
          "flex py-2 transition-all duration-300",
          isCollapsed ? "justify-center px-2" : "justify-end px-3"
        )}
      >
        <button
          className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-accent"
          onClick={toggleSidebar}
          aria-label={isCollapsed ? t("sidebar.aria.expandSidebar") : t("sidebar.aria.collapseSidebar")}
        >
          {isCollapsed ? (
            <PanelLeft className="h-4 w-4" />
          ) : (
            <PanelLeftClose className="h-4 w-4" />
          )}
        </button>
      </div>

      <div className="h-px bg-border" />

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto">
        <div
          className={cn(
            "py-4 transition-all duration-300",
            isCollapsed ? "px-2" : "px-3"
          )}
        >
          {!isCollapsed && (
            <h3 className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {t("sidebar.sectionProject")}
            </h3>
          )}
          <nav className="space-y-1">{visibleNavItems.map(renderNavItem)}</nav>
        </div>
      </div>

      <div className="h-px bg-border" />

      {/* Bottom section */}
      <div
        className={cn(
          "space-y-3 transition-all duration-300",
          isCollapsed ? "p-2" : "p-4"
        )}
      >
        {/* Settings and Help row */}
        <div
          className={cn(
            "flex items-center",
            isCollapsed ? "flex-col gap-1" : "gap-2"
          )}
        >
          <button
            className={cn(
              "flex items-center rounded-md hover:bg-accent transition-colors",
              isCollapsed ? "h-8 w-8 justify-center" : "flex-1 gap-2 px-3 py-1.5 text-sm justify-start"
            )}
            onClick={() => setActiveView("settings")}
          >
            <Settings className="h-4 w-4" />
            {!isCollapsed && t("sidebar.actions.settings")}
          </button>
          <button
            className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-accent transition-colors"
            onClick={() =>
              window.open("https://github.com/AndyMik90/Auto-Claude/issues", "_blank")
            }
            aria-label={t("sidebar.aria.help")}
          >
            <HelpCircle className="h-4 w-4" />
          </button>
        </div>

        {/* New Task button */}
        <button
          className={cn(
            "w-full rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors flex items-center justify-center",
            isCollapsed ? "h-8 w-8 mx-auto" : "px-4 py-2 text-sm"
          )}
          onClick={() => setNewTaskDialogOpen(true)}
          disabled={!activeProjectId}
        >
          <Plus className={isCollapsed ? "h-4 w-4" : "mr-2 h-4 w-4"} />
          {!isCollapsed && t("sidebar.actions.newTask")}
        </button>
      </div>
    </div>
  );
}
