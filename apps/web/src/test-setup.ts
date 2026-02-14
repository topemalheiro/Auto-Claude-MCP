/**
 * Test setup file for Vitest
 * Configures mocks and global test environment for Next.js + Convex app
 */
import { vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom';

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: vi.fn(() => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
  })),
  usePathname: vi.fn(() => '/'),
  useSearchParams: vi.fn(() => new URLSearchParams()),
}));

// Mock Convex React hooks (used in cloud mode)
vi.mock('convex/react', () => ({
  ConvexReactClient: vi.fn(),
  ConvexProvider: vi.fn(({ children }) => children),
  Authenticated: vi.fn(({ children }) => children),
  Unauthenticated: vi.fn(() => null),
  AuthLoading: vi.fn(() => null),
  useQuery: vi.fn(),
  useMutation: vi.fn(),
  useConvex: vi.fn(),
}));

// Mock Convex Better Auth (used in cloud mode)
vi.mock('@convex-dev/better-auth/react', () => ({
  ConvexBetterAuthProvider: vi.fn(({ children }) => children),
}));

// Mock auth client (used in cloud mode)
vi.mock('@/lib/auth-client', () => ({
  authClient: {
    signIn: { social: vi.fn() },
    signOut: vi.fn(),
    useSession: vi.fn(() => ({ data: null, isPending: false })),
  },
}));

// Mock convex-imports to avoid require() issues in tests
vi.mock('@/lib/convex-imports', () => ({
  getConvexReact: vi.fn(() => ({
    ConvexReactClient: vi.fn(),
    useQuery: vi.fn(),
    useMutation: vi.fn(),
    Authenticated: vi.fn(({ children }) => children),
    Unauthenticated: vi.fn(() => null),
    AuthLoading: vi.fn(() => null),
  })),
  getBetterAuthReact: vi.fn(() => ({
    ConvexBetterAuthProvider: vi.fn(({ children }) => children),
  })),
  getAuthClient: vi.fn(() => ({
    authClient: {
      signIn: { social: vi.fn() },
      signOut: vi.fn(),
      useSession: vi.fn(() => ({ data: null, isPending: false })),
    },
  })),
  getConvexApi: vi.fn(() => ({
    api: {
      users: {
        me: 'users:me',
        ensureUser: 'users:ensureUser',
      },
    },
  })),
  getConvexClient: vi.fn(),
}));

// Mock window.matchMedia for jsdom (used by theme detection in AppShell)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock scrollIntoView for Radix UI components in jsdom
if (typeof HTMLElement !== 'undefined' && !HTMLElement.prototype.scrollIntoView) {
  Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
    value: vi.fn(),
    writable: true
  });
}

// Mock requestAnimationFrame/cancelAnimationFrame for jsdom
if (typeof global.requestAnimationFrame === 'undefined') {
  global.requestAnimationFrame = vi.fn((callback: FrameRequestCallback) => {
    return setTimeout(() => callback(Date.now()), 0) as unknown as number;
  });
  global.cancelAnimationFrame = vi.fn((id: number) => {
    clearTimeout(id);
  });
}

// Mock localStorage for tests that need it
const localStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    })
  };
})();

// Make localStorage available globally
Object.defineProperty(global, 'localStorage', {
  value: localStorageMock
});

// Reset environment variables before each test
beforeEach(() => {
  // Clear localStorage
  localStorageMock.clear();

  // Reset environment variables to defaults
  process.env.NEXT_PUBLIC_CONVEX_URL = undefined;
  process.env.NEXT_PUBLIC_API_URL = undefined;
});

// Clean up mocks after each test
afterEach(() => {
  vi.clearAllMocks();
  vi.resetModules();
});

// Suppress console errors in tests unless explicitly testing error scenarios
const originalConsoleError = console.error;
console.error = (...args: unknown[]) => {
  // Allow certain error messages through for debugging
  const message = args[0]?.toString() || '';
  if (message.includes('[TEST]')) {
    originalConsoleError(...args);
  }
};
