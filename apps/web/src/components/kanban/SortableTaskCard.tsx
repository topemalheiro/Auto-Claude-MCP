"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { cn } from "@auto-claude/ui";
import type { Task, TaskStatus } from "@auto-claude/types";
import { TaskCard } from "./TaskCard";

interface SortableTaskCardProps {
  task: Task;
  onClick: () => void;
  onStatusChange?: (taskId: string, newStatus: TaskStatus) => void;
}

export function SortableTaskCard({
  task,
  onClick,
  onStatusChange,
}: SortableTaskCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: task.id,
    data: { type: "task", task },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(isDragging && "opacity-50")}
      {...attributes}
      {...listeners}
    >
      <TaskCard
        task={task}
        onClick={onClick}
        onStatusChange={onStatusChange}
      />
    </div>
  );
}
