"use client";

import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/data";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface FileNode {
  /** File or directory name. */
  name: string;
  /** Full relative path from project root. */
  path: string;
  /** Whether this is a directory. */
  isDirectory: boolean;
  /** Child nodes (populated for expanded directories). */
  children?: FileNode[];
}

export interface FileExplorerState {
  /** Root-level file tree entries. */
  tree: FileNode[];
  /** Paths of currently expanded directories. */
  expandedPaths: Set<string>;
  /** Whether the initial tree is loading. */
  isLoading: boolean;
  /** Error message, if the fetch failed. */
  error: string | null;
}

export interface FileExplorerActions {
  /** Expand a directory, loading its children from the API. */
  expand: (path: string) => Promise<void>;
  /** Collapse a directory. */
  collapse: (path: string) => void;
  /** Toggle expand/collapse. */
  toggle: (path: string) => Promise<void>;
  /** Refresh the entire tree. */
  refresh: () => Promise<void>;
}

// ---------------------------------------------------------------------------
// API helper
// ---------------------------------------------------------------------------

interface FileListResponse {
  files: FileNode[];
}

async function fetchFileTree(
  projectId: string,
  dirPath?: string,
  signal?: AbortSignal,
): Promise<FileNode[]> {
  const params = dirPath ? `?path=${encodeURIComponent(dirPath)}` : "";
  const url = `/api/projects/${projectId}/files${params}`;

  // Use a raw fetch since apiClient doesn't have a files endpoint yet
  const response = await fetch(`${apiClient["baseUrl"] ?? ""}${url}`, {
    signal,
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    throw new Error(`Failed to load files: ${response.status}`);
  }

  const data: FileListResponse = await response.json();
  return data.files ?? [];
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Manage a lazy-loaded file tree for a project.
 *
 * Replaces Electron's IPC-based file explorer with REST API calls.
 * Directories are loaded on demand when expanded to keep payloads small.
 *
 * @param projectId - The project whose files to explore. Pass `null` to disable.
 */
export function useFileExplorer(
  projectId: string | null,
): FileExplorerState & FileExplorerActions {
  const [tree, setTree] = useState<FileNode[]>([]);
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // --- Load root tree on mount / projectId change --------------------------

  const loadRoot = useCallback(async () => {
    if (!projectId) {
      setTree([]);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const files = await fetchFileTree(projectId);
      setTree(files);
      setExpandedPaths(new Set());
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : "Failed to load file tree");
      setTree([]);
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadRoot();
  }, [loadRoot]);

  // --- Expand / collapse helpers -------------------------------------------

  /**
   * Recursively insert children into the tree at the given path.
   */
  function insertChildren(
    nodes: FileNode[],
    targetPath: string,
    children: FileNode[],
  ): FileNode[] {
    return nodes.map((node) => {
      if (node.path === targetPath) {
        return { ...node, children };
      }
      if (node.children && targetPath.startsWith(node.path + "/")) {
        return {
          ...node,
          children: insertChildren(node.children, targetPath, children),
        };
      }
      return node;
    });
  }

  const expand = useCallback(
    async (path: string) => {
      if (!projectId) return;

      try {
        const children = await fetchFileTree(projectId, path);
        setTree((prev) => insertChildren(prev, path, children));
        setExpandedPaths((prev) => new Set([...prev, path]));
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Failed to load directory");
      }
    },
    [projectId],
  );

  const collapse = useCallback((path: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      // Remove path and all descendants
      for (const p of next) {
        if (p === path || p.startsWith(path + "/")) {
          next.delete(p);
        }
      }
      return next;
    });
  }, []);

  const toggle = useCallback(
    async (path: string) => {
      if (expandedPaths.has(path)) {
        collapse(path);
      } else {
        await expand(path);
      }
    },
    [expandedPaths, expand, collapse],
  );

  return {
    tree,
    expandedPaths,
    isLoading,
    error,
    expand,
    collapse,
    toggle,
    refresh: loadRoot,
  };
}
