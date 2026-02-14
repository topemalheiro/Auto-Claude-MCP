"use client";

import { memo, useMemo, useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  GitPullRequest,
  AlertTriangle,
  Target,
  Bug,
  Wrench,
  FileCode,
  Shield,
  Gauge,
  Palette,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import type { Task, TaskStatus } from "@auto-claude/types";
import { TaskActions } from "./TaskActions";
import { PhaseProgressIndicator } from "@/components/common/PhaseProgressIndicator";

/** Stuck detection interval (ms) — last-resort safety net */
const STUCK_CHECK_INTERVAL_MS = 60_000;

const PRIORITY_COLORS: Record<string, string> = {
  urgent: "border-l-red-500",
  high: "border-l-orange-500",
  medium: "border-l-yellow-500",
  low: "border-l-blue-500",
};

const COMPLEXITY_VARIANTS: Record<string, string> = {
  trivial: "bg-green-500/10 text-green-600",
  small: "bg-blue-500/10 text-blue-600",
  medium: "bg-yellow-500/10 text-yellow-600",
  large: "bg-orange-500/10 text-orange-600",
  complex: "bg-red-500/10 text-red-600",
};

const IMPACT_VARIANTS: Record<string, string> = {
  low: "bg-blue-500/10 text-blue-600",
  medium: "bg-yellow-500/10 text-yellow-600",
  high: "bg-orange-500/10 text-orange-600",
  critical: "bg-red-500/10 text-red-600",
};

/** Category icon mapping */
const CategoryIcon: Record<string, React.ElementType> = {
  feature: Target,
  bug_fix: Bug,
  refactoring: Wrench,
  documentation: FileCode,
  security: Shield,
  performance: Gauge,
  ui_ux: Palette,
  infrastructure: Wrench,
  testing: FileCode,
};

/** Format execution time from seconds */
function formatExecutionTime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

interface TaskCardProps {
  task: Task;
  onClick: () => void;
  onStatusChange?: (taskId: string, newStatus: TaskStatus) => void;
  onStart?: (taskId: string) => void;
  onStop?: (taskId: string) => void;
  onArchive?: (taskId: string) => void;
  onCreatePR?: (taskId: string) => void;
}

export const TaskCard = memo(function TaskCard({
  task,
  onClick,
  onStatusChange,
  onStart,
  onStop,
  onArchive,
  onCreatePR,
}: TaskCardProps) {
  const { t } = useTranslation("kanban");
  const [isStuck, setIsStuck] = useState(false);
  const stuckIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const priority = task.metadata?.priority;
  const category = task.metadata?.category;
  const complexity = task.metadata?.complexity;
  const impact = task.metadata?.impact;
  const isRunning = task.status === "in_progress";
  const executionPhase = task.executionProgress?.phase;
  const hasActiveExecution = executionPhase && executionPhase !== "idle" && executionPhase !== "complete" && executionPhase !== "failed";

  // Subtask progress
  const totalSubtasks = task.subtasks?.length || 0;
  const completedSubtasks = task.subtasks?.filter((s) => s.status === "completed").length || 0;

  // Execution time display — use task timestamps
  const executionTime = useMemo(() => {
    if (!isRunning && !hasActiveExecution) return null;
    const start = task.createdAt ? new Date(task.createdAt).getTime() : 0;
    if (!start) return null;
    const end = task.updatedAt ? new Date(task.updatedAt).getTime() : Date.now();
    const seconds = Math.floor((end - start) / 1000);
    return seconds > 0 ? formatExecutionTime(seconds) : null;
  }, [task.createdAt, task.updatedAt, isRunning, hasActiveExecution]);

  // Stuck detection for running tasks
  useEffect(() => {
    if (!isRunning) {
      setIsStuck(false);
      if (stuckIntervalRef.current) {
        clearInterval(stuckIntervalRef.current);
        stuckIntervalRef.current = null;
      }
      return;
    }

    stuckIntervalRef.current = setInterval(() => {
      const lastUpdate = task.updatedAt ? new Date(task.updatedAt).getTime() : 0;
      const elapsed = Date.now() - lastUpdate;
      setIsStuck(elapsed > STUCK_CHECK_INTERVAL_MS);
    }, STUCK_CHECK_INTERVAL_MS);

    return () => {
      if (stuckIntervalRef.current) {
        clearInterval(stuckIntervalRef.current);
      }
    };
  }, [isRunning, task.updatedAt]);

  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card p-3 cursor-pointer transition-all hover:shadow-md hover:border-border/80 group",
        "border-l-2",
        priority ? PRIORITY_COLORS[priority] || "border-l-transparent" : "border-l-transparent",
        isStuck && "ring-1 ring-warning/50",
      )}
      onClick={onClick}
    >
      {/* Title row with actions */}
      <div className="flex items-start gap-1.5">
        <h3 className="flex-1 text-sm font-medium leading-tight line-clamp-2">
          {task.title}
        </h3>
        <div className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          <TaskActions
            task={task}
            onStatusChange={onStatusChange}
            onStart={onStart}
            onStop={onStop}
            onArchive={onArchive}
            onCreatePR={onCreatePR}
          />
        </div>
      </div>

      {/* Description preview */}
      {task.description && (
        <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
          {task.description}
        </p>
      )}

      {/* Badges row: category, complexity, priority, impact */}
      <div className="mt-2 flex items-center gap-1.5 flex-wrap">
        {category && (
          <span className="inline-flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
            {CategoryIcon[category] &&
              (() => {
                const CatIcon = CategoryIcon[category];
                return <CatIcon className="h-2.5 w-2.5" />;
              })()}
            {t(`card.category.${category}`, category)}
          </span>
        )}

        {complexity && (
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[10px] font-medium",
              COMPLEXITY_VARIANTS[complexity] || "bg-secondary text-muted-foreground",
            )}
          >
            {t(`card.complexity.${complexity}`, complexity)}
          </span>
        )}

        {priority && (
          <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
            {t(`card.priority.${priority}`, priority)}
          </span>
        )}

        {impact && (
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[10px] font-medium",
              IMPACT_VARIANTS[impact] || "bg-secondary text-muted-foreground",
            )}
          >
            {t(`card.impact.${impact}`, impact)}
          </span>
        )}

        {/* Subtask progress */}
        {totalSubtasks > 0 && (
          <span className="ml-auto flex items-center gap-1 text-[10px] text-muted-foreground">
            <CheckCircle2 className="h-3 w-3" />
            {completedSubtasks}/{totalSubtasks}
          </span>
        )}
      </div>

      {/* Phase progress indicator for active executions */}
      {hasActiveExecution && (
        <div className="mt-2">
          <PhaseProgressIndicator
            phase={executionPhase}
            subtasks={task.subtasks || []}
            phaseProgress={task.executionProgress?.phaseProgress}
            isStuck={isStuck}
            isRunning={isRunning}
          />
        </div>
      )}

      {/* Execution time and stuck indicator */}
      <div className="mt-2 flex items-center gap-2">
        {executionTime && (
          <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
            <Clock className="h-3 w-3" />
            {executionTime}
          </span>
        )}
        {isStuck && (
          <span className="flex items-center gap-1 text-[10px] text-warning font-medium">
            <AlertTriangle className="h-3 w-3" />
            {t("card.stuck", "Stuck")}
          </span>
        )}
      </div>

      {/* Remapped status badges */}
      {task.status === "pr_created" && (
        <div className="mt-2">
          <span className="inline-flex items-center gap-1 rounded-full bg-green-500/10 px-2 py-0.5 text-[10px] font-medium text-green-600">
            <GitPullRequest className="h-3 w-3" />
            {t("card.badges.prCreated")}
          </span>
        </div>
      )}
      {task.status === "error" && (
        <div className="mt-2">
          <span className="inline-flex items-center gap-1 rounded-full bg-red-500/10 px-2 py-0.5 text-[10px] font-medium text-red-600">
            <AlertCircle className="h-3 w-3" />
            {t("card.badges.error")}
          </span>
        </div>
      )}

      {/* Review reason badge */}
      {task.status === "human_review" && task.reviewReason && (
        <div className="mt-2">
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[10px] font-medium",
              task.reviewReason === "completed" && "bg-green-500/10 text-green-600",
              task.reviewReason === "errors" && "bg-red-500/10 text-red-600",
              task.reviewReason === "qa_rejected" && "bg-orange-500/10 text-orange-600",
              task.reviewReason === "plan_review" && "bg-blue-500/10 text-blue-600",
            )}
          >
            {t(`card.review.${task.reviewReason}`, task.reviewReason)}
          </span>
        </div>
      )}
    </div>
  );
});
