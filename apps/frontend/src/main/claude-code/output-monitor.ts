/**
 * Claude Code Output Monitor
 *
 * Monitors Claude Code's session state to detect when it's waiting at a prompt.
 * This prevents RDR from sending messages while Claude is in a prompt loop.
 *
 * FIXED: Now monitors JSONL transcripts in ~/.claude/projects/ instead of empty
 * .output files in %LOCALAPPDATA%\Temp\claude\
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
  private claudeProjectsDir: string;

  constructor() {
    // Monitor JSONL transcripts in ~/.claude/projects/
    // (.output files in temp are empty/old, JSONL files have real session data)
    this.claudeProjectsDir = path.join(os.homedir(), '.claude', 'projects');
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
   * Update Claude's state by checking recent JSONL transcript
   */
  private async updateState(): Promise<void> {
    // Find the most recent JSONL transcript across all projects
    const latestTranscript = await this.getLatestOutputFile();

    if (!latestTranscript) {
      // No recent transcript files - Claude is idle
      this.setState('IDLE');
      return;
    }

    // Read last 50 lines of JSONL file (each line is a JSON object)
    const content = await fs.readFile(latestTranscript, 'utf-8');
    const lines = content.trim().split('\n');
    const recentLines = lines.slice(-50);

    // Parse JSONL and extract text content
    let recentText = '';
    for (const line of recentLines) {
      try {
        const entry = JSON.parse(line);
        // Extract text from "text" field or "content" array
        if (entry.text) {
          recentText += entry.text + '\n';
        } else if (entry.content && Array.isArray(entry.content)) {
          for (const block of entry.content) {
            if (block.type === 'text' && block.text) {
              recentText += block.text + '\n';
            }
          }
        }
      } catch {
        // Skip malformed JSON lines
        continue;
      }
    }

    // Check for prompt pattern (highest priority)
    if (this.matchesAnyPattern(recentText, PATTERNS.AT_PROMPT)) {
      this.setState('AT_PROMPT');
      return;
    }

    // Check for processing pattern
    if (this.matchesAnyPattern(recentText, PATTERNS.PROCESSING)) {
      this.setState('PROCESSING');
      return;
    }

    // Default to idle if no patterns match
    this.setState('IDLE');
  }

  /**
   * Find the most recently modified JSONL transcript file across all project directories
   */
  private async getLatestOutputFile(): Promise<string | null> {
    try {
      // List all project directories under ~/.claude/projects/
      const projectDirs = await fs.readdir(this.claudeProjectsDir);

      let latestFile: { path: string; mtime: number } | null = null;

      for (const projectDir of projectDirs) {
        const projectPath = path.join(this.claudeProjectsDir, projectDir);

        try {
          const files = await fs.readdir(projectPath);

          for (const file of files) {
            // Find .jsonl files (but skip sessions-index.json)
            if (file.endsWith('.jsonl') && !file.startsWith('sessions-index')) {
              const filePath = path.join(projectPath, file);
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
          // Directory doesn't exist or can't be read, skip
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
      await fs.access(this.claudeProjectsDir);
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
