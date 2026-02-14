"use client";

import { useCallback } from "react";
import { useWebSocket } from "@/providers/WebSocketProvider";
import { useWebSocketEvent } from "./useWebSocketEvent";
import { useTaskStore } from "@/stores/task-store";
import { useProjectStore } from "@/stores/project-store";
import type { EventsServerEvents } from "@/lib/websocket-client";
import type { TaskStatus } from "@auto-claude/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface NotificationEvent {
  level: string;
  title: string;
  body?: string;
}

export interface RealTimeEventsOptions {
  /** Called when a notification event arrives. */
  onNotification?: (notification: NotificationEvent) => void;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Subscribe to general real-time application events (task status changes,
 * project updates, settings changes, notifications).
 *
 * Replaces Electron's IPC listeners for task/project/settings events
 * with WebSocket subscriptions on the `/events` namespace.
 *
 * Should be mounted once at the app root level (like useIpcListeners in
 * the Electron app).
 */
export function useRealTimeEvents(options?: RealTimeEventsOptions): void {
  const { events } = useWebSocket();

  const onTaskUpdated = useCallback(
    (data: Parameters<EventsServerEvents["task:updated"]>[0]) => {
      useTaskStore.getState().updateTask(data.taskId, {
        status: data.status as TaskStatus,
      });
    },
    [],
  );

  const onTaskCreated = useCallback(
    (_data: Parameters<EventsServerEvents["task:created"]>[0]) => {
      // Re-fetch tasks for the active project to pick up the new task.
      // A targeted insert would be more efficient but requires the full
      // Task object which the event doesn't carry.
      const projectId =
        useProjectStore.getState().activeProjectId ??
        useProjectStore.getState().selectedProjectId;
      if (projectId) {
        // Dynamic import avoids circular dependency with task-store
        import("@/stores/task-store").then(({ loadTasks }) => loadTasks(projectId));
      }
    },
    [],
  );

  const onProjectUpdated = useCallback(
    (_data: Parameters<EventsServerEvents["project:updated"]>[0]) => {
      // Re-fetch project list to pick up any changes
      import("@/stores/project-store").then(({ loadProjects }) => loadProjects());
    },
    [],
  );

  const onNotification = useCallback(
    (data: Parameters<EventsServerEvents["notification"]>[0]) => {
      options?.onNotification?.(data);
    },
    [options?.onNotification],
  );

  useWebSocketEvent(events, "task:updated", onTaskUpdated, [onTaskUpdated]);
  useWebSocketEvent(events, "task:created", onTaskCreated, [onTaskCreated]);
  useWebSocketEvent(events, "project:updated", onProjectUpdated, [onProjectUpdated]);
  useWebSocketEvent(events, "notification", onNotification, [onNotification]);
}
