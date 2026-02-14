"use client";

import { useMemo, useState, useCallback, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragEndEvent,
  type DragOverEvent,
} from "@dnd-kit/core";
import { sortableKeyboardCoordinates } from "@dnd-kit/sortable";
import {
  Plus,
  Loader2,
  RefreshCw,
  Archive,
} from "lucide-react";
import { cn, Button, Tooltip, TooltipContent, TooltipTrigger } from "@auto-claude/ui";
import type { Task, TaskStatus } from "@auto-claude/types";
import { useTaskStore, loadTasks, updateTaskStatusAPI, startTask, stopTask } from "@/stores/task-store";
import { useProjectStore } from "@/stores/project-store";
import { useUIStore } from "@/stores/ui-store";
import {
  useKanbanSettingsStore,
  DEFAULT_COLUMN_WIDTH,
  MIN_COLUMN_WIDTH,
  MAX_COLUMN_WIDTH,
} from "@/stores/kanban-settings-store";
import { KanbanColumn } from "./KanbanColumn";
import { TaskCard } from "./TaskCard";
import { TaskDetailModal } from "./TaskDetailModal";

const TASK_STATUS_COLUMNS: TaskStatus[] = [
  "backlog",
  "queue",
  "in_progress",
  "ai_review",
  "human_review",
  "done",
];

/**
 * Get the visual column for a task status.
 * pr_created → done, error → human_review
 */
function getVisualColumn(status: TaskStatus): TaskStatus {
  if (status === "pr_created") return "done";
  if (status === "error") return "human_review";
  return status;
}

/** Valid drop transitions */
const VALID_TRANSITIONS: Record<TaskStatus, TaskStatus[]> = {
  backlog: ["queue"],
  queue: ["in_progress", "backlog"],
  in_progress: ["ai_review", "human_review", "error", "backlog"],
  ai_review: ["in_progress", "done", "human_review", "error"],
  human_review: ["in_progress", "done", "backlog"],
  done: ["backlog"],
  pr_created: ["done"],
  error: ["in_progress", "human_review", "backlog"],
};

export function KanbanBoard() {
  const { t } = useTranslation("kanban");
  const tasks = useTaskStore((s) => s.tasks);
  const isLoading = useTaskStore((s) => s.isLoading);
  const taskOrder = useTaskStore((s) => s.taskOrder);
  const reorderTasksInColumn = useTaskStore((s) => s.reorderTasksInColumn);
  const moveTaskToColumnTop = useTaskStore((s) => s.moveTaskToColumnTop);
  const saveTaskOrder = useTaskStore((s) => s.saveTaskOrder);
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const selectedProjectId = useProjectStore((s) => s.selectedProjectId);
  const setNewTaskDialogOpen = useUIStore((s) => s.setNewTaskDialogOpen);

  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);

  // Resize state
  const [resizingColumn, setResizingColumn] = useState<string | null>(null);
  const resizeStartX = useRef(0);
  const resizeStartWidth = useRef(DEFAULT_COLUMN_WIDTH);

  const currentProjectId = activeProjectId || selectedProjectId;

  // Kanban settings
  const columnPreferences = useKanbanSettingsStore((s) => s.columnPreferences);
  const setColumnWidth = useKanbanSettingsStore((s) => s.setColumnWidth);
  const toggleColumnCollapsed = useKanbanSettingsStore((s) => s.toggleColumnCollapsed);
  const initializePreferences = useKanbanSettingsStore((s) => s.initializePreferences);

  useEffect(() => {
    initializePreferences();
  }, [initializePreferences]);

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  // Group tasks by visual column
  const tasksByStatus = useMemo(() => {
    const grouped: Record<string, Task[]> = {};
    for (const status of TASK_STATUS_COLUMNS) {
      grouped[status] = [];
    }
    for (const task of tasks) {
      if (!showArchived && task.metadata?.archivedAt) continue;
      const displayStatus = getVisualColumn(task.status);
      if (grouped[displayStatus]) {
        grouped[displayStatus].push(task);
      }
    }
    return grouped;
  }, [tasks, showArchived]);

  // Count archived tasks
  const archivedCount = useMemo(
    () => tasks.filter((t) => t.metadata?.archivedAt).length,
    [tasks],
  );

  // Active drag task
  const activeTask = useMemo(
    () => (activeId ? tasks.find((t) => t.id === activeId) : null),
    [activeId, tasks],
  );

  const handleRefresh = useCallback(async () => {
    if (!currentProjectId) return;
    setIsRefreshing(true);
    try {
      await loadTasks(currentProjectId);
    } finally {
      setIsRefreshing(false);
    }
  }, [currentProjectId]);

  // Drag handlers
  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  }, []);

  const handleDragOver = useCallback((_event: DragOverEvent) => {
    // Could highlight target column - handled by isOver in KanbanColumn
  }, []);

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setActiveId(null);
      const { active, over } = event;
      if (!over || !currentProjectId) return;

      const activeTaskId = active.id as string;
      const task = tasks.find((t) => t.id === activeTaskId);
      if (!task) return;

      const overData = over.data.current;
      const overId = over.id as string;

      // Determine target column
      let targetColumn: TaskStatus | null = null;

      if (overData?.type === "column") {
        targetColumn = overData.status as TaskStatus;
      } else if (overData?.type === "task") {
        // Dropped on a task - find which column it's in
        const overTask = tasks.find((t) => t.id === overId);
        if (overTask) {
          targetColumn = getVisualColumn(overTask.status);
        }
      } else {
        // overId might be a column id directly
        if (TASK_STATUS_COLUMNS.includes(overId as TaskStatus)) {
          targetColumn = overId as TaskStatus;
        }
      }

      if (!targetColumn) return;

      const sourceColumn = getVisualColumn(task.status);

      if (sourceColumn === targetColumn) {
        // Reorder within column
        if (overData?.type === "task" && overId !== activeTaskId) {
          reorderTasksInColumn(targetColumn, activeTaskId, overId);
          saveTaskOrder(currentProjectId);
        }
      } else {
        // Move to different column - validate transition
        if (VALID_TRANSITIONS[task.status]?.includes(targetColumn)) {
          moveTaskToColumnTop(activeTaskId, targetColumn, sourceColumn);
          saveTaskOrder(currentProjectId);
          updateTaskStatusAPI(currentProjectId, activeTaskId, targetColumn);
        }
      }
    },
    [tasks, currentProjectId, reorderTasksInColumn, moveTaskToColumnTop, saveTaskOrder],
  );

  // Status change handler
  const handleStatusChange = useCallback(
    (taskId: string, newStatus: TaskStatus) => {
      if (!currentProjectId) return;
      updateTaskStatusAPI(currentProjectId, taskId, newStatus);
    },
    [currentProjectId],
  );

  const handleStartTask = useCallback(
    (taskId: string) => {
      if (!currentProjectId) return;
      startTask(currentProjectId, taskId);
    },
    [currentProjectId],
  );

  const handleStopTask = useCallback(
    (taskId: string) => {
      if (!currentProjectId) return;
      stopTask(currentProjectId, taskId);
    },
    [currentProjectId],
  );

  // Column resize handlers
  const handleResizeStart = useCallback(
    (column: string) => (startX: number) => {
      setResizingColumn(column);
      resizeStartX.current = startX;
      const pref = columnPreferences?.[column as keyof typeof columnPreferences];
      resizeStartWidth.current = pref?.width ?? DEFAULT_COLUMN_WIDTH;
    },
    [columnPreferences],
  );

  useEffect(() => {
    if (!resizingColumn) return;

    const handleMouseMove = (e: MouseEvent) => {
      const delta = e.clientX - resizeStartX.current;
      const newWidth = Math.max(
        MIN_COLUMN_WIDTH,
        Math.min(MAX_COLUMN_WIDTH, resizeStartWidth.current + delta),
      );
      setColumnWidth(resizingColumn as any, newWidth);
    };

    const handleMouseUp = () => {
      setResizingColumn(null);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [resizingColumn, setColumnWidth]);

  if (isLoading && tasks.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <h1 className="text-lg font-semibold">{t("board.title")}</h1>
        <div className="flex items-center gap-2">
          {archivedCount > 0 && (
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  className={cn(
                    "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors",
                    showArchived && "bg-accent text-foreground",
                  )}
                  onClick={() => setShowArchived(!showArchived)}
                >
                  <Archive className="h-3.5 w-3.5" />
                  {t("board.archived", "Archived")} ({archivedCount})
                </button>
              </TooltipTrigger>
              <TooltipContent>
                {showArchived
                  ? t("board.hideArchived", "Hide archived")
                  : t("board.showArchived", "Show archived")}
              </TooltipContent>
            </Tooltip>
          )}
          <button
            className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw
              className={cn("h-3.5 w-3.5", isRefreshing && "animate-spin")}
            />
            {t("board.refresh")}
          </button>
          <button
            className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 transition-colors"
            onClick={() => setNewTaskDialogOpen(true)}
          >
            <Plus className="h-3.5 w-3.5" />
            {t("board.newTask")}
          </button>
        </div>
      </div>

      {/* Columns with DnD */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
      >
        <div className="flex flex-1 overflow-x-auto p-4 gap-4">
          {TASK_STATUS_COLUMNS.map((status) => {
            const columnTasks = tasksByStatus[status] || [];
            const pref = columnPreferences?.[status as keyof typeof columnPreferences];

            return (
              <KanbanColumn
                key={status}
                status={status}
                tasks={columnTasks}
                onTaskClick={setSelectedTask}
                onStatusChange={handleStatusChange}
                isOver={false}
                columnWidth={pref?.width ?? DEFAULT_COLUMN_WIDTH}
                isCollapsed={pref?.isCollapsed ?? false}
                onToggleCollapsed={() => toggleColumnCollapsed(status as any)}
                showArchived={showArchived}
                archivedCount={status === "done" ? archivedCount : 0}
                onToggleArchived={() => setShowArchived(!showArchived)}
                onResizeStart={handleResizeStart(status)}
              />
            );
          })}
        </div>

        {/* Drag overlay */}
        <DragOverlay>
          {activeTask ? (
            <div className="w-[280px] opacity-90 rotate-2">
              <TaskCard
                task={activeTask}
                onClick={() => {}}
              />
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

      {/* Task Detail Modal */}
      {selectedTask && (
        <TaskDetailModal
          task={selectedTask}
          onClose={() => setSelectedTask(null)}
        />
      )}
    </div>
  );
}
