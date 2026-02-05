"""Pytest configuration for graphiti tests."""

import pytest


def pytest_collection_modifyitems(items):
    """Prevent collection of test_ prefixed API functions."""
    # Skip the actual API functions that start with test_
    # (test_graphiti_connection and test_provider_configuration in memory module)
    skip_api_functions = pytest.mark.skip(
        reason="API function with test_ prefix - not a test function"
    )

    for item in items:
        # Check if the item is one of the API functions we want to skip
        if hasattr(item, 'obj') and item.obj.__module__ == 'integrations.graphiti.memory':
            if item.name in ['test_graphiti_connection', 'test_provider_configuration']:
                item.add_marker(skip_api_functions)
