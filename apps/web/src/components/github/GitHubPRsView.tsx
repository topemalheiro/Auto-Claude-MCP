"use client";

import { useState } from "react";
import {
  GitPullRequest,
  Search,
  RefreshCw,
  ExternalLink,
  MessageSquare,
  CheckCircle2,
  XCircle,
  Clock,
  GitMerge,
  Settings,
  Eye,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useTranslation } from "react-i18next";

interface GitHubPRsViewProps {
  projectId: string;
}

interface PullRequest {
  number: number;
  title: string;
  state: "open" | "closed" | "merged";
  author: string;
  reviewStatus: "pending" | "approved" | "changes_requested" | "reviewing";
  additions: number;
  deletions: number;
  files: number;
  createdAt: string;
  labels: { name: string; color: string }[];
  draft: boolean;
}

const PLACEHOLDER_PRS: PullRequest[] = [
  {
    number: 1783,
    title: "Cloud Phase 1: Extract shared types and UI packages",
    state: "merged",
    author: "dev1",
    reviewStatus: "approved",
    additions: 2500,
    deletions: 150,
    files: 45,
    createdAt: "2025-02-12",
    labels: [{ name: "cloud", color: "0075ca" }],
    draft: false,
  },
  {
    number: 1804,
    title: "Fix Sentry integration for Python subprocesses",
    state: "merged",
    author: "dev2",
    reviewStatus: "approved",
    additions: 120,
    deletions: 30,
    files: 5,
    createdAt: "2025-02-11",
    labels: [{ name: "bug", color: "d73a4a" }],
    draft: false,
  },
  {
    number: 1810,
    title: "Add real-time task progress WebSocket support",
    state: "open",
    author: "dev1",
    reviewStatus: "pending",
    additions: 890,
    deletions: 45,
    files: 12,
    createdAt: "2025-02-13",
    labels: [{ name: "feature", color: "a2eeef" }],
    draft: false,
  },
];

const STATE_ICONS: Record<string, React.ElementType> = {
  open: GitPullRequest,
  merged: GitMerge,
  closed: XCircle,
};

const STATE_COLORS: Record<string, string> = {
  open: "text-green-500",
  merged: "text-purple-500",
  closed: "text-red-500",
};

const REVIEW_STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-500/10 text-yellow-600",
  approved: "bg-green-500/10 text-green-600",
  changes_requested: "bg-red-500/10 text-red-600",
  reviewing: "bg-blue-500/10 text-blue-600",
};

const REVIEW_STATUS_KEYS: Record<string, string> = {
  pending: "github.prs.reviews.pending",
  approved: "github.prs.reviews.approved",
  changes_requested: "github.prs.reviews.changesRequested",
  reviewing: "github.prs.reviews.inReview",
};

export function GitHubPRsView({ projectId }: GitHubPRsViewProps) {
  const { t } = useTranslation("integrations");
  const [prs] = useState(PLACEHOLDER_PRS);
  const [selectedPR, setSelectedPR] = useState<PullRequest | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "open" | "merged" | "closed">("all");

  const filteredPRs = prs.filter((pr) => {
    if (filter !== "all" && pr.state !== filter) return false;
    if (searchQuery && !pr.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="flex h-full overflow-hidden">
      {/* PR List */}
      <div className={cn("flex flex-col border-r border-border", selectedPR ? "w-96" : "flex-1")}>
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h1 className="text-sm font-semibold flex items-center gap-2">
            <GitPullRequest className="h-4 w-4" />
            {t("github.prs.title")}
          </h1>
          <button className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-accent transition-colors">
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* Filters */}
        <div className="border-b border-border px-4 py-2 space-y-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <input
              className="w-full rounded-md border border-border bg-background pl-8 pr-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/20"
              placeholder={t("github.prs.search")}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-1">
            {(["all", "open", "merged", "closed"] as const).map((f) => (
              <button
                key={f}
                className={cn(
                  "rounded-full px-2.5 py-1 text-[10px] font-medium transition-colors",
                  filter === f ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"
                )}
                onClick={() => setFilter(f)}
              >
                {t(`github.prs.filters.${f}`)}
              </button>
            ))}
          </div>
        </div>

        {/* PR list */}
        <div className="flex-1 overflow-y-auto">
          {filteredPRs.map((pr) => {
            const StateIcon = STATE_ICONS[pr.state] || GitPullRequest;
            const stateColor = STATE_COLORS[pr.state] || "text-muted-foreground";
            const reviewColor = REVIEW_STATUS_COLORS[pr.reviewStatus];
            const reviewKey = REVIEW_STATUS_KEYS[pr.reviewStatus];

            return (
              <div
                key={pr.number}
                className={cn(
                  "flex items-start gap-3 border-b border-border px-4 py-3 cursor-pointer transition-colors",
                  selectedPR?.number === pr.number ? "bg-accent" : "hover:bg-accent/50"
                )}
                onClick={() => setSelectedPR(pr)}
              >
                <StateIcon className={cn("h-4 w-4 mt-0.5 shrink-0", stateColor)} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium leading-tight">
                    #{pr.number} {pr.title}
                  </p>
                  <div className="mt-1 flex items-center gap-2 flex-wrap">
                    {pr.labels.map((label) => (
                      <span
                        key={label.name}
                        className="rounded-full border px-2 py-0.5 text-[10px]"
                        style={{ borderColor: `#${label.color}40`, color: `#${label.color}` }}
                      >
                        {label.name}
                      </span>
                    ))}
                    <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-medium", reviewColor)}>
                      {t(reviewKey)}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-3 text-[10px] text-muted-foreground">
                    <span>{pr.author}</span>
                    <span>{pr.createdAt}</span>
                    <span className="text-green-600">+{pr.additions}</span>
                    <span className="text-red-600">-{pr.deletions}</span>
                    <span>{t("github.prs.stats.filesCount", { count: pr.files })}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* PR Detail */}
      {selectedPR && (
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex items-center justify-between border-b border-border px-6 py-3">
            <h2 className="text-sm font-semibold">
              #{selectedPR.number} {selectedPR.title}
            </h2>
            <div className="flex items-center gap-2">
              <button className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors">
                <Eye className="h-3 w-3" />
                {t("github.prs.aiReview")}
              </button>
              <a
                href="#"
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
              {/* Stats */}
              <div className="grid grid-cols-4 gap-3">
                <div className="rounded-md border border-border p-3 text-center">
                  <p className="text-lg font-semibold text-green-600">+{selectedPR.additions}</p>
                  <p className="text-[10px] text-muted-foreground">{t("github.prs.stats.additions")}</p>
                </div>
                <div className="rounded-md border border-border p-3 text-center">
                  <p className="text-lg font-semibold text-red-600">-{selectedPR.deletions}</p>
                  <p className="text-[10px] text-muted-foreground">{t("github.prs.stats.deletions")}</p>
                </div>
                <div className="rounded-md border border-border p-3 text-center">
                  <p className="text-lg font-semibold">{selectedPR.files}</p>
                  <p className="text-[10px] text-muted-foreground">{t("github.prs.stats.files")}</p>
                </div>
                <div className="rounded-md border border-border p-3 text-center">
                  <p className="text-lg font-semibold capitalize">{selectedPR.state}</p>
                  <p className="text-[10px] text-muted-foreground">{t("github.prs.status")}</p>
                </div>
              </div>

              {/* Review status */}
              <div className="rounded-lg border border-border p-4">
                <h3 className="text-sm font-medium mb-2">{t("github.prs.reviewStatus")}</h3>
                <div className="flex items-center gap-2">
                  {selectedPR.reviewStatus === "approved" ? (
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                  ) : selectedPR.reviewStatus === "changes_requested" ? (
                    <XCircle className="h-4 w-4 text-red-500" />
                  ) : (
                    <Clock className="h-4 w-4 text-yellow-500" />
                  )}
                  <span className="text-sm">
                    {t(REVIEW_STATUS_KEYS[selectedPR.reviewStatus])}
                  </span>
                </div>
              </div>

              {/* AI Review button */}
              <button className="w-full flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm text-primary-foreground hover:bg-primary/90 transition-colors">
                <Eye className="h-4 w-4" />
                {t("github.prs.startAiReview")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
