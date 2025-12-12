import { create } from 'zustand';
import type { Task, TaskStatus, ImplementationPlan, Chunk, TaskMetadata, ExecutionProgress, ExecutionPhase, ReviewReason } from '../../shared/types';

interface TaskState {
  tasks: Task[];
  selectedTaskId: string | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  setTasks: (tasks: Task[]) => void;
  addTask: (task: Task) => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;
  updateTaskStatus: (taskId: string, status: TaskStatus) => void;
  updateTaskFromPlan: (taskId: string, plan: ImplementationPlan) => void;
  updateExecutionProgress: (taskId: string, progress: Partial<ExecutionProgress>) => void;
  appendLog: (taskId: string, log: string) => void;
  selectTask: (taskId: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearTasks: () => void;

  // Selectors
  getSelectedTask: () => Task | undefined;
  getTasksByStatus: (status: TaskStatus) => Task[];
}

export const useTaskStore = create<TaskState>((set, get) => ({
  tasks: [],
  selectedTaskId: null,
  isLoading: false,
  error: null,

  setTasks: (tasks) => set({ tasks }),

  addTask: (task) =>
    set((state) => ({
      tasks: [...state.tasks, task]
    })),

  updateTask: (taskId, updates) =>
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.id === taskId || t.specId === taskId ? { ...t, ...updates } : t
      )
    })),

  updateTaskStatus: (taskId, status) =>
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.id === taskId || t.specId === taskId
          ? { ...t, status, updatedAt: new Date() }
          : t
      )
    })),

  updateTaskFromPlan: (taskId, plan) =>
    set((state) => ({
      tasks: state.tasks.map((t) => {
        if (t.id !== taskId && t.specId !== taskId) return t;

        // Extract chunks from plan
        const chunks: Chunk[] = plan.phases.flatMap((phase) =>
          phase.chunks.map((chunk) => ({
            id: chunk.id,
            title: chunk.description,
            description: chunk.description,
            status: chunk.status,
            files: [],
            verification: chunk.verification as Chunk['verification']
          }))
        );

        // Determine status and reviewReason based on chunks
        // This logic must match the backend (project-store.ts) exactly
        const allCompleted = chunks.length > 0 && chunks.every((c) => c.status === 'completed');
        const anyInProgress = chunks.some((c) => c.status === 'in_progress');
        const anyFailed = chunks.some((c) => c.status === 'failed');
        const anyCompleted = chunks.some((c) => c.status === 'completed');

        let status: TaskStatus = t.status;
        let reviewReason: ReviewReason | undefined = t.reviewReason;

        if (allCompleted) {
          // All chunks done - waiting for QA review
          status = 'ai_review';
          reviewReason = undefined;
        } else if (anyFailed) {
          // Some chunks failed - needs human attention
          status = 'human_review';
          reviewReason = 'errors';
        } else if (anyInProgress || anyCompleted) {
          // Work in progress
          status = 'in_progress';
          reviewReason = undefined;
        }

        return {
          ...t,
          title: plan.feature || t.title,
          chunks,
          status,
          reviewReason,
          updatedAt: new Date()
        };
      })
    })),

  updateExecutionProgress: (taskId, progress) =>
    set((state) => ({
      tasks: state.tasks.map((t) => {
        if (t.id !== taskId && t.specId !== taskId) return t;

        // Merge with existing progress
        const existingProgress = t.executionProgress || {
          phase: 'idle' as ExecutionPhase,
          phaseProgress: 0,
          overallProgress: 0
        };

        return {
          ...t,
          executionProgress: {
            ...existingProgress,
            ...progress
          },
          updatedAt: new Date()
        };
      })
    })),

  appendLog: (taskId, log) =>
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.id === taskId || t.specId === taskId
          ? { ...t, logs: [...(t.logs || []), log] }
          : t
      )
    })),

  selectTask: (taskId) => set({ selectedTaskId: taskId }),

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),

  clearTasks: () => set({ tasks: [], selectedTaskId: null }),

  getSelectedTask: () => {
    const state = get();
    return state.tasks.find((t) => t.id === state.selectedTaskId);
  },

  getTasksByStatus: (status) => {
    const state = get();
    return state.tasks.filter((t) => t.status === status);
  }
}));

/**
 * Load tasks for a project
 */
export async function loadTasks(projectId: string): Promise<void> {
  const store = useTaskStore.getState();
  store.setLoading(true);
  store.setError(null);

  try {
    const result = await window.electronAPI.getTasks(projectId);
    if (result.success && result.data) {
      store.setTasks(result.data);
    } else {
      store.setError(result.error || 'Failed to load tasks');
    }
  } catch (error) {
    store.setError(error instanceof Error ? error.message : 'Unknown error');
  } finally {
    store.setLoading(false);
  }
}

/**
 * Create a new task
 */
export async function createTask(
  projectId: string,
  title: string,
  description: string,
  metadata?: TaskMetadata
): Promise<Task | null> {
  const store = useTaskStore.getState();

  try {
    const result = await window.electronAPI.createTask(projectId, title, description, metadata);
    if (result.success && result.data) {
      store.addTask(result.data);
      return result.data;
    } else {
      store.setError(result.error || 'Failed to create task');
      return null;
    }
  } catch (error) {
    store.setError(error instanceof Error ? error.message : 'Unknown error');
    return null;
  }
}

/**
 * Start a task
 */
export function startTask(taskId: string, options?: { parallel?: boolean; workers?: number }): void {
  window.electronAPI.startTask(taskId, options);
}

/**
 * Stop a task
 */
export function stopTask(taskId: string): void {
  window.electronAPI.stopTask(taskId);
}

/**
 * Submit review for a task
 */
export async function submitReview(
  taskId: string,
  approved: boolean,
  feedback?: string
): Promise<boolean> {
  const store = useTaskStore.getState();

  try {
    const result = await window.electronAPI.submitReview(taskId, approved, feedback);
    if (result.success) {
      store.updateTaskStatus(taskId, approved ? 'done' : 'in_progress');
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

/**
 * Update task status and persist to file
 */
export async function persistTaskStatus(
  taskId: string,
  status: TaskStatus
): Promise<boolean> {
  const store = useTaskStore.getState();

  try {
    // Update local state first for immediate feedback
    store.updateTaskStatus(taskId, status);

    // Persist to file
    const result = await window.electronAPI.updateTaskStatus(taskId, status);
    if (!result.success) {
      console.error('Failed to persist task status:', result.error);
      return false;
    }
    return true;
  } catch (error) {
    console.error('Error persisting task status:', error);
    return false;
  }
}

/**
 * Check if a task has an active running process
 */
export async function checkTaskRunning(taskId: string): Promise<boolean> {
  try {
    const result = await window.electronAPI.checkTaskRunning(taskId);
    return result.success && result.data === true;
  } catch (error) {
    console.error('Error checking task running status:', error);
    return false;
  }
}

/**
 * Recover a stuck task (status shows in_progress but no process running)
 * @param taskId - The task ID to recover
 * @param options - Recovery options (autoRestart defaults to true)
 */
export async function recoverStuckTask(
  taskId: string,
  options: { targetStatus?: TaskStatus; autoRestart?: boolean } = { autoRestart: true }
): Promise<{ success: boolean; message: string; autoRestarted?: boolean }> {
  const store = useTaskStore.getState();

  try {
    const result = await window.electronAPI.recoverStuckTask(taskId, options);

    if (result.success && result.data) {
      // Update local state
      store.updateTaskStatus(taskId, result.data.newStatus);
      return { 
        success: true, 
        message: result.data.message,
        autoRestarted: result.data.autoRestarted
      };
    }

    return {
      success: false,
      message: result.error || 'Failed to recover task'
    };
  } catch (error) {
    console.error('Error recovering stuck task:', error);
    return {
      success: false,
      message: error instanceof Error ? error.message : 'Unknown error'
    };
  }
}

/**
 * Delete a task and its spec directory
 */
export async function deleteTask(
  taskId: string
): Promise<{ success: boolean; error?: string }> {
  const store = useTaskStore.getState();

  try {
    const result = await window.electronAPI.deleteTask(taskId);

    if (result.success) {
      // Remove from local state
      store.setTasks(store.tasks.filter(t => t.id !== taskId && t.specId !== taskId));
      // Clear selection if this task was selected
      if (store.selectedTaskId === taskId) {
        store.selectTask(null);
      }
      return { success: true };
    }

    return {
      success: false,
      error: result.error || 'Failed to delete task'
    };
  } catch (error) {
    console.error('Error deleting task:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
}
