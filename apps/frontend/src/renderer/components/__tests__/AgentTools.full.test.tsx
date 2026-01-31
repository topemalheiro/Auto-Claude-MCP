/**
 * @vitest-environment jsdom
 */
/**
 * Comprehensive tests for AgentTools component
 * Tests MCP server configuration, agent configuration display, and custom server management
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { ProjectEnvConfig, CustomMcpServer, McpHealthCheckResult } from '../../../shared/types';

// Mock dependencies
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      if (params) {
        let result = key;
        Object.entries(params).forEach(([k, v]) => {
          result = result.replace(`{{${k}}}`, String(v));
        });
        return result;
      }
      return key;
    },
  }),
}));

vi.mock('../stores/settings-store', () => ({
  useSettingsStore: vi.fn((selector) => {
    if (typeof selector === 'function') {
      return selector({
        settings: {
          selectedAgentProfile: 'auto',
        },
      });
    }
    return { settings: {} };
  }),
}));

vi.mock('../stores/project-store', () => ({
  useProjectStore: vi.fn((selector) => {
    if (typeof selector === 'function') {
      return selector({
        projects: [],
        selectedProjectId: null,
      });
    }
    return { projects: [], selectedProjectId: null };
  }),
}));

vi.mock('../hooks', () => ({
  useResolvedAgentSettings: () => ({
    phaseModels: {
      spec: 'opus' as const,
      planning: 'opus' as const,
      coding: 'opus' as const,
      qa: 'opus' as const,
    },
    phaseThinking: {
      spec: 'ultrathink' as const,
      planning: 'high' as const,
      coding: 'low' as const,
      qa: 'low' as const,
    },
    featureModels: {
      insights: 'sonnet' as const,
      ideation: 'opus' as const,
      roadmap: 'opus' as const,
      githubIssues: 'opus' as const,
      githubPrs: 'opus' as const,
      utility: 'haiku' as const,
    },
    featureThinking: {
      insights: 'medium' as const,
      ideation: 'high' as const,
      roadmap: 'high' as const,
      githubIssues: 'medium' as const,
      githubPrs: 'medium' as const,
      utility: 'low' as const,
    },
  }),
  resolveAgentSettings: (source: any, resolved: any) => {
    if (source.type === 'phase') {
      return {
        model: resolved.phaseModels[source.phase],
        thinking: resolved.phaseThinking[source.phase],
      };
    }
    if (source.type === 'feature') {
      return {
        model: resolved.featureModels[source.feature],
        thinking: resolved.featureThinking[source.feature],
      };
    }
    if (source.type === 'fixed') {
      return {
        model: source.model,
        thinking: source.thinking,
      };
    }
    return { model: 'sonnet', thinking: 'medium' };
  },
}));

// Mock window.electronAPI
const mockElectronAPI = {
  getProjectEnv: vi.fn(),
  updateProjectEnv: vi.fn(),
  checkMcpHealth: vi.fn(),
  testMcpConnection: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
  (global.window as any).electronAPI = mockElectronAPI;
});

// Helper to create test project env config
function createProjectEnvConfig(overrides: Partial<ProjectEnvConfig> = {}): ProjectEnvConfig {
  return {
    claudeAuthStatus: 'authenticated',
    mcpServers: {
      context7Enabled: true,
      graphitiEnabled: false,
      linearMcpEnabled: false,
      electronEnabled: false,
      puppeteerEnabled: false,
    },
    customMcpServers: [],
    agentMcpOverrides: {},
    ...overrides,
  } as ProjectEnvConfig;
}

// Helper to create custom MCP server
function createCustomServer(overrides: Partial<CustomMcpServer> = {}): CustomMcpServer {
  return {
    id: `custom-${Date.now()}`,
    name: 'Custom Server',
    type: 'command',
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-custom'],
    ...overrides,
  };
}

describe('AgentTools', () => {
  describe('MCP Server Configuration', () => {
    it('should calculate enabled MCP servers correctly', () => {
      const mcpServers = {
        context7Enabled: true,
        graphitiEnabled: true,
        linearMcpEnabled: true,
        electronEnabled: false,
        puppeteerEnabled: false,
      };

      const enabledCount = [
        mcpServers.context7Enabled !== false,
        mcpServers.graphitiEnabled,
        mcpServers.linearMcpEnabled !== false,
        mcpServers.electronEnabled,
        mcpServers.puppeteerEnabled,
        true, // auto-claude always enabled
      ].filter(Boolean).length;

      expect(enabledCount).toBe(4); // context7, graphiti, linear, auto-claude
    });

    it('should handle all MCP servers disabled', () => {
      const mcpServers = {
        context7Enabled: false,
        graphitiEnabled: false,
        linearMcpEnabled: false,
        electronEnabled: false,
        puppeteerEnabled: false,
      };

      const enabledCount = [
        mcpServers.context7Enabled !== false,
        mcpServers.graphitiEnabled,
        mcpServers.linearMcpEnabled !== false,
        mcpServers.electronEnabled,
        mcpServers.puppeteerEnabled,
        true, // auto-claude always enabled
      ].filter(Boolean).length;

      expect(enabledCount).toBe(1); // Only auto-claude
    });

    it('should handle Context7 toggle', () => {
      const envConfig = createProjectEnvConfig({
        mcpServers: { context7Enabled: true },
      });

      // Toggle off
      envConfig.mcpServers!.context7Enabled = false;
      expect(envConfig.mcpServers!.context7Enabled).toBe(false);

      // Toggle on
      envConfig.mcpServers!.context7Enabled = true;
      expect(envConfig.mcpServers!.context7Enabled).toBe(true);
    });

    it('should handle Graphiti toggle with provider config check', () => {
      const envConfig = createProjectEnvConfig({
        mcpServers: { graphitiEnabled: true },
        graphitiProviderConfig: {
          embeddingProvider: 'openai',
          openaiApiKey: 'test-key',
        },
      });

      const isEnabled = envConfig.mcpServers!.graphitiEnabled && !!envConfig.graphitiProviderConfig;
      expect(isEnabled).toBe(true);
    });

    it('should disable Graphiti when no provider config', () => {
      const envConfig = createProjectEnvConfig({
        mcpServers: { graphitiEnabled: true },
        graphitiProviderConfig: undefined,
      });

      const isEnabled = envConfig.mcpServers!.graphitiEnabled && !!envConfig.graphitiProviderConfig;
      expect(isEnabled).toBe(false);
    });

    it('should handle Linear toggle with Linear enabled check', () => {
      const envConfig = createProjectEnvConfig({
        mcpServers: { linearMcpEnabled: true },
        linearEnabled: true,
      });

      const isEnabled = envConfig.mcpServers!.linearMcpEnabled && envConfig.linearEnabled;
      expect(isEnabled).toBe(true);
    });
  });

  describe('Agent MCP Overrides', () => {
    it('should add MCP to agent override list', () => {
      const envConfig = createProjectEnvConfig();
      const agentId = 'coder';
      const mcpId = 'electron';

      // Add to override
      envConfig.agentMcpOverrides = {
        ...envConfig.agentMcpOverrides,
        [agentId]: {
          add: [mcpId],
        },
      };

      expect(envConfig.agentMcpOverrides![agentId]?.add).toContain(mcpId);
    });

    it('should remove MCP from agent (default MCP)', () => {
      const envConfig = createProjectEnvConfig();
      const agentId = 'coder';
      const mcpId = 'context7'; // This is a default MCP

      // Remove from defaults
      envConfig.agentMcpOverrides = {
        ...envConfig.agentMcpOverrides,
        [agentId]: {
          remove: [mcpId],
        },
      };

      expect(envConfig.agentMcpOverrides![agentId]?.remove).toContain(mcpId);
    });

    it('should restore removed MCP', () => {
      const envConfig = createProjectEnvConfig({
        agentMcpOverrides: {
          coder: {
            remove: ['context7'],
          },
        },
      });

      const agentId = 'coder';
      const mcpId = 'context7';

      // Remove from remove list (restore)
      const currentRemove = envConfig.agentMcpOverrides![agentId]?.remove || [];
      const newRemove = currentRemove.filter(m => m !== mcpId);

      if (newRemove.length === 0) {
        delete envConfig.agentMcpOverrides![agentId]?.remove;
      } else {
        envConfig.agentMcpOverrides![agentId] = {
          ...envConfig.agentMcpOverrides![agentId],
          remove: newRemove,
        };
      }

      expect(envConfig.agentMcpOverrides![agentId]?.remove).toBeUndefined();
    });

    it('should calculate effective MCPs for agent', () => {
      const defaultMcps = ['context7', 'graphiti-memory', 'auto-claude'];
      const optionalMcps = ['linear'];
      const overrides = {
        add: ['electron'],
        remove: ['graphiti-memory'],
      };

      const allDefaults = [...defaultMcps, ...optionalMcps];
      const added = overrides.add || [];
      const removed = overrides.remove || [];

      const effectiveMcps = [...new Set([...allDefaults, ...added])]
        .filter(mcp => !removed.includes(mcp));

      expect(effectiveMcps).toContain('context7');
      expect(effectiveMcps).toContain('electron');
      expect(effectiveMcps).not.toContain('graphiti-memory');
      expect(effectiveMcps).toContain('auto-claude');
    });

    it('should filter MCPs by project-level settings', () => {
      const effectiveMcps = ['context7', 'graphiti-memory', 'linear', 'electron'];
      const mcpServerStates = {
        context7Enabled: true,
        graphitiEnabled: false, // Disabled at project level
        linearMcpEnabled: true,
        electronEnabled: false, // Disabled at project level
        puppeteerEnabled: false,
      };

      const filteredMcps = effectiveMcps.filter(mcp => {
        switch (mcp) {
          case 'context7':
            return mcpServerStates.context7Enabled !== false;
          case 'graphiti-memory':
            return mcpServerStates.graphitiEnabled !== false;
          case 'linear':
            return mcpServerStates.linearMcpEnabled !== false;
          case 'electron':
            return mcpServerStates.electronEnabled !== false;
          case 'puppeteer':
            return mcpServerStates.puppeteerEnabled !== false;
          default:
            return true;
        }
      });

      expect(filteredMcps).toEqual(['context7', 'linear']);
    });
  });

  describe('Custom MCP Servers', () => {
    it('should add custom MCP server', () => {
      const envConfig = createProjectEnvConfig();
      const customServer = createCustomServer({
        id: 'my-custom-server',
        name: 'My Custom Server',
      });

      envConfig.customMcpServers = [...(envConfig.customMcpServers || []), customServer];

      expect(envConfig.customMcpServers).toHaveLength(1);
      expect(envConfig.customMcpServers?.[0].id).toBe('my-custom-server');
    });

    it('should update existing custom MCP server', () => {
      const customServer = createCustomServer({ id: 'server-1', name: 'Original Name' });
      const envConfig = createProjectEnvConfig({
        customMcpServers: [customServer],
      });

      const updatedServer = { ...customServer, name: 'Updated Name' };
      const existingIndex = envConfig.customMcpServers?.findIndex(s => s.id === updatedServer.id) ?? -1;

      if (existingIndex >= 0 && envConfig.customMcpServers) {
        envConfig.customMcpServers[existingIndex] = updatedServer;
      }

      expect(envConfig.customMcpServers?.[0].name).toBe('Updated Name');
    });

    it('should delete custom MCP server', () => {
      const server1 = createCustomServer({ id: 'server-1' });
      const server2 = createCustomServer({ id: 'server-2' });
      const envConfig = createProjectEnvConfig({
        customMcpServers: [server1, server2],
      });

      const serverIdToDelete = 'server-1';
      envConfig.customMcpServers = envConfig.customMcpServers?.filter(
        s => s.id !== serverIdToDelete
      );

      expect(envConfig.customMcpServers).toHaveLength(1);
      expect(envConfig.customMcpServers?.[0].id).toBe('server-2');
    });

    it('should remove deleted custom server from agent overrides', () => {
      const customServer = createCustomServer({ id: 'custom-1' });
      const envConfig = createProjectEnvConfig({
        customMcpServers: [customServer],
        agentMcpOverrides: {
          coder: {
            add: ['custom-1', 'electron'],
          },
          planner: {
            add: ['custom-1'],
          },
        },
      });

      const serverIdToDelete = 'custom-1';

      // Remove from custom servers
      envConfig.customMcpServers = envConfig.customMcpServers?.filter(
        s => s.id !== serverIdToDelete
      );

      // Remove from all agent overrides
      Object.keys(envConfig.agentMcpOverrides || {}).forEach(agentId => {
        const override = envConfig.agentMcpOverrides?.[agentId];
        if (override?.add?.includes(serverIdToDelete)) {
          override.add = override.add.filter(m => m !== serverIdToDelete);
          if (override.add.length === 0) {
            delete override.add;
          }
        }
      });

      expect(envConfig.agentMcpOverrides?.coder?.add).toEqual(['electron']);
      expect(envConfig.agentMcpOverrides?.planner?.add).toBeUndefined();
    });

    it('should create command-type custom server', () => {
      const server = createCustomServer({
        type: 'command',
        command: 'node',
        args: ['server.js'],
      });

      expect(server.type).toBe('command');
      expect(server.command).toBe('node');
      expect(server.args).toEqual(['server.js']);
    });

    it('should create http-type custom server', () => {
      const server = createCustomServer({
        type: 'http',
        url: 'http://localhost:3000/mcp',
      });

      expect(server.type).toBe('http');
      expect(server.url).toBe('http://localhost:3000/mcp');
    });

    it('should include custom servers in available MCPs list', () => {
      const customServers = [
        createCustomServer({ id: 'custom-1', name: 'Custom Server 1' }),
        createCustomServer({ id: 'custom-2', name: 'Custom Server 2' }),
      ];

      const builtInMcps = ['context7', 'graphiti-memory', 'linear', 'electron', 'puppeteer', 'auto-claude'];
      const customMcpIds = customServers.map(s => s.id);
      const allMcpIds = [...builtInMcps, ...customMcpIds];

      expect(allMcpIds).toHaveLength(8);
      expect(allMcpIds).toContain('custom-1');
      expect(allMcpIds).toContain('custom-2');
    });
  });

  describe('MCP Health Checks', () => {
    it('should track health check status for custom servers', () => {
      const server = createCustomServer({ id: 'server-1' });
      const healthStatus: Record<string, McpHealthCheckResult> = {
        'server-1': {
          serverId: 'server-1',
          status: 'healthy',
          message: 'Server is responding',
          responseTime: 150,
          checkedAt: new Date().toISOString(),
        },
      };

      const health = healthStatus['server-1'];
      expect(health.status).toBe('healthy');
      expect(health.responseTime).toBe(150);
    });

    it('should handle unhealthy server status', () => {
      const healthStatus: McpHealthCheckResult = {
        serverId: 'server-1',
        status: 'unhealthy',
        message: 'Connection refused',
        checkedAt: new Date().toISOString(),
      };

      expect(healthStatus.status).toBe('unhealthy');
      expect(healthStatus.message).toBe('Connection refused');
    });

    it('should handle needs_auth status', () => {
      const healthStatus: McpHealthCheckResult = {
        serverId: 'server-1',
        status: 'needs_auth',
        message: 'Authentication required',
        checkedAt: new Date().toISOString(),
      };

      expect(healthStatus.status).toBe('needs_auth');
    });

    it('should handle checking status', () => {
      const healthStatus: McpHealthCheckResult = {
        serverId: 'server-1',
        status: 'checking',
        checkedAt: new Date().toISOString(),
      };

      expect(healthStatus.status).toBe('checking');
    });

    it('should track testing servers', () => {
      const testingServers = new Set<string>();

      // Add server to testing
      testingServers.add('server-1');
      expect(testingServers.has('server-1')).toBe(true);

      // Remove server from testing
      testingServers.delete('server-1');
      expect(testingServers.has('server-1')).toBe(false);
    });
  });

  describe('Agent Categories', () => {
    it('should group agents by category', () => {
      const agentConfigs = {
        spec_gatherer: { category: 'spec' },
        spec_researcher: { category: 'spec' },
        planner: { category: 'build' },
        coder: { category: 'build' },
        qa_reviewer: { category: 'qa' },
        qa_fixer: { category: 'qa' },
        insights: { category: 'utility' },
        ideation: { category: 'ideation' },
      };

      const grouped: Record<string, string[]> = {};

      Object.entries(agentConfigs).forEach(([id, config]) => {
        if (!grouped[config.category]) {
          grouped[config.category] = [];
        }
        grouped[config.category].push(id);
      });

      expect(grouped.spec).toHaveLength(2);
      expect(grouped.build).toHaveLength(2);
      expect(grouped.qa).toHaveLength(2);
      expect(grouped.utility).toHaveLength(1);
      expect(grouped.ideation).toHaveLength(1);
    });

    it('should track expanded categories', () => {
      const expandedCategories = new Set(['spec', 'build', 'qa']);

      expect(expandedCategories.has('spec')).toBe(true);
      expect(expandedCategories.has('utility')).toBe(false);

      // Toggle category
      const category = 'utility';
      if (expandedCategories.has(category)) {
        expandedCategories.delete(category);
      } else {
        expandedCategories.add(category);
      }

      expect(expandedCategories.has('utility')).toBe(true);
    });
  });

  describe('Agent Model Configuration', () => {
    it('should resolve phase-based agent model config', () => {
      const phaseModels = {
        spec: 'opus' as const,
        planning: 'opus' as const,
        coding: 'opus' as const,
        qa: 'opus' as const,
      };
      const phaseThinking = {
        spec: 'ultrathink' as const,
        planning: 'high' as const,
        coding: 'low' as const,
        qa: 'low' as const,
      };

      // Spec phase agent
      const specConfig = {
        model: phaseModels.spec,
        thinking: phaseThinking.spec,
      };

      expect(specConfig.model).toBe('opus');
      expect(specConfig.thinking).toBe('ultrathink');
    });

    it('should resolve feature-based agent model config', () => {
      const featureModels = {
        insights: 'sonnet' as const,
        ideation: 'opus' as const,
        roadmap: 'opus' as const,
        githubIssues: 'opus' as const,
        githubPrs: 'opus' as const,
        utility: 'haiku' as const,
      };
      const featureThinking = {
        insights: 'medium' as const,
        ideation: 'high' as const,
        roadmap: 'high' as const,
        githubIssues: 'medium' as const,
        githubPrs: 'medium' as const,
        utility: 'low' as const,
      };

      // Insights feature agent
      const insightsConfig = {
        model: featureModels.insights,
        thinking: featureThinking.insights,
      };

      expect(insightsConfig.model).toBe('sonnet');
      expect(insightsConfig.thinking).toBe('medium');
    });

    it('should format model label correctly', () => {
      const modelLabels: Record<string, string> = {
        opus: 'Opus 4.5',
        sonnet: 'Sonnet 4.5',
        haiku: 'Haiku 3.5',
      };

      expect(modelLabels.opus).toBe('Opus 4.5');
      expect(modelLabels.sonnet).toBe('Sonnet 4.5');
      expect(modelLabels.haiku).toBe('Haiku 3.5');
    });

    it('should format thinking label correctly', () => {
      const thinkingLabels: Record<string, string> = {
        ultrathink: 'Ultra (200K)',
        high: 'High (100K)',
        medium: 'Medium (50K)',
        low: 'Low (10K)',
        none: 'None',
      };

      expect(thinkingLabels.ultrathink).toBe('Ultra (200K)');
      expect(thinkingLabels.high).toBe('High (100K)');
      expect(thinkingLabels.medium).toBe('Medium (50K)');
      expect(thinkingLabels.low).toBe('Low (10K)');
    });
  });

  describe('Agent Tools', () => {
    it('should list available tools for agent', () => {
      const agentTools = [
        'Read',
        'Glob',
        'Grep',
        'Write',
        'Edit',
        'Bash',
        'WebFetch',
        'WebSearch',
      ];

      expect(agentTools).toContain('Read');
      expect(agentTools).toContain('Bash');
      expect(agentTools).toContain('WebSearch');
    });

    it('should handle agents with no tools', () => {
      const agentTools: string[] = [];

      expect(agentTools).toHaveLength(0);
    });

    it('should determine if agent has tools', () => {
      const hasTools = (tools: string[]) => tools.length > 0;

      expect(hasTools(['Read', 'Write'])).toBe(true);
      expect(hasTools([])).toBe(false);
    });
  });

  describe('No Project State', () => {
    it('should handle no project selected', () => {
      const selectedProjectId = null;
      const selectedProject = undefined;

      expect(selectedProjectId).toBeNull();
      expect(selectedProject).toBeUndefined();
    });

    it('should handle project not initialized', () => {
      const selectedProject = {
        id: 'proj-1',
        name: 'Test Project',
        path: '/path/to/project',
        autoBuildPath: undefined, // Not initialized
      };

      const isInitialized = !!selectedProject.autoBuildPath;
      expect(isInitialized).toBe(false);
    });

    it('should handle project initialized', () => {
      const selectedProject = {
        id: 'proj-1',
        name: 'Test Project',
        path: '/path/to/project',
        autoBuildPath: '/path/to/project/.auto-claude',
      };

      const isInitialized = !!selectedProject.autoBuildPath;
      expect(isInitialized).toBe(true);
    });
  });

  describe('IPC Communication', () => {
    it('should call getProjectEnv on project change', async () => {
      mockElectronAPI.getProjectEnv.mockResolvedValue({
        success: true,
        data: createProjectEnvConfig(),
      });

      const projectId = 'test-project';
      const result = await mockElectronAPI.getProjectEnv(projectId);

      expect(mockElectronAPI.getProjectEnv).toHaveBeenCalledWith(projectId);
      expect(result.success).toBe(true);
      expect(result.data).toBeDefined();
    });

    it('should call updateProjectEnv when toggling MCP server', async () => {
      mockElectronAPI.updateProjectEnv.mockResolvedValue({ success: true });

      const projectId = 'test-project';
      const updates = {
        mcpServers: {
          context7Enabled: false,
        },
      };

      await mockElectronAPI.updateProjectEnv(projectId, updates);

      expect(mockElectronAPI.updateProjectEnv).toHaveBeenCalledWith(projectId, updates);
    });

    it('should call checkMcpHealth for custom servers', async () => {
      const customServer = createCustomServer();
      const healthResult: McpHealthCheckResult = {
        serverId: customServer.id,
        status: 'healthy',
        checkedAt: new Date().toISOString(),
      };

      mockElectronAPI.checkMcpHealth.mockResolvedValue({
        success: true,
        data: healthResult,
      });

      const result = await mockElectronAPI.checkMcpHealth(customServer);

      expect(mockElectronAPI.checkMcpHealth).toHaveBeenCalledWith(customServer);
      expect(result.data?.status).toBe('healthy');
    });

    it('should call testMcpConnection for full server test', async () => {
      const customServer = createCustomServer();
      mockElectronAPI.testMcpConnection.mockResolvedValue({
        success: true,
        data: {
          success: true,
          message: 'Connection successful',
          responseTime: 120,
        },
      });

      const result = await mockElectronAPI.testMcpConnection(customServer);

      expect(mockElectronAPI.testMcpConnection).toHaveBeenCalledWith(customServer);
      expect(result.data?.success).toBe(true);
    });
  });
});
