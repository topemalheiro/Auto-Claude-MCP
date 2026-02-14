import { useEffect } from "react";
import type { Socket } from "socket.io-client";

/**
 * Subscribe to a Socket.IO event with automatic cleanup on unmount.
 *
 * Replaces Electron's `window.electronAPI.on*` pattern with a generic
 * Socket.IO listener that auto-cleans when the component unmounts or
 * dependencies change.
 *
 * @param socket - The Socket.IO socket instance (from WebSocketProvider).
 * @param event  - The event name to listen for.
 * @param handler - Callback invoked with the event payload.
 * @param deps   - Additional dependency array entries (handler is NOT
 *                 included automatically — callers should stabilize it
 *                 with useCallback or pass a stable reference).
 */
export function useWebSocketEvent<T = unknown>(
  socket: Socket | null | undefined,
  event: string,
  handler: (data: T) => void,
  deps: React.DependencyList = [],
): void {
  useEffect(() => {
    if (!socket) return;

    socket.on(event, handler as (...args: unknown[]) => void);

    return () => {
      socket.off(event, handler as (...args: unknown[]) => void);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [socket, event, ...deps]);
}
