/**
 * Shared utility functions for checkpoint components.
 *
 * Story Reference: Story 5.3 - Implement Checkpoint Feedback Input
 */

/**
 * Format file size in human-readable format.
 *
 * @param bytes - File size in bytes
 * @returns Formatted string (e.g., "1.5 KB", "2.3 MB")
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * Validate that a URL is safe to use as a link attachment.
 *
 * Only allows http: and https: protocols to prevent XSS via
 * javascript:, data:, or file: URLs.
 *
 * @param str - URL string to validate
 * @returns true if URL is valid and safe
 */
export function isValidUrl(str: string): boolean {
  try {
    const parsed = new URL(str);
    return ['http:', 'https:'].includes(parsed.protocol);
  } catch {
    return false;
  }
}
