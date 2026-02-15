"use client";

import { Sparkles, Zap, Brain, FileCode } from "lucide-react";
import { useTranslation } from "react-i18next";

interface WelcomeStepProps {
  onGetStarted: () => void;
  onSkip: () => void;
}

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
}

function FeatureCard({ icon, title, description }: FeatureCardProps) {
  return (
    <div className="rounded-lg border border-border bg-card/50 p-4">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          {icon}
        </div>
        <div>
          <h3 className="font-medium text-foreground">{title}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        </div>
      </div>
    </div>
  );
}

export function WelcomeStep({ onGetStarted, onSkip }: WelcomeStepProps) {
  const { t } = useTranslation("onboarding");

  const features = [
    {
      icon: <Sparkles className="h-5 w-5" />,
      title: t("welcome.features.aiPowered.title"),
      description: t("welcome.features.aiPowered.description"),
    },
    {
      icon: <FileCode className="h-5 w-5" />,
      title: t("welcome.features.specDriven.title"),
      description: t("welcome.features.specDriven.description"),
    },
    {
      icon: <Brain className="h-5 w-5" />,
      title: t("welcome.features.memory.title"),
      description: t("welcome.features.memory.description"),
    },
    {
      icon: <Zap className="h-5 w-5" />,
      title: t("welcome.features.parallel.title"),
      description: t("welcome.features.parallel.description"),
    },
  ];

  return (
    <div className="flex flex-col items-center px-8 py-6">
      <div className="w-full max-w-2xl">
        <div className="mb-8 text-center">
          <div className="mb-6 flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
              <Sparkles className="h-8 w-8 text-primary" />
            </div>
          </div>
          <h2 className="text-2xl font-bold text-foreground tracking-tight">
            {t("welcome.title")}
          </h2>
          <p className="mt-3 text-muted-foreground">
            {t("welcome.subtitle")}
          </p>
        </div>

        <div className="mb-10 grid grid-cols-1 gap-4 md:grid-cols-2">
          {features.map((feature, index) => (
            <FeatureCard
              key={index}
              icon={feature.icon}
              title={feature.title}
              description={feature.description}
            />
          ))}
        </div>

        <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <button
            onClick={onGetStarted}
            className="flex items-center gap-2 rounded-lg bg-primary px-8 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Sparkles className="h-5 w-5" />
            {t("welcome.getStarted")}
          </button>
          <button
            onClick={onSkip}
            className="rounded-lg px-4 py-3 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            {t("welcome.skip")}
          </button>
        </div>
      </div>
    </div>
  );
}
