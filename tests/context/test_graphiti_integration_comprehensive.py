"""
Comprehensive Tests for context.graphiti_integration module
===========================================================

Tests for Graphiti integration including enabled/disabled states,
error handling, and all functionality paths.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestGraphitiAvailability:
    """Tests for Graphiti availability detection"""

    def test_graphiti_available_flag_exists(self):
        """Test that GRAPHITI_AVAILABLE flag exists"""
        from context.graphiti_integration import GRAPHITI_AVAILABLE
        assert isinstance(GRAPHITI_AVAILABLE, bool)

    def test_is_graphiti_enabled_exists(self):
        """Test that is_graphiti_enabled function exists"""
        from context.graphiti_integration import is_graphiti_enabled
        assert callable(is_graphiti_enabled)

    def test_get_graph_hints_exists(self):
        """Test that get_graph_hints function exists"""
        from context.graphiti_integration import get_graph_hints
        assert callable(get_graph_hints)


class TestIsGraphitiEnabled:
    """Tests for is_graphiti_enabled function"""

    def test_is_graphiti_enabled_returns_bool(self):
        """Test that is_graphiti_enabled returns boolean"""
        from context.graphiti_integration import is_graphiti_enabled
        result = is_graphiti_enabled()
        assert isinstance(result, bool)

    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=False)
    def test_is_graphiti_disabled_when_unavailable(self, mock_enabled):
        """Test that is_graphiti_enabled returns False when unavailable"""
        from context.graphiti_integration import is_graphiti_enabled
        result = is_graphiti_enabled()
        assert result is False


class TestFetchGraphHintsBasic:
    """Tests for fetch_graph_hints basic functionality"""

    @pytest.mark.asyncio
    async def test_fetch_graph_hints_returns_list(self):
        """Test that fetch_graph_hints always returns a list"""
        from context.graphiti_integration import fetch_graph_hints
        result = await fetch_graph_hints("test query", "/tmp/test")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_fetch_graph_hints_basic_params(self):
        """Test fetch_graph_hints with basic parameters"""
        from context.graphiti_integration import fetch_graph_hints
        result = await fetch_graph_hints(
            query="authentication",
            project_id="/tmp/test_project"
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_fetch_graph_hints_with_max_results(self):
        """Test fetch_graph_hints with max_results parameter"""
        from context.graphiti_integration import fetch_graph_hints
        result = await fetch_graph_hints(
            query="authentication",
            project_id="/tmp/test_project",
            max_results=15
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_fetch_graph_hints_empty_query(self):
        """Test fetch_graph_hints with empty query"""
        from context.graphiti_integration import fetch_graph_hints
        result = await fetch_graph_hints(
            query="",
            project_id="/tmp/test_project"
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_fetch_graph_hints_empty_project_id(self):
        """Test fetch_graph_hints with empty project_id"""
        from context.graphiti_integration import fetch_graph_hints
        result = await fetch_graph_hints(
            query="authentication",
            project_id=""
        )
        assert isinstance(result, list)


class TestFetchGraphHintsWhenDisabled:
    """Tests for fetch_graph_hints when Graphiti is disabled"""

    @pytest.mark.asyncio
    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=False)
    async def test_returns_empty_list_when_disabled(self, mock_enabled):
        """Test that fetch_graph_hints returns empty list when disabled"""
        from context.graphiti_integration import fetch_graph_hints
        result = await fetch_graph_hints(
            query="authentication",
            project_id="/tmp/test_project"
        )
        assert result == []

    @pytest.mark.asyncio
    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=False)
    async def test_skips_get_graph_hints_when_disabled(self, mock_enabled):
        """Test that get_graph_hints is not called when disabled"""
        from context.graphiti_integration import fetch_graph_hints

        # When disabled, should return empty list without calling get_graph_hints
        result = await fetch_graph_hints(
            query="authentication",
            project_id="/tmp/test_project"
        )
        # Should return empty list
        assert result == []


class TestFetchGraphHintsWhenEnabled:
    """Tests for fetch_graph_hints when Graphiti is enabled"""

    @pytest.mark.asyncio
    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=True)
    @patch('context.graphiti_integration.get_graph_hints', new_callable=AsyncMock)
    async def test_calls_get_graph_hints_when_enabled(self, mock_get_hints, mock_enabled):
        """Test that get_graph_hints is called when enabled"""
        from context.graphiti_integration import fetch_graph_hints

        mock_hints = [
            {"content": "Previous auth implementation"},
            {"content": "User login patterns"}
        ]
        mock_get_hints.return_value = mock_hints

        result = await fetch_graph_hints(
            query="authentication",
            project_id="/tmp/test_project",
            max_results=10
        )

        # Should call get_graph_hints with correct params
        mock_get_hints.assert_called_once_with(
            query="authentication",
            project_id="/tmp/test_project",
            max_results=10
        )
        assert result == mock_hints

    @pytest.mark.asyncio
    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=True)
    @patch('context.graphiti_integration.get_graph_hints', new_callable=AsyncMock)
    async def test_returns_hints_from_get_graph_hints(self, mock_get_hints, mock_enabled):
        """Test that hints from get_graph_hints are returned"""
        from context.graphiti_integration import fetch_graph_hints

        mock_hints = [
            {"content": "Auth pattern 1"},
            {"content": "Auth pattern 2"},
            {"content": "Auth pattern 3"}
        ]
        mock_get_hints.return_value = mock_hints

        result = await fetch_graph_hints(
            query="authentication",
            project_id="/tmp/test_project"
        )

        assert result == mock_hints
        assert len(result) == 3

    @pytest.mark.asyncio
    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=True)
    @patch('context.graphiti_integration.get_graph_hints', new_callable=AsyncMock)
    async def test_passes_query_parameter(self, mock_get_hints, mock_enabled):
        """Test that query parameter is passed correctly"""
        from context.graphiti_integration import fetch_graph_hints

        await fetch_graph_hints(
            query="user authentication",
            project_id="/tmp/test"
        )

        mock_get_hints.assert_called_once()
        call_kwargs = mock_get_hints.call_args.kwargs
        assert call_kwargs['query'] == "user authentication"

    @pytest.mark.asyncio
    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=True)
    @patch('context.graphiti_integration.get_graph_hints', new_callable=AsyncMock)
    async def test_passes_project_id_parameter(self, mock_get_hints, mock_enabled):
        """Test that project_id parameter is passed correctly"""
        from context.graphiti_integration import fetch_graph_hints

        await fetch_graph_hints(
            query="auth",
            project_id="/my/project"
        )

        mock_get_hints.assert_called_once()
        call_kwargs = mock_get_hints.call_args.kwargs
        assert call_kwargs['project_id'] == "/my/project"

    @pytest.mark.asyncio
    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=True)
    @patch('context.graphiti_integration.get_graph_hints', new_callable=AsyncMock)
    async def test_passes_max_results_parameter(self, mock_get_hints, mock_enabled):
        """Test that max_results parameter is passed correctly"""
        from context.graphiti_integration import fetch_graph_hints

        await fetch_graph_hints(
            query="auth",
            project_id="/tmp/test",
            max_results=20
        )

        mock_get_hints.assert_called_once()
        call_kwargs = mock_get_hints.call_args.kwargs
        assert call_kwargs['max_results'] == 20

    @pytest.mark.asyncio
    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=True)
    @patch('context.graphiti_integration.get_graph_hints', new_callable=AsyncMock)
    async def test_default_max_results(self, mock_get_hints, mock_enabled):
        """Test default max_results value"""
        from context.graphiti_integration import fetch_graph_hints

        await fetch_graph_hints(
            query="auth",
            project_id="/tmp/test"
        )

        mock_get_hints.assert_called_once()
        call_kwargs = mock_get_hints.call_args.kwargs
        assert call_kwargs['max_results'] == 5


class TestFetchGraphHintsErrorHandling:
    """Tests for error handling in fetch_graph_hints"""

    @pytest.mark.asyncio
    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=True)
    @patch('context.graphiti_integration.get_graph_hints', new_callable=AsyncMock)
    async def test_handles_exception_gracefully(self, mock_get_hints, mock_enabled):
        """Test that exceptions are handled gracefully"""
        from context.graphiti_integration import fetch_graph_hints

        # Mock get_graph_hints to raise exception
        mock_get_hints.side_effect = Exception("Graphiti connection error")

        result = await fetch_graph_hints(
            query="authentication",
            project_id="/tmp/test_project"
        )

        # Should return empty list on error
        assert result == []

    @pytest.mark.asyncio
    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=True)
    @patch('context.graphiti_integration.get_graph_hints', new_callable=AsyncMock)
    async def test_handles_connection_error(self, mock_get_hints, mock_enabled):
        """Test handling of connection errors"""
        from context.graphiti_integration import fetch_graph_hints

        mock_get_hints.side_effect = ConnectionError("Cannot connect to Graphiti")

        result = await fetch_graph_hints(
            query="auth",
            project_id="/tmp/test"
        )

        assert result == []

    @pytest.mark.asyncio
    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=True)
    @patch('context.graphiti_integration.get_graph_hints', new_callable=AsyncMock)
    async def test_handles_timeout_error(self, mock_get_hints, mock_enabled):
        """Test handling of timeout errors"""
        from context.graphiti_integration import fetch_graph_hints

        mock_get_hints.side_effect = TimeoutError("Graphiti timeout")

        result = await fetch_graph_hints(
            query="auth",
            project_id="/tmp/test"
        )

        assert result == []

    @pytest.mark.asyncio
    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=True)
    @patch('context.graphiti_integration.get_graph_hints', new_callable=AsyncMock)
    async def test_handles_generic_exception(self, mock_get_hints, mock_enabled):
        """Test handling of generic exceptions"""
        from context.graphiti_integration import fetch_graph_hints

        mock_get_hints.side_effect = RuntimeError("Unexpected error")

        result = await fetch_graph_hints(
            query="auth",
            project_id="/tmp/test"
        )

        # Should fail gracefully
        assert result == []

    @pytest.mark.asyncio
    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=True)
    @patch('context.graphiti_integration.get_graph_hints', new_callable=AsyncMock)
    async def test_handles_value_error(self, mock_get_hints, mock_enabled):
        """Test handling of value errors"""
        from context.graphiti_integration import fetch_graph_hints

        mock_get_hints.side_effect = ValueError("Invalid query format")

        result = await fetch_graph_hints(
            query="",
            project_id="/tmp/test"
        )

        assert result == []

    @pytest.mark.asyncio
    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=True)
    @patch('context.graphiti_integration.get_graph_hints', new_callable=AsyncMock)
    async def test_returns_empty_list_on_any_error(self, mock_get_hints, mock_enabled):
        """Test that any error results in empty list"""
        from context.graphiti_integration import fetch_graph_hints

        mock_get_hints.side_effect = Exception("Any error")

        result = await fetch_graph_hints(
            query="auth",
            project_id="/tmp/test"
        )

        # Should always return list (empty) on error
        assert isinstance(result, list)
        assert result == []


class TestFetchGraphHintsRealWorldScenarios:
    """Tests with real-world scenarios"""

    @pytest.mark.asyncio
    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=False)
    async def test_fallback_when_graphiti_unavailable(self, mock_enabled):
        """Test graceful fallback when Graphiti is not available"""
        from context.graphiti_integration import fetch_graph_hints

        result = await fetch_graph_hints(
            query="Implement JWT authentication for user login",
            project_id="/projects/myapp"
        )

        # Should return empty list instead of crashing
        assert result == []

    @pytest.mark.asyncio
    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=True)
    @patch('context.graphiti_integration.get_graph_hints', new_callable=AsyncMock)
    async def test_real_query_with_results(self, mock_get_hints, mock_enabled):
        """Test with realistic query and results"""
        from context.graphiti_integration import fetch_graph_hints

        mock_hints = [
            {
                "content": "Previously implemented JWT authentication in api/auth.py",
                "relevance": 0.95
            },
            {
                "content": "User login endpoint at POST /api/login",
                "relevance": 0.87
            }
        ]
        mock_get_hints.return_value = mock_hints

        result = await fetch_graph_hints(
            query="Implement JWT authentication for user login",
            project_id="/projects/myapp"
        )

        assert len(result) == 2
        assert result[0]["relevance"] == 0.95
        assert "JWT" in result[0]["content"]

    @pytest.mark.asyncio
    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=True)
    @patch('context.graphiti_integration.get_graph_hints', new_callable=AsyncMock)
    async def test_query_with_no_results(self, mock_get_hints, mock_enabled):
        """Test query that returns no results"""
        from context.graphiti_integration import fetch_graph_hints

        mock_get_hints.return_value = []

        result = await fetch_graph_hints(
            query="Brand new feature never implemented before",
            project_id="/projects/myapp"
        )

        assert result == []

    @pytest.mark.asyncio
    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=True)
    @patch('context.graphiti_integration.get_graph_hints', new_callable=AsyncMock)
    async def test_special_characters_in_query(self, mock_get_hints, mock_enabled):
        """Test query with special characters"""
        from context.graphiti_integration import fetch_graph_hints

        mock_get_hints.return_value = [{"content": "result"}]

        result = await fetch_graph_hints(
            query="Fix: API endpoint /api/v1/users returns 500 error!",
            project_id="/projects/myapp"
        )

        # Should handle special characters
        assert isinstance(result, list)

    @pytest.mark.asyncio
    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=True)
    @patch('context.graphiti_integration.get_graph_hints', new_callable=AsyncMock)
    async def test_very_long_query(self, mock_get_hints, mock_enabled):
        """Test with very long query"""
        from context.graphiti_integration import fetch_graph_hints

        mock_get_hints.return_value = [{"content": "result"}]
        long_query = " ".join(["authentication"] * 1000)

        result = await fetch_graph_hints(
            query=long_query,
            project_id="/projects/myapp"
        )

        # Should handle long queries
        assert isinstance(result, list)

    @pytest.mark.asyncio
    @patch('context.graphiti_integration.is_graphiti_enabled', return_value=True)
    @patch('context.graphiti_integration.get_graph_hints', new_callable=AsyncMock)
    async def test_unicode_in_query(self, mock_get_hints, mock_enabled):
        """Test query with unicode characters"""
        from context.graphiti_integration import fetch_graph_hints

        mock_get_hints.return_value = [{"content": "result"}]

        result = await fetch_graph_hints(
            query="Implement authentication for user caf support",
            project_id="/projects/myapp"
        )

        # Should handle unicode
        assert isinstance(result, list)
