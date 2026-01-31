/**
 * Claude Code Output Monitor
 *
 * Monitors Claude Code's session state to detect when it's waiting at a prompt.
 * This prevents RDR from sending messages while Claude is in a prompt loop.
 *
 * FIXED: Now uses the CORRECT directory paths where Claude Code stores output
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import * as os from 'os';

/**
 * Claude Code's possible states
 */
export type ClaudeState = 'AT_PROMPT' | 'PROCESSING' | 'IDLE';

/**
 * Prompt and activity patterns to detect Claude's state
 */
const PATTERNS = {
  // Claude waiting for input (the ">" prompt)
  AT_PROMPT: [
    /^>\s*$/m, // Just ">" on its own line
    /\n>\s*$/m, // ">" at end after newline
    /^\s*>\s+$/m // ">" with possible whitespace
  ],

  // Claude actively processing/working
  PROCESSING: [
    /^●/m, // Claude's response bullet point
    /\u25cf/m, // Unicode bullet point (●)
    /^(Read|Write|Edit|Bash|Grep|Glob|Task|WebFetch|WebSearch|TodoWrite|AskUserQuestion)\(/m, // Tool calls
    /^\s*\d+\s*[│|]\s*/m, // Line numbers (Claude reading files)
    /Loading\.\.\./i,
    /Thinking\.\.\./i,
    /Analyzing\.\.\./i,
    /Processing\.\.\./i,
    /Working\.\.\./i,
    /Searching\.\.\./i,
    /Creating\.\.\./i,
    /Updating\.\.\./i,
    /Running\.\.\./i
  ]
};

/**
 * Monitor Claude Code's output files to detect prompt state
 */
class ClaudeOutputMonitor {
  private currentState: ClaudeState = 'IDLE';
  private lastStateChange: number = Date.now();
  private taskOutputBaseDir: string;

  constructor() {
    // Use the CORRECT path: %APPDATA%\Local\Temp\claude\
    const localAppData = process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local');
    this.taskOutputBaseDir = path.join(localAppData, 'Temp', 'claude');
  }

  /**
   * Check if Claude Code is currently at a prompt (waiting for input)
   * This is the PRIMARY indicator that we should NOT send RDR messages
   */
  async isAtPrompt(): Promise<boolean> {
    try {
      await this.updateState();
      return this.currentState === 'AT_PROMPT';
    } catch (error) {
      // On error, assume not at prompt (graceful degradation)
      console.warn('[OutputMonitor] Failed to check prompt state:', error);
      return false;
    }
  }

  /**
   * Get current Claude Code state
   */
  getCurrentState(): ClaudeState {
    return this.currentState;
  }

  /**
   * Get time since last state change (in milliseconds)
   */
  getTimeSinceStateChange(): number {
    return Date.now() - this.lastStateChange;
  }

  /**
   * Update Claude's state by checking recent output files
   */
  private async updateState(): Promise<void> {
    // Find the most recent .output file across all projects
    const latestOutput = await this.getLatestOutputFile();

    if (!latestOutput) {
      // No recent output files - Claude is idle
      this.setState('IDLE');
      return;
    }

    const content = await fs.readFile(latestOutput, 'utf-8');

    // Get last 20 lines (enough to detect current state)
    const lines = content.split('\n');
    const recentLines = lines.slice(-20).join('\n');

    // Check for prompt pattern (highest priority)
    if (this.matchesAnyPattern(recentLines, PATTERNS.AT_PROMPT)) {
      this.setState('AT_PROMPT');
      return;
    }

    // Check for processing pattern
    if (this.matchesAnyPattern(recentLines, PATTERNS.PROCESSING)) {
      this.setState('PROCESSING');
      return;
    }

    // Default to idle if no patterns match
    this.setState('IDLE');
  }

  /**
   * Find the most recently modified .output file across all project directories
   */
  private async getLatestOutputFile(): Promise<string | null> {
    try {
      // List all project directories under %APPDATA%\Local\Temp\claude\
      const projectDirs = await fs.readdir(this.taskOutputBaseDir);

      let latestFile: { path: string; mtime: number } | null = null;

      for (const projectDir of projectDirs) {
        const tasksDir = path.join(this.taskOutputBaseDir, projectDir, 'tasks');

        try {
          const files = await fs.readdir(tasksDir);

          for (const file of files) {
            if (file.endsWith('.output')) {
              const filePath = path.join(tasksDir, file);
              const stats = await fs.stat(filePath);

              // Only consider files modified in the last 60 seconds
              const ageMs = Date.now() - stats.mtimeMs;
              if (ageMs > 60000) continue;

              if (!latestFile || stats.mtimeMs > latestFile.mtime) {
                latestFile = { path: filePath, mtime: stats.mtimeMs };
              }
            }
          }
        } catch {
          // tasks directory doesn't exist for this project, skip
          continue;
        }
      }

      return latestFile?.path || null;
    } catch (error) {
      // Base directory doesn't exist or can't be accessed
      return null;
    }
  }

  /**
   * Check if text matches any pattern in the list
   */
  private matchesAnyPattern(text: string, patterns: RegExp[]): boolean {
    return patterns.some((pattern) => pattern.test(text));
  }

  /**
   * Update state and log transition if changed
   */
  private setState(newState: ClaudeState): void {
    if (newState !== this.currentState) {
      const oldState = this.currentState;
      this.currentState = newState;
      this.lastStateChange = Date.now();

      console.log(
        `[OutputMonitor] State transition: ${oldState} → ${newState} (after ${this.getTimeSinceStateChange()}ms)`
      );

      // Log additional context for debugging
      if (newState === 'AT_PROMPT') {
        console.log('[OutputMonitor] ⚠️  Claude is at prompt - RDR should skip sending');
      } else if (newState === 'PROCESSING') {
        console.log('[OutputMonitor] 🔄 Claude is processing - RDR should skip sending');
      } else if (newState === 'IDLE') {
        console.log('[OutputMonitor] ✅ Claude is idle - RDR can send');
      }
    }
  }

  /**
   * Get diagnostic information about current state
   */
  async getDiagnostics(): Promise<{
    state: ClaudeState;
    timeSinceStateChange: number;
    recentOutputFiles: number;
    baseDirExists: boolean;
  }> {
    const latestOutput = await this.getLatestOutputFile().catch(() => null);
    let baseDirExists = false;
    try {
      await fs.access(this.taskOutputBaseDir);
      baseDirExists = true;
    } catch {
      baseDirExists = false;
    }

    return {
      state: this.currentState,
      timeSinceStateChange: this.getTimeSinceStateChange(),
      recentOutputFiles: latestOutput ? 1 : 0,
      baseDirExists
    };
  }
}

// Export singleton instance
export const outputMonitor = new ClaudeOutputMonitor();
