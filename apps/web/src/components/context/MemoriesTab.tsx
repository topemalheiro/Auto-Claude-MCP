"use client";

import { useState, useCallback } from "react";
import { Search, Brain, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { MemoryEpisode, ContextSearchResult } from "@/stores/context-store";
import { MemoryCard } from "./MemoryCard";

interface MemoriesTabProps {
  memories: MemoryEpisode[];
  memoriesLoading: boolean;
  searchResults: ContextSearchResult[];
  searchLoading: boolean;
  searchQuery: string;
  onSearch: (query: string) => void;
}

export function MemoriesTab({
  memories,
  memoriesLoading,
  searchResults,
  searchLoading,
  searchQuery,
  onSearch,
}: MemoriesTabProps) {
  const { t } = useTranslation("integrations");
  const [localQuery, setLocalQuery] = useState(searchQuery);

  const handleSearch = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      onSearch(localQuery);
    },
    [localQuery, onSearch],
  );

  const displayItems = searchQuery
    ? searchResults.map((r) => ({
        id: r.id,
        content: r.content,
        type: r.type,
        createdAt: new Date(),
      }))
    : memories;

  const isLoading = memoriesLoading || searchLoading;

  return (
    <div className="max-w-3xl mx-auto">
      {/* Search */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            className="w-full rounded-lg border border-border bg-background pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
            placeholder={t("context.search.memories")}
            value={localQuery}
            onChange={(e) => setLocalQuery(e.target.value)}
          />
          {searchLoading && (
            <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
          )}
        </div>
      </form>

      {/* Loading state */}
      {isLoading && displayItems.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Memory list */}
      {displayItems.length > 0 && (
        <div className="space-y-3">
          {displayItems.map((memory) => (
            <MemoryCard key={memory.id} memory={memory} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && displayItems.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <Brain className="h-12 w-12 text-muted-foreground/50 mb-4" />
          <h3 className="text-sm font-semibold mb-1">
            {searchQuery
              ? t("context.empty.noResults", { defaultValue: "No results found" })
              : t("context.empty.noMemories")}
          </h3>
          <p className="text-xs text-muted-foreground max-w-sm">
            {searchQuery
              ? t("context.empty.noResultsDescription", { defaultValue: "Try a different search query." })
              : t("context.empty.noMemoriesDescription")}
          </p>
        </div>
      )}
    </div>
  );
}
