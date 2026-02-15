"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Wrench,
  Server,
  Brain,
  Code,
  Search,
  FileCheck,
  ChevronRight,
  ChevronDown,
  CheckCircle2,
  Circle,
  RefreshCw,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useTranslation } from "react-i18next";
import { apiClient } from "@/lib/data/api-client";

interface AgentToolsViewProps {
  projectId: string;
}

interface McpServerStatus {
  name: string;
  status: "connected" | "disconnected" | "error";
  toolCount?: number;
}

interface AgentPhase {
  id: string;
  label: string;
  description: string;
  category: "spec" | "build" | "qa" | "utility";
  tools: string[];
  mcpServers: string[];
}

const AGENT_PHASES: AgentPhase[] = [
  // Spec phases
  { id: "spec_gatherer", label: "Spec Gatherer", description: "Collects initial requirements", category: "spec", tools: ["Read", "Glob", "Grep", "WebFetch", "WebSearch"], mcpServers: [] },
  { id: "spec_researcher", label: "Spec Researcher", description: "Validates external integrations", category: "spec", tools: ["Read", "Glob", "Grep", "WebFetch", "WebSearch"], mcpServers: ["context7"] },
  { id: "spec_writer", label: "Spec Writer", description: "Creates the spec document", category: "spec", tools: ["Read", "Glob", "Grep", "Write", "Edit", "Bash"], mcpServers: [] },
  { id: "spec_critic", label: "Spec Critic", description: "Self-critique using deep analysis", category: "spec", tools: ["Read", "Glob", "Grep"], mcpServers: [] },
  // Build phases
  { id: "planner", label: "Planner", description: "Creates implementation plan with subtasks", category: "build", tools: ["Read", "Glob", "Grep", "Write", "Edit", "Bash", "WebFetch", "WebSearch"], mcpServers: ["context7", "graphiti-memory", "auto-claude"] },
  { id: "coder", label: "Coder", description: "Implements individual subtasks", category: "build", tools: ["Read", "Glob", "Grep", "Write", "Edit", "Bash", "WebFetch", "WebSearch"], mcpServers: ["context7", "graphiti-memory", "auto-claude"] },
  // QA phases
  { id: "qa_reviewer", label: "QA Reviewer", description: "Validates acceptance criteria", category: "qa", tools: ["Read", "Glob", "Grep", "Bash", "WebFetch", "WebSearch"], mcpServers: ["context7", "graphiti-memory", "auto-claude"] },
  { id: "qa_fixer", label: "QA Fixer", description: "Fixes QA-reported issues", category: "qa", tools: ["Read", "Glob", "Grep", "Write", "Edit", "Bash", "WebFetch", "WebSearch"], mcpServers: ["context7", "graphiti-memory", "auto-claude"] },
  // Utility
  { id: "pr_reviewer", label: "PR Reviewer", description: "Reviews pull requests", category: "utility", tools: ["Read", "Glob", "Grep", "WebFetch", "WebSearch"], mcpServers: ["context7"] },
];

const CATEGORY_CONFIG: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  spec: { label: "Spec Creation", icon: Search, color: "text-blue-500" },
  build: { label: "Build", icon: Code, color: "text-green-500" },
  qa: { label: "Quality Assurance", icon: FileCheck, color: "text-amber-500" },
  utility: { label: "Utility", icon: Wrench, color: "text-purple-500" },
};

export function AgentToolsView({ projectId }: AgentToolsViewProps) {
  const { t } = useTranslation("views");
  const [mcpServers, setMcpServers] = useState<McpServerStatus[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(["build", "qa"]),
  );
  const [expandedPhases, setExpandedPhases] = useState<Set<string>>(new Set());

  const loadMcpStatus = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.getMcpStatus(projectId);
      if (response.servers) {
        setMcpServers(response.servers as McpServerStatus[]);
      }
    } catch {
      // MCP status is optional - may not be available
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadMcpStatus();
  }, [loadMcpStatus]);

  const toggleCategory = (cat: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  };

  const togglePhase = (id: string) => {
    setExpandedPhases((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const getServerStatus = (name: string): McpServerStatus | undefined => {
    return mcpServers.find((s) => s.name === name);
  };

  const groupedPhases = AGENT_PHASES.reduce(
    (acc, phase) => {
      if (!acc[phase.category]) acc[phase.category] = [];
      acc[phase.category].push(phase);
      return acc;
    },
    {} as Record<string, AgentPhase[]>,
  );

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <div className="flex items-center gap-3">
          <Wrench className="h-5 w-5 text-muted-foreground" />
          <h1 className="text-lg font-semibold">{t("agentTools.title")}</h1>
        </div>
        <button
          className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-50"
          onClick={loadMcpStatus}
          disabled={isLoading}
        >
          {isLoading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <RefreshCw className="h-3.5 w-3.5" />
          )}
          {t("agentTools.refresh")}
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* MCP Server Status */}
        {mcpServers.length > 0 && (
          <div className="mb-6">
            <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
              <Server className="h-4 w-4" />
              {t("agentTools.mcpServers")}
            </h2>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {mcpServers.map((server) => (
                <div
                  key={server.name}
                  className="flex items-center gap-3 rounded-lg border border-border bg-card p-3"
                >
                  {server.status === "connected" ? (
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-green-500" />
                  ) : server.status === "error" ? (
                    <AlertCircle className="h-4 w-4 shrink-0 text-destructive" />
                  ) : (
                    <Circle className="h-4 w-4 shrink-0 text-muted-foreground" />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{server.name}</p>
                    {server.toolCount != null && (
                      <p className="text-xs text-muted-foreground">
                        {server.toolCount} {t("agentTools.tools")}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Agent Phases */}
        <div className="space-y-4">
          {Object.entries(groupedPhases).map(([category, phases]) => {
            const config = CATEGORY_CONFIG[category];
            if (!config) return null;
            const Icon = config.icon;
            const isExpanded = expandedCategories.has(category);

            return (
              <div key={category} className="rounded-lg border border-border">
                <button
                  className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-accent/50"
                  onClick={() => toggleCategory(category)}
                >
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  )}
                  <Icon className={cn("h-4 w-4", config.color)} />
                  <span className="text-sm font-semibold">{config.label}</span>
                  <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                    {phases.length}
                  </span>
                </button>

                {isExpanded && (
                  <div className="border-t border-border">
                    {phases.map((phase) => {
                      const isPhaseExpanded = expandedPhases.has(phase.id);
                      return (
                        <div key={phase.id} className="border-b border-border/50 last:border-b-0">
                          <button
                            className="flex w-full items-center gap-3 px-6 py-2.5 text-left hover:bg-accent/30"
                            onClick={() => togglePhase(phase.id)}
                          >
                            {isPhaseExpanded ? (
                              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                            ) : (
                              <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                            )}
                            <div className="min-w-0 flex-1">
                              <span className="text-sm font-medium">{phase.label}</span>
                              <span className="ml-2 text-xs text-muted-foreground">
                                {phase.description}
                              </span>
                            </div>
                            <span className="text-xs text-muted-foreground">
                              {phase.tools.length} {t("agentTools.tools")}
                              {phase.mcpServers.length > 0 &&
                                ` · ${phase.mcpServers.length} MCP`}
                            </span>
                          </button>

                          {isPhaseExpanded && (
                            <div className="bg-muted/30 px-10 py-3">
                              <div className="space-y-2">
                                <div>
                                  <p className="mb-1 text-xs font-medium text-muted-foreground">
                                    {t("agentTools.availableTools")}
                                  </p>
                                  <div className="flex flex-wrap gap-1.5">
                                    {phase.tools.map((tool) => (
                                      <span
                                        key={tool}
                                        className="rounded-md bg-background px-2 py-0.5 text-xs font-medium"
                                      >
                                        {tool}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                                {phase.mcpServers.length > 0 && (
                                  <div>
                                    <p className="mb-1 text-xs font-medium text-muted-foreground">
                                      MCP Servers
                                    </p>
                                    <div className="flex flex-wrap gap-1.5">
                                      {phase.mcpServers.map((server) => {
                                        const status = getServerStatus(server);
                                        return (
                                          <span
                                            key={server}
                                            className={cn(
                                              "inline-flex items-center gap-1 rounded-md bg-background px-2 py-0.5 text-xs font-medium",
                                              status?.status === "connected" && "text-green-600 dark:text-green-400",
                                              status?.status === "error" && "text-destructive",
                                            )}
                                          >
                                            {status?.status === "connected" ? (
                                              <CheckCircle2 className="h-3 w-3" />
                                            ) : status?.status === "error" ? (
                                              <AlertCircle className="h-3 w-3" />
                                            ) : (
                                              <Circle className="h-3 w-3" />
                                            )}
                                            {server}
                                          </span>
                                        );
                                      })}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
