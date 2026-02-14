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

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: any) => {
      // Simple translation mock that returns the key
      if (key === 'pages:home.selfHosted.title') return 'Auto Claude Dashboard';
      if (key === 'pages:home.selfHosted.mode') return 'Running in self-hosted mode';
      if (key === 'pages:home.selfHosted.unlockFeatures') return 'Unlock Premium Features';
      if (key === 'pages:home.selfHosted.featuresDescription') return 'Upgrade to cloud mode';
      if (key === 'common:navigation.specs') return 'Specs';
      if (key === 'common:navigation.teams') return 'Teams';
      if (key === 'common:navigation.personas') return 'Personas';
      if (key === 'common:navigation.prQueue') return 'PR Queue';
      if (key === 'common:navigation.settings') return 'Settings';
      if (key === 'common:buttons.learnMore') return 'Learn More';
      if (key === 'pages:home.landing.title') return 'Welcome to Auto Claude';
      if (key === 'pages:home.landing.subtitle') return 'AI-powered development';
      if (key === 'common:buttons.getStarted') return 'Get Started';
      if (key === 'common:loading') return 'Loading...';
      if (key === 'pages:home.welcome') return `Welcome, ${params?.name || 'User'}!`;
      if (key === 'pages:home.tier') return `Tier: ${params?.tier || 'free'}`;
      return key;
    },
    i18n: { language: 'en' },
  }),
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

    it('should render without crashing in self-hosted mode', () => {
      render(<HomePage />);
      expect(screen.getByText('Auto Claude Dashboard')).toBeInTheDocument();
    });

    it('should show self-hosted mode indicator', () => {
      render(<HomePage />);
      expect(screen.getByText('Running in self-hosted mode')).toBeInTheDocument();
    });

    it('should display upgrade CTA in self-hosted mode', () => {
      render(<HomePage />);
      expect(screen.getByText('Unlock Premium Features')).toBeInTheDocument();
      expect(screen.getByText('Upgrade to cloud mode')).toBeInTheDocument();
    });

    it('should show learn more button linking to autoclaude.com', () => {
      render(<HomePage />);
      const learnMoreLink = screen.getByText('Learn More');
      expect(learnMoreLink).toBeInTheDocument();
      expect(learnMoreLink.closest('a')).toHaveAttribute('href', 'https://autoclaude.com');
    });

    it('should show specs navigation link', () => {
      render(<HomePage />);
      const specsLink = screen.getByText('Specs');
      expect(specsLink).toBeInTheDocument();
      expect(specsLink.closest('a')).toHaveAttribute('href', '/specs');
    });

    it('should not show cloud-only navigation links in self-hosted mode', () => {
      render(<HomePage />);
      // Teams, Personas, PR Queue should not be visible in self-hosted mode
      expect(screen.queryByText('Teams')).not.toBeInTheDocument();
      expect(screen.queryByText('Personas')).not.toBeInTheDocument();
      expect(screen.queryByText('PR Queue')).not.toBeInTheDocument();
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
      vi.mocked(CloudAuthenticated).mockImplementation(() => null);
      vi.mocked(CloudUnauthenticated).mockImplementation(({ children }) => <>{children}</>);
      vi.mocked(CloudAuthLoading).mockImplementation(() => null);
    });

    it('should render without crashing in cloud mode', () => {
      render(<HomePage />);
      expect(screen.getByText('Welcome to Auto Claude')).toBeInTheDocument();
    });

    it('should show landing page for unauthenticated users', () => {
      render(<HomePage />);
      expect(screen.getByText('Welcome to Auto Claude')).toBeInTheDocument();
      expect(screen.getByText('AI-powered development')).toBeInTheDocument();
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

    it('should show welcome message with user name', () => {
      render(<HomePage />);
      expect(screen.getByText('Welcome, Test User!')).toBeInTheDocument();
    });

    it('should show user tier', () => {
      render(<HomePage />);
      expect(screen.getByText('Tier: pro')).toBeInTheDocument();
    });

    it('should show all navigation links for authenticated users', () => {
      render(<HomePage />);
      const linkTexts = ['Specs', 'Teams', 'Personas', 'PR Queue', 'Settings'];

      linkTexts.forEach(text => {
        expect(screen.getByText(text)).toBeInTheDocument();
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

    it('should have accessible links', async () => {
      const { useCloudMode } = await import('@/hooks/useCloudMode');
      vi.mocked(useCloudMode).mockReturnValue({
        isCloud: false,
        apiUrl: 'http://localhost:8000',
      });

      render(<HomePage />);
      const links = screen.getAllByRole('link');
      expect(links.length).toBeGreaterThan(0);
      links.forEach(link => {
        expect(link).toHaveAttribute('href');
      });
    });
  });
});
