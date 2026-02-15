"use client";

import { ListTodo, Plus, X } from "lucide-react";
import type { Task } from "@auto-claude/types";
import { cn, Button, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from "@auto-claude/ui";

interface TaskSelectorProps {
  terminalId: string;
  backlogTasks: Task[];
  associatedTask?: Task;
  onTaskSelect: (taskId: string) => void;
  onClearTask: () => void;
  onNewTaskClick?: () => void;
}

export function TaskSelector({
  backlogTasks,
  associatedTask,
  onTaskSelect,
  onClearTask,
  onNewTaskClick,
}: TaskSelectorProps) {
  if (associatedTask) {
    return (
      <span className="flex items-center gap-1 text-[10px] font-medium text-blue-500 bg-blue-500/10 px-1.5 py-0.5 rounded max-w-40">
        <ListTodo className="h-2.5 w-2.5 flex-shrink-0" />
        <span className="truncate">{associatedTask.title}</span>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onClearTask();
          }}
          className="ml-0.5 hover:text-blue-300"
        >
          <X className="h-2.5 w-2.5" />
        </button>
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
          <ListTodo className="h-3 w-3" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        {backlogTasks.length === 0 ? (
          <DropdownMenuItem disabled>No backlog tasks</DropdownMenuItem>
        ) : (
          backlogTasks.map((task) => (
            <DropdownMenuItem
              key={task.id}
              onClick={() => onTaskSelect(task.id)}
            >
              <span className="truncate">{task.title}</span>
            </DropdownMenuItem>
          ))
        )}
        {onNewTaskClick && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onNewTaskClick}>
              <Plus className="h-3.5 w-3.5 mr-2" />
              New task
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
