/**
 * FeedbackHistory component for displaying checkpoint feedback history.
 *
 * Shows all feedback entries provided at checkpoints for the current task,
 * including timestamps, feedback text, and any attachments.
 *
 * Story Reference: Story 5.3 - Implement Checkpoint Feedback Input
 * Acceptance Criteria 3: View feedback history for the task
 */

import { useTranslation } from 'react-i18next';
import {
  ChevronDown,
  ChevronUp,
  Clock,
  ExternalLink,
  File,
  History,
  Link2,
  MessageSquare,
} from 'lucide-react';
import { useState } from 'react';

import { Button } from '../ui/button';
import { cn } from '../../lib/utils';

import type { FeedbackHistoryProps, FeedbackAttachment, CheckpointFeedback } from './types';
import { formatFileSize } from './utils';

/**
 * Format a date string to a human-readable format.
 */
function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('default', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

/**
 * Single attachment display.
 */
function AttachmentDisplay({
  attachment,
  onView,
}: {
  attachment: FeedbackAttachment;
  onView?: (attachment: FeedbackAttachment) => void;
}) {
  const { t } = useTranslation(['checkpoints']);
  const Icon = attachment.type === 'file' ? File : Link2;
  const isLink = attachment.type === 'link';

  return (
    <button
      onClick={() => onView?.(attachment)}
      className={cn(
        'flex items-center gap-2 p-2 rounded-md',
        'bg-background/50 border border-border/50',
        'hover:bg-muted/50 transition-colors',
        'text-sm text-left w-full'
      )}
    >
      <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="truncate">{attachment.name}</p>
        {attachment.type === 'file' && attachment.size && (
          <p className="text-xs text-muted-foreground">
            {formatFileSize(attachment.size)}
          </p>
        )}
      </div>
      {isLink && <ExternalLink className="h-3 w-3 text-muted-foreground" />}
    </button>
  );
}

/**
 * Single feedback entry display.
 */
function FeedbackEntry({
  entry,
  onViewAttachment,
  defaultExpanded = false,
}: {
  entry: CheckpointFeedback;
  onViewAttachment?: (attachment: FeedbackAttachment) => void;
  defaultExpanded?: boolean;
}) {
  const { t } = useTranslation(['checkpoints']);
  const [expanded, setExpanded] = useState(defaultExpanded);
  const hasAttachments = entry.attachments && entry.attachments.length > 0;

  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden">
      {/* Header - always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className={cn(
          'w-full p-3 flex items-center justify-between',
          'hover:bg-muted/30 transition-colors',
          'text-left'
        )}
      >
        <div className="flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-muted-foreground" />
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            <span>{formatDate(entry.createdAt)}</span>
          </div>
          {hasAttachments && (
            <span className="text-xs bg-muted px-1.5 py-0.5 rounded">
              {t('checkpoints:feedback.attachmentCount', {
                count: entry.attachments.length,
              })}
            </span>
          )}
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        )}
      </button>

      {/* Content - expanded */}
      {expanded && (
        <div className="px-3 pb-3 space-y-3 border-t border-border/50">
          {/* Feedback text */}
          <p className="text-sm pt-3 whitespace-pre-wrap">{entry.feedback}</p>

          {/* Attachments */}
          {hasAttachments && (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground font-medium">
                {t('checkpoints:feedback.attachments', {
                  count: entry.attachments.length,
                })}
              </p>
              <div className="grid gap-2">
                {entry.attachments.map((attachment) => (
                  <AttachmentDisplay
                    key={attachment.id}
                    attachment={attachment}
                    onView={onViewAttachment}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * FeedbackHistory component.
 *
 * Displays the history of feedback provided at checkpoints for the current task.
 * Entries can be expanded to see full feedback text and attachments.
 */
export function FeedbackHistory({
  feedbackHistory,
  onViewAttachment,
}: FeedbackHistoryProps) {
  const { t } = useTranslation(['checkpoints']);
  const [showAll, setShowAll] = useState(false);

  if (!feedbackHistory || feedbackHistory.length === 0) {
    return null;
  }

  // Sort by most recent first
  const sortedHistory = [...feedbackHistory].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  );

  // Show only the last 3 by default
  const visibleHistory = showAll ? sortedHistory : sortedHistory.slice(0, 3);
  const hasMore = sortedHistory.length > 3;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <History className="h-4 w-4 text-muted-foreground" />
          <h4 className="text-sm font-medium">
            {t('checkpoints:feedback.historyTitle')}
          </h4>
          <span className="text-xs text-muted-foreground">
            ({feedbackHistory.length})
          </span>
        </div>
        {hasMore && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowAll(!showAll)}
            className="h-7 text-xs"
          >
            {showAll
              ? t('checkpoints:feedback.showLess')
              : t('checkpoints:feedback.showAll', {
                  count: sortedHistory.length,
                })}
          </Button>
        )}
      </div>

      <div className="space-y-2">
        {visibleHistory.map((entry, index) => (
          <FeedbackEntry
            key={entry.id}
            entry={entry}
            onViewAttachment={onViewAttachment}
            defaultExpanded={index === 0}
          />
        ))}
      </div>
    </div>
  );
}

export default FeedbackHistory;
