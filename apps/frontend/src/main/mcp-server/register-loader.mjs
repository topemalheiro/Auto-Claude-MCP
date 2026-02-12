/**
 * Register the ESM electron mock loader.
 * Used with: node --import ./register-loader.mjs
 *
 * CRITICAL: Sets process.versions.electron BEFORE any modules load,
 * because @sentry/electron reads it at module evaluation time.
 */
if (!process.versions.electron) {
  process.versions.electron = '30.0.0';
}
process.env.MCP_STANDALONE = 'true';

import { register } from 'node:module';
register('./electron-loader.mjs', import.meta.url);
