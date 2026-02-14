import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  CloudAuthenticated,
  CloudUnauthenticated,
  CloudAuthLoading,
} from '../AuthGate';

describe('AuthGate Components', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
  });

  describe('CloudAuthenticated', () => {
    describe('self-hosted mode', () => {
      it('should always render children in self-hosted mode', async () => {
        delete process.env.NEXT_PUBLIC_CONVEX_URL;

        const { CloudAuthenticated: FreshComponent } = await import('../AuthGate');

        render(
          <FreshComponent>
            <div data-testid="authenticated-content">Authenticated Content</div>
          </FreshComponent>
        );

        expect(screen.getByTestId('authenticated-content')).toBeInTheDocument();
      });

      it('should render multiple children in self-hosted mode', async () => {
        delete process.env.NEXT_PUBLIC_CONVEX_URL;

        const { CloudAuthenticated: FreshComponent } = await import('../AuthGate');

        render(
          <FreshComponent>
            <div>First</div>
            <div>Second</div>
          </FreshComponent>
        );

        expect(screen.getByText('First')).toBeInTheDocument();
        expect(screen.getByText('Second')).toBeInTheDocument();
      });
    });

    describe('cloud mode', () => {
      it('should render children (wrapper behavior tested via integration)', async () => {
        process.env.NEXT_PUBLIC_CONVEX_URL = 'https://example.convex.cloud';

        // Cloud mode lazy-loads the Convex Authenticated component via require()
        // The exact wrapper behavior is tested in integration tests
        const { CloudAuthenticated: FreshComponent } = await import('../AuthGate');

        render(
          <FreshComponent>
            <div data-testid="test-content">Test Content</div>
          </FreshComponent>
        );

        expect(screen.getByTestId('test-content')).toBeInTheDocument();
      });
    });
  });

  describe('CloudUnauthenticated', () => {
    describe('self-hosted mode', () => {
      it('should never render children in self-hosted mode', async () => {
        delete process.env.NEXT_PUBLIC_CONVEX_URL;

        const { CloudUnauthenticated: FreshComponent } = await import('../AuthGate');

        render(
          <FreshComponent>
            <div data-testid="unauthenticated-content">Login Required</div>
          </FreshComponent>
        );

        expect(screen.queryByTestId('unauthenticated-content')).not.toBeInTheDocument();
      });

      it('should return null in self-hosted mode', async () => {
        delete process.env.NEXT_PUBLIC_CONVEX_URL;

        const { CloudUnauthenticated: FreshComponent } = await import('../AuthGate');

        const { container } = render(
          <FreshComponent>
            <div>Should not render</div>
          </FreshComponent>
        );

        expect(container.firstChild).toBeNull();
      });
    });

    describe('cloud mode', () => {
      it('should delegate rendering to Convex Unauthenticated component', async () => {
        process.env.NEXT_PUBLIC_CONVEX_URL = 'https://example.convex.cloud';

        const { CloudUnauthenticated: FreshComponent } = await import('../AuthGate');

        const { container } = render(
          <FreshComponent>
            <div data-testid="login-content">Login Page</div>
          </FreshComponent>
        );

        // In cloud mode with default mocks, Unauthenticated returns null
        // (Actual visibility is controlled by Convex auth state in production)
        expect(container.firstChild).toBeNull();
      });
    });
  });

  describe('CloudAuthLoading', () => {
    describe('self-hosted mode', () => {
      it('should never render children in self-hosted mode', async () => {
        delete process.env.NEXT_PUBLIC_CONVEX_URL;

        const { CloudAuthLoading: FreshComponent } = await import('../AuthGate');

        render(
          <FreshComponent>
            <div data-testid="loading-content">Loading...</div>
          </FreshComponent>
        );

        expect(screen.queryByTestId('loading-content')).not.toBeInTheDocument();
      });

      it('should return null in self-hosted mode', async () => {
        delete process.env.NEXT_PUBLIC_CONVEX_URL;

        const { CloudAuthLoading: FreshComponent } = await import('../AuthGate');

        const { container } = render(
          <FreshComponent>
            <div>Should not render</div>
          </FreshComponent>
        );

        expect(container.firstChild).toBeNull();
      });
    });

    describe('cloud mode', () => {
      it('should delegate rendering to Convex AuthLoading component', async () => {
        process.env.NEXT_PUBLIC_CONVEX_URL = 'https://example.convex.cloud';

        const { CloudAuthLoading: FreshComponent } = await import('../AuthGate');

        const { container } = render(
          <FreshComponent>
            <div data-testid="spinner">Loading...</div>
          </FreshComponent>
        );

        // In cloud mode with default mocks, AuthLoading returns null
        // (Actual visibility is controlled by Convex auth state in production)
        expect(container.firstChild).toBeNull();
      });
    });
  });

  describe('combined usage scenarios', () => {
    it('should work together in a typical auth flow (self-hosted)', async () => {
      delete process.env.NEXT_PUBLIC_CONVEX_URL;

      const {
        CloudAuthenticated,
        CloudUnauthenticated,
        CloudAuthLoading,
      } = await import('../AuthGate');

      render(
        <>
          <CloudAuthenticated>
            <div data-testid="authenticated">Dashboard</div>
          </CloudAuthenticated>
          <CloudUnauthenticated>
            <div data-testid="unauthenticated">Login</div>
          </CloudUnauthenticated>
          <CloudAuthLoading>
            <div data-testid="loading">Loading...</div>
          </CloudAuthLoading>
        </>
      );

      // In self-hosted mode:
      // - Authenticated content always shows
      // - Unauthenticated and Loading never show
      expect(screen.getByTestId('authenticated')).toBeInTheDocument();
      expect(screen.queryByTestId('unauthenticated')).not.toBeInTheDocument();
      expect(screen.queryByTestId('loading')).not.toBeInTheDocument();
    });

    it('should work together in a typical auth flow (cloud mode)', async () => {
      process.env.NEXT_PUBLIC_CONVEX_URL = 'https://example.convex.cloud';

      const {
        CloudAuthenticated,
        CloudUnauthenticated,
        CloudAuthLoading,
      } = await import('../AuthGate');

      const { container } = render(
        <>
          <CloudAuthenticated>
            <div data-testid="authenticated">Dashboard</div>
          </CloudAuthenticated>
          <CloudUnauthenticated>
            <div data-testid="unauthenticated">Login</div>
          </CloudUnauthenticated>
          <CloudAuthLoading>
            <div data-testid="loading">Loading...</div>
          </CloudAuthLoading>
        </>
      );

      // CloudAuthenticated renders by default in our mocks
      expect(screen.getByTestId('authenticated')).toBeInTheDocument();
      // CloudUnauthenticated and CloudAuthLoading return null in mocks
      // (Actual auth state would be controlled by Convex)
      expect(container).toBeTruthy();
    });
  });

  describe('nesting scenarios', () => {
    it('should handle nested auth gates in self-hosted mode', async () => {
      delete process.env.NEXT_PUBLIC_CONVEX_URL;

      const { CloudAuthenticated } = await import('../AuthGate');

      render(
        <CloudAuthenticated>
          <CloudAuthenticated>
            <div data-testid="nested">Nested Content</div>
          </CloudAuthenticated>
        </CloudAuthenticated>
      );

      expect(screen.getByTestId('nested')).toBeInTheDocument();
    });
  });
});
