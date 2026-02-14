"use client";

import { useState, useEffect } from "react";
import {
  Sparkles,
  Key,
  FolderOpen,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useTranslation } from "react-i18next";

interface OnboardingWizardProps {
  open: boolean;
  onClose: () => void;
}

type Step = "welcome" | "api-key" | "project" | "complete";

const STEP_IDS: { id: Step; titleKey: string; icon: React.ElementType }[] = [
  { id: "welcome", titleKey: "onboarding.steps.welcome", icon: Sparkles },
  { id: "api-key", titleKey: "onboarding.steps.apiKey", icon: Key },
  { id: "project", titleKey: "onboarding.steps.project", icon: FolderOpen },
  { id: "complete", titleKey: "onboarding.steps.complete", icon: CheckCircle2 },
];

export function OnboardingWizard({ open, onClose }: OnboardingWizardProps) {
  const [currentStep, setCurrentStep] = useState<Step>("welcome");
  const { t } = useTranslation("layout");

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const currentIndex = STEP_IDS.findIndex((s) => s.id === currentStep);

  const goNext = () => {
    if (currentIndex < STEP_IDS.length - 1) {
      setCurrentStep(STEP_IDS[currentIndex + 1].id);
    }
  };

  const goPrev = () => {
    if (currentIndex > 0) {
      setCurrentStep(STEP_IDS[currentIndex - 1].id);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-background/80 backdrop-blur-sm" />
      <div className="relative z-10 w-full max-w-lg rounded-xl border border-border bg-card shadow-2xl">
        {/* Progress */}
        <div className="flex items-center justify-center gap-2 border-b border-border px-6 py-4">
          {STEP_IDS.map((step, idx) => {
            const Icon = step.icon;
            const isActive = idx === currentIndex;
            const isComplete = idx < currentIndex;
            return (
              <div key={step.id} className="flex items-center">
                <div
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full transition-colors",
                    isActive && "bg-primary text-primary-foreground",
                    isComplete && "bg-green-500/10 text-green-600",
                    !isActive && !isComplete && "bg-secondary text-muted-foreground"
                  )}
                >
                  {isComplete ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : (
                    <Icon className="h-4 w-4" />
                  )}
                </div>
                {idx < STEP_IDS.length - 1 && (
                  <div
                    className={cn(
                      "mx-2 h-px w-8",
                      idx < currentIndex ? "bg-green-500" : "bg-border"
                    )}
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Content */}
        <div className="p-8">
          {currentStep === "welcome" && (
            <div className="text-center">
              <div className="mb-6 flex justify-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
                  <Sparkles className="h-8 w-8 text-primary" />
                </div>
              </div>
              <h2 className="text-xl font-semibold mb-2">
                {t("onboarding.title")}
              </h2>
              <p className="text-sm text-muted-foreground mb-4">
                {t("onboarding.titleDescription")}
              </p>
            </div>
          )}

          {currentStep === "api-key" && (
            <div>
              <h2 className="text-xl font-semibold mb-2">{t("onboarding.apiConfiguration.title")}</h2>
              <p className="text-sm text-muted-foreground mb-6">
                {t("onboarding.apiConfiguration.description")}
              </p>
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium">{t("onboarding.apiConfiguration.authMethod")}</label>
                  <div className="mt-2 grid grid-cols-2 gap-3">
                    <button className="rounded-lg border-2 border-primary bg-primary/5 p-4 text-left">
                      <p className="text-sm font-medium">{t("onboarding.apiConfiguration.claudeOAuth")}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {t("onboarding.apiConfiguration.claudeOAuthDescription")}
                      </p>
                    </button>
                    <button className="rounded-lg border border-border p-4 text-left hover:border-border/80 transition-colors">
                      <p className="text-sm font-medium">{t("onboarding.apiConfiguration.apiKey")}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {t("onboarding.apiConfiguration.apiKeyDescription")}
                      </p>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {currentStep === "project" && (
            <div>
              <h2 className="text-xl font-semibold mb-2">{t("onboarding.connectProject.title")}</h2>
              <p className="text-sm text-muted-foreground mb-6">
                {t("onboarding.connectProject.description")}
              </p>
              <div className="space-y-4">
                <button className="w-full flex items-center gap-3 rounded-lg border-2 border-dashed border-border p-6 hover:border-primary/50 hover:bg-primary/5 transition-colors">
                  <FolderOpen className="h-8 w-8 text-muted-foreground" />
                  <div className="text-left">
                    <p className="text-sm font-medium">{t("onboarding.connectProject.selectDirectory")}</p>
                    <p className="text-xs text-muted-foreground">
                      {t("onboarding.connectProject.selectDirectoryDescription")}
                    </p>
                  </div>
                </button>
              </div>
            </div>
          )}

          {currentStep === "complete" && (
            <div className="text-center">
              <div className="mb-6 flex justify-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-green-500/10">
                  <CheckCircle2 className="h-8 w-8 text-green-600" />
                </div>
              </div>
              <h2 className="text-xl font-semibold mb-2">{t("onboarding.complete.title")}</h2>
              <p className="text-sm text-muted-foreground mb-4">
                {t("onboarding.complete.description")}
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border px-6 py-4">
          <button
            className="flex items-center gap-1.5 rounded-md px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            onClick={currentStep === "welcome" ? onClose : goPrev}
          >
            {currentStep === "welcome" ? (
              t("onboarding.actions.skipSetup")
            ) : (
              <>
                <ArrowLeft className="h-3.5 w-3.5" />
                {t("onboarding.actions.back")}
              </>
            )}
          </button>
          <button
            className="flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 transition-colors"
            onClick={currentStep === "complete" ? onClose : goNext}
          >
            {currentStep === "complete" ? (
              t("onboarding.actions.getStarted")
            ) : (
              <>
                {t("onboarding.actions.continue")}
                <ArrowRight className="h-3.5 w-3.5" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
