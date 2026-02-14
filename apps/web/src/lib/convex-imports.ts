/**
 * Type-safe lazy imports for Convex dependencies.
 *
 * These are loaded dynamically to avoid build errors in self-hosted mode
 * when Convex packages aren't fully configured.
 *
 * All imports use the `as typeof import(...)` pattern to maintain full type safety
 * while still using require() for conditional loading.
 */

import type { ConvexReactClient } from "convex/react";

// Lazy-loaded singleton instances
let _convexReact: typeof import("convex/react") | null = null;
let _betterAuthReact: typeof import("@convex-dev/better-auth/react") | null = null;
let _authClient: typeof import("@/lib/auth-client") | null = null;
let _convexApi: typeof import("../../convex/_generated/api") | null = null;
let _convexClientInstance: ConvexReactClient | null = null;

/**
 * Get the convex/react module with full type safety.
 * Includes: useQuery, useMutation, useAction, Authenticated, Unauthenticated, AuthLoading, etc.
 */
export function getConvexReact() {
  if (!_convexReact) {
    _convexReact = require("convex/react") as typeof import("convex/react");
  }
  return _convexReact;
}

/**
 * Get the @convex-dev/better-auth/react module with full type safety.
 * Includes: ConvexBetterAuthProvider
 */
export function getBetterAuthReact() {
  if (!_betterAuthReact) {
    _betterAuthReact = require("@convex-dev/better-auth/react") as typeof import("@convex-dev/better-auth/react");
  }
  return _betterAuthReact;
}

/**
 * Get the auth-client module with full type safety.
 * Returns the authClient instance configured for Better Auth.
 */
export function getAuthClient() {
  if (!_authClient) {
    _authClient = require("@/lib/auth-client") as typeof import("@/lib/auth-client");
  }
  return _authClient;
}

/**
 * Get the Convex API module with full type safety.
 * Includes all generated API endpoints from convex/_generated/api.
 */
export function getConvexApi() {
  if (!_convexApi) {
    _convexApi = require("../../convex/_generated/api") as typeof import("../../convex/_generated/api");
  }
  return _convexApi;
}

/**
 * Get or create the singleton Convex client instance.
 *
 * @param convexUrl - The Convex deployment URL (required on first call)
 * @returns The ConvexReactClient instance
 */
export function getConvexClient(convexUrl?: string): ConvexReactClient {
  if (!_convexClientInstance) {
    if (!convexUrl) {
      throw new Error("convexUrl is required to initialize ConvexReactClient");
    }
    const { ConvexReactClient } = getConvexReact();
    _convexClientInstance = new ConvexReactClient(convexUrl);
  }
  return _convexClientInstance;
}

/**
 * Re-export commonly used types for convenience.
 * These can be imported directly without runtime overhead.
 */
export type {
  ConvexReactClient,
  // Additional commonly used types can be added here
} from "convex/react";
