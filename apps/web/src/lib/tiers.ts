export type Tier = "free" | "pro" | "team" | "enterprise";

const TIER_LEVELS: Record<Tier, number> = {
  free: 0,
  pro: 1,
  team: 2,
  enterprise: 3,
};

export function hasTierAccess(currentTier: Tier | undefined, requiredTier: Tier): boolean {
  if (!currentTier) return false;
  return TIER_LEVELS[currentTier] >= TIER_LEVELS[requiredTier];
}
