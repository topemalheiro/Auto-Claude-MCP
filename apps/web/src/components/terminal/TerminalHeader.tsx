"use client";

import {
  X,
  Sparkles,
  TerminalSquare,
  GripVertical,
  Maximize2,
  Minimize2,
} from "lucide-react";
import type { SyntheticListenerMap } from "@dnd-kit/core/dist/hooks/utilities";
import type { Task } from "@auto-claude/types";
import { cn, Button } from "@auto-claude/ui";
import { TaskSelector } from "./TaskSelector";
import { WorktreeSelector, type WorktreeConfig } from "./WorktreeSelector";

const STATUS_COLORS: Record<string, string> = {
  idle: "bg-gray-400",
  running: "bg-green-500",
  "claude-active": "bg-purple-500 animate-pulse",
  exited: "bg-red-500",
};

interface TerminalHeaderProps {
  terminalId: string;
  title: string;
  status: string;
  isClaudeMode: boolean;
  tasks: Task[];
  associatedTask?: Task;
  onClose: () => void;
  onTitleChange: (newTitle: string) => void;
  onTaskSelect: (taskId: string) => void;
  onClearTask: () => void;
  onNewTaskClick?: () => void;
  terminalCount?: number;
  worktreeConfig?: WorktreeConfig;
  projectPath?: string;
  onCreateWorktree?: () => void;
  onSelectWorktree?: (config: WorktreeConfig) => void;
  dragHandleListeners?: SyntheticListenerMap;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
}

export function TerminalHeader({
  terminalId,
  title,
  status,
  isClaudeMode,
  tasks,
  associatedTask,
  onClose,
  onTitleChange,
  onTaskSelect,
  onClearTask,
  onNewTaskClick,
  terminalCount = 1,
  worktreeConfig,
  projectPath,
  onCreateWorktree,
  onSelectWorktree,
  dragHandleListeners,
  isExpanded,
  onToggleExpand,
}: TerminalHeaderProps) {
  const backlogTasks = tasks.filter((t) => t.status === "backlog");

  return (
    <div className="group/header flex h-9 items-center justify-between border-b border-border/50 bg-card/30 px-2">
      <div className="flex items-center gap-2">
        {/* Drag handle */}
        {dragHandleListeners && (
          <div
            {...dragHandleListeners}
            className={cn(
              "flex items-center justify-center",
              "w-4 h-6 -ml-1",
              "opacity-0 group-hover/header:opacity-60",
              "hover:opacity-100 transition-opacity",
              "cursor-grab active:cursor-grabbing",
              "text-muted-foreground hover:text-foreground",
            )}
          >
            <GripVertical className="h-3.5 w-3.5" />
          </div>
        )}

        <div className={cn("h-2 w-2 rounded-full", STATUS_COLORS[status] ?? "bg-gray-400")} />

        <div className="flex items-center gap-1.5">
          <TerminalSquare className="h-3.5 w-3.5 text-muted-foreground" />
          <span
            className="text-xs font-medium text-foreground truncate max-w-32 cursor-text"
            contentEditable
            suppressContentEditableWarning
            onBlur={(e) => {
              const newTitle = e.currentTarget.textContent?.trim();
              if (newTitle && newTitle !== title) {
                onTitleChange(newTitle);
              }
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                e.currentTarget.blur();
              }
            }}
          >
            {title}
          </span>
        </div>

        {isClaudeMode && (
          <span className="flex items-center gap-1 text-[10px] font-medium text-primary bg-primary/10 px-1.5 py-0.5 rounded">
            <Sparkles className="h-2.5 w-2.5" />
            {terminalCount < 4 && <span>Claude</span>}
          </span>
        )}

        {isClaudeMode && (
          <TaskSelector
            terminalId={terminalId}
            backlogTasks={backlogTasks}
            associatedTask={associatedTask}
            onTaskSelect={onTaskSelect}
            onClearTask={onClearTask}
            onNewTaskClick={onNewTaskClick}
          />
        )}

        {/* Worktree selector */}
        {projectPath && onCreateWorktree && onSelectWorktree && (
          <WorktreeSelector
            terminalId={terminalId}
            projectPath={projectPath}
            currentWorktree={worktreeConfig}
            onCreateWorktree={onCreateWorktree}
            onSelectWorktree={onSelectWorktree}
          />
        )}
      </div>

      <div className="flex items-center gap-1">
        {onToggleExpand && (
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 hover:bg-muted"
            onClick={(e) => {
              e.stopPropagation();
              onToggleExpand();
            }}
          >
            {isExpanded ? (
              <Minimize2 className="h-3 w-3" />
            ) : (
              <Maximize2 className="h-3 w-3" />
            )}
          </Button>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 hover:bg-destructive/20 hover:text-destructive"
          onClick={(e) => {
            e.stopPropagation();
            onClose();
          }}
        >
          <X className="h-3 w-3" />
        </Button>
      </div>
    </div>
  );
}
