"use client";

import { Brain, FileCode, GitPullRequest, Tag } from "lucide-react";
import { cn } from "@auto-claude/ui";
import type { MemoryEpisode } from "@/stores/context-store";

interface MemoryCardProps {
  memory: MemoryEpisode;
}

const CATEGORY_ICONS: Record<string, React.ElementType> = {
  code: FileCode,
  review: GitPullRequest,
  discovery: Brain,
};

const CATEGORY_COLORS: Record<string, string> = {
  code: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  review: "bg-purple-500/10 text-purple-600 dark:text-purple-400",
  discovery: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
};

export function MemoryCard({ memory }: MemoryCardProps) {
  const Icon = CATEGORY_ICONS[memory.type] || Brain;
  const colorClass = CATEGORY_COLORS[memory.type] || "bg-muted text-muted-foreground";

  return (
    <div className="rounded-lg border border-border bg-card p-4 hover:bg-accent/50 transition-colors">
      <div className="flex items-start gap-3">
        <div className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-md", colorClass)}>
          <Icon className="h-4 w-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-medium", colorClass)}>
              {memory.type}
            </span>
            <span className="text-[10px] text-muted-foreground">
              {new Date(memory.createdAt).toLocaleDateString()}
            </span>
          </div>
          <p className="text-sm text-foreground line-clamp-3">{memory.content}</p>
        </div>
      </div>
    </div>
  );
}
