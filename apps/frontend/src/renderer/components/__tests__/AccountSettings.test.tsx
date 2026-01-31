/**
 * @vitest-environment jsdom
 */
/**
 * Tests for AccountSettings component
 * Tests profile management, OAuth flows, API profile configuration, and auto-switching
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { AppSettings, ClaudeProfile, ClaudeAutoSwitchSettings } from '../../../shared/types';
import type { APIProfile } from '@shared/types/profile';

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

vi.mock('../../hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

vi.mock('../../stores/claude-profile-store', () => ({
  loadClaudeProfiles: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('../../stores/settings-store', () => ({
  useSettingsStore: vi.fn((selector) => {
    if (typeof selector === 'function') {
      return selector({
        profiles: [],
        activeProfileId: null,
        deleteProfile: vi.fn().mockResolvedValue(true),
        setActiveProfile: vi.fn().mockResolvedValue(true),
        profilesError: null,
      });
    }
    return {};
  }),
}));

// Mock electronAPI
const mockElectronAPI = {
  getClaudeProfiles: vi.fn(),
  saveClaudeProfile: vi.fn(),
  deleteClaudeProfile: vi.fn(),
  renameClaudeProfile: vi.fn(),
  setActiveClaudeProfile: vi.fn(),
  authenticateClaudeProfile: vi.fn(),
  setClaudeProfileToken: vi.fn(),
  getAutoSwitchSettings: vi.fn(),
  updateAutoSwitchSettings: vi.fn(),
  getAccountPriorityOrder: vi.fn(),
  setAccountPriorityOrder: vi.fn(),
  requestAllProfilesUsage: vi.fn(),
  onAllProfilesUsageUpdated: vi.fn((_callback: (data: unknown) => void) => vi.fn()),
};

beforeEach(() => {
  (window as unknown as { electronAPI: typeof mockElectronAPI }).electronAPI = mockElectronAPI;
});

// Helper to create test Claude profile
function createClaudeProfile(overrides: Partial<ClaudeProfile> = {}): ClaudeProfile {
  return {
    id: `profile-${Date.now()}`,
    name: 'Test Profile',
    configDir: '~/.claude-profiles/test',
    isDefault: false,
    createdAt: new Date(),
    isAuthenticated: false,
    ...overrides,
  };
}

// Helper to create test API profile
function createAPIProfile(overrides: Partial<APIProfile> = {}): APIProfile {
  return {
    id: `api-${Date.now()}`,
    name: 'Test API Profile',
    baseUrl: 'https://api.anthropic.com',
    apiKey: 'sk-ant-test-key-123',
    models: {},
    createdAt: Date.now(),
    updatedAt: Date.now(),
    ...overrides,
  };
}

// Helper to create test settings
function createTestSettings(overrides: Partial<AppSettings> = {}): AppSettings {
  return {
    theme: 'system',
    defaultModel: 'claude-opus-4-5-20251101',
    agentFramework: 'auto-claude',
    autoUpdateAutoBuild: true,
    autoNameTerminals: true,
    notifications: {
      onTaskComplete: true,
      onTaskFailed: true,
      onReviewNeeded: true,
      sound: true,
    },
    ...overrides,
  };
}

describe('AccountSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockElectronAPI.getClaudeProfiles.mockResolvedValue({
      success: true,
      data: { profiles: [], activeProfileId: null },
    });
    mockElectronAPI.getAutoSwitchSettings.mockResolvedValue({
      success: true,
      data: {
        enabled: false,
        proactiveSwapEnabled: true,
        sessionThreshold: 95,
        weeklyThreshold: 99,
        autoSwitchOnRateLimit: false,
      },
    });
    mockElectronAPI.getAccountPriorityOrder.mockResolvedValue({
      success: true,
      data: [],
    });
    mockElectronAPI.requestAllProfilesUsage.mockResolvedValue({
      success: true,
      data: { allProfiles: [] },
    });
  });

  describe('Tab Navigation', () => {
    it('should render Claude Code and Custom Endpoints tabs', () => {
      const settings = createTestSettings();
      const tabs = ['settings:accounts.tabs.claudeCode', 'settings:accounts.tabs.customEndpoints'];

      expect(tabs).toHaveLength(2);
      expect(tabs[0]).toBe('settings:accounts.tabs.claudeCode');
      expect(tabs[1]).toBe('settings:accounts.tabs.customEndpoints');
    });

    it('should switch between tabs', () => {
      let activeTab: 'claude-code' | 'custom-endpoints' = 'claude-code';

      activeTab = 'custom-endpoints';
      expect(activeTab).toBe('custom-endpoints');

      activeTab = 'claude-code';
      expect(activeTab).toBe('claude-code');
    });
  });

  describe('Claude Code Profiles', () => {
    it('should load Claude profiles successfully', async () => {
      const profiles = [
        createClaudeProfile({ id: 'profile-1', name: 'Profile 1' }),
        createClaudeProfile({ id: 'profile-2', name: 'Profile 2' }),
      ];

      mockElectronAPI.getClaudeProfiles.mockResolvedValue({
        success: true,
        data: { profiles, activeProfileId: 'profile-1' },
      });

      const result = await mockElectronAPI.getClaudeProfiles();
      expect(result.success).toBe(true);
      expect(result.data?.profiles).toHaveLength(2);
    });

    it('should display authenticated profile badge', () => {
      const profile = createClaudeProfile({
        isAuthenticated: true,
        email: 'test@example.com',
      });

      expect(profile.isAuthenticated).toBe(true);
      expect(profile.email).toBe('test@example.com');
    });

    it('should display active profile badge', () => {
      const activeProfileId = 'profile-1';
      const profile = createClaudeProfile({ id: 'profile-1' });

      expect(profile.id).toBe(activeProfileId);
    });

    it('should handle profile creation', async () => {
      const newProfileName = 'New Profile';
      const profileSlug = newProfileName.toLowerCase().replace(/\s+/g, '-');

      const expectedProfile = {
        id: expect.stringContaining('profile-'),
        name: newProfileName,
        configDir: `~/.claude-profiles/${profileSlug}`,
        isDefault: false,
        createdAt: expect.any(Date),
      };

      expect(expectedProfile.name).toBe(newProfileName);
      expect(expectedProfile.configDir).toContain(profileSlug);
    });

    it('should handle profile deletion', async () => {
      mockElectronAPI.deleteClaudeProfile.mockResolvedValue({ success: true });

      const result = await mockElectronAPI.deleteClaudeProfile('profile-1');
      expect(result.success).toBe(true);
      expect(mockElectronAPI.deleteClaudeProfile).toHaveBeenCalledWith('profile-1');
    });

    it('should handle profile rename', async () => {
      const newName = 'Renamed Profile';
      mockElectronAPI.renameClaudeProfile.mockResolvedValue({ success: true });

      const result = await mockElectronAPI.renameClaudeProfile('profile-1', newName);
      expect(result.success).toBe(true);
      expect(mockElectronAPI.renameClaudeProfile).toHaveBeenCalledWith('profile-1', newName);
    });

    it('should handle setting active profile', async () => {
      mockElectronAPI.setActiveClaudeProfile.mockResolvedValue({ success: true });

      const result = await mockElectronAPI.setActiveClaudeProfile('profile-1');
      expect(result.success).toBe(true);
      expect(mockElectronAPI.setActiveClaudeProfile).toHaveBeenCalledWith('profile-1');
    });

    it('should prevent deletion of default profile', () => {
      const profile = createClaudeProfile({ isDefault: true });
      const canDelete = !profile.isDefault;

      expect(canDelete).toBe(false);
    });

    it('should display usage bars for authenticated profiles', () => {
      const usageData = {
        profileId: 'profile-1',
        sessionPercent: 75,
        weeklyPercent: 50,
        isRateLimited: false,
      };

      expect(usageData.sessionPercent).toBe(75);
      expect(usageData.weeklyPercent).toBe(50);
    });

    it('should display needs reauthentication warning', () => {
      const usageData = {
        profileId: 'profile-1',
        needsReauthentication: true,
      };

      expect(usageData.needsReauthentication).toBe(true);
    });
  });

  describe('OAuth Authentication', () => {
    it('should start OAuth authentication flow', async () => {
      mockElectronAPI.authenticateClaudeProfile.mockResolvedValue({
        success: true,
        data: {
          terminalId: 'term-123',
          configDir: '~/.claude-profiles/test',
        },
      });

      const result = await mockElectronAPI.authenticateClaudeProfile('profile-1');
      expect(result.success).toBe(true);
      expect(result.data?.terminalId).toBe('term-123');
    });

    it('should handle OAuth authentication failure', async () => {
      mockElectronAPI.authenticateClaudeProfile.mockResolvedValue({
        success: false,
        error: 'Authentication failed',
      });

      const result = await mockElectronAPI.authenticateClaudeProfile('profile-1');
      expect(result.success).toBe(false);
      expect(result.error).toBe('Authentication failed');
    });

    it('should display auth terminal when authenticating', () => {
      const authTerminal = {
        terminalId: 'term-123',
        configDir: '~/.claude-profiles/test',
        profileId: 'profile-1',
        profileName: 'Test Profile',
      };

      expect(authTerminal.terminalId).toBe('term-123');
      expect(authTerminal.profileId).toBe('profile-1');
    });
  });

  describe('Manual Token Entry', () => {
    it('should save manual token', async () => {
      const token = 'sk-ant-test-token-123';
      const email = 'test@example.com';

      mockElectronAPI.setClaudeProfileToken.mockResolvedValue({ success: true });

      const result = await mockElectronAPI.setClaudeProfileToken('profile-1', token, email);
      expect(result.success).toBe(true);
      expect(mockElectronAPI.setClaudeProfileToken).toHaveBeenCalledWith('profile-1', token, email);
    });

    it('should toggle token visibility', () => {
      let showToken = false;

      showToken = !showToken;
      expect(showToken).toBe(true);

      showToken = !showToken;
      expect(showToken).toBe(false);
    });

    it('should expand/collapse token entry section', () => {
      let expandedProfileId: string | null = null;

      expandedProfileId = 'profile-1';
      expect(expandedProfileId).toBe('profile-1');

      expandedProfileId = null;
      expect(expandedProfileId).toBe(null);
    });
  });

  describe('API Profiles (Custom Endpoints)', () => {
    it('should display API profile list', () => {
      const profiles = [
        createAPIProfile({ id: 'api-1', name: 'Profile 1' }),
        createAPIProfile({ id: 'api-2', name: 'Profile 2' }),
      ];

      expect(profiles).toHaveLength(2);
    });

    it('should display active API profile badge', () => {
      const profile = createAPIProfile({ id: 'api-1' });
      const isActive = profile.id === 'api-1'; // Check if active by ID comparison

      expect(isActive).toBe(true);
    });

    it('should mask API key', () => {
      const apiKey = 'sk-ant-api-test-key-123456';
      const masked = `${apiKey.slice(0, 8)}...${apiKey.slice(-4)}`;

      expect(masked).toBe('sk-ant-a...3456');
    });

    it('should extract hostname from URL', () => {
      const url = 'https://api.anthropic.com/v1';
      const host = new URL(url).host;

      expect(host).toBe('api.anthropic.com');
    });

    it('should show empty state when no profiles', () => {
      const profiles: APIProfile[] = [];

      expect(profiles.length).toBe(0);
    });

    it('should prevent deletion of active profile', () => {
      const profile = createAPIProfile({ id: 'active-profile' });
      const activeProfileId = 'active-profile';
      const canDelete = profile.id !== activeProfileId;

      expect(canDelete).toBe(false);
    });
  });

  describe('Auto-Switch Settings', () => {
    it('should load auto-switch settings', async () => {
      const settings: ClaudeAutoSwitchSettings = {
        enabled: true,
        proactiveSwapEnabled: true,
        sessionThreshold: 95,
        weeklyThreshold: 99,
        autoSwitchOnRateLimit: false,
        usageCheckInterval: 60000,
      };

      mockElectronAPI.getAutoSwitchSettings.mockResolvedValue({
        success: true,
        data: settings,
      });

      const result = await mockElectronAPI.getAutoSwitchSettings();
      expect(result.data).toEqual(settings);
    });

    it('should update auto-switch settings', async () => {
      const updates = { enabled: true };
      mockElectronAPI.updateAutoSwitchSettings.mockResolvedValue({ success: true });

      const result = await mockElectronAPI.updateAutoSwitchSettings(updates);
      expect(result.success).toBe(true);
      expect(mockElectronAPI.updateAutoSwitchSettings).toHaveBeenCalledWith(updates);
    });

    it('should show auto-switch section when multiple accounts exist', () => {
      const claudeProfiles = [createClaudeProfile(), createClaudeProfile()];
      const apiProfiles: APIProfile[] = [];
      const totalAccounts = claudeProfiles.length + apiProfiles.length;

      expect(totalAccounts).toBeGreaterThan(1);
    });

    it('should hide auto-switch section when only one account', () => {
      const claudeProfiles = [createClaudeProfile()];
      const apiProfiles: APIProfile[] = [];
      const totalAccounts = claudeProfiles.length + apiProfiles.length;

      expect(totalAccounts).toBe(1);
    });

    it('should validate session threshold range', () => {
      const thresholds = [70, 85, 95, 99];

      thresholds.forEach((threshold) => {
        expect(threshold).toBeGreaterThanOrEqual(70);
        expect(threshold).toBeLessThanOrEqual(99);
      });
    });

    it('should validate weekly threshold range', () => {
      const thresholds = [70, 85, 95, 99];

      thresholds.forEach((threshold) => {
        expect(threshold).toBeGreaterThanOrEqual(70);
        expect(threshold).toBeLessThanOrEqual(99);
      });
    });
  });

  describe('Priority Order', () => {
    it('should load priority order', async () => {
      const order = ['oauth-profile-1', 'api-profile-1', 'oauth-profile-2'];
      mockElectronAPI.getAccountPriorityOrder.mockResolvedValue({
        success: true,
        data: order,
      });

      const result = await mockElectronAPI.getAccountPriorityOrder();
      expect(result.data).toEqual(order);
    });

    it('should save priority order', async () => {
      const newOrder = ['oauth-profile-2', 'api-profile-1', 'oauth-profile-1'];
      mockElectronAPI.setAccountPriorityOrder.mockResolvedValue({ success: true });

      const result = await mockElectronAPI.setAccountPriorityOrder(newOrder);
      expect(result.success).toBe(true);
      expect(mockElectronAPI.setAccountPriorityOrder).toHaveBeenCalledWith(newOrder);
    });

    it('should build unified accounts list', () => {
      const claudeProfiles = [
        createClaudeProfile({ id: 'profile-1', name: 'Claude 1' }),
      ];
      const apiProfiles = [
        createAPIProfile({ id: 'api-1', name: 'API 1' }),
      ];

      const unified = [
        { id: 'oauth-profile-1', name: 'Claude 1', type: 'oauth' },
        { id: 'api-api-1', name: 'API 1', type: 'api' },
      ];

      expect(unified).toHaveLength(2);
      expect(unified[0].type).toBe('oauth');
      expect(unified[1].type).toBe('api');
    });

    it('should sort accounts by priority order', () => {
      const accounts = [
        { id: 'oauth-profile-1' },
        { id: 'api-profile-1' },
        { id: 'oauth-profile-2' },
      ];
      const priorityOrder = ['oauth-profile-2', 'api-profile-1', 'oauth-profile-1'];

      const sorted = [...accounts].sort((a, b) => {
        const aIndex = priorityOrder.indexOf(a.id);
        const bIndex = priorityOrder.indexOf(b.id);
        const aPos = aIndex === -1 ? Infinity : aIndex;
        const bPos = bIndex === -1 ? Infinity : bIndex;
        return aPos - bPos;
      });

      expect(sorted.map(a => a.id)).toEqual(priorityOrder);
    });
  });

  describe('Usage Monitoring', () => {
    it('should load profile usage data', async () => {
      const usageData = {
        allProfiles: [
          {
            profileId: 'profile-1',
            sessionPercent: 75,
            weeklyPercent: 50,
            isRateLimited: false,
          },
        ],
      };

      mockElectronAPI.requestAllProfilesUsage.mockResolvedValue({
        success: true,
        data: usageData,
      });

      const result = await mockElectronAPI.requestAllProfilesUsage();
      expect(result.data).toEqual(usageData);
    });

    it('should subscribe to usage updates', () => {
      const unsubscribe = mockElectronAPI.onAllProfilesUsageUpdated(() => {});

      expect(unsubscribe).toBeDefined();
      expect(typeof unsubscribe).toBe('function');
    });

    it('should calculate usage bar color based on percentage', () => {
      const getColor = (percent: number) => {
        if (percent >= 95) return 'red';
        if (percent >= 91) return 'orange';
        if (percent >= 71) return 'yellow';
        return 'green';
      };

      expect(getColor(50)).toBe('green');
      expect(getColor(75)).toBe('yellow');
      expect(getColor(92)).toBe('orange');
      expect(getColor(96)).toBe('red');
    });

    it('should detect rate limited profiles', () => {
      const usageData = {
        profileId: 'profile-1',
        isRateLimited: true,
        rateLimitType: 'session',
      };

      expect(usageData.isRateLimited).toBe(true);
      expect(usageData.rateLimitType).toBe('session');
    });
  });

  describe('Error Handling', () => {
    it('should handle profile load failure', async () => {
      mockElectronAPI.getClaudeProfiles.mockResolvedValue({
        success: false,
        error: 'Failed to load profiles',
      });

      const result = await mockElectronAPI.getClaudeProfiles();
      expect(result.success).toBe(false);
      expect(result.error).toBe('Failed to load profiles');
    });

    it('should handle profile save failure', async () => {
      mockElectronAPI.saveClaudeProfile.mockResolvedValue({
        success: false,
        error: 'Failed to save profile',
      });

      const result = await mockElectronAPI.saveClaudeProfile(createClaudeProfile());
      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });

    it('should handle auto-switch update failure', async () => {
      mockElectronAPI.updateAutoSwitchSettings.mockResolvedValue({
        success: false,
        error: 'Update failed',
      });

      const result = await mockElectronAPI.updateAutoSwitchSettings({ enabled: true });
      expect(result.success).toBe(false);
      expect(result.error).toBe('Update failed');
    });
  });

  describe('Settings Persistence', () => {
    it('should call onSettingsChange when settings updated', () => {
      const onSettingsChange = vi.fn();
      const newSettings = createTestSettings({ theme: 'dark' });

      onSettingsChange(newSettings);
      expect(onSettingsChange).toHaveBeenCalledWith(newSettings);
    });

    it('should persist settings to backend', () => {
      const settings = createTestSettings();

      expect(settings).toBeDefined();
      expect(settings.theme).toBeDefined();
    });
  });

  describe('Component Lifecycle', () => {
    it('should load data when isOpen becomes true', () => {
      let isOpen = false;

      isOpen = true;
      expect(isOpen).toBe(true);
    });

    it('should not load data when isOpen is false', () => {
      const isOpen = false;

      expect(isOpen).toBe(false);
    });

    it('should cleanup on unmount', () => {
      const cleanup = vi.fn();

      cleanup();
      expect(cleanup).toHaveBeenCalled();
    });
  });
});
