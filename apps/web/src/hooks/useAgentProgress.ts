"use client";

import { useCallback, useEffect, useState } from "react";
import { useWebSocket } from "@/providers/WebSocketProvider";
import { useWebSocketEvent } from "./useWebSocketEvent";
import type { AgentServerEvents } from "@/lib/websocket-client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AgentProgressState {
  /** Current subtask being worked on. */
  subtaskId: string | null;
  /** Human-readable status of the current step. */
  status: string | null;
  /** Optional progress message from the agent. */
  message: string | null;
  /** Whether the agent has started for this task. */
  isRunning: boolean;
  /** Completion result, if finished. */
  result: string | null;
  /** Error message, if failed. */
  error: string | null;
}

const INITIAL_STATE: AgentProgressState = {
  subtaskId: null,
  status: null,
  message: null,
  isRunning: false,
  result: null,
  error: null,
};

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Subscribe to agent progress events for a specific task.
 *
 * Replaces Electron's `window.electronAPI.onTaskProgress` IPC pattern
 * with WebSocket subscriptions on the `/agent` namespace.
 *
 * @param taskId - The task ID to monitor. Pass `null` to disable.
 */
export function useAgentProgress(taskId: string | null): AgentProgressState {
  const { agent } = useWebSocket();
  const [state, setState] = useState<AgentProgressState>(INITIAL_STATE);

  // Reset state when taskId changes
  useEffect(() => {
    setState(INITIAL_STATE);
  }, [taskId]);

  // --- Event handlers (stable via useCallback + taskId dep) ----------------

  const onProgress = useCallback(
    (data: Parameters<AgentServerEvents["progress"]>[0]) => {
      if (data.taskId !== taskId) return;
      setState((prev) => ({
        ...prev,
        subtaskId: data.subtaskId,
        status: data.status,
        message: data.message ?? prev.message,
      }));
    },
    [taskId],
  );

  const onStarted = useCallback(
    (data: Parameters<AgentServerEvents["started"]>[0]) => {
      if (data.taskId !== taskId) return;
      setState((prev) => ({
        ...prev,
        isRunning: true,
        error: null,
        result: null,
      }));
    },
    [taskId],
  );

  const onCompleted = useCallback(
    (data: Parameters<AgentServerEvents["completed"]>[0]) => {
      if (data.taskId !== taskId) return;
      setState((prev) => ({
        ...prev,
        isRunning: false,
        result: data.result,
      }));
    },
    [taskId],
  );

  const onFailed = useCallback(
    (data: Parameters<AgentServerEvents["failed"]>[0]) => {
      if (data.taskId !== taskId) return;
      setState((prev) => ({
        ...prev,
        isRunning: false,
        error: data.error,
      }));
    },
    [taskId],
  );

  // --- Socket subscriptions ------------------------------------------------

  useWebSocketEvent(taskId ? agent : null, "progress", onProgress, [onProgress]);
  useWebSocketEvent(taskId ? agent : null, "started", onStarted, [onStarted]);
  useWebSocketEvent(taskId ? agent : null, "completed", onCompleted, [onCompleted]);
  useWebSocketEvent(taskId ? agent : null, "failed", onFailed, [onFailed]);

  return state;
}
