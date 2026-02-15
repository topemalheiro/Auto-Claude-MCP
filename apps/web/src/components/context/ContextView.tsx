"use client";

import { useState, useEffect, useCallback } from "react";
import {
  FolderTree,
  Brain,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useTranslation } from "react-i18next";
import { useContextStore } from "@/stores/context-store";
import { apiClient } from "@/lib/data/api-client";
import { ProjectIndexTab } from "./ProjectIndexTab";
import { MemoriesTab } from "./MemoriesTab";

interface ContextViewProps {
  projectId: string;
}

type TabId = "project-index" | "memories";

export function ContextView({ projectId }: ContextViewProps) {
  const { t } = useTranslation("integrations");
  const [activeTab, setActiveTab] = useState<TabId>("project-index");

  const {
    projectIndex,
    indexLoading,
    indexError,
    recentMemories,
    memoriesLoading,
    searchResults,
    searchLoading,
    searchQuery,
    setProjectIndex,
    setIndexLoading,
    setIndexError,
    setRecentMemories,
    setMemoriesLoading,
    setSearchResults,
    setSearchLoading,
    setSearchQuery,
  } = useContextStore();

  // Fetch project context on mount
  useEffect(() => {
    const fetchContext = async () => {
      setIndexLoading(true);
      setIndexError(null);
      try {
        const response = await apiClient.getProjectContext(projectId);
        if (response.context) {
          setProjectIndex(response.context as typeof projectIndex);
        }
      } catch (err) {
        setIndexError(err instanceof Error ? err.message : "Failed to load context");
      } finally {
        setIndexLoading(false);
      }
    };
    fetchContext();
  }, [projectId, setProjectIndex, setIndexLoading, setIndexError]);

  // Fetch memories on mount
  useEffect(() => {
    const fetchMemories = async () => {
      setMemoriesLoading(true);
      try {
        const response = await apiClient.getMemories(projectId);
        if (response.memories) {
          setRecentMemories(response.memories as typeof recentMemories);
        }
      } catch {
        // Memories are optional, don't show error
      } finally {
        setMemoriesLoading(false);
      }
    };
    fetchMemories();
  }, [projectId, setRecentMemories, setMemoriesLoading]);

  const handleRefreshIndex = useCallback(async () => {
    setIndexLoading(true);
    setIndexError(null);
    try {
      const response = await apiClient.refreshProjectIndex(projectId);
      if (response.index) {
        setProjectIndex(response.index as typeof projectIndex);
      }
    } catch (err) {
      setIndexError(err instanceof Error ? err.message : "Failed to refresh index");
    } finally {
      setIndexLoading(false);
    }
  }, [projectId, setProjectIndex, setIndexLoading, setIndexError]);

  const handleSearch = useCallback(
    async (query: string) => {
      setSearchQuery(query);
      if (!query.trim()) {
        setSearchResults([]);
        return;
      }
      setSearchLoading(true);
      try {
        const response = await apiClient.getMemories(projectId, query);
        if (response.memories) {
          setSearchResults(
            response.memories.map((m: unknown, i: number) => {
              const mem = m as { id?: string; content?: string; score?: number; type?: string };
              return {
                id: mem.id || String(i),
                content: mem.content || "",
                score: mem.score || 0,
                type: mem.type || "unknown",
              };
            }),
          );
        }
      } catch {
        // Search failure is non-critical
      } finally {
        setSearchLoading(false);
      }
    },
    [projectId, setSearchQuery, setSearchResults, setSearchLoading],
  );

  const tabs: { id: TabId; label: string; icon: React.ElementType }[] = [
    { id: "project-index", label: t("context.tabs.overview"), icon: FolderTree },
    { id: "memories", label: t("context.tabs.memories"), icon: Brain },
  ];

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold">{t("context.title")}</h1>
          <div className="flex items-center rounded-lg border border-border bg-card/50">
            {tabs.map((tab, i) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors",
                    i === 0 && "rounded-l-lg",
                    i === tabs.length - 1 && "rounded-r-lg",
                    activeTab === tab.id
                      ? "bg-accent text-foreground"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                  onClick={() => setActiveTab(tab.id)}
                >
                  <Icon className="h-3 w-3" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === "project-index" && (
          <ProjectIndexTab
            projectIndex={projectIndex}
            indexLoading={indexLoading}
            indexError={indexError}
            onRefresh={handleRefreshIndex}
          />
        )}

        {activeTab === "memories" && (
          <MemoriesTab
            memories={recentMemories}
            memoriesLoading={memoriesLoading}
            searchResults={searchResults}
            searchLoading={searchLoading}
            searchQuery={searchQuery}
            onSearch={handleSearch}
          />
        )}
      </div>
    </div>
  );
}
