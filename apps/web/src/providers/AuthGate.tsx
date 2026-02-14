"use client";

import { ReactNode } from "react";
import { CLOUD_MODE } from "@/lib/cloud-mode";
import { getConvexReact } from "@/lib/convex-imports";

/**
 * Auth-aware wrapper components that work in both cloud and self-hosted mode.
 *
 * In cloud mode: delegates to Convex's Authenticated/Unauthenticated/AuthLoading.
 * In self-hosted mode: renders content directly (no auth required).
 */

export function CloudAuthenticated({ children }: { children: ReactNode }) {
  if (!CLOUD_MODE) {
    // Self-hosted: always render (no auth)
    return <>{children}</>;
  }
  const { Authenticated } = getConvexReact();
  return <Authenticated>{children}</Authenticated>;
}

export function CloudUnauthenticated({ children }: { children: ReactNode }) {
  if (!CLOUD_MODE) {
    // Self-hosted: never render the unauthenticated state
    return null;
  }
  const { Unauthenticated } = getConvexReact();
  return <Unauthenticated>{children}</Unauthenticated>;
}

export function CloudAuthLoading({ children }: { children: ReactNode }) {
  if (!CLOUD_MODE) {
    // Self-hosted: no auth loading state
    return null;
  }
  const { AuthLoading } = getConvexReact();
  return <AuthLoading>{children}</AuthLoading>;
}
