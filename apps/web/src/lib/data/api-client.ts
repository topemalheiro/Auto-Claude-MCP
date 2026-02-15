/**
 * HTTP API client for self-hosted mode.
 *
 * Communicates with the Python backend (Auto Claude) via REST API.
 * In self-hosted mode, the backend runs locally or on a user's server.
 *
 * Provides typed fetch wrappers for all backend REST endpoints including
 * projects, tasks, settings, env, roadmap, ideation, insights (SSE),
 * changelog, context, GitHub, and GitLab integrations.
 */

import { API_URL } from "@/lib/cloud-mode";
import type {
  Task,
  TaskStatus,
  TaskMetadata,
  TaskLogs,
  ImplementationPlan,
  Project,
  ProjectSettings,
  ProjectEnvConfig,
  IPCResult,
} from "@auto-claude/types";

// ============================================
// Response Types
// ============================================

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface ProjectListResponse {
  projects: Project[];
}

export interface ProjectResponse {
  project: Project;
}

export interface TaskListResponse {
  tasks: Task[];
}

export interface TaskResponse {
  task: Task;
}

export interface SettingsResponse {
  settings: Record<string, unknown>;
}

export interface EnvConfigResponse {
  config: ProjectEnvConfig;
}

export interface RoadmapResponse {
  roadmap: unknown;
}

export interface IdeationResponse {
  ideas: unknown[];
}

export interface ChangelogResponse {
  changelog: unknown;
}

export interface ContextResponse {
  context: unknown;
}

export interface MemoriesResponse {
  memories: unknown[];
}

export interface ProjectIndexResponse {
  index: unknown;
}

export interface InsightsStreamEvent {
  type: "chunk" | "done" | "error";
  content?: string;
  error?: string;
}

export interface GitHubIssuesResponse {
  issues: unknown[];
}

export interface GitHubPRsResponse {
  prs: unknown[];
}

export interface GitHubOAuthResponse {
  url: string;
}

export interface GitHubInvestigationResponse {
  investigation: unknown;
}

export interface GitHubReviewResponse {
  review: unknown;
}

export interface GitHubAutoFixResponse {
  result: unknown;
}

export interface GitLabIssuesResponse {
  issues: unknown[];
}

export interface GitLabMRsResponse {
  merge_requests: unknown[];
}

export interface GitLabOAuthResponse {
  url: string;
}

export interface GitLabReviewResponse {
  review: unknown;
}

export interface TaskLogsResponse {
  logs: TaskLogs;
}

export interface HealthResponse {
  status: string;
}

export interface WorktreeListResponse {
  worktrees: Array<{
    specName: string;
    path: string;
    branch: string;
    baseBranch: string;
    commitCount?: number;
    filesChanged?: number;
    additions?: number;
    deletions?: number;
    isOrphaned?: boolean;
  }>;
}

export interface McpStatusResponse {
  servers: Array<{
    name: string;
    status: "connected" | "disconnected" | "error";
    toolCount?: number;
  }>;
}

// ============================================
// Request option types
// ============================================

export interface RequestOptions {
  signal?: AbortSignal;
  timeoutMs?: number;
}

// ============================================
// API Client
// ============================================

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Core request method with timeout and abort support.
   */
  private async request<T>(
    path: string,
    options: RequestInit = {},
    timeoutMs: number = 10000,
    externalSignal?: AbortSignal,
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);

    // Link external abort signal if provided
    const onExternalAbort = () => controller.abort();
    externalSignal?.addEventListener("abort", onExternalAbort);

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...options.headers,
        },
        signal: controller.signal,
      });

      if (!response.ok) {
        const error = await response.text().catch(() => "Unknown error");
        throw new Error(`API error ${response.status}: ${error}`);
      }

      return response.json();
    } finally {
      clearTimeout(timeout);
      externalSignal?.removeEventListener("abort", onExternalAbort);
    }
  }

  // ============================================
  // Projects
  // ============================================

  async getProjects(opts?: RequestOptions): Promise<ProjectListResponse> {
    return this.request<ProjectListResponse>(
      "/api/projects",
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async getProject(
    id: string,
    opts?: RequestOptions,
  ): Promise<ProjectResponse> {
    return this.request<ProjectResponse>(
      `/api/projects/${id}`,
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async createProject(
    data: { name: string; path: string },
    opts?: RequestOptions,
  ): Promise<ProjectResponse> {
    return this.request<ProjectResponse>(
      "/api/projects",
      { method: "POST", body: JSON.stringify(data) },
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async updateProjectSettings(
    projectId: string,
    settings: Partial<ProjectSettings>,
    opts?: RequestOptions,
  ): Promise<ApiResponse> {
    return this.request<ApiResponse>(
      `/api/projects/${projectId}/settings`,
      { method: "PUT", body: JSON.stringify(settings) },
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  // ============================================
  // Tasks
  // ============================================

  async getTasks(
    projectId: string,
    opts?: RequestOptions,
  ): Promise<TaskListResponse> {
    return this.request<TaskListResponse>(
      `/api/projects/${projectId}/tasks`,
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async getTask(
    projectId: string,
    taskId: string,
    opts?: RequestOptions,
  ): Promise<TaskResponse> {
    return this.request<TaskResponse>(
      `/api/projects/${projectId}/tasks/${taskId}`,
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async createTask(
    projectId: string,
    data: { title: string; description: string; metadata?: TaskMetadata },
    opts?: RequestOptions,
  ): Promise<TaskResponse> {
    return this.request<TaskResponse>(
      `/api/projects/${projectId}/tasks`,
      { method: "POST", body: JSON.stringify(data) },
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async updateTaskStatus(
    projectId: string,
    taskId: string,
    status: TaskStatus,
    opts?: RequestOptions,
  ): Promise<ApiResponse> {
    return this.request<ApiResponse>(
      `/api/projects/${projectId}/tasks/${taskId}/status`,
      { method: "PUT", body: JSON.stringify({ status }) },
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async updateTask(
    projectId: string,
    taskId: string,
    data: Record<string, unknown>,
    opts?: RequestOptions,
  ): Promise<TaskResponse> {
    return this.request<TaskResponse>(
      `/api/projects/${projectId}/tasks/${taskId}`,
      { method: "PUT", body: JSON.stringify(data) },
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async createPR(
    projectId: string,
    taskId: string,
    opts?: RequestOptions,
  ): Promise<ApiResponse<{ url: string }>> {
    return this.request<ApiResponse<{ url: string }>>(
      `/api/projects/${projectId}/tasks/${taskId}/pr`,
      { method: "POST" },
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async deleteTask(
    projectId: string,
    taskId: string,
    opts?: RequestOptions,
  ): Promise<ApiResponse> {
    return this.request<ApiResponse>(
      `/api/projects/${projectId}/tasks/${taskId}`,
      { method: "DELETE" },
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async startTask(
    projectId: string,
    taskId: string,
    options?: Record<string, unknown>,
    opts?: RequestOptions,
  ): Promise<ApiResponse> {
    return this.request<ApiResponse>(
      `/api/projects/${projectId}/tasks/${taskId}/start`,
      { method: "POST", body: JSON.stringify(options ?? {}) },
      opts?.timeoutMs ?? 30000,
      opts?.signal,
    );
  }

  async stopTask(
    projectId: string,
    taskId: string,
    opts?: RequestOptions,
  ): Promise<ApiResponse> {
    return this.request<ApiResponse>(
      `/api/projects/${projectId}/tasks/${taskId}/stop`,
      { method: "POST" },
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async getTaskLogs(
    projectId: string,
    specId: string,
    opts?: RequestOptions,
  ): Promise<TaskLogsResponse> {
    return this.request<TaskLogsResponse>(
      `/api/projects/${projectId}/tasks/${specId}/logs`,
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async getTaskPlan(
    projectId: string,
    taskId: string,
    opts?: RequestOptions,
  ): Promise<ApiResponse<ImplementationPlan>> {
    return this.request<ApiResponse<ImplementationPlan>>(
      `/api/projects/${projectId}/tasks/${taskId}/plan`,
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  // ============================================
  // Settings
  // ============================================

  async getSettings(opts?: RequestOptions): Promise<SettingsResponse> {
    return this.request<SettingsResponse>(
      "/api/settings",
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async saveSettings(
    settings: Record<string, unknown>,
    opts?: RequestOptions,
  ): Promise<ApiResponse> {
    return this.request<ApiResponse>(
      "/api/settings",
      { method: "PUT", body: JSON.stringify(settings) },
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  // ============================================
  // Environment Config
  // ============================================

  async getProjectEnv(
    projectId: string,
    opts?: RequestOptions,
  ): Promise<EnvConfigResponse> {
    return this.request<EnvConfigResponse>(
      `/api/projects/${projectId}/env`,
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async saveProjectEnv(
    projectId: string,
    config: Partial<ProjectEnvConfig>,
    opts?: RequestOptions,
  ): Promise<ApiResponse> {
    return this.request<ApiResponse>(
      `/api/projects/${projectId}/env`,
      { method: "PUT", body: JSON.stringify(config) },
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  // ============================================
  // Roadmap
  // ============================================

  async getRoadmap(
    projectId: string,
    opts?: RequestOptions,
  ): Promise<RoadmapResponse> {
    return this.request<RoadmapResponse>(
      `/api/projects/${projectId}/roadmap`,
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async generateRoadmap(
    projectId: string,
    opts?: RequestOptions,
  ): Promise<RoadmapResponse> {
    return this.request<RoadmapResponse>(
      `/api/projects/${projectId}/roadmap/generate`,
      { method: "POST" },
      opts?.timeoutMs ?? 60000,
      opts?.signal,
    );
  }

  // ============================================
  // Ideation
  // ============================================

  async getIdeas(
    projectId: string,
    opts?: RequestOptions,
  ): Promise<IdeationResponse> {
    return this.request<IdeationResponse>(
      `/api/projects/${projectId}/ideas`,
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async generateIdeas(
    projectId: string,
    data?: { category?: string },
    opts?: RequestOptions,
  ): Promise<IdeationResponse> {
    return this.request<IdeationResponse>(
      `/api/projects/${projectId}/ideas/generate`,
      { method: "POST", body: JSON.stringify(data ?? {}) },
      opts?.timeoutMs ?? 60000,
      opts?.signal,
    );
  }

  // ============================================
  // Insights (SSE Streaming)
  // ============================================

  /**
   * Query insights with Server-Sent Events streaming.
   * Returns an async generator that yields events as they arrive.
   */
  async *streamInsights(
    projectId: string,
    message: string,
    signal?: AbortSignal,
  ): AsyncGenerator<InsightsStreamEvent> {
    const url = `${this.baseUrl}/api/projects/${projectId}/insights/stream`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
      signal,
    });

    if (!response.ok) {
      const error = await response.text().catch(() => "Unknown error");
      throw new Error(`API error ${response.status}: ${error}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error("No response body for SSE stream");
    }

    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6).trim();
            if (data === "[DONE]") {
              yield { type: "done" };
              return;
            }
            try {
              yield JSON.parse(data) as InsightsStreamEvent;
            } catch {
              yield { type: "chunk", content: data };
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * Non-streaming insights query (falls back to simple POST).
   */
  async queryInsights(
    projectId: string,
    message: string,
    opts?: RequestOptions,
  ): Promise<ApiResponse<{ response: string }>> {
    return this.request<ApiResponse<{ response: string }>>(
      `/api/projects/${projectId}/insights`,
      { method: "POST", body: JSON.stringify({ message }) },
      opts?.timeoutMs ?? 60000,
      opts?.signal,
    );
  }

  // ============================================
  // Changelog
  // ============================================

  async getChangelog(
    projectId: string,
    opts?: RequestOptions,
  ): Promise<ChangelogResponse> {
    return this.request<ChangelogResponse>(
      `/api/projects/${projectId}/changelog`,
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async generateChangelog(
    projectId: string,
    data?: { version?: string; taskIds?: string[] },
    opts?: RequestOptions,
  ): Promise<ChangelogResponse> {
    return this.request<ChangelogResponse>(
      `/api/projects/${projectId}/changelog/generate`,
      { method: "POST", body: JSON.stringify(data ?? {}) },
      opts?.timeoutMs ?? 60000,
      opts?.signal,
    );
  }

  // ============================================
  // Context
  // ============================================

  async getProjectContext(
    projectId: string,
    opts?: RequestOptions,
  ): Promise<ContextResponse> {
    return this.request<ContextResponse>(
      `/api/projects/${projectId}/context`,
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async getMemories(
    projectId: string,
    query?: string,
    opts?: RequestOptions,
  ): Promise<MemoriesResponse> {
    const params = query
      ? `?query=${encodeURIComponent(query)}`
      : "";
    return this.request<MemoriesResponse>(
      `/api/projects/${projectId}/context/memories${params}`,
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async refreshProjectIndex(
    projectId: string,
    opts?: RequestOptions,
  ): Promise<ProjectIndexResponse> {
    return this.request<ProjectIndexResponse>(
      `/api/projects/${projectId}/context/index`,
      { method: "POST" },
      opts?.timeoutMs ?? 30000,
      opts?.signal,
    );
  }

  // ============================================
  // GitHub
  // ============================================

  async getGitHubIssues(
    projectId: string,
    opts?: RequestOptions,
  ): Promise<GitHubIssuesResponse> {
    return this.request<GitHubIssuesResponse>(
      `/api/projects/${projectId}/github/issues`,
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async getGitHubPRs(
    projectId: string,
    opts?: RequestOptions,
  ): Promise<GitHubPRsResponse> {
    return this.request<GitHubPRsResponse>(
      `/api/projects/${projectId}/github/prs`,
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async getGitHubOAuthUrl(
    projectId: string,
    opts?: RequestOptions,
  ): Promise<GitHubOAuthResponse> {
    return this.request<GitHubOAuthResponse>(
      `/api/projects/${projectId}/github/oauth`,
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async investigateGitHubIssue(
    projectId: string,
    issueNumber: number,
    opts?: RequestOptions,
  ): Promise<GitHubInvestigationResponse> {
    return this.request<GitHubInvestigationResponse>(
      `/api/projects/${projectId}/github/issues/${issueNumber}/investigate`,
      { method: "POST" },
      opts?.timeoutMs ?? 60000,
      opts?.signal,
    );
  }

  async reviewGitHubPR(
    projectId: string,
    prNumber: number,
    opts?: RequestOptions,
  ): Promise<GitHubReviewResponse> {
    return this.request<GitHubReviewResponse>(
      `/api/projects/${projectId}/github/prs/${prNumber}/review`,
      { method: "POST" },
      opts?.timeoutMs ?? 60000,
      opts?.signal,
    );
  }

  async autoFixGitHubPR(
    projectId: string,
    prNumber: number,
    opts?: RequestOptions,
  ): Promise<GitHubAutoFixResponse> {
    return this.request<GitHubAutoFixResponse>(
      `/api/projects/${projectId}/github/prs/${prNumber}/auto-fix`,
      { method: "POST" },
      opts?.timeoutMs ?? 120000,
      opts?.signal,
    );
  }

  // ============================================
  // GitLab
  // ============================================

  async getGitLabIssues(
    projectId: string,
    opts?: RequestOptions,
  ): Promise<GitLabIssuesResponse> {
    return this.request<GitLabIssuesResponse>(
      `/api/projects/${projectId}/gitlab/issues`,
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async getGitLabMRs(
    projectId: string,
    opts?: RequestOptions,
  ): Promise<GitLabMRsResponse> {
    return this.request<GitLabMRsResponse>(
      `/api/projects/${projectId}/gitlab/merge-requests`,
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async getGitLabOAuthUrl(
    projectId: string,
    opts?: RequestOptions,
  ): Promise<GitLabOAuthResponse> {
    return this.request<GitLabOAuthResponse>(
      `/api/projects/${projectId}/gitlab/oauth`,
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async reviewGitLabMR(
    projectId: string,
    mrNumber: number,
    opts?: RequestOptions,
  ): Promise<GitLabReviewResponse> {
    return this.request<GitLabReviewResponse>(
      `/api/projects/${projectId}/gitlab/merge-requests/${mrNumber}/review`,
      { method: "POST" },
      opts?.timeoutMs ?? 60000,
      opts?.signal,
    );
  }

  // ============================================
  // Worktrees
  // ============================================

  async listWorktrees(
    projectId: string,
    opts?: RequestOptions,
  ): Promise<WorktreeListResponse> {
    return this.request<WorktreeListResponse>(
      `/api/projects/${projectId}/worktrees`,
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  async mergeWorktree(
    projectId: string,
    specName: string,
    opts?: RequestOptions,
  ): Promise<ApiResponse> {
    return this.request<ApiResponse>(
      `/api/projects/${projectId}/worktrees/${specName}/merge`,
      { method: "POST" },
      opts?.timeoutMs ?? 60000,
      opts?.signal,
    );
  }

  async discardWorktree(
    projectId: string,
    specName: string,
    opts?: RequestOptions,
  ): Promise<ApiResponse> {
    return this.request<ApiResponse>(
      `/api/projects/${projectId}/worktrees/${specName}`,
      { method: "DELETE" },
      opts?.timeoutMs ?? 30000,
      opts?.signal,
    );
  }

  async createWorktree(
    projectId: string,
    specName: string,
    baseBranch?: string,
    opts?: RequestOptions,
  ): Promise<ApiResponse> {
    return this.request<ApiResponse>(
      `/api/projects/${projectId}/worktrees`,
      { method: "POST", body: JSON.stringify({ specName, baseBranch }) },
      opts?.timeoutMs ?? 30000,
      opts?.signal,
    );
  }

  // ============================================
  // MCP / Agent Tools
  // ============================================

  async getMcpStatus(
    projectId: string,
    opts?: RequestOptions,
  ): Promise<McpStatusResponse> {
    return this.request<McpStatusResponse>(
      `/api/projects/${projectId}/mcp/status`,
      {},
      opts?.timeoutMs,
      opts?.signal,
    );
  }

  // ============================================
  // Health
  // ============================================

  async health(opts?: RequestOptions): Promise<HealthResponse> {
    return this.request<HealthResponse>(
      "/api/health",
      {},
      opts?.timeoutMs ?? 3000,
      opts?.signal,
    );
  }
}

export const apiClient = new ApiClient();
