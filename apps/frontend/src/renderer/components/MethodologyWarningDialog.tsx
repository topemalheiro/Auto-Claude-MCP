/**
 * MethodologyWarningDialog - Displays version compatibility warnings
 *
 * Shows when a methodology's installed version may not be compatible
 * with the current Auto Claude version. Provides options to:
 * - Continue anyway (at user's own risk)
 * - Switch to native methodology
 */

import { useTranslation } from 'react-i18next';
import { AlertTriangle, Play, Home, RefreshCw } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from './ui/alert-dialog';
import { Button } from './ui/button';
import type { MethodologyWarningInfo } from '../hooks/useMethodologyCompatibility';

interface MethodologyWarningDialogProps {
  /** Warning information to display */
  warning: MethodologyWarningInfo | null;
  /** Called when user chooses to continue anyway */
  onContinue: () => void;
  /** Called when user chooses to switch to native */
  onSwitchToNative: () => void;
  /** Called when dialog is dismissed */
  onDismiss: () => void;
}

export function MethodologyWarningDialog({
  warning,
  onContinue,
  onSwitchToNative,
  onDismiss,
}: MethodologyWarningDialogProps) {
  const { t } = useTranslation(['tasks', 'common']);

  if (!warning?.showWarning) {
    return null;
  }

  return (
    <AlertDialog open={warning.showWarning} onOpenChange={(open) => !open && onDismiss()}>
      <AlertDialogContent className="max-w-md">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2 text-warning">
            <AlertTriangle className="h-5 w-5" />
            {t('tasks:methodology.versionWarning.title')}
          </AlertDialogTitle>
          <AlertDialogDescription className="space-y-4">
            <p>
              {t('tasks:methodology.versionWarning.description', {
                methodology: warning.methodologyName.toUpperCase(),
                version: warning.installedVersion,
                minVersion: warning.minVersion || '1.0.0',
              })}
            </p>
            {warning.warningMessage && (
              <p className="text-sm text-muted-foreground bg-muted p-3 rounded-md">
                {warning.warningMessage}
              </p>
            )}
            <p className="text-sm text-muted-foreground">
              {t('tasks:methodology.versionWarning.riskNotice')}
            </p>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="flex-col sm:flex-row gap-2">
          <Button variant="outline" onClick={onSwitchToNative} className="gap-2">
            <Home className="h-4 w-4" />
            {t('tasks:methodology.versionWarning.useNative')}
          </Button>
          <AlertDialogCancel onClick={onDismiss}>
            {t('common:cancel')}
          </AlertDialogCancel>
          <AlertDialogAction onClick={onContinue} className="gap-2">
            <Play className="h-4 w-4" />
            {t('tasks:methodology.versionWarning.continueAnyway')}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
