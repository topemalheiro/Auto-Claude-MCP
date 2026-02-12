/**
 * Electron Compatibility Layer
 *
 * Provides fallback implementations when running outside Electron context
 * (e.g., MCP server running as standalone Node.js process)
 */

// Check if we're running in Electron context
// Use process.type which is only set in Electron (undefined in Node.js)
const isElectronContext = typeof process !== 'undefined' &&
                         typeof (process as any).type === 'string' &&
                         ['browser', 'renderer', 'worker'].includes((process as any).type);

let electronApp: any = null;

// Only try to load electron if we're actually in Electron context
if (isElectronContext) {
  try {
    const electron = require('electron');
    electronApp = electron.app;
  } catch (error) {
    console.warn('[ElectronCompat] Failed to load electron module:', error);
    electronApp = null;
  }
}

// Fallback app implementation for non-Electron contexts
const fallbackApp = {
  getPath(name: string): string {
    // Provide fallback paths for MCP server
    // CRITICAL: userData must match Electron's actual path so MCP server
    // and Electron app share the same project store (same UUIDs).
    // Electron uses: {APPDATA|~/Library/Application Support|~/.config}/auto-claude-ui
    const homedir = require('os').homedir();
    const pathModule = require('path');
    switch (name) {
      case 'userData':
        if (process.platform === 'win32') {
          return pathModule.join(process.env.APPDATA || pathModule.join(homedir, 'AppData', 'Roaming'), 'auto-claude-ui');
        } else if (process.platform === 'darwin') {
          return pathModule.join(homedir, 'Library', 'Application Support', 'auto-claude-ui');
        } else {
          return pathModule.join(homedir, '.config', 'auto-claude-ui');
        }
      case 'home':
        return homedir;
      default:
        return homedir;
    }
  },
  isPackaged: false,
  getVersion(): string {
    try {
      const packageJson = require('../../package.json');
      return packageJson.version;
    } catch {
      return '0.0.0';
    }
  }
};

// Export app with fallback
export const app = electronApp || fallbackApp;

// Export isElectronContext for conditional logic
export const isElectron = isElectronContext;
