import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConvexClientProvider } from '../ConvexClientProvider';

describe('ConvexClientProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
  });

  describe('self-hosted mode (no CONVEX_URL)', () => {
    it('should render children directly without Convex wrapper', async () => {
      delete process.env.NEXT_PUBLIC_CONVEX_URL;

      const { ConvexClientProvider: FreshProvider } = await import('../ConvexClientProvider');

      render(
        <FreshProvider>
          <div data-testid="test-child">Test Content</div>
        </FreshProvider>
      );

      expect(screen.getByTestId('test-child')).toBeInTheDocument();
      expect(screen.getByText('Test Content')).toBeInTheDocument();
    });

    it('should not require initialToken prop in self-hosted mode', async () => {
      delete process.env.NEXT_PUBLIC_CONVEX_URL;

      const { ConvexClientProvider: FreshProvider } = await import('../ConvexClientProvider');

      render(
        <FreshProvider>
          <div>Content</div>
        </FreshProvider>
      );

      expect(screen.getByText('Content')).toBeInTheDocument();
    });

    it('should handle multiple children in self-hosted mode', async () => {
      delete process.env.NEXT_PUBLIC_CONVEX_URL;

      const { ConvexClientProvider: FreshProvider } = await import('../ConvexClientProvider');

      render(
        <FreshProvider>
          <div>First</div>
          <div>Second</div>
          <div>Third</div>
        </FreshProvider>
      );

      expect(screen.getByText('First')).toBeInTheDocument();
      expect(screen.getByText('Second')).toBeInTheDocument();
      expect(screen.getByText('Third')).toBeInTheDocument();
    });

    it('should not import Convex dependencies in self-hosted mode', async () => {
      delete process.env.NEXT_PUBLIC_CONVEX_URL;

      // Mock require to verify it's not called for Convex packages
      const originalRequire = global.require;
      const mockRequire = vi.fn(originalRequire);
      global.require = mockRequire as any;

      const { ConvexClientProvider: FreshProvider } = await import('../ConvexClientProvider');

      render(
        <FreshProvider>
          <div>Test</div>
        </FreshProvider>
      );

      // Verify Convex packages were not required
      const convexCalls = mockRequire.mock.calls.filter(
        call => call[0] === 'convex/react' || call[0] === '@convex-dev/better-auth/react'
      );
      expect(convexCalls.length).toBe(0);

      // Restore original require
      global.require = originalRequire;
    });
  });

  describe('cloud mode (with CONVEX_URL)', () => {
    it('should render children (cloud mode behavior tested via integration)', async () => {
      process.env.NEXT_PUBLIC_CONVEX_URL = 'https://example.convex.cloud';

      // In cloud mode, the provider lazy-loads dependencies via require()
      // Testing the exact wrapper behavior requires integration tests
      // Here we verify it doesn't crash and renders children

      const { ConvexClientProvider: FreshProvider } = await import('../ConvexClientProvider');

      render(
        <FreshProvider>
          <div data-testid="test-child">Test Content</div>
        </FreshProvider>
      );

      expect(screen.getByTestId('test-child')).toBeInTheDocument();
    });

    it('should accept initialToken prop without errors', async () => {
      process.env.NEXT_PUBLIC_CONVEX_URL = 'https://example.convex.cloud';

      const { ConvexClientProvider: FreshProvider } = await import('../ConvexClientProvider');

      const testToken = 'test-token-123';
      render(
        <FreshProvider initialToken={testToken}>
          <div data-testid="test-content">Test</div>
        </FreshProvider>
      );

      expect(screen.getByTestId('test-content')).toBeInTheDocument();
    });

    it('should accept null initialToken without errors', async () => {
      process.env.NEXT_PUBLIC_CONVEX_URL = 'https://example.convex.cloud';

      const { ConvexClientProvider: FreshProvider } = await import('../ConvexClientProvider');

      render(
        <FreshProvider initialToken={null}>
          <div data-testid="test-content">Test</div>
        </FreshProvider>
      );

      expect(screen.getByTestId('test-content')).toBeInTheDocument();
    });
  });

  describe('provider nesting', () => {
    it('should allow nesting multiple providers', async () => {
      delete process.env.NEXT_PUBLIC_CONVEX_URL;

      const { ConvexClientProvider: FreshProvider } = await import('../ConvexClientProvider');

      render(
        <FreshProvider>
          <FreshProvider>
            <div data-testid="nested-content">Nested Content</div>
          </FreshProvider>
        </FreshProvider>
      );

      expect(screen.getByTestId('nested-content')).toBeInTheDocument();
    });
  });

  describe('error handling', () => {
    it('should handle rendering errors gracefully', async () => {
      delete process.env.NEXT_PUBLIC_CONVEX_URL;

      const { ConvexClientProvider: FreshProvider } = await import('../ConvexClientProvider');

      const ThrowError = () => {
        throw new Error('Test error');
      };

      expect(() => {
        render(
          <FreshProvider>
            <ThrowError />
          </FreshProvider>
        );
      }).toThrow('Test error');
    });
  });
});
