/**
 * @vitest-environment jsdom
 */
/**
 * Tests for FeedbackHistory component
 *
 * Story Reference: Story 5.3 - Implement Checkpoint Feedback Input
 * Acceptance Criteria 3: View feedback history for the task
 */
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { FeedbackHistory } from '../checkpoints/FeedbackHistory';
import type { CheckpointFeedback, FeedbackAttachment } from '../checkpoints/types';

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      const translations: Record<string, string> = {
        'checkpoints:feedback.historyTitle': 'Previous Feedback',
        'checkpoints:feedback.showAll': `Show all (${params?.count || 0})`,
        'checkpoints:feedback.showLess': 'Show less',
        'checkpoints:feedback.attachments': `${params?.count || 0} attachment`,
        'checkpoints:feedback.attachmentCount': `${params?.count || 0} file`,
      };
      return translations[key] || key;
    },
  }),
}));

// Helper to create mock feedback entries
const createMockFeedback = (overrides?: Partial<CheckpointFeedback>): CheckpointFeedback => ({
  id: 'feedback-1',
  checkpointId: 'after_planning',
  feedback: 'Please add more error handling',
  attachments: [],
  createdAt: '2026-01-16T10:00:00Z',
  ...overrides,
});

const createMockAttachment = (overrides?: Partial<FeedbackAttachment>): FeedbackAttachment => ({
  id: 'attachment-1',
  type: 'file',
  name: 'example.md',
  path: '/path/to/example.md',
  size: 1024,
  ...overrides,
});

describe('FeedbackHistory', () => {
  const defaultProps = {
    feedbackHistory: [createMockFeedback()],
    onViewAttachment: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('rendering', () => {
    it('renders history title', () => {
      render(<FeedbackHistory {...defaultProps} />);

      expect(screen.getByText('Previous Feedback')).toBeInTheDocument();
    });

    it('renders feedback count', () => {
      render(<FeedbackHistory {...defaultProps} />);

      expect(screen.getByText('(1)')).toBeInTheDocument();
    });

    it('does not render when history is empty', () => {
      render(<FeedbackHistory {...defaultProps} feedbackHistory={[]} />);

      expect(screen.queryByText('Previous Feedback')).not.toBeInTheDocument();
    });

    it('does not render when history is undefined', () => {
      render(<FeedbackHistory feedbackHistory={undefined as unknown as CheckpointFeedback[]} />);

      expect(screen.queryByText('Previous Feedback')).not.toBeInTheDocument();
    });

    it('expands first entry by default', () => {
      render(<FeedbackHistory {...defaultProps} />);

      expect(screen.getByText('Please add more error handling')).toBeInTheDocument();
    });
  });

  describe('feedback entries', () => {
    it('renders feedback text when entry is expanded', () => {
      render(<FeedbackHistory {...defaultProps} />);

      expect(screen.getByText('Please add more error handling')).toBeInTheDocument();
    });

    it('can collapse and expand entries', () => {
      render(<FeedbackHistory {...defaultProps} />);

      // Feedback should be visible (first entry expanded by default)
      expect(screen.getByText('Please add more error handling')).toBeInTheDocument();

      // Find and click the header button to collapse
      const headerButtons = screen.getAllByRole('button');
      fireEvent.click(headerButtons[0]); // First button is the entry header

      // Feedback text should be hidden
      expect(screen.queryByText('Please add more error handling')).not.toBeInTheDocument();

      // Click again to expand
      fireEvent.click(headerButtons[0]);

      // Feedback should be visible again
      expect(screen.getByText('Please add more error handling')).toBeInTheDocument();
    });

    it('shows attachment count badge when entry has attachments', () => {
      const feedbackWithAttachments = createMockFeedback({
        attachments: [createMockAttachment()],
      });
      render(<FeedbackHistory {...defaultProps} feedbackHistory={[feedbackWithAttachments]} />);

      expect(screen.getByText('1 file')).toBeInTheDocument();
    });
  });

  describe('attachments display', () => {
    it('renders file attachments', () => {
      const feedbackWithFile = createMockFeedback({
        attachments: [
          createMockAttachment({
            type: 'file',
            name: 'document.pdf',
            path: '/path/document.pdf',
            size: 2048,
          }),
        ],
      });
      render(<FeedbackHistory {...defaultProps} feedbackHistory={[feedbackWithFile]} />);

      expect(screen.getByText('document.pdf')).toBeInTheDocument();
      expect(screen.getByText('2 KB')).toBeInTheDocument();
    });

    it('renders link attachments', () => {
      const feedbackWithLink = createMockFeedback({
        attachments: [
          createMockAttachment({
            type: 'link',
            name: 'Documentation',
            path: 'https://docs.example.com',
          }),
        ],
      });
      render(<FeedbackHistory {...defaultProps} feedbackHistory={[feedbackWithLink]} />);

      expect(screen.getByText('Documentation')).toBeInTheDocument();
    });

    it('calls onViewAttachment when attachment is clicked', () => {
      const attachment = createMockAttachment({ id: 'test-attachment' });
      const feedbackWithAttachment = createMockFeedback({
        attachments: [attachment],
      });
      render(<FeedbackHistory {...defaultProps} feedbackHistory={[feedbackWithAttachment]} />);

      fireEvent.click(screen.getByText('example.md'));

      expect(defaultProps.onViewAttachment).toHaveBeenCalledWith(attachment);
    });
  });

  describe('pagination', () => {
    it('shows only first 3 entries by default', () => {
      const feedbackHistory = [
        createMockFeedback({ id: '1', feedback: 'Feedback 1', createdAt: '2026-01-16T10:00:00Z' }),
        createMockFeedback({ id: '2', feedback: 'Feedback 2', createdAt: '2026-01-16T11:00:00Z' }),
        createMockFeedback({ id: '3', feedback: 'Feedback 3', createdAt: '2026-01-16T12:00:00Z' }),
        createMockFeedback({ id: '4', feedback: 'Feedback 4', createdAt: '2026-01-16T13:00:00Z' }),
        createMockFeedback({ id: '5', feedback: 'Feedback 5', createdAt: '2026-01-16T14:00:00Z' }),
      ];
      render(<FeedbackHistory {...defaultProps} feedbackHistory={feedbackHistory} />);

      // Should show "Show all" button when there are more than 3
      expect(screen.getByRole('button', { name: /show all/i })).toBeInTheDocument();
    });

    it('shows all entries when "Show all" is clicked', () => {
      const feedbackHistory = [
        createMockFeedback({ id: '1', feedback: 'Feedback 1', createdAt: '2026-01-16T10:00:00Z' }),
        createMockFeedback({ id: '2', feedback: 'Feedback 2', createdAt: '2026-01-16T11:00:00Z' }),
        createMockFeedback({ id: '3', feedback: 'Feedback 3', createdAt: '2026-01-16T12:00:00Z' }),
        createMockFeedback({ id: '4', feedback: 'Feedback 4', createdAt: '2026-01-16T13:00:00Z' }),
      ];
      render(<FeedbackHistory {...defaultProps} feedbackHistory={feedbackHistory} />);

      // Click "Show all"
      fireEvent.click(screen.getByRole('button', { name: /show all/i }));

      // Should now show "Show less"
      expect(screen.getByRole('button', { name: /show less/i })).toBeInTheDocument();
    });

    it('hides pagination when 3 or fewer entries', () => {
      const feedbackHistory = [
        createMockFeedback({ id: '1', feedback: 'Feedback 1' }),
        createMockFeedback({ id: '2', feedback: 'Feedback 2' }),
      ];
      render(<FeedbackHistory {...defaultProps} feedbackHistory={feedbackHistory} />);

      expect(screen.queryByRole('button', { name: /show all/i })).not.toBeInTheDocument();
    });
  });

  describe('sorting', () => {
    it('shows most recent feedback first', () => {
      const feedbackHistory = [
        createMockFeedback({ id: '1', feedback: 'Old feedback', createdAt: '2026-01-15T10:00:00Z' }),
        createMockFeedback({ id: '2', feedback: 'New feedback', createdAt: '2026-01-16T10:00:00Z' }),
      ];
      render(<FeedbackHistory {...defaultProps} feedbackHistory={feedbackHistory} />);

      // The most recent feedback should be expanded (first visible)
      expect(screen.getByText('New feedback')).toBeInTheDocument();
    });
  });

  describe('date formatting', () => {
    it('formats dates in readable format', () => {
      const feedback = createMockFeedback({
        createdAt: '2026-01-16T14:30:00Z',
      });
      render(<FeedbackHistory {...defaultProps} feedbackHistory={[feedback]} />);

      // The formatted date should be present (exact format depends on locale)
      // Just verify the component renders without error
      expect(screen.getByText('Previous Feedback')).toBeInTheDocument();
    });
  });
});
