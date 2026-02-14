/**
 * Cloud mode detection.
 *
 * The web app runs in two modes:
 * - Cloud mode: NEXT_PUBLIC_CONVEX_URL is set, full Convex-powered features
 * - Self-hosted mode: No NEXT_PUBLIC_CONVEX_URL, local Python backend via REST/Socket.IO
 *
 * This module provides the detection logic used throughout the app.
 */

/** Whether the app is running in cloud mode (Convex backend). */
export const CLOUD_MODE = !!process.env.NEXT_PUBLIC_CONVEX_URL;

/** Convex deployment URL (empty string in self-hosted mode). */
export const CONVEX_URL = process.env.NEXT_PUBLIC_CONVEX_URL ?? "";

/** Local Python backend REST API URL (self-hosted mode). */
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Socket.IO URL for real-time updates (self-hosted mode). */
export const SOCKET_URL = process.env.NEXT_PUBLIC_SOCKET_URL ?? "http://localhost:8000";

/** Whether debug logging is enabled. */
export const DEBUG = process.env.NEXT_PUBLIC_DEBUG === "true";
