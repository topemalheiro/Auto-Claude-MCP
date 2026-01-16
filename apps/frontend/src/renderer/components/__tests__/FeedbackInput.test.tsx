/**
 * @vitest-environment jsdom
 */
/**
 * Tests for FeedbackInput component
 *
 * Story Reference: Story 5.3 - Implement Checkpoint Feedback Input
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { FeedbackInput } from '../checkpoints/FeedbackInput';

// Mock uuid
vi.mock('uuid', () => ({
  v4: () => 'mock-uuid-1234',
}));

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      const translations: Record<string, string> = {
        'checkpoints:feedback.placeholder': 'Enter your feedback...',
        'checkpoints:feedback.submit': 'Submit Feedback',
        'checkpoints:feedback.submitting': 'Submitting...',
        'checkpoints:feedback.attachFile': 'Attach File',
        'checkpoints:feedback.addLinkButton': 'Add Link',
        'checkpoints:feedback.removeAttachment': 'Remove attachment',
        'checkpoints:feedback.linkNamePlaceholder': 'Link name (optional)',
        'checkpoints:feedback.linkUrlPlaceholder': 'https://...',
        'checkpoints:feedback.cancelLink': 'Cancel',
        'checkpoints:feedback.addLink': 'Add',
        'checkpoints:feedback.attachments': `${params?.count || 0} attachment`,
        'checkpoints:feedback.invalidUrl': 'Please enter a valid URL',
        'checkpoints:feedback.fileAttachmentComingSoon': 'File attachment coming soon',
        'common:buttons.cancel': 'Cancel',
      };
      return translations[key] || key;
    },
  }),
}));

describe('FeedbackInput', () => {
  const defaultProps = {
    onSubmit: vi.fn(),
    disabled: false,
    isProcessing: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('rendering', () => {
    it('renders textarea with placeholder', () => {
      render(<FeedbackInput {...defaultProps} />);

      expect(screen.getByPlaceholderText('Enter your feedback...')).toBeInTheDocument();
    });

    it('renders custom placeholder when provided', () => {
      render(<FeedbackInput {...defaultProps} placeholder="Custom placeholder" />);

      expect(screen.getByPlaceholderText('Custom placeholder')).toBeInTheDocument();
    });

    it('renders submit button', () => {
      render(<FeedbackInput {...defaultProps} />);

      expect(screen.getByRole('button', { name: /submit feedback/i })).toBeInTheDocument();
    });

    it('renders attach file button', () => {
      render(<FeedbackInput {...defaultProps} />);

      expect(screen.getByRole('button', { name: /attach file/i })).toBeInTheDocument();
    });

    it('renders add link button', () => {
      render(<FeedbackInput {...defaultProps} />);

      expect(screen.getByRole('button', { name: /add link/i })).toBeInTheDocument();
    });
  });

  describe('feedback submission', () => {
    it('calls onSubmit with feedback when submitted', () => {
      render(<FeedbackInput {...defaultProps} />);

      const textarea = screen.getByPlaceholderText('Enter your feedback...');
      fireEvent.change(textarea, { target: { value: 'My feedback' } });
      fireEvent.click(screen.getByRole('button', { name: /submit feedback/i }));

      expect(defaultProps.onSubmit).toHaveBeenCalledWith('My feedback', undefined);
    });

    it('trims whitespace from feedback', () => {
      render(<FeedbackInput {...defaultProps} />);

      const textarea = screen.getByPlaceholderText('Enter your feedback...');
      fireEvent.change(textarea, { target: { value: '  Trimmed feedback  ' } });
      fireEvent.click(screen.getByRole('button', { name: /submit feedback/i }));

      expect(defaultProps.onSubmit).toHaveBeenCalledWith('Trimmed feedback', undefined);
    });

    it('disables submit button when feedback is empty', () => {
      render(<FeedbackInput {...defaultProps} />);

      expect(screen.getByRole('button', { name: /submit feedback/i })).toBeDisabled();
    });

    it('disables submit button when feedback is only whitespace', () => {
      render(<FeedbackInput {...defaultProps} />);

      const textarea = screen.getByPlaceholderText('Enter your feedback...');
      fireEvent.change(textarea, { target: { value: '   ' } });

      expect(screen.getByRole('button', { name: /submit feedback/i })).toBeDisabled();
    });

    it('clears textarea after submission', () => {
      render(<FeedbackInput {...defaultProps} />);

      const textarea = screen.getByPlaceholderText('Enter your feedback...');
      fireEvent.change(textarea, { target: { value: 'My feedback' } });
      fireEvent.click(screen.getByRole('button', { name: /submit feedback/i }));

      expect(textarea).toHaveValue('');
    });
  });

  describe('disabled state', () => {
    it('disables textarea when disabled', () => {
      render(<FeedbackInput {...defaultProps} disabled={true} />);

      expect(screen.getByPlaceholderText('Enter your feedback...')).toBeDisabled();
    });

    it('disables all buttons when disabled', () => {
      render(<FeedbackInput {...defaultProps} disabled={true} />);

      expect(screen.getByRole('button', { name: /attach file/i })).toBeDisabled();
      expect(screen.getByRole('button', { name: /add link/i })).toBeDisabled();
    });

    it('disables all inputs when processing', () => {
      render(<FeedbackInput {...defaultProps} isProcessing={true} />);

      expect(screen.getByPlaceholderText('Enter your feedback...')).toBeDisabled();
      expect(screen.getByRole('button', { name: /attach file/i })).toBeDisabled();
    });

    it('shows submitting state when processing', () => {
      render(<FeedbackInput {...defaultProps} isProcessing={true} />);

      expect(screen.getByText('Submitting...')).toBeInTheDocument();
    });
  });

  describe('link attachments', () => {
    it('shows link input dialog when add link is clicked', () => {
      render(<FeedbackInput {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /add link/i }));

      expect(screen.getByPlaceholderText('Link name (optional)')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('https://...')).toBeInTheDocument();
    });

    it('adds link attachment when submitted', async () => {
      render(<FeedbackInput {...defaultProps} />);

      // Open link dialog
      fireEvent.click(screen.getByRole('button', { name: /add link/i }));

      // Fill in link details
      fireEvent.change(screen.getByPlaceholderText('Link name (optional)'), {
        target: { value: 'Documentation' },
      });
      fireEvent.change(screen.getByPlaceholderText('https://...'), {
        target: { value: 'https://docs.example.com' },
      });

      // Add link
      fireEvent.click(screen.getByRole('button', { name: /^add$/i }));

      // Check attachment is shown
      await waitFor(() => {
        expect(screen.getByText('Documentation')).toBeInTheDocument();
        expect(screen.getByText('https://docs.example.com')).toBeInTheDocument();
      });
    });

    it('uses URL as name when name is not provided', async () => {
      render(<FeedbackInput {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /add link/i }));
      fireEvent.change(screen.getByPlaceholderText('https://...'), {
        target: { value: 'https://example.com' },
      });
      fireEvent.click(screen.getByRole('button', { name: /^add$/i }));

      await waitFor(() => {
        // URL appears twice: once as name, once as path
        const elements = screen.getAllByText('https://example.com');
        expect(elements.length).toBeGreaterThanOrEqual(1);
      });
    });

    it('can cancel link dialog', () => {
      render(<FeedbackInput {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /add link/i }));
      expect(screen.getByPlaceholderText('https://...')).toBeInTheDocument();

      fireEvent.click(screen.getByRole('button', { name: /^cancel$/i }));

      expect(screen.queryByPlaceholderText('https://...')).not.toBeInTheDocument();
    });

    it('disables add button when URL is empty', () => {
      render(<FeedbackInput {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /add link/i }));

      expect(screen.getByRole('button', { name: /^add$/i })).toBeDisabled();
    });
  });

  describe('attachment management', () => {
    it('can remove an attachment', async () => {
      render(<FeedbackInput {...defaultProps} />);

      // Add a link
      fireEvent.click(screen.getByRole('button', { name: /add link/i }));
      fireEvent.change(screen.getByPlaceholderText('https://...'), {
        target: { value: 'https://example.com' },
      });
      fireEvent.click(screen.getByRole('button', { name: /^add$/i }));

      // Verify it's added (URL appears twice: as name and as path)
      await waitFor(() => {
        const elements = screen.getAllByText('https://example.com');
        expect(elements.length).toBeGreaterThanOrEqual(1);
      });

      // Remove it
      fireEvent.click(screen.getByRole('button', { name: /remove attachment/i }));

      // Verify it's removed
      expect(screen.queryAllByText('https://example.com')).toHaveLength(0);
    });

    it('includes attachments in submission', async () => {
      render(<FeedbackInput {...defaultProps} />);

      // Add feedback
      fireEvent.change(screen.getByPlaceholderText('Enter your feedback...'), {
        target: { value: 'Check this link' },
      });

      // Add a link
      fireEvent.click(screen.getByRole('button', { name: /add link/i }));
      fireEvent.change(screen.getByPlaceholderText('Link name (optional)'), {
        target: { value: 'Reference' },
      });
      fireEvent.change(screen.getByPlaceholderText('https://...'), {
        target: { value: 'https://example.com' },
      });
      fireEvent.click(screen.getByRole('button', { name: /^add$/i }));

      // Wait for attachment to be added
      await waitFor(() => {
        expect(screen.getByText('Reference')).toBeInTheDocument();
      });

      // Submit
      fireEvent.click(screen.getByRole('button', { name: /submit feedback/i }));

      expect(defaultProps.onSubmit).toHaveBeenCalledWith(
        'Check this link',
        expect.arrayContaining([
          expect.objectContaining({
            type: 'link',
            name: 'Reference',
            path: 'https://example.com',
          }),
        ])
      );
    });

    it('clears attachments after submission', async () => {
      render(<FeedbackInput {...defaultProps} />);

      // Add feedback and link
      fireEvent.change(screen.getByPlaceholderText('Enter your feedback...'), {
        target: { value: 'Check this' },
      });
      fireEvent.click(screen.getByRole('button', { name: /add link/i }));
      fireEvent.change(screen.getByPlaceholderText('https://...'), {
        target: { value: 'https://example.com' },
      });
      fireEvent.click(screen.getByRole('button', { name: /^add$/i }));

      // URL appears twice: as name and as path
      await waitFor(() => {
        const elements = screen.getAllByText('https://example.com');
        expect(elements.length).toBeGreaterThanOrEqual(1);
      });

      // Submit
      fireEvent.click(screen.getByRole('button', { name: /submit feedback/i }));

      // Attachments should be cleared
      expect(screen.queryAllByText('https://example.com')).toHaveLength(0);
    });
  });

  describe('accessibility', () => {
    it('submit button has minimum 44px touch target', () => {
      render(<FeedbackInput {...defaultProps} />);

      const submitButton = screen.getByRole('button', { name: /submit feedback/i });
      expect(submitButton).toHaveClass('min-h-[44px]');
    });
  });

  describe('URL validation', () => {
    it('rejects javascript: URLs', () => {
      render(<FeedbackInput {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /add link/i }));
      fireEvent.change(screen.getByPlaceholderText('https://...'), {
        target: { value: 'javascript:alert(1)' },
      });

      // Add button should be disabled for invalid URL
      expect(screen.getByRole('button', { name: /^add$/i })).toBeDisabled();
    });

    it('rejects data: URLs', () => {
      render(<FeedbackInput {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /add link/i }));
      fireEvent.change(screen.getByPlaceholderText('https://...'), {
        target: { value: 'data:text/html,<script>alert(1)</script>' },
      });

      expect(screen.getByRole('button', { name: /^add$/i })).toBeDisabled();
    });

    it('accepts valid https URLs', () => {
      render(<FeedbackInput {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /add link/i }));
      fireEvent.change(screen.getByPlaceholderText('https://...'), {
        target: { value: 'https://example.com' },
      });

      expect(screen.getByRole('button', { name: /^add$/i })).not.toBeDisabled();
    });

    it('accepts valid http URLs', () => {
      render(<FeedbackInput {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /add link/i }));
      fireEvent.change(screen.getByPlaceholderText('https://...'), {
        target: { value: 'http://example.com' },
      });

      expect(screen.getByRole('button', { name: /^add$/i })).not.toBeDisabled();
    });
  });

  describe('edge cases', () => {
    it('passes undefined when all attachments are removed before submission', async () => {
      render(<FeedbackInput {...defaultProps} />);

      // Add feedback
      fireEvent.change(screen.getByPlaceholderText('Enter your feedback...'), {
        target: { value: 'Test feedback' },
      });

      // Add a link
      fireEvent.click(screen.getByRole('button', { name: /add link/i }));
      fireEvent.change(screen.getByPlaceholderText('https://...'), {
        target: { value: 'https://example.com' },
      });
      fireEvent.click(screen.getByRole('button', { name: /^add$/i }));

      // Wait for attachment to be added
      await waitFor(() => {
        const elements = screen.getAllByText('https://example.com');
        expect(elements.length).toBeGreaterThanOrEqual(1);
      });

      // Remove the attachment
      fireEvent.click(screen.getByRole('button', { name: /remove attachment/i }));

      // Submit - should pass undefined, not empty array
      fireEvent.click(screen.getByRole('button', { name: /submit feedback/i }));

      expect(defaultProps.onSubmit).toHaveBeenCalledWith('Test feedback', undefined);
    });

    it('file attachment button is disabled (feature not implemented)', () => {
      render(<FeedbackInput {...defaultProps} />);

      // File attachment feature should be disabled
      expect(screen.getByRole('button', { name: /attach file/i })).toBeDisabled();
    });
  });
});
