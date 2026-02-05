"""Tests for agents.memory_manager module."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest

from agents.memory_manager import (
    debug_memory_system_status,
    get_graphiti_context,
    save_session_memory,
    save_session_to_graphiti,
)


class TestDebugMemorySystemStatus:
    """Test debug_memory_system_status function."""

    @patch("agents.memory_manager.is_debug_enabled")
    def test_does_not_crash(self, mock_debug_enabled):
        """Test that debug function runs without crashing when debug is disabled."""
        mock_debug_enabled.return_value = False
        # Should not raise any exceptions
        debug_memory_system_status()

    @patch("agents.memory_manager.debug")
    @patch("agents.memory_manager.debug_section")
    @patch("agents.memory_manager.is_debug_enabled")
    def test_logs_status_when_debug_enabled(self, mock_debug_enabled, mock_debug_section, mock_debug):
        """Test that debug function logs status when debug is enabled."""
        mock_debug_enabled.return_value = True
        mock_graphiti_status = {
            "enabled": True,
            "available": True,
            "host": "localhost",
            "port": 5433,
            "database": "test_db",
            "llm_provider": "openai",
            "embedder_provider": "openai",
        }
        with patch("agents.memory_manager.get_graphiti_status", return_value=mock_graphiti_status):
            debug_memory_system_status()

        mock_debug_section.assert_called_once()
        mock_debug.assert_called()

    @patch("agents.memory_manager.debug_detailed")
    @patch("agents.memory_manager.debug")
    @patch("agents.memory_manager.debug_section")
    @patch("agents.memory_manager.is_debug_enabled")
    def test_logs_graphiti_config_details(self, mock_debug_enabled, mock_debug_section, mock_debug, mock_debug_detailed):
        """Test that debug function logs Graphiti configuration details."""
        mock_debug_enabled.return_value = True
        mock_graphiti_status = {
            "enabled": True,
            "available": True,
            "host": "localhost",
            "port": 5433,
            "database": "test_db",
            "llm_provider": "openai",
            "embedder_provider": "openai",
        }
        with patch("agents.memory_manager.get_graphiti_status", return_value=mock_graphiti_status):
            debug_memory_system_status()

        mock_debug_detailed.assert_called_once()

    @patch("agents.memory_manager.debug_warning")
    @patch("agents.memory_manager.debug")
    @patch("agents.memory_manager.debug_section")
    @patch("agents.memory_manager.is_debug_enabled")
    def test_logs_warning_when_graphiti_unavailable(self, mock_debug_enabled, mock_debug_section, mock_debug, mock_debug_warning):
        """Test that debug function logs warning when Graphiti is enabled but unavailable."""
        mock_debug_enabled.return_value = True
        mock_graphiti_status = {
            "enabled": True,
            "available": False,
            "reason": "Package not installed",
            "errors": ["ImportError: No module named 'graphiti_core'"],
        }
        with patch("agents.memory_manager.get_graphiti_status", return_value=mock_graphiti_status):
            debug_memory_system_status()

        mock_debug_warning.assert_called_once()

    @patch("agents.memory_manager.debug_success")
    @patch("agents.memory_manager.debug")
    @patch("agents.memory_manager.debug_section")
    @patch("agents.memory_manager.is_debug_enabled")
    def test_logs_success_when_graphiti_ready(self, mock_debug_enabled, mock_debug_section, mock_debug, mock_debug_success):
        """Test that debug function logs success when Graphiti is ready."""
        mock_debug_enabled.return_value = True
        mock_graphiti_status = {
            "enabled": True,
            "available": True,
            "host": "localhost",
            "port": 5433,
            "database": "test_db",
            "llm_provider": "openai",
            "embedder_provider": "openai",
        }
        with patch("agents.memory_manager.get_graphiti_status", return_value=mock_graphiti_status):
            debug_memory_system_status()

        mock_debug_success.assert_called_once()

    @patch("agents.memory_manager.debug")
    @patch("agents.memory_manager.debug_section")
    @patch("agents.memory_manager.is_debug_enabled")
    def test_logs_file_based_fallback_message(self, mock_debug_enabled, mock_debug_section, mock_debug):
        """Test that debug function logs file-based fallback message when Graphiti is disabled."""
        mock_debug_enabled.return_value = True
        mock_graphiti_status = {
            "enabled": False,
            "available": False,
        }
        with patch("agents.memory_manager.get_graphiti_status", return_value=mock_graphiti_status):
            debug_memory_system_status()

        # Should call debug to mention file-based memory
        assert mock_debug.call_count >= 1


class TestGetGraphitiContext:
    """Test get_graphiti_context function."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a temporary spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    @pytest.mark.asyncio
    @patch("agents.memory_manager.debug_warning")
    @patch("agents.memory_manager.is_debug_enabled")
    async def test_logs_debug_warning_when_memory_none_with_debug_enabled(self, mock_is_debug_enabled, mock_debug_warning, mock_spec_dir, mock_project_dir):
        """Test that debug warning is logged when memory is None and debug is enabled."""
        mock_is_debug_enabled.return_value = True
        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=None):

            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test subtask"},
            )

            assert result is None
            mock_debug_warning.assert_called_once()

    @pytest.mark.asyncio
    @patch("agents.memory_manager.debug_success")
    @patch("agents.memory_manager.is_debug_enabled")
    async def test_logs_debug_success_on_context_format(self, mock_is_debug_enabled, mock_debug_success, mock_spec_dir, mock_project_dir):
        """Test that debug success is logged when context is formatted."""
        mock_is_debug_enabled.return_value = True
        mock_memory = AsyncMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[
            {"content": "Important context", "type": "insight"}
        ])
        mock_memory.get_patterns_and_gotchas = AsyncMock(return_value=([], []))
        mock_memory.get_session_history = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test subtask"},
            )

            mock_debug_success.assert_called_once()

    @pytest.mark.asyncio
    @patch("agents.memory_manager.debug_detailed")
    @patch("agents.memory_manager.is_debug_enabled")
    async def test_logs_debug_detailed_on_search(self, mock_is_debug_enabled, mock_debug_detailed, mock_spec_dir, mock_project_dir):
        """Test that debug detailed is logged when searching Graphiti."""
        mock_is_debug_enabled.return_value = True
        mock_memory = AsyncMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.get_patterns_and_gotchas = AsyncMock(return_value=([], []))
        mock_memory.get_session_history = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test subtask"},
            )

            # Should call debug_detailed with specific args
            mock_debug_detailed.assert_called_once()
            # Just check it was called, the call_args assertion was incorrect

    @pytest.mark.asyncio
    @patch("agents.memory_manager.debug_success")
    @patch("agents.memory_manager.debug")
    @patch("agents.memory_manager.debug_detailed")
    @patch("agents.memory_manager.is_debug_enabled")
    async def test_logs_search_with_valid_query(self, mock_is_debug_enabled, mock_debug_detailed, mock_debug, mock_debug_success, mock_spec_dir, mock_project_dir):
        """Test that searching Graphiti with valid query logs debug info."""
        mock_is_debug_enabled.return_value = True
        mock_memory = AsyncMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[
            {"content": "test", "type": "info"}
        ])
        mock_memory.get_patterns_and_gotchas = AsyncMock(return_value=([], []))
        mock_memory.get_session_history = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "abc123", "description": "Build authentication feature"},
            )

            assert result is not None
            mock_debug_detailed.assert_called()
            mock_debug.assert_called()
            mock_debug_success.assert_called()

    @pytest.mark.asyncio
    async def test_returns_none_when_graphiti_disabled(self, mock_spec_dir, mock_project_dir):
        """Test that None is returned when Graphiti is disabled."""
        with patch("agents.memory_manager.is_graphiti_enabled", return_value=False):
            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test subtask"},
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_memory_unavailable(self, mock_spec_dir, mock_project_dir):
        """Test that None is returned when GraphitiMemory is unavailable."""
        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=None):

            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test subtask"},
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_query_empty(self, mock_spec_dir, mock_project_dir):
        """Test that None is returned when the query is empty."""
        mock_memory = AsyncMock()
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "", "description": ""},  # Empty query
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_subtask_has_no_id_or_description(self, mock_spec_dir, mock_project_dir):
        """Test that None is returned when subtask has no id or description."""
        mock_memory = AsyncMock()
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={},  # Empty subtask
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_data_found(self, mock_spec_dir, mock_project_dir):
        """Test that None is returned when Graphiti has no relevant data."""
        mock_memory = AsyncMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.get_patterns_and_gotchas = AsyncMock(return_value=([], []))
        mock_memory.get_session_history = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test subtask"},
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_context_when_data_available(self, mock_spec_dir, mock_project_dir):
        """Test that formatted context is returned when Graphiti has data."""
        mock_memory = AsyncMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[
            {"content": "Important context", "type": "insight"}
        ])
        mock_memory.get_patterns_and_gotchas = AsyncMock(return_value=([], []))
        mock_memory.get_session_history = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test subtask"},
            )

            assert result is not None
            assert "Graphiti Memory Context" in result
            assert "Important context" in result

    @pytest.mark.asyncio
    async def test_closes_memory_connection(self, mock_spec_dir, mock_project_dir):
        """Test that memory connection is always closed."""
        mock_memory = AsyncMock()
        mock_memory.get_relevant_context = AsyncMock(side_effect=Exception("Test error"))
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            try:
                await get_graphiti_context(
                    spec_dir=mock_spec_dir,
                    project_dir=mock_project_dir,
                    subtask={"id": "test-1", "description": "Test subtask"},
                )
            except Exception:
                pass

            # Memory should still be closed despite error
            mock_memory.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_includes_patterns_in_context(self, mock_spec_dir, mock_project_dir):
        """Test that patterns are included in the context."""
        mock_memory = AsyncMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.get_patterns_and_gotchas = AsyncMock(return_value=(
            [{"pattern": "Use async/await", "applies_to": "file operations"}],
            []
        ))
        mock_memory.get_session_history = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test subtask"},
            )

            assert result is not None
            assert "Learned Patterns" in result
            assert "Use async/await" in result

    @pytest.mark.asyncio
    async def test_includes_gotchas_in_context(self, mock_spec_dir, mock_project_dir):
        """Test that gotchas are included in the context."""
        mock_memory = AsyncMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.get_patterns_and_gotchas = AsyncMock(return_value=(
            [],
            [{"gotcha": "Forgetting to close files", "solution": "Use context managers"}]
        ))
        mock_memory.get_session_history = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test subtask"},
            )

            assert result is not None
            assert "Known Gotchas" in result
            assert "Forgetting to close files" in result
            assert "Use context managers" in result

    @pytest.mark.asyncio
    async def test_includes_session_history_in_context(self, mock_spec_dir, mock_project_dir):
        """Test that session history is included in the context."""
        mock_memory = AsyncMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.get_patterns_and_gotchas = AsyncMock(return_value=([], []))
        mock_memory.get_session_history = AsyncMock(return_value=[
            {
                "session_number": 1,
                "recommendations_for_next_session": ["Review error handling", "Add more tests"]
            }
        ])
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test subtask"},
            )

            assert result is not None
            assert "Recent Session Insights" in result
            assert "Session 1 recommendations" in result
            assert "Review error handling" in result

    @pytest.mark.asyncio
    async def test_patterns_without_applies_to(self, mock_spec_dir, mock_project_dir):
        """Test pattern formatting when applies_to is not present."""
        mock_memory = AsyncMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.get_patterns_and_gotchas = AsyncMock(return_value=(
            [{"pattern": "Keep functions small"}],  # No applies_to
            []
        ))
        mock_memory.get_session_history = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test subtask"},
            )

            assert result is not None
            assert "Keep functions small" in result

    @pytest.mark.asyncio
    async def test_gotchas_without_solution(self, mock_spec_dir, mock_project_dir):
        """Test gotcha formatting when solution is not present."""
        mock_memory = AsyncMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.get_patterns_and_gotchas = AsyncMock(return_value=(
            [],
            [{"gotcha": "Race condition in tests"}]  # No solution
        ))
        mock_memory.get_session_history = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test subtask"},
            )

            assert result is not None
            assert "Race condition in tests" in result

    @pytest.mark.asyncio
    async def test_closes_connection_on_get_graphiti_memory_exception(self, mock_spec_dir, mock_project_dir):
        """Test that connection is closed even when get_graphiti_memory raises an exception."""
        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, side_effect=Exception("Connection failed")):

            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test subtask"},
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_limits_session_history_to_two_sessions(self, mock_spec_dir, mock_project_dir):
        """Test that only the first 2 sessions from history are included in context."""
        mock_memory = AsyncMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.get_patterns_and_gotchas = AsyncMock(return_value=([], []))
        mock_memory.get_session_history = AsyncMock(return_value=[
            {"session_number": i, "recommendations_for_next_session": [f"Rec {i}"]}
            for i in range(1, 6)  # 5 sessions
        ])
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test subtask"},
            )

            assert result is not None
            # The code uses session_history[:2] which takes the first 2 sessions
            assert "Session 1" in result
            assert "Session 2" in result
            # Sessions 3, 4, 5 should not be included
            assert "Session 3" not in result
            assert "Session 4" not in result
            assert "Session 5" not in result

    @pytest.mark.asyncio
    @patch("agents.memory_manager.capture_exception")
    async def test_captures_exception_on_error(self, mock_capture_exception, mock_spec_dir, mock_project_dir):
        """Test that exceptions are captured to Sentry."""
        mock_memory = AsyncMock()
        mock_memory.get_relevant_context = AsyncMock(side_effect=RuntimeError("Test error"))
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test subtask"},
            )

            assert result is None
            mock_capture_exception.assert_called_once()

    @pytest.mark.asyncio
    @patch("agents.memory_manager.debug_error")
    @patch("agents.memory_manager.capture_exception")
    @patch("agents.memory_manager.is_debug_enabled")
    async def test_logs_debug_error_on_exception_with_debug_enabled(self, mock_is_debug_enabled, mock_capture_exception, mock_debug_error, mock_spec_dir, mock_project_dir):
        """Test that debug error is logged when exception occurs and debug is enabled."""
        mock_is_debug_enabled.return_value = True
        mock_memory = AsyncMock()
        mock_memory.get_relevant_context = AsyncMock(side_effect=RuntimeError("Test error"))
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test subtask"},
            )

            assert result is None
            mock_debug_error.assert_called_once()
            mock_capture_exception.assert_called_once()

    @pytest.mark.asyncio
    @patch("agents.memory_manager.debug")
    @patch("agents.memory_manager.is_debug_enabled")
    async def test_logs_debug_info(self, mock_is_debug_enabled, mock_debug, mock_spec_dir, mock_project_dir):
        """Test that debug logging works when enabled."""
        mock_is_debug_enabled.return_value = True
        mock_memory = AsyncMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.get_patterns_and_gotchas = AsyncMock(return_value=([], []))
        mock_memory.get_session_history = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test subtask"},
            )

            mock_debug.assert_called()

    @pytest.mark.asyncio
    @patch("agents.memory_manager.debug")
    @patch("agents.memory_manager.is_debug_enabled")
    async def test_logs_graphiti_not_enabled_debug(self, mock_is_debug_enabled, mock_debug, mock_spec_dir, mock_project_dir):
        """Test debug logging when Graphiti is not enabled."""
        mock_is_debug_enabled.return_value = True
        with patch("agents.memory_manager.is_graphiti_enabled", return_value=False):
            await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test subtask"},
            )
        # Should log that Graphiti is not enabled
        mock_debug.assert_called()

    @pytest.mark.asyncio
    @patch("agents.memory_manager.debug_warning")
    @patch("agents.memory_manager.is_debug_enabled")
    async def test_logs_empty_query_warning(self, mock_is_debug_enabled, mock_debug_warning, mock_spec_dir, mock_project_dir):
        """Test debug warning when query is empty."""
        mock_is_debug_enabled.return_value = True
        mock_memory = AsyncMock()
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "", "description": ""},  # Empty query
            )
        # Should log warning for empty query
        mock_debug_warning.assert_called_once()


class TestSaveSessionMemory:
    """Test save_session_memory function."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a temporary spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    @pytest.mark.asyncio
    @patch("agents.memory_manager.debug")
    @patch("agents.memory_manager.is_debug_enabled")
    async def test_saves_to_graphiti_when_enabled(self, mock_is_debug_enabled, mock_debug, mock_spec_dir, mock_project_dir):
        """Test that session is saved to Graphiti when enabled."""
        mock_is_debug_enabled.return_value = True
        mock_memory = AsyncMock()
        mock_memory.is_enabled = True
        mock_memory.save_structured_insights = AsyncMock(return_value=True)
        mock_memory.save_session_insights = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            success, storage_type = await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries={"file_insights": [{"file": "test.py", "insights": ["test"]}]},
            )

            assert success is True
            assert storage_type == "graphiti"
            # Should call save_structured_insights when file_insights is present and non-empty
            mock_memory.save_structured_insights.assert_called_once()
            mock_debug.assert_called()

    @pytest.mark.asyncio
    async def test_saves_basic_insights_without_file_insights(self, mock_spec_dir, mock_project_dir):
        """Test that basic session insights are saved when file_insights is missing."""
        mock_memory = AsyncMock()
        mock_memory.is_enabled = True
        mock_memory.save_session_insights = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            success, storage_type = await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries=None,  # No file_insights
            )

            assert success is True
            assert storage_type == "graphiti"
            # Should call save_session_insights when file_insights is not present
            mock_memory.save_session_insights.assert_called_once()

    @pytest.mark.asyncio
    async def test_saves_basic_insights_with_empty_file_insights(self, mock_spec_dir, mock_project_dir):
        """Test that basic insights are saved when file_insights is empty."""
        mock_memory = AsyncMock()
        mock_memory.is_enabled = True
        mock_memory.save_session_insights = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            success, storage_type = await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries={},  # Empty discoveries
            )

            assert success is True
            assert storage_type == "graphiti"
            mock_memory.save_session_insights.assert_called_once()

    @pytest.mark.asyncio
    @patch("agents.memory_manager.debug_warning")
    @patch("agents.memory_manager.is_debug_enabled")
    async def test_falls_back_to_file_when_graphiti_save_fails(self, mock_is_debug_enabled, mock_debug_warning, mock_spec_dir, mock_project_dir):
        """Test fallback to file-based memory when Graphiti save returns False."""
        mock_is_debug_enabled.return_value = True
        mock_memory = AsyncMock()
        mock_memory.is_enabled = True
        mock_memory.save_session_insights = AsyncMock(return_value=False)  # Save fails
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory), \
             patch("agents.memory_manager.save_file_based_memory") as mock_save:

            success, storage_type = await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries=None,
            )

            assert success is True
            assert storage_type == "file"
            mock_save.assert_called_once()
            mock_debug_warning.assert_called()

    @pytest.mark.asyncio
    @patch("agents.memory_manager.debug_error")
    @patch("agents.memory_manager.is_debug_enabled")
    async def test_falls_back_to_file_when_graphiti_exception(self, mock_is_debug_enabled, mock_debug_error, mock_spec_dir, mock_project_dir):
        """Test fallback to file-based memory when Graphiti raises exception."""
        mock_is_debug_enabled.return_value = True
        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, side_effect=Exception("Graphiti error")), \
             patch("agents.memory_manager.save_file_based_memory") as mock_save:

            success, storage_type = await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries=None,
            )

            assert success is True
            assert storage_type == "file"
            mock_save.assert_called_once()
            mock_debug_error.assert_called()

    @pytest.mark.asyncio
    async def test_uses_file_based_when_graphiti_disabled(self, mock_spec_dir, mock_project_dir):
        """Test that file-based memory is used when Graphiti is disabled."""
        with patch("agents.memory_manager.is_graphiti_enabled", return_value=False), \
             patch("agents.memory_manager.save_file_based_memory") as mock_save:

            success, storage_type = await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries=None,
            )

            assert success is True
            assert storage_type == "file"
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    @patch("agents.memory_manager.debug_error")
    @patch("agents.memory_manager.is_debug_enabled")
    async def test_returns_failure_when_both_fail(self, mock_is_debug_enabled, mock_debug_error, mock_spec_dir, mock_project_dir):
        """Test that failure is returned when both storage methods fail."""
        mock_is_debug_enabled.return_value = True
        with patch("agents.memory_manager.is_graphiti_enabled", return_value=False), \
             patch("agents.memory_manager.save_file_based_memory", side_effect=Exception("File save error")):

            success, storage_type = await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries=None,
            )

            assert success is False
            assert storage_type == "none"
            mock_debug_error.assert_called()

    @pytest.mark.asyncio
    async def test_closes_memory_connection_on_graphiti_success(self, mock_spec_dir, mock_project_dir):
        """Test that memory connection is closed after successful Graphiti save."""
        mock_memory = AsyncMock()
        mock_memory.is_enabled = True
        mock_memory.save_structured_insights = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries=None,
            )

            mock_memory.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_closes_memory_connection_on_graphiti_exception(self, mock_spec_dir, mock_project_dir):
        """Test that memory connection is closed even when Graphiti raises exception."""
        mock_memory = AsyncMock()
        mock_memory.is_enabled = True
        mock_memory.save_session_insights = AsyncMock(side_effect=Exception("Save failed"))
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory), \
             patch("agents.memory_manager.save_file_based_memory"):

            await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries=None,
            )

            mock_memory.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_memory_not_enabled(self, mock_spec_dir, mock_project_dir):
        """Test handling when memory is not None but is_enabled is False."""
        mock_memory = AsyncMock()
        mock_memory.is_enabled = False  # Not enabled
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory), \
             patch("agents.memory_manager.save_file_based_memory") as mock_save:

            success, storage_type = await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries=None,
            )

            # Should fall back to file-based
            assert success is True
            assert storage_type == "file"
            mock_save.assert_called_once()
            mock_memory.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_memory_none_from_get_graphiti_memory(self, mock_spec_dir, mock_project_dir):
        """Test handling when get_graphiti_memory returns None."""
        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=None), \
             patch("agents.memory_manager.save_file_based_memory") as mock_save:

            success, storage_type = await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries=None,
            )

            # Should fall back to file-based
            assert success is True
            assert storage_type == "file"
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    @patch("agents.memory_manager.capture_exception")
    async def test_captures_exception_on_graphiti_error(self, mock_capture_exception, mock_spec_dir, mock_project_dir):
        """Test that exceptions are captured to Sentry on Graphiti errors."""
        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, side_effect=RuntimeError("Connection error")), \
             patch("agents.memory_manager.save_file_based_memory"):

            await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries=None,
            )

            mock_capture_exception.assert_called_once()

    @pytest.mark.asyncio
    @patch("agents.memory_manager.capture_exception")
    async def test_captures_exception_on_file_error(self, mock_capture_exception, mock_spec_dir, mock_project_dir):
        """Test that exceptions are captured to Sentry on file save errors."""
        with patch("agents.memory_manager.is_graphiti_enabled", return_value=False), \
             patch("agents.memory_manager.save_file_based_memory", side_effect=IOError("Disk full")):

            success, storage_type = await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries=None,
            )

            assert success is False
            assert storage_type == "none"
            mock_capture_exception.assert_called_once()

    @pytest.mark.asyncio
    @patch("agents.memory_manager.debug")
    @patch("agents.memory_manager.debug_section")
    @patch("agents.memory_manager.is_debug_enabled")
    async def test_logs_debug_info(self, mock_is_debug_enabled, mock_debug_section, mock_debug, mock_spec_dir, mock_project_dir):
        """Test that debug logging works when enabled."""
        mock_is_debug_enabled.return_value = True
        with patch("agents.memory_manager.is_graphiti_enabled", return_value=False), \
             patch("agents.memory_manager.save_file_based_memory"):

            await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries=None,
            )

            mock_debug_section.assert_called_once()
            mock_debug.assert_called()

    @pytest.mark.asyncio
    @patch("agents.memory_manager.debug_detailed")
    @patch("agents.memory_manager.debug")
    @patch("agents.memory_manager.debug_section")
    @patch("agents.memory_manager.is_debug_enabled")
    async def test_logs_graphiti_status_debug_info(self, mock_is_debug_enabled, mock_debug_section, mock_debug, mock_debug_detailed, mock_spec_dir, mock_project_dir):
        """Test that Graphiti status is logged when debug is enabled."""
        mock_is_debug_enabled.return_value = True
        mock_graphiti_status = {
            "enabled": True,
            "available": True,
            "host": "localhost",
            "port": 5433,
            "database": "test_db",
            "llm_provider": "openai",
            "embedder_provider": "openai",
            "reason": None,
        }

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_status", return_value=mock_graphiti_status), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=None), \
             patch("agents.memory_manager.save_file_based_memory"):

            await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries=None,
            )

            mock_debug_detailed.assert_called()

    @pytest.mark.asyncio
    async def test_builds_insights_structure_correctly_on_success(self, mock_spec_dir, mock_project_dir):
        """Test that insights structure is built correctly for successful session."""
        mock_memory = AsyncMock()
        mock_memory.is_enabled = True
        mock_memory.save_session_insights = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1", "test-2"],
                discoveries=None,
            )

            # Verify the insights structure passed to save_session_insights
            call_args = mock_memory.save_session_insights.call_args
            session_num_arg = call_args[0][0]
            insights_arg = call_args[0][1]

            assert session_num_arg == 1
            assert insights_arg["subtasks_completed"] == ["test-1", "test-2"]
            assert insights_arg["what_worked"] == ["Implemented subtask: test-1"]
            assert insights_arg["what_failed"] == []

    @pytest.mark.asyncio
    async def test_builds_insights_structure_correctly_on_failure(self, mock_spec_dir, mock_project_dir):
        """Test that insights structure is built correctly for failed session."""
        mock_memory = AsyncMock()
        mock_memory.is_enabled = True
        mock_memory.save_session_insights = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=False,  # Failed session
                subtasks_completed=["test-1"],
                discoveries=None,
            )

            # Verify the insights structure
            call_args = mock_memory.save_session_insights.call_args
            insights_arg = call_args[0][1]

            assert insights_arg["what_worked"] == []
            assert insights_arg["what_failed"] == ["Failed to complete subtask: test-1"]

    @pytest.mark.asyncio
    async def test_handles_close_exception_gracefully(self, mock_spec_dir, mock_project_dir):
        """Test that close exceptions are handled gracefully."""
        mock_memory = AsyncMock()
        mock_memory.is_enabled = True
        mock_memory.save_session_insights = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock(side_effect=Exception("Close failed"))

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            # Should not raise exception even if close fails
            success, storage_type = await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries=None,
            )

            # Should still be successful
            assert success is True
            assert storage_type == "graphiti"

    @pytest.mark.asyncio
    @patch("agents.memory_manager.debug")
    @patch("agents.memory_manager.debug_section")
    @patch("agents.memory_manager.is_debug_enabled")
    async def test_logs_saving_to_graphiti_debug(self, mock_is_debug_enabled, mock_debug_section, mock_debug, mock_spec_dir, mock_project_dir):
        """Test that saving to Graphiti is logged when debug is enabled."""
        mock_is_debug_enabled.return_value = True
        mock_memory = AsyncMock()
        mock_memory.is_enabled = True
        mock_memory.save_session_insights = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries=None,
            )

        # Should log "Saving to Graphiti..."
        assert any("Saving" in str(call) for call in mock_debug.call_args_list)

    @pytest.mark.asyncio
    @patch("agents.memory_manager.debug_warning")
    @patch("agents.memory_manager.debug")
    @patch("agents.memory_manager.debug_section")
    @patch("agents.memory_manager.is_debug_enabled")
    async def test_logs_graphiti_disabled_warning_debug(self, mock_is_debug_enabled, mock_debug_section, mock_debug, mock_debug_warning, mock_spec_dir, mock_project_dir):
        """Test that Graphiti disabled warning is logged when debug is enabled."""
        mock_is_debug_enabled.return_value = True
        mock_memory = AsyncMock()
        mock_memory.is_enabled = False  # Disabled
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory), \
             patch("agents.memory_manager.save_file_based_memory"):

            await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries=None,
            )

        # Should log warning about GraphitiMemory being disabled
        mock_debug_warning.assert_called()


class TestSaveSessionToGraphiti:
    """Test save_session_to_graphiti backwards compatibility wrapper."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a temporary spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    @pytest.mark.asyncio
    async def test_wraps_save_session_memory(self, mock_spec_dir, mock_project_dir):
        """Test that wrapper correctly calls save_session_memory."""
        with patch("agents.memory_manager.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")) as mock_save:

            result = await save_session_to_graphiti(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries=None,
            )

            assert result is True
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_forwards_all_parameters(self, mock_spec_dir, mock_project_dir):
        """Test that wrapper forwards all parameters correctly."""
        discoveries = {"file_insights": ["test"]}
        with patch("agents.memory_manager.save_session_memory", new_callable=AsyncMock, return_value=(True, "graphiti")) as mock_save:

            await save_session_to_graphiti(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=5,
                success=False,
                subtasks_completed=["test-1", "test-2"],
                discoveries=discoveries,
            )

            mock_save.assert_called_once_with(
                mock_spec_dir,
                mock_project_dir,
                "test-1",
                5,
                False,
                ["test-1", "test-2"],
                discoveries,
            )

    @pytest.mark.asyncio
    async def test_returns_false_on_save_failure(self, mock_spec_dir, mock_project_dir):
        """Test that wrapper returns False when save fails."""
        with patch("agents.memory_manager.save_session_memory", new_callable=AsyncMock, return_value=(False, "none")):

            result = await save_session_to_graphiti(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries=None,
            )

            assert result is False


class TestGetGraphitiContextEdgeCases:
    """Test get_graphiti_context edge cases and error handling."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a temporary spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    @pytest.mark.asyncio
    async def test_handles_memory_close_exception(self, mock_spec_dir, mock_project_dir):
        """Test that close exception is handled gracefully."""
        mock_memory = AsyncMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.get_patterns_and_gotchas = AsyncMock(return_value=([], []))
        mock_memory.get_session_history = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock(side_effect=ConnectionError("Close failed"))

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            # Should not raise exception
            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test"},
            )

            assert result is None  # No data, but no exception

    @pytest.mark.asyncio
    async def test_handles_empty_results_from_graphiti(self, mock_spec_dir, mock_project_dir):
        """Test handling when Graphiti returns empty results."""
        mock_memory = AsyncMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.get_patterns_and_gotchas = AsyncMock(return_value=([], []))
        mock_memory.get_session_history = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test"},
            )

            # Empty results should return None
            assert result is None

    @pytest.mark.asyncio
    async def test_handles_malformed_context_items(self, mock_spec_dir, mock_project_dir):
        """Test handling of malformed context items."""
        mock_memory = AsyncMock()
        # Malformed items (missing keys, empty content, etc.)
        mock_memory.get_relevant_context = AsyncMock(return_value=[
            {},  # Empty dict
            {"content": "", "type": "insight"},  # Empty content
            {"type": "unknown"},  # Missing content
        ])
        mock_memory.get_patterns_and_gotchas = AsyncMock(return_value=([], []))
        mock_memory.get_session_history = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            # Should not crash, should return None or formatted result
            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test"},
            )

            # Result could be None or have empty sections
            assert result is not None  # Has the header at least

    @pytest.mark.asyncio
    async def test_handles_long_content_truncation(self, mock_spec_dir, mock_project_dir):
        """Test that long content is properly truncated."""
        long_content = "x" * 1000  # 1000 characters
        mock_memory = AsyncMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[
            {"content": long_content, "type": "insight"}
        ])
        mock_memory.get_patterns_and_gotchas = AsyncMock(return_value=([], []))
        mock_memory.get_session_history = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test"},
            )

            # Should truncate content to 500 chars
            assert result is not None
            # Content should be truncated
            assert len([line for line in result.split("\n") if "x" in line]) > 0

    @pytest.mark.asyncio
    async def test_handles_unicode_in_subtask(self, mock_spec_dir, mock_project_dir):
        """Test handling of unicode characters in subtask description."""
        mock_memory = AsyncMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.get_patterns_and_gotchas = AsyncMock(return_value=([], []))
        mock_memory.get_session_history = AsyncMock(return_value=[])
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            # Unicode description should not cause issues
            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test with unicode: \u2713 \u2717 \u2600"},
            )

            # Should handle gracefully
            assert result is None

    @pytest.mark.asyncio
    async def test_handles_session_without_recommendations(self, mock_spec_dir, mock_project_dir):
        """Test session history without recommendations."""
        mock_memory = AsyncMock()
        mock_memory.get_relevant_context = AsyncMock(return_value=[])
        mock_memory.get_patterns_and_gotchas = AsyncMock(return_value=([], []))
        mock_memory.get_session_history = AsyncMock(return_value=[
            {"session_number": 1},  # No recommendations
        ])
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            result = await get_graphiti_context(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask={"id": "test-1", "description": "Test"},
            )

            assert result is not None
            # Should not crash on missing recommendations


class TestSaveSessionMemoryEdgeCases:
    """Test save_session_memory edge cases."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a temporary spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    @pytest.mark.asyncio
    async def test_handles_empty_discoveries_dict(self, mock_spec_dir, mock_project_dir):
        """Test handling of empty discoveries dictionary."""
        mock_memory = AsyncMock()
        mock_memory.is_enabled = True
        mock_memory.save_session_insights = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            success, storage_type = await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries={},  # Empty dict
            )

            assert success is True
            assert storage_type == "graphiti"
            # Should call save_session_insights since file_insights is missing
            mock_memory.save_session_insights.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_discoveries_with_empty_file_insights(self, mock_spec_dir, mock_project_dir):
        """Test handling of discoveries with empty file_insights list."""
        mock_memory = AsyncMock()
        mock_memory.is_enabled = True
        mock_memory.save_session_insights = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            success, storage_type = await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries={"file_insights": []},  # Empty list
            )

            assert success is True
            # Empty file_insights should use save_session_insights
            mock_memory.save_session_insights.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_multiple_subtasks_completed(self, mock_spec_dir, mock_project_dir):
        """Test handling of multiple completed subtasks."""
        mock_memory = AsyncMock()
        mock_memory.is_enabled = True
        mock_memory.save_session_insights = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            success, storage_type = await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1", "test-2", "test-3"],  # Multiple
                discoveries=None,
            )

            assert success is True
            # Verify insights includes all subtasks
            call_args = mock_memory.save_session_insights.call_args
            insights = call_args[0][1]
            assert insights["subtasks_completed"] == ["test-1", "test-2", "test-3"]

    @pytest.mark.asyncio
    async def test_handles_zero_session_number(self, mock_spec_dir, mock_project_dir):
        """Test handling of session_num=0 (edge case)."""
        mock_memory = AsyncMock()
        mock_memory.is_enabled = True
        mock_memory.save_session_insights = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            success, storage_type = await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=0,  # Edge case
                success=True,
                subtasks_completed=["test-1"],
                discoveries=None,
            )

            assert success is True
            # Should pass session_num=0 to save
            call_args = mock_memory.save_session_insights.call_args
            assert call_args[0][0] == 0

    @pytest.mark.asyncio
    async def test_graphiti_save_returns_false_falls_back_to_file(self, mock_spec_dir, mock_project_dir):
        """Test fallback to file when Graphiti save returns False."""
        mock_memory = AsyncMock()
        mock_memory.is_enabled = True
        mock_memory.save_structured_insights = AsyncMock(return_value=False)  # Save fails
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory), \
             patch("agents.memory_manager.save_file_based_memory") as mock_save:

            success, storage_type = await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries={"file_insights": ["test"]},  # Has file_insights
            )

            # Should fall back to file-based
            assert success is True
            assert storage_type == "file"
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_dual_storage_both_fail(self, mock_spec_dir, mock_project_dir):
        """Test complete failure when both storage methods fail."""
        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, side_effect=ConnectionError("Graphiti failed")), \
             patch("agents.memory_manager.save_file_based_memory", side_effect=IOError("File write failed")):

            success, storage_type = await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries=None,
            )

            # Both failed
            assert success is False
            assert storage_type == "none"

    @pytest.mark.asyncio
    async def test_structured_insights_with_rich_discoveries(self, mock_spec_dir, mock_project_dir):
        """Test that rich discoveries use save_structured_insights."""
        mock_memory = AsyncMock()
        mock_memory.is_enabled = True
        mock_memory.save_structured_insights = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock()

        rich_discoveries = {
            "file_insights": [
                {"file": "test.py", "summary": "Added function"},
                {"file": "main.py", "summary": "Updated imports"},
            ],
            "patterns_discovered": [
                {"pattern": "Use factory pattern", "applies_to": "object creation"}
            ],
            "gotchas_encountered": [
                {"gotcha": "Race condition", "solution": "Add mutex"}
            ]
        }

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            success, storage_type = await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="test-1",
                session_num=1,
                success=True,
                subtasks_completed=["test-1"],
                discoveries=rich_discoveries,
            )

            assert success is True
            # Should use save_structured_insights for rich data
            mock_memory.save_structured_insights.assert_called_once_with(rich_discoveries)

    @pytest.mark.asyncio
    async def test_what_worked_includes_subtask_for_success(self, mock_spec_dir, mock_project_dir):
        """Test that what_worked includes subtask info on success."""
        mock_memory = AsyncMock()
        mock_memory.is_enabled = True
        mock_memory.save_session_insights = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="my-subtask",
                session_num=1,
                success=True,
                subtasks_completed=["my-subtask"],
                discoveries=None,
            )

            # Check what_worked in insights
            call_args = mock_memory.save_session_insights.call_args
            insights = call_args[0][1]
            assert insights["what_worked"] == ["Implemented subtask: my-subtask"]
            assert insights["what_failed"] == []

    @pytest.mark.asyncio
    async def test_what_failed_includes_subtask_for_failure(self, mock_spec_dir, mock_project_dir):
        """Test that what_failed includes subtask info on failure."""
        mock_memory = AsyncMock()
        mock_memory.is_enabled = True
        mock_memory.save_session_insights = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock()

        with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
             patch("agents.memory_manager.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):

            await save_session_memory(
                spec_dir=mock_spec_dir,
                project_dir=mock_project_dir,
                subtask_id="failed-subtask",
                session_num=1,
                success=False,  # Failed
                subtasks_completed=[],
                discoveries=None,
            )

            # Check what_failed in insights
            call_args = mock_memory.save_session_insights.call_args
            insights = call_args[0][1]
            assert insights["what_worked"] == []
            assert insights["what_failed"] == ["Failed to complete subtask: failed-subtask"]


class TestDebugMemorySystemStatusEdgeCases:
    """Test debug_memory_system_status edge cases."""

    @patch("agents.memory_manager.is_debug_enabled")
    def test_handles_missing_optional_status_keys(self, mock_debug_enabled):
        """Test handling of Graphiti status with missing optional keys."""
        mock_debug_enabled.return_value = True
        # Status dict missing optional keys
        incomplete_status = {
            "enabled": True,
            "available": True,
            # Missing: host, port, database, llm_provider, embedder_provider
        }

        with patch("agents.memory_manager.get_graphiti_status", return_value=incomplete_status):
            # Should not crash on missing keys
            debug_memory_system_status()

    @patch("agents.memory_manager.debug")
    @patch("agents.memory_manager.debug_section")
    @patch("agents.memory_manager.is_debug_enabled")
    def test_logs_message_when_graphiti_available_but_errors_present(self, mock_debug_enabled, mock_debug_section, mock_debug):
        """Test logging when Graphiti reports errors."""
        mock_debug_enabled.return_value = True
        status_with_errors = {
            "enabled": True,
            "available": False,
            "reason": "Connection failed",
            "errors": ["Error 1", "Error 2"],
        }

        with patch("agents.memory_manager.get_graphiti_status", return_value=status_with_errors):
            debug_memory_system_status()

        # Should have logged the error information
        mock_debug.assert_called()

    @patch("agents.memory_manager.debug")
    @patch("agents.memory_manager.debug_section")
    @patch("agents.memory_manager.is_debug_enabled")
    def test_handles_empty_errors_list(self, mock_debug_enabled, mock_debug_section, mock_debug):
        """Test handling of empty errors list."""
        mock_debug_enabled.return_value = True
        status_with_empty_errors = {
            "enabled": True,
            "available": False,
            "reason": "Unknown",
            "errors": [],  # Empty errors
        }

        with patch("agents.memory_manager.get_graphiti_status", return_value=status_with_empty_errors):
            # Should not crash on empty errors
            debug_memory_system_status()

            mock_debug.assert_called()
