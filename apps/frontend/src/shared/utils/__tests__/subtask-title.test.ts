/**
 * Unit tests for subtask title extraction utility
 * Tests extractSubtaskTitle() which derives concise titles from subtask descriptions
 */
import { describe, it, expect } from 'vitest';
import { extractSubtaskTitle } from '../subtask-title';

describe('extractSubtaskTitle', () => {
  describe('short descriptions (<=80 chars)', () => {
    it('should return short description as-is', () => {
      const desc = 'Fix the login button styling';
      expect(extractSubtaskTitle(desc)).toBe(desc);
    });

    it('should return description exactly at 80 chars as-is', () => {
      const desc = 'A'.repeat(80);
      expect(extractSubtaskTitle(desc)).toBe(desc);
    });
  });

  describe('long descriptions with sentence boundary', () => {
    it('should truncate at first sentence ending with period-space', () => {
      const desc = 'Fix the login button styling. Then update the tests and make sure everything works correctly across all browsers.';
      expect(extractSubtaskTitle(desc)).toBe('Fix the login button styling');
    });

    it('should truncate at first sentence ending with colon-space', () => {
      const desc = 'Fix the login button: Then update the tests and make sure everything works correctly across all browsers and devices.';
      expect(extractSubtaskTitle(desc)).toBe('Fix the login button');
    });
  });

  describe('long descriptions without sentence boundary', () => {
    it('should truncate at word boundary with ellipsis', () => {
      const desc = 'This is a very long description that does not have any sentence boundaries and keeps going on and on without stopping at all';
      const result = extractSubtaskTitle(desc);
      expect(result.endsWith('\u2026')).toBe(true);
      expect(result.length).toBeLessThanOrEqual(81); // 80 + ellipsis char
      // Should end with a space before the truncation point (word boundary)
      const withoutEllipsis = result.slice(0, -1);
      expect(desc.charAt(withoutEllipsis.length)).toMatch(/\s/);
    });

    it('should truncate at last space before maxLength', () => {
      const desc = 'word '.repeat(20); // 100 chars, spaces every 5 chars
      const result = extractSubtaskTitle(desc.trim());
      expect(result.endsWith('\u2026')).toBe(true);
    });
  });

  describe('empty and falsy inputs', () => {
    it('should return empty string for empty string', () => {
      expect(extractSubtaskTitle('')).toBe('');
    });

    it('should return empty string for undefined', () => {
      expect(extractSubtaskTitle(undefined)).toBe('');
    });

    it('should return empty string for null', () => {
      expect(extractSubtaskTitle(null)).toBe('');
    });

    it('should return empty string for whitespace-only string', () => {
      expect(extractSubtaskTitle('   ')).toBe('');
    });
  });

  describe('boundary at maxLength', () => {
    it('should return as-is when exactly at default maxLength', () => {
      const desc = 'x'.repeat(80);
      expect(extractSubtaskTitle(desc)).toBe(desc);
    });

    it('should truncate when one char over maxLength', () => {
      const desc = 'x'.repeat(81);
      const result = extractSubtaskTitle(desc);
      expect(result).toContain('\u2026');
    });
  });

  describe('custom maxLength parameter', () => {
    it('should respect custom maxLength of 40', () => {
      const desc = 'This is a medium length description that exceeds forty characters';
      const result = extractSubtaskTitle(desc, 40);
      // Should truncate since > 40 chars
      expect(result.length).toBeLessThanOrEqual(41);
    });

    it('should return short description as-is with large maxLength', () => {
      const desc = 'Short description';
      expect(extractSubtaskTitle(desc, 200)).toBe(desc);
    });

    it('should truncate with custom maxLength at sentence boundary', () => {
      const desc = 'Fix bug. Then do more work that is unnecessary and verbose and goes on forever and ever.';
      expect(extractSubtaskTitle(desc, 40)).toBe('Fix bug');
    });
  });

  describe('terminal period edge cases', () => {
    it('should handle single sentence ending with period and no trailing space', () => {
      const desc = 'Implement the complete authentication flow for the new user registration module.';
      expect(extractSubtaskTitle(desc)).toBe('Implement the complete authentication flow for the new user registration module');
    });

    it('should handle long single sentence with terminal period', () => {
      const desc = 'This is a very long single sentence that exceeds the maximum length threshold and ends with a period.';
      const result = extractSubtaskTitle(desc);
      // Should truncate at word boundary since sentence is too long
      expect(result.endsWith('\u2026')).toBe(true);
      expect(result.length).toBeLessThanOrEqual(81);
    });

    it('should handle period followed by newline', () => {
      const desc = 'Fix the login button.\nThen update the tests.';
      expect(extractSubtaskTitle(desc)).toBe('Fix the login button');
    });
  });

  describe('degenerate truncation cases', () => {
    it('should not exceed maxLength even for single-word input', () => {
      const longWord = 'a'.repeat(100);
      const result = extractSubtaskTitle(longWord, 80);
      // Should be 79 chars + ellipsis = 80 total
      expect(result.length).toBeLessThanOrEqual(80);
      expect(result.endsWith('\u2026')).toBe(true);
    });

    it('should handle very short maxLength gracefully', () => {
      const desc = 'This is a description';
      const result = extractSubtaskTitle(desc, 5);
      expect(result.length).toBeLessThanOrEqual(5);
      expect(result.endsWith('\u2026')).toBe(true);
    });
  });
});
