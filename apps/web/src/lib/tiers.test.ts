import { describe, it, expect } from 'vitest';
import { hasTierAccess, type Tier } from './tiers';

describe('tiers', () => {
  describe('hasTierAccess', () => {
    describe('free tier access', () => {
      it('should grant access to free tier with free subscription', () => {
        expect(hasTierAccess('free', 'free')).toBe(true);
      });

      it('should grant access to free tier with pro subscription', () => {
        expect(hasTierAccess('pro', 'free')).toBe(true);
      });

      it('should grant access to free tier with team subscription', () => {
        expect(hasTierAccess('team', 'free')).toBe(true);
      });

      it('should grant access to free tier with enterprise subscription', () => {
        expect(hasTierAccess('enterprise', 'free')).toBe(true);
      });
    });

    describe('pro tier access', () => {
      it('should deny pro tier access with free subscription', () => {
        expect(hasTierAccess('free', 'pro')).toBe(false);
      });

      it('should grant pro tier access with pro subscription', () => {
        expect(hasTierAccess('pro', 'pro')).toBe(true);
      });

      it('should grant pro tier access with team subscription', () => {
        expect(hasTierAccess('team', 'pro')).toBe(true);
      });

      it('should grant pro tier access with enterprise subscription', () => {
        expect(hasTierAccess('enterprise', 'pro')).toBe(true);
      });
    });

    describe('team tier access', () => {
      it('should deny team tier access with free subscription', () => {
        expect(hasTierAccess('free', 'team')).toBe(false);
      });

      it('should deny team tier access with pro subscription', () => {
        expect(hasTierAccess('pro', 'team')).toBe(false);
      });

      it('should grant team tier access with team subscription', () => {
        expect(hasTierAccess('team', 'team')).toBe(true);
      });

      it('should grant team tier access with enterprise subscription', () => {
        expect(hasTierAccess('enterprise', 'team')).toBe(true);
      });
    });

    describe('enterprise tier access', () => {
      it('should deny enterprise tier access with free subscription', () => {
        expect(hasTierAccess('free', 'enterprise')).toBe(false);
      });

      it('should deny enterprise tier access with pro subscription', () => {
        expect(hasTierAccess('pro', 'enterprise')).toBe(false);
      });

      it('should deny enterprise tier access with team subscription', () => {
        expect(hasTierAccess('team', 'enterprise')).toBe(false);
      });

      it('should grant enterprise tier access with enterprise subscription', () => {
        expect(hasTierAccess('enterprise', 'enterprise')).toBe(true);
      });
    });

    describe('undefined tier handling', () => {
      it('should deny access when current tier is undefined', () => {
        expect(hasTierAccess(undefined, 'free')).toBe(false);
        expect(hasTierAccess(undefined, 'pro')).toBe(false);
        expect(hasTierAccess(undefined, 'team')).toBe(false);
        expect(hasTierAccess(undefined, 'enterprise')).toBe(false);
      });
    });

    describe('tier hierarchy verification', () => {
      const tiers: Tier[] = ['free', 'pro', 'team', 'enterprise'];

      it('should maintain proper tier hierarchy', () => {
        // Verify that each tier grants access to all lower tiers
        for (let i = 0; i < tiers.length; i++) {
          const currentTier = tiers[i];
          for (let j = 0; j <= i; j++) {
            const requiredTier = tiers[j];
            expect(hasTierAccess(currentTier, requiredTier)).toBe(true);
          }
          for (let j = i + 1; j < tiers.length; j++) {
            const requiredTier = tiers[j];
            expect(hasTierAccess(currentTier, requiredTier)).toBe(false);
          }
        }
      });
    });
  });
});
