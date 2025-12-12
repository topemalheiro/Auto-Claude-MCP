import { useState, useRef, useEffect } from 'react';
import {
  X,
  Play,
  Square,
  CheckCircle2,
  XCircle,
  AlertCircle,
  AlertTriangle,
  Clock,
  FileCode,
  Terminal,
  Target,
  Bug,
  Wrench,
  Shield,
  Gauge,
  Palette,
  Lightbulb,
  Users,
  GitBranch,
  ListChecks,
  Loader2,
  RotateCcw,
  Trash2,
  GitMerge,
  Eye,
  FolderX,
  Plus,
  Minus,
  ExternalLink,
  Zap,
  Info
} from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { ScrollArea } from './ui/scroll-area';
import { Separator } from './ui/separator';
import { Textarea } from './ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from './ui/tooltip';
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
import { cn, calculateProgress, formatRelativeTime } from '../lib/utils';
import {
  TASK_STATUS_LABELS,
  TASK_CATEGORY_LABELS,
  TASK_CATEGORY_COLORS,
  TASK_COMPLEXITY_LABELS,
  TASK_COMPLEXITY_COLORS,
  TASK_IMPACT_LABELS,
  TASK_IMPACT_COLORS,
  TASK_PRIORITY_LABELS,
  TASK_PRIORITY_COLORS,
  IDEATION_TYPE_LABELS,
  EXECUTION_PHASE_LABELS,
  EXECUTION_PHASE_BADGE_COLORS,
  EXECUTION_PHASE_COLORS
} from '../../shared/constants';
import { startTask, stopTask, submitReview, checkTaskRunning, recoverStuckTask, deleteTask } from '../stores/task-store';
import type { Task, TaskCategory, ExecutionPhase, WorktreeStatus, WorktreeDiff, ReviewReason } from '../../shared/types';

// Category icon mapping
const CategoryIcon: Record<TaskCategory, typeof Target> = {
  feature: Target,
  bug_fix: Bug,
  refactoring: Wrench,
  documentation: FileCode,
  security: Shield,
  performance: Gauge,
  ui_ux: Palette,
  infrastructure: Wrench,
  testing: FileCode
};

interface TaskDetailPanelProps {
  task: Task;
  onClose: () => void;
}

export function TaskDetailPanel({ task, onClose }: TaskDetailPanelProps) {
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [isUserScrolledUp, setIsUserScrolledUp] = useState(false);
  const [isStuck, setIsStuck] = useState(false);
  const [isRecovering, setIsRecovering] = useState(false);
  const [hasCheckedRunning, setHasCheckedRunning] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  // Workspace management state
  const [worktreeStatus, setWorktreeStatus] = useState<WorktreeStatus | null>(null);
  const [worktreeDiff, setWorktreeDiff] = useState<WorktreeDiff | null>(null);
  const [isLoadingWorktree, setIsLoadingWorktree] = useState(false);
  const [isMerging, setIsMerging] = useState(false);
  const [isDiscarding, setIsDiscarding] = useState(false);
  const [showDiscardDialog, setShowDiscardDialog] = useState(false);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [showDiffDialog, setShowDiffDialog] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const logsContainerRef = useRef<HTMLDivElement>(null);

  const progress = calculateProgress(task.chunks);
  const isRunning = task.status === 'in_progress';
  const needsReview = task.status === 'human_review';
  const executionPhase = task.executionProgress?.phase;
  const hasActiveExecution = executionPhase && executionPhase !== 'idle' && executionPhase !== 'complete' && executionPhase !== 'failed';

  // Check if task is stuck (status says in_progress but no actual process)
  useEffect(() => {
    if (isRunning && !hasCheckedRunning) {
      checkTaskRunning(task.id).then((actuallyRunning) => {
        setIsStuck(!actuallyRunning);
        setHasCheckedRunning(true);
      });
    } else if (!isRunning) {
      setIsStuck(false);
      setHasCheckedRunning(false);
    }
  }, [task.id, isRunning, hasCheckedRunning]);

  // Handle scroll events in logs to detect if user scrolled up
  const handleLogsScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.target as HTMLDivElement;
    const isNearBottom = target.scrollHeight - target.scrollTop - target.clientHeight < 100;
    setIsUserScrolledUp(!isNearBottom);
  };

  // Auto-scroll logs to bottom only if user hasn't scrolled up
  useEffect(() => {
    if (activeTab === 'logs' && logsEndRef.current && !isUserScrolledUp) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [task.logs, activeTab, isUserScrolledUp]);

  // Reset scroll state when switching to logs tab
  useEffect(() => {
    if (activeTab === 'logs') {
      setIsUserScrolledUp(false);
    }
  }, [activeTab]);

  // Load worktree status when task is in human_review
  useEffect(() => {
    if (needsReview) {
      setIsLoadingWorktree(true);
      setWorkspaceError(null);

      Promise.all([
        window.electronAPI.getWorktreeStatus(task.id),
        window.electronAPI.getWorktreeDiff(task.id)
      ]).then(([statusResult, diffResult]) => {
        if (statusResult.success && statusResult.data) {
          setWorktreeStatus(statusResult.data);
        }
        if (diffResult.success && diffResult.data) {
          setWorktreeDiff(diffResult.data);
        }
      }).catch((err) => {
        console.error('Failed to load worktree info:', err);
      }).finally(() => {
        setIsLoadingWorktree(false);
      });
    } else {
      setWorktreeStatus(null);
      setWorktreeDiff(null);
    }
  }, [task.id, needsReview]);

  const handleStartStop = () => {
    if (isRunning && !isStuck) {
      stopTask(task.id);
    } else {
      startTask(task.id);
    }
  };

  const handleRecover = async () => {
    setIsRecovering(true);
    // Auto-restart the task after recovery (no need to click Start again)
    const result = await recoverStuckTask(task.id, { autoRestart: true });
    if (result.success) {
      setIsStuck(false);
      // Reset the check flag so it will re-verify running state
      setHasCheckedRunning(false);
    }
    setIsRecovering(false);
  };

  const handleApprove = async () => {
    setIsSubmitting(true);
    await submitReview(task.id, true);
    setIsSubmitting(false);
    onClose();
  };

  const handleReject = async () => {
    if (!feedback.trim()) {
      return;
    }
    setIsSubmitting(true);
    await submitReview(task.id, false, feedback);
    setIsSubmitting(false);
    setFeedback('');
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    setDeleteError(null);
    const result = await deleteTask(task.id);
    if (result.success) {
      setShowDeleteDialog(false);
      onClose();
    } else {
      setDeleteError(result.error || 'Failed to delete task');
    }
    setIsDeleting(false);
  };

  const handleMerge = async () => {
    setIsMerging(true);
    setWorkspaceError(null);
    const result = await window.electronAPI.mergeWorktree(task.id);
    if (result.success && result.data?.success) {
      // Task will be moved to 'done' by the IPC handler
      onClose();
    } else {
      setWorkspaceError(result.data?.message || result.error || 'Failed to merge changes');
    }
    setIsMerging(false);
  };

  const handleDiscard = async () => {
    setIsDiscarding(true);
    setWorkspaceError(null);
    const result = await window.electronAPI.discardWorktree(task.id);
    if (result.success && result.data?.success) {
      // Task will be moved back to 'backlog' by the IPC handler
      setShowDiscardDialog(false);
      onClose();
    } else {
      setWorkspaceError(result.data?.message || result.error || 'Failed to discard changes');
    }
    setIsDiscarding(false);
  };

  const getChunkStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-4 w-4 text-[var(--success)]" />;
      case 'in_progress':
        return <Clock className="h-4 w-4 text-[var(--info)] animate-pulse" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-[var(--error)]" />;
      default:
        return <AlertCircle className="h-4 w-4 text-muted-foreground" />;
    }
  };

  return (
    <TooltipProvider delayDuration={300}>
      <div className="flex h-full w-96 flex-col bg-card border-l border-border">
        {/* Header - Enhanced with better visual hierarchy */}
        <div className="flex items-start justify-between p-4 pb-3">
          <div className="flex-1 min-w-0 pr-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <h2 className="font-semibold text-lg text-foreground line-clamp-2 leading-snug cursor-default">
                  {task.title}
                </h2>
              </TooltipTrigger>
              {task.title.length > 40 && (
                <TooltipContent side="bottom" className="max-w-xs">
                  <p className="text-sm">{task.title}</p>
                </TooltipContent>
              )}
            </Tooltip>
            <div className="mt-2 flex items-center gap-2 flex-wrap">
              <Badge variant="outline" className="text-xs font-mono">
                {task.specId}
              </Badge>
              {isStuck ? (
                <Badge variant="warning" className="text-xs flex items-center gap-1 animate-pulse">
                  <AlertTriangle className="h-3 w-3" />
                  Stuck
                </Badge>
              ) : (
                <>
                  <Badge
                    variant={task.status === 'done' ? 'success' : task.status === 'human_review' ? 'purple' : task.status === 'in_progress' ? 'info' : 'secondary'}
                    className={cn('text-xs', (task.status === 'in_progress' && !isStuck) && 'status-running')}
                  >
                    {TASK_STATUS_LABELS[task.status]}
                  </Badge>
                  {/* Review reason badge - explains why task needs human review */}
                  {task.status === 'human_review' && task.reviewReason && (
                    <Badge
                      variant={task.reviewReason === 'completed' ? 'success' : task.reviewReason === 'errors' ? 'destructive' : 'warning'}
                      className="text-xs"
                    >
                      {task.reviewReason === 'completed' ? 'Completed' : task.reviewReason === 'errors' ? 'Has Errors' : 'QA Issues'}
                    </Badge>
                  )}
                </>
              )}
            </div>
          </div>
          <Button variant="ghost" size="icon" className="shrink-0 -mr-1 -mt-1 hover:bg-destructive/10 hover:text-destructive transition-colors" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

      <Separator />

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <TabsList className="w-full justify-start rounded-none border-b border-border bg-transparent p-0 h-auto">
          <TabsTrigger
            value="overview"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none px-4 py-2.5 text-sm"
          >
            Overview
          </TabsTrigger>
          <TabsTrigger
            value="chunks"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none px-4 py-2.5 text-sm"
          >
            Chunks ({task.chunks.length})
          </TabsTrigger>
          <TabsTrigger
            value="logs"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none px-4 py-2.5 text-sm"
          >
            Logs
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="flex-1 min-h-0 overflow-hidden mt-0">
          <ScrollArea className="h-full">
            <div className="p-4 space-y-5">
              {/* Stuck Task Warning */}
              {isStuck && (
                <div className="rounded-xl border border-warning/30 bg-warning/10 p-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="h-5 w-5 text-warning shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <h3 className="font-medium text-sm text-foreground mb-1">
                        Task Appears Stuck
                      </h3>
                      <p className="text-sm text-muted-foreground mb-3">
                        This task is marked as running but no active process was found.
                        This can happen if the app crashed or the process was terminated unexpectedly.
                      </p>
                      <Button
                        variant="warning"
                        size="sm"
                        onClick={handleRecover}
                        disabled={isRecovering}
                        className="w-full"
                      >
                        {isRecovering ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Recovering...
                          </>
                        ) : (
                          <>
                            <RotateCcw className="mr-2 h-4 w-4" />
                            Recover & Restart Task
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </div>
              )}

              {/* Execution Phase Indicator */}
              {hasActiveExecution && executionPhase && !isStuck && (
                <div className={cn(
                  'rounded-xl border p-3 flex items-center gap-3',
                  EXECUTION_PHASE_BADGE_COLORS[executionPhase]
                )}>
                  <Loader2 className="h-5 w-5 animate-spin shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">
                        {EXECUTION_PHASE_LABELS[executionPhase]}
                      </span>
                      <span className="text-sm">
                        {task.executionProgress?.overallProgress || 0}%
                      </span>
                    </div>
                    {task.executionProgress?.message && (
                      <p className="text-xs mt-0.5 opacity-80 truncate">
                        {task.executionProgress.message}
                      </p>
                    )}
                    {task.executionProgress?.currentChunk && (
                      <p className="text-xs mt-0.5 opacity-70">
                        Chunk: {task.executionProgress.currentChunk}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Progress */}
              <div>
                <div className="section-divider mb-3">
                  <Zap className="h-3 w-3" />
                  Progress
                </div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-muted-foreground">
                    {hasActiveExecution && task.executionProgress?.message
                      ? task.executionProgress.message
                      : task.chunks.length > 0
                        ? `${task.chunks.filter(c => c.status === 'completed').length}/${task.chunks.length} chunks completed`
                        : 'No chunks yet'}
                  </span>
                  <span className={cn(
                    'text-sm font-semibold tabular-nums',
                    task.status === 'done' ? 'text-success' : 'text-foreground'
                  )}>
                    {hasActiveExecution
                      ? `${task.executionProgress?.overallProgress || 0}%`
                      : `${progress}%`}
                  </span>
                </div>
                <div className={cn(
                  'rounded-full',
                  hasActiveExecution && 'progress-working'
                )}>
                  <Progress
                    value={hasActiveExecution ? (task.executionProgress?.overallProgress || 0) : progress}
                    className={cn(
                      'h-2',
                      task.status === 'done' && '[&>div]:bg-success',
                      hasActiveExecution && '[&>div]:bg-info'
                    )}
                    animated={isRunning || task.status === 'ai_review'}
                  />
                </div>
                {/* Phase Progress Bar Segments */}
                {hasActiveExecution && (
                  <div className="mt-2 flex gap-0.5 h-1.5 rounded-full overflow-hidden bg-muted/30">
                    <div
                      className={cn(
                        'transition-all duration-300',
                        executionPhase === 'planning' ? 'bg-amber-500' : 'bg-amber-500/30'
                      )}
                      style={{ width: '20%' }}
                      title="Planning (0-20%)"
                    />
                    <div
                      className={cn(
                        'transition-all duration-300',
                        executionPhase === 'coding' ? 'bg-info' : 'bg-info/30'
                      )}
                      style={{ width: '60%' }}
                      title="Coding (20-80%)"
                    />
                    <div
                      className={cn(
                        'transition-all duration-300',
                        (executionPhase === 'qa_review' || executionPhase === 'qa_fixing') ? 'bg-purple-500' : 'bg-purple-500/30'
                      )}
                      style={{ width: '15%' }}
                      title="AI Review (80-95%)"
                    />
                    <div
                      className={cn(
                        'transition-all duration-300',
                        executionPhase === 'complete' ? 'bg-success' : 'bg-success/30'
                      )}
                      style={{ width: '5%' }}
                      title="Complete (95-100%)"
                    />
                  </div>
                )}
              </div>

              {/* Classification Badges */}
              {task.metadata && (
                <div>
                  <div className="section-divider mb-3">
                    <Info className="h-3 w-3" />
                    Classification
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                  {/* Category */}
                  {task.metadata.category && (
                    <Badge
                      variant="outline"
                      className={cn('text-xs', TASK_CATEGORY_COLORS[task.metadata.category])}
                    >
                      {CategoryIcon[task.metadata.category] && (() => {
                        const Icon = CategoryIcon[task.metadata.category!];
                        return <Icon className="h-3 w-3 mr-1" />;
                      })()}
                      {TASK_CATEGORY_LABELS[task.metadata.category]}
                    </Badge>
                  )}
                  {/* Priority */}
                  {task.metadata.priority && (
                    <Badge
                      variant="outline"
                      className={cn('text-xs', TASK_PRIORITY_COLORS[task.metadata.priority])}
                    >
                      {TASK_PRIORITY_LABELS[task.metadata.priority]}
                    </Badge>
                  )}
                  {/* Complexity */}
                  {task.metadata.complexity && (
                    <Badge
                      variant="outline"
                      className={cn('text-xs', TASK_COMPLEXITY_COLORS[task.metadata.complexity])}
                    >
                      {TASK_COMPLEXITY_LABELS[task.metadata.complexity]}
                    </Badge>
                  )}
                  {/* Impact */}
                  {task.metadata.impact && (
                    <Badge
                      variant="outline"
                      className={cn('text-xs', TASK_IMPACT_COLORS[task.metadata.impact])}
                    >
                      {TASK_IMPACT_LABELS[task.metadata.impact]}
                    </Badge>
                  )}
                  {/* Security Severity */}
                  {task.metadata.securitySeverity && (
                    <Badge
                      variant="outline"
                      className={cn('text-xs', TASK_IMPACT_COLORS[task.metadata.securitySeverity])}
                    >
                      <Shield className="h-3 w-3 mr-1" />
                      {task.metadata.securitySeverity} severity
                    </Badge>
                  )}
                  {/* Source Type */}
                  {task.metadata.sourceType && (
                    <Badge variant="secondary" className="text-xs">
                      {task.metadata.sourceType === 'ideation' && task.metadata.ideationType
                        ? IDEATION_TYPE_LABELS[task.metadata.ideationType] || task.metadata.ideationType
                        : task.metadata.sourceType}
                    </Badge>
                  )}
                  </div>
                </div>
              )}

              {/* Description */}
              {task.description && (
                <div>
                  <div className="section-divider mb-3">
                    <FileCode className="h-3 w-3" />
                    Description
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed">{task.description}</p>
                </div>
              )}

              {/* Metadata Details */}
              {task.metadata && (
                <div className="space-y-4">
                  {/* Rationale */}
                  {task.metadata.rationale && (
                    <div>
                      <h3 className="text-sm font-medium text-foreground mb-1.5 flex items-center gap-1.5">
                        <Lightbulb className="h-3.5 w-3.5 text-warning" />
                        Rationale
                      </h3>
                      <p className="text-sm text-muted-foreground">{task.metadata.rationale}</p>
                    </div>
                  )}

                  {/* Problem Solved */}
                  {task.metadata.problemSolved && (
                    <div>
                      <h3 className="text-sm font-medium text-foreground mb-1.5 flex items-center gap-1.5">
                        <Target className="h-3.5 w-3.5 text-success" />
                        Problem Solved
                      </h3>
                      <p className="text-sm text-muted-foreground">{task.metadata.problemSolved}</p>
                    </div>
                  )}

                  {/* Target Audience */}
                  {task.metadata.targetAudience && (
                    <div>
                      <h3 className="text-sm font-medium text-foreground mb-1.5 flex items-center gap-1.5">
                        <Users className="h-3.5 w-3.5 text-info" />
                        Target Audience
                      </h3>
                      <p className="text-sm text-muted-foreground">{task.metadata.targetAudience}</p>
                    </div>
                  )}

                  {/* Dependencies */}
                  {task.metadata.dependencies && task.metadata.dependencies.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium text-foreground mb-1.5 flex items-center gap-1.5">
                        <GitBranch className="h-3.5 w-3.5 text-purple-400" />
                        Dependencies
                      </h3>
                      <ul className="text-sm text-muted-foreground list-disc list-inside space-y-0.5">
                        {task.metadata.dependencies.map((dep, idx) => (
                          <li key={idx}>{dep}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Acceptance Criteria */}
                  {task.metadata.acceptanceCriteria && task.metadata.acceptanceCriteria.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium text-foreground mb-1.5 flex items-center gap-1.5">
                        <ListChecks className="h-3.5 w-3.5 text-success" />
                        Acceptance Criteria
                      </h3>
                      <ul className="text-sm text-muted-foreground list-disc list-inside space-y-0.5">
                        {task.metadata.acceptanceCriteria.map((criteria, idx) => (
                          <li key={idx}>{criteria}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Affected Files */}
                  {task.metadata.affectedFiles && task.metadata.affectedFiles.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium text-foreground mb-1.5 flex items-center gap-1.5">
                        <FileCode className="h-3.5 w-3.5 text-muted-foreground" />
                        Affected Files
                      </h3>
                      <div className="flex flex-wrap gap-1">
                        {task.metadata.affectedFiles.map((file, idx) => (
                          <Tooltip key={idx}>
                            <TooltipTrigger asChild>
                              <Badge variant="secondary" className="text-xs font-mono cursor-help">
                                {file.split('/').pop()}
                              </Badge>
                            </TooltipTrigger>
                            <TooltipContent side="top" className="font-mono text-xs">
                              {file}
                            </TooltipContent>
                          </Tooltip>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Timestamps */}
              <div>
                <div className="section-divider mb-3">
                  <Clock className="h-3 w-3" />
                  Timeline
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Created</span>
                    <span className="text-foreground tabular-nums">{formatRelativeTime(task.createdAt)}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Updated</span>
                    <span className="text-foreground tabular-nums">{formatRelativeTime(task.updatedAt)}</span>
                  </div>
                </div>
              </div>

              {/* Human Review Section - Enhanced styling */}
              {needsReview && (
                <div className="space-y-4">
                  {/* Section divider */}
                  <div className="section-divider-gradient" />

                  {/* Workspace Status */}
                  {isLoadingWorktree ? (
                    <div className="rounded-xl border border-border bg-secondary/30 p-4">
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span className="text-sm">Loading workspace info...</span>
                      </div>
                    </div>
                  ) : worktreeStatus?.exists ? (
                    <div className="review-section-highlight">
                      <h3 className="font-medium text-sm text-foreground mb-3 flex items-center gap-2">
                        <GitBranch className="h-4 w-4 text-purple-400" />
                        Build Ready for Review
                      </h3>

                      {/* Change Summary */}
                      <div className="bg-background/50 rounded-lg p-3 mb-3">
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div className="flex items-center gap-2">
                            <FileCode className="h-4 w-4 text-muted-foreground" />
                            <span className="text-muted-foreground">Files changed:</span>
                            <span className="text-foreground font-medium">{worktreeStatus.filesChanged || 0}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <GitBranch className="h-4 w-4 text-muted-foreground" />
                            <span className="text-muted-foreground">Commits:</span>
                            <span className="text-foreground font-medium">{worktreeStatus.commitCount || 0}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Plus className="h-4 w-4 text-success" />
                            <span className="text-muted-foreground">Additions:</span>
                            <span className="text-success font-medium">+{worktreeStatus.additions || 0}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Minus className="h-4 w-4 text-destructive" />
                            <span className="text-muted-foreground">Deletions:</span>
                            <span className="text-destructive font-medium">-{worktreeStatus.deletions || 0}</span>
                          </div>
                        </div>
                        {worktreeStatus.branch && (
                          <div className="mt-2 pt-2 border-t border-border/50 text-xs text-muted-foreground">
                            Branch: <code className="bg-background px-1 rounded">{worktreeStatus.branch}</code>
                            {' → '}
                            <code className="bg-background px-1 rounded">{worktreeStatus.baseBranch || 'main'}</code>
                          </div>
                        )}
                      </div>

                      {/* Workspace Error */}
                      {workspaceError && (
                        <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-3 mb-3">
                          <p className="text-sm text-destructive">{workspaceError}</p>
                        </div>
                      )}

                      {/* Action Buttons */}
                      <div className="flex gap-2 mb-3">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setShowDiffDialog(true)}
                          className="flex-1"
                        >
                          <Eye className="mr-2 h-4 w-4" />
                          View Changes
                        </Button>
                        {worktreeStatus.worktreePath && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              // Open folder in system file manager
                              window.electronAPI.createTerminal({
                                id: `open-${task.id}`,
                                cwd: worktreeStatus.worktreePath!,
                                name: 'Open Folder'
                              });
                            }}
                            className="flex-none"
                          >
                            <ExternalLink className="h-4 w-4" />
                          </Button>
                        )}
                      </div>

                      {/* Primary Actions */}
                      <div className="flex gap-2">
                        <Button
                          variant="success"
                          onClick={handleMerge}
                          disabled={isMerging || isDiscarding}
                          className="flex-1"
                        >
                          {isMerging ? (
                            <>
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              Merging...
                            </>
                          ) : (
                            <>
                              <GitMerge className="mr-2 h-4 w-4" />
                              Merge to Main
                            </>
                          )}
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => setShowDiscardDialog(true)}
                          disabled={isMerging || isDiscarding}
                          className="text-destructive hover:text-destructive hover:bg-destructive/10"
                        >
                          <FolderX className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-xl border border-border bg-secondary/30 p-4">
                      <h3 className="font-medium text-sm text-foreground mb-2 flex items-center gap-2">
                        <AlertCircle className="h-4 w-4 text-muted-foreground" />
                        No Workspace Found
                      </h3>
                      <p className="text-sm text-muted-foreground">
                        No isolated workspace was found for this task. The changes may have been made directly in your project.
                      </p>
                    </div>
                  )}

                  {/* QA Feedback Section (for requesting changes) */}
                  <div className="rounded-xl border border-warning/30 bg-warning/10 p-4">
                    <h3 className="font-medium text-sm text-foreground mb-2 flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-warning" />
                      Request Changes
                    </h3>
                    <p className="text-sm text-muted-foreground mb-3">
                      Found issues? Describe what needs to be fixed and the AI will continue working on it.
                    </p>
                    <Textarea
                      placeholder="Describe the issues or changes needed..."
                      value={feedback}
                      onChange={(e) => setFeedback(e.target.value)}
                      className="mb-3"
                      rows={3}
                    />
                    <Button
                      variant="warning"
                      onClick={handleReject}
                      disabled={isSubmitting || !feedback.trim()}
                      className="w-full"
                    >
                      {isSubmitting ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Submitting...
                        </>
                      ) : (
                        <>
                          <RotateCcw className="mr-2 h-4 w-4" />
                          Request Changes
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>
        </TabsContent>

        {/* Chunks Tab */}
        <TabsContent value="chunks" className="flex-1 min-h-0 overflow-hidden mt-0">
          <ScrollArea className="h-full">
            <div className="p-4 space-y-3">
              {task.chunks.length === 0 ? (
                <div className="text-center py-12">
                  <ListChecks className="h-10 w-10 mx-auto mb-3 text-muted-foreground/30" />
                  <p className="text-sm font-medium text-muted-foreground mb-1">No chunks defined</p>
                  <p className="text-xs text-muted-foreground/70">
                    Implementation chunks will appear here after planning
                  </p>
                </div>
              ) : (
                <>
                  {/* Progress summary */}
                  <div className="flex items-center justify-between text-xs text-muted-foreground pb-2 border-b border-border/50">
                    <span>{task.chunks.filter(c => c.status === 'completed').length} of {task.chunks.length} completed</span>
                    <span className="tabular-nums">{progress}%</span>
                  </div>
                  {task.chunks.map((chunk, index) => (
                    <div
                      key={chunk.id}
                      className={cn(
                        'rounded-xl border border-border bg-secondary/30 p-3 transition-all duration-200 hover:bg-secondary/50',
                        chunk.status === 'in_progress' && 'border-[var(--info)]/50 bg-[var(--info-light)] ring-1 ring-info/20',
                        chunk.status === 'completed' && 'border-[var(--success)]/50 bg-[var(--success-light)]',
                        chunk.status === 'failed' && 'border-[var(--error)]/50 bg-[var(--error-light)]'
                      )}
                    >
                      <div className="flex items-start gap-2">
                        {getChunkStatusIcon(chunk.status)}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className={cn(
                              'text-[10px] font-medium px-1.5 py-0.5 rounded-full',
                              chunk.status === 'completed' ? 'bg-success/20 text-success' :
                              chunk.status === 'in_progress' ? 'bg-info/20 text-info' :
                              chunk.status === 'failed' ? 'bg-destructive/20 text-destructive' :
                              'bg-muted text-muted-foreground'
                            )}>
                              #{index + 1}
                            </span>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className="text-sm font-medium text-foreground truncate cursor-default">
                                  {chunk.id}
                                </span>
                              </TooltipTrigger>
                              <TooltipContent side="top" className="max-w-xs">
                                <p className="font-mono text-xs">{chunk.id}</p>
                              </TooltipContent>
                            </Tooltip>
                          </div>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <p className="mt-1 text-xs text-muted-foreground line-clamp-2 cursor-default">
                                {chunk.description}
                              </p>
                            </TooltipTrigger>
                            {chunk.description && chunk.description.length > 80 && (
                              <TooltipContent side="bottom" className="max-w-sm">
                                <p className="text-xs">{chunk.description}</p>
                              </TooltipContent>
                            )}
                          </Tooltip>
                          {chunk.files && chunk.files.length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-1">
                              {chunk.files.map((file) => (
                                <Tooltip key={file}>
                                  <TooltipTrigger asChild>
                                    <Badge
                                      variant="secondary"
                                      className="text-xs font-mono cursor-help"
                                    >
                                      <FileCode className="mr-1 h-3 w-3" />
                                      {file.split('/').pop()}
                                    </Badge>
                                  </TooltipTrigger>
                                  <TooltipContent side="top" className="font-mono text-xs">
                                    {file}
                                  </TooltipContent>
                                </Tooltip>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </>
              )}
            </div>
          </ScrollArea>
        </TabsContent>

        {/* Logs Tab */}
        <TabsContent value="logs" className="flex-1 min-h-0 overflow-hidden mt-0">
          <div
            ref={logsContainerRef}
            className="h-full overflow-y-auto scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent"
            onScroll={handleLogsScroll}
          >
            <div className="p-4">
              {task.logs && task.logs.length > 0 ? (
                <pre className="text-xs font-mono text-muted-foreground whitespace-pre-wrap break-all">
                  {task.logs.join('')}
                  <div ref={logsEndRef} />
                </pre>
              ) : (
                <div className="text-center text-sm text-muted-foreground py-8">
                  <Terminal className="mx-auto mb-2 h-8 w-8 opacity-50" />
                  <p>No logs yet</p>
                  <p className="text-xs mt-1">Logs will appear here when the task runs</p>
                </div>
              )}
            </div>
          </div>
        </TabsContent>
      </Tabs>

      <Separator />

      {/* Actions */}
      <div className="p-4">
        {isStuck ? (
          <Button
            className="w-full"
            variant="warning"
            onClick={handleRecover}
            disabled={isRecovering}
          >
            {isRecovering ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Recovering...
              </>
            ) : (
              <>
                <RotateCcw className="mr-2 h-4 w-4" />
                Recover Task
              </>
            )}
          </Button>
        ) : (task.status === 'backlog' || task.status === 'in_progress') && (
          <Button
            className="w-full"
            variant={isRunning ? 'destructive' : 'default'}
            onClick={handleStartStop}
          >
            {isRunning ? (
              <>
                <Square className="mr-2 h-4 w-4" />
                Stop Task
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Start Task
              </>
            )}
          </Button>
        )}
        {task.status === 'done' && (
          <div className="completion-state text-sm">
            <CheckCircle2 className="h-5 w-5" />
            <span className="font-medium">Task completed successfully</span>
          </div>
        )}

        {/* Delete Button - always visible but disabled when running */}
        <Button
          variant="ghost"
          size="sm"
          className="w-full mt-3 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
          onClick={() => setShowDeleteDialog(true)}
          disabled={isRunning && !isStuck}
        >
          <Trash2 className="mr-2 h-4 w-4" />
          Delete Task
        </Button>
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              Delete Task
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="text-sm text-muted-foreground space-y-3">
                <p>
                  Are you sure you want to delete <strong className="text-foreground">"{task.title}"</strong>?
                </p>
                <p className="text-destructive">
                  This action cannot be undone. All task files, including the spec, implementation plan, and any generated code will be permanently deleted from the project.
                </p>
                {deleteError && (
                  <p className="text-destructive bg-destructive/10 px-3 py-2 rounded-lg text-sm">
                    {deleteError}
                  </p>
                )}
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault();
                handleDelete();
              }}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete Permanently
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Discard Confirmation Dialog */}
      <AlertDialog open={showDiscardDialog} onOpenChange={setShowDiscardDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <FolderX className="h-5 w-5 text-destructive" />
              Discard Build
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="text-sm text-muted-foreground space-y-3">
                <p>
                  Are you sure you want to discard all changes for <strong className="text-foreground">"{task.title}"</strong>?
                </p>
                <p className="text-destructive">
                  This will permanently delete the isolated workspace and all uncommitted changes.
                  The task will be moved back to Planning status.
                </p>
                {worktreeStatus?.exists && (
                  <div className="bg-muted/50 rounded-lg p-3 text-sm">
                    <div className="flex justify-between mb-1">
                      <span className="text-muted-foreground">Files changed:</span>
                      <span>{worktreeStatus.filesChanged || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Lines:</span>
                      <span className="text-success">+{worktreeStatus.additions || 0}</span>
                      <span className="text-destructive">-{worktreeStatus.deletions || 0}</span>
                    </div>
                  </div>
                )}
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDiscarding}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault();
                handleDiscard();
              }}
              disabled={isDiscarding}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDiscarding ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Discarding...
                </>
              ) : (
                <>
                  <FolderX className="mr-2 h-4 w-4" />
                  Discard Build
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Diff View Dialog */}
      <AlertDialog open={showDiffDialog} onOpenChange={setShowDiffDialog}>
        <AlertDialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5 text-purple-400" />
              Changed Files
            </AlertDialogTitle>
            <AlertDialogDescription>
              {worktreeDiff?.summary || 'No changes found'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="flex-1 overflow-auto min-h-0 -mx-6 px-6">
            {worktreeDiff?.files && worktreeDiff.files.length > 0 ? (
              <div className="space-y-2">
                {worktreeDiff.files.map((file, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-2 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors"
                  >
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <FileCode className={cn(
                        'h-4 w-4 shrink-0',
                        file.status === 'added' && 'text-success',
                        file.status === 'deleted' && 'text-destructive',
                        file.status === 'modified' && 'text-info',
                        file.status === 'renamed' && 'text-warning'
                      )} />
                      <span className="text-sm font-mono truncate">{file.path}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0 ml-2">
                      <Badge
                        variant="secondary"
                        className={cn(
                          'text-xs',
                          file.status === 'added' && 'bg-success/10 text-success',
                          file.status === 'deleted' && 'bg-destructive/10 text-destructive',
                          file.status === 'modified' && 'bg-info/10 text-info',
                          file.status === 'renamed' && 'bg-warning/10 text-warning'
                        )}
                      >
                        {file.status}
                      </Badge>
                      <span className="text-xs text-success">+{file.additions}</span>
                      <span className="text-xs text-destructive">-{file.deletions}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No changed files found
              </div>
            )}
          </div>
          <AlertDialogFooter className="mt-4">
            <AlertDialogCancel>Close</AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      </div>
    </TooltipProvider>
  );
}
