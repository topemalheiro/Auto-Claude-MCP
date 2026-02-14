import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { TaskStatus } from "@auto-claude/types";

export interface KanbanColumnPreference {
  width: number;
  isCollapsed: boolean;
  isLocked: boolean;
}

export type KanbanColumnPreferences = Partial<
  Record<TaskStatus, KanbanColumnPreference>
>;

/** Default column width in pixels */
export const DEFAULT_COLUMN_WIDTH = 320;
/** Minimum column width in pixels */
export const MIN_COLUMN_WIDTH = 180;
/** Maximum column width in pixels */
export const MAX_COLUMN_WIDTH = 600;
/** Collapsed column width in pixels */
export const COLLAPSED_COLUMN_WIDTH = 48;

const DISPLAY_COLUMNS: TaskStatus[] = [
  "backlog",
  "queue",
  "in_progress",
  "ai_review",
  "human_review",
  "done",
];

function createDefaultPreferences(): KanbanColumnPreferences {
  const preferences: KanbanColumnPreferences = {};
  for (const column of DISPLAY_COLUMNS) {
    preferences[column] = {
      width: DEFAULT_COLUMN_WIDTH,
      isCollapsed: false,
      isLocked: false,
    };
  }
  return preferences;
}

function clampWidth(width: number): number {
  return Math.max(MIN_COLUMN_WIDTH, Math.min(MAX_COLUMN_WIDTH, width));
}

interface KanbanSettingsState {
  columnPreferences: KanbanColumnPreferences | null;

  // Actions
  initializePreferences: () => void;
  setColumnWidth: (column: TaskStatus, width: number) => void;
  toggleColumnCollapsed: (column: TaskStatus) => void;
  setColumnCollapsed: (column: TaskStatus, isCollapsed: boolean) => void;
  toggleColumnLocked: (column: TaskStatus) => void;
  setColumnLocked: (column: TaskStatus, isLocked: boolean) => void;
  resetPreferences: () => void;
  getColumnPreferences: (column: TaskStatus) => KanbanColumnPreference;
}

export const useKanbanSettingsStore = create<KanbanSettingsState>()(
  persist(
    (set, get) => ({
      columnPreferences: null,

      initializePreferences: () => {
        const state = get();
        if (!state.columnPreferences) {
          set({ columnPreferences: createDefaultPreferences() });
        }
      },

      setColumnWidth: (column, width) => {
        set((state) => {
          if (!state.columnPreferences) return state;
          const pref = state.columnPreferences[column];
          if (pref?.isLocked) return state;
          return {
            columnPreferences: {
              ...state.columnPreferences,
              [column]: {
                ...(pref ?? { isCollapsed: false, isLocked: false }),
                width: clampWidth(width),
              },
            },
          };
        });
      },

      toggleColumnCollapsed: (column) => {
        set((state) => {
          if (!state.columnPreferences) return state;
          const pref = state.columnPreferences[column];
          return {
            columnPreferences: {
              ...state.columnPreferences,
              [column]: {
                ...(pref ?? { width: DEFAULT_COLUMN_WIDTH, isLocked: false }),
                isCollapsed: !(pref?.isCollapsed ?? false),
              },
            },
          };
        });
      },

      setColumnCollapsed: (column, isCollapsed) => {
        set((state) => {
          if (!state.columnPreferences) return state;
          const pref = state.columnPreferences[column];
          return {
            columnPreferences: {
              ...state.columnPreferences,
              [column]: {
                ...(pref ?? { width: DEFAULT_COLUMN_WIDTH, isLocked: false }),
                isCollapsed,
              },
            },
          };
        });
      },

      toggleColumnLocked: (column) => {
        set((state) => {
          if (!state.columnPreferences) return state;
          const pref = state.columnPreferences[column];
          return {
            columnPreferences: {
              ...state.columnPreferences,
              [column]: {
                ...(pref ?? { width: DEFAULT_COLUMN_WIDTH, isCollapsed: false }),
                isLocked: !(pref?.isLocked ?? false),
              },
            },
          };
        });
      },

      setColumnLocked: (column, isLocked) => {
        set((state) => {
          if (!state.columnPreferences) return state;
          const pref = state.columnPreferences[column];
          return {
            columnPreferences: {
              ...state.columnPreferences,
              [column]: {
                ...(pref ?? { width: DEFAULT_COLUMN_WIDTH, isCollapsed: false }),
                isLocked,
              },
            },
          };
        });
      },

      resetPreferences: () => {
        set({ columnPreferences: createDefaultPreferences() });
      },

      getColumnPreferences: (column) => {
        const state = get();
        if (!state.columnPreferences || !state.columnPreferences[column]) {
          return {
            width: DEFAULT_COLUMN_WIDTH,
            isCollapsed: false,
            isLocked: false,
          };
        }
        return state.columnPreferences[column]!;
      },
    }),
    {
      name: "kanban-column-prefs",
      storage: createJSONStorage(() => localStorage),
      skipHydration: true,
    },
  ),
);
