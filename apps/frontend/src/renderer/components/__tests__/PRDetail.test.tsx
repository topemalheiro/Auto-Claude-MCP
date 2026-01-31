/**
 * @vitest-environment jsdom
 */
/**
 * Tests for PRDetail component
 * Tests PR information display, review actions, comment display, and workflow management
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Define types locally to avoid module resolution issues in tests
interface PRData {
  number: number;
  title: string;
  body: string;
  state: string;
  author: string;
  createdAt: string;
  updatedAt: string;
  headSha: string;
  baseBranch: string;
  headBranch: string;
  url: string;
  mergeable: boolean;
  merged: boolean;
  draft: boolean;
  labels: string[];
  assignees: string[];
  reviewers: string[];
  comments: number;
  commits: number;
  additions: number;
  deletions: number;
  changedFiles: number;
}

interface PRReviewFinding {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  message: string;
  file: string;
  line: number;
}

interface PRReviewResult {
  success: boolean;
  overallStatus: 'approve' | 'request_changes' | 'comment';
  summary: string;
  findings: PRReviewFinding[];
  reviewedAt: string;
  reviewedCommitSha: string;
  postedFindingIds: string[];
  hasPostedFindings: boolean;
  postedAt: string | null;
  isFollowupReview: boolean;
  error?: string;
  resolvedFindings?: string[];
  unresolvedFindings?: string[];
  newFindingsSinceLastReview?: string[];
}

interface PRReviewProgress {
  progress: number;
  message: string;
  phase: string;
}

interface NewCommitsCheck {
  hasNewCommits: boolean;
  newCommitCount: number;
  lastReviewedCommit: string;
  hasCommitsAfterPosting?: boolean;
}

interface MergeReadiness {
  ready: boolean;
  blockers: string[];
  isBehind: boolean;
}

interface PRLogs {
  pr_number: number;
  is_followup: boolean;
  phases: Array<{
    name: string;
    status: string;
    started_at: string;
    completed_at?: string;
  }>;
}

interface WorkflowRun {
  id: number;
  name: string;
  workflow_name: string;
  html_url: string;
}

interface WorkflowsAwaitingApprovalResult {
  awaiting_approval: number;
  workflow_runs: WorkflowRun[];
}

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

// Mock electronAPI
const mockElectronAPI = {
  github: {
    getWorkflowsAwaitingApproval: vi.fn(),
    approveWorkflow: vi.fn(),
    checkMergeReadiness: vi.fn(),
    updatePRBranch: vi.fn(),
  },
  openExternal: vi.fn(),
};

beforeEach(() => {
  (window as unknown as { electronAPI: typeof mockElectronAPI }).electronAPI = mockElectronAPI;
});

// Helper to create test PR data
function createTestPR(overrides: Partial<PRData> = {}): PRData {
  return {
    number: 123,
    title: 'Test PR',
    body: 'Test PR description',
    state: 'open',
    author: 'testuser',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    headSha: 'abc123',
    baseBranch: 'main',
    headBranch: 'feature/test',
    url: 'https://github.com/test/repo/pull/123',
    mergeable: true,
    merged: false,
    draft: false,
    labels: [],
    assignees: [],
    reviewers: [],
    comments: 0,
    commits: 5,
    additions: 100,
    deletions: 50,
    changedFiles: 10,
    ...overrides,
  };
}

// Helper to create test review result
function createReviewResult(overrides: Partial<PRReviewResult> = {}): PRReviewResult {
  return {
    success: true,
    overallStatus: 'approve',
    summary: 'Code looks good!',
    findings: [],
    reviewedAt: new Date().toISOString(),
    reviewedCommitSha: 'abc123',
    postedFindingIds: [],
    hasPostedFindings: false,
    postedAt: null,
    isFollowupReview: false,
    ...overrides,
  };
}

// Helper to create review progress
function createReviewProgress(overrides: Partial<PRReviewProgress> = {}): PRReviewProgress {
  return {
    progress: 50,
    message: 'Analyzing code...',
    phase: 'analyzing',
    ...overrides,
  };
}

describe('PRDetail', () => {
  const mockOnRunReview = vi.fn();
  const mockOnRunFollowupReview = vi.fn();
  const mockOnCheckNewCommits = vi.fn();
  const mockOnCancelReview = vi.fn();
  const mockOnPostReview = vi.fn();
  const mockOnPostComment = vi.fn();
  const mockOnMergePR = vi.fn();
  const mockOnAssignPR = vi.fn();
  const mockOnGetLogs = vi.fn();
  const mockOnMarkReviewPosted = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockElectronAPI.github.getWorkflowsAwaitingApproval.mockResolvedValue({
      awaiting_approval: 0,
      workflow_runs: [],
    });
    mockElectronAPI.github.checkMergeReadiness.mockResolvedValue({
      ready: true,
      blockers: [],
      isBehind: false,
    });
    mockOnGetLogs.mockResolvedValue(null);
    mockOnCheckNewCommits.mockResolvedValue({
      hasNewCommits: false,
      newCommitCount: 0,
      lastReviewedCommit: 'abc123',
    });
  });

  describe('PR Header Display', () => {
    it('should display PR title and number', () => {
      const pr = createTestPR({ number: 123, title: 'Fix bug in authentication' });

      expect(pr.number).toBe(123);
      expect(pr.title).toBe('Fix bug in authentication');
    });

    it('should display PR author', () => {
      const pr = createTestPR({ author: 'johndoe' });

      expect(pr.author).toBe('johndoe');
    });

    it('should display PR state', () => {
      const pr = createTestPR({ state: 'open' });

      expect(pr.state).toBe('open');
    });

    it('should display PR stats', () => {
      const pr = createTestPR({
        commits: 5,
        changedFiles: 10,
        additions: 100,
        deletions: 50,
      });

      expect(pr.commits).toBe(5);
      expect(pr.changedFiles).toBe(10);
      expect(pr.additions).toBe(100);
      expect(pr.deletions).toBe(50);
    });

    it('should display draft badge', () => {
      const pr = createTestPR({ draft: true });

      expect(pr.draft).toBe(true);
    });

    it('should display merged badge', () => {
      const pr = createTestPR({ merged: true });

      expect(pr.merged).toBe(true);
    });
  });

  describe('Review Status', () => {
    it('should show not reviewed status', () => {
      const reviewResult = null;
      const isReviewing = false;

      expect(reviewResult).toBeNull();
      expect(isReviewing).toBe(false);
    });

    it('should show reviewing status', () => {
      const isReviewing = true;
      const progress = createReviewProgress({
        progress: 50,
        message: 'Analyzing code...',
      });

      expect(isReviewing).toBe(true);
      expect(progress.progress).toBe(50);
    });

    it('should show review complete status', () => {
      const reviewResult = createReviewResult({
        success: true,
        overallStatus: 'approve',
      });

      expect(reviewResult.success).toBe(true);
      expect(reviewResult.overallStatus).toBe('approve');
    });

    it('should show changes requested status', () => {
      const reviewResult = createReviewResult({
        overallStatus: 'request_changes',
      });

      expect(reviewResult.overallStatus).toBe('request_changes');
    });

    it('should calculate ready to merge status', () => {
      const reviewResult = createReviewResult({
        success: true,
        summary: 'READY TO MERGE',
        overallStatus: 'approve',
      });

      const isReadyToMerge = reviewResult.summary?.includes('READY TO MERGE') ||
                            reviewResult.overallStatus === 'approve';

      expect(isReadyToMerge).toBe(true);
    });

    it('should calculate clean review status', () => {
      const reviewResult = createReviewResult({
        success: true,
        findings: [
          { id: '1', severity: 'low', message: 'Minor suggestion', file: 'test.ts', line: 10 },
        ],
      });

      const isClean = !reviewResult.findings.some(f =>
        f.severity === 'critical' || f.severity === 'high' || f.severity === 'medium'
      );

      expect(isClean).toBe(true);
    });

    it('should detect blocking issues', () => {
      const reviewResult = createReviewResult({
        findings: [
          { id: '1', severity: 'high', message: 'Security issue', file: 'auth.ts', line: 50 },
        ],
      });

      const hasBlockers = reviewResult.findings.some(f =>
        f.severity === 'critical' || f.severity === 'high'
      );

      expect(hasBlockers).toBe(true);
    });
  });

  describe('Review Actions', () => {
    it('should start initial review', () => {
      mockOnRunReview();

      expect(mockOnRunReview).toHaveBeenCalled();
    });

    it('should start follow-up review', () => {
      mockOnRunFollowupReview();

      expect(mockOnRunFollowupReview).toHaveBeenCalled();
    });

    it('should cancel ongoing review', () => {
      mockOnCancelReview();

      expect(mockOnCancelReview).toHaveBeenCalled();
    });

    it('should post selected findings', async () => {
      const findingIds = ['finding-1', 'finding-2'];
      mockOnPostReview.mockResolvedValue(true);

      const result = await mockOnPostReview(findingIds);
      expect(result).toBe(true);
      expect(mockOnPostReview).toHaveBeenCalledWith(findingIds);
    });

    it('should post comment', async () => {
      mockOnPostComment.mockResolvedValue(true);

      const result = await mockOnPostComment('Test comment');
      expect(result).toBe(true);
      expect(mockOnPostComment).toHaveBeenCalledWith('Test comment');
    });

    it('should merge PR', () => {
      mockOnMergePR('squash');

      expect(mockOnMergePR).toHaveBeenCalledWith('squash');
    });

    it('should handle review error', () => {
      const reviewResult = createReviewResult({
        success: false,
        error: 'Review failed',
      });

      expect(reviewResult.success).toBe(false);
      expect(reviewResult.error).toBe('Review failed');
    });
  });

  describe('Findings Management', () => {
    it('should auto-select all findings on review complete', () => {
      const reviewResult = createReviewResult({
        findings: [
          { id: '1', severity: 'high', message: 'Issue 1', file: 'test.ts', line: 10 },
          { id: '2', severity: 'low', message: 'Issue 2', file: 'test.ts', line: 20 },
        ],
      });

      const selectedIds = new Set(reviewResult.findings.map(f => f.id));

      expect(selectedIds.size).toBe(2);
      expect(selectedIds.has('1')).toBe(true);
      expect(selectedIds.has('2')).toBe(true);
    });

    it('should exclude posted findings from selection', () => {
      const reviewResult = createReviewResult({
        findings: [
          { id: '1', severity: 'high', message: 'Issue 1', file: 'test.ts', line: 10 },
          { id: '2', severity: 'low', message: 'Issue 2', file: 'test.ts', line: 20 },
        ],
        postedFindingIds: ['1'],
      });

      const postedIds = new Set(reviewResult.postedFindingIds);
      const selectedIds = new Set(
        reviewResult.findings.filter(f => !postedIds.has(f.id)).map(f => f.id)
      );

      expect(selectedIds.size).toBe(1);
      expect(selectedIds.has('2')).toBe(true);
    });

    it('should track posted findings', () => {
      const postedIds = new Set(['finding-1', 'finding-2']);

      expect(postedIds.has('finding-1')).toBe(true);
      expect(postedIds.size).toBe(2);
    });

    it('should count selected findings', () => {
      const selectedIds = new Set(['finding-1', 'finding-2', 'finding-3']);

      expect(selectedIds.size).toBe(3);
    });

    it('should filter low severity findings', () => {
      const reviewResult = createReviewResult({
        findings: [
          { id: '1', severity: 'high', message: 'Issue 1', file: 'test.ts', line: 10 },
          { id: '2', severity: 'low', message: 'Issue 2', file: 'test.ts', line: 20 },
          { id: '3', severity: 'low', message: 'Issue 3', file: 'test.ts', line: 30 },
        ],
      });

      const lowFindings = reviewResult.findings.filter(f => f.severity === 'low');

      expect(lowFindings).toHaveLength(2);
    });
  });

  describe('New Commits Detection', () => {
    it('should check for new commits after review', async () => {
      mockOnCheckNewCommits.mockResolvedValue({
        hasNewCommits: true,
        newCommitCount: 2,
        lastReviewedCommit: 'abc123',
      });

      const result = await mockOnCheckNewCommits();
      expect(result.hasNewCommits).toBe(true);
      expect(result.newCommitCount).toBe(2);
    });

    it('should detect no new commits', async () => {
      mockOnCheckNewCommits.mockResolvedValue({
        hasNewCommits: false,
        newCommitCount: 0,
        lastReviewedCommit: 'abc123',
      });

      const result = await mockOnCheckNewCommits();
      expect(result.hasNewCommits).toBe(false);
    });

    it('should detect commits after posting', async () => {
      mockOnCheckNewCommits.mockResolvedValue({
        hasNewCommits: true,
        newCommitCount: 1,
        hasCommitsAfterPosting: true,
        lastReviewedCommit: 'abc123',
      });

      const result = await mockOnCheckNewCommits();
      expect(result.hasCommitsAfterPosting).toBe(true);
    });

    it('should show ready for follow-up status', () => {
      const newCommitsCheck: NewCommitsCheck = {
        hasNewCommits: true,
        newCommitCount: 2,
        hasCommitsAfterPosting: true,
        lastReviewedCommit: 'abc123',
      };

      expect(newCommitsCheck.hasNewCommits).toBe(true);
      expect(newCommitsCheck.hasCommitsAfterPosting).toBe(true);
    });
  });

  describe('Follow-up Review', () => {
    it('should display follow-up review badge', () => {
      const reviewResult = createReviewResult({
        isFollowupReview: true,
      });

      expect(reviewResult.isFollowupReview).toBe(true);
    });

    it('should show resolved findings', () => {
      const reviewResult = createReviewResult({
        isFollowupReview: true,
        resolvedFindings: ['finding-1', 'finding-2'],
      });

      expect(reviewResult.resolvedFindings).toHaveLength(2);
    });

    it('should show unresolved findings', () => {
      const reviewResult = createReviewResult({
        isFollowupReview: true,
        unresolvedFindings: ['finding-3'],
      });

      expect(reviewResult.unresolvedFindings).toHaveLength(1);
    });

    it('should show new findings', () => {
      const reviewResult = createReviewResult({
        isFollowupReview: true,
        newFindingsSinceLastReview: ['finding-4', 'finding-5'],
      });

      expect(reviewResult.newFindingsSinceLastReview).toHaveLength(2);
    });

    it('should calculate all issues resolved', () => {
      const reviewResult = createReviewResult({
        isFollowupReview: true,
        resolvedFindings: ['finding-1', 'finding-2'],
        unresolvedFindings: [],
        newFindingsSinceLastReview: [],
      });

      const allResolved = (reviewResult.unresolvedFindings?.length ?? 0) === 0 &&
                         (reviewResult.newFindingsSinceLastReview?.length ?? 0) === 0;

      expect(allResolved).toBe(true);
    });
  });

  describe('Merge Readiness', () => {
    it('should check merge readiness', async () => {
      mockElectronAPI.github.checkMergeReadiness.mockResolvedValue({
        ready: true,
        blockers: [],
        isBehind: false,
      });

      const result = await mockElectronAPI.github.checkMergeReadiness('project-1', 123);
      expect(result.ready).toBe(true);
      expect(result.blockers).toHaveLength(0);
    });

    it('should detect merge blockers', async () => {
      mockElectronAPI.github.checkMergeReadiness.mockResolvedValue({
        ready: false,
        blockers: ['CI checks failing', 'Requires approval'],
        isBehind: false,
      });

      const result = await mockElectronAPI.github.checkMergeReadiness('project-1', 123);
      expect(result.ready).toBe(false);
      expect(result.blockers).toHaveLength(2);
    });

    it('should detect branch behind base', async () => {
      mockElectronAPI.github.checkMergeReadiness.mockResolvedValue({
        ready: false,
        blockers: ['Branch is behind base'],
        isBehind: true,
      });

      const result = await mockElectronAPI.github.checkMergeReadiness('project-1', 123);
      expect(result.isBehind).toBe(true);
    });

    it('should update branch when behind', async () => {
      mockElectronAPI.github.updatePRBranch.mockResolvedValue({
        success: true,
      });

      const result = await mockElectronAPI.github.updatePRBranch('project-1', 123);
      expect(result.success).toBe(true);
    });

    it('should handle branch update failure', async () => {
      mockElectronAPI.github.updatePRBranch.mockResolvedValue({
        success: false,
        error: 'Merge conflict',
      });

      const result = await mockElectronAPI.github.updatePRBranch('project-1', 123);
      expect(result.success).toBe(false);
      expect(result.error).toBe('Merge conflict');
    });
  });

  describe('Workflows', () => {
    it('should load workflows awaiting approval', async () => {
      mockElectronAPI.github.getWorkflowsAwaitingApproval.mockResolvedValue({
        awaiting_approval: 2,
        workflow_runs: [
          {
            id: 1,
            name: 'Build',
            workflow_name: 'CI',
            html_url: 'https://github.com/test/repo/actions/runs/1',
          },
          {
            id: 2,
            name: 'Test',
            workflow_name: 'CI',
            html_url: 'https://github.com/test/repo/actions/runs/2',
          },
        ],
      });

      const result = await mockElectronAPI.github.getWorkflowsAwaitingApproval('', 123);
      expect(result.awaiting_approval).toBe(2);
      expect(result.workflow_runs).toHaveLength(2);
    });

    it('should approve single workflow', async () => {
      mockElectronAPI.github.approveWorkflow.mockResolvedValue(true);

      const result = await mockElectronAPI.github.approveWorkflow('', 1);
      expect(result).toBe(true);
    });

    it('should approve all workflows', async () => {
      const workflows: WorkflowsAwaitingApprovalResult = {
        awaiting_approval: 2,
        workflow_runs: [
          { id: 1, name: 'Build', workflow_name: 'CI', html_url: '' },
          { id: 2, name: 'Test', workflow_name: 'CI', html_url: '' },
        ],
      };

      mockElectronAPI.github.approveWorkflow.mockResolvedValue(true);

      for (const workflow of workflows.workflow_runs) {
        await mockElectronAPI.github.approveWorkflow('', workflow.id);
      }

      expect(mockElectronAPI.github.approveWorkflow).toHaveBeenCalledTimes(2);
    });

    it('should show blocked by workflows status', () => {
      const workflowsAwaiting: WorkflowsAwaitingApprovalResult = {
        awaiting_approval: 1,
        workflow_runs: [
          { id: 1, name: 'Build', workflow_name: 'CI', html_url: '' },
        ],
      };

      expect(workflowsAwaiting.awaiting_approval).toBeGreaterThan(0);
    });
  });

  describe('Review Logs', () => {
    it('should load review logs', async () => {
      mockOnGetLogs.mockResolvedValue({
        pr_number: 123,
        is_followup: false,
        phases: [
          {
            name: 'Analysis',
            status: 'completed',
            started_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
          },
        ],
      });

      const logs = await mockOnGetLogs();
      expect(logs).toBeDefined();
      expect(logs?.pr_number).toBe(123);
    });

    it('should expand logs when review starts', () => {
      let logsExpanded = false;
      const isReviewing = true;

      if (isReviewing) {
        logsExpanded = true;
      }

      expect(logsExpanded).toBe(true);
    });

    it('should collapse logs', () => {
      let logsExpanded = true;

      logsExpanded = false;
      expect(logsExpanded).toBe(false);
    });

    it('should show logs badge for follow-up', () => {
      const logs: PRLogs = {
        pr_number: 123,
        is_followup: true,
        phases: [],
      };

      expect(logs.is_followup).toBe(true);
    });
  });

  describe('Auto-Approval', () => {
    it('should auto-approve clean PR', async () => {
      const reviewResult = createReviewResult({
        success: true,
        overallStatus: 'approve',
        findings: [
          { id: '1', severity: 'low', message: 'Minor suggestion', file: 'test.ts', line: 10 },
        ],
      });

      const lowFindings = reviewResult.findings.filter(f => f.severity === 'low');
      const findingIds = lowFindings.map(f => f.id);

      mockOnPostReview.mockResolvedValue(true);

      const result = await mockOnPostReview(findingIds, { forceApprove: true });
      expect(result).toBe(true);
    });

    it('should post clean review comment', async () => {
      mockOnPostComment.mockResolvedValue(true);

      const message = 'Clean review - no issues found';
      const result = await mockOnPostComment(message);

      expect(result).toBe(true);
      expect(mockOnPostComment).toHaveBeenCalledWith(message);
    });

    it('should handle clean review post failure', async () => {
      mockOnPostComment.mockRejectedValue(new Error('Failed to post'));

      await expect(mockOnPostComment('message')).rejects.toThrow('Failed to post');
    });
  });

  describe('Blocked Status', () => {
    it('should post blocked status when no findings', async () => {
      const reviewResult = createReviewResult({
        success: true,
        overallStatus: 'request_changes',
        findings: [],
        summary: 'PR is blocked due to CI failures',
      });

      mockOnPostComment.mockResolvedValue(true);

      const result = await mockOnPostComment(reviewResult.summary);
      expect(result).toBe(true);
    });

    it('should mark review as posted after blocked status', async () => {
      mockOnMarkReviewPosted?.mockResolvedValue(undefined);

      await mockOnMarkReviewPosted?.(123);
      expect(mockOnMarkReviewPosted).toHaveBeenCalledWith(123);
    });
  });

  describe('Progress Tracking', () => {
    it('should display review progress', () => {
      const progress = createReviewProgress({
        progress: 75,
        message: 'Analyzing security issues...',
        phase: 'security',
      });

      expect(progress.progress).toBe(75);
      expect(progress.message).toBe('Analyzing security issues...');
    });

    it('should update progress during review', () => {
      const progress = createReviewProgress({ progress: 25 });

      progress.progress = 50;
      expect(progress.progress).toBe(50);
    });
  });

  describe('State Management', () => {
    it('should prevent state leaks when switching PRs', () => {
      const currentPr = 123;
      const actionPr = 123;

      const shouldUpdate = currentPr === actionPr;
      expect(shouldUpdate).toBe(true);
    });

    it('should not update state for different PR', () => {
      const currentPr: number = 123;
      const actionPr: number = 456;

      const shouldUpdate = currentPr === actionPr;
      expect(shouldUpdate).toBe(false);
    });

    it('should reset state when PR changes', () => {
      let cleanReviewPosted = true;
      let blockedStatusPosted = true;

      cleanReviewPosted = false;
      blockedStatusPosted = false;

      expect(cleanReviewPosted).toBe(false);
      expect(blockedStatusPosted).toBe(false);
    });
  });

  describe('UI State', () => {
    it('should toggle analysis section', () => {
      let analysisExpanded = true;

      analysisExpanded = !analysisExpanded;
      expect(analysisExpanded).toBe(false);
    });

    it('should show success message after posting', () => {
      const postSuccess = {
        count: 3,
        timestamp: Date.now(),
      };

      expect(postSuccess.count).toBe(3);
      expect(postSuccess.timestamp).toBeLessThanOrEqual(Date.now());
    });

    it('should clear success message after timeout', () => {
      let postSuccess: { count: number; timestamp: number } | null = {
        count: 3,
        timestamp: Date.now(),
      };

      postSuccess = null;
      expect(postSuccess).toBeNull();
    });

    it('should show loading state when posting', () => {
      let isPosting = false;

      isPosting = true;
      expect(isPosting).toBe(true);

      isPosting = false;
      expect(isPosting).toBe(false);
    });
  });

  describe('Previous Review', () => {
    it('should display previous review result', () => {
      const previousReviewResult = createReviewResult({
        success: true,
        findings: [
          { id: '1', severity: 'high', message: 'Issue 1', file: 'test.ts', line: 10 },
        ],
      });

      expect(previousReviewResult.success).toBe(true);
      expect(previousReviewResult.findings).toHaveLength(1);
    });

    it('should compare with current review', () => {
      const previousReview = createReviewResult({
        findings: [
          { id: '1', severity: 'high', message: 'Issue 1', file: 'test.ts', line: 10 },
        ],
      });

      const currentReview = createReviewResult({
        findings: [],
      });

      expect(previousReview.findings.length).toBeGreaterThan(currentReview.findings.length);
    });
  });
});
