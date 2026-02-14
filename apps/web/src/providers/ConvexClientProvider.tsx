"use client";

import { ReactNode } from "react";
import { CONVEX_URL } from "@/lib/cloud-mode";
import {
  getBetterAuthReact,
  getAuthClient,
  getConvexClient,
} from "@/lib/convex-imports";

/**
 * ConvexClientProvider wraps the app with Convex's real-time data layer
 * when running in cloud mode (NEXT_PUBLIC_CONVEX_URL is set).
 *
 * In self-hosted mode (no NEXT_PUBLIC_CONVEX_URL), it renders children
 * directly without any Convex context.
 */
function ConvexClientProviderInner({
  children,
  initialToken,
}: {
  children: ReactNode;
  initialToken?: string | null;
}) {
  if (!CONVEX_URL) {
    // Self-hosted mode: no Convex, render children directly
    return <>{children}</>;
  }

  // Cloud mode: lazy-load Convex dependencies with full type safety
  const { ConvexBetterAuthProvider } = getBetterAuthReact();
  const { authClient } = getAuthClient();
  const convex = getConvexClient(CONVEX_URL);

  return (
    <ConvexBetterAuthProvider
      client={convex}
      authClient={authClient}
      initialToken={initialToken}
    >
      {children}
    </ConvexBetterAuthProvider>
  );
}

export function ConvexClientProvider({
  children,
  initialToken,
}: {
  children: ReactNode;
  initialToken?: string | null;
}) {
  return (
    <ConvexClientProviderInner initialToken={initialToken}>
      {children}
    </ConvexClientProviderInner>
  );
}
