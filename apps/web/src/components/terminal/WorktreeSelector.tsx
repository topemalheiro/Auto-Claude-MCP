"use client";

import { FolderGit, Plus } from "lucide-react";
import { cn, Button, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from "@auto-claude/ui";

export interface WorktreeConfig {
  name: string;
  path: string;
  branch: string;
}

interface WorktreeSelectorProps {
  terminalId: string;
  projectPath: string;
  currentWorktree?: WorktreeConfig;
  worktrees?: WorktreeConfig[];
  onCreateWorktree: () => void;
  onSelectWorktree: (config: WorktreeConfig) => void;
}

export function WorktreeSelector({
  currentWorktree,
  worktrees = [],
  onCreateWorktree,
  onSelectWorktree,
}: WorktreeSelectorProps) {
  if (currentWorktree) {
    return (
      <span
        className="flex items-center gap-1 text-[10px] font-medium text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded max-w-40"
        title={currentWorktree.name}
      >
        <FolderGit className="h-2.5 w-2.5 flex-shrink-0" />
        <span className="truncate">{currentWorktree.name}</span>
      </span>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="h-5 px-1.5 text-[10px] text-muted-foreground hover:text-foreground"
        >
          <FolderGit className="h-3 w-3" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        {worktrees.length === 0 ? (
          <DropdownMenuItem disabled>No worktrees</DropdownMenuItem>
        ) : (
          worktrees.map((wt) => (
            <DropdownMenuItem
              key={wt.path}
              onClick={() => onSelectWorktree(wt)}
            >
              <FolderGit className="h-3.5 w-3.5 mr-2 flex-shrink-0" />
              <span className="truncate">{wt.name}</span>
            </DropdownMenuItem>
          ))
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onCreateWorktree}>
          <Plus className="h-3.5 w-3.5 mr-2" />
          Create worktree
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
