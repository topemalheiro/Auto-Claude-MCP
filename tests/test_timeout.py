"""
Tests for timeout functionality.

This module tests various timeout-related scenarios including:
- Subprocess timeouts
- Asyncio timeouts
- Time module operations
- Timeout edge cases and error handling
"""

import asyncio
import subprocess
import time
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

import pytest


class TestSubprocessTimeout:
    """Tests for subprocess timeout handling."""

    def test_subprocess_run_with_timeout_success(self):
        """Test subprocess.run completes successfully within timeout."""
        # Quick command that completes immediately
        result = subprocess.run(
            ["echo", "hello"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_subprocess_run_with_timeout_exceeded(self):
        """Test subprocess.run raises TimeoutExpired when timeout is exceeded."""
        with pytest.raises(subprocess.TimeoutExpired) as exc_info:
            subprocess.run(["sleep", "10"], timeout=0.1)

        assert exc_info.value.cmd == ["sleep", "10"]
        # Timeout value may have slight variation due to timing
        assert 0.09 < exc_info.value.timeout < 0.11

    def test_subprocess_run_timeout_zero(self):
        """Test subprocess.run with zero timeout (should timeout immediately)."""
        with pytest.raises(subprocess.TimeoutExpired):
            subprocess.run(["sleep", "1"], timeout=0)

    def test_subprocess_run_timeout_negative_treats_as_timeout(self):
        """Test subprocess.run with negative timeout causes immediate timeout."""
        # Negative timeout is treated as causing an immediate timeout
        with pytest.raises(subprocess.TimeoutExpired):
            subprocess.run(["echo", "test"], timeout=-1)

    def test_subprocess_run_timeout_fractional(self):
        """Test subprocess.run with fractional timeout."""
        # Quick command should complete within 0.5 seconds
        result = subprocess.run(
            ["true"],
            capture_output=True,
            timeout=0.5,
        )

        assert result.returncode == 0

    def test_subprocess_popen_wait_with_timeout(self):
        """Test Popen.wait() with timeout."""
        proc = subprocess.Popen(["sleep", "0.5"])

        # Should not timeout
        proc.wait(timeout=2)

        assert proc.returncode == 0

    def test_subprocess_popen_wait_timeout_exceeded(self):
        """Test Popen.wait() raises TimeoutExpired when timeout is exceeded."""
        proc = subprocess.Popen(["sleep", "10"])

        with pytest.raises(subprocess.TimeoutExpired):
            proc.wait(timeout=0.1)

        # Clean up
        proc.kill()
        proc.wait()

    def test_subprocess_popen_communicate_with_timeout(self):
        """Test Popen.communicate() with timeout."""
        proc = subprocess.Popen(
            ["echo", "test"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout, stderr = proc.communicate(timeout=2)

        assert b"test" in stdout
        assert proc.returncode == 0

    def test_subprocess_popen_communicate_timeout_exceeded(self):
        """Test Popen.communicate() raises TimeoutExpired when timeout is exceeded."""
        proc = subprocess.Popen(["sleep", "10"])

        with pytest.raises(subprocess.TimeoutExpired):
            proc.communicate(timeout=0.1)

        # Clean up
        proc.kill()
        proc.wait()


class TestAsyncioTimeout:
    """Tests for asyncio timeout handling."""

    @pytest.mark.asyncio
    async def test_wait_for_completes_within_timeout(self):
        """Test asyncio.wait_for completes successfully within timeout."""
        async def quick_task():
            await asyncio.sleep(0.1)
            return "done"

        result = await asyncio.wait_for(quick_task(), timeout=1.0)

        assert result == "done"

    @pytest.mark.asyncio
    async def test_wait_for_timeout_exceeded(self):
        """Test asyncio.wait_for raises TimeoutError when timeout is exceeded."""
        async def slow_task():
            await asyncio.sleep(10)
            return "done"

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(slow_task(), timeout=0.1)

    @pytest.mark.asyncio
    async def test_wait_for_timeout_zero(self):
        """Test asyncio.wait_for with zero timeout times out."""
        async def instant_task():
            return "instant"

        # Zero timeout causes immediate timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(instant_task(), timeout=0)

    @pytest.mark.asyncio
    async def test_wait_for_timeout_negative_times_out(self):
        """Test asyncio.wait_for with negative timeout causes timeout."""
        async def simple_task():
            return "result"

        # Negative timeout is treated as causing immediate timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(simple_task(), timeout=-1.0)

    @pytest.mark.asyncio
    async def test_gather_with_timeout(self):
        """Test asyncio.gather with individual task timeouts."""
        async def task_one():
            await asyncio.sleep(0.1)
            return "one"

        async def task_two():
            await asyncio.sleep(0.1)
            return "two"

        # Wrap tasks with wait_for for timeout
        result = await asyncio.gather(
            asyncio.wait_for(task_one(), timeout=1.0),
            asyncio.wait_for(task_two(), timeout=1.0),
        )

        assert result == ["one", "two"]

    @pytest.mark.asyncio
    async def test_gather_one_task_timeout(self):
        """Test asyncio.gather when one task times out."""
        async def quick_task():
            await asyncio.sleep(0.1)
            return "quick"

        async def slow_task():
            await asyncio.sleep(10)
            return "slow"

        # First task should complete, second should timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.gather(
                asyncio.wait_for(quick_task(), timeout=1.0),
                asyncio.wait_for(slow_task(), timeout=0.2),
            )

    @pytest.mark.asyncio
    async def test_timeout_context_manager(self):
        """Test asyncio.timeout context manager (Python 3.11+)."""
        async def quick_task():
            await asyncio.sleep(0.1)
            return "done"

        try:
            async with asyncio.timeout(1.0):
                result = await quick_task()
                assert result == "done"
        except asyncio.TimeoutError:
            pytest.fail("Should not have timed out")

    @pytest.mark.asyncio
    async def test_timeout_context_manager_exceeded(self):
        """Test asyncio.timeout context manager when timeout is exceeded."""
        async def slow_task():
            await asyncio.sleep(10)
            return "done"

        with pytest.raises(asyncio.TimeoutError):
            async with asyncio.timeout(0.1):
                await slow_task()

    @pytest.mark.asyncio
    async def test_shield_bypasses_timeout(self):
        """Test asyncio.shield protects task from timeout."""
        task_started = False
        task_completed = False

        async def shielded_task():
            nonlocal task_started, task_completed
            task_started = True
            await asyncio.sleep(0.2)
            task_completed = True
            return "shielded"

        async def with_timeout():
            try:
                return await asyncio.wait_for(
                    asyncio.shield(shielded_task()),
                    timeout=0.1
                )
            except asyncio.TimeoutError:
                # Task continues in background
                return "timed_out"

        result = await with_timeout()

        assert result == "timed_out"
        assert task_started is True
        # Wait for background task to complete
        await asyncio.sleep(0.15)
        assert task_completed is True


class TestTimeModuleOperations:
    """Tests for time module operations used in timeout scenarios."""

    def test_time_sleep_basic(self):
        """Test time.sleep basic functionality."""
        start = time.time()
        time.sleep(0.1)
        elapsed = time.time() - start

        # Allow some tolerance
        assert 0.05 < elapsed < 0.2

    def test_time_sleep_zero(self):
        """Test time.sleep(0) returns immediately."""
        start = time.time()
        time.sleep(0)
        elapsed = time.time() - start

        # Should be nearly instantaneous
        assert elapsed < 0.01

    def test_time_sleep_negative_raises_error(self):
        """Test time.sleep with negative value raises ValueError."""
        with pytest.raises(ValueError, match="sleep length must be non-negative"):
            time.sleep(-1)

    def test_time_sleep_fractional(self):
        """Test time.sleep with fractional seconds."""
        start = time.time()
        time.sleep(0.123)
        elapsed = time.time() - start

        # Allow some tolerance
        assert 0.1 < elapsed < 0.2

    def test_time_monotonic(self):
        """Test time.monotonic returns increasing values."""
        t1 = time.monotonic()
        time.sleep(0.05)
        t2 = time.monotonic()

        assert t2 > t1
        assert 0.04 < (t2 - t1) < 0.1

    def test_time_perf_counter(self):
        """Test time.perf_counter for high-resolution timing."""
        t1 = time.perf_counter()
        time.sleep(0.05)
        t2 = time.perf_counter()

        assert t2 > t1
        assert 0.04 < (t2 - t1) < 0.1


class TestThreadPoolExecutorTimeout:
    """Tests for ThreadPoolExecutor with timeout."""

    def test_future_result_timeout_success(self):
        """Test Future.result() with timeout completes successfully."""
        def quick_task():
            time.sleep(0.1)
            return "done"

        with ThreadPoolExecutor() as executor:
            future = executor.submit(quick_task)
            result = future.result(timeout=1.0)

        assert result == "done"

    def test_future_result_timeout_exceeded(self):
        """Test Future.result() raises TimeoutError when timeout is exceeded."""
        def slow_task():
            time.sleep(10)
            return "done"

        with ThreadPoolExecutor() as executor:
            future = executor.submit(slow_task)

            with pytest.raises(FuturesTimeoutError):
                future.result(timeout=0.1)

            # Clean up
            future.cancel()

    def test_future_result_timeout_zero(self):
        """Test Future.result() with zero timeout."""
        def instant_task():
            return "instant"

        with ThreadPoolExecutor() as executor:
            future = executor.submit(instant_task)
            # Zero timeout - may complete if task is ready
            result = future.result(timeout=0)

        assert result == "instant"

    def test_concurrent_future_wait_timeout(self):
        """Test concurrent.futures wait() with timeout."""
        from concurrent.futures import wait, FIRST_COMPLETED

        def slow_task():
            time.sleep(10)
            return "done"

        with ThreadPoolExecutor() as executor:
            future = executor.submit(slow_task)

            # wait returns not_done when timeout is exceeded
            done, not_done = wait([future], timeout=0.1)

            assert len(done) == 0
            assert len(not_done) == 1

            # Clean up
            future.cancel()


class TestMockedTimeoutScenarios:
    """Tests for timeout scenarios using mocks."""

    @pytest.mark.asyncio
    async def test_mocked_async_timeout(self):
        """Test timeout handling with mocked async function."""
        # Create a truly async operation that won't complete
        async def mock_operation():
            # Create a future that never completes
            fut = asyncio.Future()
            return await fut

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(mock_operation(), timeout=0.1)

    def test_mocked_subprocess_timeout(self):
        """Test subprocess timeout with mocked subprocess."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "success"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = subprocess.run(
                ["test", "command"],
                capture_output=True,
                timeout=5,
            )

            assert result.returncode == 0
            mock_run.assert_called_once()

    def test_mocked_time_sleep(self):
        """Test time.sleep with mocked time."""
        with patch("time.sleep") as mock_sleep:
            time.sleep(400)

            mock_sleep.assert_called_once_with(400)

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self):
        """Test retry logic after timeout."""
        call_count = 0

        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                await asyncio.sleep(10)  # Will timeout
            return "success"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = await asyncio.wait_for(flaky_operation(), timeout=0.1)
                assert result == "success"
                assert call_count == 3
                break
            except asyncio.TimeoutError:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(0.1)  # Backoff before retry
        else:
            pytest.fail("Should have succeeded on retry")

    @pytest.mark.asyncio
    async def test_timeout_with_cleanup(self):
        """Test timeout handling with resource cleanup."""
        resource_cleaned = False

        async def operation_with_cleanup():
            nonlocal resource_cleaned
            try:
                await asyncio.sleep(10)
                return "result"
            finally:
                resource_cleaned = True

        with pytest.raises(asyncio.TimeoutError):
            async with asyncio.timeout(0.1):
                await operation_with_cleanup()

        # Give cleanup a chance to run
        await asyncio.sleep(0.05)
        assert resource_cleaned is True


class TestTimeoutEdgeCases:
    """Tests for timeout edge cases."""

    @pytest.mark.asyncio
    async def test_very_small_timeout_completes(self):
        """Test very small timeout still allows instant task to complete."""
        async def instant_task():
            return "done"

        # Very small timeout - instant task may still complete
        # The task is just a return statement with minimal overhead
        result = await asyncio.wait_for(instant_task(), timeout=1e-9)

        assert result == "done"

    @pytest.mark.asyncio
    async def test_very_large_timeout(self):
        """Test handling of very large timeout values."""
        async def instant_task():
            return "instant"

        # Very large timeout - should complete immediately
        result = await asyncio.wait_for(instant_task(), timeout=1e9)

        assert result == "instant"

    def test_subprocess_very_small_timeout(self):
        """Test subprocess with very small timeout."""
        # Very small timeout - likely to timeout even for quick command
        with pytest.raises(subprocess.TimeoutExpired):
            subprocess.run(["echo", "test"], timeout=1e-9)

    @pytest.mark.asyncio
    async def test_multiple_concurrent_timeouts(self):
        """Test handling multiple concurrent tasks with different timeouts."""
        async def task_with_delay(delay):
            await asyncio.sleep(delay)
            return f"done-{delay}"

        # Multiple tasks with different timeouts
        results = await asyncio.gather(
            asyncio.wait_for(task_with_delay(0.05), timeout=0.2),
            asyncio.wait_for(task_with_delay(0.05), timeout=0.2),
            asyncio.wait_for(task_with_delay(0.05), timeout=0.2),
        )

        assert len(results) == 3
        assert all("done-0.05" in r for r in results)

    @pytest.mark.asyncio
    async def test_timeout_cancellation_propagation(self):
        """Test that timeout cancellation propagates correctly."""
        task_cancelled = False

        async def cancellable_task():
            nonlocal task_cancelled
            try:
                await asyncio.sleep(10)
                return "not_cancelled"
            except asyncio.CancelledError:
                task_cancelled = True
                raise

        with pytest.raises(asyncio.TimeoutError):
            async with asyncio.timeout(0.1):
                await cancellable_task()

        assert task_cancelled is True


class TestTimeoutErrorHandling:
    """Tests for timeout error handling patterns."""

    @pytest.mark.asyncio
    async def test_timeout_with_custom_exception(self):
        """Test raising custom exception on timeout."""
        class CustomTimeoutError(Exception):
            pass

        # Create a future that never completes
        fut = asyncio.Future()

        with pytest.raises(CustomTimeoutError, match="Operation timed out"):
            try:
                await asyncio.wait_for(fut, timeout=0.1)
            except asyncio.TimeoutError:
                raise CustomTimeoutError("Operation timed out")

    @pytest.mark.asyncio
    async def test_timeout_with_fallback(self):
        """Test providing fallback value on timeout."""
        async def unreliable_operation():
            await asyncio.sleep(10)
            return "result"

        try:
            result = await asyncio.wait_for(unreliable_operation(), timeout=0.1)
        except asyncio.TimeoutError:
            result = "fallback"

        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_timeout_with_logging(self, caplog):
        """Test timeout handling with logging."""
        import logging

        async def slow_operation():
            await asyncio.sleep(10)
            return "result"

        with caplog.at_level(logging.WARNING):
            try:
                await asyncio.wait_for(slow_operation(), timeout=0.1)
            except asyncio.TimeoutError:
                logging.warning("Operation timed out after 0.1 seconds")

        assert "timed out" in caplog.text.lower()

    def test_subprocess_timeout_with_fallback(self):
        """Test subprocess timeout with fallback value."""
        try:
            result = subprocess.run(
                ["sleep", "10"],
                capture_output=True,
                text=True,
                timeout=0.1,
            )
            output = result.stdout
        except subprocess.TimeoutExpired:
            output = "fallback_output"

        assert output == "fallback_output"
