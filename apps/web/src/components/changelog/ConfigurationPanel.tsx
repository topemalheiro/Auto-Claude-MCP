"use client";

import {
  ArrowLeft,
  FileText,
  GitCommit,
  Sparkles,
  RefreshCw,
  AlertCircle,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import type {
  ChangelogFormat,
  ChangelogAudience,
  ChangelogEmojiLevel,
  ChangelogSourceMode,
  ChangelogGenerationProgress,
} from "@/stores/changelog-store";

const FORMAT_OPTIONS: {
  value: ChangelogFormat;
  label: string;
  description: string;
}[] = [
  {
    value: "keep-a-changelog",
    label: "Keep a Changelog",
    description: "Standard format with Added, Changed, Fixed, Removed sections",
  },
  {
    value: "conventional",
    label: "Conventional",
    description: "Based on Conventional Commits specification",
  },
  {
    value: "custom",
    label: "Custom",
    description: "AI determines the best format",
  },
];

const AUDIENCE_OPTIONS: {
  value: ChangelogAudience;
  label: string;
  description: string;
}[] = [
  {
    value: "user-facing",
    label: "User-Facing",
    description: "Focus on features and fixes visible to end users",
  },
  {
    value: "developer",
    label: "Developer",
    description: "Include technical details and internal changes",
  },
  {
    value: "all",
    label: "All",
    description: "Comprehensive changelog for all audiences",
  },
];

const EMOJI_OPTIONS: {
  value: ChangelogEmojiLevel;
  label: string;
  description: string;
}[] = [
  { value: "none", label: "None", description: "No emojis" },
  {
    value: "minimal",
    label: "Minimal",
    description: "Section headers only",
  },
  { value: "full", label: "Full", description: "Emojis throughout" },
];

interface ConfigurationPanelProps {
  sourceMode: ChangelogSourceMode;
  selectedCount: number;
  existingChangelog: { lastVersion?: string } | null;
  version: string;
  date: string;
  format: ChangelogFormat;
  audience: ChangelogAudience;
  emojiLevel: ChangelogEmojiLevel;
  customInstructions: string;
  generationProgress: ChangelogGenerationProgress | null;
  isGenerating: boolean;
  error: string | null;
  canGenerate: boolean;
  onBack: () => void;
  onVersionChange: (v: string) => void;
  onDateChange: (d: string) => void;
  onFormatChange: (f: ChangelogFormat) => void;
  onAudienceChange: (a: ChangelogAudience) => void;
  onEmojiLevelChange: (l: ChangelogEmojiLevel) => void;
  onCustomInstructionsChange: (i: string) => void;
  onGenerate: () => void;
}

export function ConfigurationPanel({
  sourceMode,
  selectedCount,
  existingChangelog,
  version,
  date,
  format,
  audience,
  emojiLevel,
  customInstructions,
  generationProgress,
  isGenerating,
  error,
  canGenerate,
  onBack,
  onVersionChange,
  onDateChange,
  onFormatChange,
  onAudienceChange,
  onEmojiLevelChange,
  onCustomInstructionsChange,
  onGenerate,
}: ConfigurationPanelProps) {
  const { t } = useTranslation("views");

  return (
    <div className="w-80 shrink-0 border-r border-border overflow-y-auto">
      <div className="p-6 space-y-6">
        {/* Back button and summary */}
        <div className="space-y-4">
          <button
            type="button"
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors -ml-2 px-2 py-1 rounded-md hover:bg-accent"
            onClick={onBack}
          >
            <ArrowLeft className="h-4 w-4" />
            {t("changelog.config.backToSelection")}
          </button>
          <div className="rounded-lg bg-muted/50 p-3">
            <div className="flex items-center gap-2 text-sm font-medium">
              {sourceMode === "tasks" ? (
                <FileText className="h-4 w-4" />
              ) : (
                <GitCommit className="h-4 w-4" />
              )}
              {t("changelog.config.including", { count: selectedCount })}
            </div>
          </div>
        </div>

        {/* Version & Date */}
        <div className="rounded-lg border border-border p-4 space-y-4">
          <h3 className="text-sm font-medium">
            {t("changelog.config.releaseInfo")}
          </h3>
          <div className="space-y-2">
            <label className="text-xs text-muted-foreground">Version</label>
            <input
              type="text"
              value={version}
              onChange={(e) => onVersionChange(e.target.value)}
              placeholder="1.0.0"
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-muted-foreground">Date</label>
            <input
              type="date"
              value={date}
              onChange={(e) => onDateChange(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
          </div>
          {existingChangelog?.lastVersion && (
            <p className="text-xs text-muted-foreground">
              Previous: {existingChangelog.lastVersion}
            </p>
          )}
        </div>

        {/* Format & Audience */}
        <div className="rounded-lg border border-border p-4 space-y-4">
          <h3 className="text-sm font-medium">
            {t("changelog.config.outputStyle")}
          </h3>

          <div className="space-y-2">
            <label className="text-xs text-muted-foreground">Format</label>
            <select
              value={format}
              onChange={(e) =>
                onFormatChange(e.target.value as ChangelogFormat)
              }
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            >
              {FORMAT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-xs text-muted-foreground">Audience</label>
            <select
              value={audience}
              onChange={(e) =>
                onAudienceChange(e.target.value as ChangelogAudience)
              }
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            >
              {AUDIENCE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-xs text-muted-foreground">Emojis</label>
            <select
              value={emojiLevel}
              onChange={(e) =>
                onEmojiLevelChange(e.target.value as ChangelogEmojiLevel)
              }
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            >
              {EMOJI_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Custom Instructions */}
        <div className="space-y-2">
          <label className="text-xs text-muted-foreground">
            Custom Instructions
          </label>
          <textarea
            value={customInstructions}
            onChange={(e) => onCustomInstructionsChange(e.target.value)}
            placeholder="Add any special instructions for the AI..."
            rows={3}
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm resize-none"
          />
          <p className="text-xs text-muted-foreground">
            Optional. Guide the AI on tone, specific details to include, etc.
          </p>
        </div>

        {/* Generate Button */}
        <button
          type="button"
          className="w-full flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
          onClick={onGenerate}
          disabled={!canGenerate}
        >
          {isGenerating ? (
            <>
              <RefreshCw className="h-4 w-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              {t("changelog.config.generate")}
            </>
          )}
        </button>

        {/* Progress */}
        {generationProgress && isGenerating && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span>{generationProgress.message}</span>
              <span>{generationProgress.progress}%</span>
            </div>
            <div className="h-2 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${generationProgress.progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
              <span className="text-destructive">{error}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
