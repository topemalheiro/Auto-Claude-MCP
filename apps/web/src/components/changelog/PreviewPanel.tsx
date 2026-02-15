"use client";

import { useState, useCallback } from "react";
import {
  FileText,
  Copy,
  CheckCircle,
  Github,
} from "lucide-react";
import { useTranslation } from "react-i18next";

interface PreviewPanelProps {
  generatedChangelog: string;
  canSave: boolean;
  onCopy: () => void;
  onChangelogEdit: (content: string) => void;
}

export function PreviewPanel({
  generatedChangelog,
  canSave,
  onCopy,
  onChangelogEdit,
}: PreviewPanelProps) {
  const { t } = useTranslation("views");
  const [viewMode, setViewMode] = useState<"markdown" | "preview">("markdown");
  const [copySuccess, setCopySuccess] = useState(false);

  const handleCopy = useCallback(() => {
    onCopy();
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 2000);
  }, [onCopy]);

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Preview Header */}
      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <div className="flex items-center gap-3">
          <h2 className="font-medium">{t("changelog.preview.title")}</h2>
          <div className="flex items-center gap-1 rounded-md border border-border p-1">
            <button
              type="button"
              className={`h-7 px-3 text-xs rounded-sm transition-colors ${
                viewMode === "markdown"
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-accent text-muted-foreground"
              }`}
              onClick={() => setViewMode("markdown")}
            >
              Markdown
            </button>
            <button
              type="button"
              className={`h-7 px-3 text-xs rounded-sm transition-colors ${
                viewMode === "preview"
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-accent text-muted-foreground"
              }`}
              onClick={() => setViewMode("preview")}
            >
              Preview
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm hover:bg-accent transition-colors disabled:opacity-50"
            onClick={handleCopy}
            disabled={!canSave}
          >
            {copySuccess ? (
              <CheckCircle className="h-3.5 w-3.5 text-green-500" />
            ) : (
              <Copy className="h-3.5 w-3.5" />
            )}
            {copySuccess
              ? t("changelog.preview.copied")
              : t("changelog.preview.copy")}
          </button>
          <button
            type="button"
            className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            disabled={!canSave}
          >
            <Github className="h-3.5 w-3.5" />
            {t("changelog.preview.createRelease")}
          </button>
        </div>
      </div>

      {/* Preview Content */}
      <div className="flex-1 overflow-hidden p-6">
        {generatedChangelog ? (
          viewMode === "markdown" ? (
            <textarea
              className="flex-1 w-full h-full resize-none rounded-md border border-border bg-background p-4 font-mono text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              value={generatedChangelog}
              onChange={(e) => onChangelogEdit(e.target.value)}
              placeholder="Generated changelog will appear here..."
            />
          ) : (
            <div className="h-full overflow-auto">
              <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap font-mono text-sm">
                {generatedChangelog}
              </div>
            </div>
          )
        ) : (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <FileText className="mx-auto h-12 w-12 text-muted-foreground/30" />
              <p className="mt-4 text-sm text-muted-foreground">
                {t("changelog.preview.empty")}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
