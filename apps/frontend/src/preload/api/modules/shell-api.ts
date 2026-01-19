import { IPC_CHANNELS } from '../../../shared/constants';
import { invokeIpc } from './ipc-utils';
import type { IPCResult } from '../../../shared/types';

/**
 * Shell Operations API
 */
export interface ShellAPI {
  openExternal: (url: string) => Promise<void>;
  openTerminal: (dirPath: string) => Promise<IPCResult<void>>;
  /** Open user's preferred terminal with a command. Optionally cd to a directory first. */
  openTerminalWithCommand: (command: string, cwd?: string) => Promise<IPCResult<void>>;
}

/**
 * Creates the Shell Operations API implementation
 */
export const createShellAPI = (): ShellAPI => ({
  openExternal: (url: string): Promise<void> =>
    invokeIpc(IPC_CHANNELS.SHELL_OPEN_EXTERNAL, url),
  openTerminal: (dirPath: string): Promise<IPCResult<void>> =>
    invokeIpc(IPC_CHANNELS.SHELL_OPEN_TERMINAL, dirPath),
  openTerminalWithCommand: (command: string, cwd?: string): Promise<IPCResult<void>> =>
    invokeIpc(IPC_CHANNELS.SHELL_OPEN_TERMINAL_WITH_COMMAND, command, cwd)
});
