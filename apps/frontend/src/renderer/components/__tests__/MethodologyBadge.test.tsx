/**
 * @vitest-environment jsdom
 */
/**
 * Tests for MethodologyBadge component
 */
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { describe, it, expect, vi } from 'vitest';
import { MethodologyBadge, METHODOLOGY_COLORS, DEFAULT_METHODOLOGY_COLOR } from '../MethodologyBadge';

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'methodology.badge.native': 'Native',
        'methodology.badge.bmad': 'BMAD'
      };
      return translations[key] || key;
    }
  })
}));

describe('MethodologyBadge', () => {
  describe('rendering', () => {
    it('renders with methodology name', () => {
      render(<MethodologyBadge methodology="native" />);

      expect(screen.getByText('Native')).toBeInTheDocument();
    });

    it('displays BMAD in uppercase via i18n', () => {
      render(<MethodologyBadge methodology="bmad" />);

      // Per AC: should show "BMAD" not "Bmad"
      expect(screen.getByText('BMAD')).toBeInTheDocument();
    });

    it('handles already capitalized methodology names for known methodologies', () => {
      render(<MethodologyBadge methodology="Native" />);

      expect(screen.getByText('Native')).toBeInTheDocument();
    });

    it('capitalizes unknown methodology names', () => {
      render(<MethodologyBadge methodology="custom-plugin" />);

      expect(screen.getByText('Custom-plugin')).toBeInTheDocument();
    });
  });

  describe('color scheme', () => {
    it('applies native methodology color', () => {
      render(<MethodologyBadge methodology="native" />);

      const badge = screen.getByText('Native');
      // Check for native-specific color classes
      expect(badge).toHaveClass('bg-accent/20');
      expect(badge).toHaveClass('text-accent');
    });

    it('applies bmad methodology color', () => {
      render(<MethodologyBadge methodology="bmad" />);

      const badge = screen.getByText('BMAD');
      // Check for bmad-specific color classes
      expect(badge).toHaveClass('bg-blue-500/20');
      expect(badge).toHaveClass('text-blue-400');
    });

    it('applies default color for unknown methodologies', () => {
      render(<MethodologyBadge methodology="custom-plugin" />);

      const badge = screen.getByText('Custom-plugin');
      // Check for default muted color classes
      expect(badge).toHaveClass('bg-muted/50');
      expect(badge).toHaveClass('text-muted-foreground');
    });

    it('is case-insensitive for color matching', () => {
      render(<MethodologyBadge methodology="NATIVE" />);

      const badge = screen.getByText('Native');
      // Should still apply native colors
      expect(badge).toHaveClass('bg-accent/20');
    });
  });

  describe('size variants', () => {
    it('applies small size classes by default', () => {
      render(<MethodologyBadge methodology="native" />);

      const badge = screen.getByText('Native');
      expect(badge).toHaveClass('text-[10px]');
      expect(badge).toHaveClass('px-1.5');
    });

    it('applies medium size classes when size is md', () => {
      render(<MethodologyBadge methodology="native" size="md" />);

      const badge = screen.getByText('Native');
      expect(badge).toHaveClass('text-xs');
      expect(badge).toHaveClass('px-2');
    });
  });

  describe('custom className', () => {
    it('accepts additional CSS classes', () => {
      render(<MethodologyBadge methodology="native" className="custom-class" />);

      const badge = screen.getByText('Native');
      expect(badge).toHaveClass('custom-class');
    });

    it('merges custom classes with existing classes', () => {
      render(<MethodologyBadge methodology="native" className="my-custom-class" />);

      const badge = screen.getByText('Native');
      // Should have both methodology colors and custom class
      expect(badge).toHaveClass('bg-accent/20');
      expect(badge).toHaveClass('my-custom-class');
    });
  });

  describe('unknown methodologies', () => {
    it('displays the methodology name even if not recognized', () => {
      render(<MethodologyBadge methodology="my-custom-methodology" />);

      expect(screen.getByText('My-custom-methodology')).toBeInTheDocument();
    });

    it('uses neutral styling for unknown methodologies', () => {
      render(<MethodologyBadge methodology="unknown-methodology" />);

      const badge = screen.getByText('Unknown-methodology');
      // Should use the default muted color scheme
      expect(badge).toHaveClass('bg-muted/50');
      expect(badge).toHaveClass('text-muted-foreground');
      expect(badge).toHaveClass('border-muted');
    });
  });

  describe('i18n integration', () => {
    it('uses i18n translation for native methodology', () => {
      render(<MethodologyBadge methodology="native" />);

      // Should use translated value "Native"
      expect(screen.getByText('Native')).toBeInTheDocument();
    });

    it('uses i18n translation for bmad methodology', () => {
      render(<MethodologyBadge methodology="bmad" />);

      // Should use translated value "BMAD" (uppercase)
      expect(screen.getByText('BMAD')).toBeInTheDocument();
    });

    it('falls back to capitalization for unknown methodologies', () => {
      render(<MethodologyBadge methodology="community-plugin" />);

      // Unknown methodologies get simple capitalization
      expect(screen.getByText('Community-plugin')).toBeInTheDocument();
    });
  });

  describe('exported constants', () => {
    it('exports METHODOLOGY_COLORS with expected keys', () => {
      expect(METHODOLOGY_COLORS).toHaveProperty('native');
      expect(METHODOLOGY_COLORS).toHaveProperty('bmad');
    });

    it('exports DEFAULT_METHODOLOGY_COLOR', () => {
      expect(DEFAULT_METHODOLOGY_COLOR).toBe('bg-muted/50 text-muted-foreground border-muted');
    });
  });
});
