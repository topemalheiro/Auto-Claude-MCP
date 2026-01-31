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
    const homedir = require('os').homedir();
    const pathModule = require('path');
    switch (name) {
      case 'userData':
        return pathModule.join(homedir, '.auto-claude');
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
