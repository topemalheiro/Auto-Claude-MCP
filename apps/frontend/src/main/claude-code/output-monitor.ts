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
      console.log('[OutputMonitor] Checking prompt state...');
      await this.updateState();
      console.log('[OutputMonitor] Current state after update:', this.currentState);
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
      console.log('[OutputMonitor] No recent JSONL transcript found - setting IDLE');
      this.setState('IDLE');
      return;
    }

    console.log('[OutputMonitor] Found latest transcript:', latestTranscript);

    // Read last 50 lines of JSONL file (each line is a JSON object)
    const content = await fs.readFile(latestTranscript, 'utf-8');
    const lines = content.trim().split('\n');
    const recentLines = lines.slice(-50);

    console.log('[OutputMonitor] Reading last', recentLines.length, 'lines from transcript');

    // Check file age first - if very old, session is IDLE not AT_PROMPT
    const stats = await fs.stat(latestTranscript);
    const timeSinceLastWrite = Date.now() - stats.mtimeMs;
    const ageMinutes = Math.floor(timeSinceLastWrite / 60000);

    // If file hasn't been touched in 2+ minutes, session is IDLE
    if (timeSinceLastWrite > 120000) {
      console.log(`[OutputMonitor] Session idle for ${ageMinutes} minutes - setting IDLE`);
      this.setState('IDLE');
      return;
    }

    // NEW: Detect when LLM is actively thinking/generating a response
    // If last entry is a USER message and file was updated < 90s ago, LLM is processing
    // (90s window covers RDR's 60s interval + thinking time)
    if (lines.length > 0 && timeSinceLastWrite < 90000) {
      try {
        const lastLine = lines[lines.length - 1];
        const lastEntry = JSON.parse(lastLine);

        if (lastEntry.type === 'user') {
          // User just sent message < 90s ago, LLM is likely thinking/generating
          const ageSeconds = Math.floor(timeSinceLastWrite / 1000);
          console.log(
            `[OutputMonitor] Recent user message (${ageSeconds}s ago), LLM likely processing - setting PROCESSING`
          );
          this.setState('PROCESSING');
          return;
        }
      } catch {
        // If we can't parse the last line, continue with normal detection
        console.log('[OutputMonitor] Could not parse last JSONL line, continuing with pattern detection');
      }
    }

    // Parse JSONL and extract text content
    let recentText = '';
    for (const line of recentLines) {
      try {
        const entry = JSON.parse(line);
        // Extract text from message.content array (user/assistant messages)
        if ((entry.type === 'user' || entry.type === 'assistant') && entry.message?.content) {
          for (const block of entry.message.content) {
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

    const textPreview = recentText.slice(-200).replace(/\n/g, '\\n');
    console.log('[OutputMonitor] Extracted text (last 200 chars):', textPreview);

    // Check for prompt pattern (PRIMARY detection method)
    if (this.matchesAnyPattern(recentText, PATTERNS.AT_PROMPT)) {
      console.log('[OutputMonitor] PROMPT DETECTED - Setting AT_PROMPT');
      this.setState('AT_PROMPT');
      return;
    }

    // Check for processing pattern
    if (this.matchesAnyPattern(recentText, PATTERNS.PROCESSING)) {
      console.log('[OutputMonitor] PROCESSING DETECTED - Setting PROCESSING');
      this.setState('PROCESSING');
      return;
    }

    // Default to idle if no patterns match
    console.log('[OutputMonitor] No patterns matched - setting IDLE');
    this.setState('IDLE');
  }

  /**
   * Find the most recently modified JSONL transcript file across all project directories
   */
  private async getLatestOutputFile(): Promise<string | null> {
    try {
      console.log('[OutputMonitor] Searching for JSONL transcripts in:', this.claudeProjectsDir);

      // List all project directories under ~/.claude/projects/
      const projectDirs = await fs.readdir(this.claudeProjectsDir);
      console.log('[OutputMonitor] Found', projectDirs.length, 'project directories');

      let latestFile: { path: string; mtime: number } | null = null;
      let totalJsonlFiles = 0;
      let recentJsonlFiles = 0;

      for (const projectDir of projectDirs) {
        const projectPath = path.join(this.claudeProjectsDir, projectDir);

        try {
          const files = await fs.readdir(projectPath);

          for (const file of files) {
            // Find .jsonl files (but skip sessions-index.json)
            if (file.endsWith('.jsonl') && !file.startsWith('sessions-index')) {
              totalJsonlFiles++;
              const filePath = path.join(projectPath, file);
              const stats = await fs.stat(filePath);

              // Only consider files modified in the last 5 minutes
              // (Claude Code sessions may not constantly write to JSONL)
              const ageMs = Date.now() - stats.mtimeMs;

              if (ageMs > 300000) {
                continue; // Skip old files silently
              }

              const ageSeconds = Math.floor(ageMs / 1000);
              recentJsonlFiles++;
              console.log('[OutputMonitor]   Found recent file:', file, `(${ageSeconds}s old)`);

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

      console.log('[OutputMonitor] Summary: Found', totalJsonlFiles, 'total JSONL files,', recentJsonlFiles, 'recent (<5min)');

      if (latestFile) {
        console.log('[OutputMonitor] Selected latest file:', latestFile.path);
      } else {
        console.log('[OutputMonitor] No recent JSONL files found');
      }

      return latestFile?.path || null;
    } catch (error) {
      // Base directory doesn't exist or can't be accessed
      console.warn('[OutputMonitor] Failed to access projects directory:', error);
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
        `[OutputMonitor] State transition: ${oldState} -> ${newState} (after ${this.getTimeSinceStateChange()}ms)`
      );

      // Log additional context for debugging
      if (newState === 'AT_PROMPT') {
        console.log('[OutputMonitor] WARNING: Claude is at prompt - RDR should skip sending');
      } else if (newState === 'PROCESSING') {
        console.log('[OutputMonitor] INFO: Claude is processing - RDR should skip sending');
      } else if (newState === 'IDLE') {
        console.log('[OutputMonitor] INFO: Claude is idle - RDR can send');
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
