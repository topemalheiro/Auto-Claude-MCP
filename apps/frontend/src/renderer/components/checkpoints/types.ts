/**
 * Types for checkpoint dialog components.
 *
 * Story Reference: Story 5.2 - Implement Checkpoint Dialog Component
 * Story Reference: Story 5.3 - Implement Checkpoint Feedback Input
 * Architecture Source: architecture.md#Checkpoint-Service
 */

/**
 * Artifact produced during a phase.
 */
export interface CheckpointArtifact {
  /** Relative path to the artifact file */
  path: string;
  /** Display name for the artifact */
  name: string;
  /** Type of artifact for icon display */
  type: 'file' | 'plan' | 'code' | 'test' | 'report';
}

/**
 * Key decision made by the AI during the phase.
 */
export interface CheckpointDecisionItem {
  /** Description of the decision */
  description: string;
  /** Severity/importance of the decision */
  severity?: 'info' | 'warning' | 'critical';
  /** Related file or component */
  relatedTo?: string;
}

/**
 * Information about a checkpoint for display in the dialog.
 * Maps to the backend's checkpoint event data.
 */
export interface CheckpointInfo {
  /** Unique identifier for the checkpoint */
  checkpointId: string;
  /** Human-readable name */
  name: string;
  /** Description of what was completed */
  description: string;
  /** Phase that was completed. Supports both frontend naming (planning/validation) and backend naming (plan/validate) */
  phase: 'planning' | 'plan' | 'coding' | 'validation' | 'validate';
  /** Task ID this checkpoint belongs to */
  taskId: string;
  /** When the checkpoint was reached */
  pausedAt: string;
  /** Artifacts produced during this phase */
  artifacts: CheckpointArtifact[];
  /** Key decisions made during this phase */
  decisions?: CheckpointDecisionItem[];
  /** Any warnings or concerns to highlight */
  warnings?: string[];
  /** Whether approval is required to continue */
  requiresApproval: boolean;
  /** Summary of what was accomplished */
  summary?: string;
}

/**
 * Props for the CheckpointDialog component.
 */
export interface CheckpointDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Checkpoint information to display */
  checkpoint: CheckpointInfo | null;
  /** Callback when user approves and wants to continue */
  onApprove: () => void;
  /** Callback when user requests revision with feedback */
  onRevision: (feedback: string) => void;
  /** Callback when user cancels the task */
  onCancel: () => void;
  /** Callback when dialog is closed without action */
  onOpenChange: (open: boolean) => void;
  /** Callback when user wants to view an artifact */
  onViewArtifact?: (artifact: CheckpointArtifact) => void;
  /** Whether an action is being processed */
  isProcessing?: boolean;
  /** Callback when user submits feedback with optional attachments (Story 5.3) */
  onFeedbackSubmit?: (feedback: string, attachments?: FeedbackAttachment[]) => void;
  /** Previous feedback history for this checkpoint (Story 5.3) */
  feedbackHistory?: CheckpointFeedback[];
}

/**
 * Attachment type for feedback (Story 5.3).
 */
export interface FeedbackAttachment {
  /** Unique identifier for the attachment */
  id: string;
  /** Type of attachment */
  type: 'file' | 'link';
  /** Display name for the attachment */
  name: string;
  /** File path (for files) or URL (for links) */
  path: string;
  /** File size in bytes (for files) */
  size?: number;
  /** MIME type (for files) */
  mimeType?: string;
}

/**
 * Feedback entry for a checkpoint (Story 5.3).
 */
export interface CheckpointFeedback {
  /** Unique identifier for the feedback entry */
  id: string;
  /** ID of the checkpoint this feedback belongs to */
  checkpointId: string;
  /** The feedback text */
  feedback: string;
  /** Attached files or links */
  attachments: FeedbackAttachment[];
  /** When the feedback was submitted */
  createdAt: string;
}

/**
 * Props for the FeedbackInput component (Story 5.3).
 */
export interface FeedbackInputProps {
  /** Callback when feedback is submitted */
  onSubmit: (feedback: string, attachments?: FeedbackAttachment[]) => void;
  /** Placeholder text for the textarea */
  placeholder?: string;
  /** Whether the component is disabled */
  disabled?: boolean;
  /** Whether an action is being processed */
  isProcessing?: boolean;
}

/**
 * Props for the FeedbackHistory component (Story 5.3).
 */
export interface FeedbackHistoryProps {
  /** List of feedback entries to display */
  feedbackHistory: CheckpointFeedback[];
  /** Callback when user wants to view an attachment */
  onViewAttachment?: (attachment: FeedbackAttachment) => void;
}
