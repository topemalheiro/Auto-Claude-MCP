"use client";

import { useState } from "react";
import {
  Search,
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  XCircle,
  Clock,
  Eye,
  GitMerge,
} from "lucide-react";
import { cn } from "@auto-claude/ui";

interface GitLabMRsViewProps {
  projectId: string;
}

interface MergeRequest {
  iid: number;
  title: string;
  state: "opened" | "merged" | "closed";
  author: string;
  additions: number;
  deletions: number;
  changedFiles: number;
  createdAt: string;
  labels: string[];
  draft: boolean;
  approvals: number;
  approvalsRequired: number;
}

const PLACEHOLDER_MRS: MergeRequest[] = [
  {
    iid: 95,
    title: "Add database migration framework",
    state: "opened",
    author: "dev1",
    additions: 450,
    deletions: 20,
    changedFiles: 8,
    createdAt: "2025-02-13",
    labels: ["database", "feature"],
    draft: false,
    approvals: 1,
    approvalsRequired: 2,
  },
  {
    iid: 94,
    title: "Fix memory leak in worker process",
    state: "merged",
    author: "dev2",
    additions: 35,
    deletions: 12,
    changedFiles: 3,
    createdAt: "2025-02-12",
    labels: ["bug", "hotfix"],
    draft: false,
    approvals: 2,
    approvalsRequired: 2,
  },
  {
    iid: 93,
    title: "WIP: Refactor authentication module",
    state: "opened",
    author: "dev1",
    additions: 890,
    deletions: 340,
    changedFiles: 15,
    createdAt: "2025-02-11",
    labels: ["refactoring"],
    draft: true,
    approvals: 0,
    approvalsRequired: 2,
  },
];

const STATE_COLORS: Record<string, string> = {
  opened: "text-green-500",
  merged: "text-purple-500",
  closed: "text-red-500",
};

export function GitLabMRsView({ projectId }: GitLabMRsViewProps) {
  const [mrs] = useState(PLACEHOLDER_MRS);
  const [selectedMR, setSelectedMR] = useState<MergeRequest | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "opened" | "merged" | "closed">("all");

  const filteredMRs = mrs.filter((mr) => {
    if (filter !== "all" && mr.state !== filter) return false;
    if (searchQuery && !mr.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="flex h-full overflow-hidden">
      {/* MR List */}
      <div className={cn("flex flex-col border-r border-border", selectedMR ? "w-96" : "flex-1")}>
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h1 className="text-sm font-semibold flex items-center gap-2">
            <GitMerge className="h-4 w-4" />
            Merge Requests
          </h1>
          <button className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-accent transition-colors">
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="border-b border-border px-4 py-2 space-y-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <input
              className="w-full rounded-md border border-border bg-background pl-8 pr-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/20"
              placeholder="Search merge requests..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-1">
            {(["all", "opened", "merged", "closed"] as const).map((f) => (
              <button
                key={f}
                className={cn(
                  "rounded-full px-2.5 py-1 text-[10px] font-medium transition-colors",
                  filter === f ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"
                )}
                onClick={() => setFilter(f)}
              >
                {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {filteredMRs.map((mr) => (
            <div
              key={mr.iid}
              className={cn(
                "flex items-start gap-3 border-b border-border px-4 py-3 cursor-pointer transition-colors",
                selectedMR?.iid === mr.iid ? "bg-accent" : "hover:bg-accent/50"
              )}
              onClick={() => setSelectedMR(mr)}
            >
              <GitMerge className={cn("h-4 w-4 mt-0.5 shrink-0", STATE_COLORS[mr.state])} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium leading-tight">
                  !{mr.iid} {mr.title}
                </p>
                <div className="mt-1 flex items-center gap-1.5 flex-wrap">
                  {mr.draft && (
                    <span className="rounded-full bg-yellow-500/10 text-yellow-600 px-2 py-0.5 text-[10px] font-medium">
                      Draft
                    </span>
                  )}
                  {mr.labels.map((label) => (
                    <span
                      key={label}
                      className="rounded-full bg-secondary px-2 py-0.5 text-[10px] text-muted-foreground"
                    >
                      {label}
                    </span>
                  ))}
                </div>
                <div className="mt-1 flex items-center gap-3 text-[10px] text-muted-foreground">
                  <span>{mr.author}</span>
                  <span>{mr.createdAt}</span>
                  <span className="text-green-600">+{mr.additions}</span>
                  <span className="text-red-600">-{mr.deletions}</span>
                  <span>{mr.changedFiles} files</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* MR Detail */}
      {selectedMR && (
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex items-center justify-between border-b border-border px-6 py-3">
            <h2 className="text-sm font-semibold">
              !{selectedMR.iid} {selectedMR.title}
            </h2>
            <div className="flex items-center gap-2">
              <button className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors">
                <Eye className="h-3 w-3" />
                AI Review
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
              <div className="grid grid-cols-4 gap-3">
                <div className="rounded-md border border-border p-3 text-center">
                  <p className="text-lg font-semibold text-green-600">+{selectedMR.additions}</p>
                  <p className="text-[10px] text-muted-foreground">Additions</p>
                </div>
                <div className="rounded-md border border-border p-3 text-center">
                  <p className="text-lg font-semibold text-red-600">-{selectedMR.deletions}</p>
                  <p className="text-[10px] text-muted-foreground">Deletions</p>
                </div>
                <div className="rounded-md border border-border p-3 text-center">
                  <p className="text-lg font-semibold">{selectedMR.changedFiles}</p>
                  <p className="text-[10px] text-muted-foreground">Files</p>
                </div>
                <div className="rounded-md border border-border p-3 text-center">
                  <p className="text-lg font-semibold capitalize">{selectedMR.state}</p>
                  <p className="text-[10px] text-muted-foreground">Status</p>
                </div>
              </div>

              <div className="rounded-lg border border-border p-4">
                <h3 className="text-sm font-medium mb-2">Approvals</h3>
                <div className="flex items-center gap-2">
                  {selectedMR.approvals >= selectedMR.approvalsRequired ? (
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                  ) : (
                    <Clock className="h-4 w-4 text-yellow-500" />
                  )}
                  <span className="text-sm">
                    {selectedMR.approvals}/{selectedMR.approvalsRequired} approvals
                  </span>
                </div>
              </div>

              <button className="w-full flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm text-primary-foreground hover:bg-primary/90 transition-colors">
                <Eye className="h-4 w-4" />
                Start AI Code Review
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
