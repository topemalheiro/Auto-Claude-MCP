"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
  Sparkles,
  Plus,
  PanelLeft,
  PanelLeftClose,
  MessageSquare,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import {
  useInsightsStore,
  type InsightsSessionSummary,
} from "@/stores/insights-store";
import { apiClient } from "@/lib/data/api-client";
import { ChatMessage, StreamingMessage, ThinkingIndicator } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { ChatHistorySidebar } from "./ChatHistorySidebar";
import { ModelSelector, type ModelConfig } from "./ModelSelector";

const SUGGESTION_KEYS = [
  "insights.suggestions.complexity",
  "insights.suggestions.security",
  "insights.suggestions.performance",
  "insights.suggestions.tests",
  "insights.suggestions.architecture",
] as const;

interface InsightsViewProps {
  projectId: string;
}

export function InsightsView({ projectId }: InsightsViewProps) {
  const { t } = useTranslation("views");

  const session = useInsightsStore((s) => s.session);
  const sessions = useInsightsStore((s) => s.sessions);
  const status = useInsightsStore((s) => s.status);
  const streamingContent = useInsightsStore((s) => s.streamingContent);
  const currentTool = useInsightsStore((s) => s.currentTool);
  const isLoadingSessions = useInsightsStore((s) => s.isLoadingSessions);

  const [inputValue, setInputValue] = useState("");
  const [showSidebar, setShowSidebar] = useState(true);
  const [modelConfig, setModelConfig] = useState<ModelConfig>({
    profileId: "balanced",
    model: "sonnet",
    thinkingLevel: "medium",
  });
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isUserAtBottom, setIsUserAtBottom] = useState(true);
  const abortRef = useRef<AbortController | null>(null);

  const SCROLL_BOTTOM_THRESHOLD = 100;

  const checkIfAtBottom = useCallback((el: HTMLElement) => {
    const { scrollTop, scrollHeight, clientHeight } = el;
    return scrollHeight - scrollTop - clientHeight <= SCROLL_BOTTOM_THRESHOLD;
  }, []);

  // Track scroll position
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onScroll = () => setIsUserAtBottom(checkIfAtBottom(el));
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, [checkIfAtBottom]);

  // Auto-scroll when at bottom
  useEffect(() => {
    if (isUserAtBottom && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [isUserAtBottom, streamingContent, session?.messages?.length]);

  const isLoading =
    status.phase === "thinking" || status.phase === "responding";
  const messages = session?.messages ?? [];

  const handleSend = async () => {
    const message = inputValue.trim();
    if (!message || isLoading) return;

    setInputValue("");
    setIsUserAtBottom(true);

    const store = useInsightsStore.getState();

    // Add user message
    store.addMessage({
      id: `msg-${Date.now()}`,
      role: "user",
      content: message,
      timestamp: new Date(),
    });

    store.setStatus({ phase: "thinking", message: "" });
    store.clearStreamingContent();

    // Start streaming
    abortRef.current = new AbortController();
    try {
      for await (const event of apiClient.streamInsights(
        projectId,
        message,
        abortRef.current.signal,
      )) {
        const s = useInsightsStore.getState();
        if (event.type === "chunk" && event.content) {
          if (s.status.phase === "thinking") {
            s.setStatus({ phase: "responding", message: "" });
          }
          s.appendStreamingContent(event.content);
        } else if (event.type === "done") {
          s.finalizeStreamingMessage();
          s.setStatus({ phase: "idle", message: "" });
        } else if (event.type === "error") {
          s.setStatus({
            phase: "error",
            message: event.error ?? "An error occurred",
          });
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        store.setStatus({
          phase: "error",
          message: (err as Error).message || "Failed to get response",
        });
      }
    } finally {
      abortRef.current = null;
    }
  };

  const handleNewSession = async () => {
    const store = useInsightsStore.getState();
    store.clearSession();
  };

  const handleSelectSession = async (sessionId: string) => {
    // In a full implementation, this would load the session from the API
    if (sessionId !== session?.id) {
      const store = useInsightsStore.getState();
      store.clearSession();
    }
  };

  const handleDeleteSession = async (sessionId: string): Promise<boolean> => {
    const store = useInsightsStore.getState();
    store.setSessions(
      store.sessions.filter((s: InsightsSessionSummary) => s.id !== sessionId),
    );
    if (session?.id === sessionId) {
      store.clearSession();
    }
    return true;
  };

  const handleRenameSession = async (
    sessionId: string,
    newTitle: string,
  ): Promise<boolean> => {
    const store = useInsightsStore.getState();
    store.setSessions(
      store.sessions.map((s: InsightsSessionSummary) =>
        s.id === sessionId ? { ...s, title: newTitle } : s,
      ),
    );
    return true;
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion);
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* Chat History Sidebar */}
      {showSidebar && (
        <ChatHistorySidebar
          sessions={sessions}
          currentSessionId={session?.id ?? null}
          isLoading={isLoadingSessions}
          onNewSession={handleNewSession}
          onSelectSession={handleSelectSession}
          onDeleteSession={handleDeleteSession}
          onRenameSession={handleRenameSession}
        />
      )}

      {/* Main Chat Area */}
      <div className="flex flex-1 flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-2">
            <button
              className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-accent transition-colors"
              onClick={() => setShowSidebar(!showSidebar)}
            >
              {showSidebar ? (
                <PanelLeftClose className="h-4 w-4" />
              ) : (
                <PanelLeft className="h-4 w-4" />
              )}
            </button>
            <Sparkles className="h-4 w-4 text-primary" />
            <h1 className="text-sm font-semibold">
              {t("insights.title")}
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <ModelSelector
              currentConfig={modelConfig}
              onConfigChange={setModelConfig}
              disabled={isLoading}
            />
            <button
              className="flex h-8 items-center gap-1.5 rounded-md border border-border px-3 text-sm hover:bg-accent transition-colors"
              onClick={handleNewSession}
            >
              <Plus className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">{t("insights.newChat")}</span>
            </button>
          </div>
        </div>

        {/* Messages */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-6"
        >
          {messages.length === 0 && !streamingContent ? (
            <div className="flex flex-col items-center justify-center h-full max-w-2xl mx-auto">
              <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
                <Sparkles className="h-8 w-8 text-primary" />
              </div>
              <h2 className="text-xl font-semibold mb-2">
                {t("insights.welcomeTitle")}
              </h2>
              <p className="text-sm text-muted-foreground text-center mb-8">
                {t("insights.welcomeDescription")}
              </p>
              <div className="grid grid-cols-1 gap-2 w-full max-w-lg">
                {SUGGESTION_KEYS.map((key) => {
                  const suggestion = t(key);
                  return (
                    <button
                      key={key}
                      className="text-left rounded-lg border border-border bg-card/50 px-4 py-3 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                      onClick={() => handleSuggestionClick(suggestion)}
                    >
                      {suggestion}
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-6">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}

              {/* Streaming message */}
              {(streamingContent || currentTool) && (
                <StreamingMessage
                  content={streamingContent}
                  currentTool={currentTool}
                />
              )}

              {/* Thinking indicator */}
              {status.phase === "thinking" &&
                !streamingContent &&
                !currentTool && <ThinkingIndicator />}

              {/* Error message */}
              {status.phase === "error" && status.message && (
                <div className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  {status.message}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Input */}
        <ChatInput
          value={inputValue}
          onChange={setInputValue}
          onSend={handleSend}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}
