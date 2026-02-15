"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  User,
  Bot,
  FileText,
  FolderSearch,
  Search,
  Loader2,
} from "lucide-react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@auto-claude/ui";
import type {
  InsightsChatMessage,
  InsightsToolUsage,
} from "@/stores/insights-store";

// Safe link component that validates URLs
function SafeLink({
  href,
  children,
  ...props
}: React.AnchorHTMLAttributes<HTMLAnchorElement>) {
  const isValidUrl =
    href &&
    (href.startsWith("http://") ||
      href.startsWith("https://") ||
      href.startsWith("/") ||
      href.startsWith("#"));

  if (!isValidUrl) {
    return <span className="text-muted-foreground">{children}</span>;
  }

  const isExternal =
    href?.startsWith("http://") || href?.startsWith("https://");

  return (
    <a
      href={href}
      {...props}
      {...(isExternal && {
        target: "_blank",
        rel: "noopener noreferrer",
      })}
      className="text-primary hover:underline"
    >
      {children}
    </a>
  );
}

const markdownComponents: Components = {
  a: SafeLink,
};

interface ChatMessageProps {
  message: InsightsChatMessage;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const { t } = useTranslation("views");
  const isUser = message.role === "user";

  return (
    <div className="flex gap-3">
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-muted" : "bg-primary/10",
        )}
      >
        {isUser ? (
          <User className="h-4 w-4 text-muted-foreground" />
        ) : (
          <Bot className="h-4 w-4 text-primary" />
        )}
      </div>
      <div className="flex-1 space-y-2 min-w-0">
        <div className="text-sm font-medium text-foreground">
          {isUser ? t("insights.you") : t("insights.aiAssistant")}
        </div>
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={markdownComponents}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Tool usage history for assistant messages */}
        {!isUser && message.toolsUsed && message.toolsUsed.length > 0 && (
          <ToolUsageHistory tools={message.toolsUsed} />
        )}
      </div>
    </div>
  );
}

// Streaming message component
interface StreamingMessageProps {
  content: string;
  currentTool: { name: string; input?: string } | null;
}

export function StreamingMessage({
  content,
  currentTool,
}: StreamingMessageProps) {
  return (
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
        <Bot className="h-4 w-4 text-primary" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="mb-1 text-sm font-medium text-foreground">
          Assistant
        </div>
        {content && (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={markdownComponents}
            >
              {content}
            </ReactMarkdown>
          </div>
        )}
        {currentTool && (
          <ToolIndicator name={currentTool.name} input={currentTool.input} />
        )}
      </div>
    </div>
  );
}

// Thinking indicator
export function ThinkingIndicator() {
  return (
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
        <Bot className="h-4 w-4 text-primary" />
      </div>
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Thinking...
      </div>
    </div>
  );
}

// Tool usage history
function ToolUsageHistory({ tools }: { tools: InsightsToolUsage[] }) {
  const [expanded, setExpanded] = useState(false);

  if (tools.length === 0) return null;

  const toolCounts = tools.reduce(
    (acc, tool) => {
      acc[tool.name] = (acc[tool.name] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  const getToolIcon = (toolName: string) => {
    switch (toolName) {
      case "Read":
        return FileText;
      case "Glob":
        return FolderSearch;
      case "Grep":
        return Search;
      default:
        return FileText;
    }
  };

  const getToolColor = (toolName: string) => {
    switch (toolName) {
      case "Read":
        return "text-blue-500";
      case "Glob":
        return "text-amber-500";
      case "Grep":
        return "text-green-500";
      default:
        return "text-muted-foreground";
    }
  };

  return (
    <div className="mt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <span className="flex items-center gap-1">
          {Object.entries(toolCounts).map(([name, count]) => {
            const Icon = getToolIcon(name);
            return (
              <span
                key={name}
                className={cn(
                  "flex items-center gap-0.5",
                  getToolColor(name),
                )}
              >
                <Icon className="h-3 w-3" />
                <span>{count}</span>
              </span>
            );
          })}
        </span>
        <span>
          {tools.length} tool{tools.length !== 1 ? "s" : ""} used
        </span>
        <span className="text-[10px]">{expanded ? "\u25B2" : "\u25BC"}</span>
      </button>

      {expanded && (
        <div className="mt-2 space-y-1 rounded-md border border-border bg-muted/30 p-2">
          {tools.map((tool, index) => {
            const Icon = getToolIcon(tool.name);
            return (
              <div
                key={`${tool.name}-${index}`}
                className="flex items-center gap-2 text-xs"
              >
                <Icon
                  className={cn(
                    "h-3 w-3 shrink-0",
                    getToolColor(tool.name),
                  )}
                />
                <span className="font-medium">{tool.name}</span>
                {tool.input && (
                  <span className="text-muted-foreground truncate max-w-[250px]">
                    {tool.input}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// Tool indicator for streaming
function ToolIndicator({ name, input }: { name: string; input?: string }) {
  const getToolInfo = (toolName: string) => {
    switch (toolName) {
      case "Read":
        return {
          icon: FileText,
          label: "Reading file",
          color: "text-blue-500 bg-blue-500/10",
        };
      case "Glob":
        return {
          icon: FolderSearch,
          label: "Searching files",
          color: "text-amber-500 bg-amber-500/10",
        };
      case "Grep":
        return {
          icon: Search,
          label: "Searching code",
          color: "text-green-500 bg-green-500/10",
        };
      default:
        return {
          icon: Loader2,
          label: toolName,
          color: "text-primary bg-primary/10",
        };
    }
  };

  const { icon: Icon, label, color } = getToolInfo(name);

  return (
    <div
      className={cn(
        "mt-2 inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm",
        color,
      )}
    >
      <Icon className="h-4 w-4 animate-pulse" />
      <span className="font-medium">{label}</span>
      {input && (
        <span className="text-muted-foreground truncate max-w-[300px]">
          {input}
        </span>
      )}
    </div>
  );
}
