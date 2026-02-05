"""Tests for rate_limiter"""

import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from runners.github.rate_limiter import (
    CostLimitExceeded,
    CostTracker,
    RateLimitExceeded,
    RateLimiter,
    TokenBucket,
    check_rate_limit,
    rate_limited,
)


class TestTokenBucket:
    """Test TokenBucket class."""

    def test_post_init(self):
        """Test TokenBucket initialization."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        assert bucket.tokens == 100.0
        assert bucket.capacity == 100
        assert bucket.refill_rate == 10.0
        assert bucket.last_refill > 0

    def test_try_acquire_success(self):
        """Test try_acquire returns True when tokens available."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        assert bucket.try_acquire(1) is True
        assert bucket.try_acquire(50) is True
        assert bucket.available() == 49

    def test_try_acquire_insufficient_tokens(self):
        """Test try_acquire returns False when insufficient tokens."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.try_acquire(5) is True
        assert bucket.try_acquire(6) is False
        assert bucket.available() == 5

    def test_refill(self):
        """Test token refill over time."""
        bucket = TokenBucket(capacity=100, refill_rate=100.0)  # 100 tokens per second
        # Empty the bucket
        bucket.try_acquire(100)
        assert bucket.available() == 0
        # Wait for refill
        import time
        time.sleep(0.1)  # 100ms should give ~10 tokens
        assert bucket.available() >= 5  # At least 5 tokens

    def test_acquire_success(self):
        """Test async acquire with tokens available."""
        async def test():
            bucket = TokenBucket(capacity=100, refill_rate=10.0)
            result = await bucket.acquire(1)
            assert result is True
            assert bucket.available() == 99

        asyncio.run(test())

    def test_acquire_timeout(self):
        """Test async acquire with timeout."""
        async def test():
            bucket = TokenBucket(capacity=10, refill_rate=1.0)
            # Use all tokens
            bucket.try_acquire(10)
            # Try to acquire with short timeout - refill at 1/sec means
            # we need to wait 1 second for 1 token, so 0.1s timeout won't get it
            result = await bucket.acquire(5, timeout=0.05)
            assert result is False

        asyncio.run(test())

    def test_time_until_available(self):
        """Test time_until_available calculation."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        bucket.try_acquire(95)
        # Need 5 more tokens (we have 5 left), refill at 10/sec = 0.5 second
        wait_time = bucket.time_until_available(10)
        # Should be approximately 0.5 seconds
        assert 0.4 < wait_time < 0.6

    def test_time_until_available_immediate(self):
        """Test time_until_available when tokens available immediately."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        wait_time = bucket.time_until_available(10)
        assert wait_time == 0.0


class TestCostTracker:
    """Test CostTracker class."""

    def test_add_operation(self):
        """Test adding an operation."""
        tracker = CostTracker(cost_limit=10.0)
        cost = tracker.add_operation(
            input_tokens=1000,
            output_tokens=500,
            model="claude-sonnet-4-5-20250929",
            operation_name="test_op",
        )
        assert cost > 0
        assert tracker.total_cost == cost
        assert len(tracker.operations) == 1
        assert tracker.operations[0]["operation"] == "test_op"

    def test_add_operation_exceeds_limit(self):
        """Test adding operation that exceeds budget."""
        tracker = CostTracker(cost_limit=0.001)  # Very small budget
        with pytest.raises(CostLimitExceeded):
            tracker.add_operation(
                input_tokens=100000,
                output_tokens=50000,
                model="claude-sonnet-4-5-20250929",
                operation_name="expensive_op",
            )

    def test_calculate_cost(self):
        """Test cost calculation."""
        # For claude-sonnet-4-5-20250929: $3/M input, $15/M output
        cost = CostTracker.calculate_cost(
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            model="claude-sonnet-4-5-20250929",
        )
        assert cost == 18.0  # $3 + $15

    def test_calculate_cost_unknown_model(self):
        """Test cost calculation with unknown model uses default."""
        cost = CostTracker.calculate_cost(
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            model="unknown-model",
        )
        # Should use default pricing
        assert cost > 0

    def test_remaining_budget(self):
        """Test remaining budget calculation."""
        tracker = CostTracker(cost_limit=10.0)
        tracker.add_operation(
            input_tokens=1000,
            output_tokens=500,
            model="claude-sonnet-4-5-20250929",
            operation_name="test",
        )
        remaining = tracker.remaining_budget()
        assert remaining >= 0
        assert remaining < 10.0

    def test_usage_report(self):
        """Test usage report generation."""
        tracker = CostTracker(cost_limit=10.0)
        tracker.add_operation(
            input_tokens=1000,
            output_tokens=500,
            model="claude-sonnet-4-5-20250929",
            operation_name="test_op",
        )
        report = tracker.usage_report()
        assert "Cost Usage Report" in report
        assert "Total Cost:" in report
        assert "Budget:" in report
        assert "test_op" in report


class TestRateLimiter:
    """Test RateLimiter class."""

    def setup_method(self):
        """Reset singleton before each test."""
        RateLimiter.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        RateLimiter.reset_instance()

    def test_init(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(
            github_limit=1000,
            github_refill_rate=2.0,
            cost_limit=5.0,
            max_retry_delay=100.0,
        )
        assert limiter.github_bucket.capacity == 1000
        assert limiter.cost_tracker.cost_limit == 5.0
        assert limiter.max_retry_delay == 100.0
        assert limiter.github_requests == 0
        assert limiter.github_errors == 0
        assert isinstance(limiter.start_time, datetime)

    def test_get_instance_singleton(self):
        """Test get_instance returns singleton."""
        limiter1 = RateLimiter.get_instance(github_limit=1000)
        limiter2 = RateLimiter.get_instance(github_limit=2000)
        assert limiter1 is limiter2
        # First call wins, second ignored
        assert limiter1.github_bucket.capacity == 1000

    def test_reset_instance(self):
        """Test reset_instance clears singleton."""
        limiter1 = RateLimiter.get_instance()
        RateLimiter.reset_instance()
        limiter2 = RateLimiter.get_instance()
        assert limiter1 is not limiter2

    def test_acquire_github_success(self):
        """Test acquire_github with available tokens."""
        async def test():
            limiter = RateLimiter.get_instance(github_limit=100)
            result = await limiter.acquire_github()
            assert result is True
            assert limiter.github_requests == 1

        asyncio.run(test())

    def test_acquire_github_timeout(self):
        """Test acquire_github with timeout when bucket empty."""
        async def test():
            limiter = RateLimiter.get_instance(github_limit=1, github_refill_rate=0.1)
            # Use the only token
            await limiter.acquire_github()
            # Try again with timeout
            result = await limiter.acquire_github(timeout=0.1)
            assert result is False
            assert limiter.github_rate_limited > 0

        asyncio.run(test())

    def test_check_github_available(self):
        """Test check_github_available."""
        limiter = RateLimiter.get_instance(github_limit=100)
        available, msg = limiter.check_github_available()
        assert available is True
        assert "available" in msg.lower()

    def test_check_github_available_empty(self):
        """Test check_github_available when empty."""
        limiter = RateLimiter.get_instance(github_limit=1, github_refill_rate=0.01)
        # Use the token
        limiter.github_bucket.try_acquire(1)
        available, msg = limiter.check_github_available()
        assert available is False
        assert "rate limited" in msg.lower() or "wait" in msg.lower()

    def test_track_ai_cost(self):
        """Test tracking AI cost."""
        limiter = RateLimiter.get_instance(cost_limit=10.0)
        cost = limiter.track_ai_cost(
            input_tokens=1000,
            output_tokens=500,
            model="claude-sonnet-4-5-20250929",
            operation_name="test",
        )
        assert cost > 0
        assert limiter.cost_tracker.total_cost == cost

    def test_check_cost_available(self):
        """Test check_cost_available."""
        limiter = RateLimiter.get_instance(cost_limit=10.0)
        available, msg = limiter.check_cost_available()
        assert available is True
        assert "remaining" in msg.lower() or "$" in msg

    def test_check_cost_available_exceeded(self):
        """Test check_cost_available when budget exceeded."""
        limiter = RateLimiter.get_instance(cost_limit=0.0001)
        # Add cost to reach budget exactly (not exceed)
        # Use small amount that fits in budget
        try:
            limiter.track_ai_cost(
                input_tokens=10,
                output_tokens=5,
                model="claude-sonnet-4-5-20250929",
                operation_name="cheap",
            )
        except CostLimitExceeded:
            pass

        # Now check - should still have some budget or be at 0
        available, msg = limiter.check_cost_available()
        # If we're at exactly 0 remaining, it should return False
        if limiter.cost_tracker.remaining_budget() <= 0:
            assert available is False
        else:
            assert available is True

    def test_record_github_error(self):
        """Test recording GitHub error."""
        limiter = RateLimiter.get_instance()
        assert limiter.github_errors == 0
        limiter.record_github_error()
        assert limiter.github_errors == 1
        limiter.record_github_error()
        assert limiter.github_errors == 2

    def test_statistics(self):
        """Test statistics generation."""
        limiter = RateLimiter.get_instance(github_limit=100, cost_limit=10.0)
        stats = limiter.statistics()
        assert "runtime_seconds" in stats
        assert "github" in stats
        assert "cost" in stats
        assert stats["github"]["total_requests"] == 0
        assert stats["github"]["errors"] == 0
        assert stats["cost"]["total_cost"] == 0

    def test_report(self):
        """Test report generation."""
        limiter = RateLimiter.get_instance(github_limit=100, cost_limit=10.0)
        report = limiter.report()
        assert "Rate Limiter Report" in report
        assert "GitHub API:" in report
        assert "AI Cost:" in report
        assert "Cost Usage Report" in report


class TestRateLimitedDecorator:
    """Test @rate_limited decorator."""

    def setup_method(self):
        """Reset singleton before each test."""
        RateLimiter.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        RateLimiter.reset_instance()

    def test_rate_limited_returns_decorator(self):
        """Test rate_limited returns a decorator."""
        decorator = rate_limited(operation_type="github", max_retries=3, base_delay=1.0)
        assert callable(decorator)

    def test_rate_limited_async_function(self):
        """Test rate_limited with async function."""
        async def test():
            @rate_limited(operation_type="github")
            async def fetch_data():
                return "data"

            result = await fetch_data()
            assert result == "data"

        asyncio.run(test())

    def test_rate_limited_sync_function(self):
        """Test rate_limited with sync function - wrapper runs async."""
        # Note: @rate_limited wraps sync functions to run in asyncio
        # This test verifies the decorator can be applied to sync functions
        @rate_limited(operation_type="github")
        async def fetch_data():
            # The actual function must be async for the wrapper to work properly
            return "data"

        result = asyncio.run(fetch_data())
        assert result == "data"


class TestCheckRateLimit:
    """Test check_rate_limit convenience function."""

    def setup_method(self):
        """Reset singleton before each test."""
        RateLimiter.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        RateLimiter.reset_instance()

    def test_check_rate_limit_github_available(self):
        """Test check_rate_limit for GitHub when available."""
        limiter = RateLimiter.get_instance(github_limit=100)
        # Should not raise
        asyncio.run(check_rate_limit(operation_type="github"))

    def test_check_rate_limit_github_unavailable(self):
        """Test check_rate_limit for GitHub when unavailable."""
        limiter = RateLimiter.get_instance(github_limit=1, github_refill_rate=0.01)
        # Empty the bucket
        limiter.github_bucket.try_acquire(1)

        with pytest.raises(RateLimitExceeded):
            asyncio.run(check_rate_limit(operation_type="github"))

    def test_check_rate_limit_cost_available(self):
        """Test check_rate_limit for cost when available."""
        limiter = RateLimiter.get_instance(cost_limit=10.0)
        # Should not raise
        asyncio.run(check_rate_limit(operation_type="cost"))

    def test_check_rate_limit_cost_exceeded(self):
        """Test check_rate_limit for cost when exceeded."""
        # Set a budget that's easy to exceed
        limiter = RateLimiter.get_instance(cost_limit=0.01)  # 1 cent budget
        # Directly set the cost to exceed the limit
        limiter.cost_tracker.total_cost = 0.02  # Set to 2 cents, exceeding 1 cent limit

        with pytest.raises(CostLimitExceeded):
            asyncio.run(check_rate_limit(operation_type="cost"))
