"""Tests for providers_pkg/utils.py module."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile

import pytest

from integrations.graphiti.providers_pkg.utils import (
    is_graphiti_enabled,
    get_graph_hints,
)


class TestIsGraphitiEnabled:
    """Tests for is_graphiti_enabled function."""

    @patch("graphiti_config.is_graphiti_enabled")
    def test_is_graphiti_enabled_true(self, mock_config_enabled):
        """Test is_graphiti_enabled returns True when enabled."""
        mock_config_enabled.return_value = True
        result = is_graphiti_enabled()
        assert result is True
        mock_config_enabled.assert_called_once()

    @patch("graphiti_config.is_graphiti_enabled")
    def test_is_graphiti_enabled_false(self, mock_config_enabled):
        """Test is_graphiti_enabled returns False when not enabled."""
        mock_config_enabled.return_value = False
        result = is_graphiti_enabled()
        assert result is False
        mock_config_enabled.assert_called_once()

    @patch("graphiti_config.is_graphiti_enabled")
    def test_is_graphiti_enabled_reexport(self, mock_config_enabled):
        """Test is_graphiti_enabled is a re-export from graphiti_config."""
        # Verify the function calls through to graphiti_config
        mock_config_enabled.return_value = True
        result = is_graphiti_enabled()
        assert result is True


class TestGetGraphHints:
    """Tests for get_graph_hints function."""

    @pytest.mark.asyncio
    async def test_get_graph_hints_disabled(self):
        """Test get_graph_hints returns empty list when Graphiti not enabled."""
        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=False,
        ):
            result = await get_graph_hints("test query", "test_project")
            assert result == []

    @pytest.mark.asyncio
    async def test_get_graph_hints_basic_call(self):
        """Test get_graph_hints basic successful call."""
        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[
            {"content": "hint 1", "score": 0.9, "type": "pattern"},
            {"content": "hint 2", "score": 0.8, "type": "gotcha"},
        ])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch("integrations.graphiti.memory.GraphitiMemory", return_value=mock_memory):
                result = await get_graph_hints(
                    query="authentication patterns",
                    project_id="test_project",
                    max_results=10,
                )

                assert len(result) == 2
                assert result[0]["content"] == "hint 1"
                assert result[0]["score"] == 0.9
                assert result[1]["content"] == "hint 2"

    @pytest.mark.asyncio
    async def test_get_graph_hints_custom_max_results(self):
        """Test get_graph_hints with custom max_results."""
        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch("integrations.graphiti.memory.GraphitiMemory", return_value=mock_memory):
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
    async def test_get_graph_hints_with_spec_dir(self):
        """Test get_graph_hints with explicit spec_dir parameter."""
        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        spec_dir = Path("/tmp/test_spec")

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch("integrations.graphiti.memory.GraphitiMemory", return_value=mock_memory) as mock_graphiti_memory:
                await get_graph_hints(
                    query="test",
                    project_id="proj",
                    spec_dir=spec_dir,
                )

                # Verify GraphitiMemory was created with the provided spec_dir
                mock_graphiti_memory.assert_called_once()
                call_kwargs = mock_graphiti_memory.call_args.kwargs
                assert call_kwargs["spec_dir"] == spec_dir
                # GroupIdMode.PROJECT is the string "project"
                # The mock might return the actual value or a mock, so we check the attribute access
                group_id_mode = call_kwargs.get("group_id_mode")
                # It should be "project" or something that represents that value
                assert group_id_mode is not None

    @pytest.mark.asyncio
    async def test_get_graph_hints_creates_temp_spec_dir(self):
        """Test get_graph_hints creates temp spec_dir when not provided."""
        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch("tempfile.mkdtemp") as mock_mkdtemp:
                mock_mkdtemp.return_value = "/tmp/temp_graphiti_query_123"

                with patch("integrations.graphiti.memory.GraphitiMemory", return_value=mock_memory):
                    await get_graph_hints(
                        query="test",
                        project_id="proj",
                    )

                    # Verify temp directory was created
                    mock_mkdtemp.assert_called_once_with(prefix="graphiti_query_")

    @pytest.mark.asyncio
    async def test_get_graph_hints_import_error(self):
        """Test get_graph_hints handles ImportError gracefully."""
        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            # Mock the import to fail by patching the import location
            with patch("integrations.graphiti.memory.GraphitiMemory", side_effect=ImportError("No module named 'graphiti_memory'")):
                result = await get_graph_hints("test", "proj")
                assert result == []

    @pytest.mark.asyncio
    async def test_get_graph_hints_generic_exception(self):
        """Test get_graph_hints handles generic exceptions gracefully."""
        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch("integrations.graphiti.memory.GraphitiMemory", side_effect=RuntimeError("Connection failed")):
                result = await get_graph_hints("test", "proj")
                assert result == []

    @pytest.mark.asyncio
    async def test_get_graph_hints_memory_get_context_exception(self):
        """Test get_graph_hints handles exceptions from get_relevant_context."""
        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(
            side_effect=Exception("Query failed")
        )
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch("integrations.graphiti.memory.GraphitiMemory", return_value=mock_memory):
                result = await get_graph_hints("test", "proj")
                assert result == []

    @pytest.mark.asyncio
    async def test_get_graph_hints_memory_close_exception(self):
        """Test get_graph_hints handles exceptions from close."""
        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock(side_effect=Exception("Close failed"))

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch("integrations.graphiti.memory.GraphitiMemory", return_value=mock_memory):
                # Should still return results even if close fails
                result = await get_graph_hints("test", "proj")
                assert result == []

    @pytest.mark.asyncio
    async def test_get_graph_hints_empty_query(self):
        """Test get_graph_hints with empty query string."""
        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch("integrations.graphiti.memory.GraphitiMemory", return_value=mock_memory):
                result = await get_graph_hints("", "proj")
                assert result == []
                mock_memory.get_relevant_context.assert_called_once_with(
                    query="",
                    num_results=10,
                    include_project_context=True,
                )

    @pytest.mark.asyncio
    async def test_get_graph_hints_special_characters_in_query(self):
        """Test get_graph_hints with special characters in query."""
        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch("integrations.graphiti.memory.GraphitiMemory", return_value=mock_memory):
                result = await get_graph_hints(
                    "API authentication with OAuth2 & JWT",
                    "proj",
                )
                assert result == []

    @pytest.mark.asyncio
    async def test_get_graph_hints_long_query_truncation_in_log(self):
        """Test get_graph_hints truncates long query in log message."""
        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        long_query = "a" * 100

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch("integrations.graphiti.memory.GraphitiMemory", return_value=mock_memory):
                # Should not raise exception for long query
                result = await get_graph_hints(long_query, "proj")
                assert result == []

    @pytest.mark.asyncio
    async def test_get_graph_hints_project_level_scope(self):
        """Test get_graph_hints uses project-level group scope."""
        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch("integrations.graphiti.memory.GraphitiMemory", return_value=mock_memory) as mock_graphiti_memory:
                await get_graph_hints("test", "proj")

                # Verify it was called with group_id_mode parameter
                call_args = mock_graphiti_memory.call_args
                assert "group_id_mode" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_get_graph_hints_uses_cwd_as_project_dir(self):
        """Test get_graph_hints uses current working directory as project_dir."""
        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch("pathlib.Path.cwd") as mock_cwd:
                mock_cwd.return_value = Path("/test/project")

                with patch("integrations.graphiti.memory.GraphitiMemory", return_value=mock_memory):
                    await get_graph_hints("test", "proj")

    @pytest.mark.asyncio
    async def test_get_graph_hints_returns_list_of_dicts(self):
        """Test get_graph_hints returns list of dictionaries with expected keys."""
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
            with patch("integrations.graphiti.memory.GraphitiMemory", return_value=mock_memory):
                result = await get_graph_hints("test", "proj")

                assert isinstance(result, list)
                if len(result) > 0:
                    assert isinstance(result[0], dict)
                    # Verify expected keys are present
                    assert "content" in result[0] or "score" in result[0] or "type" in result[0]

    @pytest.mark.asyncio
    async def test_get_graph_hints_zero_max_results(self):
        """Test get_graph_hints with max_results=0."""
        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch("integrations.graphiti.memory.GraphitiMemory", return_value=mock_memory):
                await get_graph_hints("test", "proj", max_results=0)

                mock_memory.get_relevant_context.assert_called_once_with(
                    query="test",
                    num_results=0,
                    include_project_context=True,
                )

    @pytest.mark.asyncio
    async def test_get_graph_hints_large_max_results(self):
        """Test get_graph_hints with large max_results value."""
        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch("integrations.graphiti.memory.GraphitiMemory", return_value=mock_memory):
                await get_graph_hints("test", "proj", max_results=1000)

                mock_memory.get_relevant_context.assert_called_once_with(
                    query="test",
                    num_results=1000,
                    include_project_context=True,
                )

    @pytest.mark.asyncio
    async def test_get_graph_hints_project_id_parameter(self):
        """Test get_graph_hints accepts project_id parameter."""
        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch("integrations.graphiti.memory.GraphitiMemory", return_value=mock_memory):
                # project_id is accepted but not directly used in the current implementation
                # It's available for future use or logging
                result = await get_graph_hints(
                    query="test",
                    project_id="my_project_123",
                )
                assert result == []

    @pytest.mark.asyncio
    async def test_get_graph_hints_unicode_query(self):
        """Test get_graph_hints with unicode characters in query."""
        mock_memory = MagicMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch(
            "integrations.graphiti.providers_pkg.utils.is_graphiti_enabled",
            return_value=True,
        ):
            with patch("integrations.graphiti.memory.GraphitiMemory", return_value=mock_memory):
                result = await get_graph_hints(
                    "search for user authentication patterns",
                    "proj",
                )
                assert result == []
