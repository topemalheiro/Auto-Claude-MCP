"""Tests for test_memory_save"""

import pytest
from unittest.mock import patch, MagicMock
import sys


@pytest.mark.asyncio
async def test_test_memory_imports():
    """Test test_memory_imports"""
    from scripts.test_memory_save import test_memory_imports

    # Act - await the async function
    result = await test_memory_imports()

    # Assert
    # The function returns True if all imports succeed, False otherwise
    # We expect it to succeed in test environment
    assert result is True


@pytest.mark.asyncio
async def test_test_graphiti_status():
    """Test test_graphiti_status"""
    from scripts.test_memory_save import test_graphiti_status

    # Act
    result = await test_graphiti_status()

    # Assert
    # Returns Graphiti enabled status (bool)
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_test_sentry_status():
    """Test test_sentry_status"""
    from scripts.test_memory_save import test_sentry_status

    # Act
    result = await test_sentry_status()

    # Assert
    # Returns True if Sentry status check succeeds
    assert result is True


@pytest.mark.asyncio
async def test_test_memory_save_flow():
    """Test test_memory_save_flow"""
    from scripts.test_memory_save import test_memory_save_flow

    # Act
    result = await test_memory_save_flow()

    # Assert
    # Returns True if memory save flow succeeds
    assert result is True


@pytest.mark.asyncio
async def test_test_sentry_capture():
    """Test test_sentry_capture"""
    from scripts.test_memory_save import test_sentry_capture

    # Act
    result = await test_sentry_capture()

    # Assert
    # Returns True (skips if Sentry not enabled)
    assert result is True


@pytest.mark.asyncio
async def test_main():
    """Test main"""
    from scripts.test_memory_save import main

    # Act
    # main() calls sys.exit, so we need to patch it
    with patch('sys.exit') as mock_exit:
        await main()

        # Assert - main should complete successfully
        assert mock_exit.called
