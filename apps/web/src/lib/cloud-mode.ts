/**
 * Cloud mode detection.
 *
 * The web app runs in two modes:
 * - Cloud mode: NEXT_PUBLIC_CONVEX_URL is set, full Convex-powered features
 * - Self-hosted mode: No NEXT_PUBLIC_CONVEX_URL, local Python backend via REST
 *
 * This module provides the detection logic used throughout the app.
 */

export const CLOUD_MODE = !!process.env.NEXT_PUBLIC_CONVEX_URL;
export const CONVEX_URL = process.env.NEXT_PUBLIC_CONVEX_URL ?? "";
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
