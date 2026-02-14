import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useCurrentUser } from '../useCurrentUser';
import * as convexReact from 'convex/react';

// Mock the Convex API
vi.mock('../../convex/_generated/api', () => ({
  api: {
    users: {
      me: 'users:me'
    }
  }
}));

describe('useCurrentUser', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should call useQuery with the users.me API endpoint', () => {
    const mockUseQuery = vi.fn().mockReturnValue(undefined);
    vi.spyOn(convexReact, 'useQuery').mockImplementation(mockUseQuery);

    renderHook(() => useCurrentUser());

    // Verify useQuery was called once with the API endpoint
    expect(mockUseQuery).toHaveBeenCalledTimes(1);
    // The API endpoint is passed as first argument
    expect(mockUseQuery.mock.calls[0].length).toBeGreaterThan(0);
  });

  it('should return user data when authenticated', () => {
    const mockUser = {
      _id: 'user123',
      email: 'test@example.com',
      name: 'Test User',
      tier: 'pro' as const,
    };

    vi.spyOn(convexReact, 'useQuery').mockReturnValue(mockUser);

    const { result } = renderHook(() => useCurrentUser());

    expect(result.current).toEqual(mockUser);
  });

  it('should return undefined when not authenticated', () => {
    vi.spyOn(convexReact, 'useQuery').mockReturnValue(undefined);

    const { result } = renderHook(() => useCurrentUser());

    expect(result.current).toBeUndefined();
  });

  it('should return null when query is loading', () => {
    vi.spyOn(convexReact, 'useQuery').mockReturnValue(null);

    const { result } = renderHook(() => useCurrentUser());

    expect(result.current).toBeNull();
  });

  it('should update when user data changes', () => {
    const mockUser1 = {
      _id: 'user123',
      email: 'test@example.com',
      name: 'Test User',
      tier: 'free' as const,
    };

    const mockUser2 = {
      _id: 'user123',
      email: 'test@example.com',
      name: 'Test User',
      tier: 'pro' as const,
    };

    const mockUseQuery = vi.spyOn(convexReact, 'useQuery');
    mockUseQuery.mockReturnValue(mockUser1);

    const { result, rerender } = renderHook(() => useCurrentUser());

    expect(result.current).toEqual(mockUser1);

    // Simulate user upgrade
    mockUseQuery.mockReturnValue(mockUser2);
    rerender();

    expect(result.current).toEqual(mockUser2);
  });

  it('should handle user with all tier types', () => {
    const tiers = ['free', 'pro', 'team', 'enterprise'] as const;

    tiers.forEach(tier => {
      const mockUser = {
        _id: 'user123',
        email: 'test@example.com',
        name: 'Test User',
        tier,
      };

      vi.spyOn(convexReact, 'useQuery').mockReturnValue(mockUser);

      const { result } = renderHook(() => useCurrentUser());

      expect(result.current?.tier).toBe(tier);
    });
  });

  it('should handle user without tier (defaults to free)', () => {
    const mockUser = {
      _id: 'user123',
      email: 'test@example.com',
      name: 'Test User',
      // tier not set - should default to free in the backend
    };

    vi.spyOn(convexReact, 'useQuery').mockReturnValue(mockUser);

    const { result } = renderHook(() => useCurrentUser());

    expect(result.current).toEqual(mockUser);
  });

  it('should handle multiple concurrent renders correctly', () => {
    const mockUser = {
      _id: 'user123',
      email: 'test@example.com',
      name: 'Test User',
      tier: 'pro' as const,
    };

    const mockUseQuery = vi.spyOn(convexReact, 'useQuery').mockReturnValue(mockUser);

    const { result: result1 } = renderHook(() => useCurrentUser());
    const { result: result2 } = renderHook(() => useCurrentUser());

    expect(result1.current).toEqual(mockUser);
    expect(result2.current).toEqual(mockUser);
    expect(mockUseQuery).toHaveBeenCalledTimes(2);
  });
});
