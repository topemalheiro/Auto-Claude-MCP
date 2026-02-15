"use client";

import { useState } from "react";
import { Brain, Scale, Zap, Sparkles, Sliders, Check } from "lucide-react";
import { cn } from "@auto-claude/ui";

export interface ModelConfig {
  profileId: string;
  model: string;
  thinkingLevel: string;
}

interface ModelProfile {
  id: string;
  name: string;
  model: string;
  thinkingLevel: string;
  icon: string;
  description: string;
}

const DEFAULT_PROFILES: ModelProfile[] = [
  {
    id: "complex",
    name: "Complex",
    model: "opus",
    thinkingLevel: "high",
    icon: "Brain",
    description: "Opus + High thinking",
  },
  {
    id: "balanced",
    name: "Balanced",
    model: "sonnet",
    thinkingLevel: "medium",
    icon: "Scale",
    description: "Sonnet + Medium thinking",
  },
  {
    id: "quick",
    name: "Quick",
    model: "haiku",
    thinkingLevel: "low",
    icon: "Zap",
    description: "Haiku + Low thinking",
  },
];

const iconMap: Record<string, React.ElementType> = {
  Brain,
  Scale,
  Zap,
  Sparkles,
  Sliders,
};

interface ModelSelectorProps {
  currentConfig?: ModelConfig;
  onConfigChange: (config: ModelConfig) => void;
  disabled?: boolean;
}

export function ModelSelector({
  currentConfig,
  onConfigChange,
  disabled,
}: ModelSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);

  const selectedProfileId = currentConfig?.profileId || "balanced";
  const profile = DEFAULT_PROFILES.find((p) => p.id === selectedProfileId);
  const Icon = profile
    ? iconMap[profile.icon] || Scale
    : iconMap.Scale;

  const getDisplayText = () => {
    return profile?.name || "Balanced";
  };

  const handleSelectProfile = (p: ModelProfile) => {
    onConfigChange({
      profileId: p.id,
      model: p.model,
      thinkingLevel: p.thinkingLevel,
    });
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <button
        className={cn(
          "flex h-8 items-center gap-2 rounded-md px-2 text-sm hover:bg-accent transition-colors",
          disabled && "opacity-50 pointer-events-none",
        )}
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        title={`Model: ${getDisplayText()}`}
      >
        <Icon className="h-4 w-4" />
        <span className="hidden text-xs text-muted-foreground sm:inline">
          {getDisplayText()}
        </span>
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 top-full mt-1 w-64 rounded-md border border-border bg-popover p-1 shadow-md z-50">
            <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground">
              Agent Profile
            </div>
            {DEFAULT_PROFILES.map((p) => {
              const ProfileIcon = iconMap[p.icon] || Brain;
              const isSelected = selectedProfileId === p.id;
              return (
                <button
                  key={p.id}
                  className="flex w-full cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent"
                  onClick={() => handleSelectProfile(p)}
                >
                  <ProfileIcon className="h-4 w-4 shrink-0" />
                  <div className="min-w-0 flex-1 text-left">
                    <div className="font-medium">{p.name}</div>
                    <div className="truncate text-xs text-muted-foreground">
                      {p.description}
                    </div>
                  </div>
                  {isSelected && (
                    <Check className="h-4 w-4 shrink-0 text-primary" />
                  )}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
