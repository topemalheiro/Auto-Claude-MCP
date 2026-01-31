/**
 * Tests for Claude Profile Manager
 * Comprehensive test coverage for profile management, tokens, and auto-switching
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { app } from 'electron';
import path from 'path';
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs';
import type { ClaudeProfile, ClaudeUsageData, ClaudeAutoSwitchSettings } from '../../shared/types';

// Mock dependencies before importing the module under test
vi.mock('electron', () => ({
  app: {
    getPath: vi.fn(() => '/tmp/test-app-data'),
    isPackaged: false
  }
}));

vi.mock('fs');
vi.mock('fs/promises', () => ({
  readFile: vi.fn(),
  mkdir: vi.fn()
}));

// Mock profile modules
vi.mock('../claude-profile/token-encryption', () => ({
  encryptToken: vi.fn((token: string) => `encrypted_${token}`),
  decryptToken: vi.fn((encrypted: string) => encrypted.replace('encrypted_', ''))
}));

vi.mock('../claude-profile/usage-parser', () => ({
  parseUsageOutput: vi.fn()
}));

vi.mock('../claude-profile/rate-limit-manager', () => ({
  recordRateLimitEvent: vi.fn(),
  isProfileRateLimited: vi.fn(() => ({ limited: false })),
  clearRateLimitEvents: vi.fn()
}));

vi.mock('../claude-profile/profile-storage', () => ({
  loadProfileStore: vi.fn(),
  loadProfileStoreAsync: vi.fn(),
  saveProfileStore: vi.fn(),
  DEFAULT_AUTO_SWITCH_SETTINGS: {
    enabled: false,
    proactiveSwapEnabled: false,
    sessionThreshold: 95,
    weeklyThreshold: 99,
    autoSwitchOnRateLimit: false,
    usageCheckInterval: 30000
  }
}));

vi.mock('../claude-profile/profile-scorer', () => ({
  getBestAvailableProfile: vi.fn(),
  shouldProactivelySwitch: vi.fn(() => ({ shouldSwitch: false })),
  getProfilesSortedByAvailability: vi.fn((profiles) => [...profiles])
}));

vi.mock('../claude-profile/credential-utils', () => ({
  getCredentialsFromKeychain: vi.fn(() => ({ token: null })),
  normalizeWindowsPath: vi.fn((path: string) => path)
}));

vi.mock('../claude-profile/profile-utils', () => ({
  CLAUDE_PROFILES_DIR: '/tmp/.claude-profiles',
  generateProfileId: vi.fn((name: string, profiles: any[]) => {
    const base = name.toLowerCase().replace(/[^a-z0-9]+/g, '-');
    return base;
  }),
  createProfileDirectory: vi.fn(async (name: string) => {
    const dir = `/tmp/.claude-profiles/${name.toLowerCase()}`;
    return dir;
  }),
  isProfileAuthenticated: vi.fn(() => true),
  hasValidToken: vi.fn(() => true),
  expandHomePath: vi.fn((path: string) => path.replace('~', '/home/user')),
  getEmailFromConfigDir: vi.fn(() => null)
}));

// Import after mocks are set up
import { ClaudeProfileManager, getClaudeProfileManager, initializeClaudeProfileManager } from '../claude-profile-manager';
import * as profileStorage from '../claude-profile/profile-storage';
import * as tokenEncryption from '../claude-profile/token-encryption';
import * as usageParser from '../claude-profile/usage-parser';
import * as rateLimitManager from '../claude-profile/rate-limit-manager';
import * as profileScorer from '../claude-profile/profile-scorer';
import * as credentialUtils from '../claude-profile/credential-utils';
import * as profileUtils from '../claude-profile/profile-utils';

describe('ClaudeProfileManager', () => {
  let manager: ClaudeProfileManager;
  const mockProfileData = {
    version: 3,
    profiles: [
      {
        id: 'primary',
        name: 'Primary',
        configDir: '/tmp/.claude-profiles/primary',
        isDefault: true,
        description: 'Primary Claude account',
        createdAt: new Date('2024-01-01')
      }
    ],
    activeProfileId: 'primary',
    autoSwitch: {
      enabled: false,
      proactiveSwapEnabled: false,
      sessionThreshold: 95,
      weeklyThreshold: 99,
      autoSwitchOnRateLimit: false,
      usageCheckInterval: 30000
    }
  };

  beforeEach(async () => {
    vi.clearAllMocks();

    // Mock fs operations
    vi.mocked(existsSync).mockReturnValue(true);
    vi.mocked(readFileSync).mockReturnValue(JSON.stringify(mockProfileData));
    vi.mocked(writeFileSync).mockImplementation(() => {});
    vi.mocked(mkdirSync).mockImplementation(() => undefined);

    // Mock async profile loading
    vi.mocked(profileStorage.loadProfileStoreAsync).mockResolvedValue(mockProfileData);
    vi.mocked(profileStorage.loadProfileStore).mockReturnValue(mockProfileData);

    // Create and initialize manager
    manager = new ClaudeProfileManager();
    await manager.initialize();
  });

  describe('Initialization', () => {
    it('should initialize with default profile', () => {
      const settings = manager.getSettings();

      expect(settings.profiles).toHaveLength(1);
      expect(settings.profiles[0].name).toBe('Primary');
      expect(settings.profiles[0].isDefault).toBe(true);
      expect(settings.activeProfileId).toBe('primary');
    });

    it('should load existing profiles from disk', async () => {
      const customData = {
        ...mockProfileData,
        profiles: [
          ...mockProfileData.profiles,
          {
            id: 'work',
            name: 'Work Account',
            configDir: '/tmp/.claude-profiles/work',
            isDefault: false,
            createdAt: new Date('2024-01-02')
          }
        ]
      };

      vi.mocked(profileStorage.loadProfileStoreAsync).mockResolvedValue(customData);

      const newManager = new ClaudeProfileManager();
      await newManager.initialize();

      const settings = newManager.getSettings();
      expect(settings.profiles).toHaveLength(2);
      expect(settings.profiles[1].name).toBe('Work Account');
    });

    it('should create config directory if it does not exist', async () => {
      const { mkdir } = await import('fs/promises');
      await manager.initialize();

      expect(mkdir).toHaveBeenCalledWith(
        expect.stringContaining('config'),
        { recursive: true }
      );
    });

    it('should mark as initialized after setup', async () => {
      expect(manager.isInitialized()).toBe(true);
    });

    it('should not re-initialize if already initialized', async () => {
      await manager.initialize();
      await manager.initialize();

      const { mkdir } = await import('fs/promises');
      // Should only be called once from beforeEach initialization
      expect(mkdir).toHaveBeenCalledTimes(1);
    });
  });

  describe('Profile Management', () => {
    it('should get active profile', () => {
      const active = manager.getActiveProfile();

      expect(active.id).toBe('primary');
      expect(active.name).toBe('Primary');
    });

    it('should get specific profile by ID', () => {
      const profile = manager.getProfile('primary');

      expect(profile).toBeDefined();
      expect(profile?.name).toBe('Primary');
    });

    it('should return undefined for non-existent profile', () => {
      const profile = manager.getProfile('nonexistent');

      expect(profile).toBeUndefined();
    });

    it('should save new profile', () => {
      const newProfile: ClaudeProfile = {
        id: 'work',
        name: 'Work Account',
        configDir: '/tmp/.claude-profiles/work',
        isDefault: false,
        createdAt: new Date()
      };

      const saved = manager.saveProfile(newProfile);

      expect(saved.id).toBe('work');
      expect(profileStorage.saveProfileStore).toHaveBeenCalled();
    });

    it('should update existing profile', () => {
      const settings = manager.getSettings();
      const profile = { ...settings.profiles[0], name: 'Updated Name' };

      manager.saveProfile(profile);

      const updated = manager.getProfile('primary');
      expect(updated?.name).toBe('Updated Name');
    });

    it('should expand home path in configDir when saving', () => {
      const profile: ClaudeProfile = {
        id: 'test',
        name: 'Test',
        configDir: '~/.claude-test',
        isDefault: false,
        createdAt: new Date()
      };

      manager.saveProfile(profile);

      expect(profileUtils.expandHomePath).toHaveBeenCalledWith('~/.claude-test');
    });

    it('should set active profile', () => {
      const newProfile: ClaudeProfile = {
        id: 'work',
        name: 'Work',
        configDir: '/tmp/.claude-profiles/work',
        isDefault: false,
        createdAt: new Date()
      };

      manager.saveProfile(newProfile);
      const result = manager.setActiveProfile('work');

      expect(result).toBe(true);
      expect(manager.getActiveProfile().id).toBe('work');
    });

    it('should fail to set non-existent profile as active', () => {
      // Ensure no other profiles exist from previous tests
      const currentActive = manager.getActiveProfile().id;
      const result = manager.setActiveProfile('nonexistent');

      expect(result).toBe(false);
      expect(manager.getActiveProfile().id).toBe(currentActive);
    });

    it('should update lastUsedAt when setting active profile', () => {
      const before = new Date();
      manager.setActiveProfile('primary');
      const after = new Date();

      const profile = manager.getProfile('primary');
      expect(profile?.lastUsedAt).toBeDefined();
      expect(profile!.lastUsedAt!.getTime()).toBeGreaterThanOrEqual(before.getTime());
      expect(profile!.lastUsedAt!.getTime()).toBeLessThanOrEqual(after.getTime());
    });

    it('should mark profile as used', () => {
      manager.markProfileUsed('primary');

      const profile = manager.getProfile('primary');
      expect(profile?.lastUsedAt).toBeDefined();
    });

    it('should rename profile', () => {
      const result = manager.renameProfile('primary', 'New Name');

      expect(result).toBe(true);
      expect(manager.getProfile('primary')?.name).toBe('New Name');
    });

    it('should fail to rename with empty name', () => {
      const result = manager.renameProfile('primary', '   ');

      expect(result).toBe(false);
    });

    it('should delete non-default profile', () => {
      const newProfile: ClaudeProfile = {
        id: 'work',
        name: 'Work',
        configDir: '/tmp/.claude-profiles/work',
        isDefault: false,
        createdAt: new Date()
      };

      manager.saveProfile(newProfile);
      const result = manager.deleteProfile('work');

      expect(result).toBe(true);
      expect(manager.getProfile('work')).toBeUndefined();
    });

    it('should not delete default profile', () => {
      const result = manager.deleteProfile('primary');

      expect(result).toBe(false);
      expect(manager.getProfile('primary')).toBeDefined();
    });

    it('should switch to default when deleting active profile', () => {
      const work: ClaudeProfile = {
        id: 'work',
        name: 'Work',
        configDir: '/tmp/.claude-profiles/work',
        isDefault: false,
        createdAt: new Date()
      };

      manager.saveProfile(work);
      manager.setActiveProfile('work');
      manager.deleteProfile('work');

      expect(manager.getActiveProfile().id).toBe('primary');
    });
  });

  describe('Token Management', () => {
    it('should set OAuth token for profile (encrypted)', () => {
      const token = 'test-oauth-token';
      const result = manager.setProfileToken('primary', token, 'user@example.com');

      expect(result).toBe(true);
      expect(tokenEncryption.encryptToken).toHaveBeenCalledWith(token);
    });

    it('should get decrypted token for active profile', () => {
      manager.setProfileToken('primary', 'test-token');
      const token = manager.getActiveProfileToken();

      expect(token).toBe('test-token'); // Decrypted by mock
      expect(tokenEncryption.decryptToken).toHaveBeenCalled();
    });

    it('should get decrypted token for specific profile', () => {
      manager.setProfileToken('primary', 'test-token');
      const token = manager.getProfileToken('primary');

      expect(token).toBe('test-token');
    });

    it('should return undefined for profile without token', () => {
      // Get a fresh manager instance for this test
      const freshManager = new ClaudeProfileManager();
      vi.mocked(profileStorage.loadProfileStore).mockReturnValue({
        ...mockProfileData,
        profiles: [{ ...mockProfileData.profiles[0], oauthToken: undefined }]
      });

      // Re-initialize with fresh data (synchronous load for this test)
      const token = freshManager.getProfileToken('primary');

      expect(token).toBeUndefined();
    });

    it('should validate token age', () => {
      vi.mocked(profileUtils.hasValidToken).mockReturnValue(true);

      const result = manager.hasValidToken('primary');

      expect(result).toBe(true);
    });

    it('should update email when setting token', () => {
      manager.setProfileToken('primary', 'token', 'user@example.com');

      const profile = manager.getProfile('primary');
      expect(profile?.email).toBe('user@example.com');
    });

    it('should clear rate limit events when setting new token', () => {
      manager.setProfileToken('primary', 'new-token');

      const profile = manager.getProfile('primary');
      expect(profile?.rateLimitEvents).toEqual([]);
    });
  });

  describe('Usage Tracking', () => {
    it('should update usage from terminal output', () => {
      const usageOutput = 'Session: 50% | Weekly: 75%';
      const mockUsage: ClaudeUsageData = {
        sessionUsagePercent: 50,
        sessionResetTime: '2h',
        weeklyUsagePercent: 75,
        weeklyResetTime: '3d',
        lastUpdated: new Date()
      };

      vi.mocked(usageParser.parseUsageOutput).mockReturnValue(mockUsage);

      const result = manager.updateProfileUsage('primary', usageOutput);

      expect(result).toEqual(mockUsage);
      expect(usageParser.parseUsageOutput).toHaveBeenCalledWith(usageOutput);
    });

    it('should update usage from API percentages', () => {
      const result = manager.updateProfileUsageFromAPI('primary', 60, 80);

      expect(result).toBeDefined();
      expect(result?.sessionUsagePercent).toBe(60);
      expect(result?.weeklyUsagePercent).toBe(80);
    });

    it('should batch update usage for multiple profiles', () => {
      const work: ClaudeProfile = {
        id: 'work',
        name: 'Work',
        configDir: '/tmp/.claude-profiles/work',
        isDefault: false,
        createdAt: new Date()
      };

      manager.saveProfile(work);

      const updates = [
        { profileId: 'primary', sessionPercent: 50, weeklyPercent: 70 },
        { profileId: 'work', sessionPercent: 30, weeklyPercent: 40 }
      ];

      const count = manager.batchUpdateProfileUsageFromAPI(updates);

      expect(count).toBe(2);
      expect(manager.getProfile('primary')?.usage?.sessionUsagePercent).toBe(50);
      expect(manager.getProfile('work')?.usage?.sessionUsagePercent).toBe(30);
    });

    it('should skip invalid profiles in batch update', () => {
      const updates = [
        { profileId: 'primary', sessionPercent: 50, weeklyPercent: 70 },
        { profileId: 'invalid', sessionPercent: 30, weeklyPercent: 40 }
      ];

      const count = manager.batchUpdateProfileUsageFromAPI(updates);

      expect(count).toBe(1);
    });

    it('should preserve existing reset times in API update', () => {
      const existing: ClaudeUsageData = {
        sessionUsagePercent: 40,
        sessionResetTime: '2h',
        weeklyUsagePercent: 60,
        weeklyResetTime: '3d',
        lastUpdated: new Date()
      };

      manager.getProfile('primary')!.usage = existing;

      manager.updateProfileUsageFromAPI('primary', 50, 70);

      const profile = manager.getProfile('primary');
      expect(profile?.usage?.sessionResetTime).toBe('2h');
      expect(profile?.usage?.weeklyResetTime).toBe('3d');
    });
  });

  describe('Rate Limiting', () => {
    it('should record rate limit event', () => {
      const mockEvent = {
        hitAt: new Date(),
        resetAt: new Date(Date.now() + 3600000),
        resetTimeString: 'in 1 hour',
        type: 'session' as const
      };

      vi.mocked(rateLimitManager.recordRateLimitEvent).mockReturnValue(mockEvent);

      const event = manager.recordRateLimitEvent('primary', '1h');

      expect(event).toEqual(mockEvent);
      expect(rateLimitManager.recordRateLimitEvent).toHaveBeenCalled();
    });

    it('should check if profile is rate limited', () => {
      vi.mocked(rateLimitManager.isProfileRateLimited).mockReturnValue({
        limited: true,
        type: 'session',
        resetAt: new Date()
      });

      const result = manager.isProfileRateLimited('primary');

      expect(result.limited).toBe(true);
      expect(result.type).toBe('session');
    });

    it('should clear rate limit events', () => {
      manager.clearRateLimitEvents('primary');

      expect(rateLimitManager.clearRateLimitEvents).toHaveBeenCalled();
    });
  });

  describe('Auto-Switch Settings', () => {
    it('should get auto-switch settings', () => {
      const settings = manager.getAutoSwitchSettings();

      expect(settings.enabled).toBe(false);
      expect(settings.sessionThreshold).toBe(95);
      expect(settings.weeklyThreshold).toBe(99);
    });

    it('should update auto-switch settings', () => {
      manager.updateAutoSwitchSettings({
        enabled: true,
        sessionThreshold: 90
      });

      const settings = manager.getAutoSwitchSettings();
      expect(settings.enabled).toBe(true);
      expect(settings.sessionThreshold).toBe(90);
      expect(settings.weeklyThreshold).toBe(99); // Preserved
    });

    it('should get best available profile', () => {
      const mockBestProfile: ClaudeProfile = {
        id: 'work',
        name: 'Work',
        configDir: '/tmp/.claude-profiles/work',
        isDefault: false,
        createdAt: new Date()
      };

      vi.mocked(profileScorer.getBestAvailableProfile).mockReturnValue(mockBestProfile);

      const result = manager.getBestAvailableProfile('primary');

      expect(result).toEqual(mockBestProfile);
    });

    it('should determine if should proactively switch', () => {
      vi.mocked(profileScorer.shouldProactivelySwitch).mockReturnValue({
        shouldSwitch: true,
        reason: 'High usage',
        suggestedProfile: {
          id: 'work',
          name: 'Work',
          configDir: '/tmp/.claude-profiles/work',
          isDefault: false,
          createdAt: new Date()
        }
      });

      const result = manager.shouldProactivelySwitch('primary');

      expect(result.shouldSwitch).toBe(true);
      expect(result.reason).toBe('High usage');
    });

    it('should get profiles sorted by availability', () => {
      const sorted = manager.getProfilesSortedByAvailability();

      expect(profileScorer.getProfilesSortedByAvailability).toHaveBeenCalled();
      expect(sorted).toBeInstanceOf(Array);
    });
  });

  describe('Account Priority Order', () => {
    it('should get account priority order', () => {
      const order = manager.getAccountPriorityOrder();

      expect(order).toBeInstanceOf(Array);
    });

    it('should set account priority order', () => {
      const order = ['oauth-primary', 'oauth-work', 'api-backup'];

      manager.setAccountPriorityOrder(order);

      expect(manager.getAccountPriorityOrder()).toEqual(order);
    });
  });

  describe('Environment Variables', () => {
    it('should get environment for active profile', () => {
      const env = manager.getActiveProfileEnv();

      expect(env.CLAUDE_CONFIG_DIR).toBeDefined();
      expect(env.CLAUDE_CONFIG_DIR).toContain('primary');
    });

    it('should get environment for specific profile', () => {
      const env = manager.getProfileEnv('primary');

      expect(env.CLAUDE_CONFIG_DIR).toBeDefined();
    });

    it('should expand home directory in config path', () => {
      const profile: ClaudeProfile = {
        id: 'test',
        name: 'Test',
        configDir: '~/.claude-test',
        isDefault: false,
        createdAt: new Date()
      };

      manager.saveProfile(profile);
      const env = manager.getProfileEnv('test');

      expect(env.CLAUDE_CONFIG_DIR).not.toContain('~');
    });

    it('should retrieve OAuth token from Keychain', () => {
      vi.mocked(credentialUtils.getCredentialsFromKeychain).mockReturnValue({
        token: 'keychain-token',
        email: 'test@example.com'
      });

      const env = manager.getProfileEnv('primary');

      expect(env.CLAUDE_CODE_OAUTH_TOKEN).toBe('keychain-token');
    });

    it('should continue without token if Keychain retrieval fails', () => {
      vi.mocked(credentialUtils.getCredentialsFromKeychain).mockImplementation(() => {
        throw new Error('Keychain error');
      });

      const env = manager.getProfileEnv('primary');

      expect(env.CLAUDE_CONFIG_DIR).toBeDefined();
      expect(env.CLAUDE_CODE_OAUTH_TOKEN).toBeUndefined();
    });
  });

  describe('Profile Utilities', () => {
    it('should generate unique profile ID', () => {
      const id = manager.generateProfileId('Work Account');

      expect(profileUtils.generateProfileId).toHaveBeenCalledWith(
        'Work Account',
        expect.any(Array)
      );
      expect(id).toBe('work-account');
    });

    it('should create profile directory', async () => {
      const dir = await manager.createProfileDirectory('Work');

      expect(profileUtils.createProfileDirectory).toHaveBeenCalledWith('Work');
      expect(dir).toContain('work');
    });

    it('should check if profile is authenticated', () => {
      vi.mocked(profileUtils.isProfileAuthenticated).mockReturnValue(true);

      const result = manager.isProfileAuthenticated(manager.getActiveProfile());

      expect(result).toBe(true);
    });

    it('should check if profile has valid auth', () => {
      vi.mocked(profileUtils.hasValidToken).mockReturnValue(true);

      const result = manager.hasValidAuth('primary');

      expect(result).toBe(true);
    });

    it('should check configDir auth if no valid token', () => {
      vi.mocked(profileUtils.hasValidToken).mockReturnValue(false);
      vi.mocked(profileUtils.isProfileAuthenticated).mockReturnValue(true);

      const result = manager.hasValidAuth('primary');

      expect(result).toBe(true);
    });
  });

  describe('Profile Migration', () => {
    it('should get migrated profile IDs', () => {
      const ids = manager.getMigratedProfileIds();

      expect(ids).toBeInstanceOf(Array);
    });

    it('should clear migrated profile after re-authentication', async () => {
      // Set up manager with migrated profile - must mock async loader
      vi.mocked(profileStorage.loadProfileStoreAsync).mockResolvedValue({
        ...mockProfileData,
        migratedProfileIds: ['primary']
      });

      // Create new manager and initialize to load data
      const mgr = new ClaudeProfileManager();
      await mgr.initialize();

      // Clear only the call history, not the mock implementations
      vi.mocked(profileStorage.saveProfileStore).mockClear();

      mgr.clearMigratedProfile('primary');

      expect(profileStorage.saveProfileStore).toHaveBeenCalled();
    });

    it('should check if profile is migrated', () => {
      const result = manager.isProfileMigrated('primary');

      expect(typeof result).toBe('boolean');
    });
  });

  describe('Settings Integration', () => {
    it('should include authentication status in settings', () => {
      vi.mocked(profileUtils.isProfileAuthenticated).mockReturnValue(true);
      vi.mocked(profileUtils.hasValidToken).mockReturnValue(false);

      const settings = manager.getSettings();

      expect(settings.profiles[0].isAuthenticated).toBe(true);
    });

    it('should combine token and configDir auth status', () => {
      vi.mocked(profileUtils.isProfileAuthenticated).mockReturnValue(false);
      vi.mocked(profileUtils.hasValidToken).mockReturnValue(true);

      const settings = manager.getSettings();

      expect(settings.profiles[0].isAuthenticated).toBe(true);
    });
  });

  describe('Singleton Pattern', () => {
    it('should return same instance from getClaudeProfileManager', () => {
      const instance1 = getClaudeProfileManager();
      const instance2 = getClaudeProfileManager();

      expect(instance1).toBe(instance2);
    });

    it('should initialize singleton async', async () => {
      const instance = await initializeClaudeProfileManager();

      expect(instance).toBeDefined();
      expect(instance.isInitialized()).toBe(true);
    });

    it('should cache initialization promise', async () => {
      // Note: The singleton manager is already initialized from beforeEach
      // This test verifies subsequent calls return the same instance
      const instance1 = await initializeClaudeProfileManager();
      const instance2 = await initializeClaudeProfileManager();

      expect(instance1).toBe(instance2);
      expect(instance1.isInitialized()).toBe(true);
    });
  });

  describe('Error Handling', () => {
    it('should handle missing profile in token operations', () => {
      const result = manager.setProfileToken('nonexistent', 'token');

      expect(result).toBe(false);
    });

    it('should handle missing profile in usage update', () => {
      const result = manager.updateProfileUsage('nonexistent', 'output');

      expect(result).toBeNull();
    });

    it('should throw error when recording rate limit for missing profile', () => {
      expect(() => {
        manager.recordRateLimitEvent('nonexistent', '1h');
      }).toThrow('Profile not found');
    });

    it('should return false for rate limit check on missing profile', () => {
      const result = manager.isProfileRateLimited('nonexistent');

      expect(result.limited).toBe(false);
    });
  });
});
