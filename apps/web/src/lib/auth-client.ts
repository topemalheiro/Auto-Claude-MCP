import { createAuthClient } from "better-auth/react";
import { convexClient, crossDomainClient } from "@convex-dev/better-auth/client/plugins";

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_CONVEX_SITE_URL!,
  plugins: [
    convexClient(),
    ...(typeof window !== "undefined" ? [crossDomainClient()] : []),
  ],
});
