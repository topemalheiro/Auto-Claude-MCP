/**
 * CheckpointDialog component for Semi-Auto execution mode.
 *
 * Displays checkpoint results and allows users to make decisions
 * about continuing, revising, or canceling task execution.
 *
 * Story Reference: Story 5.2 - Implement Checkpoint Dialog Component
 * Design System: Oscura (card-based UI with subtle borders)
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileCode,
  FileText,
  Loader2,
  Play,
  RefreshCw,
  TestTube,
  X,
  ClipboardList,
  FileBarChart,
} from 'lucide-react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { cn } from '../../lib/utils';

import type { CheckpointDialogProps, CheckpointArtifact, CheckpointDecisionItem, FeedbackAttachment } from './types';
import { FeedbackHistory } from './FeedbackHistory';

/**
 * Get the appropriate icon for an artifact type.
 */
function getArtifactIcon(type: CheckpointArtifact['type']) {
  switch (type) {
    case 'plan':
      return ClipboardList;
    case 'code':
      return FileCode;
    case 'test':
      return TestTube;
    case 'report':
      return FileBarChart;
    case 'file':
    default:
      return FileText;
  }
}

/**
 * Phase color mapping.
 */
const PHASE_COLORS: Record<string, string> = {
  planning: 'text-blue-500',
  plan: 'text-blue-500', // Backend alias
  coding: 'text-green-500',
  validation: 'text-purple-500',
  validate: 'text-purple-500', // Backend alias
};

/**
 * Get phase display information using i18n.
 * Supports both frontend naming (planning/validation) and backend naming (plan/validate).
 */
function getPhaseInfo(phase: string, t: (key: string) => string) {
  // Normalize backend phase names to frontend names for i18n lookup
  const normalizedPhase = phase === 'plan' ? 'planning' : phase === 'validate' ? 'validation' : phase;
  const i18nKey = `checkpoints:phases.${normalizedPhase}`;
  const label = t(i18nKey);
  // If translation returns the key itself, use the phase name as fallback
  const displayLabel = label === i18nKey ? phase : label;
  const color = PHASE_COLORS[phase] || 'text-muted-foreground';

  return { label: displayLabel, color };
}

/**
 * Summary section showing what was completed.
 */
function CheckpointSummary({
  checkpoint,
  expanded,
  onToggleExpand,
}: {
  checkpoint: NonNullable<CheckpointDialogProps['checkpoint']>;
  expanded: boolean;
  onToggleExpand: () => void;
}) {
  const { t } = useTranslation(['checkpoints']);
  const phaseInfo = getPhaseInfo(checkpoint.phase, t);

  return (
    <div className="space-y-3">
      {/* Phase and Status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CheckCircle2 className={cn('h-5 w-5', phaseInfo.color)} />
          <span className="font-medium">{phaseInfo.label}</span>
          <span className="text-muted-foreground">{t('checkpoints:dialog.phaseComplete')}</span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onToggleExpand}
          className="h-8 px-2"
          aria-label={expanded ? t('checkpoints:dialog.collapse') : t('checkpoints:dialog.expand')}
        >
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </Button>
      </div>

      {/* Summary */}
      {checkpoint.summary && (
        <p className="text-sm text-muted-foreground">{checkpoint.summary}</p>
      )}

      {/* Expanded Details */}
      {expanded && (
        <div className="space-y-4 pt-2">
          {/* Key Decisions */}
          {checkpoint.decisions && checkpoint.decisions.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium">{t('checkpoints:dialog.keyDecisions')}</h4>
              <ul className="space-y-1">
                {checkpoint.decisions.map((decision, index) => (
                  <DecisionItem key={index} decision={decision} />
                ))}
              </ul>
            </div>
          )}

          {/* Warnings */}
          {checkpoint.warnings && checkpoint.warnings.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-amber-500">
                {t('checkpoints:dialog.warnings')}
              </h4>
              <ul className="space-y-1">
                {checkpoint.warnings.map((warning, index) => (
                  <li
                    key={index}
                    className="flex items-start gap-2 text-sm text-amber-600 dark:text-amber-500"
                  >
                    <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                    <span>{warning}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Single decision item display.
 */
function DecisionItem({ decision }: { decision: CheckpointDecisionItem }) {
  const severityColors = {
    info: 'text-blue-500',
    warning: 'text-amber-500',
    critical: 'text-red-500',
  };

  const severityBg = {
    info: 'bg-blue-500/10',
    warning: 'bg-amber-500/10',
    critical: 'bg-red-500/10',
  };

  const severity = decision.severity || 'info';

  return (
    <li
      className={cn(
        'flex items-start gap-2 text-sm p-2 rounded-lg',
        severityBg[severity]
      )}
    >
      <CheckCircle2 className={cn('h-4 w-4 mt-0.5 shrink-0', severityColors[severity])} />
      <div className="flex-1">
        <span>{decision.description}</span>
        {decision.relatedTo && (
          <span className="text-xs text-muted-foreground ml-2">({decision.relatedTo})</span>
        )}
      </div>
    </li>
  );
}

/**
 * Check if an artifact has valid data for rendering.
 */
function isValidArtifact(artifact: CheckpointArtifact | null | undefined): artifact is CheckpointArtifact {
  return (
    artifact != null &&
    typeof artifact.path === 'string' &&
    artifact.path.length > 0 &&
    typeof artifact.name === 'string' &&
    artifact.name.length > 0
  );
}

/**
 * Artifact list section.
 */
function ArtifactList({
  artifacts,
  onViewArtifact,
}: {
  artifacts: CheckpointArtifact[];
  onViewArtifact?: (artifact: CheckpointArtifact) => void;
}) {
  const { t } = useTranslation(['checkpoints']);

  // Filter out invalid artifacts defensively
  const validArtifacts = artifacts?.filter(isValidArtifact) ?? [];

  if (validArtifacts.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium">{t('checkpoints:dialog.artifacts')}</h4>
      <div className="grid gap-2">
        {validArtifacts.map((artifact, index) => {
          const Icon = getArtifactIcon(artifact.type);
          return (
            <button
              key={`${artifact.path}-${index}`}
              onClick={() => onViewArtifact?.(artifact)}
              className={cn(
                'flex items-center gap-3 p-3 rounded-lg',
                'bg-muted/50 hover:bg-muted',
                'border border-border/50 hover:border-border',
                'transition-colors text-left w-full',
                'min-h-[44px]' // Minimum touch target
              )}
            >
              <Icon className="h-5 w-5 text-muted-foreground shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{artifact.name}</p>
                <p className="text-xs text-muted-foreground truncate">{artifact.path}</p>
              </div>
              <ChevronDown className="h-4 w-4 text-muted-foreground rotate-[-90deg]" />
            </button>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Main CheckpointDialog component.
 */
export function CheckpointDialog({
  open,
  checkpoint,
  onApprove,
  onRevision,
  onCancel,
  onOpenChange,
  onViewArtifact,
  isProcessing = false,
  feedbackHistory,
}: CheckpointDialogProps) {
  const { t } = useTranslation(['checkpoints', 'common']);
  const [expanded, setExpanded] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState('');

  // Handle revision submission
  const handleRevisionSubmit = () => {
    if (feedback.trim()) {
      onRevision(feedback.trim());
      setFeedback('');
      setShowFeedback(false);
    }
  };

  // Reset state when dialog closes
  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      setExpanded(false);
      setShowFeedback(false);
      setFeedback('');
    }
    onOpenChange(newOpen);
  };

  if (!checkpoint) {
    return null;
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-green-500" />
            {t('checkpoints:dialog.title', { phase: getPhaseInfo(checkpoint.phase, t).label })}
          </DialogTitle>
          <DialogDescription>
            {checkpoint.description}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-4 py-4">
          {/* Summary Section */}
          <div className="bg-card border border-border rounded-xl p-4">
            <CheckpointSummary
              checkpoint={checkpoint}
              expanded={expanded}
              onToggleExpand={() => setExpanded(!expanded)}
            />
          </div>

          {/* Artifacts Section */}
          {checkpoint.artifacts.length > 0 && (
            <div className="bg-card border border-border rounded-xl p-4">
              <ArtifactList artifacts={checkpoint.artifacts} onViewArtifact={onViewArtifact} />
            </div>
          )}

          {/* Feedback History Section (Story 5.3) */}
          {feedbackHistory && feedbackHistory.length > 0 && (
            <div className="bg-card border border-border rounded-xl p-4">
              <FeedbackHistory
                feedbackHistory={feedbackHistory}
                onViewAttachment={(attachment: FeedbackAttachment) => {
                  // For link attachments, open in browser
                  if (attachment.type === 'link') {
                    window.open(attachment.path, '_blank', 'noopener,noreferrer');
                  }
                  // For file attachments, could emit an event to view in app
                }}
              />
            </div>
          )}

          {/* Feedback Input (shown when requesting revision) */}
          {showFeedback && (
            <div className="bg-card border border-border rounded-xl p-4 space-y-3">
              <h4 className="text-sm font-medium">{t('checkpoints:dialog.feedbackTitle')}</h4>
              <Textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder={t('checkpoints:dialog.feedbackPlaceholder')}
                className="min-h-[100px]"
                autoFocus
              />
              <div className="flex justify-end gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setShowFeedback(false);
                    setFeedback('');
                  }}
                  disabled={isProcessing}
                >
                  {t('common:buttons.cancel')}
                </Button>
                <Button
                  size="sm"
                  onClick={handleRevisionSubmit}
                  disabled={!feedback.trim() || isProcessing}
                >
                  {isProcessing ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      {t('checkpoints:dialog.submitting')}
                    </>
                  ) : (
                    <>
                      <RefreshCw className="mr-2 h-4 w-4" />
                      {t('checkpoints:dialog.submitRevision')}
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Decision Buttons */}
        {!showFeedback && (
          <DialogFooter className="flex-col sm:flex-row gap-2 sm:gap-3">
            {/* Cancel - Destructive */}
            <Button
              variant="destructive"
              onClick={onCancel}
              disabled={isProcessing}
              className="min-h-[44px] w-full sm:w-auto order-3 sm:order-1"
            >
              <X className="mr-2 h-4 w-4" />
              {t('checkpoints:dialog.cancel')}
            </Button>

            {/* Request Revision - Secondary */}
            <Button
              variant="secondary"
              onClick={() => setShowFeedback(true)}
              disabled={isProcessing}
              className="min-h-[44px] w-full sm:w-auto order-2"
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              {t('checkpoints:dialog.revision')}
            </Button>

            {/* Approve & Continue - Primary */}
            <Button
              onClick={onApprove}
              disabled={isProcessing}
              className="min-h-[44px] w-full sm:w-auto order-1 sm:order-3"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('checkpoints:dialog.processing')}
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  {t('checkpoints:dialog.approve')}
                </>
              )}
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default CheckpointDialog;
