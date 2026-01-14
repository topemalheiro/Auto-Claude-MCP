import { useTranslation } from 'react-i18next';
import { Badge } from './ui/badge';
import { cn } from '../lib/utils';

/**
 * Color scheme for methodology badges.
 * Uses Tailwind classes compatible with the Oscura design system.
 */
const METHODOLOGY_COLORS: Record<string, string> = {
  native: 'bg-accent/20 text-accent border-accent/30',
  bmad: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
};

const DEFAULT_METHODOLOGY_COLOR = 'bg-muted/50 text-muted-foreground border-muted';

/** Known methodologies that have i18n translations */
const KNOWN_METHODOLOGIES = ['native', 'bmad'] as const;

interface MethodologyBadgeProps {
  /** Methodology name (e.g., 'native', 'bmad') */
  methodology: string;
  /** Badge size variant */
  size?: 'sm' | 'md';
  /** Additional CSS classes */
  className?: string;
}

/**
 * Badge component for displaying methodology type on task cards.
 * Shows color-coded badges for known methodologies (Native, BMAD)
 * and neutral styling for unknown/community methodologies.
 */
export function MethodologyBadge({
  methodology,
  size = 'sm',
  className
}: MethodologyBadgeProps) {
  const { t } = useTranslation('tasks');
  const normalizedMethodology = methodology.toLowerCase();
  const colorClass = METHODOLOGY_COLORS[normalizedMethodology] || DEFAULT_METHODOLOGY_COLOR;

  // Use i18n for known methodologies, capitalize for unknown
  const isKnown = KNOWN_METHODOLOGIES.includes(normalizedMethodology as typeof KNOWN_METHODOLOGIES[number]);
  const displayName = isKnown
    ? t(`methodology.badge.${normalizedMethodology}`)
    : methodology.charAt(0).toUpperCase() + methodology.slice(1);

  return (
    <Badge
      variant="outline"
      className={cn(
        colorClass,
        size === 'sm' ? 'text-[10px] px-1.5 py-0' : 'text-xs px-2 py-0.5',
        className
      )}
    >
      {displayName}
    </Badge>
  );
}

// Export color constants for potential reuse
export { METHODOLOGY_COLORS, DEFAULT_METHODOLOGY_COLOR };
