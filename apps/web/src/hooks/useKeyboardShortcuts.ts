"use client";

import { useEffect } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface KeyboardShortcut {
  /** Human-readable label (e.g. "New Project"). */
  label: string;
  /** Key to match (e.g. "t", "k", "/"). Case-insensitive. */
  key: string;
  /** Require Cmd (macOS) / Ctrl (other). Default: true. */
  meta?: boolean;
  /** Require Shift. Default: false. */
  shift?: boolean;
  /** Action to execute when triggered. */
  action: () => void;
}

// ---------------------------------------------------------------------------
// Default shortcuts
// ---------------------------------------------------------------------------

/**
 * Create the default set of global keyboard shortcuts.
 *
 * Accepts callbacks so the consuming component can wire up navigation
 * and actions appropriate for its context.
 */
export function createDefaultShortcuts(actions: {
  onNewProject?: () => void;
  onSearch?: () => void;
  onToggleSidebar?: () => void;
  onSettings?: () => void;
}): KeyboardShortcut[] {
  const shortcuts: KeyboardShortcut[] = [];

  if (actions.onNewProject) {
    shortcuts.push({
      label: "New Project",
      key: "t",
      meta: true,
      action: actions.onNewProject,
    });
  }

  if (actions.onSearch) {
    shortcuts.push({
      label: "Search",
      key: "k",
      meta: true,
      action: actions.onSearch,
    });
  }

  if (actions.onToggleSidebar) {
    shortcuts.push({
      label: "Toggle Sidebar",
      key: "b",
      meta: true,
      action: actions.onToggleSidebar,
    });
  }

  if (actions.onSettings) {
    shortcuts.push({
      label: "Settings",
      key: ",",
      meta: true,
      action: actions.onSettings,
    });
  }

  return shortcuts;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Register global keyboard shortcuts.
 *
 * Replaces Electron's `globalShortcut` / accelerator pattern with
 * standard DOM `keydown` listeners that work in the browser.
 *
 * Shortcuts are ignored when the active element is an input, textarea,
 * or contentEditable to avoid interfering with typing.
 *
 * @param shortcuts - Array of shortcut definitions to register.
 */
export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[]): void {
  useEffect(() => {
    if (shortcuts.length === 0) return;

    function handleKeyDown(event: KeyboardEvent) {
      // Don't intercept when user is typing in an input
      const target = event.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "SELECT" ||
        target.isContentEditable
      ) {
        return;
      }

      const isMeta = event.metaKey || event.ctrlKey;

      for (const shortcut of shortcuts) {
        const requiresMeta = shortcut.meta !== false;
        const requiresShift = shortcut.shift === true;

        if (requiresMeta && !isMeta) continue;
        if (!requiresMeta && isMeta) continue;
        if (requiresShift && !event.shiftKey) continue;
        if (!requiresShift && event.shiftKey) continue;

        if (event.key.toLowerCase() === shortcut.key.toLowerCase()) {
          event.preventDefault();
          event.stopPropagation();
          shortcut.action();
          return;
        }
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [shortcuts]);
}
