/**
 * FeedbackInput component for checkpoint feedback with attachment support.
 *
 * Allows users to provide feedback and optionally attach files or links
 * that provide additional context for the AI agent.
 *
 * Story Reference: Story 5.3 - Implement Checkpoint Feedback Input
 * Architecture Source: architecture.md#Checkpoint-Feedback
 */

import { useState, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  File,
  Link2,
  Loader2,
  Paperclip,
  Send,
  X,
} from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';

import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { cn } from '../../lib/utils';

import type { FeedbackInputProps, FeedbackAttachment } from './types';
import { formatFileSize, isValidUrl } from './utils';

/**
 * AttachmentItem component for displaying a single attachment.
 */
function AttachmentItem({
  attachment,
  onRemove,
}: {
  attachment: FeedbackAttachment;
  onRemove: (id: string) => void;
}) {
  const { t } = useTranslation(['checkpoints']);
  const Icon = attachment.type === 'file' ? File : Link2;

  return (
    <div
      className={cn(
        'flex items-center gap-2 p-2 rounded-lg',
        'bg-muted/50 border border-border/50',
        'text-sm'
      )}
    >
      <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="truncate font-medium">{attachment.name}</p>
        {attachment.type === 'file' && attachment.size && (
          <p className="text-xs text-muted-foreground">
            {formatFileSize(attachment.size)}
          </p>
        )}
        {attachment.type === 'link' && (
          <p className="text-xs text-muted-foreground truncate">
            {attachment.path}
          </p>
        )}
      </div>
      <Button
        variant="ghost"
        size="sm"
        className="h-6 w-6 p-0"
        onClick={() => onRemove(attachment.id)}
        aria-label={t('checkpoints:feedback.removeAttachment')}
      >
        <X className="h-3 w-3" />
      </Button>
    </div>
  );
}

/**
 * LinkInputDialog component for adding a link attachment.
 */
function LinkInputDialog({
  open,
  onClose,
  onAdd,
}: {
  open: boolean;
  onClose: () => void;
  onAdd: (name: string, url: string) => void;
}) {
  const { t } = useTranslation(['checkpoints']);
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [urlError, setUrlError] = useState(false);

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newUrl = e.target.value;
    setUrl(newUrl);
    // Clear error when user starts typing, validate on blur/submit
    if (urlError) {
      setUrlError(false);
    }
  };

  const handleUrlBlur = () => {
    // Validate URL on blur if there's content
    if (url.trim() && !isValidUrl(url.trim())) {
      setUrlError(true);
    }
  };

  const handleSubmit = () => {
    const trimmedUrl = url.trim();
    if (trimmedUrl && isValidUrl(trimmedUrl)) {
      const linkName = name.trim() || trimmedUrl;
      onAdd(linkName, trimmedUrl);
      setName('');
      setUrl('');
      setUrlError(false);
      onClose();
    } else if (trimmedUrl) {
      setUrlError(true);
    }
  };

  const handleClose = () => {
    setName('');
    setUrl('');
    setUrlError(false);
    onClose();
  };

  if (!open) return null;

  const isUrlValid = url.trim() && isValidUrl(url.trim());

  return (
    <div className="space-y-3 p-3 bg-muted/30 rounded-lg border border-border/50">
      <div className="space-y-2">
        <input
          type="text"
          placeholder={t('checkpoints:feedback.linkNamePlaceholder')}
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={cn(
            'w-full px-3 py-2 text-sm rounded-md',
            'bg-card border border-border',
            'focus:outline-none focus:ring-2 focus:ring-ring'
          )}
        />
        <input
          type="url"
          placeholder={t('checkpoints:feedback.linkUrlPlaceholder')}
          value={url}
          onChange={handleUrlChange}
          onBlur={handleUrlBlur}
          className={cn(
            'w-full px-3 py-2 text-sm rounded-md',
            'bg-card border',
            urlError ? 'border-destructive' : 'border-border',
            'focus:outline-none focus:ring-2',
            urlError ? 'focus:ring-destructive' : 'focus:ring-ring'
          )}
        />
        {urlError && (
          <p className="text-xs text-destructive">
            {t('checkpoints:feedback.invalidUrl')}
          </p>
        )}
      </div>
      <div className="flex justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={handleClose}>
          {t('checkpoints:feedback.cancelLink')}
        </Button>
        <Button size="sm" onClick={handleSubmit} disabled={!isUrlValid}>
          {t('checkpoints:feedback.addLink')}
        </Button>
      </div>
    </div>
  );
}

/**
 * FeedbackInput component.
 *
 * Provides a textarea for entering feedback and buttons to attach
 * files or links. Attachments are displayed in a list below the textarea.
 */
export function FeedbackInput({
  onSubmit,
  placeholder,
  disabled = false,
  isProcessing = false,
}: FeedbackInputProps) {
  const { t } = useTranslation(['checkpoints', 'common']);
  const [feedback, setFeedback] = useState('');
  const [attachments, setAttachments] = useState<FeedbackAttachment[]>([]);
  const [showLinkInput, setShowLinkInput] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  /**
   * Handle file selection from the file input.
   *
   * TODO: Story 5.3 - File upload implementation is incomplete.
   * The file content is not transmitted to the backend. This feature
   * is disabled until proper file upload mechanism is implemented.
   * See: architecture.md#Checkpoint-Feedback for planned implementation.
   */
  const handleFileSelect = useCallback((_event: React.ChangeEvent<HTMLInputElement>) => {
    // File upload is disabled - feature incomplete
    // When enabled, this should:
    // 1. Read file content as base64 or use FormData
    // 2. Include file content in the attachment object
    // 3. Backend needs endpoint to receive file data
  }, []);

  // File attachment feature is disabled until backend support is implemented
  const isFileAttachmentEnabled = false;

  /**
   * Handle adding a link attachment.
   */
  const handleAddLink = useCallback((name: string, url: string) => {
    const linkAttachment: FeedbackAttachment = {
      id: uuidv4(),
      type: 'link',
      name,
      path: url,
    };
    setAttachments((prev) => [...prev, linkAttachment]);
  }, []);

  /**
   * Handle removing an attachment.
   */
  const handleRemoveAttachment = useCallback((id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
  }, []);

  /**
   * Handle form submission.
   */
  const handleSubmit = useCallback(() => {
    if (feedback.trim()) {
      onSubmit(feedback.trim(), attachments.length > 0 ? attachments : undefined);
      setFeedback('');
      setAttachments([]);
    }
  }, [feedback, attachments, onSubmit]);

  const isDisabled = disabled || isProcessing;
  const canSubmit = feedback.trim().length > 0 && !isDisabled;

  return (
    <div className="space-y-3">
      {/* Textarea */}
      <Textarea
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
        placeholder={placeholder || t('checkpoints:feedback.placeholder')}
        className="min-h-[100px]"
        disabled={isDisabled}
      />

      {/* Attachments list */}
      {attachments.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground font-medium">
            {t('checkpoints:feedback.attachments', { count: attachments.length })}
          </p>
          <div className="grid gap-2">
            {attachments.map((attachment) => (
              <AttachmentItem
                key={attachment.id}
                attachment={attachment}
                onRemove={handleRemoveAttachment}
              />
            ))}
          </div>
        </div>
      )}

      {/* Link input dialog */}
      <LinkInputDialog
        open={showLinkInput}
        onClose={() => setShowLinkInput(false)}
        onAdd={handleAddLink}
      />

      {/* Action buttons */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileSelect}
            className="hidden"
            disabled={isDisabled}
          />

          {/* Attach file button - disabled until file upload is implemented */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={isDisabled || !isFileAttachmentEnabled}
            className="h-8"
            title={!isFileAttachmentEnabled ? t('checkpoints:feedback.fileAttachmentComingSoon') : undefined}
          >
            <Paperclip className="h-4 w-4 mr-1" />
            {t('checkpoints:feedback.attachFile')}
          </Button>

          {/* Add link button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowLinkInput(!showLinkInput)}
            disabled={isDisabled}
            className="h-8"
          >
            <Link2 className="h-4 w-4 mr-1" />
            {t('checkpoints:feedback.addLinkButton')}
          </Button>
        </div>

        {/* Submit button */}
        <Button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="min-h-[44px]"
        >
          {isProcessing ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {t('checkpoints:feedback.submitting')}
            </>
          ) : (
            <>
              <Send className="mr-2 h-4 w-4" />
              {t('checkpoints:feedback.submit')}
            </>
          )}
        </Button>
      </div>
    </div>
  );
}

export default FeedbackInput;
