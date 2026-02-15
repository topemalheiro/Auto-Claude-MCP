"use client";

import { useState, useCallback } from "react";
import { FolderOpen, ArrowLeft, ArrowRight } from "lucide-react";
import { useTranslation } from "react-i18next";

interface ProjectSetupStepProps {
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

export function ProjectSetupStep({ onNext, onBack, onSkip }: ProjectSetupStepProps) {
  const { t } = useTranslation("onboarding");
  const [projectPath, setProjectPath] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    const items = e.dataTransfer.items;
    if (items.length > 0) {
      const item = items[0];
      if (item.kind === "file") {
        const entry = item.webkitGetAsEntry?.();
        if (entry?.isDirectory) {
          setProjectPath(entry.fullPath || entry.name);
        }
      }
    }
  }, []);

  return (
    <div className="flex flex-col items-center px-8 py-6">
      <div className="w-full max-w-lg">
        <h2 className="mb-2 text-xl font-semibold text-foreground">
          {t("projectSetup.title")}
        </h2>
        <p className="mb-6 text-sm text-muted-foreground">
          {t("projectSetup.description")}
        </p>

        <div className="space-y-4">
          <div>
            <label
              htmlFor="project-path-input"
              className="mb-1.5 block text-sm font-medium text-foreground"
            >
              {t("projectSetup.pathLabel")}
            </label>
            <input
              id="project-path-input"
              type="text"
              value={projectPath}
              onChange={(e) => setProjectPath(e.target.value)}
              placeholder={t("projectSetup.pathPlaceholder")}
              className="w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="relative flex items-center gap-2 py-2">
            <div className="flex-1 border-t border-border" />
            <span className="text-xs text-muted-foreground">
              {t("projectSetup.orDragDrop")}
            </span>
            <div className="flex-1 border-t border-border" />
          </div>

          <button
            type="button"
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`w-full flex items-center gap-3 rounded-lg border-2 border-dashed p-6 transition-colors ${
              isDragOver
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/50 hover:bg-primary/5"
            }`}
          >
            <FolderOpen className="h-8 w-8 text-muted-foreground" />
            <div className="text-left">
              <p className="text-sm font-medium text-foreground">
                {t("projectSetup.dropZone.title")}
              </p>
              <p className="text-xs text-muted-foreground">
                {t("projectSetup.dropZone.description")}
              </p>
            </div>
          </button>
        </div>

        <div className="mt-8 flex items-center justify-between">
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 rounded-md px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            {t("actions.back")}
          </button>
          <div className="flex items-center gap-2">
            <button
              onClick={onSkip}
              className="rounded-md px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              {t("actions.skipForNow")}
            </button>
            <button
              onClick={onNext}
              className="flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              {projectPath.trim()
                ? t("actions.continue")
                : t("actions.skipForNow")}
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
