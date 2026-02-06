"""Pytest configuration for graphiti tests."""

import asyncio

import pytest


def _check_graphiti_available() -> bool:
    """Check if graphiti dependencies are available."""
    try:
        import kuzu
        return True
    except ImportError:
        try:
            from real_ladybug import ladybug
            return True
        except ImportError:
            return False


def pytest_collection_modifyitems(items):
    """Prevent collection of test_ prefixed API functions and skip integration tests."""
    # Skip the actual API functions that start with test_
    # (test_graphiti_connection and test_provider_configuration in memory module)
    skip_api_functions = pytest.mark.skip(
        reason="API function with test_ prefix - not a test function"
    )

    # Skip integration tests that require database
    skip_no_db = pytest.mark.skip(
        reason="graphiti dependencies (kuzu or real_ladybug) not available"
    )

    has_db = _check_graphiti_available()

    for item in items:
        # Check if the item is one of the API functions we want to skip
        if hasattr(item, 'obj') and item.obj.__module__ == 'integrations.graphiti.memory':
            if item.name in ['test_graphiti_connection', 'test_provider_configuration']:
                item.add_marker(skip_api_functions)

        # Skip integration tests from test_test_graphiti_memory.py and test_test_ollama_embedding_memory.py
        # These are imported from standalone test scripts that need real database
        if not has_db:
            if item.parent.name in ['test_test_graphiti_memory.py', 'test_test_ollama_embedding_memory.py']:
                # Skip the top-level coroutine tests (not the class-based tests)
                if item.cls is None and asyncio.iscoroutinefunction(item.obj):
                    item.add_marker(skip_no_db)
