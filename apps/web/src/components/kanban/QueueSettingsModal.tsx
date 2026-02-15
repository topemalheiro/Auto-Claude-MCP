"use client";

/**
 * QueueSettingsModal - Configure parallel task queue settings
 *
 * Allows users to set the maximum number of parallel tasks,
 * auto-promotion behavior, and queue processing preferences.
 */

import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { X, Settings, Minus, Plus } from "lucide-react";
import { cn } from "@auto-claude/ui";
import { DEFAULT_MAX_PARALLEL_TASKS, useTaskStore } from "@/stores/task-store";

interface QueueSettingsModalProps {
  open: boolean;
  onClose: () => void;
  projectId: string;
}

const QUEUE_SETTINGS_KEY_PREFIX = "queue-settings";

interface QueueSettings {
  maxParallelTasks: number;
  autoPromote: boolean;
  pauseOnError: boolean;
}

function getSettingsKey(projectId: string): string {
  return `${QUEUE_SETTINGS_KEY_PREFIX}-${projectId}`;
}

function loadSettings(projectId: string): QueueSettings {
  try {
    const raw = localStorage.getItem(getSettingsKey(projectId));
    if (raw) return JSON.parse(raw) as QueueSettings;
  } catch {
    // ignore
  }
  return {
    maxParallelTasks: DEFAULT_MAX_PARALLEL_TASKS,
    autoPromote: true,
    pauseOnError: false,
  };
}

function saveSettings(projectId: string, settings: QueueSettings): void {
  try {
    localStorage.setItem(getSettingsKey(projectId), JSON.stringify(settings));
  } catch {
    // ignore
  }
}

export function QueueSettingsModal({
  open,
  onClose,
  projectId,
}: QueueSettingsModalProps) {
  const { t } = useTranslation("kanban");

  const [maxParallel, setMaxParallel] = useState(DEFAULT_MAX_PARALLEL_TASKS);
  const [autoPromote, setAutoPromote] = useState(true);
  const [pauseOnError, setPauseOnError] = useState(false);

  // Load settings on open
  useEffect(() => {
    if (open && projectId) {
      const settings = loadSettings(projectId);
      setMaxParallel(settings.maxParallelTasks);
      setAutoPromote(settings.autoPromote);
      setPauseOnError(settings.pauseOnError);
    }
  }, [open, projectId]);

  // Escape key
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  const handleSave = useCallback(() => {
    saveSettings(projectId, {
      maxParallelTasks: maxParallel,
      autoPromote,
      pauseOnError,
    });
    onClose();
  }, [projectId, maxParallel, autoPromote, pauseOnError, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative z-10 w-full max-w-md overflow-hidden rounded-xl border border-border bg-card shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div className="flex items-center gap-2">
            <Settings className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">
              {t("queueSettings.title")}
            </h2>
          </div>
          <button
            className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-accent transition-colors"
            onClick={onClose}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Max parallel tasks */}
          <div>
            <label className="text-sm font-medium mb-2 block">
              {t("queueSettings.maxParallel")}
            </label>
            <p className="text-xs text-muted-foreground mb-3">
              {t("queueSettings.maxParallelDesc")}
            </p>
            <div className="flex items-center gap-3">
              <button
                className="flex h-8 w-8 items-center justify-center rounded-md border border-border hover:bg-accent transition-colors disabled:opacity-50"
                disabled={maxParallel <= 1}
                onClick={() => setMaxParallel((v) => Math.max(1, v - 1))}
              >
                <Minus className="h-4 w-4" />
              </button>
              <span className="text-lg font-semibold w-8 text-center">
                {maxParallel}
              </span>
              <button
                className="flex h-8 w-8 items-center justify-center rounded-md border border-border hover:bg-accent transition-colors disabled:opacity-50"
                disabled={maxParallel >= 12}
                onClick={() => setMaxParallel((v) => Math.min(12, v + 1))}
              >
                <Plus className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Auto-promote */}
          <div className="flex items-center gap-3 rounded-lg border border-border p-4">
            <input
              type="checkbox"
              id="autoPromote"
              checked={autoPromote}
              onChange={(e) => setAutoPromote(e.target.checked)}
              className="h-4 w-4 rounded border-border"
            />
            <label htmlFor="autoPromote" className="text-sm">
              <span className="font-medium">
                {t("queueSettings.autoPromote")}
              </span>
              <p className="text-xs text-muted-foreground mt-0.5">
                {t("queueSettings.autoPromoteDesc")}
              </p>
            </label>
          </div>

          {/* Pause on error */}
          <div className="flex items-center gap-3 rounded-lg border border-border p-4">
            <input
              type="checkbox"
              id="pauseOnError"
              checked={pauseOnError}
              onChange={(e) => setPauseOnError(e.target.checked)}
              className="h-4 w-4 rounded border-border"
            />
            <label htmlFor="pauseOnError" className="text-sm">
              <span className="font-medium">
                {t("queueSettings.pauseOnError")}
              </span>
              <p className="text-xs text-muted-foreground mt-0.5">
                {t("queueSettings.pauseOnErrorDesc")}
              </p>
            </label>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-border px-6 py-4">
          <button
            className="rounded-md px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            onClick={onClose}
          >
            {t("wizard.cancel")}
          </button>
          <button
            className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 transition-colors"
            onClick={handleSave}
          >
            {t("queueSettings.save")}
          </button>
        </div>
      </div>
    </div>
  );
}
