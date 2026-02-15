"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Sparkles,
  Key,
  FolderOpen,
  CheckCircle2,
  Shield,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useTranslation } from "react-i18next";
import { useSettingsStore } from "@/stores/settings-store";
import { WelcomeStep } from "./WelcomeStep";
import { AuthChoiceStep } from "./AuthChoiceStep";
import { APIKeyStep } from "./APIKeyStep";
import { ProjectSetupStep } from "./ProjectSetupStep";
import { CompletionStep } from "./CompletionStep";

interface OnboardingWizardProps {
  open: boolean;
  onClose: () => void;
  onOpenSettings?: () => void;
}

type WizardStepId = "welcome" | "auth-choice" | "api-key" | "project" | "complete";

const WIZARD_STEPS: { id: WizardStepId; titleKey: string; icon: React.ElementType }[] = [
  { id: "welcome", titleKey: "steps.welcome", icon: Sparkles },
  { id: "auth-choice", titleKey: "steps.authChoice", icon: Shield },
  { id: "api-key", titleKey: "steps.apiKey", icon: Key },
  { id: "project", titleKey: "steps.project", icon: FolderOpen },
  { id: "complete", titleKey: "steps.complete", icon: CheckCircle2 },
];

/**
 * Multi-step onboarding wizard adapted for web.
 * Shows on first visit (controlled by onboardingCompleted in settings).
 * Skips Electron-specific steps (Claude Code CLI, Python environment, Graphiti).
 */
export function OnboardingWizard({ open, onClose, onOpenSettings }: OnboardingWizardProps) {
  const { t } = useTranslation("onboarding");
  const { updateSettings } = useSettingsStore();
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<WizardStepId>>(new Set());

  const currentStepId = WIZARD_STEPS[currentStepIndex].id;

  // Escape key to close
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  const goToNextStep = useCallback(() => {
    setCompletedSteps((prev) => new Set(prev).add(currentStepId));
    if (currentStepIndex < WIZARD_STEPS.length - 1) {
      setCurrentStepIndex((prev) => prev + 1);
    }
  }, [currentStepIndex, currentStepId]);

  const goToPreviousStep = useCallback(() => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex((prev) => prev - 1);
    }
  }, [currentStepIndex]);

  const completeWizard = useCallback(() => {
    updateSettings({ onboardingCompleted: true });
    onClose();
    setCurrentStepIndex(0);
    setCompletedSteps(new Set());
  }, [updateSettings, onClose]);

  // Skip directly to project step when API key path is chosen
  const handleAPIKeyPathChosen = useCallback(() => {
    setCompletedSteps((prev) => {
      const next = new Set(prev);
      next.add("auth-choice");
      next.add("api-key");
      return next;
    });
    const apiKeyIndex = WIZARD_STEPS.findIndex((s) => s.id === "api-key");
    setCurrentStepIndex(apiKeyIndex);
  }, []);

  const handleOpenSettings = useCallback(() => {
    completeWizard();
    onOpenSettings?.();
  }, [completeWizard, onOpenSettings]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-background/80 backdrop-blur-sm" />
      <div className="relative z-10 flex w-full max-w-2xl flex-col rounded-xl border border-border bg-card shadow-2xl">
        {/* Step progress indicator */}
        <div className="flex items-center justify-center gap-2 border-b border-border px-6 py-4">
          {WIZARD_STEPS.map((step, idx) => {
            const Icon = step.icon;
            const isActive = idx === currentStepIndex;
            const isComplete = completedSteps.has(step.id) || idx < currentStepIndex;
            return (
              <div key={step.id} className="flex items-center">
                <div
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full transition-colors",
                    isActive && "bg-primary text-primary-foreground",
                    isComplete && !isActive && "bg-green-500/10 text-green-600",
                    !isActive && !isComplete && "bg-secondary text-muted-foreground"
                  )}
                  title={t(step.titleKey)}
                >
                  {isComplete && !isActive ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : (
                    <Icon className="h-4 w-4" />
                  )}
                </div>
                {idx < WIZARD_STEPS.length - 1 && (
                  <div
                    className={cn(
                      "mx-2 h-px w-8",
                      idx < currentStepIndex ? "bg-green-500" : "bg-border"
                    )}
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Step content */}
        <div className="min-h-[400px] overflow-y-auto">
          {currentStepId === "welcome" && (
            <WelcomeStep onGetStarted={goToNextStep} onSkip={completeWizard} />
          )}
          {currentStepId === "auth-choice" && (
            <AuthChoiceStep
              onNext={goToNextStep}
              onBack={goToPreviousStep}
              onSkip={completeWizard}
              onAPIKeyPathChosen={handleAPIKeyPathChosen}
            />
          )}
          {currentStepId === "api-key" && (
            <APIKeyStep
              onNext={goToNextStep}
              onBack={goToPreviousStep}
              onSkip={goToNextStep}
            />
          )}
          {currentStepId === "project" && (
            <ProjectSetupStep
              onNext={goToNextStep}
              onBack={goToPreviousStep}
              onSkip={goToNextStep}
            />
          )}
          {currentStepId === "complete" && (
            <CompletionStep
              onComplete={completeWizard}
              onOpenSettings={handleOpenSettings}
            />
          )}
        </div>
      </div>
    </div>
  );
}
