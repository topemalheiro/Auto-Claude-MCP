export const PRICING = {
  pro: { monthly: 35, label: "Pro" },
  team: { monthly: 65, label: "Team" },
  enterprise: { monthly: 129, label: "Enterprise" },
} as const;

export function formatPrice(tier: keyof typeof PRICING): string {
  return `$${PRICING[tier].monthly}/mo`;
}
