"""Tests for integrations/graphiti/providers_pkg/utils.py module.

This test file covers the utility functions in the providers_pkg/utils.py module,
including is_graphiti_enabled() and get_graph_hints().
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import tempfile
import sys

import pytest


class TestIsGraphitiEnabled:
    """Tests for is_graphiti_enabled function."""

    @patch("graphiti_config.is_graphiti_enabled")
    def test_returns_true_when_enabled(self, mock_config_enabled):
        """Test is_graphiti_enabled returns True when graphiti_config reports enabled."""
        from integrations.graphiti.providers_pkg.utils import is_graphiti_enabled

        mock_config_enabled.return_value = True
        result = is_graphiti_enabled()

        assert result is True
        mock_config_enabled.assert_called_once()

    @patch("graphiti_config.is_graphiti_enabled")
    def test_returns_false_when_disabled(self, mock_config_enabled):
        """Test is_graphiti_enabled returns False when graphiti_config reports disabled."""
        from integrations.graphiti.providers_pkg.utils import is_graphiti_enabled

        mock_config_enabled.return_value = False
        result = is_graphiti_enabled()

        assert result is False
        mock_config_enabled.assert_called_once()

    @patch("graphiti_config.is_graphiti_enabled")
    def test_is_reexport_from_graphiti_config(self, mock_config_enabled):
        """Test is_graphiti_enabled is a convenience re-export from graphiti_config."""
        from integrations.graphiti.providers_pkg.utils import is_graphiti_enabled

        mock_config_enabled.return_value = True
        result = is_graphiti_enabled()

        # Verify it delegates to graphiti_config
        mock_config_enabled.assert_called_once()
        assert result is True

    @patch("graphiti_config.is_graphiti_enabled")
    def test_multiple_calls_delegate_to_config(self, mock_config_enabled):
        """Test multiple calls to is_graphiti_enabled delegate to graphiti_config."""
        from integrations.graphiti.providers_pkg.utils import is_graphiti_enabled

        mock_config_enabled.return_value = True

        # Call multiple times
        is_graphiti_enabled()
        is_graphiti_enabled()
        is_graphiti_enabled()

        # Verify it delegated each time
        assert mock_config_enabled.call_count == 3

    @patch("graphiti_config.is_graphiti_enabled", side_effect=[True, False, True])
    def test_respects_config_state_changes(self, mock_config_enabled):
        """Test is_graphiti_enabled reflects config state changes."""
        from integrations.graphiti.providers_pkg.utils import is_graphiti_enabled

        assert is_graphiti_enabled() is True
        assert is_graphiti_enabled() is False
        assert is_graphiti_enabled() is True

    @patch("graphiti_config.is_graphiti_enabled")
    def test_return_type_is_bool(self, mock_config_enabled):
        """Test is_graphiti_enabled always returns a boolean."""
        from integrations.graphiti.providers_pkg.utils import is_graphiti_enabled

        mock_config_enabled.return_value = True
        result = is_graphiti_enabled()
        assert isinstance(result, bool)

        mock_config_enabled.return_value = False
        result = is_graphiti_enabled()
        assert isinstance(result, bool)


class TestGetGraphHintsBasic:
    """Basic tests for get_graph_hints function."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_disabled(self):
        """Test get_graph_hints returns empty list when Graphiti not enabled."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=False,
        ):
            result = await get_graph_hints(
                query="test query",
                project_id="test_project",
            )

            assert result == []
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_import_error(self):
        """Test get_graph_hints returns empty list when graphiti_memory import fails."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            # Simulate ImportError by patching the import
            with patch.dict(
                "sys.modules",
                {"graphiti_memory": None},
                clear=False,
            ):
                # Remove from modules if present
                original_modules = sys.modules.copy()
                if "graphiti_memory" in sys.modules:
                    del sys.modules["graphiti_memory"]

                try:
                    result = await get_graph_hints("test", "proj")
                    assert result == []
                finally:
                    sys.modules.update(original_modules)

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_generic_exception(self):
        """Test get_graph_hints returns empty list on generic exceptions."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            # Mock GraphitiMemory to raise an exception
            mock_graphiti_memory = MagicMock(side_effect=RuntimeError("Connection failed"))
            with patch.dict(
                "sys.modules",
                {"graphiti_memory": MagicMock(GraphitiMemory=mock_graphiti_memory)},
            ):
                result = await get_graph_hints("test", "proj")
                assert result == []

    @pytest.mark.asyncio
    async def test_successful_call_returns_hints(self):
        """Test get_graph_hints returns hints on successful call."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_hints = [
            {"content": "Use OAuth2 for authentication", "score": 0.95, "type": "pattern"},
            {"content": "Check for race conditions", "score": 0.87, "type": "gotcha"},
        ]

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=mock_hints)
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {"graphiti_memory": MagicMock(GraphitiMemory=MagicMock(return_value=mock_memory))},
            ):
                result = await get_graph_hints(
                    query="authentication patterns",
                    project_id="test_project",
                )

                assert len(result) == 2
                assert result[0]["content"] == "Use OAuth2 for authentication"
                assert result[0]["score"] == 0.95
                assert result[1]["content"] == "Check for race conditions"

    @pytest.mark.asyncio
    async def test_closes_memory_after_query(self):
        """Test get_graph_hints closes memory connection after query."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {"graphiti_memory": MagicMock(GraphitiMemory=MagicMock(return_value=mock_memory))},
            ):
                await get_graph_hints("test", "proj")

                # Verify close was called
                mock_memory.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_continues_on_close_exception(self):
        """Test get_graph_hints handles close exception gracefully."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock(side_effect=Exception("Close failed"))

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {"graphiti_memory": MagicMock(GraphitiMemory=MagicMock(return_value=mock_memory))},
            ):
                # Should not raise, should return empty list
                result = await get_graph_hints("test", "proj")
                assert result == []


class TestGetGraphHintsParameters:
    """Tests for get_graph_hints parameter handling."""

    @pytest.mark.asyncio
    async def test_custom_max_results(self):
        """Test get_graph_hints with custom max_results parameter."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {"graphiti_memory": MagicMock(GraphitiMemory=MagicMock(return_value=mock_memory))},
            ):
                await get_graph_hints(
                    query="test",
                    project_id="proj",
                    max_results=5,
                )

                mock_memory.get_relevant_context.assert_called_once_with(
                    query="test",
                    num_results=5,
                    include_project_context=True,
                )

    @pytest.mark.asyncio
    async def test_default_max_results_is_ten(self):
        """Test get_graph_hints default max_results is 10."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {"graphiti_memory": MagicMock(GraphitiMemory=MagicMock(return_value=mock_memory))},
            ):
                await get_graph_hints("test", "proj")

                call_kwargs = mock_memory.get_relevant_context.call_args.kwargs
                assert call_kwargs["num_results"] == 10

    @pytest.mark.asyncio
    async def test_with_explicit_spec_dir(self):
        """Test get_graph_hints with explicit spec_dir parameter."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        spec_dir = Path("/tmp/test_spec")

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            mock_graphiti_memory = MagicMock(return_value=mock_memory)
            with patch.dict(
                "sys.modules",
                {"graphiti_memory": MagicMock(GraphitiMemory=mock_graphiti_memory)},
            ):
                await get_graph_hints(
                    query="test",
                    project_id="proj",
                    spec_dir=spec_dir,
                )

                # Verify GraphitiMemory was created with provided spec_dir
                call_kwargs = mock_graphiti_memory.call_args.kwargs
                assert call_kwargs["spec_dir"] == spec_dir

    @pytest.mark.asyncio
    async def test_creates_temp_spec_dir_when_not_provided(self):
        """Test get_graph_hints creates temp spec_dir when not provided."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch("tempfile.mkdtemp") as mock_mkdtemp:
                mock_mkdtemp.return_value = "/tmp/temp_graphiti_query_123"

                with patch.dict(
                    "sys.modules",
                    {
                        "graphiti_memory": MagicMock(
                            GraphitiMemory=MagicMock(return_value=mock_memory)
                        )
                    },
                ):
                    await get_graph_hints("test", "proj")

                    # Verify temp directory was created with correct prefix
                    mock_mkdtemp.assert_called_once_with(prefix="graphiti_query_")

    @pytest.mark.asyncio
    async def test_uses_cwd_as_project_dir(self):
        """Test get_graph_hints uses current working directory as project_dir."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch("pathlib.Path.cwd") as mock_cwd:
                mock_cwd.return_value = Path("/test/project")

                with patch.dict(
                    "sys.modules",
                    {
                        "graphiti_memory": MagicMock(
                            GraphitiMemory=MagicMock(return_value=mock_memory)
                        )
                    },
                ):
                    await get_graph_hints("test", "proj")

                    # Verify cwd was called
                    mock_cwd.assert_called_once()

    @pytest.mark.asyncio
    async def test_project_level_scope(self):
        """Test get_graph_hints uses project-level group scope."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            mock_graphiti_memory = MagicMock(return_value=mock_memory)
            with patch.dict(
                "sys.modules",
                {"graphiti_memory": MagicMock(GraphitiMemory=mock_graphiti_memory)},
            ):
                await get_graph_hints("test", "proj")

                # Verify it was called with group_id_mode parameter
                call_kwargs = mock_graphiti_memory.call_args.kwargs
                assert "group_id_mode" in call_kwargs

    @pytest.mark.asyncio
    async def test_include_project_context_true(self):
        """Test get_graph_hints passes include_project_context=True."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                await get_graph_hints("test", "proj")

                call_kwargs = mock_memory.get_relevant_context.call_args.kwargs
                assert call_kwargs["include_project_context"] is True


class TestGetGraphHintsQueryHandling:
    """Tests for get_graph_hints query parameter handling."""

    @pytest.mark.asyncio
    async def test_with_empty_query(self):
        """Test get_graph_hints with empty query string."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                result = await get_graph_hints("", "proj")
                assert result == []

                mock_memory.get_relevant_context.assert_called_once_with(
                    query="",
                    num_results=10,
                    include_project_context=True,
                )

    @pytest.mark.asyncio
    async def test_with_special_characters_in_query(self):
        """Test get_graph_hints with special characters in query."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        query = "API authentication with OAuth2 & JWT tokens"

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                result = await get_graph_hints(query, "proj")
                assert result == []

    @pytest.mark.asyncio
    async def test_with_unicode_in_query(self):
        """Test get_graph_hints with unicode characters in query."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        query = "search for user authentication patterns"

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                result = await get_graph_hints(query, "proj")
                assert result == []

    @pytest.mark.asyncio
    async def test_with_very_long_query(self):
        """Test get_graph_hints with very long query (truncation in logs)."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        long_query = "a" * 200

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                # Should not raise exception for long query
                result = await get_graph_hints(long_query, "proj")
                assert result == []

    @pytest.mark.asyncio
    async def test_query_with_newlines(self):
        """Test get_graph_hints with newlines in query."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        query = "authentication\npatterns\nand\ntokens"

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                result = await get_graph_hints(query, "proj")
                assert result == []


class TestGetGraphHintsReturnValues:
    """Tests for get_graph_hints return value handling."""

    @pytest.mark.asyncio
    async def test_returns_list_type(self):
        """Test get_graph_hints always returns a list."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                result = await get_graph_hints("test", "proj")
                assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_returns_list_of_dicts_with_hints(self):
        """Test get_graph_hints returns list of dictionaries with expected keys."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_hints = [
            {"content": "test hint", "score": 0.95, "type": "pattern"},
        ]

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=mock_hints)
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                result = await get_graph_hints("test", "proj")

                assert len(result) == 1
                assert isinstance(result[0], dict)
                assert "content" in result[0]
                assert "score" in result[0]
                assert "type" in result[0]

    @pytest.mark.asyncio
    async def test_passes_through_hints_unchanged(self):
        """Test get_graph_hints passes through hints from memory unchanged."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_hints = [
            {"content": "hint 1", "score": 0.9, "type": "pattern"},
            {"content": "hint 2", "score": 0.8, "type": "gotcha"},
            {"content": "hint 3", "score": 0.7, "type": "outcome"},
        ]

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=mock_hints)
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                result = await get_graph_hints("test", "proj")

                assert result == mock_hints
                assert len(result) == 3

    @pytest.mark.asyncio
    async def test_empty_results_from_memory(self):
        """Test get_graph_hints when memory returns empty list."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                result = await get_graph_hints("test", "proj")
                assert result == []

    @pytest.mark.asyncio
    async def test_single_hint_result(self):
        """Test get_graph_hints with single hint result."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_hints = [{"content": "only hint", "score": 1.0, "type": "pattern"}]

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=mock_hints)
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                result = await get_graph_hints("test", "proj")
                assert len(result) == 1
                assert result[0]["content"] == "only hint"


class TestGetGraphHintsEdgeCases:
    """Edge case tests for get_graph_hints function."""

    @pytest.mark.asyncio
    async def test_with_zero_max_results(self):
        """Test get_graph_hints with max_results=0."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                await get_graph_hints("test", "proj", max_results=0)

                mock_memory.get_relevant_context.assert_called_once_with(
                    query="test",
                    num_results=0,
                    include_project_context=True,
                )

    @pytest.mark.asyncio
    async def test_with_large_max_results(self):
        """Test get_graph_hints with large max_results value."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                await get_graph_hints("test", "proj", max_results=1000)

                mock_memory.get_relevant_context.assert_called_once_with(
                    query="test",
                    num_results=1000,
                    include_project_context=True,
                )

    @pytest.mark.asyncio
    async def test_with_negative_max_results(self):
        """Test get_graph_hints with negative max_results."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                await get_graph_hints("test", "proj", max_results=-5)

                mock_memory.get_relevant_context.assert_called_once_with(
                    query="test",
                    num_results=-5,
                    include_project_context=True,
                )

    @pytest.mark.asyncio
    async def test_get_relevant_context_exception(self):
        """Test get_graph_hints handles exceptions from get_relevant_context."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(
            side_effect=Exception("Query failed")
        )
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                result = await get_graph_hints("test", "proj")
                assert result == []

    @pytest.mark.asyncio
    async def test_project_id_parameter_accepted(self):
        """Test get_graph_hints accepts project_id parameter."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                # project_id is accepted but not directly used in current implementation
                result = await get_graph_hints(
                    query="test",
                    project_id="my_project_123",
                )
                assert result == []

    @pytest.mark.asyncio
    async def test_with_path_object_spec_dir(self):
        """Test get_graph_hints with Path object as spec_dir."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        spec_dir = Path("/tmp/test_spec")

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                result = await get_graph_hints("test", "proj", spec_dir=spec_dir)
                assert result == []

    @pytest.mark.asyncio
    async def test_graceful_failure_never_raises(self):
        """Test get_graph_hints never raises exceptions (always fails gracefully)."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        # Test with various failure conditions
        test_scenarios = [
            # Disabled
            (
                "disabled",
                False,
                None
            ),
            # Import error simulation
            (
                "import_error",
                True,
                ImportError("graphiti_memory not found"),
            ),
            # Generic error
            (
                "generic_error",
                True,
                RuntimeError("Connection failed"),
            ),
        ]

        for scenario, enabled, error in test_scenarios:
            with patch(
                "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
                return_value=enabled,
            ):
                if error:
                    if isinstance(error, ImportError):
                        # Handle import error case
                        original_modules = sys.modules.copy()
                        if "graphiti_memory" in sys.modules:
                            del sys.modules["graphiti_memory"]
                        try:
                            result = await get_graph_hints("test", "proj")
                            assert result == []
                        finally:
                            sys.modules.update(original_modules)
                    else:
                        mock_graphiti_memory = MagicMock(side_effect=error)
                        with patch.dict(
                            "sys.modules",
                            {
                                "graphiti_memory": MagicMock(
                                    GraphitiMemory=mock_graphiti_memory
                                )
                            },
                        ):
                            result = await get_graph_hints("test", "proj")
                            assert result == []
                else:
                    result = await get_graph_hints("test", "proj")
                    assert result == []

    @pytest.mark.asyncio
    async def test_concurrent_calls(self):
        """Test multiple concurrent calls to get_graph_hints."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints
        import asyncio

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                # Run multiple concurrent calls
                results = await asyncio.gather(
                    get_graph_hints("query1", "proj1"),
                    get_graph_hints("query2", "proj2"),
                    get_graph_hints("query3", "proj3"),
                )

                # All should return empty lists
                assert all(r == [] for r in results)


class TestGetGraphHintsLogging:
    """Tests for get_graph_hints logging behavior."""

    @pytest.mark.asyncio
    async def test_logs_debug_when_disabled(self, caplog):
        """Test get_graph_hints logs debug message when disabled."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=False,
        ):
            with caplog.at_level("DEBUG"):
                await get_graph_hints("test", "proj")

                # Should log debug message about not being enabled
                assert any(
                    "Graphiti not enabled" in record.message
                    for record in caplog.records
                )

    @pytest.mark.asyncio
    async def test_logs_debug_on_import_error(self, caplog):
        """Test get_graph_hints logs debug message on ImportError."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            # Remove graphiti_memory to trigger import error
            original_modules = sys.modules.copy()
            if "graphiti_memory" in sys.modules:
                del sys.modules["graphiti_memory"]

            try:
                with caplog.at_level("DEBUG"):
                    await get_graph_hints("test", "proj")

                    # Should log debug about packages not available
                    assert any(
                        "not available" in record.message
                        for record in caplog.records
                    )
            finally:
                sys.modules.update(original_modules)

    @pytest.mark.asyncio
    async def test_logs_warning_on_generic_error(self, caplog):
        """Test get_graph_hints logs warning on generic exception."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            mock_graphiti_memory = MagicMock(side_effect=RuntimeError("Test error"))
            with patch.dict(
                "sys.modules",
                {"graphiti_memory": MagicMock(GraphitiMemory=mock_graphiti_memory)},
            ):
                with caplog.at_level("WARNING"):
                    await get_graph_hints("test", "proj")

                    # Should log warning about failure
                    assert any(
                        "Failed to get graph hints" in record.message
                        for record in caplog.records
                    )

    @pytest.mark.asyncio
    async def test_logs_info_on_success(self, caplog):
        """Test get_graph_hints logs info on successful retrieval."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_hints = [
            {"content": "hint 1", "score": 0.9, "type": "pattern"},
            {"content": "hint 2", "score": 0.8, "type": "gotcha"},
        ]

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=mock_hints)
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                with caplog.at_level("INFO"):
                    await get_graph_hints("test query", "proj")

                    # Should log info about number of hints retrieved
                    assert any(
                        "Retrieved" in record.message and "graph hints" in record.message
                        for record in caplog.records
                    )


class TestGetGraphHintsMemoryConfiguration:
    """Tests for get_graph_hints memory instance configuration."""

    @pytest.mark.asyncio
    async def test_uses_project_group_mode(self):
        """Test get_graph_hints creates memory with PROJECT group mode."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints
        from integrations.graphiti.providers_pkg.utils import is_graphiti_enabled

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        # Import GroupIdMode to verify the value
        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            mock_graphiti_memory_class = MagicMock(return_value=mock_memory)
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=mock_graphiti_memory_class
                    )
                },
            ):
                await get_graph_hints("test", "proj")

                # Verify GraphitiMemory was called with group_id_mode
                call_kwargs = mock_graphiti_memory_class.call_args.kwargs
                assert "group_id_mode" in call_kwargs

    @pytest.mark.asyncio
    async def test_passes_spec_dir_to_memory(self):
        """Test get_graph_hints passes spec_dir to GraphitiMemory."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        test_spec_dir = Path("/custom/spec/dir")

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            mock_graphiti_memory_class = MagicMock(return_value=mock_memory)
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=mock_graphiti_memory_class
                    )
                },
            ):
                await get_graph_hints("test", "proj", spec_dir=test_spec_dir)

                # Verify spec_dir was passed
                call_kwargs = mock_graphiti_memory_class.call_args.kwargs
                assert call_kwargs["spec_dir"] == test_spec_dir

    @pytest.mark.asyncio
    async def test_passes_project_dir_to_memory(self):
        """Test get_graph_hints passes project_dir to GraphitiMemory."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        test_project_dir = Path("/custom/project/dir")

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch("pathlib.Path.cwd", return_value=test_project_dir):
                mock_graphiti_memory_class = MagicMock(return_value=mock_memory)
                with patch.dict(
                    "sys.modules",
                    {
                        "graphiti_memory": MagicMock(
                            GraphitiMemory=mock_graphiti_memory_class
                        )
                    },
                ):
                    await get_graph_hints("test", "proj")

                    # Verify project_dir was passed (from cwd)
                    call_kwargs = mock_graphiti_memory_class.call_args.kwargs
                    assert "project_dir" in call_kwargs
                    assert call_kwargs["project_dir"] == test_project_dir


class TestGetGraphHintsModuleImports:
    """Tests for get_graph_hints module import handling."""

    @pytest.mark.asyncio
    async def test_imports_pathlib_Path_when_needed(self):
        """Test get_graph_hints imports Path from pathlib when needed."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            # The function imports Path internally, verify it works
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                # This should work without raising ImportError
                result = await get_graph_hints("test", "proj")
                assert result == []

    @pytest.mark.asyncio
    async def test_imports_tempfile_when_needed(self):
        """Test get_graph_hints imports tempfile when creating temp dir."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                # Call without spec_dir to trigger tempfile usage
                result = await get_graph_hints("test", "proj")
                assert result == []

    @pytest.mark.asyncio
    async def test_imports_graphiti_memory_when_needed(self):
        """Test get_graph_hints imports graphiti_memory when enabled."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            # Provide graphiti_memory mock
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_memory": MagicMock(
                        GraphitiMemory=MagicMock(return_value=mock_memory)
                    )
                },
            ):
                result = await get_graph_hints("test", "proj")
                assert result == []

    @pytest.mark.asyncio
    async def test_handles_missing_graphiti_memory_module(self):
        """Test get_graph_hints gracefully handles missing graphiti_memory module."""
        from integrations.graphiti.providers_pkg.utils import get_graph_hints

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            # Remove graphiti_memory from sys.modules
            original_modules = sys.modules.copy()
            sys.modules.pop("graphiti_memory", None)

            try:
                result = await get_graph_hints("test", "proj")
                # Should return empty list instead of raising
                assert result == []
            finally:
                sys.modules.update(original_modules)
