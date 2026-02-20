/**
 * Auto-Claude Watchdog - External process monitor for crash detection and recovery
 *
 * This watchdog monitors the main Electron process and automatically restarts it
 * when crashes are detected. It runs as a separate Node.js process to ensure it
 * survives crashes in the main application.
 *
 * Features:
 * - Detects abnormal process exits (crashes, segfaults, unhandled exceptions)
 * - Sends crash notifications to Claude Code via MCP (if enabled in settings)
 * - Auto-restarts Auto-Claude after crashes (if enabled in settings)
 * - Crash loop protection (max 3 restarts within 60 seconds)
 * - Monitors stdout/stderr for crash indicators
 */

import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import * as path from 'path';
import * as fs from 'fs';

// Must match the "name" field in package.json so watchdog writes to the same
// directory that Electron's app.getPath('userData') resolves to.
const APP_DATA_DIR_NAME = 'auto-claude-ui';

interface CrashInfo {
  timestamp: number;
  exitCode: number | null;
  signal: NodeJS.Signals | null;
  logs: string[];
  freezeDetected?: boolean;
  freezeType?: string;
}

interface WatchdogSettings {
  enabled: boolean;
  autoRestart: boolean;
  maxRestarts: number;
  restartCooldown: number;
}

export class AutoClaudeWatchdog extends EventEmitter {
  private process: ChildProcess | null = null;
  private crashTimestamps: number[] = [];
  private restartCount = 0;
  private isShuttingDown = false;
  private recentLogs: string[] = [];
  private readonly maxLogLines = 100;
  private settings: WatchdogSettings;
  private settingsPath: string;
  // Heartbeat monitoring for freeze detection (Layer 2)
  private heartbeatCheckInterval: ReturnType<typeof setInterval> | null = null;
  private readonly HEARTBEAT_CHECK_INTERVAL_MS = 15_000;  // Check every 15s
  private readonly HEARTBEAT_STALE_THRESHOLD_MS = 45_000; // Stale after 45s
  // When true, handleProcessExit uses the stored freeze crashInfo instead of a generic one
  private freezeTriggered = false;
  private freezeCrashInfo: CrashInfo | null = null;

  constructor() {
    super();

    // Load settings from app data directory
    const appDataPath = process.env.APPDATA ||
                        (process.platform === 'darwin' ? path.join(process.env.HOME!, 'Library', 'Application Support') :
                         path.join(process.env.HOME!, '.config'));
    const settingsDir = path.join(appDataPath, APP_DATA_DIR_NAME);
    this.settingsPath = path.join(settingsDir, 'settings.json');

    // Load crash recovery settings
    this.settings = this.loadSettings();
  }

  /**
   * Load crash recovery settings from disk
   */
  private loadSettings(): WatchdogSettings {
    try {
      if (fs.existsSync(this.settingsPath)) {
        const content = fs.readFileSync(this.settingsPath, 'utf-8');
        const appSettings = JSON.parse(content);

        // Extract crash recovery settings (enabled by default)
        if (appSettings.crashRecovery) {
          return {
            enabled: appSettings.crashRecovery.enabled ?? true,
            autoRestart: appSettings.crashRecovery.autoRestart ?? true,
            maxRestarts: appSettings.crashRecovery.maxRestarts ?? 3,
            restartCooldown: appSettings.crashRecovery.restartCooldown ?? 60000
          };
        }
      }
    } catch (error) {
      console.error('[Watchdog] Failed to load settings:', error);
    }

    // Default: crash recovery ENABLED (users can disable in settings)
    return {
      enabled: true,
      autoRestart: true,
      maxRestarts: 3,
      restartCooldown: 60000
    };
  }

  /**
   * Reload settings from disk (called when settings change)
   */
  public reloadSettings(): void {
    this.settings = this.loadSettings();
    console.log('[Watchdog] Settings reloaded:', this.settings);
  }

  /**
   * Start monitoring the Auto-Claude process
   */
  public async start(electronPath: string, appPath: string, args: string[] = []): Promise<void> {
    if (!this.settings.enabled) {
      console.log('[Watchdog] Crash recovery is disabled in settings. Watchdog not started.');
      return;
    }

    console.log('[Watchdog] Starting Auto-Claude process...');
    console.log('[Watchdog] Electron path:', electronPath);
    console.log('[Watchdog] App path:', appPath);
    console.log('[Watchdog] Settings:', this.settings);

    // Resolve the electron path to absolute
    const resolvedElectronPath = path.resolve(electronPath);
    const resolvedAppPath = path.resolve(appPath);

    console.log('[Watchdog] Resolved electron path:', resolvedElectronPath);
    console.log('[Watchdog] Resolved app path:', resolvedAppPath);

    // Launch Auto-Claude main process
    // On Windows, electron in node_modules/.bin is a .cmd file — needs shell: true
    // IMPORTANT: Do NOT manually quote paths when shell: true — Node.js handles
    // argument escaping internally. Manual quotes + cmd.exe quotes = double-quoting
    // which causes '"path"' is not recognized errors.
    const isWindows = process.platform === 'win32';

    this.process = spawn(resolvedElectronPath, [resolvedAppPath, ...args], {
      stdio: ['inherit', 'pipe', 'pipe'],
      detached: false,
      shell: isWindows,
      env: {
        ...process.env,
        WATCHDOG_ENABLED: 'true'
      }
    });

    // Monitor process exit
    this.process.on('exit', (code, signal) => {
      this.handleProcessExit(code, signal);
    });

    // Monitor stdout for logs - forward to console for developer visibility
    if (this.process.stdout) {
      this.process.stdout.on('data', (data) => {
        const line = data.toString().trim();
        if (line) {
          console.log(line); // Forward Electron logs to watchdog terminal
          this.addLog(line);
          this.checkForCrashIndicators(line);
        }
      });
    }

    // Monitor stderr for errors - forward to console for developer visibility
    if (this.process.stderr) {
      this.process.stderr.on('data', (data) => {
        const line = data.toString().trim();
        if (line) {
          console.error(line); // Forward Electron errors to watchdog terminal
          this.addLog(`[ERROR] ${line}`);
          this.checkForCrashIndicators(line);
        }
      });
    }

    console.log('[Watchdog] Process started with PID:', this.process.pid);

    // Start heartbeat monitoring for freeze detection (Layer 2)
    this.startHeartbeatMonitoring();
  }

  /**
   * Add log line to buffer (keep last 100 lines)
   */
  private addLog(line: string): void {
    this.recentLogs.push(line);
    if (this.recentLogs.length > this.maxLogLines) {
      this.recentLogs.shift();
    }
  }

  /**
   * Check log line for crash indicators
   */
  private checkForCrashIndicators(line: string): void {
    const crashPatterns = [
      /segmentation fault/i,
      /unhandled exception/i,
      /fatal error/i,
      /crashed/i,
      /SIGSEGV/i,
      /SIGABRT/i
    ];

    for (const pattern of crashPatterns) {
      if (pattern.test(line)) {
        console.warn('[Watchdog] Crash indicator detected:', line);
        this.emit('crash-indicator', line);
        break;
      }
    }
  }

  /**
   * Handle process exit (normal or crash)
   */
  private async handleProcessExit(code: number | null, signal: NodeJS.Signals | null): Promise<void> {
    if (this.isShuttingDown) {
      console.log('[Watchdog] Clean shutdown detected');
      return;
    }

    const now = Date.now();
    const isCrash = code !== 0 || signal !== null;

    if (isCrash) {
      console.error('[Watchdog] Process crashed!');
      console.error('[Watchdog] Exit code:', code);
      console.error('[Watchdog] Signal:', signal);

      // Record crash timestamp
      this.crashTimestamps.push(now);

      // Use freeze crash info if this exit was triggered by freeze detection,
      // otherwise generate a generic crash info. This prevents overwriting
      // the freeze-specific crash flag that handleFreezeDetected() already wrote.
      const crashInfo = this.freezeTriggered && this.freezeCrashInfo
        ? this.freezeCrashInfo
        : this.getCrashInfo(code, signal);
      this.freezeTriggered = false;
      this.freezeCrashInfo = null;

      // Write crash flag file for Electron to read on restart
      // (skip if freeze handler already wrote it — the flag is already on disk)
      if (!crashInfo.freezeDetected) {
        this.writeCrashFlag(crashInfo);
      }

      // Check for crash loop (too many crashes in short time)
      const recentCrashes = this.crashTimestamps.filter(
        t => now - t < this.settings.restartCooldown
      );

      if (recentCrashes.length >= this.settings.maxRestarts) {
        console.error(
          `[Watchdog] Crash loop detected: ${recentCrashes.length} crashes in ${this.settings.restartCooldown / 1000}s`
        );
        console.error('[Watchdog] Stopping restart attempts to prevent infinite loop');

        // Write crash loop notification for Claude Code
        this.writeCrashLoopNotification(recentCrashes.length, crashInfo);

        this.emit('crash-loop', {
          crashCount: recentCrashes.length,
          crashInfo
        });

        return;
      }

      // Send crash notification
      this.emit('crash', crashInfo);

      // Auto-restart if enabled
      if (this.settings.autoRestart) {
        console.log('[Watchdog] Auto-restart enabled, restarting in 2 seconds...');
        this.restartCount++;

        setTimeout(() => {
          if (!this.isShuttingDown) {
            console.log(`[Watchdog] Restarting (attempt ${this.restartCount})...`);
            // Note: Restart logic would need electron/app paths stored
            this.emit('restart-needed');
          }
        }, 2000);
      }
    } else {
      console.log('[Watchdog] Process exited normally (code 0)');
      // Emit normal-exit event so launcher can exit cleanly and close the terminal
      this.emit('normal-exit', { exitCode: code });
    }
  }

  /**
   * Get crash information for reporting
   */
  private getCrashInfo(exitCode: number | null, signal: NodeJS.Signals | null): CrashInfo {
    return {
      timestamp: Date.now(),
      exitCode,
      signal,
      logs: this.recentLogs.slice(-20) // Last 20 log lines
    };
  }

  /**
   * Write crash flag file for Electron to read on next startup
   */
  private writeCrashFlag(crashInfo: CrashInfo): void {
    try {
      const appDataPath = process.env.APPDATA ||
                          (process.platform === 'darwin' ? path.join(process.env.HOME!, 'Library', 'Application Support') :
                           path.join(process.env.HOME!, '.config'));
      const flagDir = path.join(appDataPath, APP_DATA_DIR_NAME);
      const flagPath = path.join(flagDir, 'crash-flag.json');

      // Ensure directory exists
      if (!fs.existsSync(flagDir)) {
        fs.mkdirSync(flagDir, { recursive: true });
      }

      fs.writeFileSync(flagPath, JSON.stringify(crashInfo, null, 2), 'utf-8');
      console.log('[Watchdog] Crash flag written:', flagPath);

      // Also write crash notification for Claude Code's MCP server to poll
      this.writeCrashNotification(crashInfo);
    } catch (error) {
      console.error('[Watchdog] Failed to write crash flag:', error);
    }
  }

  /**
   * Write crash notification file for Claude Code's MCP server to poll
   * This file-based approach works even when Electron is crashed/dead
   * MCP server polls this file and sends notification to all connected Claude Code sessions
   */
  private writeCrashNotification(crashInfo: CrashInfo): void {
    try {
      const appDataPath = process.env.APPDATA ||
                          (process.platform === 'darwin' ? path.join(process.env.HOME!, 'Library', 'Application Support') :
                           path.join(process.env.HOME!, '.config'));

      const notificationDir = path.join(appDataPath, APP_DATA_DIR_NAME);
      const notificationPath = path.join(notificationDir, 'crash-notification.json');

      // Ensure directory exists
      if (!fs.existsSync(notificationDir)) {
        fs.mkdirSync(notificationDir, { recursive: true });
      }

      const isFreeze = crashInfo.freezeDetected === true;
      const notification = {
        type: isFreeze ? 'freeze_detected' : 'crash_detected',
        ...(isFreeze ? { freezeType: crashInfo.freezeType } : {}),
        timestamp: new Date().toISOString(),
        exitCode: crashInfo.exitCode,
        signal: crashInfo.signal,
        logs: crashInfo.logs,
        autoRestart: this.settings.autoRestart,
        restartCount: this.restartCount,
        message: isFreeze
          ? `Auto-Claude froze at ${new Date(crashInfo.timestamp).toISOString()}. Type: ${crashInfo.freezeType}. ${
              this.settings.autoRestart ? 'Restarting automatically.' : 'Auto-restart disabled.'
            }`
          : `Auto-Claude crashed at ${new Date(crashInfo.timestamp).toISOString()}. ${
              this.settings.autoRestart ? 'Auto-restart enabled, restarting in 2 seconds...' : 'Auto-restart disabled.'
            }`
      };

      fs.writeFileSync(notificationPath, JSON.stringify(notification, null, 2), 'utf-8');
      console.log('[Watchdog] Crash notification written for Claude Code:', notificationPath);
    } catch (error) {
      console.error('[Watchdog] Failed to write crash notification:', error);
    }
  }

  /**
   * Write crash loop notification for Claude Code
   */
  public writeCrashLoopNotification(crashCount: number, crashInfo: CrashInfo): void {
    try {
      const appDataPath = process.env.APPDATA ||
                          (process.platform === 'darwin' ? path.join(process.env.HOME!, 'Library', 'Application Support') :
                           path.join(process.env.HOME!, '.config'));

      const notificationDir = path.join(appDataPath, APP_DATA_DIR_NAME);
      const notificationPath = path.join(notificationDir, 'crash-notification.json');

      // Ensure directory exists
      if (!fs.existsSync(notificationDir)) {
        fs.mkdirSync(notificationDir, { recursive: true });
      }

      const notification = {
        type: 'crash_loop',
        timestamp: new Date().toISOString(),
        exitCode: crashInfo.exitCode,
        signal: crashInfo.signal,
        logs: crashInfo.logs,
        crashCount,
        autoRestart: false,
        restartCount: this.restartCount,
        message: `Auto-Claude crash loop detected: ${crashCount} crashes in ${this.settings.restartCooldown / 1000}s. Restart attempts stopped.`
      };

      fs.writeFileSync(notificationPath, JSON.stringify(notification, null, 2), 'utf-8');
      console.log('[Watchdog] Crash LOOP notification written for Claude Code:', notificationPath);
    } catch (error) {
      console.error('[Watchdog] Failed to write crash loop notification:', error);
    }
  }

  // --- Heartbeat Monitoring (Layer 2: Detect main process freeze) ---

  /**
   * Get the path to the heartbeat file written by the Electron main process
   */
  private getHeartbeatPath(): string {
    const appDataPath = process.env.APPDATA ||
      (process.platform === 'darwin'
        ? path.join(process.env.HOME!, 'Library', 'Application Support')
        : path.join(process.env.HOME!, '.config'));
    return path.join(appDataPath, APP_DATA_DIR_NAME, 'heartbeat.json');
  }

  /**
   * Start polling the heartbeat file to detect main process freezes
   */
  private startHeartbeatMonitoring(): void {
    const heartbeatPath = this.getHeartbeatPath();
    console.log('[Watchdog] Starting heartbeat monitor, checking:', heartbeatPath);

    this.heartbeatCheckInterval = setInterval(() => {
      if (this.isShuttingDown) return;

      try {
        if (!fs.existsSync(heartbeatPath)) {
          // No heartbeat file yet — process may still be starting up
          return;
        }

        const content = fs.readFileSync(heartbeatPath, 'utf-8');
        const heartbeat = JSON.parse(content);
        const age = Date.now() - heartbeat.timestamp;

        if (age > this.HEARTBEAT_STALE_THRESHOLD_MS) {
          console.error(
            `[Watchdog] FREEZE DETECTED: Heartbeat stale by ${Math.round(age / 1000)}s ` +
            `(threshold: ${this.HEARTBEAT_STALE_THRESHOLD_MS / 1000}s)`
          );
          this.handleFreezeDetected(heartbeat.pid, age);
        }
      } catch {
        // JSON parse error or read error — skip this check (file might be mid-write)
      }
    }, this.HEARTBEAT_CHECK_INTERVAL_MS);

    this.heartbeatCheckInterval.unref();
  }

  /**
   * Handle detected freeze — kill frozen process and trigger restart via existing exit handler
   */
  private handleFreezeDetected(frozenPid: number, staleAge: number): void {
    // Stop heartbeat monitoring to prevent duplicate detections
    this.stopHeartbeatMonitoring();

    const reason = `Main process freeze detected (heartbeat stale for ${Math.round(staleAge / 1000)}s)`;
    console.error('[Watchdog] Killing frozen process (PID:', frozenPid, ')');

    // Write freeze-specific crash flag + notification
    const crashInfo: CrashInfo = {
      timestamp: Date.now(),
      exitCode: null,
      signal: null,
      logs: [
        `[Freeze] ${reason}`,
        `[Freeze] Frozen PID: ${frozenPid}`,
        `[Freeze] Stale age: ${Math.round(staleAge / 1000)}s`,
        ...this.recentLogs.slice(-15)
      ],
      freezeDetected: true,
      freezeType: 'main_process_freeze'
    };
    this.writeCrashFlag(crashInfo);

    // Store freeze info so handleProcessExit doesn't overwrite the crash flag
    this.freezeTriggered = true;
    this.freezeCrashInfo = crashInfo;

    // Force-kill the frozen process
    try {
      if (process.platform === 'win32') {
        const { spawnSync } = require('child_process') as typeof import('child_process');
        spawnSync('taskkill', ['/pid', frozenPid.toString(), '/f', '/t'], { stdio: 'ignore' });
      } else {
        process.kill(frozenPid, 'SIGKILL');
      }
    } catch (error) {
      console.error('[Watchdog] Failed to kill frozen process:', error);
    }

    // The existing process.on('exit') handler fires after the kill → triggers restart
  }

  /**
   * Stop heartbeat monitoring
   */
  private stopHeartbeatMonitoring(): void {
    if (this.heartbeatCheckInterval) {
      clearInterval(this.heartbeatCheckInterval);
      this.heartbeatCheckInterval = null;
    }
  }

  /**
   * Stop the watchdog and monitored process
   */
  public async stop(): Promise<void> {
    console.log('[Watchdog] Stopping...');
    this.isShuttingDown = true;
    this.stopHeartbeatMonitoring();

    if (this.process && !this.process.killed) {
      console.log('[Watchdog] Terminating monitored process...');
      this.process.kill('SIGTERM');

      // Wait for graceful shutdown, then force kill if needed
      await new Promise<void>((resolve) => {
        const timeout = setTimeout(() => {
          if (this.process && !this.process.killed) {
            console.warn('[Watchdog] Force killing process...');
            this.process.kill('SIGKILL');
          }
          resolve();
        }, 5000);

        if (this.process) {
          this.process.once('exit', () => {
            clearTimeout(timeout);
            resolve();
          });
        } else {
          clearTimeout(timeout);
          resolve();
        }
      });
    }

    this.process = null;
    console.log('[Watchdog] Stopped');
  }

  /**
   * Get current watchdog status
   */
  public getStatus(): {
    running: boolean;
    enabled: boolean;
    pid: number | undefined;
    restartCount: number;
    recentCrashes: number;
  } {
    const now = Date.now();
    const recentCrashes = this.crashTimestamps.filter(
      t => now - t < this.settings.restartCooldown
    ).length;

    return {
      running: this.process !== null && !this.process.killed,
      enabled: this.settings.enabled,
      pid: this.process?.pid,
      restartCount: this.restartCount,
      recentCrashes
    };
  }
}
