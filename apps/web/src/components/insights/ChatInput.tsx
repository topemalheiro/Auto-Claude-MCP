"use client";

import { useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Send, Loader2 } from "lucide-react";
import { cn } from "@auto-claude/ui";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  isLoading: boolean;
  disabled?: boolean;
}

export function ChatInput({
  value,
  onChange,
  onSend,
  isLoading,
  disabled,
}: ChatInputProps) {
  const { t } = useTranslation("views");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="border-t border-border p-4">
      <div className="max-w-3xl mx-auto flex gap-2">
        <textarea
          ref={textareaRef}
          className="flex-1 resize-none rounded-lg border border-border bg-background px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary min-h-[80px]"
          placeholder={t("insights.placeholder")}
          rows={3}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || isLoading}
        />
        <button
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-lg transition-colors self-end",
            value.trim() && !isLoading
              ? "bg-primary text-primary-foreground hover:bg-primary/90"
              : "bg-secondary text-muted-foreground",
          )}
          onClick={onSend}
          disabled={!value.trim() || isLoading || disabled}
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </button>
      </div>
      <p className="mt-2 text-xs text-muted-foreground text-center">
        {t("insights.inputHint")}
      </p>
    </div>
  );
}
