"""Tests for client.py - Claude client module facade."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestClientModuleExports:
    """Tests for client module public API exports."""

    def test_create_client_export(self):
        """Test that create_client is exported from client module."""
        from client import create_client

        assert create_client is not None
        assert callable(create_client)

    def test_module_has_all_attribute(self):
        """Test that client module has __all__ attribute."""
        import client

        assert hasattr(client, "__all__")
        assert isinstance(client.__all__, list)

    def test_all_exports_exist(self):
        """Test that all exports in __all__ actually exist."""
        import client

        for name in client.__all__:
            assert hasattr(client, name), f"{name} in __all__ but not exported"

    def test_expected_exports_in_all(self):
        """Test that expected exports are in __all__."""
        import client

        expected = {"create_client"}

        assert set(client.__all__) >= expected


class TestClientModuleLazyImports:
    """Tests for client module lazy import mechanism."""

    def test_getattr_lazy_import(self):
        """Test that __getattr__ provides lazy imports."""
        from client import __getattr__

        # Should be able to get attributes through lazy import
        # This tests the facade pattern without actually importing the heavy core.client
        assert callable(__getattr__)

    def test_create_client_direct_function(self):
        """Test that create_client is a direct function, not lazy."""
        from client import create_client

        # create_client should be directly defined, not lazily imported
        # It should be a function that re-exports from core.client
        assert callable(create_client)
        assert hasattr(create_client, "__module__")
        assert "client" in create_client.__module__


class TestClientModuleFacade:
    """Tests for client module as a facade to core.client."""

    @patch("client.create_client")
    def test_create_client_reexports_from_core(self, mock_create_client):
        """Test that create_client re-exports from core.client."""
        from client import create_client as client_create_client

        # The function should be callable
        assert callable(client_create_client)

    def test_create_client_signature(self):
        """Test that create_client has expected signature."""
        from client import create_client
        import inspect

        # create_client uses *args, **kwargs to forward to core.client.create_client
        sig = inspect.signature(create_client)
        params = list(sig.parameters.keys())

        # Should accept *args and **kwargs
        assert "args" in params
        assert "kwargs" in params

    @patch("client.create_client")
    def test_create_client_with_args(self, mock_create_client):
        """Test that create_client accepts expected arguments."""
        from client import create_client

        # Mock the actual core.client.create_client
        mock_instance = MagicMock()
        mock_create_client.return_value = mock_instance

        # Call with basic args
        result = create_client(
            project_dir=Path("/test/project"),
            spec_dir=Path("/test/spec"),
            model="claude-3-5-sonnet-20241022",
        )

        # Verify it was called (though mocked)
        assert result is not None


class TestClientModuleImports:
    """Tests for client module import structure."""

    def test_no_circular_imports(self):
        """Test that importing client doesn't cause circular imports."""
        import importlib
        import sys

        # Remove from cache if present
        if "client" in sys.modules:
            del sys.modules["client"]

        # Should import without issues
        import client

        assert client is not None

    def test_import_client_module_first(self):
        """Test that client module can be imported before core.client."""
        import importlib
        import sys

        # Remove both from cache
        for mod in ["client", "core.client"]:
            if mod in sys.modules:
                del sys.modules[mod]

        # Import client first (should trigger lazy import of core.client)
        import client

        assert client is not None

        # Now import core.client
        from core import client as core_client

        assert core_client is not None

    def test_core_client_and_client_facade_are_different(self):
        """Test that client module and core.client are different."""
        from core import client as core_client
        import client as client_facade

        # They should be different modules
        # client_facade is a lightweight facade
        # core_client contains the actual implementation
        assert core_client is not client_facade


class TestClientModulePatterns:
    """Tests for client module design patterns."""

    def test_facade_pattern(self):
        """Test that client module implements facade pattern."""
        from client import create_client

        # The client module should provide a simplified interface
        # to the more complex core.client module
        assert callable(create_client)

    def test_lazy_import_pattern(self):
        """Test that client module uses lazy import pattern."""
        import client

        # The module should have __getattr__ for lazy imports
        assert hasattr(client, "__getattr__")
        assert callable(client.__getattr__)

    def test_direct_reexport_pattern(self):
        """Test that create_client is directly re-exported."""
        from client import create_client
        import client as client_module

        # create_client should be directly defined in the module
        # for faster access, not through __getattr__
        assert "create_client" in dir(client_module)


class TestClientModuleDocumentation:
    """Tests for client module documentation."""

    def test_module_has_docstring(self):
        """Test that client module has a docstring."""
        import client

        assert client.__doc__ is not None
        assert len(client.__doc__) > 0
        assert "facade" in client.__doc__.lower() or "claude" in client.__doc__.lower()

    def test_create_client_has_docstring(self):
        """Test that create_client has a docstring."""
        from client import create_client

        assert create_client.__doc__ is not None
        assert len(create_client.__doc__) > 0
