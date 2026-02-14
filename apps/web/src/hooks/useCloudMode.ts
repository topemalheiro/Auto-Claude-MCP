"use client";

import { CLOUD_MODE, API_URL } from "@/lib/cloud-mode";

/**
 * Hook to detect whether the app is running in cloud mode (Convex-powered)
 * or self-hosted mode (local Python backend).
 *
 * Usage:
 *   const { isCloud, apiUrl } = useCloudMode();
 *   if (isCloud) { // use Convex hooks }
 *   else { // use REST fetches against apiUrl }
 */
export function useCloudMode() {
  return {
    isCloud: CLOUD_MODE,
    apiUrl: API_URL,
  } as const;
}
