import { convexBetterAuthNextJs } from "@convex-dev/better-auth/nextjs";

/**
 * Server-side auth helpers powered by Convex + Better Auth.
 *
 * In cloud mode (NEXT_PUBLIC_CONVEX_URL & CONVEX_SITE_URL are set),
 * this provides the full auth integration. In self-hosted mode,
 * the helpers are stubs that return safe defaults so the build
 * doesn't crash.
 */

const isCloudMode =
  !!process.env.NEXT_PUBLIC_CONVEX_URL && !!process.env.CONVEX_SITE_URL;

function getAuthHelpers() {
  if (!isCloudMode) {
    return null;
  }
  return convexBetterAuthNextJs({
    convexUrl: process.env.NEXT_PUBLIC_CONVEX_URL!,
    convexSiteUrl: process.env.CONVEX_SITE_URL!,
  });
}

let _helpers: ReturnType<typeof getAuthHelpers>;
function helpers() {
  if (_helpers === undefined) {
    _helpers = getAuthHelpers();
  }
  return _helpers;
}

// Lazy accessors: safe in both cloud and self-hosted mode.
export const handler = {
  GET: async (req: Request) => {
    const h = helpers();
    if (!h) return new Response("Auth not configured", { status: 404 });
    return h.handler.GET(req);
  },
  POST: async (req: Request) => {
    const h = helpers();
    if (!h) return new Response("Auth not configured", { status: 404 });
    return h.handler.POST(req);
  },
};

export async function getToken(): Promise<string | undefined> {
  return helpers()?.getToken();
}

export async function isAuthenticated(): Promise<boolean> {
  return helpers()?.isAuthenticated() ?? false;
}

export async function preloadAuthQuery(...args: any[]) {
  return helpers()?.preloadAuthQuery(...(args as [any]));
}

export async function fetchAuthQuery(...args: any[]) {
  return helpers()?.fetchAuthQuery(...(args as [any]));
}

export async function fetchAuthMutation(...args: any[]) {
  return helpers()?.fetchAuthMutation(...(args as [any]));
}

export async function fetchAuthAction(...args: any[]) {
  return helpers()?.fetchAuthAction(...(args as [any]));
}
