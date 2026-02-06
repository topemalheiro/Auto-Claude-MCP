import { useState, useMemo, memo, useEffect, useCallback, useRef } from 'react';
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
import { Plus, Inbox, Loader2, Eye, CheckCircle2, Archive, RefreshCw, GitPullRequest, X, Zap } from 'lucide-react';
import { Checkbox } from './ui/checkbox';
import { ScrollArea } from './ui/scroll-area';
import { Button } from './ui/button';
import { Switch } from './ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Tooltip, TooltipContent, TooltipTrigger } from './ui/tooltip';
import { TaskCard } from './TaskCard';
import { SortableTaskCard } from './SortableTaskCard';
import { TASK_STATUS_COLUMNS, TASK_STATUS_LABELS } from '../../shared/constants';
import { cn } from '../lib/utils';
import { persistTaskStatus, forceCompleteTask, archiveTasks, useTaskStore, startTask, isIncompleteHumanReview } from '../stores/task-store';
import { useProjectStore } from '../stores/project-store';
import { useToast } from '../hooks/use-toast';
import { WorktreeCleanupDialog } from './WorktreeCleanupDialog';
import { BulkPRDialog } from './BulkPRDialog';
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
  archivedCount?: number;
  showArchived?: boolean;
  onToggleArchived?: () => void;
  // Selection props for human_review column
  selectedTaskIds?: Set<string>;
  onSelectAll?: () => void;
  onDeselectAll?: () => void;
  onToggleSelect?: (taskId: string) => void;
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
  if (prevProps.archivedCount !== nextProps.archivedCount) return false;
  if (prevProps.showArchived !== nextProps.showArchived) return false;
  if (prevProps.onToggleArchived !== nextProps.onToggleArchived) return false;
  if (prevProps.onSelectAll !== nextProps.onSelectAll) return false;
  if (prevProps.onDeselectAll !== nextProps.onDeselectAll) return false;
  if (prevProps.onToggleSelect !== nextProps.onToggleSelect) return false;

  // Compare selectedTaskIds Set
  if (prevProps.selectedTaskIds !== nextProps.selectedTaskIds) {
    // If one is undefined and other isn't, different
    if (!prevProps.selectedTaskIds || !nextProps.selectedTaskIds) return false;
    // Compare Set contents
    if (prevProps.selectedTaskIds.size !== nextProps.selectedTaskIds.size) return false;
    for (const id of prevProps.selectedTaskIds) {
      if (!nextProps.selectedTaskIds.has(id)) return false;
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

const DroppableColumn = memo(function DroppableColumn({ status, tasks, onTaskClick, onStatusChange, onRefresh, isOver, onAddClick, onArchiveAll, archivedCount, showArchived, onToggleArchived, selectedTaskIds, onSelectAll, onDeselectAll, onToggleSelect }: DroppableColumnProps) {
  const { t } = useTranslation(['tasks', 'common']);
  const { setNodeRef } = useDroppable({
    id: status
  });

  // Calculate selection state for human_review column
  const isHumanReview = status === 'human_review';
  const selectedCount = selectedTaskIds?.size ?? 0;
  const taskCount = tasks.length;
  const isAllSelected = isHumanReview && taskCount > 0 && selectedCount === taskCount;
  const isSomeSelected = isHumanReview && selectedCount > 0 && selectedCount < taskCount;

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

  // Create stable onToggleSelect handlers for each task (only for human_review column)
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
      />
    ));
  }, [tasks, onClickHandlers, onStatusChangeHandlers, onToggleSelectHandlers, selectedTaskIds]);

  const getColumnBorderColor = (): string => {
    switch (status) {
      case 'backlog':
        return 'column-backlog';
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

  return (
    <div
      ref={setNodeRef}
      className={cn(
        'flex min-w-72 max-w-[30rem] flex-1 flex-col rounded-xl border border-white/5 bg-linear-to-b from-secondary/30 to-transparent backdrop-blur-sm transition-all duration-200',
        getColumnBorderColor(),
        'border-t-2',
        isOver && 'drop-zone-highlight'
      )}
    >
      {/* Column header - enhanced styling */}
      <div className="flex items-center justify-between p-4 border-b border-white/5">
        <div className="flex items-center gap-2.5">
          {/* Select All checkbox for human_review column */}
          {isHumanReview && onSelectAll && onDeselectAll && (
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
          <span className="column-count-badge">
            {tasks.length}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {status === 'backlog' && onAddClick && (
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
  );
}, droppableColumnPropsAreEqual);

export function KanbanBoard({ tasks, onTaskClick, onNewTaskClick, onRefresh, isRefreshing }: KanbanBoardProps) {
  const { t } = useTranslation(['tasks', 'dialogs', 'common']);
  const { toast } = useToast();
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [overColumnId, setOverColumnId] = useState<string | null>(null);
  const { showArchived, toggleShowArchived } = useViewState();

  // Selection state for bulk actions (Human Review column)
  const [selectedTaskIds, setSelectedTaskIds] = useState<Set<string>>(new Set());

  // Bulk PR dialog state
  const [bulkPRDialogOpen, setBulkPRDialogOpen] = useState(false);

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

  // Calculate archived count for Done column button
  const archivedCount = useMemo(() =>
    tasks.filter(t => t.metadata?.archivedAt).length,
    [tasks]
  );

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

  // Prune stale IDs when tasks move out of human_review column
  useEffect(() => {
    const validIds = new Set(tasksByStatus.human_review.map(t => t.id));
    setSelectedTaskIds(prev => {
      const filtered = new Set([...prev].filter(id => validIds.has(id)));
      return filtered.size === prev.size ? prev : filtered;
    });
  }, [tasksByStatus.human_review]);

  // Selection callbacks for bulk actions (Human Review column)
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

  const selectAllTasks = useCallback(() => {
    const humanReviewTasks = tasksByStatus.human_review;
    const allIds = new Set(humanReviewTasks.map(t => t.id));
    setSelectedTaskIds(allIds);
  }, [tasksByStatus.human_review]);

  const deselectAllTasks = useCallback(() => {
    setSelectedTaskIds(new Set());
  }, []);

  // Get selected task objects for the BulkPRDialog
  const selectedTasks = useMemo(() => {
    return tasksByStatus.human_review.filter(task => selectedTaskIds.has(task.id));
  }, [tasksByStatus.human_review, selectedTaskIds]);

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
  const handleStatusChange = async (taskId: string, newStatus: TaskStatus, providedTask?: Task) => {
    const task = providedTask || tasks.find(t => t.id === taskId);
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

  // Get task order actions from store
  const reorderTasksInColumn = useTaskStore((state) => state.reorderTasksInColumn);
  const moveTaskToColumnTop = useTaskStore((state) => state.moveTaskToColumnTop);
  const saveTaskOrderToStorage = useTaskStore((state) => state.saveTaskOrder);
  const loadTaskOrder = useTaskStore((state) => state.loadTaskOrder);
  const setTaskOrder = useTaskStore((state) => state.setTaskOrder);

  // Get projectId from tasks (all tasks in KanbanBoard share the same project)
  const projectId = useMemo(() => tasks[0]?.projectId ?? null, [tasks]);

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
      in_progress: [],
      ai_review: [],
      human_review: [],
      pr_created: [],
      done: [],
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

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveTask(null);
    setOverColumnId(null);

    if (!over) return;

    const activeTaskId = active.id as string;
    const overId = over.id as string;

    // Find the task being dragged
    const task = tasks.find((t) => t.id === activeTaskId);

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
      const newStatus = overId;

      if (task && task.status !== newStatus) {
        // Move task to top of target column's order array
        moveTaskToColumnTop(activeTaskId, newStatus, task.status);

        // Persist task order
        if (projectId) {
          saveTaskOrder(projectId);
        }

        // Persist status change to file and update local state
        handleStatusChange(activeTaskId, newStatus, task).catch((err) =>
          console.error('[KanbanBoard] Status change failed:', err)
        );
      }
      return;
    }

    // Check if dropped on another task
    const overTask = tasks.find((t) => t.id === overId);
    if (overTask) {
      const task = tasks.find((t) => t.id === activeTaskId);
      if (!task) return;

      // Compare visual columns (pr_created maps to 'done' visually)
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
      moveTaskToColumnTop(activeTaskId, overTaskVisualColumn, taskVisualColumn);

      // Persist task order
      if (projectId) {
        saveTaskOrder(projectId);
      }

      handleStatusChange(activeTaskId, overTask.status, task).catch((err) =>
        console.error('[KanbanBoard] Status change failed:', err)
      );
    }
  };

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
  const RDR_INTERVAL_MS = 30000; // 30 seconds (reduced from 60s for faster fallback)
  const RDR_IN_FLIGHT_TIMEOUT_MS = 30000; // 30 seconds before allowing next message

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
    }>;
  }): string => {
    const lines: string[] = ['[Auto-Claude RDR] Tasks needing intervention:'];
    lines.push('');
    lines.push(`**Project UUID:** ${data.projectId}`);
    lines.push('');

    // Summary: Show batch categorization
    if (data.batches && data.batches.length > 0) {
      lines.push('**Recovery Batches:**');
      for (const batch of data.batches) {
        const taskList = batch.taskIds.join(', ');
        lines.push(`- **${batch.type}** (${batch.taskCount} tasks): ${taskList}`);
      }
      lines.push('');
    }

    lines.push('**Task Details:**');
    lines.push('');

    for (const task of data.taskDetails) {
      lines.push(`## ${task.specId}: ${task.title}`);
      lines.push(`Status: ${task.reviewReason || task.status} | Exit: ${task.exitReason || 'none'}`);

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

      lines.push('');
    }

    lines.push('---');
    lines.push('**Recovery Instructions:**');
    lines.push('');
    lines.push(`Project UUID: \`${data.projectId}\``);
    lines.push('');
    lines.push('**Step 1: Get batch details**');
    lines.push('```typescript');
    lines.push(`const batches = await get_rdr_batches("${data.projectId}");`);
    lines.push('```');
    lines.push('');
    lines.push('**Step 2: Process each batch type**');
    lines.push('```typescript');
    if (data.batches && data.batches.length > 0) {
      for (const batch of data.batches) {
        lines.push(`// ${batch.type}: ${batch.taskIds.join(', ')}`);
        lines.push(`await process_rdr_batch("${data.projectId}", "${batch.type}", [`);
        for (const taskId of batch.taskIds) {
          lines.push(`  { taskId: "${taskId}" },`);
        }
        lines.push(']);');
        lines.push('');
      }
    } else {
      lines.push('// Use process_rdr_batch for each batch type');
      lines.push(`await process_rdr_batch("${data.projectId}", "incomplete", fixes);`);
    }
    lines.push('```');
    lines.push('');
    lines.push('**Available MCP Tools:**');
    lines.push('- `get_rdr_batches(projectId)` - Get all recovery batches');
    lines.push('- `process_rdr_batch(projectId, batchType, fixes)` - Auto-recover batch');
    lines.push('- `get_task_error_details(projectId, taskId)` - Get detailed error logs');
    lines.push('- `submit_task_fix_request(projectId, taskId, feedback)` - Manual fix request');

    return lines.join('\n');
  }, []);

  /**
   * Handle automatic RDR processing every 60 seconds
   * Skips if a message is already in-flight (Claude Code is processing)
   */
  const handleAutoRdr = useCallback(async () => {
    // Skip if message is in-flight (Claude Code still processing previous request)
    if (rdrMessageInFlight) {
      console.log('[RDR] Skipping auto-send - message in flight');
      return;
    }

    // Skip if no window selected
    if (!selectedWindowHandle) {
      console.log('[RDR] Skipping auto-send - no window selected');
      return;
    }

    // Find window title from selected handle
    const selectedWindow = vsCodeWindows.find(w => w.handle === selectedWindowHandle);
    if (!selectedWindow) {
      console.log('[RDR] Skipping auto-send - selected window not found');
      return;
    }

    // Extract project name from title (e.g., "CV Project - Visual Studio Code" → "CV Project")
    const titlePattern = selectedWindow.title.split(' - ')[0];
    console.log(`[RDR] Using title pattern: "${titlePattern}"`);

    // NEW: Check if Claude Code is busy (in a prompt loop)
    try {
      const busyResult = await window.electronAPI.isClaudeCodeBusy(titlePattern);
      if (busyResult.success && busyResult.data) {
        console.log('[RDR] Skipping auto-send - Claude Code is busy (in prompt loop)');
        return;
      }
    } catch (error) {
      console.warn('[RDR] Failed to check busy state, proceeding with send:', error);
      // Continue with send on error (graceful degradation)
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
      const message = buildRdrMessage({ ...result.data, projectId });
      console.log(`[RDR] Sending detailed message with ${result.data.taskDetails.length} tasks`);

      // Mark message as in-flight
      setRdrMessageInFlight(true);

      // Send to VS Code window using title pattern (not handle to avoid stale handle errors)
      const sendResult = await window.electronAPI.sendRdrToWindow(titlePattern, message);

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
        console.log(`[RDR] 🚀 EVENT: Claude Code became idle (${data.from} -> ${data.to})`);
        console.log('[RDR]    🔄 Triggering next RDR check for sequential batching');

        // Trigger RDR check immediately when Claude finishes processing
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

        // Clear timer
        if (rdrIntervalRef.current) {
          clearInterval(rdrIntervalRef.current);
          rdrIntervalRef.current = null;
          console.log('[RDR] Auto-send timer stopped');
        }
      };
    } else {
      console.log('[RDR] Auto-send timer not started (RDR disabled or no window selected)');
    }
  }, [rdrEnabled, selectedWindowHandle, handleAutoRdr]);

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

    // When turning ON, auto-recover ALL stuck tasks and trigger RDR processing
    if (checked) {
      console.log('[KanbanBoard] RDR enabled - triggering auto-recovery for all stuck tasks');

      // FIRST: Auto-recover tasks with start_requested status or incomplete subtasks
      try {
        const recoverResult = await window.electronAPI.autoRecoverAllTasks(projectId);

        if (recoverResult.success && recoverResult.data) {
          const { recovered, taskIds } = recoverResult.data;
          console.log(`[KanbanBoard] Auto-recovered ${recovered} tasks:`, taskIds);

          if (recovered > 0) {
            toast({
              title: `Auto-recovered ${recovered} tasks`,
              description: 'Tasks have been moved to correct board states',
              variant: 'default'
            });
          }
        } else {
          console.warn('[KanbanBoard] Auto-recovery failed:', recoverResult.error);
        }
      } catch (error) {
        console.error('[KanbanBoard] Failed to auto-recover tasks:', error);
      }

      // SECOND: Also trigger RDR processing for manual/MCP intervention
      const tasksNeedingHelp = tasks.filter(task =>
        task.status === 'human_review' &&
        (task.reviewReason === 'errors' ||
         task.reviewReason === 'qa_rejected' ||
         isIncompleteHumanReview(task))
      );

      if (tasksNeedingHelp.length > 0) {
        console.log(`[KanbanBoard] Queueing ${tasksNeedingHelp.length} tasks for RDR processing`);

        // Trigger RDR processing via IPC
        try {
          await window.electronAPI.triggerRdrProcessing(projectId, tasksNeedingHelp.map(t => t.id));
        } catch (error) {
          console.error('[KanbanBoard] Failed to trigger RDR processing:', error);
        }
      } else {
        console.log('[KanbanBoard] No additional tasks need RDR processing');
      }
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

      // Extract project name from title (e.g., "CV Project - Visual Studio Code" → "CV Project")
      const titlePattern = selectedWindow.title.split(' - ')[0];

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
          message = buildRdrMessage({ ...batchResult.data, projectId });
        } else {
          // Fallback to simple message if no detailed info available
          message = 'Check RDR batches and fix errored tasks';
        }

        const result = await window.electronAPI.sendRdrToWindow(titlePattern, message);

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
      {/* Kanban header with auto-resume toggle and refresh button */}
      <div className="flex items-center justify-end gap-4 px-6 pt-4 pb-2">
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
                      <span className="text-muted-foreground/70">Recover / Resume</span>
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
              onArchiveAll={status === 'done' ? handleArchiveAll : undefined}
              archivedCount={status === 'done' ? archivedCount : undefined}
              showArchived={status === 'done' ? showArchived : undefined}
              onToggleArchived={status === 'done' ? toggleShowArchived : undefined}
              selectedTaskIds={status === 'human_review' ? selectedTaskIds : undefined}
              onSelectAll={status === 'human_review' ? selectAllTasks : undefined}
              onDeselectAll={status === 'human_review' ? deselectAllTasks : undefined}
              onToggleSelect={status === 'human_review' ? toggleTaskSelection : undefined}
            />
          ))}
        </div>

        {/* Drag overlay - enhanced visual feedback */}
        <DragOverlay>
          {activeTask ? (
            <div className="drag-overlay-card">
              <TaskCard task={activeTask} onClick={() => {}} />
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
              className="gap-2 text-muted-foreground hover:text-foreground"
              onClick={deselectAllTasks}
            >
              <X className="h-4 w-4" />
              {t('kanban.clearSelection')}
            </Button>
          </div>
        </div>
      )}

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
