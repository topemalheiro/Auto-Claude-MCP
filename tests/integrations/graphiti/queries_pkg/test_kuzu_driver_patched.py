"""Tests for kuzu_driver_patched.py module.

These tests verify the PatchedKuzuDriver wrapper functionality. Tests are skipped
when graphiti_core is not available in the environment.
"""

import pytest


def _has_db():
    """Check if graphiti_core.driver.kuzu_driver can be imported (requires kuzu or real_ladybug)."""
    try:
        import kuzu  # noqa: F401
        return True
    except ImportError:
        return False


# Try importing graphiti_core - if not available, skip all tests
try:
    pass
except ImportError:
    pytest.skip("graphiti_core not available", allow_module_level=True)

from integrations.graphiti.queries_pkg.kuzu_driver_patched import create_patched_kuzu_driver


class TestCreatePatchedKuzuDriver:
    """Tests for create_patched_kuzu_driver function."""

    def test_create_patched_kuzu_driver_default_params(self):
        """Test create_patched_kuzu_driver with default parameters."""
        # The function should create a driver instance
        # We can't fully test without graphiti_core installed properly
        # but we can verify it imports and the signature is correct
        import inspect
        sig = inspect.signature(create_patched_kuzu_driver)
        params = sig.parameters
        assert 'db' in params
        assert 'max_concurrent_queries' in params
        assert params['db'].default == ':memory:'
        assert params['max_concurrent_queries'].default == 1

    def test_create_patched_kuzu_driver_custom_params(self):
        """Test create_patched_kuzu_driver with custom parameters signature."""
        import inspect
        sig = inspect.signature(create_patched_kuzu_driver)
        params = sig.parameters
        # Verify custom params are accepted
        assert len(params) >= 2


class TestPatchedKuzuDriverExists:
    """Tests to verify the patched driver structure."""

    def test_module_exports_create_function(self):
        """Test that the module exports create_patched_kuzu_driver."""
        from integrations.graphiti.queries_pkg import kuzu_driver_patched
        assert hasattr(kuzu_driver_patched, 'create_patched_kuzu_driver')

    def test_module_has_docstring(self):
        """Test that the module has documentation."""
        from integrations.graphiti.queries_pkg import kuzu_driver_patched
        assert kuzu_driver_patched.__doc__ is not None
        assert 'Patched KuzuDriver' in kuzu_driver_patched.__doc__


@pytest.mark.skipif(
    not _has_db(),
    reason="Requires graphiti_core.driver.kuzu_driver to be importable (needs kuzu or properly configured real_ladybug)"
)
class TestPatchedKuzuDriverIntegration:
    """Integration tests that require database driver to be available."""

    @pytest.mark.asyncio
    async def test_create_and_initialize_driver(self):
        """Test creating and initializing the driver with in-memory database."""
        from integrations.graphiti.queries_pkg.kuzu_driver_patched import create_patched_kuzu_driver

        # Create a driver with in-memory database
        driver = create_patched_kuzu_driver(db=":memory:")

        assert driver is not None
        assert hasattr(driver, '_database')
        assert driver._database == ":memory:"

    @pytest.mark.asyncio
    async def test_driver_has_execute_query_method(self):
        """Test that the driver has the execute_query method."""
        from integrations.graphiti.queries_pkg.kuzu_driver_patched import create_patched_kuzu_driver

        driver = create_patched_kuzu_driver()

        assert hasattr(driver, 'execute_query')

    @pytest.mark.asyncio
    async def test_driver_has_build_indices_method(self):
        """Test that the driver has the build_indices_and_constraints method."""
        from integrations.graphiti.queries_pkg.kuzu_driver_patched import create_patched_kuzu_driver

        driver = create_patched_kuzu_driver()

        assert hasattr(driver, 'build_indices_and_constraints')

    def test_driver_has_setup_schema_method(self):
        """Test that the driver has the setup_schema method."""
        from integrations.graphiti.queries_pkg.kuzu_driver_patched import create_patched_kuzu_driver

        driver = create_patched_kuzu_driver()

        assert hasattr(driver, 'setup_schema')
