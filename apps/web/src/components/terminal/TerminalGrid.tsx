"use client";

import { useCallback, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import {
  DndContext,
  DragOverlay,
  type DragEndEvent,
  type DragStartEvent,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  closestCenter,
} from "@dnd-kit/core";
import {
  SortableContext,
  rectSortingStrategy,
  sortableKeyboardCoordinates,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Plus, TerminalSquare } from "lucide-react";
import type { Task } from "@auto-claude/types";
import { cn, Button } from "@auto-claude/ui";
import { useTerminalStore, type Terminal } from "@/stores/terminal-store";
import { useTerminal } from "@/hooks/useTerminal";
import { TerminalHeader } from "./TerminalHeader";
import type { WorktreeConfig } from "./WorktreeSelector";

// Dynamic import of TerminalPanel — requires browser APIs (xterm, WebGL)
const TerminalPanel = dynamic(
  () =>
    import("@/components/terminal/TerminalPanel").then((m) => m.TerminalPanel),
  { ssr: false, loading: () => <div className="h-full w-full bg-[#0B0B0F]" /> },
);

// ---------------------------------------------------------------------------
// SortableTerminalWrapper
// ---------------------------------------------------------------------------

interface SortableTerminalWrapperProps {
  terminal: Terminal;
  tasks: Task[];
  projectPath?: string;
  isExpanded: boolean;
  isHidden: boolean;
  onClose: (id: string) => void;
  onToggleExpand: (id: string) => void;
  onNewTaskClick?: () => void;
}

function SortableTerminalWrapper({
  terminal,
  tasks,
  projectPath,
  isExpanded,
  isHidden,
  onClose,
  onToggleExpand,
  onNewTaskClick,
}: SortableTerminalWrapperProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: terminal.id });

  const updateTerminal = useTerminalStore((s) => s.updateTerminal);
  const setAssociatedTask = useTerminalStore((s) => s.setAssociatedTask);
  const setActiveTerminal = useTerminalStore((s) => s.setActiveTerminal);

  const associatedTask = useMemo(
    () => tasks.find((t) => t.id === terminal.associatedTaskId),
    [tasks, terminal.associatedTaskId],
  );

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        "flex flex-col rounded-lg border border-border/50 bg-card/20 overflow-hidden",
        "min-h-[200px]",
        isDragging && "opacity-50 z-50",
        isHidden && "hidden",
        isExpanded && "col-span-full row-span-full",
      )}
      onClick={() => setActiveTerminal(terminal.id)}
      {...attributes}
    >
      <TerminalHeader
        terminalId={terminal.id}
        title={terminal.title}
        status={terminal.status}
        isClaudeMode={terminal.isClaudeMode}
        tasks={tasks}
        associatedTask={associatedTask}
        onClose={() => onClose(terminal.id)}
        onTitleChange={(newTitle) =>
          updateTerminal(terminal.id, { title: newTitle })
        }
        onTaskSelect={(taskId) => setAssociatedTask(terminal.id, taskId)}
        onClearTask={() => setAssociatedTask(terminal.id, undefined)}
        onNewTaskClick={onNewTaskClick}
        projectPath={projectPath}
        dragHandleListeners={listeners}
        isExpanded={isExpanded}
        onToggleExpand={() => onToggleExpand(terminal.id)}
      />
      <div className="flex-1 min-h-0">
        <TerminalPanel sessionId={terminal.id} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// TerminalGrid
// ---------------------------------------------------------------------------

interface TerminalGridProps {
  projectPath?: string;
  tasks?: Task[];
  onNewTaskClick?: () => void;
}

export function TerminalGrid({
  projectPath,
  tasks = [],
  onNewTaskClick,
}: TerminalGridProps) {
  const allTerminals = useTerminalStore((s) => s.terminals);
  const addTerminal = useTerminalStore((s) => s.addTerminal);
  const removeTerminal = useTerminalStore((s) => s.removeTerminal);
  const canAddTerminal = useTerminalStore((s) => s.canAddTerminal);
  const reorderTerminals = useTerminalStore((s) => s.reorderTerminals);

  const [expandedTerminalId, setExpandedTerminalId] = useState<string | null>(
    null,
  );
  const [activeDragId, setActiveDragId] = useState<string | null>(null);

  // Filter terminals for the current project
  const terminals = useMemo(
    () =>
      projectPath
        ? allTerminals.filter(
            (t) =>
              t.projectPath === projectPath ||
              (!t.projectPath && t.status !== "exited"),
          )
        : allTerminals.filter((t) => t.status !== "exited"),
    [allTerminals, projectPath],
  );

  const terminalIds = useMemo(() => terminals.map((t) => t.id), [terminals]);

  // useTerminal hook for creating sessions
  const { create: createSession } = useTerminal(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const handleAddTerminal = useCallback(() => {
    if (!canAddTerminal(projectPath)) return;
    const terminal = addTerminal(undefined, projectPath);
    if (terminal) {
      // Create backend session
      import("@/lib/websocket-client").then(({ terminalSocket }) => {
        terminalSocket.emit("create", {
          sessionId: terminal.id,
          cwd: projectPath,
        });
      });
    }
  }, [addTerminal, canAddTerminal, projectPath]);

  const handleClose = useCallback(
    (id: string) => {
      import("@/lib/websocket-client").then(({ terminalSocket }) => {
        terminalSocket.emit("kill", { sessionId: id });
      });
      removeTerminal(id);
      if (expandedTerminalId === id) {
        setExpandedTerminalId(null);
      }
    },
    [removeTerminal, expandedTerminalId],
  );

  const handleToggleExpand = useCallback(
    (id: string) => {
      setExpandedTerminalId((prev) => (prev === id ? null : id));
    },
    [],
  );

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveDragId(event.active.id as string);
  }, []);

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setActiveDragId(null);
      const { active, over } = event;
      if (over && active.id !== over.id) {
        reorderTerminals(active.id as string, over.id as string);
      }
    },
    [reorderTerminals],
  );

  // Compute grid columns based on terminal count
  const gridCols = useMemo(() => {
    const count = terminals.length;
    if (count <= 1) return "grid-cols-1";
    if (count <= 2) return "grid-cols-2";
    if (count <= 4) return "grid-cols-2";
    if (count <= 6) return "grid-cols-3";
    return "grid-cols-4";
  }, [terminals.length]);

  if (terminals.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-muted-foreground">
          <TerminalSquare className="h-12 w-12 opacity-30" />
          <p className="text-sm">No terminals open</p>
          <Button variant="outline" size="sm" onClick={handleAddTerminal}>
            <Plus className="h-4 w-4 mr-2" />
            New Terminal
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-2 p-2">
      {/* Tab bar */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1 flex-1 overflow-x-auto">
          {terminals.map((terminal) => (
            <button
              key={terminal.id}
              type="button"
              className={cn(
                "flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-colors",
                "hover:bg-muted",
                terminal.id === useTerminalStore.getState().activeTerminalId
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground",
              )}
              onClick={() =>
                useTerminalStore.getState().setActiveTerminal(terminal.id)
              }
            >
              <TerminalSquare className="h-3 w-3" />
              <span className="truncate max-w-24">{terminal.title}</span>
            </button>
          ))}
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 flex-shrink-0"
          onClick={handleAddTerminal}
          disabled={!canAddTerminal(projectPath)}
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {/* Terminal grid */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <SortableContext items={terminalIds} strategy={rectSortingStrategy}>
          <div
            className={cn(
              "grid flex-1 gap-2 auto-rows-fr",
              expandedTerminalId ? "grid-cols-1" : gridCols,
            )}
          >
            {terminals.map((terminal) => (
              <SortableTerminalWrapper
                key={terminal.id}
                terminal={terminal}
                tasks={tasks}
                projectPath={projectPath}
                isExpanded={expandedTerminalId === terminal.id}
                isHidden={
                  expandedTerminalId !== null &&
                  expandedTerminalId !== terminal.id
                }
                onClose={handleClose}
                onToggleExpand={handleToggleExpand}
                onNewTaskClick={onNewTaskClick}
              />
            ))}
          </div>
        </SortableContext>
        <DragOverlay>
          {activeDragId ? (
            <div className="rounded-lg border border-primary/50 bg-card/80 p-4 opacity-80 shadow-lg">
              <span className="text-xs text-muted-foreground">
                Moving terminal...
              </span>
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>
    </div>
  );
}
