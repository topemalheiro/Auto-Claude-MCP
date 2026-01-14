/**
 * MethodologySelector - Dropdown for selecting task execution methodology
 *
 * Allows users to choose which methodology plugin to use for task execution:
 * - Native: Built-in methodology with spec creation and implementation phases
 * - BMAD: Community plugin for comprehensive planning workflows (future)
 *
 * Displays verified badge for bundled methodologies and warning badge for
 * unverified community plugins (AC #3, NFR15).
 */
import { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { Workflow, BadgeCheck, AlertTriangle, Loader2 } from 'lucide-react';
import { Label } from '../ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '../ui/select';
import { Badge } from '../ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger
} from '../ui/tooltip';
import { useMethodologies } from './useMethodologies';
import type { MethodologyInfo } from '../../../shared/types/methodology';

interface MethodologySelectorProps {
  /** Currently selected methodology name */
  value: string;
  /** Callback when methodology changes */
  onChange: (value: string) => void;
  /** Whether the selector is disabled */
  disabled?: boolean;
  /** Optional ID prefix for accessibility */
  idPrefix?: string;
}

/**
 * Render a methodology option with verified badge if applicable
 */
function MethodologyOption({
  methodology,
  showDescription = true
}: {
  methodology: MethodologyInfo;
  showDescription?: boolean;
}) {
  const { t } = useTranslation(['tasks']);

  return (
    <div className="flex items-center gap-2 w-full">
      <Workflow className="h-4 w-4 shrink-0 text-primary" />
      <div className="flex flex-col flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="capitalize">{methodology.name}</span>
          {methodology.is_verified ? (
            <Badge
              variant="secondary"
              className="h-5 px-1.5 text-[10px] font-medium gap-0.5"
            >
              <BadgeCheck className="h-3 w-3" />
              {t('tasks:methodology.verified')}
            </Badge>
          ) : (
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge
                  variant="outline"
                  className="h-5 px-1.5 text-[10px] font-medium gap-0.5 border-warning text-warning"
                >
                  <AlertTriangle className="h-3 w-3" />
                  {t('tasks:methodology.unverified')}
                </Badge>
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-xs">
                <p>{t('tasks:methodology.unverifiedWarning')}</p>
              </TooltipContent>
            </Tooltip>
          )}
        </div>
        {showDescription && methodology.description && (
          <span className="text-xs text-muted-foreground truncate">
            {methodology.description}
          </span>
        )}
      </div>
    </div>
  );
}

export const MethodologySelector = memo(function MethodologySelector({
  value,
  onChange,
  disabled = false,
  idPrefix = ''
}: MethodologySelectorProps) {
  const { t } = useTranslation(['tasks']);
  const { methodologies, isLoading, error } = useMethodologies();
  const prefix = idPrefix ? `${idPrefix}-` : '';

  // Find the currently selected methodology
  const selectedMethodology = methodologies.find(m => m.name === value);

  // If loading and no value, show loading state
  const isLoadingState = isLoading && methodologies.length === 0;

  return (
    <div className="space-y-2">
      <Label
        htmlFor={`${prefix}methodology`}
        className="text-sm font-medium text-foreground"
      >
        {t('tasks:methodology.label')}
      </Label>
      <Select
        value={value}
        onValueChange={onChange}
        disabled={disabled || isLoadingState}
      >
        <SelectTrigger
          id={`${prefix}methodology`}
          aria-describedby={`${prefix}methodology-help`}
          className="h-10"
        >
          {isLoadingState ? (
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              <span className="text-muted-foreground">
                {t('tasks:methodology.loading')}
              </span>
            </div>
          ) : selectedMethodology ? (
            <MethodologyOption
              methodology={selectedMethodology}
              showDescription={false}
            />
          ) : (
            <SelectValue placeholder={t('tasks:methodology.placeholder')} />
          )}
        </SelectTrigger>
        <SelectContent>
          {error ? (
            <div className="px-2 py-4 text-center text-sm text-destructive">
              {error}
            </div>
          ) : methodologies.length === 0 ? (
            <div className="px-2 py-4 text-center text-sm text-muted-foreground">
              {t('tasks:methodology.noMethodologies')}
            </div>
          ) : (
            methodologies.map((methodology) => (
              <SelectItem
                key={methodology.name}
                value={methodology.name}
                className="py-2"
              >
                <MethodologyOption methodology={methodology} />
              </SelectItem>
            ))
          )}
        </SelectContent>
      </Select>
      <p
        id={`${prefix}methodology-help`}
        className="text-xs text-muted-foreground"
      >
        {t('tasks:methodology.helpText')}
      </p>
    </div>
  );
});
