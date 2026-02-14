"use client";

import { useState } from "react";
import {
  Search,
  RefreshCw,
  ExternalLink,
  MessageSquare,
  Settings,
  AlertCircle,
  ArrowRight,
  Tag,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useTranslation } from "react-i18next";

// GitLab icon as inline SVG since lucide-react's GitlabIcon may not be available in all versions
function GitLabIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m22 13.29-3.33-10a.42.42 0 0 0-.14-.18.38.38 0 0 0-.22-.11.39.39 0 0 0-.23.07.42.42 0 0 0-.14.18l-2.26 6.67H8.32L6.1 3.26a.42.42 0 0 0-.1-.18.38.38 0 0 0-.26-.08.39.39 0 0 0-.23.07.42.42 0 0 0-.14.18L2 13.29a.74.74 0 0 0 .27.83L12 21l9.69-6.88a.71.71 0 0 0 .31-.83Z" />
    </svg>
  );
}

interface GitLabIssuesViewProps {
  projectId: string;
}

interface GitLabIssue {
  iid: number;
  title: string;
  state: "opened" | "closed";
  labels: string[];
  author: string;
  comments: number;
  createdAt: string;
  description: string;
}

const PLACEHOLDER_ISSUES: GitLabIssue[] = [
  {
    iid: 15,
    title: "Implement CI/CD pipeline for staging environment",
    state: "opened",
    labels: ["devops", "priority::high"],
    author: "dev1",
    comments: 4,
    createdAt: "2025-02-12",
    description: "We need to set up a proper CI/CD pipeline for the staging environment...",
  },
  {
    iid: 14,
    title: "Add internationalization support",
    state: "opened",
    labels: ["feature", "i18n"],
    author: "dev2",
    comments: 2,
    createdAt: "2025-02-10",
    description: "Support multiple languages in the application...",
  },
  {
    iid: 12,
    title: "Fix database connection pool exhaustion",
    state: "opened",
    labels: ["bug", "priority::critical"],
    author: "dev3",
    comments: 8,
    createdAt: "2025-02-08",
    description: "Under heavy load, the database connection pool gets exhausted...",
  },
];

export function GitLabIssuesView({ projectId }: GitLabIssuesViewProps) {
  const { t } = useTranslation("integrations");
  const [issues] = useState(PLACEHOLDER_ISSUES);
  const [selectedIssue, setSelectedIssue] = useState<GitLabIssue | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [isConnected] = useState(true);

  if (!isConnected) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8">
        <div className="max-w-md text-center">
          <div className="mb-6 flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-secondary">
              <GitLabIcon className="h-8 w-8 text-muted-foreground" />
            </div>
          </div>
          <h2 className="mb-3 text-xl font-semibold">{t("gitlab.issues.notConnected")}</h2>
          <p className="mb-6 text-sm text-muted-foreground">
            {t("gitlab.issues.notConnectedDescription")}
          </p>
          <button className="flex items-center gap-2 mx-auto rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors">
            <Settings className="h-4 w-4" />
            {t("gitlab.issues.configure")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* Issue List */}
      <div className={cn("flex flex-col border-r border-border", selectedIssue ? "w-96" : "flex-1")}>
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h1 className="text-sm font-semibold flex items-center gap-2">
            <GitLabIcon className="h-4 w-4" />
            {t("gitlab.issues.title")}
          </h1>
          <button className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-accent transition-colors">
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="border-b border-border px-4 py-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <input
              className="w-full rounded-md border border-border bg-background pl-8 pr-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/20"
              placeholder={t("gitlab.issues.search")}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {issues.map((issue) => (
            <div
              key={issue.iid}
              className={cn(
                "flex items-start gap-3 border-b border-border px-4 py-3 cursor-pointer transition-colors",
                selectedIssue?.iid === issue.iid ? "bg-accent" : "hover:bg-accent/50"
              )}
              onClick={() => setSelectedIssue(issue)}
            >
              <AlertCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium leading-tight">
                  #{issue.iid} {issue.title}
                </p>
                <div className="mt-1 flex items-center gap-1.5 flex-wrap">
                  {issue.labels.map((label) => (
                    <span
                      key={label}
                      className="rounded-full bg-secondary px-2 py-0.5 text-[10px] text-muted-foreground"
                    >
                      {label}
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
              #{selectedIssue.iid} {selectedIssue.title}
            </h2>
            <a
              href="#"
              target="_blank"
              rel="noopener noreferrer"
              className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-accent transition-colors"
            >
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-2xl space-y-4">
              <div className="flex items-center gap-2 flex-wrap">
                {selectedIssue.labels.map((label) => (
                  <span
                    key={label}
                    className="rounded-full bg-secondary px-2.5 py-0.5 text-xs text-muted-foreground"
                  >
                    {label}
                  </span>
                ))}
              </div>
              <div className="text-sm text-muted-foreground whitespace-pre-wrap">
                {selectedIssue.description}
              </div>
              <div className="pt-4 border-t border-border">
                <button className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 transition-colors">
                  <ArrowRight className="h-3.5 w-3.5" />
                  {t("gitlab.issues.createTask")}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
