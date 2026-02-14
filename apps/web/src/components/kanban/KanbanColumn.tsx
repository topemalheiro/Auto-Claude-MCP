"use client";

import { useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useDroppable } from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import {
  ChevronLeft,
  ChevronRight,
  Inbox,
  Loader2,
  Eye,
  CheckCircle2,
  GitPullRequest,
  AlertCircle,
  Archive,
} from "lucide-react";
import {
  cn,
  Button,
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  ScrollArea,
} from "@auto-claude/ui";
import type { Task, TaskStatus } from "@auto-claude/types";
import { SortableTaskCard } from "./SortableTaskCard";
import {
  DEFAULT_COLUMN_WIDTH,
  COLLAPSED_COLUMN_WIDTH,
} from "@/stores/kanban-settings-store";

/** Column visual config */
const COLUMN_CONFIG: Record<
  string,
  { labelKey: string; icon: React.ElementType; color: string }
> = {
  backlog: { labelKey: "columns.backlog", icon: Inbox, color: "text-muted-foreground" },
  queue: { labelKey: "columns.queue", icon: Loader2, color: "text-blue-500" },
  in_progress: { labelKey: "columns.in_progress", icon: Loader2, color: "text-yellow-500" },
  ai_review: { labelKey: "columns.ai_review", icon: Eye, color: "text-purple-500" },
  human_review: { labelKey: "columns.human_review", icon: Eye, color: "text-orange-500" },
  done: { labelKey: "columns.done", icon: CheckCircle2, color: "text-green-500" },
  pr_created: { labelKey: "columns.pr_created", icon: GitPullRequest, color: "text-green-600" },
  error: { labelKey: "columns.error", icon: AlertCircle, color: "text-red-500" },
};

export interface KanbanColumnProps {
  status: TaskStatus;
  tasks: Task[];
  onTaskClick: (task: Task) => void;
  onStatusChange?: (taskId: string, newStatus: TaskStatus) => void;
  /** Whether this column is currently being dragged over */
  isOver?: boolean;
  /** Column width in pixels */
  columnWidth?: number;
  /** Whether the column is collapsed */
  isCollapsed?: boolean;
  /** Toggle collapsed state */
  onToggleCollapsed?: () => void;
  /** Show archived tasks toggle */
  showArchived?: boolean;
  /** Number of archived tasks in this column */
  archivedCount?: number;
  /** Toggle archive visibility */
  onToggleArchived?: () => void;
  /** Column resize start handler */
  onResizeStart?: (startX: number) => void;
}

export function KanbanColumn({
  status,
  tasks,
  onTaskClick,
  onStatusChange,
  isOver = false,
  columnWidth = DEFAULT_COLUMN_WIDTH,
  isCollapsed = false,
  onToggleCollapsed,
  showArchived = false,
  archivedCount = 0,
  onToggleArchived,
  onResizeStart,
}: KanbanColumnProps) {
  const { t } = useTranslation("kanban");
  const config = COLUMN_CONFIG[status] || COLUMN_CONFIG.backlog;
  const Icon = config.icon;

  const { setNodeRef, isOver: isDropOver } = useDroppable({
    id: status,
    data: { type: "column", status },
  });

  const handleResizeMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      onResizeStart?.(e.clientX);
    },
    [onResizeStart],
  );

  const taskIds = tasks.map((t) => t.id);
  const highlighted = isOver || isDropOver;

  // Collapsed column
  if (isCollapsed) {
    return (
      <div
        ref={setNodeRef}
        className={cn(
          "flex flex-col items-center rounded-lg border border-border bg-card/50 py-3 px-1 cursor-pointer transition-colors hover:bg-accent/50",
          highlighted && "border-primary/50 bg-primary/5",
        )}
        style={{ width: COLLAPSED_COLUMN_WIDTH, minWidth: COLLAPSED_COLUMN_WIDTH }}
        onClick={onToggleCollapsed}
      >
        <Icon className={cn("h-4 w-4 mb-2", config.color)} />
        <span className="text-xs font-medium text-muted-foreground [writing-mode:vertical-lr] rotate-180">
          {t(config.labelKey)}
        </span>
        <span className="mt-2 rounded-full bg-secondary px-1.5 py-0.5 text-[10px] text-muted-foreground">
          {tasks.length}
        </span>
      </div>
    );
  }

  return (
    <div
      ref={setNodeRef}
      className={cn(
        "flex flex-col rounded-lg bg-card/50 border border-border transition-colors relative",
        highlighted && "border-primary/50 bg-primary/5",
      )}
      style={{ width: columnWidth, minWidth: columnWidth, maxWidth: columnWidth }}
    >
      {/* Column header */}
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-border">
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              className="p-0.5 rounded hover:bg-accent transition-colors"
              onClick={onToggleCollapsed}
            >
              <ChevronLeft className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          </TooltipTrigger>
          <TooltipContent side="top">{t("board.collapseColumn", "Collapse")}</TooltipContent>
        </Tooltip>
        <Icon className={cn("h-4 w-4", config.color)} />
        <span className="text-sm font-medium truncate">{t(config.labelKey)}</span>
        <span className="ml-auto rounded-full bg-secondary px-2 py-0.5 text-xs text-muted-foreground">
          {tasks.length}
        </span>
        {/* Archive toggle for done column */}
        {archivedCount > 0 && (
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                className={cn(
                  "p-0.5 rounded hover:bg-accent transition-colors",
                  showArchived && "text-primary",
                )}
                onClick={onToggleArchived}
              >
                <Archive className="h-3.5 w-3.5" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="top">
              {showArchived
                ? t("board.hideArchived", "Hide archived ({{count}})", { count: archivedCount })
                : t("board.showArchived", "Show archived ({{count}})", { count: archivedCount })}
            </TooltipContent>
          </Tooltip>
        )}
      </div>

      {/* Task list */}
      <ScrollArea className="flex-1">
        <SortableContext items={taskIds} strategy={verticalListSortingStrategy}>
          <div className="p-2 space-y-2 min-h-[60px]">
            {tasks.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                <p className="text-xs">{t("board.noTasks")}</p>
              </div>
            ) : (
              tasks.map((task) => (
                <SortableTaskCard
                  key={task.id}
                  task={task}
                  onClick={() => onTaskClick(task)}
                  onStatusChange={onStatusChange}
                />
              ))
            )}
          </div>
        </SortableContext>
      </ScrollArea>

      {/* Resize handle */}
      {onResizeStart && (
        <div
          className="absolute top-0 right-0 w-1 h-full cursor-col-resize hover:bg-primary/30 transition-colors"
          onMouseDown={handleResizeMouseDown}
        />
      )}
    </div>
  );
}
