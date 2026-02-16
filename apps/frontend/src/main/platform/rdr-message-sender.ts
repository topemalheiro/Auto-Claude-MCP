/**
 * Platform-agnostic RDR Message Sender
 *
 * Provides configurable message sending to Master LLM (Claude Code, Cursor, etc.)
 * Supports custom command templates with variable substitution or platform-specific defaults.
 */

import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { exec } from 'child_process';
import { isWindows } from './index';

export interface SendMessageResult {
  success: boolean;
  error?: string;
}

/**
 * Send RDR message to Master LLM using custom template or platform default
 *
 * @param identifier - Window identifier (PID or title pattern)
 * @param message - RDR message to send
 * @param customTemplate - Optional custom command template with {{variables}}
 * @returns Promise with success/error result
 */
export async function sendRdrMessage(
  identifier: string | number,
  message: string,
  customTemplate?: string
): Promise<SendMessageResult> {
  if (!message) {
    return { success: false, error: 'Message cannot be empty' };
  }

  // Write message to temp file (always, for security and compatibility)
  const messagePath = path.join(os.tmpdir(), `rdr-message-${Date.now()}.txt`);
  let scriptPath: string | null = null;

  try {
    await fs.promises.writeFile(messagePath, message, 'utf8');

    // If custom template provided, use it
    if (customTemplate && customTemplate.trim() !== '') {
      const command = substituteVariables(customTemplate, {
        message: escapeForShell(message),
        messagePath,
        identifier: identifier.toString(),
        scriptPath: scriptPath || '' // May not be used in custom template
      });

      console.log('[RDR Sender] Using custom template:', customTemplate);
      const result = await executeCommand(command);

      // Clean up temp file
      await fs.promises.unlink(messagePath).catch(() => {});

      return result;
    }

    // Otherwise, use platform-specific default
    console.log('[RDR Sender] Using platform default');
    const result = await sendWithPlatformDefault(identifier, message, messagePath);

    // Clean up temp file (platform default may have already cleaned it)
    await fs.promises.unlink(messagePath).catch(() => {});

    return result;
  } catch (error) {
    // Clean up temp files on error
    await fs.promises.unlink(messagePath).catch(() => {});
    if (scriptPath) {
      await fs.promises.unlink(scriptPath).catch(() => {});
    }

    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error('[RDR Sender] Error sending message:', errorMessage);
    return { success: false, error: errorMessage };
  }
}

/**
 * Send message using platform-specific default method
 */
async function sendWithPlatformDefault(
  identifier: string | number,
  message: string,
  messagePath: string
): Promise<SendMessageResult> {
  if (isWindows()) {
    // Use Windows PowerShell clipboard method (existing implementation)
    const { sendMessageToWindow } = await import('./windows/window-manager');
    return sendMessageToWindow(identifier, message);
  } else {
    // Unix (macOS/Linux): Try ccli first, then fall back to file-based
    const template = 'ccli --message "$(cat \'{{messagePath}}\')"';
    const command = substituteVariables(template, {
      message: escapeForShell(message),
      messagePath,
      identifier: identifier.toString(),
      scriptPath: ''
    });

    console.log('[RDR Sender] Unix default: ccli command');
    return executeCommand(command);
  }
}

/**
 * Substitute template variables with actual values
 *
 * Supported variables:
 * - {{message}} - Escaped message text
 * - {{messagePath}} - Absolute path to temp file with message
 * - {{identifier}} - Window identifier (PID or title)
 * - {{scriptPath}} - Path to generated script (Windows only)
 */
function substituteVariables(
  template: string,
  vars: Record<string, string>
): string {
  return template.replace(/\{\{(\w+)\}\}/g, (match, key) => {
    return vars[key] ?? match;
  });
}

/**
 * Escape message for shell command line
 * Handles quotes, newlines, and special characters
 */
function escapeForShell(message: string): string {
  // Escape single quotes by replacing ' with '\''
  // This works in bash: 'can'\''t' becomes "can't"
  return message.replace(/'/g, "'\\''");
}

/**
 * Execute shell command and return result
 */
function executeCommand(command: string): Promise<SendMessageResult> {
  return new Promise((resolve) => {
    console.log('[RDR Sender] Executing command:', command);

    exec(
      command,
      {
        timeout: 10000,
        windowsHide: true
      },
      (error, stdout, stderr) => {
        if (error) {
          console.error('[RDR Sender] Command failed:', error.message);
          console.error('[RDR Sender] stderr:', stderr);
          resolve({
            success: false,
            error: stderr || error.message
          });
        } else {
          console.log('[RDR Sender] Command succeeded');
          console.log('[RDR Sender] stdout:', stdout);
          resolve({ success: true });
        }
      }
    );
  });
}
