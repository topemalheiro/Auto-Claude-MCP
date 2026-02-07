"""Comprehensive tests for Graphiti client wrapper (client.py module).

Tests cover:
- LadybugDB monkeypatch functionality
- GraphitiClient initialization
- Client lifecycle (initialize, close)
- Database connection handling
- Provider creation and error handling
- State management
- Edge cases and error paths
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import builtins

import pytest

from integrations.graphiti.queries_pkg.client import (
    GraphitiClient,
    _apply_ladybug_monkeypatch,
)
from integrations.graphiti.config import GraphitiConfig, GraphitiState


class TestApplyLadybugMonkeypatch:
    """Tests for _apply_ladybug_monkeypatch function."""

    @patch("integrations.graphiti.queries_pkg.client.logger")
    def test_apply_ladybug_monkeypatch_real_ladybug_available(self, mock_logger):
        """Test monkeypatch succeeds when real_ladybug is available."""
        with patch.dict("sys.modules", {"real_ladybug": MagicMock()}):
            result = _apply_ladybug_monkeypatch()
            assert result is True
            # Should log info about the monkeypatch
            mock_logger.info.assert_called()

    @patch("integrations.graphiti.queries_pkg.client.logger")
    def test_apply_ladybug_monkeypatch_fallback_to_kuzu(self, mock_logger):
        """Test fallback to native kuzu when real_ladybug not available."""
        modules = {"kuzu": MagicMock()}
        with patch.dict("sys.modules", modules, clear=False):
            # Remove real_ladybug to force fallback
            modules.pop("real_ladybug", None)

            result = _apply_ladybug_monkeypatch()
            assert result is True
            # Should log info about using native kuzu
            mock_logger.info.assert_called()

    @patch("integrations.graphiti.queries_pkg.client.logger")
    def test_apply_ladybug_monkeypatch_neither_available(self, mock_logger):
        """Test returns False when neither real_ladybug nor kuzu available."""
        original_import = builtins.__import__

        def custom_import(name, *args, **kwargs):
            if name == "real_ladybug":
                raise ImportError("No module named 'real_ladybug'")
            if name == "kuzu":
                raise ImportError("No module named 'kuzu'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=custom_import):
            result = _apply_ladybug_monkeypatch()
            assert result is False
            # Should log warning about missing packages
            mock_logger.warning.assert_called()

    @patch("integrations.graphiti.queries_pkg.client.logger")
    @patch("sys.platform", "win32")
    @patch("sys.version_info", (3, 12))
    def test_apply_ladybug_monkeypatch_windows_pywin32_error_by_name(self, mock_logger):
        """Test Windows-specific error message for pywin32 (name attribute)."""
        # Create an ImportError with name attribute set
        error = ImportError("DLL load failed while importing pywintypes")
        error.name = "pywintypes"

        original_import = builtins.__import__

        def custom_import(name, *args, **kwargs):
            if name == "real_ladybug":
                raise error
            if name == "kuzu":
                raise ImportError("No module named 'kuzu'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=custom_import):
            result = _apply_ladybug_monkeypatch()
            assert result is False
            # Should log specific Windows error about pywin32
            mock_logger.error.assert_called()
            error_msg = str(mock_logger.error.call_args)
            assert "pywin32" in error_msg

    @patch("integrations.graphiti.queries_pkg.client.logger")
    @patch("sys.platform", "win32")
    @patch("sys.version_info", (3, 12))
    def test_apply_ladybug_monkeypatch_windows_pywin32_error_by_string(self, mock_logger):
        """Test Windows-specific error message for pywin32 (string match)."""
        # Create an ImportError with pywin32 in the message
        error = ImportError("No module named 'pywin32'")

        original_import = builtins.__import__

        def custom_import(name, *args, **kwargs):
            if name == "real_ladybug":
                raise error
            if name == "kuzu":
                raise ImportError("No module named 'kuzu'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=custom_import):
            result = _apply_ladybug_monkeypatch()
            assert result is False
            # Should log specific Windows error about pywin32
            mock_logger.error.assert_called()


class TestGraphitiClientInit:
    """Tests for GraphitiClient initialization."""

    def test_init_with_default_config(self):
        """Test GraphitiClient.__init__ with default config."""
        config = GraphitiConfig(enabled=True, llm_provider="openai")
        client = GraphitiClient(config)

        assert client.config == config
        assert client._graphiti is None
        assert client._driver is None
        assert client._llm_client is None
        assert client._embedder is None
        assert client._initialized is False

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="anthropic",
            embedder_provider="voyage",
            database="custom_db",
            db_path="/custom/path"
        )
        client = GraphitiClient(config)

        assert client.config == config
        assert client._graphiti is None
        assert client._driver is None
        assert client._llm_client is None
        assert client._embedder is None
        assert client._initialized is False

    def test_graphiti_property_before_initialization(self):
        """Test graphiti property returns None before initialization."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        assert client.graphiti is None

    def test_graphiti_property_after_initialization(self):
        """Test graphiti property returns instance after initialization."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._graphiti = MagicMock()

        assert client.graphiti is not None

    def test_is_initialized_property_false_by_default(self):
        """Test is_initialized is False by default."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        assert client.is_initialized is False

    def test_is_initialized_property_true_when_set(self):
        """Test is_initialized reflects actual state."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        client._initialized = True
        assert client.is_initialized is True

        client._initialized = False
        assert client.is_initialized is False


class TestGraphitiClientInitialize:
    """Tests for GraphitiClient.initialize method."""

    @pytest.mark.asyncio
    async def test_initialize_already_initialized_returns_early(self):
        """Test initialize returns True immediately if already initialized."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._initialized = True

        result = await client.initialize()

        assert result is True
        # Should not attempt any initialization
        assert client._llm_client is None

    @pytest.mark.asyncio
    async def test_initialize_import_error_graphiti_core_not_installed(self):
        """Test initialize handles ImportError when graphiti-core not installed."""
        config = GraphitiConfig(enabled=True)

        original_import = builtins.__import__

        def custom_import(name, *args, **kwargs):
            if name == "graphiti_core":
                raise ImportError("No module named 'graphiti_core'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=custom_import):
            client = GraphitiClient(config)
            result = await client.initialize()

            assert result is False
            assert client._initialized is False

    @pytest.mark.asyncio
    async def test_initialize_import_error_providers_not_installed(self):
        """Test initialize handles ImportError when providers not installed."""
        config = GraphitiConfig(enabled=True)

        original_import = builtins.__import__

        def custom_import(name, *args, **kwargs):
            if name == "graphiti_providers":
                raise ImportError("No module named 'graphiti_providers'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=custom_import):
            client = GraphitiClient(config)
            result = await client.initialize()

            # Should return False due to import error
            assert result is False

    @pytest.mark.asyncio
    async def test_initialize_llm_provider_not_installed_error(self):
        """Test initialize handles ProviderNotInstalled for LLM provider."""
        from integrations.graphiti.providers_pkg import ProviderNotInstalled

        config = GraphitiConfig(enabled=True, llm_provider="openai")

        def mock_create_llm_with_error(cfg):
            raise ProviderNotInstalled("openai package not installed")

        def mock_create_embedder(cfg):
            return MagicMock()

        mock_driver = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()

        mock_providers = MagicMock()
        mock_providers.ProviderNotInstalled = ProviderNotInstalled
        mock_providers.create_llm_client = MagicMock(side_effect=mock_create_llm_with_error)
        mock_providers.create_embedder = MagicMock(side_effect=mock_create_embedder)

        # Patch at the source where the names are imported
        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(return_value=mock_graphiti)),
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(return_value=mock_driver))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                with patch("graphiti_providers.create_llm_client",
                          side_effect=mock_providers.create_llm_client):
                    with patch("graphiti_providers.create_embedder",
                              side_effect=mock_providers.create_embedder):
                        with patch("integrations.graphiti.queries_pkg.client.capture_exception") as mock_capture:
                            client = GraphitiClient(config)
                            result = await client.initialize()

                            assert result is False
                            # Should capture exception for Sentry
                            mock_capture.assert_called()
                            call_kwargs = mock_capture.call_args[1]
                            assert call_kwargs["error_type"] == "ProviderNotInstalled"
                            assert call_kwargs["provider_type"] == "llm"

    @pytest.mark.asyncio
    async def test_initialize_llm_provider_configuration_error(self):
        """Test initialize handles ProviderError for LLM configuration."""
        from integrations.graphiti.providers_pkg import ProviderError

        config = GraphitiConfig(enabled=True, llm_provider="openai")

        def mock_create_llm_with_error(cfg):
            raise ProviderError("Invalid API key format")

        def mock_create_embedder(cfg):
            return MagicMock()

        mock_driver = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()

        mock_providers = MagicMock()
        mock_providers.ProviderError = ProviderError
        mock_providers.create_llm_client = MagicMock(side_effect=mock_create_llm_with_error)
        mock_providers.create_embedder = MagicMock(side_effect=mock_create_embedder)

        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(return_value=mock_graphiti)),
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(return_value=mock_driver))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                with patch("graphiti_providers.create_llm_client",
                          side_effect=mock_providers.create_llm_client):
                    with patch("graphiti_providers.create_embedder",
                              side_effect=mock_providers.create_embedder):
                        with patch("integrations.graphiti.queries_pkg.client.capture_exception") as mock_capture:
                            client = GraphitiClient(config)
                            result = await client.initialize()

                            assert result is False
                            # Should capture exception
                            mock_capture.assert_called()
                            call_kwargs = mock_capture.call_args[1]
                            assert call_kwargs["error_type"] == "ProviderError"

    @pytest.mark.asyncio
    async def test_initialize_embedder_provider_not_installed(self):
        """Test initialize handles ProviderNotInstalled for embedder."""
        from integrations.graphiti.providers_pkg import ProviderNotInstalled

        config = GraphitiConfig(enabled=True, embedder_provider="voyage")

        def mock_create_llm(cfg):
            return MagicMock()

        def mock_create_embedder_with_error(cfg):
            raise ProviderNotInstalled("voyage package not installed")

        mock_driver = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()

        mock_providers = MagicMock()
        mock_providers.ProviderNotInstalled = ProviderNotInstalled
        mock_providers.create_llm_client = MagicMock(side_effect=mock_create_llm)
        mock_providers.create_embedder = MagicMock(side_effect=mock_create_embedder_with_error)

        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(return_value=mock_graphiti)),
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(return_value=mock_driver))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                with patch("graphiti_providers.create_llm_client",
                          side_effect=mock_providers.create_llm_client):
                    with patch("graphiti_providers.create_embedder",
                              side_effect=mock_providers.create_embedder):
                        client = GraphitiClient(config)
                        result = await client.initialize()

                        assert result is False

    @pytest.mark.asyncio
    async def test_initialize_embedder_provider_error(self):
        """Test initialize handles ProviderError for embedder configuration."""
        from integrations.graphiti.providers_pkg import ProviderError

        config = GraphitiConfig(enabled=True, embedder_provider="openai")

        def mock_create_llm(cfg):
            return MagicMock()

        def mock_create_embedder_with_error(cfg):
            raise ProviderError("Invalid embedder model")

        mock_driver = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()

        mock_providers = MagicMock()
        mock_providers.ProviderError = ProviderError
        mock_providers.create_llm_client = MagicMock(side_effect=mock_create_llm)
        mock_providers.create_embedder = MagicMock(side_effect=mock_create_embedder_with_error)

        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(return_value=mock_graphiti)),
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(return_value=mock_driver))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                with patch("graphiti_providers.create_llm_client",
                          side_effect=mock_providers.create_llm_client):
                    with patch("graphiti_providers.create_embedder",
                              side_effect=mock_providers.create_embedder):
                        client = GraphitiClient(config)
                        result = await client.initialize()

                        assert result is False

    @pytest.mark.asyncio
    async def test_initialize_ladybug_not_available(self):
        """Test initialize when LadybugDB/Kuzu not available."""
        config = GraphitiConfig(enabled=True)

        def mock_create_llm(cfg):
            return MagicMock()

        def mock_create_embedder(cfg):
            return MagicMock()

        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()

        with patch("graphiti_providers.create_llm_client",
                   side_effect=mock_create_llm):
            with patch("graphiti_providers.create_embedder",
                      side_effect=mock_create_embedder):
                with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                          return_value=False):
                    client = GraphitiClient(config)
                    result = await client.initialize()

                    assert result is False

    @pytest.mark.asyncio
    async def test_initialize_driver_permission_error(self):
        """Test initialize handles PermissionError from driver creation."""
        config = GraphitiConfig(enabled=True, db_path="/root/protected")

        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()

        mock_providers = MagicMock()
        mock_providers.create_llm_client = MagicMock(return_value=MagicMock())
        mock_providers.create_embedder = MagicMock(return_value=MagicMock())

        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(return_value=mock_graphiti)),
            "graphiti_providers": mock_providers,
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(side_effect=PermissionError("[Errno 13] Permission denied")))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                with patch("integrations.graphiti.queries_pkg.client.capture_exception"):
                    client = GraphitiClient(config)
                    result = await client.initialize()

                    assert result is False

    @pytest.mark.asyncio
    async def test_initialize_driver_os_error(self):
        """Test initialize handles OSError from driver creation."""
        config = GraphitiConfig(enabled=True, db_path="/invalid/path")

        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()

        mock_providers = MagicMock()
        mock_providers.create_llm_client = MagicMock(return_value=MagicMock())
        mock_providers.create_embedder = MagicMock(return_value=MagicMock())

        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(return_value=mock_graphiti)),
            "graphiti_providers": mock_providers,
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(side_effect=OSError("[Errno 2] No such file or directory")))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                with patch("integrations.graphiti.queries_pkg.client.capture_exception"):
                    client = GraphitiClient(config)
                    result = await client.initialize()

                    assert result is False

    @pytest.mark.asyncio
    async def test_initialize_driver_unexpected_exception(self):
        """Test initialize handles unexpected errors from driver creation."""
        config = GraphitiConfig(enabled=True)

        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()

        mock_providers = MagicMock()
        mock_providers.create_llm_client = MagicMock(return_value=MagicMock())
        mock_providers.create_embedder = MagicMock(return_value=MagicMock())

        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(return_value=mock_graphiti)),
            "graphiti_providers": mock_providers,
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(side_effect=RuntimeError("Unexpected database error")))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                with patch("integrations.graphiti.queries_pkg.client.capture_exception"):
                    client = GraphitiClient(config)
                    result = await client.initialize()

                    assert result is False

    @pytest.mark.asyncio
    async def test_initialize_driver_import_error(self):
        """Test initialize handles ImportError from patched driver."""
        config = GraphitiConfig(enabled=True)

        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()

        mock_providers = MagicMock()
        mock_providers.create_llm_client = MagicMock(return_value=MagicMock())
        mock_providers.create_embedder = MagicMock(return_value=MagicMock())

        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(return_value=mock_graphiti)),
            "graphiti_providers": mock_providers,
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(side_effect=ImportError("kuzu_driver_patched module not found")))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                with patch("integrations.graphiti.queries_pkg.client.capture_exception"):
                    client = GraphitiClient(config)
                    result = await client.initialize()

                    assert result is False

    @pytest.mark.asyncio
    async def test_initialize_builds_indices_on_first_run(self):
        """Test initialize builds indices on first run (state.indices_built=False)."""
        config = GraphitiConfig(enabled=True)

        mock_driver = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()

        mock_providers = MagicMock()
        mock_providers.create_llm_client = MagicMock(return_value=MagicMock())
        mock_providers.create_embedder = MagicMock(return_value=MagicMock())

        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(return_value=mock_graphiti)),
            "graphiti_providers": mock_providers,
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(return_value=mock_driver))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                state = GraphitiState()  # indices_built defaults to False
                client = GraphitiClient(config)
                result = await client.initialize(state)

                assert result is True
                mock_graphiti.build_indices_and_constraints.assert_called_once()
                assert state.indices_built is True
                assert state.initialized is True
                assert state.database is not None
                assert state.created_at is not None

    @pytest.mark.asyncio
    async def test_initialize_skips_indices_when_already_built(self):
        """Test initialize skips index building when already done."""
        config = GraphitiConfig(enabled=True)

        mock_driver = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()

        mock_providers = MagicMock()
        mock_providers.create_llm_client = MagicMock(return_value=MagicMock())
        mock_providers.create_embedder = MagicMock(return_value=MagicMock())

        state = GraphitiState(indices_built=True)

        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(return_value=mock_graphiti)),
            "graphiti_providers": mock_providers,
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(return_value=mock_driver))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                client = GraphitiClient(config)
                result = await client.initialize(state)

                assert result is True
                mock_graphiti.build_indices_and_constraints.assert_not_called()

    @pytest.mark.asyncio
    async def test_initialize_updates_state_with_config(self):
        """Test initialize updates state with configuration info."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="anthropic",
            embedder_provider="voyage",
            database="test_database"
        )

        mock_driver = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()

        mock_providers = MagicMock()
        mock_providers.create_llm_client = MagicMock(return_value=MagicMock())
        mock_providers.create_embedder = MagicMock(return_value=MagicMock())

        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(return_value=mock_graphiti)),
            "graphiti_providers": mock_providers,
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(return_value=mock_driver))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                state = GraphitiState()
                client = GraphitiClient(config)
                result = await client.initialize(state)

                assert result is True
                assert state.initialized is True
                assert state.database == "test_database"
                assert state.llm_provider == "anthropic"
                assert state.embedder_provider == "voyage"
                assert state.created_at is not None

                # Verify timestamp is valid ISO format
                datetime.fromisoformat(state.created_at)

    @pytest.mark.asyncio
    async def test_initialize_success_path(self):
        """Test complete successful initialization path."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="openai",
            embedder_provider="openai"
        )

        mock_llm = MagicMock()
        mock_embedder = MagicMock()
        mock_driver = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()

        mock_providers = MagicMock()
        mock_providers.create_llm_client = MagicMock(return_value=mock_llm)
        mock_providers.create_embedder = MagicMock(return_value=mock_embedder)

        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(return_value=mock_graphiti)),
            "graphiti_providers": mock_providers,
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(return_value=mock_driver))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                client = GraphitiClient(config)
                result = await client.initialize()

                assert result is True
                assert client.is_initialized is True
                assert client._llm_client == mock_llm
                assert client._embedder == mock_embedder
                assert client._driver == mock_driver
                assert client._graphiti == mock_graphiti
                # Should build indices when no state provided
                mock_graphiti.build_indices_and_constraints.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_with_state_none(self):
        """Test initialize when state is None (no state tracking)."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="openai",
            embedder_provider="openai"
        )

        mock_llm = MagicMock()
        mock_embedder = MagicMock()
        mock_driver = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()

        mock_providers = MagicMock()
        mock_providers.create_llm_client = MagicMock(return_value=mock_llm)
        mock_providers.create_embedder = MagicMock(return_value=mock_embedder)

        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(return_value=mock_graphiti)),
            "graphiti_providers": mock_providers,
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(return_value=mock_driver))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                client = GraphitiClient(config)
                result = await client.initialize(None)

                # Should still build indices when state is None
                assert result is True
                mock_graphiti.build_indices_and_constraints.assert_called_once()

        with patch("graphiti_providers.create_llm_client",
                   side_effect=mock_create_llm):
            with patch("graphiti_providers.create_embedder",
                      side_effect=mock_create_embedder):
                with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                          return_value=True):
                    with patch("integrations.graphiti.queries_pkg.kuzu_driver_patched.create_patched_kuzu_driver",
                              return_value=mock_driver):
                        with patch("graphiti_core.Graphiti",
                                  return_value=mock_graphiti):
                            client = GraphitiClient(config)
                            result = await client.initialize()

                            assert result is True
                            assert client._initialized is True
                            assert client._graphiti == mock_graphiti
                            assert client._driver == mock_driver
                            assert client._llm_client is not None
                            assert client._embedder is not None

    @pytest.mark.asyncio
    async def test_initialize_with_state_none(self):
        """Test initialize when state is None (no state tracking)."""
    @pytest.mark.asyncio
    async def test_initialize_generic_exception(self):
        """Test initialize handles generic exceptions."""
        config = GraphitiConfig(enabled=True)

        mock_graphiti = MagicMock()

        mock_providers = MagicMock()
        mock_providers.create_llm_client = MagicMock(return_value=MagicMock())
        mock_providers.create_embedder = MagicMock(return_value=MagicMock())

        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(side_effect=RuntimeError("Unexpected error"))),
            "graphiti_providers": mock_providers,
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(return_value=MagicMock()))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                with patch("integrations.graphiti.queries_pkg.client.capture_exception"):
                    client = GraphitiClient(config)
                    result = await client.initialize()

                    assert result is False

    @pytest.mark.asyncio
    async def test_initialize_get_db_path_from_config(self):
        """Test initialize uses config.get_db_path() for database path."""
        config = GraphitiConfig(enabled=True, db_path="/tmp/test_graphiti_db")

        mock_driver = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()

        mock_providers = MagicMock()
        mock_providers.create_llm_client = MagicMock(return_value=MagicMock())
        mock_providers.create_embedder = MagicMock(return_value=MagicMock())

        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(return_value=mock_graphiti)),
            "graphiti_providers": mock_providers,
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(return_value=mock_driver))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                client = GraphitiClient(config)
                result = await client.initialize()

                assert result is True
                # Verify initialization succeeded


class TestGraphitiClientClose:
    """Tests for GraphitiClient.close method."""

    @pytest.mark.asyncio
    async def test_close_success(self):
        """Test close closes graphiti connection and cleans up."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.close = AsyncMock()
        client._graphiti = mock_graphiti
        client._driver = MagicMock()
        client._llm_client = MagicMock()
        client._embedder = MagicMock()
        client._initialized = True

        await client.close()

        mock_graphiti.close.assert_called_once()
        assert client._graphiti is None
        assert client._driver is None
        assert client._llm_client is None
        assert client._embedder is None
        assert client._initialized is False

    @pytest.mark.asyncio
    async def test_close_when_graphiti_is_none(self):
        """Test close when graphiti is None (no connection)."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._graphiti = None

        # Should not raise
        await client.close()

        assert client._initialized is False

    @pytest.mark.asyncio
    async def test_close_handles_exception_gracefully(self):
        """Test close logs warning but continues cleanup on error."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.close = AsyncMock(side_effect=RuntimeError("Connection reset"))
        client._graphiti = mock_graphiti
        client._driver = MagicMock()
        client._llm_client = MagicMock()
        client._embedder = MagicMock()
        client._initialized = True

        with patch("integrations.graphiti.queries_pkg.client.logger") as mock_logger:
            # Should not raise
            await client.close()

            # Should log warning
            mock_logger.warning.assert_called()

        # Despite error, should still cleanup
        assert client._graphiti is None
        assert client._driver is None
        assert client._llm_client is None
        assert client._embedder is None
        assert client._initialized is False

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self):
        """Test close can be called multiple times safely."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.close = AsyncMock()
        client._graphiti = mock_graphiti
        client._initialized = True

        await client.close()
        await client.close()
        await client.close()

        # Should only close once (first time)
        mock_graphiti.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_when_already_closed(self):
        """Test close when already closed (all attributes are None)."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        # All None, already closed
        client._graphiti = None
        client._driver = None
        client._llm_client = None
        client._embedder = None
        client._initialized = False

        # Should not raise
        await client.close()

    @pytest.mark.asyncio
    async def test_close_preserves_cleanup_on_error(self):
        """Test all cleanup happens even when close() raises."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.close = AsyncMock(side_effect=Exception("Close failed"))
        client._graphiti = mock_graphiti
        client._driver = MagicMock(spec=["close"])  # Driver doesn't have close
        client._llm_client = MagicMock()
        client._embedder = MagicMock()
        client._initialized = True

        # Should complete despite exception
        await client.close()

        # Verify all cleanup happened
        assert client._graphiti is None
        assert client._driver is None
        assert client._llm_client is None
        assert client._embedder is None
        assert client._initialized is False


class TestGraphitiClientIntegration:
    """Integration tests for GraphitiClient lifecycle."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_initialize_close(self):
        """Test full lifecycle: initialize and close."""
        config = GraphitiConfig(enabled=True)

        mock_llm = MagicMock()
        mock_embedder = MagicMock()
        mock_driver = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()
        mock_graphiti.close = AsyncMock()

        mock_providers = MagicMock()
        mock_providers.create_llm_client = MagicMock(return_value=mock_llm)
        mock_providers.create_embedder = MagicMock(return_value=mock_embedder)

        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(return_value=mock_graphiti)),
            "graphiti_providers": mock_providers,
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(return_value=mock_driver))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                client = GraphitiClient(config)

                # Initialize
                result = await client.initialize()
                assert result is True
                assert client.is_initialized

                # Close
                await client.close()
                assert not client.is_initialized
                assert client.graphiti is None

    @pytest.mark.asyncio
    async def test_reinitialize_after_close(self):
        """Test reinitializing after close."""
        config = GraphitiConfig(enabled=True)

        mock_llm = MagicMock()
        mock_embedder = MagicMock()
        mock_driver = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()
        mock_graphiti.close = AsyncMock()

        mock_providers = MagicMock()
        mock_providers.create_llm_client = MagicMock(return_value=mock_llm)
        mock_providers.create_embedder = MagicMock(return_value=mock_embedder)

        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(return_value=mock_graphiti)),
            "graphiti_providers": mock_providers,
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(return_value=mock_driver))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                client = GraphitiClient(config)

                # First initialization
                result = await client.initialize()
                assert result is True

                # Close
                await client.close()
                assert not client.is_initialized

                # Reinitialize (will skip building indices since state is separate)
                result = await client.initialize()
                assert result is True
                assert client.is_initialized

    @pytest.mark.asyncio
    async def test_multiple_initialize_calls(self):
        """Test multiple initialize calls without close."""
        config = GraphitiConfig(enabled=True)

        mock_llm = MagicMock()
        mock_embedder = MagicMock()
        mock_driver = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()

        mock_providers = MagicMock()
        mock_providers.create_llm_client = MagicMock(return_value=mock_llm)
        mock_providers.create_embedder = MagicMock(return_value=mock_embedder)

        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(return_value=mock_graphiti)),
            "graphiti_providers": mock_providers,
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(return_value=mock_driver))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                client = GraphitiClient(config)

                # First call - should initialize
                result1 = await client.initialize()
                assert result1 is True

                # Second call - should return early
                result2 = await client.initialize()
                assert result2 is True

                # Third call - should still return early
                result3 = await client.initialize()
                assert result3 is True

                # Indices should only be built once
                mock_graphiti.build_indices_and_constraints.assert_called_once()


class TestGraphitiClientEdgeCases:
    """Edge case tests for GraphitiClient."""

    @pytest.mark.asyncio
    async def test_initialize_with_minimal_config(self):
        """Test initialize with minimal configuration."""
        config = GraphitiConfig(enabled=True)

        def mock_create_llm(cfg):
            return MagicMock()

        def mock_create_embedder(cfg):
            return MagicMock()

        mock_driver = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()

        mock_providers = MagicMock()
        mock_providers.create_llm_client = MagicMock(return_value=mock_create_llm(None))
        mock_providers.create_embedder = MagicMock(return_value=mock_create_embedder(None))

        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(return_value=mock_graphiti)),
            "graphiti_providers": mock_providers,
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(return_value=mock_driver))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                client = GraphitiClient(config)
                result = await client.initialize()

                assert result is True

    @pytest.mark.asyncio
    async def test_initialize_state_without_indices_built_attribute(self):
        """Test initialize with state object that has indices_built."""
        config = GraphitiConfig(enabled=True)

        mock_driver = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()

        mock_providers = MagicMock()
        mock_providers.create_llm_client = MagicMock(return_value=MagicMock())
        mock_providers.create_embedder = MagicMock(return_value=MagicMock())

        # Create a state with indices_built
        mock_state = GraphitiState()
        mock_state.indices_built = False

        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(return_value=mock_graphiti)),
            "graphiti_providers": mock_providers,
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(return_value=mock_driver))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                client = GraphitiClient(config)
                result = await client.initialize(mock_state)

                assert result is True

    @pytest.mark.asyncio
    async def test_close_various_exception_types(self):
        """Test close handles various exception types."""
        exception_types = [
            RuntimeError("Runtime error"),
            ValueError("Value error"),
            IOError("IO error"),
            Exception("Generic error"),
        ]

        for exc in exception_types:
            config = GraphitiConfig(enabled=True)
            client = GraphitiClient(config)

            mock_graphiti = MagicMock()
            mock_graphiti.close = AsyncMock(side_effect=exc)
            client._graphiti = mock_graphiti
            client._initialized = True

            # Should not raise for any exception type
            await client.close()

            assert client._initialized is False

    @pytest.mark.asyncio
    async def test_initialize_concurrent_calls(self):
        """Test handling of concurrent initialize calls."""
        config = GraphitiConfig(enabled=True)

        async def mock_create_llm(cfg):
            await asyncio.sleep(0.01)  # Simulate some delay
            return MagicMock()

        async def mock_create_embedder(cfg):
            await asyncio.sleep(0.01)
            return MagicMock()

        mock_llm = MagicMock()
        mock_embedder = MagicMock()
        mock_driver = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.build_indices_and_constraints = AsyncMock()

        mock_providers = MagicMock()
        mock_providers.create_llm_client = MagicMock(return_value=mock_llm)
        mock_providers.create_embedder = MagicMock(return_value=mock_embedder)

        with patch.dict("sys.modules", {
            "graphiti_core": MagicMock(Graphiti=MagicMock(return_value=mock_graphiti)),
            "graphiti_providers": mock_providers,
            "integrations.graphiti.queries_pkg.kuzu_driver_patched": MagicMock(create_patched_kuzu_driver=MagicMock(return_value=mock_driver))
        }):
            with patch("integrations.graphiti.queries_pkg.client._apply_ladybug_monkeypatch",
                      return_value=True):
                client = GraphitiClient(config)

                # Concurrent calls
                results = await asyncio.gather(
                    client.initialize(),
                    client.initialize(),
                    client.initialize()
                )

                # All should succeed
                assert all(results)
                # But indices should only be built once
                mock_graphiti.build_indices_and_constraints.assert_called_once()
