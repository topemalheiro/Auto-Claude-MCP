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

    // Read and parse JSONL file
    const content = await fs.readFile(latestTranscript, 'utf-8');
    const lines = content.trim().split('\n');

    // Parse all messages (we need full context for conversation state)
    const messages: any[] = [];
    for (const line of lines) {
      try {
        const entry = JSON.parse(line);
        if (entry.type === 'user' || entry.type === 'assistant') {
          messages.push(entry);
        }
      } catch {
        // Skip malformed JSON lines
        continue;
      }
    }

    console.log('[OutputMonitor] Parsed', messages.length, 'messages from transcript');

    // Parse conversation state (not time-based guess)
    const state = this.parseConversationState(messages);
    this.setState(state);
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
   * Parse the actual conversation state from JSONL messages
   * Returns the true state based on conversation flow, not time guesses
   */
  private parseConversationState(messages: any[]): ClaudeState {
    if (messages.length === 0) {
      console.log('[OutputMonitor] No messages - returning IDLE');
      return 'IDLE';
    }

    // Get last message
    const lastMessage = messages[messages.length - 1];
    console.log('[OutputMonitor] Last message type:', lastMessage.type, 'stop_reason:', lastMessage.stop_reason);

    // CASE 1: Last message is user message → Claude should be thinking
    if (lastMessage.type === 'user') {
      // Check if session is abandoned (>5 minutes old)
      if (this.isMessageVeryOld(lastMessage)) {
        console.log('[OutputMonitor] User message is very old (>5min) - session abandoned');
        return 'IDLE';
      }
      console.log('[OutputMonitor] User message detected - Claude should be responding');
      return 'PROCESSING';
    }

    // CASE 2: Last message is assistant message
    if (lastMessage.type === 'assistant') {
      // Check stop_reason (ACTUAL STATE, not time guess)
      if (lastMessage.stop_reason === 'tool_use') {
        console.log('[OutputMonitor] stop_reason=tool_use - waiting for tool results');
        return 'PROCESSING';
      }

      if (lastMessage.stop_reason === null || lastMessage.stop_reason === undefined) {
        console.log('[OutputMonitor] stop_reason=null - still streaming');
        return 'PROCESSING';
      }

      if (lastMessage.stop_reason === 'end_turn') {
        // Message complete - check what it contains
        const lastContent = this.getLastTextContent(lastMessage);

        // Does it end with a question to the user?
        if (this.endsWithQuestion(lastContent)) {
          console.log('[OutputMonitor] Message ends with question - waiting for user answer');
          return 'AT_PROMPT';
        }

        // Does it contain the ">" prompt pattern?
        if (this.matchesAnyPattern(lastContent, PATTERNS.AT_PROMPT)) {
          console.log('[OutputMonitor] Prompt pattern detected - at command prompt');
          return 'AT_PROMPT';
        }

        // Message complete, no question, no prompt
        // Grace period: 2 minutes after completion before allowing RDR
        const messageAge = this.getMessageAge(lastMessage);
        if (messageAge < 120000) {
          const ageSeconds = Math.floor(messageAge / 1000);
          console.log(`[OutputMonitor] Recent completion (${ageSeconds}s ago) - grace period active`);
          return 'PROCESSING';
        }

        console.log('[OutputMonitor] Message complete, grace period expired - session idle');
        return 'IDLE';
      }
    }

    console.log('[OutputMonitor] Unknown state - defaulting to IDLE');
    return 'IDLE';
  }

  /**
   * Helper: Extract last text content from message
   */
  private getLastTextContent(message: any): string {
    if (!message.message?.content) return '';

    const textBlocks = message.message.content
      .filter((block: any) => block.type === 'text')
      .map((block: any) => block.text);

    return textBlocks[textBlocks.length - 1] || '';
  }

  /**
   * Helper: Check if text ends with a question
   */
  private endsWithQuestion(text: string): boolean {
    const trimmed = text.trim();
    return trimmed.endsWith('?') || /\?\s*$/m.test(trimmed);
  }

  /**
   * Helper: Check if message is very old (>5 minutes) - session abandoned
   */
  private isMessageVeryOld(message: any): boolean {
    if (!message.timestamp) return false;
    const messageTime = new Date(message.timestamp).getTime();
    const ageMs = Date.now() - messageTime;
    return ageMs > 300000; // 5 minutes
  }

  /**
   * Helper: Get message age from timestamp
   */
  private getMessageAge(message: any): number {
    if (!message.timestamp) return Infinity;
    const messageTime = new Date(message.timestamp).getTime();
    return Date.now() - messageTime;
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
