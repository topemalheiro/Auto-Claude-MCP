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
  private appDataDir: string;
  private logStream: fs.WriteStream | null = null;
  // Heartbeat monitoring for freeze detection (Layer 2)
  private heartbeatCheckInterval: ReturnType<typeof setInterval> | null = null;
  private readonly HEARTBEAT_CHECK_INTERVAL_MS = 15_000;  // Check every 15s
  private readonly HEARTBEAT_STALE_THRESHOLD_MS = 45_000; // Stale after 45s
  // Watchdog self-heartbeat (so launcher can detect watchdog freeze)
  private selfHeartbeatInterval: ReturnType<typeof setInterval> | null = null;
  // When true, handleProcessExit uses the stored freeze crashInfo instead of a generic one
  private freezeTriggered = false;
  private freezeCrashInfo: CrashInfo | null = null;

  constructor() {
    super();

    // Load settings from app data directory
    const appDataPath = process.env.APPDATA ||
                        (process.platform === 'darwin' ? path.join(process.env.HOME!, 'Library', 'Application Support') :
                         path.join(process.env.HOME!, '.config'));
    this.appDataDir = path.join(appDataPath, APP_DATA_DIR_NAME);
    this.settingsPath = path.join(this.appDataDir, 'settings.json');

    // Ensure app data directory exists
    if (!fs.existsSync(this.appDataDir)) {
      fs.mkdirSync(this.appDataDir, { recursive: true });
    }

    // Initialize disk logging
    this.initLogFile();

    // Load crash recovery settings
    this.settings = this.loadSettings();
  }

  /**
   * Initialize log file for persistent disk logging
   */
  private initLogFile(): void {
    const logPath = path.join(this.appDataDir, 'watchdog.log');
    try {
      // Truncate if > 1MB
      if (fs.existsSync(logPath)) {
        const stat = fs.statSync(logPath);
        if (stat.size > 1_000_000) {
          fs.unlinkSync(logPath);
        }
      }
      this.logStream = fs.createWriteStream(logPath, { flags: 'a' });
    } catch (error) {
      console.error('[Watchdog] Failed to init log file:', error);
    }
  }

  /**
   * Write a timestamped log entry to both console and disk
   */
  private log(level: 'INFO' | 'WARN' | 'ERROR', ...args: unknown[]): void {
    const timestamp = new Date().toISOString();
    const message = args.map(a => (typeof a === 'object' ? JSON.stringify(a) : String(a))).join(' ');
    const line = `[${timestamp}] [Watchdog:${level}] ${message}`;

    if (level === 'ERROR') {
      console.error(line);
    } else if (level === 'WARN') {
      console.warn(line);
    } else {
      console.log(line);
    }

    try {
      this.logStream?.write(line + '\n');
    } catch { /* ignore write errors */ }
  }

  /**
   * Start watchdog self-heartbeat and status file
   */
  private startSelfHeartbeat(): void {
    const hbPath = path.join(this.appDataDir, 'watchdog-heartbeat.json');
    const statusPath = path.join(this.appDataDir, 'watchdog-status.json');

    const writeStatus = (): void => {
      try {
        const heartbeat = {
          pid: process.pid,
          timestamp: Date.now(),
          monitoring: this.process?.pid ?? null,
          restartCount: this.restartCount,
          recentCrashes: this.crashTimestamps.filter(t => Date.now() - t < this.settings.restartCooldown).length,
          enabled: this.settings.enabled,
          running: this.process !== null && !this.process.killed
        };
        fs.writeFileSync(hbPath, JSON.stringify(heartbeat), 'utf-8');
        fs.writeFileSync(statusPath, JSON.stringify(heartbeat, null, 2), 'utf-8');
      } catch { /* ignore */ }
    };

    writeStatus(); // Write immediately
    this.selfHeartbeatInterval = setInterval(writeStatus, 15_000);
    this.selfHeartbeatInterval.unref();
  }

  /**
   * Stop watchdog self-heartbeat and clean up files
   */
  private stopSelfHeartbeat(): void {
    if (this.selfHeartbeatInterval) {
      clearInterval(this.selfHeartbeatInterval);
      this.selfHeartbeatInterval = null;
    }
    // Clean up heartbeat file on clean shutdown
    try {
      const hbPath = path.join(this.appDataDir, 'watchdog-heartbeat.json');
      if (fs.existsSync(hbPath)) fs.unlinkSync(hbPath);
    } catch { /* ignore */ }
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
    this.log('INFO', 'Settings reloaded:', this.settings);
  }

  /**
   * Start monitoring the Auto-Claude process
   */
  public async start(electronPath: string, appPath: string, args: string[] = []): Promise<void> {
    if (!this.settings.enabled) {
      console.log('[Watchdog] Crash recovery is disabled in settings. Watchdog not started.');
      return;
    }

    this.log('INFO', 'Starting Auto-Claude process...');
    this.log('INFO', 'Electron path:', electronPath);
    this.log('INFO', 'App path:', appPath);
    this.log('INFO', 'Settings:', this.settings);

    // Resolve the electron path to absolute
    const resolvedElectronPath = path.resolve(electronPath);
    const resolvedAppPath = path.resolve(appPath);

    this.log('INFO', 'Resolved electron path:', resolvedElectronPath);
    this.log('INFO', 'Resolved app path:', resolvedAppPath);

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

    this.log('INFO', 'Process started with PID:', this.process.pid);

    // Start heartbeat monitoring for freeze detection (Layer 2)
    this.startHeartbeatMonitoring();

    // Start watchdog self-heartbeat (so launcher can detect watchdog freeze)
    this.startSelfHeartbeat();
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
        this.log('WARN', 'Crash indicator detected:', line);
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
      this.log('ERROR', 'Process crashed!');
      this.log('ERROR', 'Exit code:', code);
      this.log('ERROR', 'Signal:', signal);

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
        this.log('ERROR',
          `Crash loop detected: ${recentCrashes.length} crashes in ${this.settings.restartCooldown / 1000}s`
        );
        this.log('ERROR', 'Stopping restart attempts to prevent infinite loop');

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
        this.log('INFO', 'Auto-restart enabled, restarting in 2 seconds...');
        this.restartCount++;

        setTimeout(() => {
          if (!this.isShuttingDown) {
            this.log('INFO', `Restarting (attempt ${this.restartCount})...`);
            // Note: Restart logic would need electron/app paths stored
            this.emit('restart-needed');
          }
        }, 2000);
      }
    } else {
      this.log('INFO', 'Process exited normally (code 0)');
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
      const flagPath = path.join(this.appDataDir, 'crash-flag.json');

      fs.writeFileSync(flagPath, JSON.stringify(crashInfo, null, 2), 'utf-8');
      this.log('INFO', 'Crash flag written:', flagPath);

      // Also write crash notification for Claude Code's MCP server to poll
      this.writeCrashNotification(crashInfo);
    } catch (error) {
      this.log('ERROR', 'Failed to write crash flag:', error);
    }
  }

  /**
   * Write crash notification file for Claude Code's MCP server to poll
   * This file-based approach works even when Electron is crashed/dead
   * MCP server polls this file and sends notification to all connected Claude Code sessions
   */
  private writeCrashNotification(crashInfo: CrashInfo): void {
    try {
      const notificationPath = path.join(this.appDataDir, 'crash-notification.json');

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
      this.log('INFO', 'Crash notification written for Claude Code:', notificationPath);
    } catch (error) {
      this.log('ERROR', 'Failed to write crash notification:', error);
    }
  }

  /**
   * Write crash loop notification for Claude Code
   */
  public writeCrashLoopNotification(crashCount: number, crashInfo: CrashInfo): void {
    try {
      const notificationPath = path.join(this.appDataDir, 'crash-notification.json');

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
      this.log('ERROR', 'Crash LOOP notification written for Claude Code:', notificationPath);
    } catch (error) {
      this.log('ERROR', 'Failed to write crash loop notification:', error);
    }
  }

  // --- Heartbeat Monitoring (Layer 2: Detect main process freeze) ---

  /**
   * Get the path to the heartbeat file written by the Electron main process
   */
  private getHeartbeatPath(): string {
    return path.join(this.appDataDir, 'heartbeat.json');
  }

  /**
   * Start polling the heartbeat file to detect main process freezes
   */
  private startHeartbeatMonitoring(): void {
    const heartbeatPath = this.getHeartbeatPath();
    this.log('INFO', 'Starting heartbeat monitor, checking:', heartbeatPath);

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
          this.log('ERROR',
            `FREEZE DETECTED: Heartbeat stale by ${Math.round(age / 1000)}s ` +
            `(threshold: ${this.HEARTBEAT_STALE_THRESHOLD_MS / 1000}s)`
          );
          this.handleFreezeDetected(heartbeat.pid, age);
          return;
        }

        // Functional freeze check: process alive but no useful work happening
        // Main process self-heals at 15 min; watchdog is the backup at 20 min
        const FUNCTIONAL_FREEZE_MS = 20 * 60_000;
        if (heartbeat.activity) {
          const activityAge = Date.now() - heartbeat.activity.lastActivityAt;
          if (activityAge > FUNCTIONAL_FREEZE_MS && heartbeat.activity.selfHealAttempts >= 3) {
            this.log('ERROR',
              `FUNCTIONAL FREEZE: No activity for ${Math.round(activityAge / 60_000)}min, ` +
              `${heartbeat.activity.selfHealAttempts} self-heals failed, ` +
              `last activity: "${heartbeat.activity.lastActivitySource}"`
            );
            this.handleFreezeDetected(heartbeat.pid, activityAge);
          }
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
    this.log('ERROR', 'Killing frozen process (PID:', frozenPid, ')');

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
      this.log('ERROR', 'Failed to kill frozen process:', error);
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
    this.log('INFO', 'Stopping...');
    this.isShuttingDown = true;
    this.stopHeartbeatMonitoring();
    this.stopSelfHeartbeat();

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
    this.log('INFO', 'Stopped');
    // Close log stream
    try { this.logStream?.end(); } catch { /* ignore */ }
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
