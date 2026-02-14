import { describe, it, expect } from 'vitest';
import { PRICING, formatPrice } from './pricing';

describe('pricing', () => {
  describe('PRICING constants', () => {
    it('should have correct pro tier pricing', () => {
      expect(PRICING.pro).toEqual({ monthly: 35, label: 'Pro' });
    });

    it('should have correct team tier pricing', () => {
      expect(PRICING.team).toEqual({ monthly: 65, label: 'Team' });
    });

    it('should have correct enterprise tier pricing', () => {
      expect(PRICING.enterprise).toEqual({ monthly: 129, label: 'Enterprise' });
    });

    it('should only include paid tiers', () => {
      const keys = Object.keys(PRICING);
      expect(keys).toEqual(['pro', 'team', 'enterprise']);
      expect(keys).not.toContain('free');
    });

    it('should have pricing in ascending order', () => {
      expect(PRICING.pro.monthly).toBeLessThan(PRICING.team.monthly);
      expect(PRICING.team.monthly).toBeLessThan(PRICING.enterprise.monthly);
    });
  });

  describe('formatPrice', () => {
    it('should format pro tier price correctly', () => {
      expect(formatPrice('pro')).toBe('$35/mo');
    });

    it('should format team tier price correctly', () => {
      expect(formatPrice('team')).toBe('$65/mo');
    });

    it('should format enterprise tier price correctly', () => {
      expect(formatPrice('enterprise')).toBe('$129/mo');
    });

    it('should include dollar sign', () => {
      expect(formatPrice('pro')).toMatch(/^\$/);
      expect(formatPrice('team')).toMatch(/^\$/);
      expect(formatPrice('enterprise')).toMatch(/^\$/);
    });

    it('should include /mo suffix', () => {
      expect(formatPrice('pro')).toMatch(/\/mo$/);
      expect(formatPrice('team')).toMatch(/\/mo$/);
      expect(formatPrice('enterprise')).toMatch(/\/mo$/);
    });

    it('should use the monthly price from PRICING constants', () => {
      expect(formatPrice('pro')).toBe(`$${PRICING.pro.monthly}/mo`);
      expect(formatPrice('team')).toBe(`$${PRICING.team.monthly}/mo`);
      expect(formatPrice('enterprise')).toBe(`$${PRICING.enterprise.monthly}/mo`);
    });
  });

  describe('pricing structure integrity', () => {
    it('should have consistent structure for all tiers', () => {
      const tiers = ['pro', 'team', 'enterprise'] as const;

      tiers.forEach(tier => {
        expect(PRICING[tier]).toHaveProperty('monthly');
        expect(PRICING[tier]).toHaveProperty('label');
        expect(typeof PRICING[tier].monthly).toBe('number');
        expect(typeof PRICING[tier].label).toBe('string');
        expect(PRICING[tier].monthly).toBeGreaterThan(0);
        expect(PRICING[tier].label.length).toBeGreaterThan(0);
      });
    });

    it('should have labels matching tier keys', () => {
      expect(PRICING.pro.label.toLowerCase()).toBe('pro');
      expect(PRICING.team.label.toLowerCase()).toBe('team');
      expect(PRICING.enterprise.label.toLowerCase()).toBe('enterprise');
    });
  });
});
