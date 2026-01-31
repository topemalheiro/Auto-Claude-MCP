/**
 * Tests for CLI Tool Manager
 * Comprehensive test coverage for tool detection, validation, and caching
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { execFileSync, execFile } from 'child_process';
import { existsSync, readdirSync, promises as fsPromises } from 'fs';
import path from 'path';
import os from 'os';
import { app } from 'electron';

// Mock dependencies before importing the module under test
vi.mock('child_process');
vi.mock('fs');
vi.mock('fs', async () => {
  const actual = await vi.importActual<typeof import('fs')>('fs');
  return {
    ...actual,
    existsSync: vi.fn(),
    readdirSync: vi.fn(),
    promises: {
      ...actual.promises,
      readdir: vi.fn()
    }
  };
});
vi.mock('electron', () => ({
  app: {
    getPath: vi.fn(),
    isPackaged: false
  }
}));

// Mock platform module
vi.mock('../platform', () => ({
  isWindows: vi.fn(() => false),
  isMacOS: vi.fn(() => false),
  isLinux: vi.fn(() => true),
  isUnix: vi.fn(() => true),
  joinPaths: vi.fn((...parts: string[]) => path.join(...parts)),
  getExecutableExtension: vi.fn(() => '')
}));

// Mock env-utils module
vi.mock('../env-utils', () => ({
  findExecutable: vi.fn(),
  findExecutableAsync: vi.fn(),
  getAugmentedEnv: vi.fn(() => ({})),
  getAugmentedEnvAsync: vi.fn(() => Promise.resolve({})),
  shouldUseShell: vi.fn(() => false),
  existsAsync: vi.fn()
}));

// Mock windows-paths module
vi.mock('../utils/windows-paths', () => ({
  getWindowsExecutablePaths: vi.fn(() => []),
  getWindowsExecutablePathsAsync: vi.fn(() => Promise.resolve([])),
  WINDOWS_GIT_PATHS: [],
  WINDOWS_GLAB_PATHS: [],
  findWindowsExecutableViaWhere: vi.fn(),
  findWindowsExecutableViaWhereAsync: vi.fn(),
  isSecurePath: vi.fn(() => true)
}));

// Mock homebrew-python utility
vi.mock('../utils/homebrew-python', () => ({
  findHomebrewPython: vi.fn()
}));

// Import after mocks are set up
import {
  getToolPath,
  getToolPathAsync,
  configureTools,
  getToolInfo,
  clearToolCache,
  getClaudeCliPathForSdk,
  getClaudeCliPathForSdkAsync,
  isPathFromWrongPlatform,
  getClaudeDetectionPaths,
  sortNvmVersionDirs,
  buildClaudeDetectionResult,
  preWarmToolCache,
  type ToolConfig
} from '../cli-tool-manager';

import * as platform from '../platform';
import * as envUtils from '../env-utils';
import * as windowsPaths from '../utils/windows-paths';
import * as homebrewPython from '../utils/homebrew-python';

describe('CLI Tool Manager', () => {
  beforeEach(() => {
    // Clear cache and config first, before resetting mocks
    clearToolCache();

    // CRITICAL: Reset user configuration to prevent state leakage between tests
    // The singleton cliToolManager persists config across tests
    configureTools({});

    // Now clear all mocks
    vi.clearAllMocks();

    // Reset platform mocks to default (Linux)
    vi.mocked(platform.isWindows).mockReturnValue(false);
    vi.mocked(platform.isMacOS).mockReturnValue(false);
    vi.mocked(platform.isLinux).mockReturnValue(true);
    vi.mocked(platform.isUnix).mockReturnValue(true);
    vi.mocked(platform.getExecutableExtension).mockReturnValue('');

    // Reset fs mocks
    vi.mocked(existsSync).mockReturnValue(false);
    vi.mocked(readdirSync).mockReturnValue([]);

    // Reset env utils mocks
    vi.mocked(envUtils.findExecutable).mockReturnValue(null);
    vi.mocked(envUtils.findExecutableAsync).mockResolvedValue(null);
    vi.mocked(envUtils.existsAsync).mockResolvedValue(false);

    // Reset windows paths mocks
    vi.mocked(windowsPaths.findWindowsExecutableViaWhere).mockReturnValue(null);
    vi.mocked(windowsPaths.findWindowsExecutableViaWhereAsync).mockResolvedValue(null);

    // Reset homebrew python mock
    vi.mocked(homebrewPython.findHomebrewPython).mockReturnValue(null);
  });

  describe('Python Detection', () => {
    it('should detect Python from user configuration', () => {
      clearToolCache();
      const pythonPath = '/custom/python3';
      vi.mocked(execFileSync).mockReturnValue('Python 3.11.0\n' as any);

      configureTools({ pythonPath });
      const result = getToolPath('python');

      expect(result).toBe(pythonPath);
      expect(execFileSync).toHaveBeenCalledWith(
        pythonPath,
        ['--version'],
        expect.objectContaining({ encoding: 'utf-8' })
      );
    });

    it('should validate Python minimum version (3.10.0)', () => {
      vi.mocked(execFileSync).mockReturnValue('Python 3.9.0\n' as any);

      const result = getToolInfo('python');

      expect(result.found).toBe(false);
      expect(result.message).toContain('3.10.0+');
    });

    it('should accept Python 3.10 and higher', () => {
      vi.mocked(execFileSync).mockReturnValue('Python 3.10.0\n' as any);
      vi.mocked(envUtils.findExecutable).mockReturnValue('/usr/bin/python3');

      const result = getToolPath('python');

      expect(result).toBe('/usr/bin/python3');
    });

    it('should detect Homebrew Python on macOS', () => {
      vi.mocked(platform.isMacOS).mockReturnValue(true);
      vi.mocked(platform.isUnix).mockReturnValue(true);
      vi.mocked(homebrewPython.findHomebrewPython).mockReturnValue('/opt/homebrew/bin/python3');

      const result = getToolPath('python');

      expect(result).toBe('/opt/homebrew/bin/python3');
    });

    it('should handle Windows Python launcher (py -3)', () => {
      vi.mocked(platform.isWindows).mockReturnValue(true);
      vi.mocked(platform.isUnix).mockReturnValue(false);
      vi.mocked(execFileSync).mockReturnValue('Python 3.11.0\n' as any);

      const result = getToolPath('python');

      // Should try 'py -3' first on Windows
      expect(execFileSync).toHaveBeenCalledWith(
        'py',
        ['-3', '--version'],
        expect.any(Object)
      );
    });

    it('should fallback to "python" when not found', () => {
      vi.mocked(execFileSync).mockImplementation(() => {
        throw new Error('Command not found');
      });
      vi.mocked(envUtils.findExecutable).mockReturnValue(null);

      const result = getToolPath('python');

      expect(result).toBe('python');
    });

    it('should reject wrong platform paths', () => {
      const windowsPath = 'C:\\Python\\python.exe';
      configureTools({ pythonPath: windowsPath });

      const result = getToolPath('python');

      // Should ignore Windows path on Unix
      expect(result).not.toBe(windowsPath);
    });
  });

  describe('Git Detection', () => {
    it('should detect Git from user configuration', () => {
      const gitPath = '/custom/git';
      vi.mocked(execFileSync).mockReturnValue('git version 2.40.0\n' as any);

      configureTools({ gitPath });
      const result = getToolPath('git');

      expect(result).toBe(gitPath);
    });

    it('should detect Homebrew Git on macOS', () => {
      vi.mocked(platform.isMacOS).mockReturnValue(true);
      vi.mocked(platform.isUnix).mockReturnValue(true);
      vi.mocked(existsSync).mockReturnValue(true);
      vi.mocked(execFileSync).mockReturnValue('git version 2.40.0\n' as any);

      const result = getToolPath('git');

      // Should check homebrew paths on macOS
      expect(result).toMatch(/homebrew.*git/);
    });

    it('should detect Git from system PATH', () => {
      vi.mocked(envUtils.findExecutable).mockReturnValue('/usr/bin/git');
      vi.mocked(execFileSync).mockReturnValue('git version 2.40.0\n' as any);

      const result = getToolPath('git');

      expect(result).toBe('/usr/bin/git');
    });

    it('should use Windows where command for Git detection', () => {
      vi.mocked(platform.isWindows).mockReturnValue(true);
      vi.mocked(platform.isUnix).mockReturnValue(false);
      vi.mocked(windowsPaths.findWindowsExecutableViaWhere).mockReturnValue('C:\\Program Files\\Git\\cmd\\git.exe');
      vi.mocked(execFileSync).mockReturnValue('git version 2.40.0\n' as any);

      const result = getToolPath('git');

      expect(windowsPaths.findWindowsExecutableViaWhere).toHaveBeenCalledWith('git', '[Git]');
      expect(result).toBe('C:\\Program Files\\Git\\cmd\\git.exe');
    });

    it('should extract version from git output', () => {
      vi.mocked(execFileSync).mockReturnValue('git version 2.40.1\n' as any);
      vi.mocked(envUtils.findExecutable).mockReturnValue('/usr/bin/git');

      const result = getToolInfo('git');

      expect(result.version).toBe('2.40.1');
    });
  });

  describe('GitHub CLI Detection', () => {
    it('should detect gh from user configuration', () => {
      const ghPath = '/custom/gh';
      vi.mocked(execFileSync).mockReturnValue('gh version 2.30.0\n' as any);

      configureTools({ githubCLIPath: ghPath });
      const result = getToolPath('gh');

      expect(result).toBe(ghPath);
    });

    it('should detect Homebrew gh on macOS', () => {
      vi.mocked(platform.isMacOS).mockReturnValue(true);
      vi.mocked(platform.isUnix).mockReturnValue(true);
      vi.mocked(existsSync).mockReturnValue(true);
      vi.mocked(execFileSync).mockReturnValue('gh version 2.30.0\n' as any);

      const result = getToolPath('gh');

      // Should check homebrew paths on macOS
      expect(result).toMatch(/homebrew.*gh/);
    });

    it('should check Windows Program Files for gh', () => {
      vi.mocked(platform.isWindows).mockReturnValue(true);
      vi.mocked(platform.isUnix).mockReturnValue(false);
      vi.mocked(existsSync).mockReturnValue(true);
      vi.mocked(execFileSync).mockReturnValue('gh version 2.30.0\n' as any);

      const result = getToolPath('gh');

      // Should check Windows Program Files paths
      expect(existsSync).toHaveBeenCalledWith(expect.stringContaining('Program Files'));
    });

    it('should return not found when gh is missing', () => {
      // All detection methods fail
      vi.mocked(envUtils.findExecutable).mockReturnValue(null);
      vi.mocked(existsSync).mockReturnValue(false);
      vi.mocked(execFileSync).mockImplementation(() => {
        throw new Error('Command not found');
      });

      const result = getToolInfo('gh');

      expect(result.found).toBe(false);
      expect(result.message).toContain('cli.github.com');
    });
  });

  describe('Claude CLI Detection', () => {
    it('should detect Claude from user configuration', () => {
      const claudePath = '/custom/claude';
      vi.mocked(execFileSync).mockReturnValue('1.5.0\n' as any);

      configureTools({ claudePath });
      const result = getToolPath('claude');

      expect(result).toBe(claudePath);
    });

    it('should detect Homebrew Claude on macOS', () => {
      vi.mocked(platform.isMacOS).mockReturnValue(true);
      vi.mocked(platform.isUnix).mockReturnValue(true);
      vi.mocked(existsSync).mockReturnValue(true);
      vi.mocked(execFileSync).mockReturnValue('1.5.0\n' as any);

      const result = getToolPath('claude');

      // Should check homebrew paths on macOS
      expect(result).toMatch(/homebrew.*claude/);
    });

    it('should check NVM paths for Claude on Unix', () => {
      vi.mocked(platform.isUnix).mockReturnValue(true);
      const nvmDir = path.join(os.homedir(), '.nvm/versions/node');
      const claudePath = path.join(nvmDir, 'v20.0.0', 'bin', 'claude');

      // Mock NVM directory exists with version subdirectories
      vi.mocked(existsSync).mockImplementation((p) => {
        return p === nvmDir || p === claudePath;
      });
      vi.mocked(readdirSync).mockReturnValue([
        { name: 'v20.0.0', isDirectory: () => true },
        { name: 'v18.0.0', isDirectory: () => true }
      ] as any);
      vi.mocked(execFileSync).mockReturnValue('1.5.0\n' as any);

      const result = getToolPath('claude');

      // Should check NVM paths and find Claude
      expect(result).toBe(claudePath);
    });

    it('should return null for .cmd files on Windows (SDK compatibility)', () => {
      vi.mocked(platform.isWindows).mockReturnValue(true);
      vi.mocked(envUtils.findExecutable).mockReturnValue('C:\\Users\\test\\AppData\\Roaming\\npm\\claude.cmd');

      const result = getClaudeCliPathForSdk();

      expect(result).toBeNull();
    });

    it('should return path for .exe files on Windows', () => {
      vi.mocked(platform.isWindows).mockReturnValue(true);
      const exePath = 'C:\\Program Files\\Claude\\claude.exe';
      vi.mocked(execFileSync).mockReturnValue('1.5.0\n' as any);
      vi.mocked(envUtils.findExecutable).mockReturnValue(exePath);

      const result = getClaudeCliPathForSdk();

      expect(result).toBe(exePath);
    });

    it('should validate Claude CLI path security on Windows', () => {
      clearToolCache();
      vi.mocked(platform.isWindows).mockReturnValue(true);
      vi.mocked(platform.isUnix).mockReturnValue(false);
      vi.mocked(windowsPaths.isSecurePath).mockReturnValue(false);

      configureTools({ claudePath: 'C:\\malicious\\claude.exe' });
      const result = getToolInfo('claude');

      // Should ignore insecure path
      expect(result.found).toBe(false);
    });
  });

  describe('Caching', () => {
    it('should cache tool paths after first detection', () => {
      vi.mocked(envUtils.findExecutable).mockReturnValue('/usr/bin/git');
      vi.mocked(execFileSync).mockReturnValue('git version 2.40.0\n' as any);

      getToolPath('git');
      getToolPath('git');

      // Should only validate once (cached on second call)
      expect(execFileSync).toHaveBeenCalledTimes(1);
    });

    it('should clear cache when configuration changes', () => {
      vi.mocked(execFileSync).mockReturnValue('git version 2.40.0\n' as any);
      vi.mocked(envUtils.findExecutable).mockReturnValue('/usr/bin/git');

      getToolPath('git');
      configureTools({ gitPath: '/custom/git' });
      getToolPath('git');

      // Should validate twice (cache cleared on configure)
      expect(execFileSync).toHaveBeenCalledTimes(2);
    });

    it('should manually clear cache', () => {
      vi.mocked(execFileSync).mockReturnValue('git version 2.40.0\n' as any);
      vi.mocked(envUtils.findExecutable).mockReturnValue('/usr/bin/git');

      getToolPath('git');
      clearToolCache();
      getToolPath('git');

      expect(execFileSync).toHaveBeenCalledTimes(2);
    });
  });

  describe('Async Methods', () => {
    // Note: Direct async detection (without cache) is difficult to test due to promisify() interaction with mocks.
    // The sync version is tested in "should detect Git from system PATH" and async caching is tested below.
    it('should detect tools asynchronously with cache', async () => {
      vi.mocked(envUtils.findExecutable).mockReturnValue('/usr/bin/git');
      vi.mocked(execFileSync).mockReturnValue('git version 2.40.0\n' as any);

      // Populate cache using sync method
      const syncResult = getToolPath('git');

      // Async should use the cached value
      const asyncResult = await getToolPathAsync('git');

      expect(syncResult).toBe('/usr/bin/git');
      expect(asyncResult).toBe('/usr/bin/git');
    });

    it('should use cached values for async calls', async () => {
      vi.mocked(envUtils.findExecutable).mockReturnValue('/usr/bin/git');
      vi.mocked(execFileSync).mockReturnValue('git version 2.40.0\n' as any);

      const syncResult = getToolPath('git'); // Populate cache synchronously
      const asyncResult = await getToolPathAsync('git');

      expect(syncResult).toBe('/usr/bin/git');
      expect(asyncResult).toBe('/usr/bin/git');
      expect(execFile).not.toHaveBeenCalled(); // Should use cache for async call
    });

    it('should pre-warm tool cache asynchronously', async () => {
      vi.mocked(envUtils.findExecutableAsync).mockResolvedValue('/usr/bin/claude');
      vi.mocked(execFile).mockImplementation((cmd, args, opts, callback: any) => {
        callback(null, { stdout: '1.5.0\n', stderr: '' });
        return {} as any;
      });

      await preWarmToolCache(['claude', 'git']);

      expect(envUtils.findExecutableAsync).toHaveBeenCalledWith('claude');
      expect(envUtils.findExecutableAsync).toHaveBeenCalledWith('git');
    });
  });

  describe('Platform Path Validation', () => {
    it('should detect Windows paths on Unix', () => {
      expect(isPathFromWrongPlatform('C:\\Program Files\\tool.exe')).toBe(true);
      expect(isPathFromWrongPlatform('D:\\Users\\test')).toBe(true);
    });

    it('should detect Unix paths on Windows', () => {
      vi.mocked(platform.isWindows).mockReturnValue(true);

      expect(isPathFromWrongPlatform('/usr/local/bin/tool')).toBe(true);
    });

    it('should accept correct platform paths', () => {
      expect(isPathFromWrongPlatform('/usr/bin/python3')).toBe(false);
      expect(isPathFromWrongPlatform('python3')).toBe(false);
    });
  });

  describe('Helper Functions', () => {
    describe('getClaudeDetectionPaths', () => {
      it('should return platform-specific paths', () => {
        const homeDir = '/home/user';
        const paths = getClaudeDetectionPaths(homeDir);

        expect(paths.homebrewPaths).toContain('/opt/homebrew/bin/claude');
        expect(paths.homebrewPaths).toContain('/usr/local/bin/claude');
        expect(paths.platformPaths.length).toBeGreaterThan(0);
        expect(paths.nvmVersionsDir).toBe(path.join(homeDir, '.nvm/versions/node'));
      });

      it('should include Windows-specific paths on Windows', () => {
        vi.mocked(platform.isWindows).mockReturnValue(true);
        vi.mocked(platform.getExecutableExtension).mockReturnValue('.exe');
        const homeDir = 'C:\\Users\\test';

        const paths = getClaudeDetectionPaths(homeDir);

        expect(paths.platformPaths.some(p => p.includes('AppData'))).toBe(true);
      });
    });

    describe('sortNvmVersionDirs', () => {
      it('should sort version directories newest first', () => {
        const entries = [
          { name: 'v18.0.0', isDirectory: () => true },
          { name: 'v20.5.0', isDirectory: () => true },
          { name: 'v19.2.1', isDirectory: () => true }
        ];

        const sorted = sortNvmVersionDirs(entries);

        expect(sorted).toEqual(['v20.5.0', 'v19.2.1', 'v18.0.0']);
      });

      it('should filter out non-directory entries', () => {
        const entries = [
          { name: 'v20.0.0', isDirectory: () => true },
          { name: '.DS_Store', isDirectory: () => false },
          { name: 'README.md', isDirectory: () => false }
        ];

        const sorted = sortNvmVersionDirs(entries);

        expect(sorted).toEqual(['v20.0.0']);
      });

      it('should filter out invalid semver directories', () => {
        const entries = [
          { name: 'v20.0.0', isDirectory: () => true },
          { name: 'v20.abc.1', isDirectory: () => true },
          { name: 'latest', isDirectory: () => true }
        ];

        const sorted = sortNvmVersionDirs(entries);

        expect(sorted).toEqual(['v20.0.0']);
      });
    });

    describe('buildClaudeDetectionResult', () => {
      it('should build successful detection result', () => {
        const validation = { valid: true, version: '1.5.0', message: 'OK' };
        const result = buildClaudeDetectionResult(
          '/usr/bin/claude',
          validation,
          'system-path',
          'Using system Claude CLI'
        );

        expect(result).toEqual({
          found: true,
          path: '/usr/bin/claude',
          version: '1.5.0',
          source: 'system-path',
          message: 'Using system Claude CLI: /usr/bin/claude'
        });
      });

      it('should return null for failed validation', () => {
        const validation = { valid: false, message: 'Not found' };
        const result = buildClaudeDetectionResult(
          '/usr/bin/claude',
          validation,
          'system-path',
          'Using system Claude CLI'
        );

        expect(result).toBeNull();
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle validation errors gracefully', () => {
      vi.mocked(execFileSync).mockImplementation(() => {
        throw new Error('Command failed');
      });

      const result = getToolInfo('git');

      expect(result.found).toBe(false);
    });

    it('should handle timeout errors', () => {
      vi.mocked(execFileSync).mockImplementation(() => {
        throw new Error('Timeout exceeded');
      });

      const result = getToolInfo('python');

      expect(result.found).toBe(false);
    });

    it('should handle malformed version output', () => {
      // Mock Python found but with invalid version output
      vi.mocked(execFileSync).mockReturnValue('Invalid output\n' as any);
      vi.mocked(envUtils.findExecutable).mockReturnValue(null);

      const result = getToolInfo('python');

      // Should fail to detect since all methods return invalid version
      expect(result.found).toBe(false);
      expect(result.message).toContain('3.10.0+');
    });
  });

  describe('Configuration', () => {
    beforeEach(() => {
      clearToolCache();
    });

    it('should update multiple tools at once', () => {
      const config: ToolConfig = {
        pythonPath: '/custom/python',
        gitPath: '/custom/git',
        githubCLIPath: '/custom/gh'
      };

      vi.mocked(execFileSync).mockImplementation((cmd: string) => {
        if (cmd.includes('python')) return 'Python 3.11.0\n' as any;
        if (cmd.includes('git')) return 'git version 2.40.0\n' as any;
        if (cmd.includes('gh')) return 'gh version 2.30.0\n' as any;
        throw new Error('Unknown command');
      });

      configureTools(config);

      expect(getToolPath('python')).toBe('/custom/python');
      expect(getToolPath('git')).toBe('/custom/git');
      expect(getToolPath('gh')).toBe('/custom/gh');
    });

    it('should preserve configuration across tool accesses', () => {
      clearToolCache();
      vi.mocked(execFileSync).mockReturnValue('git version 2.40.0\n' as any);

      configureTools({ gitPath: '/custom/git' });
      getToolPath('git');
      clearToolCache();

      // Configuration is preserved even when cache is cleared
      const result = getToolPath('git');
      expect(result).toBe('/custom/git');
    });
  });
});
