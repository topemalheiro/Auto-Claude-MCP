import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useCloudMode } from '../useCloudMode';

describe('useCloudMode', () => {
  beforeEach(() => {
    // Reset environment variables before each test
    delete process.env.NEXT_PUBLIC_CONVEX_URL;
    delete process.env.NEXT_PUBLIC_API_URL;
    // Clear module cache to get fresh imports
    vi.resetModules();
  });

  describe('self-hosted mode', () => {
    it('should return isCloud=false when NEXT_PUBLIC_CONVEX_URL is not set', async () => {
      delete process.env.NEXT_PUBLIC_CONVEX_URL;

      // Dynamically import to get fresh module
      const { useCloudMode: freshHook } = await import('../useCloudMode');
      const { result } = renderHook(() => freshHook());

      expect(result.current.isCloud).toBe(false);
    });

    it('should return default API URL when NEXT_PUBLIC_API_URL is not set', async () => {
      delete process.env.NEXT_PUBLIC_CONVEX_URL;
      delete process.env.NEXT_PUBLIC_API_URL;

      const { useCloudMode: freshHook } = await import('../useCloudMode');
      const { result } = renderHook(() => freshHook());

      expect(result.current.apiUrl).toBe('http://localhost:8000');
    });

    it('should return custom API URL when NEXT_PUBLIC_API_URL is set', async () => {
      delete process.env.NEXT_PUBLIC_CONVEX_URL;
      process.env.NEXT_PUBLIC_API_URL = 'https://api.example.com';

      const { useCloudMode: freshHook } = await import('../useCloudMode');
      const { result } = renderHook(() => freshHook());

      expect(result.current.apiUrl).toBe('https://api.example.com');
    });
  });

  describe('cloud mode', () => {
    it('should return isCloud=true when NEXT_PUBLIC_CONVEX_URL is set', async () => {
      process.env.NEXT_PUBLIC_CONVEX_URL = 'https://example.convex.cloud';

      const { useCloudMode: freshHook } = await import('../useCloudMode');
      const { result } = renderHook(() => freshHook());

      expect(result.current.isCloud).toBe(true);
    });

    it('should still provide API URL in cloud mode', async () => {
      process.env.NEXT_PUBLIC_CONVEX_URL = 'https://example.convex.cloud';
      process.env.NEXT_PUBLIC_API_URL = 'https://api.example.com';

      const { useCloudMode: freshHook } = await import('../useCloudMode');
      const { result } = renderHook(() => freshHook());

      expect(result.current.isCloud).toBe(true);
      expect(result.current.apiUrl).toBe('https://api.example.com');
    });
  });

  describe('return value immutability', () => {
    it('should return a readonly object', async () => {
      const { useCloudMode: freshHook } = await import('../useCloudMode');
      const { result } = renderHook(() => freshHook());

      // TypeScript should enforce this, but we can verify the structure
      expect(result.current).toHaveProperty('isCloud');
      expect(result.current).toHaveProperty('apiUrl');
      expect(Object.keys(result.current)).toHaveLength(2);
    });

    it('should return consistent values across multiple calls', async () => {
      process.env.NEXT_PUBLIC_CONVEX_URL = 'https://example.convex.cloud';
      process.env.NEXT_PUBLIC_API_URL = 'https://api.example.com';

      const { useCloudMode: freshHook } = await import('../useCloudMode');
      const { result, rerender } = renderHook(() => freshHook());

      const firstCall = result.current;
      rerender();
      const secondCall = result.current;

      expect(firstCall.isCloud).toBe(secondCall.isCloud);
      expect(firstCall.apiUrl).toBe(secondCall.apiUrl);
    });
  });

  describe('edge cases', () => {
    it('should handle empty string CONVEX_URL', async () => {
      process.env.NEXT_PUBLIC_CONVEX_URL = '';

      const { useCloudMode: freshHook } = await import('../useCloudMode');
      const { result } = renderHook(() => freshHook());

      expect(result.current.isCloud).toBe(false);
    });

    it('should handle whitespace-only CONVEX_URL', async () => {
      process.env.NEXT_PUBLIC_CONVEX_URL = '   ';

      const { useCloudMode: freshHook } = await import('../useCloudMode');
      const { result } = renderHook(() => freshHook());

      // Whitespace is truthy, so CLOUD_MODE will be true
      expect(result.current.isCloud).toBe(true);
    });
  });
});
