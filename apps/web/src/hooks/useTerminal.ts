"use client";

import { useCallback, useEffect, useRef } from "react";
import { terminalSocket } from "@/lib/websocket-client";
import { useTerminalStore } from "@/stores/terminal-store";

/**
 * Hook for terminal session management via WebSocket.
 * Handles creation, destruction, input writing, and resize events.
 */
export function useTerminal(sessionId: string | null) {
  const isConnectedRef = useRef(false);

  const setTerminalStatus = useTerminalStore((s) => s.setTerminalStatus);
  const removeTerminal = useTerminalStore((s) => s.removeTerminal);

  // Track connection state
  useEffect(() => {
    if (!sessionId) return;

    const handleConnect = () => {
      isConnectedRef.current = true;
    };
    const handleDisconnect = () => {
      isConnectedRef.current = false;
    };

    terminalSocket.on("connect", handleConnect);
    terminalSocket.on("disconnect", handleDisconnect);
    isConnectedRef.current = terminalSocket.connected;

    return () => {
      terminalSocket.off("connect", handleConnect);
      terminalSocket.off("disconnect", handleDisconnect);
    };
  }, [sessionId]);

  // Listen for exit/error events for this session
  useEffect(() => {
    if (!sessionId) return;

    const handleExit = (data: { sessionId: string; code: number }) => {
      if (data.sessionId === sessionId) {
        setTerminalStatus(sessionId, "exited");
      }
    };

    const handleError = (data: { sessionId: string; error: string }) => {
      if (data.sessionId === sessionId) {
        setTerminalStatus(sessionId, "exited");
      }
    };

    terminalSocket.on("exit", handleExit);
    terminalSocket.on("error", handleError);

    return () => {
      terminalSocket.off("exit", handleExit);
      terminalSocket.off("error", handleError);
    };
  }, [sessionId, setTerminalStatus]);

  /** Create a terminal session on the backend */
  const create = useCallback(
    (cwd?: string) => {
      if (!sessionId) return;
      terminalSocket.emit("create", { sessionId, cwd });
      setTerminalStatus(sessionId, "running");
    },
    [sessionId, setTerminalStatus],
  );

  /** Write data to the terminal */
  const write = useCallback(
    (data: string) => {
      if (!sessionId) return;
      terminalSocket.emit("input", { sessionId, data });
    },
    [sessionId],
  );

  /** Resize the terminal */
  const resize = useCallback(
    (cols: number, rows: number) => {
      if (!sessionId) return;
      terminalSocket.emit("resize", { sessionId, cols, rows });
    },
    [sessionId],
  );

  /** Kill and remove the terminal session */
  const close = useCallback(() => {
    if (!sessionId) return;
    terminalSocket.emit("kill", { sessionId });
    removeTerminal(sessionId);
  }, [sessionId, removeTerminal]);

  return { create, write, resize, close };
}
