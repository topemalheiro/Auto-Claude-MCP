/**
 * HTTP API client for self-hosted mode.
 *
 * Communicates with the Python backend (Auto Claude) via REST API.
 * In self-hosted mode, the backend runs locally or on a user's server.
 */

import { API_URL } from "@/lib/cloud-mode";

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
    timeoutMs: number = 3000
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);

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
    }
  }

  // Projects
  async getProjects() {
    return this.request<{ projects: unknown[] }>("/api/projects");
  }

  async getProject(id: string) {
    return this.request<{ project: unknown }>(`/api/projects/${id}`);
  }

  // Tasks
  async getTasks(projectId: string) {
    return this.request<{ tasks: unknown[] }>(
      `/api/projects/${projectId}/tasks`
    );
  }

  async updateTaskStatus(projectId: string, taskId: string, status: string) {
    return this.request(`/api/projects/${projectId}/tasks/${taskId}/status`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    });
  }

  // Settings
  async getSettings() {
    return this.request<{ settings: unknown }>("/api/settings");
  }

  async updateSettings(settings: Record<string, unknown>) {
    return this.request("/api/settings", {
      method: "PUT",
      body: JSON.stringify(settings),
    });
  }

  // Project Env Config
  async getProjectEnv(projectId: string) {
    return this.request<{ config: unknown }>(
      `/api/projects/${projectId}/env`
    );
  }

  // Roadmap
  async getRoadmap(projectId: string) {
    return this.request(`/api/projects/${projectId}/roadmap`);
  }

  async generateRoadmap(projectId: string) {
    return this.request(
      `/api/projects/${projectId}/roadmap/generate`,
      { method: "POST" },
      30000
    );
  }

  // Changelog
  async getChangelog(projectId: string) {
    return this.request(`/api/projects/${projectId}/changelog`);
  }

  // Ideation
  async getIdeas(projectId: string) {
    return this.request(`/api/projects/${projectId}/ideas`);
  }

  // GitHub
  async getGitHubIssues(projectId: string) {
    return this.request(`/api/projects/${projectId}/github/issues`);
  }

  async getGitHubPRs(projectId: string) {
    return this.request(`/api/projects/${projectId}/github/prs`);
  }

  // GitLab
  async getGitLabIssues(projectId: string) {
    return this.request(`/api/projects/${projectId}/gitlab/issues`);
  }

  async getGitLabMRs(projectId: string) {
    return this.request(`/api/projects/${projectId}/gitlab/merge-requests`);
  }

  // Insights
  async sendInsightsMessage(projectId: string, message: string) {
    return this.request(
      `/api/projects/${projectId}/insights`,
      { method: "POST", body: JSON.stringify({ message }) },
      30000
    );
  }

  // Context
  async getProjectContext(projectId: string) {
    return this.request(`/api/projects/${projectId}/context`);
  }

  // Health check
  async health() {
    return this.request<{ status: string }>("/api/health");
  }
}

export const apiClient = new ApiClient();
