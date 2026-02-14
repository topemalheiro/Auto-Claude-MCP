import { create } from "zustand";
import type { Task, TaskStatus } from "@auto-claude/types";
import { apiClient } from "@/lib/data";

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

interface TaskState {
  tasks: Task[];
  isLoading: boolean;
  error: string | null;

  // Actions
  setTasks: (tasks: Task[]) => void;
  clearTasks: () => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;
}

export const useTaskStore = create<TaskState>((set) => ({
  tasks: [],
  isLoading: false,
  error: null,

  setTasks: (tasks) => set({ tasks }),

  clearTasks: () => set({ tasks: [] }),

  updateTask: (taskId, updates) =>
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.id === taskId ? { ...t, ...updates } : t
      ),
    })),
}));

export async function loadTasks(projectId: string) {
  useTaskStore.setState({ isLoading: true, error: null });
  try {
    const result = await apiClient.getTasks(projectId);
    useTaskStore.setState({
      tasks: result.tasks as Task[],
      isLoading: false,
    });
  } catch (err) {
    // Network errors (backend not running) and timeouts → silent empty state.
    // API errors (4xx/5xx) → surface so the UI can display them.
    const isNetworkError =
      err instanceof TypeError ||
      (err instanceof Error && err.name === "AbortError");
    useTaskStore.setState({
      tasks: [],
      isLoading: false,
      error: isNetworkError
        ? null
        : err instanceof Error
          ? err.message
          : "Failed to load tasks",
    });
  }
}

export async function updateTaskStatus(
  projectId: string,
  taskId: string,
  status: TaskStatus
) {
  const currentTask = useTaskStore.getState().tasks.find((t) => t.id === taskId);
  if (currentTask && !VALID_TRANSITIONS[currentTask.status]?.includes(status)) {
    console.warn(`Invalid transition: ${currentTask.status} -> ${status}`);
    return;
  }

  try {
    await apiClient.updateTaskStatus(projectId, taskId, status);
    useTaskStore.getState().updateTask(taskId, { status });
  } catch (error) {
    console.error("Failed to update task status:", error);
  }
}
