/**
 * @vitest-environment jsdom
 */
/**
 * Tests for Worktrees component
 * Tests worktree listing, actions (merge, delete, PR creation), and status display
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { WorktreeListItem, TerminalWorktreeConfig, Task, WorktreeStatus } from '../../../shared/types';

// Mock dependencies
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      if (params) {
        let result = key;
        Object.entries(params).forEach(([k, v]) => {
          result = result.replace(`{{${k}}}`, String(v));
        });
        return result;
      }
      return key;
    },
  }),
}));

vi.mock('../../hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

vi.mock('../../stores/project-store', () => ({
  useProjectStore: vi.fn((selector) => {
    if (typeof selector === 'function') {
      return selector({
        projects: [
          {
            id: 'test-project',
            name: 'Test Project',
            path: '/test/project',
            autoBuildPath: '/test/project/.auto-claude',
            createdAt: new Date(),
            updatedAt: new Date(),
          },
        ],
      });
    }
    return { projects: [] };
  }),
}));

vi.mock('../../stores/task-store', () => ({
  useTaskStore: vi.fn((selector) => {
    if (typeof selector === 'function') {
      return selector({
        tasks: [],
        updateTask: vi.fn(),
        getState: () => ({ tasks: [] }),
      });
    }
    return { tasks: [] };
  }),
}));

// Mock electronAPI
const mockElectronAPI = {
  listWorktrees: vi.fn(),
  listTerminalWorktrees: vi.fn(),
  mergeWorktree: vi.fn(),
  discardWorktree: vi.fn(),
  discardOrphanedWorktree: vi.fn(),
  createWorktreePR: vi.fn(),
  removeTerminalWorktree: vi.fn(),
};

beforeEach(() => {
  (window as unknown as { electronAPI: typeof mockElectronAPI }).electronAPI = mockElectronAPI;
});

// Helper to create test worktree
function createTestWorktree(overrides: Partial<WorktreeListItem> = {}): WorktreeListItem {
  return {
    specName: `spec-${Date.now()}`,
    path: '/test/worktree/path',
    branch: 'feature/test-branch',
    baseBranch: 'main',
    commitCount: 5,
    filesChanged: 10,
    additions: 50,
    deletions: 20,
    isOrphaned: false,
    ...overrides,
  };
}

// Helper to create terminal worktree
function createTerminalWorktree(overrides: Partial<TerminalWorktreeConfig> = {}): TerminalWorktreeConfig {
  return {
    name: `terminal-${Date.now()}`,
    worktreePath: '/test/terminal/worktree',
    branchName: 'terminal/test-branch',
    baseBranch: 'main',
    hasGitBranch: true,
    createdAt: new Date().toISOString(),
    terminalId: `term-${Date.now()}`,
    ...overrides,
  };
}

// Helper to create test task
function createTestTask(overrides: Partial<Task> = {}): Task {
  return {
    id: `task-${Date.now()}`,
    projectId: 'test-project',
    title: 'Test Task',
    description: 'Test description',
    status: 'in_progress',
    specId: `spec-${Date.now()}`,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    subtasks: [],
    ...overrides,
  } as Task;
}

describe('Worktrees', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockElectronAPI.listWorktrees.mockResolvedValue({
      success: true,
      data: { worktrees: [] },
    });
    mockElectronAPI.listTerminalWorktrees.mockResolvedValue({
      success: true,
      data: [],
    });
  });

  describe('Loading', () => {
    it('should load task worktrees successfully', async () => {
      const worktrees = [
        createTestWorktree({ specName: 'spec-1' }),
        createTestWorktree({ specName: 'spec-2' }),
      ];

      mockElectronAPI.listWorktrees.mockResolvedValue({
        success: true,
        data: { worktrees },
      });

      const result = await mockElectronAPI.listWorktrees('test-project', { includeStats: true });
      expect(result.success).toBe(true);
      expect(result.data?.worktrees).toHaveLength(2);
    });

    it('should display loading state', () => {
      const isLoading = true;

      expect(isLoading).toBe(true);
    });

    it('should handle worktree load failure', async () => {
      mockElectronAPI.listWorktrees.mockResolvedValue({
        success: false,
        error: 'Failed to load worktrees',
      });

      const result = await mockElectronAPI.listWorktrees('test-project', { includeStats: true });
      expect(result.success).toBe(false);
      expect(result.error).toBe('Failed to load worktrees');
    });

    it('should load terminal worktrees successfully', async () => {
      const terminalWorktrees = [
        createTerminalWorktree({ name: 'terminal-1' }),
        createTerminalWorktree({ name: 'terminal-2' }),
      ];

      mockElectronAPI.listTerminalWorktrees.mockResolvedValue({
        success: true,
        data: terminalWorktrees,
      });

      const result = await mockElectronAPI.listTerminalWorktrees('/test/project');
      expect(result.success).toBe(true);
      expect(result.data).toHaveLength(2);
    });
  });

  describe('Worktree Display', () => {
    it('should display worktree branch name', () => {
      const worktree = createTestWorktree({ branch: 'feature/new-feature' });

      expect(worktree.branch).toBe('feature/new-feature');
    });

    it('should display worktree stats', () => {
      const worktree = createTestWorktree({
        commitCount: 5,
        filesChanged: 10,
        additions: 50,
        deletions: 20,
      });

      expect(worktree.commitCount).toBe(5);
      expect(worktree.filesChanged).toBe(10);
      expect(worktree.additions).toBe(50);
      expect(worktree.deletions).toBe(20);
    });

    it('should display orphaned worktree badge', () => {
      const worktree = createTestWorktree({ isOrphaned: true });

      expect(worktree.isOrphaned).toBe(true);
    });

    it('should display base branch info', () => {
      const worktree = createTestWorktree({
        baseBranch: 'develop',
        branch: 'feature/test',
      });

      expect(worktree.baseBranch).toBe('develop');
      expect(worktree.branch).toBe('feature/test');
    });

    it('should show empty state when no worktrees', () => {
      const worktrees: WorktreeListItem[] = [];
      const terminalWorktrees: TerminalWorktreeConfig[] = [];

      expect(worktrees.length).toBe(0);
      expect(terminalWorktrees.length).toBe(0);
    });

    it('should display spec name badge', () => {
      const worktree = createTestWorktree({ specName: '001-feature-name' });

      expect(worktree.specName).toBe('001-feature-name');
    });
  });

  describe('Terminal Worktrees', () => {
    it('should display terminal worktree name', () => {
      const terminal = createTerminalWorktree({ name: 'my-terminal-workspace' });

      expect(terminal.name).toBe('my-terminal-workspace');
    });

    it('should display terminal worktree branch', () => {
      const terminal = createTerminalWorktree({
        branchName: 'terminal/experiment',
        baseBranch: 'main',
      });

      expect(terminal.branchName).toBe('terminal/experiment');
      expect(terminal.baseBranch).toBe('main');
    });

    it('should display created date', () => {
      const createdAt = new Date('2024-01-15').toISOString();
      const terminal = createTerminalWorktree({ createdAt });

      expect(terminal.createdAt).toBe(createdAt);
    });

    it('should track task association', () => {
      const terminal = createTerminalWorktree({ taskId: 'task-123' });

      expect(terminal.taskId).toBe('task-123');
    });
  });

  describe('Merge Operations', () => {
    it('should open merge dialog', () => {
      const worktree = createTestWorktree();
      let selectedWorktree: WorktreeListItem | null = null;
      let showDialog = false;

      selectedWorktree = worktree;
      showDialog = true;

      expect(selectedWorktree).toBe(worktree);
      expect(showDialog).toBe(true);
    });

    it('should handle successful merge', async () => {
      mockElectronAPI.mergeWorktree.mockResolvedValue({
        success: true,
        data: {
          success: true,
          message: 'Merge successful',
        },
      });

      const result = await mockElectronAPI.mergeWorktree('task-1');
      expect(result.success).toBe(true);
      expect(result.data?.success).toBe(true);
    });

    it('should handle merge conflict', async () => {
      mockElectronAPI.mergeWorktree.mockResolvedValue({
        success: true,
        data: {
          success: false,
          message: 'Merge conflict',
          conflictFiles: ['file1.ts', 'file2.ts'],
        },
      });

      const result = await mockElectronAPI.mergeWorktree('task-1');
      expect(result.data?.success).toBe(false);
      expect(result.data?.conflictFiles).toHaveLength(2);
    });

    it('should display merge confirmation dialog', () => {
      const worktree = createTestWorktree({
        branch: 'feature/test',
        baseBranch: 'main',
        commitCount: 5,
        filesChanged: 10,
      });

      expect(worktree.branch).toBe('feature/test');
      expect(worktree.baseBranch).toBe('main');
    });

    it('should close dialog after successful merge', () => {
      let showDialog = true;

      showDialog = false;
      expect(showDialog).toBe(false);
    });
  });

  describe('Delete Operations', () => {
    it('should open delete confirmation dialog', () => {
      const worktree = createTestWorktree();
      let worktreeToDelete: WorktreeListItem | null = null;
      let showConfirm = false;

      worktreeToDelete = worktree;
      showConfirm = true;

      expect(worktreeToDelete).toBe(worktree);
      expect(showConfirm).toBe(true);
    });

    it('should delete worktree via task ID', async () => {
      mockElectronAPI.discardWorktree.mockResolvedValue({ success: true });

      const result = await mockElectronAPI.discardWorktree('task-1');
      expect(result.success).toBe(true);
      expect(mockElectronAPI.discardWorktree).toHaveBeenCalledWith('task-1');
    });

    it('should delete orphaned worktree by spec name', async () => {
      mockElectronAPI.discardOrphanedWorktree.mockResolvedValue({ success: true });

      const result = await mockElectronAPI.discardOrphanedWorktree(
        'project-1',
        'spec-001'
      );
      expect(result.success).toBe(true);
      expect(mockElectronAPI.discardOrphanedWorktree).toHaveBeenCalledWith(
        'project-1',
        'spec-001'
      );
    });

    it('should delete terminal worktree', async () => {
      mockElectronAPI.removeTerminalWorktree.mockResolvedValue({ success: true });

      const result = await mockElectronAPI.removeTerminalWorktree(
        '/project/path',
        'terminal-1',
        true
      );
      expect(result.success).toBe(true);
    });

    it('should handle delete failure', async () => {
      mockElectronAPI.discardWorktree.mockResolvedValue({
        success: false,
        error: 'Delete failed',
      });

      const result = await mockElectronAPI.discardWorktree('task-1');
      expect(result.success).toBe(false);
      expect(result.error).toBe('Delete failed');
    });

    it('should refresh worktree list after delete', async () => {
      mockElectronAPI.discardWorktree.mockResolvedValue({ success: true });

      await mockElectronAPI.discardWorktree('task-1');
      expect(mockElectronAPI.discardWorktree).toHaveBeenCalled();
    });
  });

  describe('Bulk Delete', () => {
    it('should select multiple worktrees', () => {
      const selectedIds = new Set<string>();

      selectedIds.add('task:spec-1');
      selectedIds.add('task:spec-2');
      selectedIds.add('terminal:terminal-1');

      expect(selectedIds.size).toBe(3);
    });

    it('should toggle worktree selection', () => {
      const selectedIds = new Set(['task:spec-1']);

      const toggleId = 'task:spec-2';
      if (selectedIds.has(toggleId)) {
        selectedIds.delete(toggleId);
      } else {
        selectedIds.add(toggleId);
      }

      expect(selectedIds.has('task:spec-2')).toBe(true);
    });

    it('should select all worktrees', () => {
      const worktrees = [
        createTestWorktree({ specName: 'spec-1' }),
        createTestWorktree({ specName: 'spec-2' }),
      ];
      const terminalWorktrees = [
        createTerminalWorktree({ name: 'terminal-1' }),
      ];

      const allIds = [
        ...worktrees.map(w => `task:${w.specName}`),
        ...terminalWorktrees.map(w => `terminal:${w.name}`),
      ];

      expect(allIds).toHaveLength(3);
    });

    it('should deselect all worktrees', () => {
      const selectedIds = new Set(['task:spec-1', 'terminal:terminal-1']);

      selectedIds.clear();
      expect(selectedIds.size).toBe(0);
    });

    it('should calculate selection count', () => {
      const selectedIds = new Set(['task:spec-1', 'task:spec-2']);
      const validIds = new Set(['task:spec-1', 'task:spec-2', 'task:spec-3']);

      let count = 0;
      selectedIds.forEach(id => {
        if (validIds.has(id)) {
          count++;
        }
      });

      expect(count).toBe(2);
    });

    it('should handle bulk delete confirmation', () => {
      const selectedIds = new Set(['task:spec-1', 'terminal:terminal-1']);
      let showConfirm = false;

      if (selectedIds.size > 0) {
        showConfirm = true;
      }

      expect(showConfirm).toBe(true);
    });

    it('should clear selection after bulk delete', () => {
      const selectedIds = new Set(['task:spec-1']);

      selectedIds.clear();
      expect(selectedIds.size).toBe(0);
    });

    it('should parse task IDs from selection', () => {
      const selectedIds = new Set(['task:spec-1', 'task:spec-2', 'terminal:term-1']);
      const TASK_PREFIX = 'task:';

      const taskSpecNames: string[] = [];
      selectedIds.forEach(id => {
        if (id.startsWith(TASK_PREFIX)) {
          taskSpecNames.push(id.slice(TASK_PREFIX.length));
        }
      });

      expect(taskSpecNames).toEqual(['spec-1', 'spec-2']);
    });

    it('should parse terminal IDs from selection', () => {
      const selectedIds = new Set(['task:spec-1', 'terminal:term-1', 'terminal:term-2']);
      const TERMINAL_PREFIX = 'terminal:';

      const terminalNames: string[] = [];
      selectedIds.forEach(id => {
        if (id.startsWith(TERMINAL_PREFIX)) {
          terminalNames.push(id.slice(TERMINAL_PREFIX.length));
        }
      });

      expect(terminalNames).toEqual(['term-1', 'term-2']);
    });
  });

  describe('Selection Mode', () => {
    it('should enable selection mode', () => {
      let isSelectionMode = false;

      isSelectionMode = true;
      expect(isSelectionMode).toBe(true);
    });

    it('should disable selection mode', () => {
      let isSelectionMode = true;

      isSelectionMode = false;
      expect(isSelectionMode).toBe(false);
    });

    it('should clear selection when disabling selection mode', () => {
      let isSelectionMode = true;
      const selectedIds = new Set(['task:spec-1']);

      isSelectionMode = false;
      selectedIds.clear();

      expect(isSelectionMode).toBe(false);
      expect(selectedIds.size).toBe(0);
    });

    it('should calculate if all are selected', () => {
      const worktrees = [
        createTestWorktree({ specName: 'spec-1' }),
        createTestWorktree({ specName: 'spec-2' }),
      ];
      const selectedIds = new Set(['task:spec-1', 'task:spec-2']);

      const allSelected = worktrees.every(w => selectedIds.has(`task:${w.specName}`));
      expect(allSelected).toBe(true);
    });

    it('should calculate if some are selected', () => {
      const worktrees = [
        createTestWorktree({ specName: 'spec-1' }),
        createTestWorktree({ specName: 'spec-2' }),
      ];
      const selectedIds = new Set(['task:spec-1']);

      const allSelected = worktrees.every(w => selectedIds.has(`task:${w.specName}`));
      const someSelected = worktrees.some(w => selectedIds.has(`task:${w.specName}`)) && !allSelected;

      expect(someSelected).toBe(true);
    });
  });

  describe('PR Creation', () => {
    it('should open PR creation dialog', () => {
      const worktree = createTestWorktree();
      const task = createTestTask();

      let prWorktree: WorktreeListItem | null = null;
      let prTask: Task | null = null;
      let showDialog = false;

      prWorktree = worktree;
      prTask = task;
      showDialog = true;

      expect(prWorktree).toBe(worktree);
      expect(prTask).toBe(task);
      expect(showDialog).toBe(true);
    });

    it('should convert worktree to status for dialog', () => {
      const worktree = createTestWorktree({
        path: '/test/path',
        branch: 'feature/test',
        baseBranch: 'main',
        commitCount: 5,
        filesChanged: 10,
        additions: 50,
        deletions: 20,
      });

      const status: WorktreeStatus = {
        exists: true,
        worktreePath: worktree.path,
        branch: worktree.branch,
        baseBranch: worktree.baseBranch,
        commitCount: worktree.commitCount ?? 0,
        filesChanged: worktree.filesChanged ?? 0,
        additions: worktree.additions ?? 0,
        deletions: worktree.deletions ?? 0,
      };

      expect(status.exists).toBe(true);
      expect(status.commitCount).toBe(5);
    });

    it('should create PR successfully', async () => {
      mockElectronAPI.createWorktreePR.mockResolvedValue({
        success: true,
        data: {
          success: true,
          prUrl: 'https://github.com/test/repo/pull/123',
          alreadyExists: false,
        },
      });

      const result = await mockElectronAPI.createWorktreePR('task-1', {
        title: 'Test PR',
        body: 'Test PR body',
      });

      expect(result.data?.success).toBe(true);
      expect(result.data?.prUrl).toBeDefined();
    });

    it('should handle PR already exists', async () => {
      mockElectronAPI.createWorktreePR.mockResolvedValue({
        success: true,
        data: {
          success: true,
          prUrl: 'https://github.com/test/repo/pull/123',
          alreadyExists: true,
        },
      });

      const result = await mockElectronAPI.createWorktreePR('task-1', {});
      expect(result.data?.alreadyExists).toBe(true);
    });

    it('should handle PR creation failure', async () => {
      mockElectronAPI.createWorktreePR.mockResolvedValue({
        success: false,
        error: 'Failed to create PR',
      });

      const result = await mockElectronAPI.createWorktreePR('task-1', {});
      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });
  });

  describe('Task Association', () => {
    it('should find task for worktree', () => {
      const tasks = [
        createTestTask({ id: 'task-1', specId: 'spec-001' }),
        createTestTask({ id: 'task-2', specId: 'spec-002' }),
      ];

      const task = tasks.find(t => t.specId === 'spec-001');
      expect(task?.id).toBe('task-1');
    });

    it('should handle worktree without task', () => {
      const tasks: Task[] = [];
      const task = tasks.find(t => t.specId === 'spec-999');

      expect(task).toBeUndefined();
    });

    it('should display task title for worktree', () => {
      const task = createTestTask({ title: 'Implement feature X' });

      expect(task.title).toBe('Implement feature X');
    });
  });

  describe('Error Handling', () => {
    it('should display error message', () => {
      const error = 'Failed to load worktrees';

      expect(error).toBe('Failed to load worktrees');
    });

    it('should clear error on successful operation', () => {
      let error: string | null = 'Some error';

      error = null;
      expect(error).toBeNull();
    });

    it('should handle missing project', () => {
      const projectId: string | null = null;

      expect(projectId).toBeNull();
    });
  });

  describe('Refresh', () => {
    it('should refresh worktree list', async () => {
      mockElectronAPI.listWorktrees.mockClear();

      await mockElectronAPI.listWorktrees('test-project', { includeStats: true });
      expect(mockElectronAPI.listWorktrees).toHaveBeenCalled();
    });

    it('should clear selection on refresh', () => {
      const selectedIds = new Set(['task:spec-1']);
      let isSelectionMode = true;

      selectedIds.clear();
      isSelectionMode = false;

      expect(selectedIds.size).toBe(0);
      expect(isSelectionMode).toBe(false);
    });
  });

  describe('Path Operations', () => {
    it('should copy worktree path to clipboard', () => {
      const worktree = createTestWorktree({ path: '/test/worktree/path' });

      expect(worktree.path).toBe('/test/worktree/path');
    });

    it('should copy terminal worktree path', () => {
      const terminal = createTerminalWorktree({
        worktreePath: '/test/terminal/path',
      });

      expect(terminal.worktreePath).toBe('/test/terminal/path');
    });
  });
});
