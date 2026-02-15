"use client";

import { CheckCircle2, ArrowRight, Settings } from "lucide-react";
import { useTranslation } from "react-i18next";

interface CompletionStepProps {
  onComplete: () => void;
  onOpenSettings?: () => void;
}

export function CompletionStep({ onComplete, onOpenSettings }: CompletionStepProps) {
  const { t } = useTranslation("onboarding");

  return (
    <div className="flex flex-col items-center px-8 py-6">
      <div className="w-full max-w-lg text-center">
        <div className="mb-6 flex justify-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-green-500/10">
            <CheckCircle2 className="h-8 w-8 text-green-600" />
          </div>
        </div>

        <h2 className="mb-2 text-xl font-semibold text-foreground">
          {t("completion.title")}
        </h2>
        <p className="mb-8 text-sm text-muted-foreground">
          {t("completion.description")}
        </p>

        <div className="flex flex-col items-center gap-3">
          <button
            onClick={onComplete}
            className="flex items-center gap-2 rounded-lg bg-primary px-8 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            {t("completion.getStarted")}
            <ArrowRight className="h-4 w-4" />
          </button>

          {onOpenSettings && (
            <button
              onClick={onOpenSettings}
              className="flex items-center gap-2 rounded-md px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <Settings className="h-4 w-4" />
              {t("completion.openSettings")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
