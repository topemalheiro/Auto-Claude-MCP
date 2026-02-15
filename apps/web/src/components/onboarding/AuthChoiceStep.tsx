"use client";

import { useState } from "react";
import { Shield, Key, ArrowLeft, ArrowRight } from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useTranslation } from "react-i18next";

interface AuthChoiceStepProps {
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
  onAPIKeyPathChosen: () => void;
}

type AuthMethod = "oauth" | "api-key";

export function AuthChoiceStep({
  onNext,
  onBack,
  onSkip,
  onAPIKeyPathChosen,
}: AuthChoiceStepProps) {
  const { t } = useTranslation("onboarding");
  const [selected, setSelected] = useState<AuthMethod>("oauth");

  const handleContinue = () => {
    if (selected === "api-key") {
      onAPIKeyPathChosen();
    } else {
      onNext();
    }
  };

  return (
    <div className="flex flex-col items-center px-8 py-6">
      <div className="w-full max-w-lg">
        <h2 className="mb-2 text-xl font-semibold text-foreground">
          {t("authChoice.title")}
        </h2>
        <p className="mb-6 text-sm text-muted-foreground">
          {t("authChoice.description")}
        </p>

        <div className="space-y-3">
          <button
            type="button"
            onClick={() => setSelected("oauth")}
            className={cn(
              "w-full rounded-lg border-2 p-4 text-left transition-colors",
              selected === "oauth"
                ? "border-primary bg-primary/5"
                : "border-border hover:border-border/80"
            )}
          >
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Shield className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">
                  {t("authChoice.oauth.title")}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {t("authChoice.oauth.description")}
                </p>
              </div>
            </div>
          </button>

          <button
            type="button"
            onClick={() => setSelected("api-key")}
            className={cn(
              "w-full rounded-lg border-2 p-4 text-left transition-colors",
              selected === "api-key"
                ? "border-primary bg-primary/5"
                : "border-border hover:border-border/80"
            )}
          >
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Key className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">
                  {t("authChoice.apiKey.title")}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {t("authChoice.apiKey.description")}
                </p>
              </div>
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
          <button
            onClick={handleContinue}
            className="flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            {t("actions.continue")}
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
