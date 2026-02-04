/**
 * Watchdog Launcher - Entry point for launching Auto-Claude with crash recovery
 *
 * This is a standalone Node.js script that runs OUTSIDE the Electron process.
 * It launches Electron as a child process and monitors it for crashes.
 *
 * Usage:
 *   node launcher.js [electron-path] [app-path]
 *
 * Or via npm script:
 *   npm run start:watchdog
 */

import { AutoClaudeWatchdog } from './auto-claude-watchdog';
import { crashNotifier } from './crash-notifier';
import * as path from 'path';
import * as fs from 'fs';

// Parse command line arguments
const args = process.argv.slice(2);
const electronPath = args[0] || process.execPath; // Default to current Node.js if not specified
const appPath = args[1] || path.join(__dirname, '../index.js'); // Default to compiled main

console.log('='.repeat(80));
console.log('Auto-Claude Watchdog Launcher');
console.log('='.repeat(80));
console.log(`Electron: ${electronPath}`);
console.log(`App: ${appPath}`);
console.log('');

// Create watchdog instance
const watchdog = new AutoClaudeWatchdog();

// Handle crash events
watchdog.on('crash', async (crashInfo) => {
  console.error('[Launcher] 🚨 CRASH DETECTED');
  console.error('[Launcher] Exit code:', crashInfo.exitCode);
  console.error('[Launcher] Signal:', crashInfo.signal);
  console.error('[Launcher] Recent logs:', crashInfo.logs.join('\n'));

  // Send crash notification to Claude Code via MCP
  try {
    await crashNotifier.sendCrashNotification('crash_detected', {
      exitCode: crashInfo.exitCode,
      signal: crashInfo.signal,
      restartCount: watchdog.getStatus().restartCount,
      logs: crashInfo.logs
    });
  } catch (error) {
    console.error('[Launcher] Failed to send crash notification:', error);
  }
});

// Handle crash loop events
watchdog.on('crash-loop', async (data) => {
  console.error('[Launcher] 🔥 CRASH LOOP DETECTED');
  console.error('[Launcher] Crash count:', data.crashCount);
  console.error('[Launcher] Stopping restart attempts');

  // Send crash loop notification
  try {
    await crashNotifier.sendCrashNotification('crash_loop', {
      exitCode: data.crashInfo.exitCode,
      signal: data.crashInfo.signal,
      restartCount: watchdog.getStatus().restartCount,
      logs: data.crashInfo.logs,
      crashCount: data.crashCount
    });
  } catch (error) {
    console.error('[Launcher] Failed to send crash loop notification:', error);
  }

  // Exit launcher after crash loop
  console.error('[Launcher] Exiting...');
  process.exit(1);
});

// Handle restart needed events
watchdog.on('restart-needed', async () => {
  console.log('[Launcher] Restart requested, relaunching...');

  try {
    await watchdog.start(electronPath, appPath);
  } catch (error) {
    console.error('[Launcher] Failed to restart:', error);
    process.exit(1);
  }
});

// Handle normal exit events (user closed the app via X button)
watchdog.on('normal-exit', (data) => {
  console.log('[Launcher] ✅ Auto-Claude closed normally');
  console.log('[Launcher] Exit code:', data.exitCode);
  console.log('[Launcher] Exiting launcher (terminal will close)...');
  process.exit(0);
});

// Handle SIGINT (Ctrl+C) and SIGTERM for clean shutdown
process.on('SIGINT', async () => {
  console.log('[Launcher] Received SIGINT, shutting down...');
  await watchdog.stop();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('[Launcher] Received SIGTERM, shutting down...');
  await watchdog.stop();
  process.exit(0);
});

// Unhandled exceptions in launcher
process.on('uncaughtException', (error) => {
  console.error('[Launcher] Uncaught exception:', error);
  // Don't exit - keep watchdog running
});

// Start watchdog
(async () => {
  try {
    console.log('[Launcher] Starting watchdog...');
    await watchdog.start(electronPath, appPath);

    const status = watchdog.getStatus();

    // Check if watchdog actually started (crash recovery might be disabled)
    if (!status.running) {
      console.log('[Launcher] Crash recovery is disabled in settings');
      console.log('[Launcher] Starting Electron directly without monitoring...');

      // Start Electron directly using spawn
      const { spawn } = await import('child_process');
      const electronProcess = spawn(electronPath, [appPath], {
        stdio: 'inherit',
        detached: false,
        env: { ...process.env }
      });

      electronProcess.on('exit', (code) => {
        console.log('[Launcher] Electron exited with code:', code);
        process.exit(code || 0);
      });

      electronProcess.on('error', (err) => {
        console.error('[Launcher] Failed to start Electron:', err);
        process.exit(1);
      });

      return;
    }

    console.log('[Launcher] Watchdog started successfully');
    console.log('[Launcher] Status:', status);
    console.log('');
    console.log('Press Ctrl+C to stop');
    console.log('='.repeat(80));
  } catch (error) {
    console.error('[Launcher] Failed to start watchdog:', error);
    process.exit(1);
  }
})();
