import { useState, useMemo, useEffect, useCallback, useRef, memo } from 'react';
import { useTranslation } from 'react-i18next';
import { useViewState } from '../contexts/ViewStateContext';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
  type DragStartEvent,
  type DragEndEvent,
  type DragOverEvent
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy
} from '@dnd-kit/sortable';
import { Plus, Inbox, Loader2, Eye, CheckCircle2, Archive, RefreshCw, GitPullRequest, X, Settings, ListPlus, ChevronLeft, ChevronRight, ChevronsRight, Lock, Unlock, Trash2, Zap, ShieldOff, Shield } from 'lucide-react';
import { Checkbox } from './ui/checkbox';
import { ScrollArea } from './ui/scroll-area';
import { Button } from './ui/button';
import { Switch } from './ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Tooltip, TooltipContent, TooltipTrigger } from './ui/tooltip';
import { TaskCard } from './TaskCard';
import { SortableTaskCard } from './SortableTaskCard';
import { QueueSettingsModal } from './QueueSettingsModal';
import { TASK_STATUS_COLUMNS, TASK_STATUS_LABELS } from '../../shared/constants';
import { debugLog } from '../../shared/utils/debug-logger';
import { cn } from '../lib/utils';
import { persistTaskStatus, forceCompleteTask, archiveTasks, deleteTasks, useTaskStore, isQueueAtCapacity, DEFAULT_MAX_PARALLEL_TASKS, startTask, isIncompleteHumanReview } from '../stores/task-store';
import { updateProjectSettings, useProjectStore } from '../stores/project-store';
import { useKanbanSettingsStore, DEFAULT_COLUMN_WIDTH, MIN_COLUMN_WIDTH, MAX_COLUMN_WIDTH, COLLAPSED_COLUMN_WIDTH_REM, MIN_COLUMN_WIDTH_REM, MAX_COLUMN_WIDTH_REM, BASE_FONT_SIZE, pxToRem } from '../stores/kanban-settings-store';
import { useToast } from '../hooks/use-toast';
import { WorktreeCleanupDialog } from './WorktreeCleanupDialog';
import { BulkPRDialog } from './BulkPRDialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from './ui/alert-dialog';
import type { Task, TaskStatus, TaskOrderState } from '../../shared/types';

// Type guard for valid drop column targets - preserves literal type from TASK_STATUS_COLUMNS
const VALID_DROP_COLUMNS = new Set<string>(TASK_STATUS_COLUMNS);
function isValidDropColumn(id: string): id is typeof TASK_STATUS_COLUMNS[number] {
  return VALID_DROP_COLUMNS.has(id);
}

/**
 * Get the visual column for a task status.
 * pr_created tasks are displayed in the 'done' column, so we map them accordingly.
 * error tasks are displayed in the 'human_review' column (errors need human attention).
 * This is used to compare visual positions during drag-and-drop operations.
 */
function getVisualColumn(status: TaskStatus): typeof TASK_STATUS_COLUMNS[number] {
  if (status === 'pr_created') return 'done';
  if (status === 'error') return 'human_review';
  return status;
}

interface KanbanBoardProps {
  tasks: Task[];
  onTaskClick: (task: Task) => void;
  onNewTaskClick?: () => void;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

interface DroppableColumnProps {
  status: TaskStatus;
  tasks: Task[];
  onTaskClick: (task: Task) => void;
  onStatusChange: (taskId: string, newStatus: TaskStatus) => unknown;
  onRefresh?: () => void;
  isOver: boolean;
  onAddClick?: () => void;
  onArchiveAll?: () => void;
  onQueueSettings?: () => void;
  onQueueAll?: () => void;
  maxParallelTasks?: number;
  archivedCount?: number;
  showArchived?: boolean;
  onToggleArchived?: () => void;
  // Selection props for human_review column
  selectedTaskIds?: Set<string>;
  onSelectAll?: () => void;
  onDeselectAll?: () => void;
  onToggleSelect?: (taskId: string) => void;
  // Collapse props
  isCollapsed?: boolean;
  onToggleCollapsed?: () => void;
  // Resize props
  columnWidth?: number;
  isResizing?: boolean;
  onResizeStart?: (startX: number) => void;
  onResizeEnd?: () => void;
  // Lock props
  isLocked?: boolean;
  onToggleLocked?: () => void;
  // Whether the global RDR toggle is enabled (per-project setting)
  rdrEnabled?: boolean;
  // Queue blocking props (RDR-driven)
  queueBlocked?: boolean;
  queueBlockReason?: string | null;
}

/**
 * Compare two tasks arrays for meaningful changes.
 * Returns true if tasks are equivalent (should skip re-render).
 */
function tasksAreEquivalent(prevTasks: Task[], nextTasks: Task[]): boolean {
  if (prevTasks.length !== nextTasks.length) return false;
  if (prevTasks === nextTasks) return true;

  // Compare by ID and fields that affect rendering
  for (let i = 0; i < prevTasks.length; i++) {
    const prev = prevTasks[i];
    const next = nextTasks[i];
    if (
      prev.id !== next.id ||
      prev.status !== next.status ||
      prev.executionProgress?.phase !== next.executionProgress?.phase ||
      prev.updatedAt !== next.updatedAt
    ) {
      return false;
    }
  }
  return true;
}

/**
 * Custom comparator for DroppableColumn memo.
 */
function droppableColumnPropsAreEqual(
  prevProps: DroppableColumnProps,
  nextProps: DroppableColumnProps
): boolean {
  // Quick checks first
  if (prevProps.status !== nextProps.status) return false;
  if (prevProps.isOver !== nextProps.isOver) return false;
  if (prevProps.onTaskClick !== nextProps.onTaskClick) return false;
  if (prevProps.onStatusChange !== nextProps.onStatusChange) return false;
  if (prevProps.onRefresh !== nextProps.onRefresh) return false;
  if (prevProps.onAddClick !== nextProps.onAddClick) return false;
  if (prevProps.onArchiveAll !== nextProps.onArchiveAll) return false;
  if (prevProps.onQueueSettings !== nextProps.onQueueSettings) return false;
  if (prevProps.onQueueAll !== nextProps.onQueueAll) return false;
  if (prevProps.maxParallelTasks !== nextProps.maxParallelTasks) return false;
  if (prevProps.archivedCount !== nextProps.archivedCount) return false;
  if (prevProps.showArchived !== nextProps.showArchived) return false;
  if (prevProps.onToggleArchived !== nextProps.onToggleArchived) return false;
  if (prevProps.onSelectAll !== nextProps.onSelectAll) return false;
  if (prevProps.onDeselectAll !== nextProps.onDeselectAll) return false;
  if (prevProps.onToggleSelect !== nextProps.onToggleSelect) return false;
  if (prevProps.isCollapsed !== nextProps.isCollapsed) return false;
  if (prevProps.onToggleCollapsed !== nextProps.onToggleCollapsed) return false;
  if (prevProps.columnWidth !== nextProps.columnWidth) return false;
  if (prevProps.isResizing !== nextProps.isResizing) return false;
  if (prevProps.onResizeStart !== nextProps.onResizeStart) return false;
  if (prevProps.onResizeEnd !== nextProps.onResizeEnd) return false;
  if (prevProps.isLocked !== nextProps.isLocked) return false;
  if (prevProps.onToggleLocked !== nextProps.onToggleLocked) return false;
  if (prevProps.rdrEnabled !== nextProps.rdrEnabled) return false;
  if (prevProps.queueBlocked !== nextProps.queueBlocked) return false;
  if (prevProps.queueBlockReason !== nextProps.queueBlockReason) return false;

  // Compare selection props
  const prevSelected = prevProps.selectedTaskIds;
  const nextSelected = nextProps.selectedTaskIds;
  if (prevSelected !== nextSelected) {
    if (!prevSelected || !nextSelected) return false;
    if (prevSelected.size !== nextSelected.size) return false;
    for (const id of prevSelected) {
      if (!nextSelected.has(id)) return false;
    }
  }

  // Deep compare tasks
  const tasksEqual = tasksAreEquivalent(prevProps.tasks, nextProps.tasks);

  // Only log when re-rendering (reduces noise)
  if (window.DEBUG && !tasksEqual) {
    console.log(`[DroppableColumn] Re-render: ${nextProps.status} column (${nextProps.tasks.length} tasks)`);
  }

  return tasksEqual;
}

// Empty state content for each column
const getEmptyStateContent = (status: TaskStatus, t: (key: string) => string): { icon: React.ReactNode; message: string; subtext?: string } => {
  switch (status) {
    case 'backlog':
      return {
        icon: <Inbox className="h-6 w-6 text-muted-foreground/50" />,
        message: t('kanban.emptyBacklog'),
        subtext: t('kanban.emptyBacklogHint')
      };
    case 'queue':
      return {
        icon: <Loader2 className="h-6 w-6 text-muted-foreground/50" />,
        message: t('kanban.emptyQueue'),
        subtext: t('kanban.emptyQueueHint')
      };
    case 'in_progress':
      return {
        icon: <Loader2 className="h-6 w-6 text-muted-foreground/50" />,
        message: t('kanban.emptyInProgress'),
        subtext: t('kanban.emptyInProgressHint')
      };
    case 'ai_review':
      return {
        icon: <Eye className="h-6 w-6 text-muted-foreground/50" />,
        message: t('kanban.emptyAiReview'),
        subtext: t('kanban.emptyAiReviewHint')
      };
    case 'human_review':
      return {
        icon: <Eye className="h-6 w-6 text-muted-foreground/50" />,
        message: t('kanban.emptyHumanReview'),
        subtext: t('kanban.emptyHumanReviewHint')
      };
    case 'done':
      return {
        icon: <CheckCircle2 className="h-6 w-6 text-muted-foreground/50" />,
        message: t('kanban.emptyDone'),
        subtext: t('kanban.emptyDoneHint')
      };
    default:
      return {
        icon: <Inbox className="h-6 w-6 text-muted-foreground/50" />,
        message: t('kanban.emptyDefault')
      };
  }
};

const DroppableColumn = memo(function DroppableColumn({ status, tasks, onTaskClick, onStatusChange, onRefresh, isOver, onAddClick, onArchiveAll, onQueueSettings, onQueueAll, maxParallelTasks, archivedCount, showArchived, onToggleArchived, selectedTaskIds, onSelectAll, onDeselectAll, onToggleSelect, isCollapsed, onToggleCollapsed, columnWidth, isResizing, onResizeStart, onResizeEnd, isLocked, onToggleLocked, rdrEnabled, queueBlocked, queueBlockReason }: DroppableColumnProps) {
  const { t } = useTranslation(['tasks', 'common']);
  const { setNodeRef } = useDroppable({
    id: status
  });

  // Calculate selection state for this column
  const taskCount = tasks.length;
  const columnSelectedCount = tasks.filter(t => selectedTaskIds?.has(t.id)).length;
  const isAllSelected = taskCount > 0 && columnSelectedCount === taskCount;
  const isSomeSelected = columnSelectedCount > 0 && columnSelectedCount < taskCount;

  // Determine checkbox checked state: true (all), 'indeterminate' (some), false (none)
  const selectAllCheckedState: boolean | 'indeterminate' = isAllSelected
    ? true
    : isSomeSelected
      ? 'indeterminate'
      : false;

  // Handle select all checkbox change
  const handleSelectAllChange = useCallback(() => {
    if (isAllSelected) {
      onDeselectAll?.();
    } else {
      onSelectAll?.();
    }
  }, [isAllSelected, onSelectAll, onDeselectAll]);

  // Memoize taskIds to prevent SortableContext from re-rendering unnecessarily
  const taskIds = useMemo(() => tasks.map((t) => t.id), [tasks]);

  // Create stable onClick handlers for each task to prevent unnecessary re-renders
  const onClickHandlers = useMemo(() => {
    const handlers = new Map<string, () => void>();
    tasks.forEach((task) => {
      handlers.set(task.id, () => onTaskClick(task));
    });
    return handlers;
  }, [tasks, onTaskClick]);

  // Create stable onStatusChange handlers for each task
  const onStatusChangeHandlers = useMemo(() => {
    const handlers = new Map<string, (newStatus: TaskStatus) => unknown>();
    tasks.forEach((task) => {
      handlers.set(task.id, (newStatus: TaskStatus) => onStatusChange(task.id, newStatus));
    });
    return handlers;
  }, [tasks, onStatusChange]);

  // Create stable onToggleSelect handlers for each task (for bulk selection)
  const onToggleSelectHandlers = useMemo(() => {
    if (!onToggleSelect) return null;
    const handlers = new Map<string, () => void>();
    tasks.forEach((task) => {
      handlers.set(task.id, () => onToggleSelect(task.id));
    });
    return handlers;
  }, [tasks, onToggleSelect]);

  // Memoize task card elements to prevent recreation on every render
  const taskCards = useMemo(() => {
    if (tasks.length === 0) return null;
    const isSelectable = !!onToggleSelectHandlers;
    return tasks.map((task) => (
      <SortableTaskCard
        key={task.id}
        task={task}
        onClick={onClickHandlers.get(task.id)!}
        onStatusChange={onStatusChangeHandlers.get(task.id)}
        onRefresh={onRefresh}
        isSelectable={isSelectable}
        isSelected={isSelectable ? selectedTaskIds?.has(task.id) : undefined}
        onToggleSelect={onToggleSelectHandlers?.get(task.id)}
        rdrEnabled={rdrEnabled}
      />
    ));
  }, [tasks, onClickHandlers, onStatusChangeHandlers, onToggleSelectHandlers, selectedTaskIds, rdrEnabled]);

  const getColumnBorderColor = (): string => {
    switch (status) {
      case 'backlog':
        return 'column-backlog';
      case 'queue':
        return 'column-queue';
      case 'in_progress':
        return 'column-in-progress';
      case 'ai_review':
        return 'column-ai-review';
      case 'human_review':
        return 'column-human-review';
      case 'done':
        return 'column-done';
      default:
        return 'border-t-muted-foreground/30';
    }
  };

  const emptyState = getEmptyStateContent(status, t);

  // Collapsed state: show narrow vertical strip with rotated title and task count
  if (isCollapsed) {
    return (
      <div
        ref={setNodeRef}
        className={cn(
          'flex flex-col rounded-xl border border-white/5 bg-linear-to-b from-secondary/30 to-transparent backdrop-blur-sm transition-all duration-200',
          getColumnBorderColor(),
          'border-t-2',
          isOver && 'drop-zone-highlight'
        )}
        style={{ width: COLLAPSED_COLUMN_WIDTH_REM, minWidth: COLLAPSED_COLUMN_WIDTH_REM, maxWidth: COLLAPSED_COLUMN_WIDTH_REM }}
      >
        {/* Expand button at top */}
        <div className="flex justify-center p-2 border-b border-white/5">
          <Tooltip delayDuration={200}>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 hover:bg-primary/10 hover:text-primary transition-colors"
                onClick={onToggleCollapsed}
                aria-label={t('kanban.expandColumn')}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">
              {t('kanban.expandColumn')}
            </TooltipContent>
          </Tooltip>
        </div>

        {/* Rotated title and task count */}
        <div className="flex-1 flex flex-col items-center justify-center">
          <div
            className="flex items-center gap-2 whitespace-nowrap"
            style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
          >
            <span className="column-count-badge">
              {tasks.length}
            </span>
            <h2 className="font-semibold text-sm text-foreground">
              {t(TASK_STATUS_LABELS[status])}
            </h2>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="relative flex"
      style={columnWidth ? { width: pxToRem(columnWidth), minWidth: MIN_COLUMN_WIDTH_REM, maxWidth: MAX_COLUMN_WIDTH_REM, flexShrink: 0 } : undefined}
    >
      <div
        ref={setNodeRef}
        className={cn(
          'flex flex-1 flex-col rounded-xl border border-white/5 bg-linear-to-b from-secondary/30 to-transparent backdrop-blur-sm transition-all duration-200',
          !columnWidth && 'min-w-80 max-w-[30rem]',
          getColumnBorderColor(),
          'border-t-2',
          isOver && 'drop-zone-highlight'
        )}
      >
        {/* Column header - enhanced styling */}
        <div className="flex items-center justify-between p-4 border-b border-white/5">
        <div className="flex items-center gap-2.5">
          {/* Collapse button */}
          {onToggleCollapsed && (
            <Tooltip delayDuration={200}>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 hover:bg-muted-foreground/10 hover:text-muted-foreground transition-colors"
                  onClick={onToggleCollapsed}
                  aria-label={t('kanban.collapseColumn')}
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {t('kanban.collapseColumn')}
              </TooltipContent>
            </Tooltip>
          )}
          {/* Select All checkbox for column */}
          {onSelectAll && onDeselectAll && (
            <Tooltip delayDuration={200}>
              <TooltipTrigger asChild>
                <div className="flex items-center">
                  <Checkbox
                    checked={selectAllCheckedState}
                    onCheckedChange={handleSelectAllChange}
                    disabled={taskCount === 0}
                    aria-label={isAllSelected ? t('kanban.deselectAll') : t('kanban.selectAll')}
                    className="h-4 w-4"
                  />
                </div>
              </TooltipTrigger>
              <TooltipContent>
                {isAllSelected ? t('kanban.deselectAll') : t('kanban.selectAll')}
              </TooltipContent>
            </Tooltip>
          )}
          <h2 className="font-semibold text-sm text-foreground">
            {t(TASK_STATUS_LABELS[status])}
          </h2>
          {status === 'in_progress' && maxParallelTasks ? (
            <div className="flex flex-col items-end gap-0.5">
              <span className={cn(
                "column-count-badge",
                tasks.length >= maxParallelTasks && "bg-warning/20 text-warning border-warning/30",
                queueBlocked && "bg-destructive/20 text-destructive border-destructive/30"
              )}>
                {tasks.length}/{maxParallelTasks}
              </span>
              {queueBlocked && (
                <span className="text-[10px] text-destructive leading-tight">
                  ⚠️ Queue paused: {queueBlockReason}
                </span>
              )}
            </div>
          ) : (
            <span className="column-count-badge">
              {tasks.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {/* Lock toggle button - available for all columns */}
          {onToggleLocked && (
            <Tooltip delayDuration={200}>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    'h-7 w-7 transition-colors',
                    isLocked
                      ? 'text-amber-500 bg-amber-500/10 hover:bg-amber-500/20'
                      : 'hover:bg-muted-foreground/10 hover:text-muted-foreground'
                  )}
                  onClick={onToggleLocked}
                  aria-pressed={isLocked}
                  aria-label={isLocked ? t('kanban.unlockColumn') : t('kanban.lockColumn')}
                >
                  {isLocked ? <Lock className="h-3.5 w-3.5" /> : <Unlock className="h-3.5 w-3.5" />}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {isLocked ? t('kanban.unlockColumn') : t('kanban.lockColumn')}
              </TooltipContent>
            </Tooltip>
          )}
          {status === 'backlog' && (
            <>
              {onQueueAll && tasks.length > 0 && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 hover:bg-cyan-500/10 hover:text-cyan-400 transition-colors"
                  onClick={onQueueAll}
                  title={t('queue.queueAll')}
                >
                  <ListPlus className="h-4 w-4" />
                </Button>
              )}
              {onAddClick && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 hover:bg-primary/10 hover:text-primary transition-colors"
                  onClick={onAddClick}
                  aria-label={t('kanban.addTaskAriaLabel')}
                >
                  <Plus className="h-4 w-4" />
                </Button>
              )}
            </>
          )}
          {status === 'queue' && onQueueSettings && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 hover:bg-cyan-500/10 hover:text-cyan-400 transition-colors"
              onClick={onQueueSettings}
              title={t('kanban.queueSettings')}
            >
              <Settings className="h-4 w-4" />
            </Button>
          )}
          {status === 'done' && onArchiveAll && tasks.length > 0 && !showArchived && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 hover:bg-muted-foreground/10 hover:text-muted-foreground transition-colors"
              onClick={onArchiveAll}
              aria-label={t('tooltips.archiveAllDone')}
            >
              <Archive className="h-4 w-4" />
            </Button>
          )}
          {status === 'done' && archivedCount !== undefined && archivedCount > 0 && onToggleArchived && (
            <Tooltip delayDuration={200}>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    'h-7 w-7 transition-colors relative',
                    showArchived
                      ? 'text-primary bg-primary/10 hover:bg-primary/20'
                      : 'hover:bg-muted-foreground/10 hover:text-muted-foreground'
                  )}
                  onClick={onToggleArchived}
                  aria-pressed={showArchived}
                  aria-label={t('common:accessibility.toggleShowArchivedAriaLabel')}
                >
                  <Archive className="h-4 w-4" />
                  <span className="absolute -top-1 -right-1 text-[10px] font-medium bg-muted rounded-full min-w-[14px] h-[14px] flex items-center justify-center">
                    {archivedCount}
                  </span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {showArchived ? t('common:projectTab.hideArchived') : t('common:projectTab.showArchived')}
              </TooltipContent>
            </Tooltip>
          )}
        </div>
      </div>

      {/* Task list */}
      <div className="flex-1 min-h-0">
        <ScrollArea className="h-full px-3 pb-3 pt-2">
          <SortableContext
            items={taskIds}
            strategy={verticalListSortingStrategy}
          >
            <div className="space-y-3 min-h-[120px]">
              {tasks.length === 0 ? (
                <div
                  className={cn(
                    'empty-column-dropzone flex flex-col items-center justify-center py-6',
                    isOver && 'active'
                  )}
                >
                  {isOver ? (
                    <>
                      <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center mb-2">
                        <Plus className="h-4 w-4 text-primary" />
                      </div>
                      <span className="text-sm font-medium text-primary">{t('kanban.dropHere')}</span>
                    </>
                  ) : (
                    <>
                      {emptyState.icon}
                      <span className="mt-2 text-sm font-medium text-muted-foreground/70">
                        {emptyState.message}
                      </span>
                      {emptyState.subtext && (
                        <span className="mt-0.5 text-xs text-muted-foreground/50">
                          {emptyState.subtext}
                        </span>
                      )}
                    </>
                  )}
                </div>
              ) : (
                taskCards
              )}
            </div>
          </SortableContext>
        </ScrollArea>
      </div>
      </div>

      {/* Resize handle on right edge */}
      {onResizeStart && onResizeEnd && (
        <div
          className={cn(
            "absolute right-0 top-0 bottom-0 w-1 touch-none z-10",
            "transition-colors duration-150",
            isLocked
              ? "cursor-not-allowed bg-transparent"
              : "cursor-col-resize hover:bg-primary/40",
            isResizing && !isLocked && "bg-primary/60"
          )}
          onMouseDown={(e) => {
            e.preventDefault();
            // Don't start resize if column is locked
            if (isLocked) return;
            onResizeStart(e.clientX);
          }}
          onTouchStart={(e) => {
            e.preventDefault();
            // Don't start resize if column is locked
            if (isLocked) return;
            if (e.touches.length > 0) {
              onResizeStart(e.touches[0].clientX);
            }
          }}
          title={isLocked ? t('kanban.columnLocked') : undefined}
        >
          {/* Wider invisible hit area for easier grabbing */}
          <div className="absolute inset-y-0 -left-1 -right-1" />
        </div>
      )}
    </div>
  );
}, droppableColumnPropsAreEqual);

export function KanbanBoard({ tasks, onTaskClick, onNewTaskClick, onRefresh, isRefreshing }: KanbanBoardProps) {
  const { t } = useTranslation(['tasks', 'dialogs', 'common']);
  const { toast } = useToast();
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [overColumnId, setOverColumnId] = useState<string | null>(null);
  const { showArchived, toggleShowArchived } = useViewState();

  // Project store for queue settings
  const projects = useProjectStore((state) => state.projects);

  // Kanban settings store for column preferences (collapse state, width, lock state)
  const columnPreferences = useKanbanSettingsStore((state) => state.columnPreferences);
  const loadKanbanPreferences = useKanbanSettingsStore((state) => state.loadPreferences);
  const saveKanbanPreferences = useKanbanSettingsStore((state) => state.savePreferences);
  const toggleColumnCollapsed = useKanbanSettingsStore((state) => state.toggleColumnCollapsed);
  const setColumnCollapsed = useKanbanSettingsStore((state) => state.setColumnCollapsed);
  const setColumnWidth = useKanbanSettingsStore((state) => state.setColumnWidth);
  const toggleColumnLocked = useKanbanSettingsStore((state) => state.toggleColumnLocked);

  // Column resize state
  const [resizingColumn, setResizingColumn] = useState<typeof TASK_STATUS_COLUMNS[number] | null>(null);
  const resizeStartX = useRef<number>(0);
  const resizeStartWidth = useRef<number>(0);
  // Capture projectId at resize start to avoid stale closure if project changes during resize
  const resizeProjectIdRef = useRef<string | null>(null);

  // Get projectId from first task
  const projectId = tasks[0]?.projectId;
  const project = projectId ? projects.find((p) => p.id === projectId) : undefined;
  const maxParallelTasks = project?.settings?.maxParallelTasks ?? DEFAULT_MAX_PARALLEL_TASKS;

  // Queue settings modal state
  const [showQueueSettings, setShowQueueSettings] = useState(false);
  // Store projectId when modal opens to prevent modal from disappearing if tasks change
  const queueSettingsProjectIdRef = useRef<string | null>(null);

  // Queue processing lock to prevent race conditions
  const isProcessingQueueRef = useRef(false);

  // Synchronous queue blocking flag (useRef = immediate, no stale closure)
  // useState is async (takes effect next render), so processQueue can read stale false.
  // useRef is synchronous — setting .current = true blocks immediately.
  const queueBlockedRef = useRef(false);

  // Selection state for bulk actions (Human Review column)
  const [selectedTaskIds, setSelectedTaskIds] = useState<Set<string>>(new Set());

  // Bulk PR dialog state
  const [bulkPRDialogOpen, setBulkPRDialogOpen] = useState(false);

  // Delete confirmation dialog state
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Worktree cleanup dialog state
  const [worktreeCleanupDialog, setWorktreeCleanupDialog] = useState<{
    open: boolean;
    taskId: string | null;
    taskTitle: string;
    worktreePath?: string;
    isProcessing: boolean;
    error?: string;
  }>({
    open: false,
    taskId: null,
    taskTitle: '',
    worktreePath: undefined,
    isProcessing: false,
    error: undefined
  });

  // Queue blocking state (RDR-driven)
  const [queueBlocked, setQueueBlocked] = useState(false);
  const [queueBlockReason, setQueueBlockReason] = useState<string | null>(null);

  // Calculate archived count for Done column button
  const archivedCount = useMemo(() =>
    tasks.filter(t => t.metadata?.archivedAt).length,
    [tasks]
  );

  // Calculate collapsed column count for "Expand All" button
  const collapsedColumnCount = useMemo(() => {
    if (!columnPreferences) return 0;
    return TASK_STATUS_COLUMNS.filter(
      (status) => columnPreferences[status]?.isCollapsed
    ).length;
  }, [columnPreferences]);

  // Filter tasks based on archive status
  const filteredTasks = useMemo(() => {
    if (showArchived) {
      return tasks; // Show all tasks including archived
    }
    return tasks.filter((t) => !t.metadata?.archivedAt);
  }, [tasks, showArchived]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8 // 8px movement required before drag starts
      }
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates
    })
  );

  // Get task order from store for custom ordering
  const taskOrder = useTaskStore((state) => state.taskOrder);

  const tasksByStatus = useMemo(() => {
    // Note: pr_created tasks are shown in the 'done' column since they're essentially complete
    // Note: error tasks are shown in the 'human_review' column since they need human attention
    const grouped: Record<typeof TASK_STATUS_COLUMNS[number], Task[]> = {
      backlog: [],
      queue: [],
      in_progress: [],
      ai_review: [],
      human_review: [],
      done: []
    };

    filteredTasks.forEach((task) => {
      // Map pr_created tasks to the done column, error tasks to human_review
      const targetColumn = getVisualColumn(task.status);
      if (grouped[targetColumn]) {
        grouped[targetColumn].push(task);
      }
    });

    // Sort tasks within each column
    Object.keys(grouped).forEach((status) => {
      const statusKey = status as typeof TASK_STATUS_COLUMNS[number];
      const columnTasks = grouped[statusKey];
      const columnOrder = taskOrder?.[statusKey];

      if (columnOrder && columnOrder.length > 0) {
        // Custom order exists: sort by order index
        // 1. Create a set of current task IDs for fast lookup (filters stale IDs)
        const currentTaskIds = new Set(columnTasks.map(t => t.id));

        // 2. Create valid order by filtering out stale IDs
        const validOrder = columnOrder.filter(id => currentTaskIds.has(id));
        const validOrderSet = new Set(validOrder);

        // 3. Find new tasks not in order (prepend at top)
        const newTasks = columnTasks.filter(t => !validOrderSet.has(t.id));
        // Sort new tasks by createdAt (newest first)
        newTasks.sort((a, b) => {
          const dateA = new Date(a.createdAt).getTime();
          const dateB = new Date(b.createdAt).getTime();
          return dateB - dateA;
        });

        // 4. Sort ordered tasks by their index in validOrder
        // Pre-compute index map for O(n) sorting instead of O(n²) with indexOf
        const indexMap = new Map(validOrder.map((id, idx) => [id, idx]));
        const orderedTasks = columnTasks
          .filter(t => validOrderSet.has(t.id))
          .sort((a, b) => (indexMap.get(a.id) ?? 0) - (indexMap.get(b.id) ?? 0));

        // 5. Prepend new tasks at top, then ordered tasks
        grouped[statusKey] = [...newTasks, ...orderedTasks];
      } else {
        // No custom order: fallback to createdAt sort (newest first)
        grouped[statusKey].sort((a, b) => {
          const dateA = new Date(a.createdAt).getTime();
          const dateB = new Date(b.createdAt).getTime();
          return dateB - dateA;
        });
      }
    });

    return grouped;
  }, [filteredTasks, taskOrder]);

  // Prune stale IDs when tasks are deleted or filtered out
  useEffect(() => {
    const allTaskIds = new Set(filteredTasks.map(t => t.id));
    setSelectedTaskIds(prev => {
      const filtered = new Set([...prev].filter(id => allTaskIds.has(id)));
      return filtered.size === prev.size ? prev : filtered;
    });
  }, [filteredTasks]);

  // Selection callbacks for bulk actions (all columns)
  const toggleTaskSelection = useCallback((taskId: string) => {
    setSelectedTaskIds(prev => {
      const next = new Set(prev);
      if (next.has(taskId)) {
        next.delete(taskId);
      } else {
        next.add(taskId);
      }
      return next;
    });
  }, []);

  const selectAllTasks = useCallback((columnStatus?: typeof TASK_STATUS_COLUMNS[number]) => {
    if (columnStatus) {
      // Select all in specific column
      const columnTasks = tasksByStatus[columnStatus] || [];
      const columnIds = new Set(columnTasks.map((t: Task) => t.id));
      setSelectedTaskIds(prev => new Set<string>([...prev, ...columnIds]));
    } else {
      // Select all across all columns
      const allIds = new Set(filteredTasks.map(t => t.id));
      setSelectedTaskIds(allIds);
    }
  }, [tasksByStatus, filteredTasks]);

  const deselectAllTasks = useCallback(() => {
    setSelectedTaskIds(new Set());
  }, []);

  // Get selected task objects for bulk actions
  const selectedTasks = useMemo(() => {
    return filteredTasks.filter(task => selectedTaskIds.has(task.id));
  }, [filteredTasks, selectedTaskIds]);

  // Handle opening the bulk PR dialog
  const handleOpenBulkPRDialog = useCallback(() => {
    if (selectedTaskIds.size > 0) {
      setBulkPRDialogOpen(true);
    }
  }, [selectedTaskIds.size]);

  // Handle bulk PR dialog completion - clear selection
  const handleBulkPRComplete = useCallback(() => {
    deselectAllTasks();
  }, [deselectAllTasks]);

  // Handle opening delete confirmation dialog
  const handleOpenDeleteConfirm = useCallback(() => {
    if (selectedTaskIds.size > 0) {
      setDeleteConfirmOpen(true);
    }
  }, [selectedTaskIds.size]);

  // Handle confirmed bulk delete
  const handleConfirmDelete = useCallback(async () => {
    if (selectedTaskIds.size === 0) return;

    setIsDeleting(true);
    const taskIdsToDelete = Array.from(selectedTaskIds);
    const result = await deleteTasks(taskIdsToDelete);

    setIsDeleting(false);
    setDeleteConfirmOpen(false);

    if (result.success) {
      toast({
        title: t('kanban.deleteSuccess', { count: taskIdsToDelete.length }),
      });
      deselectAllTasks();
    } else {
      toast({
        title: t('kanban.deleteError'),
        description: result.error,
        variant: 'destructive',
      });
      // Still clear selection for successfully deleted tasks
      if (result.failedIds) {
        const remainingIds = new Set(result.failedIds);
        setSelectedTaskIds(remainingIds);
      }
    }
  }, [selectedTaskIds, deselectAllTasks, toast, t]);

  // Check if all selected tasks have RDR disabled
  const allSelectedRdrDisabled = useMemo(() => {
    return selectedTasks.length > 0 && selectedTasks.every(t => t.metadata?.rdrDisabled);
  }, [selectedTasks]);

  // Handle bulk RDR toggle
  const handleBulkToggleRdr = useCallback(async () => {
    if (selectedTaskIds.size === 0) return;

    const newDisabled = !allSelectedRdrDisabled;
    const taskIds = Array.from(selectedTaskIds);
    let successCount = 0;

    for (const taskId of taskIds) {
      const result = await window.electronAPI.toggleTaskRdr(taskId, newDisabled);
      if (result.success) successCount++;
    }

    if (successCount > 0) {
      toast({
        title: `RDR ${newDisabled ? 'disabled' : 'enabled'} for ${successCount} task${successCount > 1 ? 's' : ''}`,
      });
      // Trigger refresh to update task cards
      onRefresh?.();
    }
  }, [selectedTaskIds, allSelectedRdrDisabled, toast, onRefresh]);

  const handleArchiveAll = async () => {
    // Get projectId from the first task (all tasks should have the same projectId)
    const projectId = tasks[0]?.projectId;
    if (!projectId) {
      console.error('[KanbanBoard] No projectId found');
      return;
    }

    const doneTaskIds = tasksByStatus.done.map((t) => t.id);
    if (doneTaskIds.length === 0) return;

    const result = await archiveTasks(projectId, doneTaskIds);
    if (!result.success) {
      console.error('[KanbanBoard] Failed to archive tasks:', result.error);
    }
  };

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    const task = tasks.find((t) => t.id === active.id);
    if (task) {
      setActiveTask(task);
    }
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { over } = event;

    if (!over) {
      setOverColumnId(null);
      return;
    }

    const overId = over.id as string;

    // Check if over a column
    if (isValidDropColumn(overId)) {
      setOverColumnId(overId);
      return;
    }

    // Check if over a task - get its column
    const overTask = tasks.find((t) => t.id === overId);
    if (overTask) {
      setOverColumnId(overTask.status);
    }
  };

  /**
   * Handle status change with worktree cleanup dialog support
   * Consolidated handler that accepts an optional task object for the dialog title
   */
  const handleStatusChange = async (taskId: string, requestedStatus: TaskStatus, providedTask?: Task) => {
    const task = providedTask || tasks.find(t => t.id === taskId);
    let newStatus = requestedStatus;

    // ============================================
    // QUEUE SYSTEM: Enforce parallel task limit
    // Called from both the dropdown menu and the drag-and-drop handler.
    // Excludes the task itself from the count to handle re-entry (e.g., redundant
    // status change or race with auto-promotion). processQueue auto-promotion
    // calls persistTaskStatus directly, never this function.
    // ============================================
    if (newStatus === 'in_progress' && isQueueAtCapacity(taskId)) {
      console.log('[Queue] In Progress full, redirecting task to Queue');
      newStatus = 'queue';
    }

    const oldStatus = task?.status;
    const result = await persistTaskStatus(taskId, newStatus);

    if (!result.success) {
      if (result.worktreeExists) {
        // Show the worktree cleanup dialog
        setWorktreeCleanupDialog({
          open: true,
          taskId: taskId,
          taskTitle: task?.title || t('tasks:untitled'),
          worktreePath: result.worktreePath,
          isProcessing: false,
          error: undefined
        });
      } else {
        // Show error toast for other failures
        toast({
          title: t('common:errors.operationFailed'),
          description: result.error || t('common:errors.unknownError'),
          variant: 'destructive'
        });
      }
    }
    // Note: queue auto-promotion when a task leaves in_progress is handled by the
    // useEffect task status change listener (registerTaskStatusChangeListener), so
    // no explicit processQueue() call is needed here.
  };

  /**
   * Handle worktree cleanup confirmation
   */
  const handleWorktreeCleanupConfirm = async () => {
    if (!worktreeCleanupDialog.taskId) return;

    setWorktreeCleanupDialog(prev => ({ ...prev, isProcessing: true, error: undefined }));

    const result = await forceCompleteTask(worktreeCleanupDialog.taskId);

    if (result.success) {
      setWorktreeCleanupDialog({
        open: false,
        taskId: null,
        taskTitle: '',
        worktreePath: undefined,
        isProcessing: false,
        error: undefined
      });
    } else {
      // Keep dialog open with error state for retry - show actual error if available
      setWorktreeCleanupDialog(prev => ({
        ...prev,
        isProcessing: false,
        error: result.error || t('dialogs:worktreeCleanup.errorDescription')
      }));
    }
  };

  /**
   * Move all backlog tasks to queue
   */
  const handleQueueAll = async () => {
    const backlogTasks = tasksByStatus.backlog;
    if (backlogTasks.length === 0) return;

    let movedCount = 0;
    for (const task of backlogTasks) {
      const result = await persistTaskStatus(task.id, 'queue');
      if (result.success) {
        movedCount++;
      } else {
        console.error(`[Queue] Failed to move task ${task.id} to queue:`, result.error);
      }
    }

    // Auto-promote queued tasks to fill available capacity
    await processQueue();

    toast({
      title: t('queue.queueAllSuccess', { count: movedCount }),
      variant: 'default'
    });
  };

  /**
   * Save queue settings (maxParallelTasks)
   *
   * Uses the stored ref value to ensure the save works even if tasks
   * change while the modal is open.
   */
  const handleSaveQueueSettings = async (maxParallel: number) => {
    const savedProjectId = queueSettingsProjectIdRef.current || projectId;
    if (!savedProjectId) return;

    const success = await updateProjectSettings(savedProjectId, { maxParallelTasks: maxParallel });
    if (success) {
      toast({
        title: t('queue.settings.saved'),
        variant: 'default'
      });
    } else {
      toast({
        title: t('queue.settings.saveFailed'),
        description: t('queue.settings.retry'),
        variant: 'destructive'
      });
    }
  };

  /**
   * Automatically move tasks from Queue to In Progress to fill available capacity
   * Promotes multiple tasks if needed (e.g., after bulk queue)
   */
  const processQueue = useCallback(async () => {
    // Check if queue is blocked by RDR (regression/failure detection)
    // Uses ref (synchronous) instead of state (async) to prevent race conditions
    if (queueBlockedRef.current) {
      debugLog('[Queue] Queue is BLOCKED (ref), skipping processing:', queueBlockReason);
      return;
    }

    // RDR timing guard: Check live store data for failed tasks
    // This catches edge cases where the blocking ref hasn't been set yet
    // but the store already reflects the failure (synchronous Zustand update)
    const rdrProject = useProjectStore.getState().getActiveProject();
    const rdrActive = rdrProject?.settings?.rdrEnabled ?? false;
    if (rdrActive) {
      const allTasks = useTaskStore.getState().tasks;
      const activeFailures = allTasks.filter(t =>
        t.status === 'human_review' &&
        t.reviewReason &&
        t.reviewReason !== 'stopped' &&
        t.reviewReason !== 'completed' &&
        !t.metadata?.archivedAt
      );
      if (activeFailures.length > 0 && !queueBlockedRef.current) {
        debugLog('[Queue] RDR timing guard: failed tasks detected, setting block', {
          failedIds: activeFailures.map(t => t.id)
        });
        queueBlockedRef.current = true;
        setQueueBlocked(true);
        setQueueBlockReason('Task(s) failed during execution');
        return;
      }
    }

    // Prevent concurrent executions to avoid race conditions
    if (isProcessingQueueRef.current) {
      debugLog('[Queue] Already processing queue, skipping duplicate call');
      return;
    }

    isProcessingQueueRef.current = true;

    try {
      // Track tasks we've already processed in this call to prevent duplicates
      // This is critical because store updates happen synchronously but we need to ensure
      // we never process the same task twice, even if there are timing issues
      const processedTaskIds = new Set<string>();
      let consecutiveFailures = 0;
      const MAX_CONSECUTIVE_FAILURES = 10; // Safety limit to prevent infinite loop

      // Track promotions in this call for logging/summary only
      let promotedInThisCall = 0;

      // Log initial state
      const startTasks = useTaskStore.getState().tasks;
      const startInProgress = startTasks.filter((t) => t.status === 'in_progress' && !t.metadata?.archivedAt);
      const startQueued = startTasks.filter((t) => t.status === 'queue' && !t.metadata?.archivedAt);
      debugLog(`[Queue] === PROCESS QUEUE START ===`, {
        maxParallelTasks,
        inProgressCount: startInProgress.length,
        inProgressIds: startInProgress.map(t => t.id),
        queuedCount: startQueued.length,
        queuedIds: startQueued.map(t => t.id),
        projectId
      });

      // Loop until capacity is full or queue is empty
      let iteration = 0;
      while (true) {
        iteration++;

        // Fresh read of actual in-progress count every iteration
        // This catches concurrent changes (file watcher restarts, RDR recoveries)
        // that would make a stale snapshot incorrect
        const currentTasks = useTaskStore.getState().tasks;
        const currentInProgress = currentTasks.filter((t) => t.status === 'in_progress' && !t.metadata?.archivedAt);
        const queuedTasks = currentTasks.filter((t) =>
          t.status === 'queue' && !t.metadata?.archivedAt && !processedTaskIds.has(t.id)
        );

        debugLog(`[Queue] --- Iteration ${iteration} ---`, {
          liveInProgressCount: currentInProgress.length,
          liveInProgressIds: currentInProgress.map(t => t.id),
          promotedInThisCall,
          capacityCheck: currentInProgress.length >= maxParallelTasks,
          queuedCount: queuedTasks.length,
          queuedIds: queuedTasks.map(t => t.id),
          processedCount: processedTaskIds.size
        });

        // Stop if no capacity (live count — includes tasks promoted by this call AND concurrent restarts)
        if (currentInProgress.length >= maxParallelTasks) {
          debugLog(`[Queue] Capacity reached (live: ${currentInProgress.length}/${maxParallelTasks}), stopping queue processing`);
          break;
        }

        // Stop if no queued tasks or too many consecutive failures
        if (queuedTasks.length === 0) {
          debugLog('[Queue] No more queued tasks to process');
          break;
        }

        if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
          debugLog(`[Queue] Stopping queue processing after ${MAX_CONSECUTIVE_FAILURES} consecutive failures`);
          break;
        }

        // Get the oldest task in queue (FIFO ordering)
        const nextTask = queuedTasks.sort((a, b) => {
          const dateA = new Date(a.createdAt).getTime();
          const dateB = new Date(b.createdAt).getTime();
          return dateA - dateB; // Ascending order (oldest first)
        })[0];

        debugLog(`[Queue] Selected task for promotion:`, {
          id: nextTask.id,
          currentStatus: nextTask.status,
          title: nextTask.title?.substring(0, 50)
        });

        // Mark task as processed BEFORE attempting promotion to prevent duplicates
        processedTaskIds.add(nextTask.id);

        // Re-check blocking ref before each promotion (another failure may have set it mid-loop)
        if (queueBlockedRef.current) {
          debugLog('[Queue] Queue blocked mid-processing, stopping promotion');
          break;
        }

        debugLog(`[Queue] Promoting task ${nextTask.id} (${promotedInThisCall + 1}/${maxParallelTasks})`);
        const result = await persistTaskStatus(nextTask.id, 'in_progress');

        // Check store state after promotion
        const afterPromoteTasks = useTaskStore.getState().tasks;
        const afterPromoteInProgress = afterPromoteTasks.filter((t) => t.status === 'in_progress' && !t.metadata?.archivedAt);
        const afterPromoteQueued = afterPromoteTasks.filter((t) => t.status === 'queue' && !t.metadata?.archivedAt);

        debugLog(`[Queue] After promotion attempt:`, {
          resultSuccess: result.success,
          promotedInThisCall,
          inProgressCount: afterPromoteInProgress.length,
          inProgressIds: afterPromoteInProgress.map(t => t.id),
          queuedCount: afterPromoteQueued.length,
          queuedIds: afterPromoteQueued.map(t => t.id)
        });

        if (result.success) {
          // Increment our local promotion counter
          promotedInThisCall++;
          // Reset consecutive failures on success
          consecutiveFailures = 0;
        } else {
          // If promotion failed, log error and continue to next task
          console.error(`[Queue] Failed to promote task ${nextTask.id} to In Progress:`, result.error);
          consecutiveFailures++;
        }
      }

      // Log summary
      debugLog(`[Queue] === PROCESS QUEUE COMPLETE ===`, {
        totalIterations: iteration,
        tasksProcessed: processedTaskIds.size,
        tasksPromoted: promotedInThisCall,
        processedIds: Array.from(processedTaskIds)
      });

      // Trigger UI refresh if tasks were promoted to ensure UI reflects all changes
      // This handles the case where store updates are batched/delayed via IPC events
      if (promotedInThisCall > 0 && onRefresh) {
        debugLog('[Queue] Triggering UI refresh after queue promotion');
        onRefresh();
      }
    } finally {
      isProcessingQueueRef.current = false;
    }
  }, [maxParallelTasks, projectId, onRefresh]);

  // Register task status change listener for queue auto-promotion
  // This ensures processQueue() is called whenever a task leaves in_progress
  // AND implements queue blocking when RDR detects regressions/failures
  useEffect(() => {
    const unregister = useTaskStore.getState().registerTaskStatusChangeListener(
      (taskId, oldStatus, newStatus) => {
        // Get RDR setting
        const projectState = useProjectStore.getState().getActiveProject();
        const rdrEnabled = projectState?.settings?.rdrEnabled ?? false;

        // Queue blocking logic (only when RDR is ON)
        if (rdrEnabled) {
          const task = useTaskStore.getState().tasks.find(t => t.id === taskId);

          // REGRESSION: Task regressed from in_progress to backlog (Planning board)
          if (oldStatus === 'in_progress' && newStatus === 'backlog') {
            debugLog(`[Queue] BLOCKED - Task ${taskId} regressed to backlog (Planning board)`);
            queueBlockedRef.current = true;  // Synchronous — takes effect immediately
            setQueueBlocked(true);           // Async — for UI rendering
            setQueueBlockReason('Task regressed to Planning board');
            return; // Don't process queue
          }

          // FAILURE: Task failed from in_progress to human_review (not user-stopped)
          if (oldStatus === 'in_progress' && newStatus === 'human_review') {
            if (task?.reviewReason !== 'stopped') {
              debugLog(`[Queue] BLOCKED - Task ${taskId} failed during execution`);
              queueBlockedRef.current = true;  // Synchronous — takes effect immediately
              setQueueBlocked(true);           // Async — for UI rendering
              setQueueBlockReason('Task failed during execution');
              return; // Don't process queue
            }
          }

          // FAILURE: Task failed from ai_review to human_review (not user-stopped)
          if (oldStatus === 'ai_review' && newStatus === 'human_review') {
            if (task?.reviewReason !== 'stopped') {
              debugLog(`[Queue] BLOCKED - Task ${taskId} failed QA review`);
              queueBlockedRef.current = true;  // Synchronous — takes effect immediately
              setQueueBlocked(true);           // Async — for UI rendering
              setQueueBlockReason('Task failed QA review');
              return; // Don't process queue
            }
          }
        }

        // Normal queue processing (when task leaves in_progress)
        if (oldStatus === 'in_progress' && newStatus !== 'in_progress') {
          // When RDR is enabled, don't promote queue tasks for stopped transitions
          // RDR will restart killed agents, so the slot will be re-filled — promoting would over-fill capacity
          if (rdrEnabled && newStatus === 'human_review') {
            const stoppedTask = useTaskStore.getState().tasks.find(t => t.id === taskId);
            if (stoppedTask?.reviewReason === 'stopped') {
              debugLog(`[Queue] RDR enabled, task ${taskId} stopped — skipping queue promotion (RDR will handle)`);
              return;
            }
          }
          debugLog(`[Queue] Task ${taskId} left in_progress, processing queue to fill slot`);
          processQueue();
        }
      }
    );

    // Cleanup: unregister listener when component unmounts
    return unregister;
  }, [processQueue]);

  /**
   * Manually unblock the queue
   * Called when user manually drags a task to in_progress (shows they want to override)
   * or when the problematic task is fixed/moved
   */
  const unblockQueue = useCallback(() => {
    if (queueBlockedRef.current || queueBlocked) {
      debugLog('[Queue] Manually unblocking queue');
      queueBlockedRef.current = false;  // Clear ref synchronously
      setQueueBlocked(false);
      setQueueBlockReason(null);
      // Trigger queue processing to fill newly available slots
      processQueue();
    }
  }, [queueBlocked, processQueue]);

  // Auto-promote queued tasks when max parallel capacity increases
  useEffect(() => {
    processQueue();
  }, [maxParallelTasks, processQueue]);

  // Clear queue blocking when RDR is toggled off
  const rdrEnabledForBlockClear = useProjectStore(
    (state) => state.getSelectedProject()?.settings?.rdrEnabled ?? false
  );
  useEffect(() => {
    if (!rdrEnabledForBlockClear && queueBlockedRef.current) {
      debugLog('[Queue] RDR disabled, clearing queue block');
      queueBlockedRef.current = false;
      setQueueBlocked(false);
      setQueueBlockReason(null);
    }
  }, [rdrEnabledForBlockClear]);

  // Get task order actions from store
  const reorderTasksInColumn = useTaskStore((state) => state.reorderTasksInColumn);
  const moveTaskToColumnTop = useTaskStore((state) => state.moveTaskToColumnTop);
  const saveTaskOrderToStorage = useTaskStore((state) => state.saveTaskOrder);
  const loadTaskOrder = useTaskStore((state) => state.loadTaskOrder);
  const setTaskOrder = useTaskStore((state) => state.setTaskOrder);

  const saveTaskOrder = useCallback((projectIdToSave: string) => {
    const success = saveTaskOrderToStorage(projectIdToSave);
    if (!success) {
      toast({
        title: t('kanban.orderSaveFailedTitle'),
        description: t('kanban.orderSaveFailedDescription'),
        variant: 'destructive'
      });
    }
    return success;
  }, [saveTaskOrderToStorage, toast, t]);

  // Load task order on mount and when project changes
  useEffect(() => {
    if (projectId) {
      loadTaskOrder(projectId);
    }
  }, [projectId, loadTaskOrder]);

  // Load kanban column preferences on mount and when project changes
  useEffect(() => {
    if (projectId) {
      loadKanbanPreferences(projectId);
    }
  }, [projectId, loadKanbanPreferences]);

  // Create a callback to toggle collapsed state and save to storage
  const handleToggleColumnCollapsed = useCallback((status: typeof TASK_STATUS_COLUMNS[number]) => {
    // Capture projectId at function start to avoid stale closure in setTimeout
    const currentProjectId = projectId;
    toggleColumnCollapsed(status);
    // Save preferences after toggling
    if (currentProjectId) {
      // Use setTimeout to ensure state is updated before saving
      setTimeout(() => {
        saveKanbanPreferences(currentProjectId);
      }, 0);
    }
  }, [toggleColumnCollapsed, saveKanbanPreferences, projectId]);

  // Create a callback to expand all collapsed columns and save to storage
  const handleExpandAll = useCallback(() => {
    // Capture projectId at function start to avoid stale closure in setTimeout
    const currentProjectId = projectId;
    // Expand all collapsed columns
    for (const status of TASK_STATUS_COLUMNS) {
      if (columnPreferences?.[status]?.isCollapsed) {
        setColumnCollapsed(status, false);
      }
    }
    // Save preferences after expanding
    if (currentProjectId) {
      setTimeout(() => {
        saveKanbanPreferences(currentProjectId);
      }, 0);
    }
  }, [columnPreferences, setColumnCollapsed, saveKanbanPreferences, projectId]);

  // Create a callback to toggle locked state and save to storage
  const handleToggleColumnLocked = useCallback((status: typeof TASK_STATUS_COLUMNS[number]) => {
    // Capture projectId at function start to avoid stale closure in setTimeout
    const currentProjectId = projectId;
    toggleColumnLocked(status);
    // Save preferences after toggling
    if (currentProjectId) {
      // Use setTimeout to ensure state is updated before saving
      setTimeout(() => {
        saveKanbanPreferences(currentProjectId);
      }, 0);
    }
  }, [toggleColumnLocked, saveKanbanPreferences, projectId]);

  // Resize handlers for column width adjustment
  const handleResizeStart = useCallback((status: typeof TASK_STATUS_COLUMNS[number], startX: number) => {
    const currentWidth = columnPreferences?.[status]?.width ?? DEFAULT_COLUMN_WIDTH;
    resizeStartX.current = startX;
    resizeStartWidth.current = currentWidth;
    // Capture projectId at resize start to ensure we save to the correct project
    resizeProjectIdRef.current = projectId ?? null;
    setResizingColumn(status);
  }, [columnPreferences, projectId]);

  const handleResizeMove = useCallback((clientX: number) => {
    if (!resizingColumn) return;

    const scaleFactor = parseFloat(getComputedStyle(document.documentElement).fontSize) / BASE_FONT_SIZE;
    const deltaX = (clientX - resizeStartX.current) / scaleFactor;
    const newWidth = Math.max(MIN_COLUMN_WIDTH, Math.min(MAX_COLUMN_WIDTH, resizeStartWidth.current + deltaX));
    setColumnWidth(resizingColumn, newWidth);
  }, [resizingColumn, setColumnWidth]);

  const handleResizeEnd = useCallback(() => {
    // Use the projectId captured at resize start to avoid saving to wrong project
    const savedProjectId = resizeProjectIdRef.current;
    if (resizingColumn && savedProjectId) {
      saveKanbanPreferences(savedProjectId);
    }
    setResizingColumn(null);
    resizeProjectIdRef.current = null;
  }, [resizingColumn, saveKanbanPreferences]);

  // Document-level event listeners for resize dragging
  useEffect(() => {
    if (!resizingColumn) return;

    const handleMouseMove = (e: MouseEvent) => {
      handleResizeMove(e.clientX);
    };

    const handleMouseUp = () => {
      handleResizeEnd();
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 0) return;
      handleResizeMove(e.touches[0].clientX);
    };

    const handleTouchEnd = () => {
      handleResizeEnd();
    };

    // Prevent text selection and set resize cursor during drag
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'col-resize';

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('touchmove', handleTouchMove, { passive: false });
    document.addEventListener('touchend', handleTouchEnd);

    return () => {
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('touchmove', handleTouchMove);
      document.removeEventListener('touchend', handleTouchEnd);
    };
  }, [resizingColumn, handleResizeMove, handleResizeEnd]);

  // Clean up stale task IDs from order when tasks change (e.g., after deletion)
  // This ensures the persisted order doesn't contain IDs for deleted tasks
  useEffect(() => {
    if (!projectId || !taskOrder) return;

    // Build a set of current task IDs for fast lookup
    const currentTaskIds = new Set(tasks.map(t => t.id));

    // Check each column for stale IDs
    let hasStaleIds = false;
    const cleanedOrder: typeof taskOrder = {
      backlog: [],
      queue: [],
      in_progress: [],
      ai_review: [],
      human_review: [],
      done: [],
      pr_created: [],
      error: []
    };

    for (const status of Object.keys(taskOrder) as Array<keyof typeof taskOrder>) {
      const columnOrder = taskOrder[status] || [];
      const cleanedColumnOrder = columnOrder.filter(id => currentTaskIds.has(id));

      cleanedOrder[status] = cleanedColumnOrder;

      // Check if any IDs were removed
      if (cleanedColumnOrder.length !== columnOrder.length) {
        hasStaleIds = true;
      }
    }

    // If stale IDs were found, update the order and persist
    if (hasStaleIds) {
      setTaskOrder(cleanedOrder);
      saveTaskOrder(projectId);
    }
  }, [tasks, taskOrder, projectId, setTaskOrder, saveTaskOrder]);

  const handleDragEnd = useCallback(async (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveTask(null);
    setOverColumnId(null);

    if (!over) return;

    const activeTaskId = active.id as string;
    const overId = over.id as string;

    // Determine target status
    let newStatus: TaskStatus | null = null;
    let oldStatus: TaskStatus | null = null;

    // Get the task being dragged
    const task = tasks.find((t) => t.id === activeTaskId);
    if (!task) return;
    oldStatus = task.status;

    // If dragging an archived task, unarchive it first
    if (task?.metadata?.archivedAt) {
      await window.electron.ipcRenderer.invoke('TASK_UNARCHIVE', {
        projectId,
        taskIds: [task.id]
      });

      // Exit archive mode to show task in active view
      if (showArchived) {
        toggleShowArchived();
      }
    }

    // Check if dropped on a column
    if (isValidDropColumn(overId)) {
      newStatus = overId;
    } else {
      // Check if dropped on another task - move to that task's column
      const overTask = tasks.find((t) => t.id === overId);
      if (overTask) {

        // Compare visual columns
        const taskVisualColumn = getVisualColumn(task.status);
        const overTaskVisualColumn = getVisualColumn(overTask.status);

        // Same visual column: reorder within column
        if (taskVisualColumn === overTaskVisualColumn) {
          // Ensure both tasks are in the order array before reordering
          // This handles tasks that existed before ordering was enabled
          const currentColumnOrder = taskOrder?.[taskVisualColumn] ?? [];
          const activeInOrder = currentColumnOrder.includes(activeTaskId);
          const overInOrder = currentColumnOrder.includes(overId);

          if (!activeInOrder || !overInOrder) {
            // Sync the current visual order to the stored order
            // This ensures existing tasks can be reordered
            const visualOrder = tasksByStatus[taskVisualColumn].map(t => t.id);
            setTaskOrder({
              ...taskOrder,
              [taskVisualColumn]: visualOrder
            } as TaskOrderState);
          }

          // Reorder tasks within the same column using the visual column key
          reorderTasksInColumn(taskVisualColumn, activeTaskId, overId);

          if (projectId) {
            saveTaskOrder(projectId);
          }
          return;
        }

        // Different visual column: move to that task's column (status change)
        // Use the visual column key for ordering to ensure consistency
        newStatus = overTask.status;
        moveTaskToColumnTop(activeTaskId, overTaskVisualColumn, taskVisualColumn);

        // Persist task order
        if (projectId) {
          saveTaskOrder(projectId);
        }
      }
    }

    if (!newStatus || newStatus === oldStatus) return;

    // Persist status change via handleStatusChange which enforces queue capacity,
    // handles worktree cleanup dialogs, and calls processQueue() when a task
    // leaves in_progress.
    await handleStatusChange(activeTaskId, newStatus, task);

    // If user manually drags a task to in_progress, unblock the queue
    // This shows user wants to override the blocking and continue
    if (newStatus === 'in_progress') {
      unblockQueue();
    }
  }, [tasks, projectId, showArchived, toggleShowArchived, taskOrder, setTaskOrder, reorderTasksInColumn, moveTaskToColumnTop, saveTaskOrder, handleStatusChange, unblockQueue]);

  // Get project store for auto-resume and RDR toggles (per-project settings)
  const currentProject = useProjectStore((state) => state.getSelectedProject());
  const updateProject = useProjectStore((state) => state.updateProject);

  // Per-project settings for auto-resume and RDR
  const autoResumeEnabled = currentProject?.settings?.autoResumeAfterRateLimit ?? false;
  const rdrEnabled = currentProject?.settings?.rdrEnabled ?? false;

  // VS Code window state for RDR direct sending
  const [vsCodeWindows, setVsCodeWindows] = useState<Array<{ handle: number; title: string; processId: number }>>([]);
  const [selectedWindowHandle, setSelectedWindowHandle] = useState<number | null>(null);
  const [isLoadingWindows, setIsLoadingWindows] = useState(false);

  // RDR 60-second auto timer state
  const [rdrMessageInFlight, setRdrMessageInFlight] = useState(false);
  const rdrIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const rdrSkipBusyCheckRef = useRef(true); // Skip busy check on first send + idle events
  const RDR_INTERVAL_MS = 30000; // 30 seconds (reduced from 60s for faster fallback)
  const RDR_IN_FLIGHT_TIMEOUT_MS = 90000; // 90 seconds - safety net (3x polling interval to prevent double-send)

  // Load VS Code windows from system
  const loadVsCodeWindows = useCallback(async () => {
    setIsLoadingWindows(true);
    try {
      const result = await window.electronAPI.getVSCodeWindows();
      if (result.success && result.data) {
        setVsCodeWindows(result.data);
        // Auto-select first window if none selected
        if (result.data.length > 0 && selectedWindowHandle === null) {
          setSelectedWindowHandle(result.data[0].handle);
        }
      }
    } catch (error) {
      console.error('[KanbanBoard] Failed to load VS Code windows:', error);
    } finally {
      setIsLoadingWindows(false);
    }
  }, [selectedWindowHandle]);

  // Load windows on mount
  useEffect(() => {
    loadVsCodeWindows();
  }, [loadVsCodeWindows]);

  /**
   * Build detailed RDR message with task error information
   * This gives Claude Code all the info it needs to act directly
   */
  const buildRdrMessage = useCallback((data: {
    projectId: string;
    projectPath?: string;
    batches: Array<{ type: string; taskIds: string[]; taskCount: number }>;
    taskDetails: Array<{
      specId: string;
      title: string;
      description: string;
      status: string;
      reviewReason?: string;
      exitReason?: string;
      subtasks?: Array<{ name: string; status: string }>;
      errorSummary?: string;
      lastLogs?: Array<{ timestamp: string; phase: string; content: string }>;
      board?: string;
      currentPhase?: string;
      qaSignoff?: string;
      rdrAttempts?: number;
      stuckSince?: string;
    }>;
  }): string => {
    const lines: string[] = ['/auto-claude-rdr'];
    lines.push('');
    lines.push('[Auto-Claude RDR] Tasks needing intervention:');
    lines.push('');
    lines.push(`**Project UUID:** ${data.projectId}`);
    lines.push(`**Project Path:** ${data.projectPath || 'unknown'}`);
    lines.push('');

    // Build task-to-batch mapping for summary display
    const taskBatchMap: Record<string, string> = {};
    if (data.batches) {
      for (const batch of data.batches) {
        for (const taskId of batch.taskIds) {
          taskBatchMap[taskId] = batch.type;
        }
      }
    }

    // Calculate expected board from subtask progress + QA signoff status
    const getExpectedBoard = (task: typeof data.taskDetails[0]): string => {
      const subtasks = task.subtasks || [];
      if (subtasks.length === 0) return 'Planning';
      const completed = subtasks.filter(s => s.status === 'completed').length;
      if (completed === subtasks.length) {
        // QA approved → expected on Human Review (QA already validated)
        if ((task as any).qaSignoff === 'approved') return 'Human Review';
        return 'AI Review';
      }
      return 'In Progress';
    };

    // Compute per-task priority (metadata-only, NOT batch-type):
    // P1: Default — ALL tasks needing restart (any batch type)
    // P2: Recovery mode only — stuckSince (yellow outline)
    // P3: JSON error — corrupted JSON file
    // P4-6: Escalation — rdrAttempts >= 3 (P1 failed multiple times)
    const computeTaskPriority = (task: typeof data.taskDetails[0]): number => {
      if ((task.rdrAttempts || 0) >= 3) return 4;                // P4-6: escalation
      if (taskBatchMap[task.specId] === 'json_error') return 3;  // P3: corrupted JSON
      if (task.stuckSince) return 2;                              // P2: recovery mode only
      return 1;                                                    // P1: ALL other tasks
    };

    // Group tasks by priority
    const tasksByPriority = new Map<number, typeof data.taskDetails>();
    for (const task of data.taskDetails) {
      const priority = computeTaskPriority(task);
      const existing = tasksByPriority.get(priority) || [];
      tasksByPriority.set(priority, [...existing, task]);
    }

    // Priority labels
    const priorityLabels: Record<number, string> = {
      1: 'Auto-CONTINUE',
      2: 'Auto-RECOVER',
      3: 'Auto-fix JSON',
      4: 'Request Changes (Escalation P4-6)'
    };

    // Recovery Summary — grouped by priority
    lines.push('**Recovery Summary:**');
    lines.push('');

    const sortedPriorities = [...tasksByPriority.keys()].sort((a, b) => a - b);
    for (const priority of sortedPriorities) {
      const tasks = tasksByPriority.get(priority) || [];
      const attemptNote = priority === 4 ? ' (3+ attempts — investigate before restarting)' : '';
      const priorityNum = priority === 4 ? '4-6' : String(priority);
      lines.push(`### Priority ${priorityNum}: ${priorityLabels[priority]} — ${tasks.length} task${tasks.length !== 1 ? 's' : ''}${attemptNote}`);
      lines.push('');
      for (const task of tasks) {
        const completed = task.subtasks?.filter(s => s.status === 'completed').length || 0;
        const total = task.subtasks?.length || 0;
        const expected = getExpectedBoard(task);
        const current = task.board || 'Unknown';
        const boardInfo = current !== expected ? `${current} → **${expected}**` : current;
        const exitInfo = task.exitReason ? `, exited: ${task.exitReason}` : '';
        const attemptInfo = (task.rdrAttempts || 0) > 0 ? ` [attempt #${task.rdrAttempts}]` : '';
        const stuckInfo = task.stuckSince ? ` [stuck since ${new Date(task.stuckSince).toLocaleTimeString('en-US', { hour12: false })}]` : '';
        lines.push(`- ${task.specId}: ${boardInfo} (${completed}/${total}${exitInfo})${attemptInfo}${stuckInfo}`);
      }
      lines.push('');
    }

    // Detailed task info
    lines.push('**Task Details:**');
    lines.push('');

    for (const task of data.taskDetails) {
      const expected = getExpectedBoard(task);
      const current = task.board || 'Unknown';
      const boardMismatch = current !== expected;
      const priority = computeTaskPriority(task);

      const pTag = priority === 4 ? 'P4-6' : `P${priority}`;
      lines.push(`## ${task.specId}: ${task.title} [${pTag}]`);

      if (task.board) {
        const phaseLabel = task.currentPhase ? ` (${task.currentPhase})` : '';
        lines.push(`Board: ${task.board}${phaseLabel} | Expected: ${expected}${boardMismatch ? ' | **WRONG BOARD**' : ''}`);
      }

      lines.push(`Status: ${task.reviewReason || task.status} | Exit: ${task.exitReason || 'none'} | Attempts: ${task.rdrAttempts || 0}`);

      if (task.subtasks && task.subtasks.length > 0) {
        const completed = task.subtasks.filter(s => s.status === 'completed').length;
        lines.push(`Subtasks: ${completed}/${task.subtasks.length} complete`);
        const pending = task.subtasks.filter(s => s.status !== 'completed');
        if (pending.length > 0) {
          lines.push(`Pending: ${pending.map(s => s.name).join(', ')}`);
        }
      }

      if (task.errorSummary) {
        lines.push(`Error: ${task.errorSummary}`);
      }

      if (task.lastLogs && task.lastLogs.length > 0) {
        lines.push('Recent Logs:');
        for (const log of task.lastLogs) {
          const time = new Date(log.timestamp).toLocaleTimeString('en-US', { hour12: false });
          lines.push(`  [${time}] (${log.phase}) ${log.content}`);
        }
      }

      lines.push('');
    }

    lines.push('---');
    lines.push('**Recovery Instructions:**');
    lines.push('');

    const pathParam = data.projectPath ? `, projectPath: "${data.projectPath}"` : '';

    // Per-priority recovery instructions
    const p1Tasks = tasksByPriority.get(1) || [];
    const p2Tasks = tasksByPriority.get(2) || [];
    const p3Tasks = tasksByPriority.get(3) || [];
    const p4Tasks = tasksByPriority.get(4) || [];

    if (p1Tasks.length > 0) {
      lines.push(`**Priority 1: Auto-CONTINUE** (${p1Tasks.length} task${p1Tasks.length !== 1 ? 's' : ''}):`);
      lines.push('');
      // Group P1 tasks by batch type
      const p1BatchGroups: Record<string, string[]> = {};
      for (const task of p1Tasks) {
        const bt = taskBatchMap[task.specId] || 'incomplete';
        const existing = p1BatchGroups[bt] || [];
        p1BatchGroups[bt] = [...existing, task.specId];
      }
      for (const [bt, taskIds] of Object.entries(p1BatchGroups)) {
        lines.push(`  mcp__auto-claude-manager__process_rdr_batch({`);
        lines.push(`    projectId: "${data.projectId}",`);
        if (data.projectPath) {
          lines.push(`    projectPath: "${data.projectPath}",`);
        }
        lines.push(`    batchType: "${bt}",`);
        lines.push(`    fixes: [${taskIds.map(id => `{ taskId: "${id}" }`).join(', ')}]`);
        lines.push(`  })`);
        lines.push('');
      }
    }

    if (p2Tasks.length > 0) {
      lines.push(`**Priority 2: Auto-RECOVER** (${p2Tasks.length} task${p2Tasks.length !== 1 ? 's' : ''} in recovery mode):`);
      lines.push('');
      for (const task of p2Tasks) {
        lines.push(`  mcp__auto-claude-manager__recover_stuck_task({`);
        lines.push(`    projectId: "${data.projectId}",`);
        if (data.projectPath) {
          lines.push(`    projectPath: "${data.projectPath}",`);
        }
        lines.push(`    taskId: "${task.specId}",`);
        lines.push(`    autoRestart: true`);
        lines.push(`  })`);
        lines.push('');
      }
    }

    if (p3Tasks.length > 0) {
      lines.push(`**Priority 3: Auto-fix JSON** (${p3Tasks.length} task${p3Tasks.length !== 1 ? 's' : ''} with corrupted JSON):`);
      lines.push('');
      lines.push(`  mcp__auto-claude-manager__process_rdr_batch({`);
      lines.push(`    projectId: "${data.projectId}",`);
      if (data.projectPath) {
        lines.push(`    projectPath: "${data.projectPath}",`);
      }
      lines.push(`    batchType: "json_error",`);
      lines.push(`    fixes: [${p3Tasks.map(t => `{ taskId: "${t.specId}" }`).join(', ')}]`);
      lines.push(`  })`);
      lines.push('');
    }

    if (p4Tasks.length > 0) {
      lines.push(`**Priority 4-6: Request Changes** (${p4Tasks.length} task${p4Tasks.length !== 1 ? 's' : ''}, 3+ attempts — investigate before restarting):`);
      lines.push('');
      for (const task of p4Tasks) {
        lines.push(`  // First investigate: mcp__auto-claude-manager__get_task_error_details({ projectId: "${data.projectId}"${pathParam}, taskId: "${task.specId}" })`);
        lines.push(`  mcp__auto-claude-manager__submit_task_fix_request({`);
        lines.push(`    projectId: "${data.projectId}",`);
        if (data.projectPath) {
          lines.push(`    projectPath: "${data.projectPath}",`);
        }
        lines.push(`    taskId: "${task.specId}",`);
        lines.push(`    feedback: "RDR P4: ${task.rdrAttempts || 0} recovery attempts failed. Error: ${task.errorSummary || task.exitReason || 'unknown'}. Investigate root cause."`);
        lines.push(`  })`);
        lines.push('');
      }
    }

    if (p1Tasks.length > 0 || p2Tasks.length > 0) {
      lines.push('**If recovery fails**, escalate:');
      lines.push('- P1 tasks enter recovery mode → become P2 next iteration');
      lines.push('- After 3+ P1 attempts → auto-escalates to P3');
      lines.push('- P5-6 (Manual Debug / Delete & Recreate): See RDR skill docs');
      lines.push('');
    }

    lines.push('**Available MCP Tools:**');
    lines.push(`- \`mcp__auto-claude-manager__process_rdr_batch\` — P1: Auto-continue batch`);
    lines.push(`- \`mcp__auto-claude-manager__recover_stuck_task\` — P2: Recover stuck task`);
    lines.push(`- \`mcp__auto-claude-manager__submit_task_fix_request\` — P3: Request changes with fix guidance`);
    lines.push(`- \`mcp__auto-claude-manager__get_task_error_details\` — Investigate task errors`);
    lines.push(`- \`mcp__auto-claude-manager__get_rdr_batches\` — Get all recovery batches`);

    return lines.join('\n');
  }, []);

  /**
   * Handle automatic RDR processing every 60 seconds
   * Skips if a message is already in-flight (Claude Code is processing)
   */
  const handleAutoRdr = useCallback(async () => {
    // Skip if no window selected
    if (!selectedWindowHandle) {
      console.log('[RDR] Skipping auto-send - no window selected');
      return;
    }

    // Find window from selected handle to get process ID
    const selectedWindow = vsCodeWindows.find(w => w.handle === selectedWindowHandle);
    if (!selectedWindow) {
      console.log('[RDR] Skipping auto-send - selected window not found');
      return;
    }

    // Use process ID for stable matching (title changes when user switches editor tabs)
    const processId = selectedWindow.processId;

    // Check if Claude Code is busy - SKIP on first check after enable and on idle events
    if (rdrSkipBusyCheckRef.current) {
      console.log('[RDR] Skipping busy check (first send or idle event)');
      rdrSkipBusyCheckRef.current = false;
    } else {
      try {
        const busyResult = await window.electronAPI.isClaudeCodeBusy(processId);
        if (busyResult.success && busyResult.data) {
          console.log('[RDR] Skipping auto-send - Claude Code is busy');
          return;
        }
        // Claude is NOT busy — if we were in-flight, clear it (Claude finished processing)
        if (rdrMessageInFlight) {
          console.log('[RDR] Claude is idle while in-flight — clearing in-flight flag');
          setRdrMessageInFlight(false);
        }
      } catch (error) {
        console.warn('[RDR] Failed to check busy state, proceeding with send:', error);
      }
    }

    // Still in-flight after busy check — Claude is actively processing our last message
    if (rdrMessageInFlight) {
      console.log('[RDR] Message still in-flight, will retry next poll');
      return;
    }

    // Skip if no project
    if (!projectId) {
      console.log('[RDR] Skipping auto-send - no project');
      return;
    }

    console.log('[RDR] Auto-send triggered - getting batch details...');

    try {
      // Get detailed task info via IPC
      const result = await window.electronAPI.getRdrBatchDetails(projectId);

      if (!result.success || !result.data?.taskDetails?.length) {
        console.log('[RDR] No tasks needing intervention');
        return;
      }

      // Build detailed message
      const message = buildRdrMessage({ ...result.data, projectId, projectPath: result.data.projectPath });
      console.log(`[RDR] Sending detailed message with ${result.data.taskDetails.length} tasks`);

      // Mark message as in-flight
      setRdrMessageInFlight(true);

      // Send to VS Code window using process ID (stable regardless of active editor tab)
      const sendResult = await window.electronAPI.sendRdrToWindow(processId, message);

      if (sendResult.success) {
        console.log('[RDR] Auto-send successful');
        toast({
          title: t('kanban.rdrSendSuccess'),
          description: t('kanban.rdrSendSuccessDesc')
        });
      } else {
        console.error('[RDR] Auto-send failed:', sendResult.data?.error);
        setRdrMessageInFlight(false); // Allow retry immediately on failure
      }

      // Reset in-flight flag after timeout (assume Claude Code processed by then)
      setTimeout(() => {
        setRdrMessageInFlight(false);
        console.log('[RDR] In-flight timeout - ready for next message');
      }, RDR_IN_FLIGHT_TIMEOUT_MS);

    } catch (error) {
      console.error('[RDR] Auto-send error:', error);
      setRdrMessageInFlight(false);
    }
  }, [rdrMessageInFlight, selectedWindowHandle, projectId, buildRdrMessage, toast, t]);

  // EVENT-DRIVEN RDR: Check immediately on startup, then respond to idle events
  useEffect(() => {
    // Clear any existing timer
    if (rdrIntervalRef.current) {
      clearInterval(rdrIntervalRef.current);
      rdrIntervalRef.current = null;
    }

    // Only start timer if RDR is enabled AND a window is selected
    if (rdrEnabled && selectedWindowHandle) {
      console.log(`[RDR] Starting event-driven RDR - immediate check + idle event triggers`);

      // IMMEDIATE CHECK: Catch existing tasks needing intervention
      handleAutoRdr();

      // EVENT-DRIVEN: Subscribe to 'claude-code-idle' IPC event for sequential batching
      const idleListener = (_event: any, data: { from: string; to: string; timestamp: number }) => {
        console.log(`[RDR] EVENT: Claude Code became idle (${data.from} -> ${data.to})`);

        // Clear in-flight flag — idle event proves Claude finished processing
        setRdrMessageInFlight(false);

        // Skip busy check - the idle event already proves Claude is idle
        // Re-checking creates a race condition where state changes between emit and check
        rdrSkipBusyCheckRef.current = true;
        handleAutoRdr();
      };

      // @ts-ignore - electron API exists in renderer
      window.electron?.ipcRenderer.on('claude-code-idle', idleListener);

      // FALLBACK POLLING: Set up 60-second interval as fallback if event system fails
      rdrIntervalRef.current = setInterval(() => {
        console.log('[RDR] Fallback polling check (30s interval)');
        handleAutoRdr();
      }, RDR_INTERVAL_MS);

      // Cleanup on unmount or dependency change
      return () => {
        // Remove IPC listener
        // @ts-ignore
        window.electron?.ipcRenderer.removeListener('claude-code-idle', idleListener);

        // Clear timer and reset skip flag for next enable
        if (rdrIntervalRef.current) {
          clearInterval(rdrIntervalRef.current);
          rdrIntervalRef.current = null;
          console.log('[RDR] Auto-send timer stopped');
        }
        rdrSkipBusyCheckRef.current = true; // Reset for next enable
      };
    } else {
      console.log('[RDR] Auto-send timer not started (RDR disabled or no window selected)');
    }
  }, [rdrEnabled, selectedWindowHandle, handleAutoRdr]);

  // Detect task regression (started → backlog) and trigger immediate RDR
  useEffect(() => {
    if (!window.electronAPI?.onTaskRegressionDetected) return;

    const cleanup = window.electronAPI.onTaskRegressionDetected((data) => {
      if (data.projectId !== projectId) return;

      console.warn(`[KanbanBoard] Task regression: ${data.specId} (${data.oldStatus} → ${data.newStatus})`);

      toast({
        title: t('tasks:kanban.rdrTaskRegression', 'Task Regression'),
        description: t('tasks:kanban.rdrTaskRegressionDesc', { specId: data.specId, defaultValue: `${data.specId} went back to planning after being started` }),
        variant: 'destructive'
      });

      // Trigger immediate RDR check (bypass 60s timer)
      handleAutoRdr();
    });
    return cleanup;
  }, [projectId, toast, t, handleAutoRdr]);

  // Helper function to start a task with retry logic
  const startTaskWithRetry = useCallback(async (taskId: string, maxRetries = 3, delayMs = 2000) => {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        await startTask(taskId);
        console.log(`[KanbanBoard] Started task ${taskId} (attempt ${attempt})`);
        return true; // Success
      } catch (error) {
        console.error(`[KanbanBoard] Failed to start task ${taskId} (attempt ${attempt}/${maxRetries}):`, error);
        if (attempt < maxRetries) {
          console.log(`[KanbanBoard] Retrying task ${taskId} in ${delayMs}ms...`);
          await new Promise(resolve => setTimeout(resolve, delayMs));
        }
      }
    }
    console.error(`[KanbanBoard] All ${maxRetries} attempts failed for task ${taskId}`);
    return false; // All retries failed
  }, []);

  // Handle auto-resume toggle - when enabled, immediately resume all incomplete tasks
  const handleAutoResumeToggle = async (checked: boolean) => {
    // Update per-project setting
    if (currentProject) {
      const updatedSettings = {
        ...currentProject.settings,
        autoResumeAfterRateLimit: checked
      };
      updateProject(currentProject.id, { settings: updatedSettings });
      // Persist to storage via IPC
      await window.electronAPI.updateProjectSettings(currentProject.id, updatedSettings);
    }

    // When turning ON, resume all incomplete tasks in human_review (those showing "Needs Resume")
    if (checked) {
      const incompleteTasks = tasks.filter(task => isIncompleteHumanReview(task));

      if (incompleteTasks.length > 0) {
        console.log(`[KanbanBoard] Auto-resume enabled - resuming ${incompleteTasks.length} incomplete tasks`);

        // Start all tasks with retry logic (run in parallel)
        const results = await Promise.all(
          incompleteTasks.map(task => startTaskWithRetry(task.id))
        );

        const successCount = results.filter(Boolean).length;
        const failCount = results.length - successCount;
        console.log(`[KanbanBoard] Auto-resume complete: ${successCount} succeeded, ${failCount} failed`);
      } else {
        console.log('[KanbanBoard] Auto-resume enabled - no incomplete tasks to resume');
      }
    }
  };

  // Handle RDR (Recover Debug Resend) toggle - when enabled, process stuck/errored tasks
  const handleRdrToggle = async (checked: boolean) => {
    // Update per-project setting
    if (currentProject) {
      const updatedSettings = {
        ...currentProject.settings,
        rdrEnabled: checked
      };
      updateProject(currentProject.id, { settings: updatedSettings });
      // Persist to storage via IPC
      await window.electronAPI.updateProjectSettings(currentProject.id, updatedSettings);
    }

    // RDR toggle only enables/disables monitoring - NO automatic task modification
    // Task recovery is handled by the RDR message pipeline (polling + idle events)
    // which reports tasks needing intervention via messages to Claude Code
    if (checked) {
      console.log('[KanbanBoard] RDR enabled - monitoring started (no automatic task changes)');
    }
  };

  // Handle manual RDR ping - sends message directly to selected VS Code window
  const handlePingRdr = async () => {
    // Get ALL tasks in Human Review (less restrictive filter than toggle)
    const humanReviewTasks = tasks.filter(task => task.status === 'human_review');

    console.log(`[KanbanBoard] Ping RDR - ${humanReviewTasks.length} tasks in Human Review`);

    if (humanReviewTasks.length === 0) {
      toast({
        title: t('kanban.rdrPingNoTasks'),
        description: t('kanban.rdrPingNoTasksDesc'),
        variant: 'default'
      });
      return;
    }

    // Check if a window is selected for direct sending
    if (selectedWindowHandle) {
      // Find window title from selected handle
      const selectedWindow = vsCodeWindows.find(w => w.handle === selectedWindowHandle);
      if (!selectedWindow) {
        toast({
          title: t('kanban.rdrSendFailed'),
          description: 'Selected window not found',
          variant: 'destructive'
        });
        return;
      }

      // Use process ID for stable matching (title changes when user switches editor tabs)
      const processId = selectedWindow.processId;

      // Send directly to VS Code window with detailed message
      toast({
        title: t('kanban.rdrSending'),
        description: t('kanban.rdrSendingDesc', { count: humanReviewTasks.length })
      });

      try {
        // Get detailed batch info for the message
        const batchResult = await window.electronAPI.getRdrBatchDetails(projectId);
        let message: string;

        if (batchResult.success && batchResult.data?.taskDetails?.length) {
          message = buildRdrMessage({ ...batchResult.data, projectId, projectPath: batchResult.data.projectPath });
        } else {
          // Fallback to simple message if no detailed info available
          message = 'Check RDR batches and fix errored tasks';
        }

        const result = await window.electronAPI.sendRdrToWindow(processId, message);

        if (result.success) {
          toast({
            title: t('kanban.rdrSendSuccess'),
            description: t('kanban.rdrSendSuccessDesc'),
            variant: 'default'
          });
          console.log(`[KanbanBoard] RDR message sent to window handle ${selectedWindowHandle}`);
        } else {
          toast({
            title: t('kanban.rdrSendFailed'),
            description: result.data?.error || t('kanban.rdrSendFailedDesc'),
            variant: 'destructive'
          });
        }
      } catch (error) {
        console.error('[KanbanBoard] Send RDR error:', error);
        toast({
          title: t('kanban.rdrSendFailed'),
          description: error instanceof Error ? error.message : t('kanban.rdrSendFailedDesc'),
          variant: 'destructive'
        });
      }
    } else {
      // Fallback: write signal file for external monitoring
      toast({
        title: t('kanban.rdrPinging'),
        description: t('kanban.rdrPingingDesc', { count: humanReviewTasks.length })
      });

      try {
        const result = await window.electronAPI.pingRdrImmediate(projectId, humanReviewTasks);

        if (result.success && result.data) {
          toast({
            title: t('kanban.rdrPingSuccess'),
            description: t('kanban.rdrPingSuccessDesc', { count: result.data.taskCount }),
            variant: 'default'
          });
          console.log(`[KanbanBoard] RDR signal file written: ${result.data.signalPath}`);
        } else {
          toast({
            title: t('kanban.rdrPingFailed'),
            description: result.error || t('kanban.rdrPingFailedDesc'),
            variant: 'destructive'
          });
        }
      } catch (error) {
        console.error('[KanbanBoard] Ping RDR error:', error);
        toast({
          title: t('kanban.rdrPingFailed'),
          description: error instanceof Error ? error.message : t('kanban.rdrPingFailedDesc'),
          variant: 'destructive'
        });
      }
    }
  };

  // Track which tasks we've already attempted to auto-resume (to prevent loops)
  const autoResumedTasksRef = useRef<Set<string>>(new Set());

  // Auto-resume on mount/reconnect if toggle is already ON
  // Also re-runs when tasks load/change to catch tasks that weren't loaded initially
  useEffect(() => {
    if (!autoResumeEnabled || tasks.length === 0) return;

    const incompleteTasks = tasks.filter(task =>
      isIncompleteHumanReview(task) && !autoResumedTasksRef.current.has(task.id)
    );

    if (incompleteTasks.length > 0) {
      console.log(`[KanbanBoard] Auto-resume active - resuming ${incompleteTasks.length} incomplete tasks`);

      // Mark these tasks as attempted (to prevent re-resuming)
      incompleteTasks.forEach(task => autoResumedTasksRef.current.add(task.id));

      // Start all tasks with retry logic (run in parallel)
      Promise.all(
        incompleteTasks.map(task => startTaskWithRetry(task.id))
      ).then(results => {
        const successCount = results.filter(Boolean).length;
        const failCount = results.length - successCount;
        console.log(`[KanbanBoard] Auto-resume complete: ${successCount} succeeded, ${failCount} failed`);
      });
    }
  }, [autoResumeEnabled, tasks, startTaskWithRetry]); // Re-run when toggle changes OR tasks load

  // Clear the auto-resumed set when toggle is turned OFF (so tasks can be resumed again when turned ON)
  useEffect(() => {
    if (!autoResumeEnabled) {
      autoResumedTasksRef.current.clear();
    }
  }, [autoResumeEnabled]);

  return (
    <div className="flex h-full flex-col">
      {/* Kanban header with refresh button, expand all, auto-resume, and RDR */}
      <div className="flex items-center justify-between px-6 pt-4 pb-2">
        <div className="flex items-center gap-2">
          {/* Expand All button - appears when 3+ columns are collapsed */}
          {collapsedColumnCount >= 3 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleExpandAll}
              className="gap-2 text-muted-foreground hover:text-foreground"
            >
              <ChevronsRight className="h-4 w-4" />
              {t('tasks:kanban.expandAll')}
            </Button>
          )}
        </div>
        <div className="flex items-center gap-4">
          {/* Auto-Resume Section */}
          <div className="flex items-center gap-3">
            {/* Toggle 1: Auto Resume (on limit reset) */}
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center gap-1.5">
                  <Switch
                    id="kanban-auto-resume-limit"
                    checked={autoResumeEnabled}
                    onCheckedChange={handleAutoResumeToggle}
                    className="scale-90"
                  />
                  <div className="flex flex-col text-[10px] leading-tight text-muted-foreground">
                    <span>{t('kanban.arLimitReset')}</span>
                    <span className="text-muted-foreground/70">{t('kanban.arLimitResetSub')}</span>
                  </div>
                </div>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-xs">
                <p>{t('kanban.autoResumeTooltip')}</p>
              </TooltipContent>
            </Tooltip>

            {/* RDR Section with accent border */}
            <div className="relative border border-primary/30 rounded-lg px-3 py-2 mt-1">
              {/* Legend-style label - positioned above border */}
              <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 bg-background px-2 text-[10px] uppercase tracking-wider text-primary whitespace-nowrap">
                {t('kanban.autoResumeHeader')}
              </span>

              <div className="flex items-center gap-2">
                {/* Toggle: RDR - Recover Debug Resend */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-1.5">
                      <Switch
                        id="kanban-auto-rdr"
                        checked={rdrEnabled}
                        onCheckedChange={handleRdrToggle}
                        className="scale-90"
                      />
                      <div className="flex flex-col text-[10px] leading-tight text-muted-foreground">
                        <span className="font-medium">RDR</span>
                        <span className="text-muted-foreground/70">Recover / Continue</span>
                        <span className="text-muted-foreground/70">Debug</span>
                        <span className="text-muted-foreground/70">Resend</span>
                      </div>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-xs">
                    <p>{t('kanban.rdrTooltip')}</p>
                  </TooltipContent>
                </Tooltip>

                {/* VS Code Window Selector for RDR */}
                <div className="flex items-center gap-1">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={loadVsCodeWindows}
                        disabled={isLoadingWindows}
                        className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                      >
                        <RefreshCw className={cn("h-3 w-3", isLoadingWindows && "animate-spin")} />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom">
                      <p>{t('kanban.rdrRefreshWindows')}</p>
                    </TooltipContent>
                  </Tooltip>

                  <Select
                    value={selectedWindowHandle?.toString() ?? ''}
                    onValueChange={(value) => setSelectedWindowHandle(value ? parseInt(value, 10) : null)}
                  >
                    <SelectTrigger className="h-7 w-[140px] text-xs">
                      <SelectValue placeholder={t('kanban.rdrSelectWindow')} />
                    </SelectTrigger>
                    <SelectContent>
                      {vsCodeWindows.map((win) => (
                        <SelectItem key={win.handle} value={win.handle.toString()}>
                          <span className="truncate max-w-[120px]" title={win.title}>
                            {win.title.length > 25 ? `${win.title.substring(0, 25)}...` : win.title}
                          </span>
                        </SelectItem>
                      ))}
                      {vsCodeWindows.length === 0 && (
                        <SelectItem value="none" disabled>
                          {t('kanban.rdrNoWindows')}
                        </SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                </div>

                {/* Manual Ping RDR Button */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handlePingRdr}
                      disabled={!selectedWindowHandle}
                      className={cn(
                        "h-7 w-7 p-0",
                        selectedWindowHandle
                          ? "text-yellow-500 hover:text-yellow-400"
                          : "text-muted-foreground/50"
                      )}
                    >
                      <Zap className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-xs">
                    <p>{selectedWindowHandle ? t('kanban.rdrPingTooltip') : t('kanban.rdrSelectWindowFirst')}</p>
                  </TooltipContent>
                </Tooltip>
              </div>
            </div>
          </div>

          {/* Refresh Button */}
          {onRefresh && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onRefresh}
              disabled={isRefreshing}
              className="gap-2 text-muted-foreground hover:text-foreground"
            >
              <RefreshCw className={cn("h-4 w-4", isRefreshing && "animate-spin")} />
              {isRefreshing ? t('common:buttons.refreshing') : t('tasks:refreshTasks')}
            </Button>
          )}
        </div>
      </div>

      {/* Archive List View - Show when in archive mode */}
      {showArchived ? (
        <div className="flex flex-1 flex-col p-6 overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-semibold">{t('tasks:archivedTasks')}</h2>
            <Button onClick={toggleShowArchived} variant="outline">
              {t('tasks:exitArchiveMode')}
            </Button>
          </div>
          <ScrollArea className="flex-1 h-full pr-4">
            <div className="flex flex-col gap-3 pb-4">
              {filteredTasks.filter(t => t.metadata?.archivedAt).length === 0 ? (
                <div className="text-center text-muted-foreground py-12">
                  {t('tasks:noArchivedTasks')}
                </div>
              ) : (
                filteredTasks.filter(t => t.metadata?.archivedAt).map(task => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    onClick={() => onTaskClick?.(task)}
                    onStatusChange={(newStatus) => handleStatusChange(task.id, newStatus, task)}
                    onRefresh={onRefresh}
                    rdrEnabled={rdrEnabled}
                  />
                ))
              )}
            </div>
          </ScrollArea>
        </div>
      ) : (
        /* Kanban columns */
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
        >
        <div className="flex flex-1 gap-4 overflow-x-auto p-6">
          {TASK_STATUS_COLUMNS.map((status) => (
            <DroppableColumn
              key={status}
              status={status}
              tasks={tasksByStatus[status]}
              onTaskClick={onTaskClick}
              onStatusChange={handleStatusChange}
              onRefresh={onRefresh}
              isOver={overColumnId === status}
              onAddClick={status === 'backlog' ? onNewTaskClick : undefined}
              onQueueAll={status === 'backlog' ? handleQueueAll : undefined}
              onQueueSettings={status === 'queue' ? () => {
                // Only open modal if we have a valid projectId
                if (!projectId) return;
                queueSettingsProjectIdRef.current = projectId;
                setShowQueueSettings(true);
              } : undefined}
              onArchiveAll={status === 'done' ? handleArchiveAll : undefined}
              maxParallelTasks={status === 'in_progress' ? maxParallelTasks : undefined}
              archivedCount={status === 'done' ? archivedCount : undefined}
              showArchived={status === 'done' ? showArchived : undefined}
              onToggleArchived={status === 'done' ? toggleShowArchived : undefined}
              selectedTaskIds={selectedTaskIds}
              onSelectAll={() => selectAllTasks(status)}
              onDeselectAll={deselectAllTasks}
              onToggleSelect={toggleTaskSelection}
              isCollapsed={columnPreferences?.[status]?.isCollapsed}
              onToggleCollapsed={() => handleToggleColumnCollapsed(status)}
              columnWidth={columnPreferences?.[status]?.width}
              isResizing={resizingColumn === status}
              onResizeStart={(startX) => handleResizeStart(status, startX)}
              onResizeEnd={handleResizeEnd}
              isLocked={columnPreferences?.[status]?.isLocked}
              onToggleLocked={() => handleToggleColumnLocked(status)}
              rdrEnabled={rdrEnabled}
              queueBlocked={status === 'in_progress' ? queueBlocked : undefined}
              queueBlockReason={status === 'in_progress' ? queueBlockReason : undefined}
            />
          ))}
        </div>

        {/* Drag overlay - enhanced visual feedback */}
        <DragOverlay>
          {activeTask ? (
            <div className="drag-overlay-card">
              <TaskCard task={activeTask} onClick={() => {}} rdrEnabled={rdrEnabled} />
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>
      )}

      {selectedTaskIds.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
          <div className="flex items-center gap-3 px-4 py-3 rounded-2xl border border-border bg-card shadow-lg backdrop-blur-sm">
            <span className="text-sm font-medium text-foreground">
              {t('kanban.selectedCountOther', { count: selectedTaskIds.size })}
            </span>
            <div className="w-px h-5 bg-border" />
            <Button
              variant="default"
              size="sm"
              className="gap-2"
              onClick={handleOpenBulkPRDialog}
            >
              <GitPullRequest className="h-4 w-4" />
              {t('kanban.createPRs')}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="gap-2 text-destructive hover:text-destructive hover:bg-destructive/10"
              onClick={handleOpenDeleteConfirm}
            >
              <Trash2 className="h-4 w-4" />
              {t('kanban.deleteSelected')}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="gap-2 text-muted-foreground hover:text-foreground"
              onClick={handleBulkToggleRdr}
            >
              {allSelectedRdrDisabled ? <Shield className="h-4 w-4" /> : <ShieldOff className="h-4 w-4" />}
              {allSelectedRdrDisabled ? 'Enable RDR' : 'Disable RDR'}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="gap-2 text-muted-foreground hover:text-foreground"
              onClick={deselectAllTasks}
            >
              <X className="h-4 w-4" />
              {t('kanban.clearSelection')}
            </Button>
          </div>
        </div>
      )}

      {/* Delete confirmation dialog */}
      <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <AlertDialogContent className="sm:max-w-[500px]">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-destructive">
              <Trash2 className="h-5 w-5" />
              {t('kanban.deleteConfirmTitle')}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t('kanban.deleteConfirmDescription')}
            </AlertDialogDescription>
          </AlertDialogHeader>

          {/* Task List Preview */}
          <div className="space-y-2">
            <label className="text-sm font-medium">{t('kanban.tasksToDelete')}</label>
            <ScrollArea className="h-32 rounded-md border border-border p-2">
              <div className="space-y-1">
                {selectedTasks.map((task, idx) => (
                  <div
                    key={task.id}
                    className="flex items-center gap-2 text-sm py-1 px-2 rounded hover:bg-muted/50"
                  >
                    <span className="text-muted-foreground">{idx + 1}.</span>
                    <span className="truncate">{task.title}</span>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>

          {/* Warning message */}
          <p className="text-sm text-destructive">
            {t('kanban.deleteWarning')}
          </p>

          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>
              {t('common:buttons.cancel')}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  {t('common:buttons.deleting')}
                </>
              ) : (
                t('kanban.deleteConfirmButton', { count: selectedTaskIds.size })
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Worktree cleanup confirmation dialog */}
      <WorktreeCleanupDialog
        open={worktreeCleanupDialog.open}
        taskTitle={worktreeCleanupDialog.taskTitle}
        worktreePath={worktreeCleanupDialog.worktreePath}
        isProcessing={worktreeCleanupDialog.isProcessing}
        error={worktreeCleanupDialog.error}
        onOpenChange={(open) => {
          if (!open && !worktreeCleanupDialog.isProcessing) {
            setWorktreeCleanupDialog(prev => ({ ...prev, open: false, error: undefined }));
          }
        }}
        onConfirm={handleWorktreeCleanupConfirm}
      />

      {/* Queue Settings Modal */}
      {(queueSettingsProjectIdRef.current || projectId) && (
        <QueueSettingsModal
          open={showQueueSettings}
          onOpenChange={(open) => {
            setShowQueueSettings(open);
            if (!open) {
              queueSettingsProjectIdRef.current = null;
            }
          }}
          projectId={queueSettingsProjectIdRef.current || projectId || ''}
          currentMaxParallel={maxParallelTasks}
          onSave={handleSaveQueueSettings}
        />
      )}

      {/* Bulk PR creation dialog */}
      <BulkPRDialog
        open={bulkPRDialogOpen}
        tasks={selectedTasks}
        onOpenChange={setBulkPRDialogOpen}
        onComplete={handleBulkPRComplete}
      />
    </div>
  );
}
