"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Plus,
  MessageSquare,
  Trash2,
  Pencil,
  Check,
  X,
  MoreVertical,
  Loader2,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import type { InsightsSessionSummary } from "@/stores/insights-store";

interface ChatHistorySidebarProps {
  sessions: InsightsSessionSummary[];
  currentSessionId: string | null;
  isLoading: boolean;
  onNewSession: () => void;
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => Promise<boolean>;
  onRenameSession: (sessionId: string, newTitle: string) => Promise<boolean>;
}

export function ChatHistorySidebar({
  sessions,
  currentSessionId,
  isLoading,
  onNewSession,
  onSelectSession,
  onDeleteSession,
  onRenameSession,
}: ChatHistorySidebarProps) {
  const { t } = useTranslation("views");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [deleteSessionId, setDeleteSessionId] = useState<string | null>(null);
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);

  const handleStartEdit = (session: InsightsSessionSummary) => {
    setEditingId(session.id);
    setEditTitle(session.title ?? "Untitled");
    setMenuOpenId(null);
  };

  const handleSaveEdit = async () => {
    if (editingId && editTitle.trim()) {
      await onRenameSession(editingId, editTitle.trim());
    }
    setEditingId(null);
    setEditTitle("");
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditTitle("");
  };

  const handleDelete = async () => {
    if (deleteSessionId) {
      await onDeleteSession(deleteSessionId);
      setDeleteSessionId(null);
    }
  };

  const formatDate = (date: Date) => {
    const now = new Date();
    const d = new Date(date);
    const diffMs = now.getTime() - d.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays} days ago`;
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  };

  const groupedSessions = sessions.reduce(
    (groups, session) => {
      const dateLabel = formatDate(session.updatedAt);
      if (!groups[dateLabel]) groups[dateLabel] = [];
      groups[dateLabel].push(session);
      return groups;
    },
    {} as Record<string, InsightsSessionSummary[]>,
  );

  return (
    <div className="flex h-full w-64 flex-col border-r border-border bg-card/50">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-3 py-3">
        <h3 className="text-sm font-medium text-foreground">
          {t("insights.chatHistory")}
        </h3>
        <button
          className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-accent transition-colors"
          onClick={onNewSession}
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : sessions.length === 0 ? (
          <div className="px-3 py-8 text-center text-sm text-muted-foreground">
            {t("insights.noConversations")}
          </div>
        ) : (
          <div className="py-2">
            {Object.entries(groupedSessions).map(
              ([dateLabel, dateSessions]) => (
                <div key={dateLabel} className="mb-2">
                  <div className="px-3 py-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                    {dateLabel}
                  </div>
                  {dateSessions.map((session) =>
                    editingId === session.id ? (
                      <div
                        key={session.id}
                        className="flex items-center gap-1 px-2 py-1"
                      >
                        <input
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              handleSaveEdit();
                            } else if (e.key === "Escape") {
                              handleCancelEdit();
                            }
                          }}
                          className="flex-1 h-7 rounded border border-border bg-background px-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                          autoFocus
                        />
                        <button
                          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md hover:bg-accent"
                          onClick={handleSaveEdit}
                        >
                          <Check className="h-3.5 w-3.5 text-green-500" />
                        </button>
                        <button
                          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md hover:bg-accent"
                          onClick={handleCancelEdit}
                        >
                          <X className="h-3.5 w-3.5 text-muted-foreground" />
                        </button>
                      </div>
                    ) : (
                      <div
                        key={session.id}
                        className={cn(
                          "group relative cursor-pointer px-2 py-2 transition-colors hover:bg-muted",
                          session.id === currentSessionId &&
                            "bg-primary/10 hover:bg-primary/15",
                        )}
                        onClick={() => onSelectSession(session.id)}
                      >
                        <div className="flex items-center gap-1.5 pr-7">
                          <MessageSquare
                            className={cn(
                              "h-4 w-4 shrink-0",
                              session.id === currentSessionId
                                ? "text-primary"
                                : "text-muted-foreground",
                            )}
                          />
                          <div className="min-w-0 flex-1">
                            <p
                              className={cn(
                                "line-clamp-2 text-sm leading-tight break-words",
                                session.id === currentSessionId
                                  ? "font-medium text-foreground"
                                  : "text-foreground/80",
                              )}
                            >
                              {session.title ?? "Untitled"}
                            </p>
                            <p className="text-[11px] text-muted-foreground mt-0.5">
                              {session.messageCount} message
                              {session.messageCount !== 1 ? "s" : ""}
                            </p>
                          </div>
                        </div>

                        {/* Context menu trigger */}
                        <div className="absolute right-1 top-1/2 -translate-y-1/2">
                          <button
                            className="flex h-6 w-6 items-center justify-center rounded-md opacity-0 group-hover:opacity-100 hover:bg-muted-foreground/20 transition-opacity"
                            onClick={(e) => {
                              e.stopPropagation();
                              setMenuOpenId(
                                menuOpenId === session.id
                                  ? null
                                  : session.id,
                              );
                            }}
                          >
                            <MoreVertical className="h-3.5 w-3.5" />
                          </button>
                          {menuOpenId === session.id && (
                            <div className="absolute right-0 top-full mt-1 w-32 rounded-md border border-border bg-popover p-1 shadow-md z-50">
                              <button
                                className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleStartEdit(session);
                                }}
                              >
                                <Pencil className="h-3.5 w-3.5" />
                                Rename
                              </button>
                              <button
                                className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-destructive hover:bg-accent"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setDeleteSessionId(session.id);
                                  setMenuOpenId(null);
                                }}
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                                Delete
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    ),
                  )}
                </div>
              ),
            )}
          </div>
        )}
      </div>

      {/* Delete confirmation */}
      {deleteSessionId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-80 rounded-lg border border-border bg-popover p-6 shadow-lg">
            <h4 className="text-sm font-semibold mb-2">
              Delete conversation?
            </h4>
            <p className="text-sm text-muted-foreground mb-4">
              This will permanently delete this conversation and all its
              messages. This action cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button
                className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-accent"
                onClick={() => setDeleteSessionId(null)}
              >
                Cancel
              </button>
              <button
                className="rounded-md bg-destructive px-3 py-1.5 text-sm text-destructive-foreground hover:bg-destructive/90"
                onClick={handleDelete}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
