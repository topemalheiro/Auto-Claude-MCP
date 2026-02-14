"use client";

import { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  Sparkles,
  Send,
  User,
  Bot,
  Plus,
  PanelLeft,
  PanelLeftClose,
  MessageSquare,
} from "lucide-react";
import { cn } from "@auto-claude/ui";

interface InsightsViewProps {
  projectId: string;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface ChatSession {
  id: string;
  title: string;
  createdAt: Date;
}

const SUGGESTION_KEYS = [
  "insights.suggestions.complexity",
  "insights.suggestions.security",
  "insights.suggestions.performance",
  "insights.suggestions.tests",
  "insights.suggestions.architecture",
] as const;

export function InsightsView({ projectId }: InsightsViewProps) {
  const { t } = useTranslation("views");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true);
  const [sessions] = useState<ChatSession[]>([
    { id: "1", title: "Architecture Review", createdAt: new Date() },
    { id: "2", title: "Security Audit", createdAt: new Date() },
  ]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    // Simulate AI response
    setTimeout(() => {
      const aiMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `I've analyzed your query about "${userMessage.content}". This is a placeholder response -- in the full implementation, this will be powered by Claude analyzing your project's codebase and providing detailed insights.`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMessage]);
      setIsLoading(false);
    }, 1500);
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInput(suggestion);
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* Chat History Sidebar */}
      {showSidebar && (
        <div className="w-64 border-r border-border bg-card/50 flex flex-col">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <h2 className="text-sm font-semibold">{t("insights.chatHistory")}</h2>
            <button className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-accent transition-colors">
              <Plus className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {sessions.map((session) => (
              <button
                key={session.id}
                className="w-full flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent transition-colors text-left"
              >
                <MessageSquare className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                <span className="truncate">{session.title}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Main Chat Area */}
      <div className="flex flex-1 flex-col">
        {/* Header */}
        <div className="flex items-center gap-2 border-b border-border px-4 py-3">
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
          <h1 className="text-sm font-semibold">{t("insights.title")}</h1>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full max-w-2xl mx-auto">
              <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
                <Sparkles className="h-8 w-8 text-primary" />
              </div>
              <h2 className="text-xl font-semibold mb-2">{t("insights.welcomeTitle")}</h2>
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
                <div key={message.id} className="flex gap-3">
                  <div className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full shrink-0",
                    message.role === "user" ? "bg-secondary" : "bg-primary/10"
                  )}>
                    {message.role === "user" ? (
                      <User className="h-4 w-4" />
                    ) : (
                      <Bot className="h-4 w-4 text-primary" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-muted-foreground mb-1">
                      {message.role === "user" ? t("insights.you") : t("insights.aiAssistant")}
                    </p>
                    <div className="text-sm leading-relaxed whitespace-pre-wrap">
                      {message.content}
                    </div>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 shrink-0">
                    <Bot className="h-4 w-4 text-primary animate-pulse" />
                  </div>
                  <div className="flex items-center gap-1 pt-2">
                    <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:0ms]" />
                    <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:150ms]" />
                    <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:300ms]" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-border p-4">
          <div className="max-w-3xl mx-auto flex gap-2">
            <textarea
              className="flex-1 resize-none rounded-lg border border-border bg-background px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
              placeholder={t("insights.placeholder")}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
            />
            <button
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-lg transition-colors",
                input.trim() && !isLoading
                  ? "bg-primary text-primary-foreground hover:bg-primary/90"
                  : "bg-secondary text-muted-foreground"
              )}
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
