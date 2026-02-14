"use client";

import { useState } from "react";
import {
  Github,
  Search,
  RefreshCw,
  ExternalLink,
  MessageSquare,
  Tag,
  Settings,
  Filter,
  AlertCircle,
  ArrowRight,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useTranslation } from "react-i18next";

interface GitHubIssuesViewProps {
  projectId: string;
}

interface GitHubIssue {
  number: number;
  title: string;
  state: "open" | "closed";
  labels: { name: string; color: string }[];
  author: string;
  comments: number;
  createdAt: string;
  body: string;
}

const PLACEHOLDER_ISSUES: GitHubIssue[] = [
  {
    number: 42,
    title: "Add dark mode support for mobile views",
    state: "open",
    labels: [{ name: "enhancement", color: "a2eeef" }, { name: "ui", color: "7057ff" }],
    author: "user1",
    comments: 3,
    createdAt: "2025-02-10",
    body: "The mobile views don't properly support dark mode...",
  },
  {
    number: 41,
    title: "Fix authentication token refresh race condition",
    state: "open",
    labels: [{ name: "bug", color: "d73a4a" }, { name: "priority:high", color: "e11d48" }],
    author: "user2",
    comments: 7,
    createdAt: "2025-02-08",
    body: "When multiple API calls happen simultaneously...",
  },
  {
    number: 39,
    title: "Implement webhook support for external integrations",
    state: "open",
    labels: [{ name: "feature", color: "0075ca" }],
    author: "user3",
    comments: 2,
    createdAt: "2025-02-05",
    body: "We need webhook endpoints for...",
  },
];

export function GitHubIssuesView({ projectId }: GitHubIssuesViewProps) {
  const { t } = useTranslation("integrations");
  const [issues] = useState(PLACEHOLDER_ISSUES);
  const [selectedIssue, setSelectedIssue] = useState<GitHubIssue | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [isConnected] = useState(true);

  if (!isConnected) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8">
        <div className="max-w-md text-center">
          <div className="mb-6 flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-secondary">
              <Github className="h-8 w-8 text-muted-foreground" />
            </div>
          </div>
          <h2 className="mb-3 text-xl font-semibold">{t("github.issues.notConnected")}</h2>
          <p className="mb-6 text-sm text-muted-foreground">
            {t("github.issues.notConnectedDescription")}
          </p>
          <button className="flex items-center gap-2 mx-auto rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors">
            <Settings className="h-4 w-4" />
            {t("github.issues.configure")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* Issue List */}
      <div className={cn("flex flex-col border-r border-border", selectedIssue ? "w-96" : "flex-1")}>
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h1 className="text-sm font-semibold flex items-center gap-2">
            <Github className="h-4 w-4" />
            {t("github.issues.title")}
          </h1>
          <button className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-accent transition-colors">
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* Search */}
        <div className="border-b border-border px-4 py-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <input
              className="w-full rounded-md border border-border bg-background pl-8 pr-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/20"
              placeholder={t("github.issues.search")}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {/* Issue list */}
        <div className="flex-1 overflow-y-auto">
          {issues.map((issue) => (
            <div
              key={issue.number}
              className={cn(
                "flex items-start gap-3 border-b border-border px-4 py-3 cursor-pointer transition-colors",
                selectedIssue?.number === issue.number ? "bg-accent" : "hover:bg-accent/50"
              )}
              onClick={() => setSelectedIssue(issue)}
            >
              <AlertCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium leading-tight">
                  #{issue.number} {issue.title}
                </p>
                <div className="mt-1 flex items-center gap-2 flex-wrap">
                  {issue.labels.map((label) => (
                    <span
                      key={label.name}
                      className="rounded-full border border-border px-2 py-0.5 text-[10px]"
                      style={{ borderColor: `#${label.color}40`, color: `#${label.color}` }}
                    >
                      {label.name}
                    </span>
                  ))}
                </div>
                <div className="mt-1 flex items-center gap-3 text-[10px] text-muted-foreground">
                  <span>{issue.author}</span>
                  <span>{issue.createdAt}</span>
                  {issue.comments > 0 && (
                    <span className="flex items-center gap-0.5">
                      <MessageSquare className="h-2.5 w-2.5" />
                      {issue.comments}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Issue Detail */}
      {selectedIssue && (
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex items-center justify-between border-b border-border px-6 py-3">
            <h2 className="text-sm font-semibold">
              #{selectedIssue.number} {selectedIssue.title}
            </h2>
            <div className="flex items-center gap-2">
              <a
                href={`https://github.com/issues/${selectedIssue.number}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-accent transition-colors"
              >
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-2xl space-y-4">
              <div className="flex items-center gap-2 flex-wrap">
                {selectedIssue.labels.map((label) => (
                  <span
                    key={label.name}
                    className="rounded-full border px-2.5 py-0.5 text-xs"
                    style={{ borderColor: `#${label.color}40`, color: `#${label.color}` }}
                  >
                    {label.name}
                  </span>
                ))}
              </div>
              <div className="text-sm text-muted-foreground whitespace-pre-wrap">
                {selectedIssue.body}
              </div>
              <div className="pt-4 border-t border-border">
                <button className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 transition-colors">
                  <ArrowRight className="h-3.5 w-3.5" />
                  {t("github.issues.createTask")}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
