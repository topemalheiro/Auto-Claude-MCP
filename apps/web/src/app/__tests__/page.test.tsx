import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import HomePage from '../page';

// Mock the hooks and dependencies
vi.mock('@/hooks/useCloudMode', () => ({
  useCloudMode: vi.fn(() => ({ isCloud: false, apiUrl: 'http://localhost:8000' })),
}));

vi.mock('@/providers/AuthGate', () => ({
  CloudAuthenticated: vi.fn(({ children }: { children: React.ReactNode }) => <>{children}</>),
  CloudUnauthenticated: vi.fn(() => null),
  CloudAuthLoading: vi.fn(() => null),
}));

vi.mock('@/lib/convex-imports', () => ({
  getConvexReact: vi.fn(() => ({
    useQuery: vi.fn(),
    useMutation: vi.fn(),
  })),
  getConvexApi: vi.fn(() => ({
    api: {
      users: {
        me: 'users:me',
        ensureUser: 'users:ensureUser',
      },
    },
  })),
}));

vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

// Mock i18next - load actual English locale files for realistic rendering
import enCommon from '@/locales/en/common.json';
import enPages from '@/locales/en/pages.json';
import enLayout from '@/locales/en/layout.json';
import enKanban from '@/locales/en/kanban.json';
import enViews from '@/locales/en/views.json';
import enIntegrations from '@/locales/en/integrations.json';
import enSettings from '@/locales/en/settings.json';

const locales: Record<string, any> = {
  common: enCommon,
  pages: enPages,
  layout: enLayout,
  kanban: enKanban,
  views: enViews,
  integrations: enIntegrations,
  settings: enSettings,
};

function resolveKey(key: string, ns: string, params?: any): string {
  // Handle "ns:key" format
  let namespace = ns;
  let path = key;
  if (key.includes(':')) {
    const [nsOverride, ...rest] = key.split(':');
    namespace = nsOverride;
    path = rest.join(':');
  }
  const data = locales[namespace];
  if (!data) return key;
  const value = path.split('.').reduce((obj: any, k: string) => obj?.[k], data);
  if (typeof value !== 'string') return key;
  if (params) {
    return value.replace(/\{\{(\w+)\}\}/g, (_: string, p: string) => params[p] ?? '');
  }
  return value;
}

vi.mock('react-i18next', () => ({
  useTranslation: (ns: string = 'common') => ({
    t: (key: string, params?: any) => resolveKey(key, ns, params),
    i18n: { language: 'en' },
  }),
}));

// Mock the data layer to prevent API calls from stores
vi.mock('@/lib/data', () => ({
  apiClient: {
    getProjects: vi.fn(() => Promise.resolve({ projects: [] })),
    getTasks: vi.fn(() => Promise.resolve({ tasks: [] })),
    getSettings: vi.fn(() => Promise.resolve({ settings: {} })),
    updateSettings: vi.fn(() => Promise.resolve({})),
    updateTaskStatus: vi.fn(() => Promise.resolve({})),
  },
}));

describe('HomePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('self-hosted mode', () => {
    beforeEach(async () => {
      const { useCloudMode } = await import('@/hooks/useCloudMode');
      vi.mocked(useCloudMode).mockReturnValue({
        isCloud: false,
        apiUrl: 'http://localhost:8000',
      });
    });

    it('should render the AppShell with sidebar and welcome screen', () => {
      render(<HomePage />);
      // Sidebar renders "Auto Claude" branding
      expect(screen.getByText('Auto Claude')).toBeInTheDocument();
      // WelcomeScreen renders when no project is selected
      expect(screen.getByText('Welcome to Auto Claude')).toBeInTheDocument();
    });

    it('should show the welcome screen when no project is selected', () => {
      render(<HomePage />);
      expect(screen.getByText('Welcome to Auto Claude')).toBeInTheDocument();
      expect(
        screen.getByText(/Get started by connecting a project/)
      ).toBeInTheDocument();
    });

    it('should display the Connect a Project button', () => {
      render(<HomePage />);
      const connectButton = screen.getByRole('button', { name: /Connect a Project/i });
      expect(connectButton).toBeInTheDocument();
    });

    it('should show sidebar navigation items', () => {
      render(<HomePage />);
      expect(screen.getByText('Tasks')).toBeInTheDocument();
      expect(screen.getByText('Insights')).toBeInTheDocument();
      expect(screen.getByText('Roadmap')).toBeInTheDocument();
      expect(screen.getByText('Ideation')).toBeInTheDocument();
      expect(screen.getByText('Changelog')).toBeInTheDocument();
      expect(screen.getByText('Context')).toBeInTheDocument();
    });

    it('should show Settings button in the sidebar', () => {
      render(<HomePage />);
      expect(screen.getByText('Settings')).toBeInTheDocument();
    });

    it('should not disable Settings button when no project is active', () => {
      render(<HomePage />);
      const settingsButton = screen.getByText('Settings').closest('button');
      expect(settingsButton).not.toBeDisabled();
    });

    it('should disable nav items when no project is active', () => {
      render(<HomePage />);
      const tasksButton = screen.getByText('Tasks').closest('button');
      expect(tasksButton).toBeDisabled();
    });

    it('should render main element', () => {
      const { container } = render(<HomePage />);
      expect(container.querySelector('main')).toBeInTheDocument();
    });
  });

  describe('cloud mode - unauthenticated', () => {
    beforeEach(async () => {
      const { useCloudMode } = await import('@/hooks/useCloudMode');
      vi.mocked(useCloudMode).mockReturnValue({
        isCloud: true,
        apiUrl: 'http://localhost:8000',
      });

      // Mock the AuthGate components to show unauthenticated state
      const { CloudAuthenticated, CloudUnauthenticated, CloudAuthLoading } = await import('@/providers/AuthGate');
      vi.mocked(CloudAuthenticated).mockImplementation(() => null as unknown as React.ReactElement);
      vi.mocked(CloudUnauthenticated).mockImplementation(({ children }) => <>{children}</>);
      vi.mocked(CloudAuthLoading).mockImplementation(() => null as unknown as React.ReactElement);
    });

    it('should render without crashing in cloud mode', () => {
      render(<HomePage />);
      expect(screen.getByText('Auto Claude Cloud')).toBeInTheDocument();
    });

    it('should show landing page for unauthenticated users', () => {
      render(<HomePage />);
      expect(screen.getByText('Auto Claude Cloud')).toBeInTheDocument();
      expect(screen.getByText('Cloud-synced specs, personas, and team collaboration')).toBeInTheDocument();
    });

    it('should show get started button linking to login', () => {
      render(<HomePage />);
      const getStartedLink = screen.getByText('Get Started');
      expect(getStartedLink).toBeInTheDocument();
      expect(getStartedLink.closest('a')).toHaveAttribute('href', '/login');
    });

    it('should wrap content with auth gates', () => {
      const { container } = render(<HomePage />);
      expect(container.querySelector('main')).toBeInTheDocument();
    });
  });

  describe('cloud mode - authenticated', () => {
    beforeEach(async () => {
      const { useCloudMode } = await import('@/hooks/useCloudMode');
      vi.mocked(useCloudMode).mockReturnValue({
        isCloud: true,
        apiUrl: 'http://localhost:8000',
      });

      const { getConvexReact } = await import('@/lib/convex-imports');
      vi.mocked(getConvexReact).mockReturnValue({
        useQuery: vi.fn(() => ({
          _id: 'user123',
          name: 'Test User',
          email: 'test@example.com',
          tier: 'pro',
        })),
        useMutation: vi.fn(() => vi.fn()),
      } as any);

      // Mock the AuthGate components to show authenticated state
      const { CloudAuthenticated, CloudUnauthenticated, CloudAuthLoading } = await import('@/providers/AuthGate');
      vi.mocked(CloudAuthenticated).mockImplementation(({ children }) => <>{children}</>);
      vi.mocked(CloudUnauthenticated).mockImplementation(() => null);
      vi.mocked(CloudAuthLoading).mockImplementation(() => null);
    });

    it('should render the AppShell for authenticated cloud users', () => {
      render(<HomePage />);
      // AppShell renders Sidebar with branding
      expect(screen.getByText('Auto Claude')).toBeInTheDocument();
    });

    it('should show welcome screen when no project is selected', () => {
      render(<HomePage />);
      expect(screen.getByText('Welcome to Auto Claude')).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /Connect a Project/i })
      ).toBeInTheDocument();
    });

    it('should show sidebar navigation items for authenticated users', () => {
      render(<HomePage />);
      const navLabels = ['Tasks', 'Insights', 'Roadmap', 'Ideation', 'Changelog', 'Context'];
      navLabels.forEach(label => {
        expect(screen.getByText(label)).toBeInTheDocument();
      });
    });
  });

  describe('cloud mode - loading state', () => {
    beforeEach(async () => {
      const { useCloudMode } = await import('@/hooks/useCloudMode');
      vi.mocked(useCloudMode).mockReturnValue({
        isCloud: true,
        apiUrl: 'http://localhost:8000',
      });

      const { getConvexReact } = await import('@/lib/convex-imports');
      vi.mocked(getConvexReact).mockReturnValue({
        useQuery: vi.fn(() => null),
        useMutation: vi.fn(() => vi.fn()),
      } as any);
    });

    it('should show loading state when user is null', () => {
      render(<HomePage />);
      // Should show loading in both CloudAuthLoading and CloudDashboard
      const loadingElements = screen.getAllByText('Loading...');
      expect(loadingElements.length).toBeGreaterThan(0);
    });
  });

  describe('accessibility', () => {
    it('should have proper heading hierarchy in self-hosted mode', async () => {
      const { useCloudMode } = await import('@/hooks/useCloudMode');
      vi.mocked(useCloudMode).mockReturnValue({
        isCloud: false,
        apiUrl: 'http://localhost:8000',
      });

      render(<HomePage />);
      const headings = screen.getAllByRole('heading');
      expect(headings.length).toBeGreaterThan(0);
    });

    it('should have accessible buttons in self-hosted mode', async () => {
      const { useCloudMode } = await import('@/hooks/useCloudMode');
      vi.mocked(useCloudMode).mockReturnValue({
        isCloud: false,
        apiUrl: 'http://localhost:8000',
      });

      render(<HomePage />);
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });
});
