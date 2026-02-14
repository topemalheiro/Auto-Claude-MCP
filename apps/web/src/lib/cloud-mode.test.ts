import { describe, it, expect, beforeEach } from 'vitest';

describe('cloud-mode', () => {
  beforeEach(() => {
    // Reset environment variables before each test
    delete process.env.NEXT_PUBLIC_CONVEX_URL;
    delete process.env.NEXT_PUBLIC_API_URL;
    // Clear module cache to get fresh imports
    vi.resetModules();
  });

  describe('CLOUD_MODE', () => {
    it('should be false when NEXT_PUBLIC_CONVEX_URL is not set', async () => {
      delete process.env.NEXT_PUBLIC_CONVEX_URL;
      const { CLOUD_MODE } = await import('./cloud-mode');
      expect(CLOUD_MODE).toBe(false);
    });

    it('should be true when NEXT_PUBLIC_CONVEX_URL is set', async () => {
      process.env.NEXT_PUBLIC_CONVEX_URL = 'https://example.convex.cloud';
      const { CLOUD_MODE } = await import('./cloud-mode');
      expect(CLOUD_MODE).toBe(true);
    });

    it('should be false when NEXT_PUBLIC_CONVEX_URL is empty string', async () => {
      process.env.NEXT_PUBLIC_CONVEX_URL = '';
      const { CLOUD_MODE } = await import('./cloud-mode');
      expect(CLOUD_MODE).toBe(false);
    });
  });

  describe('CONVEX_URL', () => {
    it('should return empty string when NEXT_PUBLIC_CONVEX_URL is not set', async () => {
      delete process.env.NEXT_PUBLIC_CONVEX_URL;
      const { CONVEX_URL } = await import('./cloud-mode');
      expect(CONVEX_URL).toBe('');
    });

    it('should return the URL when NEXT_PUBLIC_CONVEX_URL is set', async () => {
      const testUrl = 'https://example.convex.cloud';
      process.env.NEXT_PUBLIC_CONVEX_URL = testUrl;
      const { CONVEX_URL } = await import('./cloud-mode');
      expect(CONVEX_URL).toBe(testUrl);
    });
  });

  describe('API_URL', () => {
    it('should default to localhost:8000 when NEXT_PUBLIC_API_URL is not set', async () => {
      delete process.env.NEXT_PUBLIC_API_URL;
      const { API_URL } = await import('./cloud-mode');
      expect(API_URL).toBe('http://localhost:8000');
    });

    it('should return custom URL when NEXT_PUBLIC_API_URL is set', async () => {
      const testUrl = 'https://api.example.com';
      process.env.NEXT_PUBLIC_API_URL = testUrl;
      const { API_URL } = await import('./cloud-mode');
      expect(API_URL).toBe(testUrl);
    });

    it('should handle production API URLs correctly', async () => {
      const prodUrl = 'https://prod-api.autoclaude.com';
      process.env.NEXT_PUBLIC_API_URL = prodUrl;
      const { API_URL } = await import('./cloud-mode');
      expect(API_URL).toBe(prodUrl);
    });
  });

  describe('environment combinations', () => {
    it('should handle cloud mode with custom API URL', async () => {
      process.env.NEXT_PUBLIC_CONVEX_URL = 'https://example.convex.cloud';
      process.env.NEXT_PUBLIC_API_URL = 'https://api.example.com';
      const { CLOUD_MODE, CONVEX_URL, API_URL } = await import('./cloud-mode');
      expect(CLOUD_MODE).toBe(true);
      expect(CONVEX_URL).toBe('https://example.convex.cloud');
      expect(API_URL).toBe('https://api.example.com');
    });

    it('should handle self-hosted mode with default API URL', async () => {
      delete process.env.NEXT_PUBLIC_CONVEX_URL;
      delete process.env.NEXT_PUBLIC_API_URL;
      const { CLOUD_MODE, CONVEX_URL, API_URL } = await import('./cloud-mode');
      expect(CLOUD_MODE).toBe(false);
      expect(CONVEX_URL).toBe('');
      expect(API_URL).toBe('http://localhost:8000');
    });
  });
});
