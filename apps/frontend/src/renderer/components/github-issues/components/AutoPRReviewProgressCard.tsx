/**
 * AutoPRReviewProgressCard Component
 *
 * Displays the progress of an Auto-PR-Review operation with:
 * - Progress bar showing iteration progress
 * - Substep indicator showing current activity
 * - CI checks visualization
 * - External bot status badges
 * - Cancel button with confirmation
 *
 * CRITICAL: This component displays progress toward human approval.
 * The system NEVER auto-merges - human approval is always required.
 */

import React, { useState, useCallback, useMemo } from 'react';
import type {
  AutoPRReviewProgress,
  CICheckStatus,
  ExternalBotStatus,
  AutoPRReviewStatus,
} from '../types';

// =============================================================================
// Types
// =============================================================================

export interface AutoPRReviewProgressCardProps {
  /** Progress data for the PR review */
  progress: AutoPRReviewProgress;

  /** Callback to cancel the review */
  onCancel?: (repository: string, prNumber: number, reason?: string) => Promise<void>;

  /** Optional CSS class name */
  className?: string;

  /** Translation function for i18n (defaults to identity) */
  t?: (key: string) => string;
}

interface StatusConfig {
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
}

// =============================================================================
// Constants
// =============================================================================

/**
 * Status configurations for visual styling
 */
const STATUS_CONFIG: Record<AutoPRReviewStatus, StatusConfig> = {
  idle: {
    label: 'autoPRReview.status.idle',
    color: 'text-gray-600',
    bgColor: 'bg-gray-100',
    borderColor: 'border-gray-300',
  },
  awaiting_checks: {
    label: 'autoPRReview.status.awaitingChecks',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-300',
  },
  pr_reviewing: {
    label: 'autoPRReview.status.reviewing',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-300',
  },
  pr_fixing: {
    label: 'autoPRReview.status.fixing',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-300',
  },
  pr_ready_to_merge: {
    label: 'autoPRReview.status.readyToMerge',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-300',
  },
  completed: {
    label: 'autoPRReview.status.completed',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-300',
  },
  failed: {
    label: 'autoPRReview.status.failed',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-300',
  },
  cancelled: {
    label: 'autoPRReview.status.cancelled',
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-300',
  },
  max_iterations: {
    label: 'autoPRReview.status.maxIterations',
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-300',
  },
};

/**
 * CI check status configurations
 */
const CI_STATUS_CONFIG: Record<CICheckStatus['status'], { icon: string; color: string }> = {
  pending: { icon: '\u23F3', color: 'text-gray-500' }, // Hourglass
  in_progress: { icon: '\u25B6', color: 'text-blue-500' }, // Play
  success: { icon: '\u2714', color: 'text-green-500' }, // Check mark
  failure: { icon: '\u2718', color: 'text-red-500' }, // X mark
  cancelled: { icon: '\u26AA', color: 'text-gray-400' }, // Circle
  skipped: { icon: '\u2192', color: 'text-gray-400' }, // Arrow
};

// =============================================================================
// Helper Components
// =============================================================================

/**
 * Progress bar component showing iteration progress
 */
function ProgressBar({
  current,
  max,
  className = '',
}: {
  current: number;
  max: number;
  className?: string;
}) {
  const percentage = Math.min(100, Math.round((current / max) * 100));

  return (
    <div
      className={`w-full bg-gray-200 rounded-full h-2.5 ${className}`}
      role="progressbar"
      aria-valuenow={current}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-label={`Progress: ${current} of ${max} iterations`}
    >
      <div
        className="bg-blue-600 h-2.5 rounded-full transition-all duration-300 ease-in-out"
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
}

/**
 * Single CI check item
 */
function CICheckItem({ check, t }: { check: CICheckStatus; t: (key: string) => string }) {
  const config = CI_STATUS_CONFIG[check.status];

  return (
    <div
      className="flex items-center gap-2 text-sm py-1"
      title={check.conclusion ?? t(`autoPRReview.ciStatus.${check.status}`)}
    >
      <span className={config.color} aria-hidden="true">
        {config.icon}
      </span>
      <span className="truncate flex-1">{check.name}</span>
      {check.detailsUrl && (
        <a
          href={check.detailsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-500 hover:text-blue-700 text-xs"
          aria-label={t('autoPRReview.viewDetails')}
        >
          {t('autoPRReview.details')}
        </a>
      )}
    </div>
  );
}

/**
 * CI checks summary badge
 */
function CISummaryBadge({
  summary,
  t,
}: {
  summary: AutoPRReviewProgress['ciSummary'];
  t: (key: string) => string;
}) {
  const { total, passed, failed, pending } = summary;

  if (total === 0) {
    return (
      <span className="text-sm text-gray-500">{t('autoPRReview.noChecks')}</span>
    );
  }

  return (
    <div className="flex items-center gap-2 text-sm" aria-label={`CI: ${passed}/${total} passed`}>
      {passed > 0 && (
        <span className="text-green-600">
          {'\u2714'} {passed}
        </span>
      )}
      {failed > 0 && (
        <span className="text-red-600">
          {'\u2718'} {failed}
        </span>
      )}
      {pending > 0 && (
        <span className="text-gray-500">
          {'\u23F3'} {pending}
        </span>
      )}
    </div>
  );
}

/**
 * External bot status badge
 */
function BotStatusBadge({ bot, t }: { bot: ExternalBotStatus; t: (key: string) => string }) {
  const statusClass = bot.hasCommented
    ? bot.isVerified
      ? 'bg-green-100 text-green-700 border-green-300'
      : 'bg-yellow-100 text-yellow-700 border-yellow-300'
    : 'bg-gray-100 text-gray-600 border-gray-300';

  const statusIcon = bot.hasCommented
    ? bot.isVerified
      ? '\u2714' // Check mark
      : '\u26A0' // Warning
    : '\u23F3'; // Hourglass

  const statusLabel = bot.hasCommented
    ? bot.isVerified
      ? t('autoPRReview.botVerified')
      : t('autoPRReview.botUnverified')
    : t('autoPRReview.botPending');

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs border ${statusClass}`}
      title={statusLabel}
      aria-label={`${bot.botName}: ${statusLabel}`}
    >
      <span aria-hidden="true">{statusIcon}</span>
      <span className="font-medium">{bot.botName}</span>
      {bot.findingsCount !== undefined && bot.findingsCount > 0 && (
        <span className="bg-white/50 px-1.5 rounded-full">
          {bot.findingsCount} {t('autoPRReview.findings')}
        </span>
      )}
    </div>
  );
}

/**
 * Elapsed time display
 */
function ElapsedTime({ ms, t }: { ms: number; t: (key: string) => string }) {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  let display: string;
  if (hours > 0) {
    display = `${hours}h ${minutes % 60}m`;
  } else if (minutes > 0) {
    display = `${minutes}m ${seconds % 60}s`;
  } else {
    display = `${seconds}s`;
  }

  return (
    <span className="text-sm text-gray-500" aria-label={t('autoPRReview.elapsedTime')}>
      {display}
    </span>
  );
}

// =============================================================================
// Main Component
// =============================================================================

/**
 * AutoPRReviewProgressCard - Displays Auto-PR-Review progress with rich UI
 *
 * @example
 * ```tsx
 * <AutoPRReviewProgressCard
 *   progress={reviewProgress}
 *   onCancel={handleCancel}
 *   t={t}
 * />
 * ```
 */
export function AutoPRReviewProgressCard({
  progress,
  onCancel,
  className = '',
  t = (key: string) => key.split('.').pop() ?? key, // Fallback: return last key segment
}: AutoPRReviewProgressCardProps) {
  const [isCancelling, setIsCancelling] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const [showCIDetails, setShowCIDetails] = useState(false);

  // Get status configuration
  const statusConfig = STATUS_CONFIG[progress.status];

  // Memoized values
  const isInProgress = useMemo(
    () => ['awaiting_checks', 'pr_reviewing', 'pr_fixing'].includes(progress.status),
    [progress.status]
  );

  const isTerminal = useMemo(
    () => ['completed', 'failed', 'cancelled', 'pr_ready_to_merge', 'max_iterations'].includes(progress.status),
    [progress.status]
  );

  // Handle cancel action
  const handleCancelClick = useCallback(() => {
    if (progress.isCancellable) {
      setShowCancelConfirm(true);
    }
  }, [progress.isCancellable]);

  const handleCancelConfirm = useCallback(async () => {
    if (!onCancel) return;

    setIsCancelling(true);
    try {
      await onCancel(progress.repository, progress.prNumber, 'User requested cancellation');
    } finally {
      setIsCancelling(false);
      setShowCancelConfirm(false);
    }
  }, [onCancel, progress.repository, progress.prNumber]);

  const handleCancelDismiss = useCallback(() => {
    setShowCancelConfirm(false);
  }, []);

  // Toggle CI details
  const toggleCIDetails = useCallback(() => {
    setShowCIDetails((prev) => !prev);
  }, []);

  return (
    <div
      className={`rounded-lg border ${statusConfig.borderColor} ${statusConfig.bgColor} p-4 ${className}`}
      role="region"
      aria-label={t('autoPRReview.progressCard')}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* PR identifier */}
          <h3 className="font-semibold text-gray-900 truncate">
            {progress.repository}#{progress.prNumber}
          </h3>

          {/* Status badge */}
          <div className="flex items-center gap-2 mt-1">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${statusConfig.bgColor} ${statusConfig.color}`}
            >
              {t(statusConfig.label)}
            </span>
            <ElapsedTime ms={progress.elapsedMs} t={t} />
          </div>
        </div>

        {/* Cancel button */}
        {progress.isCancellable && onCancel && (
          <button
            type="button"
            onClick={handleCancelClick}
            disabled={isCancelling}
            className="px-3 py-1.5 text-sm font-medium text-red-600 bg-white border border-red-300 rounded-md hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label={t('autoPRReview.cancelReview')}
          >
            {isCancelling ? t('autoPRReview.cancelling') : t('autoPRReview.cancel')}
          </button>
        )}
      </div>

      {/* Progress section */}
      <div className="mt-4">
        {/* Iteration progress */}
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="text-gray-600">
            {t('autoPRReview.iteration')} {progress.currentIteration}/{progress.maxIterations}
          </span>
          {progress.fixedFindingsCount > 0 && (
            <span className="text-green-600">
              {progress.fixedFindingsCount} {t('autoPRReview.fixed')}
            </span>
          )}
          {progress.remainingFindingsCount > 0 && (
            <span className="text-amber-600">
              {progress.remainingFindingsCount} {t('autoPRReview.remaining')}
            </span>
          )}
        </div>

        {/* Progress bar */}
        <ProgressBar
          current={progress.currentIteration}
          max={progress.maxIterations}
          className="mb-4"
        />

        {/* Current activity */}
        {progress.currentActivity && isInProgress && (
          <div className="flex items-center gap-2 text-sm text-gray-600 mb-4">
            <span
              className="animate-spin inline-block w-4 h-4 border-2 border-gray-300 border-t-blue-600 rounded-full"
              aria-hidden="true"
            />
            <span>{progress.currentActivity}</span>
          </div>
        )}

        {/* Error message */}
        {progress.errorMessage && (
          <div
            className="p-3 mb-4 bg-red-100 border border-red-300 rounded-md text-sm text-red-700"
            role="alert"
          >
            <strong>{t('autoPRReview.error')}:</strong> {progress.errorMessage}
          </div>
        )}
      </div>

      {/* CI Checks section */}
      <div className="border-t border-gray-200 pt-4 mt-4">
        <button
          type="button"
          onClick={toggleCIDetails}
          className="flex items-center justify-between w-full text-left"
          aria-expanded={showCIDetails}
          aria-controls="ci-checks-details"
        >
          <span className="text-sm font-medium text-gray-700">
            {t('autoPRReview.ciChecks')}
          </span>
          <div className="flex items-center gap-2">
            <CISummaryBadge summary={progress.ciSummary} t={t} />
            <span
              className="text-gray-400 transform transition-transform duration-200"
              style={{ transform: showCIDetails ? 'rotate(180deg)' : 'rotate(0deg)' }}
              aria-hidden="true"
            >
              {'\u25BC'} {/* Down arrow */}
            </span>
          </div>
        </button>

        {/* CI checks details (expandable) */}
        {showCIDetails && progress.ciChecks.length > 0 && (
          <div
            id="ci-checks-details"
            className="mt-2 pl-2 border-l-2 border-gray-200 max-h-48 overflow-y-auto"
          >
            {progress.ciChecks.map((check, index) => (
              <CICheckItem key={`${check.name}-${index}`} check={check} t={t} />
            ))}
          </div>
        )}

        {showCIDetails && progress.ciChecks.length === 0 && (
          <p className="mt-2 text-sm text-gray-500 italic">
            {t('autoPRReview.noChecksYet')}
          </p>
        )}
      </div>

      {/* External Bots section */}
      {progress.externalBots.length > 0 && (
        <div className="border-t border-gray-200 pt-4 mt-4">
          <span className="text-sm font-medium text-gray-700 block mb-2">
            {t('autoPRReview.externalBots')}
          </span>
          <div className="flex flex-wrap gap-2">
            {progress.externalBots.map((bot) => (
              <BotStatusBadge key={bot.botName} bot={bot} t={t} />
            ))}
          </div>
        </div>
      )}

      {/* SHA info (for debugging/verification) */}
      {progress.currentSha && (
        <div className="border-t border-gray-200 pt-4 mt-4">
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <span>{t('autoPRReview.sha')}:</span>
            <code className="font-mono bg-gray-100 px-1.5 py-0.5 rounded">
              {progress.currentSha.substring(0, 7)}
            </code>
            {progress.originalSha && progress.currentSha !== progress.originalSha && (
              <span className="text-amber-500" title={t('autoPRReview.shaChanged')}>
                {'\u26A0'} {t('autoPRReview.changed')}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Ready to merge notice */}
      {progress.status === 'pr_ready_to_merge' && (
        <div
          className="mt-4 p-3 bg-green-100 border border-green-300 rounded-md text-sm text-green-700"
          role="status"
        >
          <strong>{t('autoPRReview.readyForReview')}</strong>
          <p className="mt-1">{t('autoPRReview.humanApprovalRequired')}</p>
        </div>
      )}

      {/* Cancel confirmation modal */}
      {showCancelConfirm && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          role="dialog"
          aria-modal="true"
          aria-labelledby="cancel-dialog-title"
        >
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-sm w-full mx-4">
            <h4
              id="cancel-dialog-title"
              className="text-lg font-semibold text-gray-900 mb-2"
            >
              {t('autoPRReview.cancelConfirmTitle')}
            </h4>
            <p className="text-sm text-gray-600 mb-4">
              {t('autoPRReview.cancelConfirmMessage')}
            </p>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={handleCancelDismiss}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
              >
                {t('autoPRReview.keepRunning')}
              </button>
              <button
                type="button"
                onClick={handleCancelConfirm}
                disabled={isCancelling}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50"
              >
                {isCancelling ? t('autoPRReview.cancelling') : t('autoPRReview.confirmCancel')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Exports
// =============================================================================

export type { AutoPRReviewProgress, CICheckStatus, ExternalBotStatus };

export default AutoPRReviewProgressCard;
