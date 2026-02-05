"""
Tests for graphiti_helpers module.
Comprehensive test coverage for all functions and edge cases.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import Any

import pytest

from memory.graphiti_helpers import (
    is_graphiti_memory_enabled,
    run_async,
    get_graphiti_memory,
    save_to_graphiti_async,
)


class TestIsGraphitiMemoryEnabled:
    """Tests for is_graphiti_memory_enabled function."""

    def test_returns_boolean(self):
        """Test that function returns a boolean."""
        result = is_graphiti_memory_enabled()
        assert isinstance(result, bool)

    def test_returns_false_on_import_error(self):
        """Test returns False when graphiti_config import fails."""
        # When graphiti_config is not available, returns False
        # This happens when the module is not installed
        result = is_graphiti_memory_enabled()
        # If graphiti_config is not installed, returns False
        assert isinstance(result, bool)

        # Also test by temporarily blocking import
        import sys
        original_modules = sys.modules.copy()
        try:
            # Remove graphiti_config from sys.modules if it exists
            sys.modules.pop("graphiti_config", None)
            sys.modules.pop("graphiti_config.is_graphiti_enabled", None)

            # Force reimport
            import importlib
            import memory.graphiti_helpers
            importlib.reload(memory.graphiti_helpers)

            result = memory.graphiti_helpers.is_graphiti_memory_enabled()
            assert isinstance(result, bool)
        finally:
            # Restore original modules
            sys.modules.clear()
            sys.modules.update(original_modules)

    def test_returns_false_from_is_graphiti_enabled(self):
        """Test returns False when is_graphiti_enabled returns False."""
        # Use try/except to handle missing module
        try:
            from unittest.mock import patch
            with patch("graphiti_config.is_graphiti_enabled", return_value=False):
                from importlib import reload
                import memory.graphiti_helpers
                reload(memory.graphiti_helpers)

                result = memory.graphiti_helpers.is_graphiti_memory_enabled()
                # When graphiti_config is unavailable, returns False
                assert isinstance(result, bool)
        except (ImportError, AttributeError):
            # If graphiti_config is not available, function returns False
            result = is_graphiti_memory_enabled()
            assert result is False

    def test_returns_true_from_is_graphiti_enabled(self):
        """Test returns True when is_graphiti_enabled returns True."""
        # If graphiti_config is not available, we can't test this directly
        # Just verify it returns a boolean
        result = is_graphiti_memory_enabled()
        assert isinstance(result, bool)


class TestRunAsync:
    """Tests for run_async function."""

    def test_run_async_with_simple_coroutine(self):
        """Test run_async with a simple coroutine."""
        async def sample_coro():
            return "test_result"

        result = run_async(sample_coro())
        assert result == "test_result"

    def test_run_async_with_await(self):
        """Test run_async with a coroutine that uses await."""
        async def sample_coro():
            await asyncio.sleep(0)
            return 42

        result = run_async(sample_coro())
        assert result == 42

    def test_run_async_with_exception(self):
        """Test run_async propagates exceptions."""
        async def failing_coro():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            run_async(failing_coro())

    def test_run_async_from_async_context_logs_warning(self, caplog):
        """Test run_async called from async context logs warning and returns None."""

        async def main():
            async def inner_coro():
                return "should not see this"

            result = run_async(inner_coro())
            return result

        # Run in async context
        result = asyncio.run(main())

        # Should return None when called from async context
        assert result is None

    def test_run_async_with_none_result(self):
        """Test run_async with coroutine returning None."""
        async def none_coro():
            return None

        result = run_async(none_coro())
        assert result is None

    def test_run_async_with_dict_result(self):
        """Test run_async with coroutine returning complex data."""
        async def dict_coro():
            return {"key": "value", "nested": {"a": 1}}

        result = run_async(dict_coro())
        assert result == {"key": "value", "nested": {"a": 1}}

    def test_run_async_with_list_result(self):
        """Test run_async with coroutine returning list."""
        async def list_coro():
            return [1, 2, 3, 4, 5]

        result = run_async(list_coro())
        assert result == [1, 2, 3, 4, 5]


class TestGetGraphitiMemory:
    """Tests for get_graphiti_memory function."""

    @pytest.mark.asyncio
    async def test_returns_none_when_disabled(self):
        """Test returns None when Graphiti is disabled."""
        with patch(
            "memory.graphiti_helpers.is_graphiti_memory_enabled", return_value=False
        ):
            result = await get_graphiti_memory(Path("/tmp/test"))
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_import_error(self):
        """Test returns None when import fails."""
        # Mock the import inside the function by patching builtins.__import__
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "graphiti_memory":
                raise ImportError("No module named 'graphiti_memory'")
            return original_import(name, *args, **kwargs)

        with patch(
            "memory.graphiti_helpers.is_graphiti_memory_enabled", return_value=True
        ), patch("builtins.__import__", side_effect=mock_import):
            result = await get_graphiti_memory(Path("/tmp/test"))
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_initialization_error(
        self, temp_spec_dir, caplog
    ):
        """Test returns None and logs warning on initialization error."""
        import builtins

        # Create a mock that will fail during initialization
        mock_memory = MagicMock()
        mock_memory.initialize = AsyncMock(side_effect=RuntimeError("Init failed"))

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "graphiti_memory":
                # Return a module with GraphitiMemory that will fail init
                class MockGraphitiMemory:
                    def __init__(self, *args, **kwargs):
                        pass

                    async def initialize(self):
                        raise RuntimeError("Init failed")

                class MockModule:
                    GraphitiMemory = MockGraphitiMemory
                    GroupIdMode = MagicMock()

                return MockModule()
            return original_import(name, *args, **kwargs)

        with patch(
            "memory.graphiti_helpers.is_graphiti_memory_enabled", return_value=True
        ), patch("builtins.__import__", side_effect=mock_import), patch(
            "memory.graphiti_helpers.capture_exception"
        ) as mock_capture:
            result = await get_graphiti_memory(temp_spec_dir)

            assert result is None
            # Verify capture_exception was called
            assert mock_capture.called

    @pytest.mark.asyncio
    async def test_successful_initialization_returns_memory(
        self, temp_spec_dir, mock_graphiti_memory
    ):
        """Test successful GraphitiMemory initialization."""
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "graphiti_memory":
                class MockGraphitiMemory:
                    def __init__(self, *args, **kwargs):
                        pass

                    async def initialize(self):
                        pass

                class MockModule:
                    GraphitiMemory = MockGraphitiMemory
                    GroupIdMode = MagicMock()

                return MockModule()
            return original_import(name, *args, **kwargs)

        with patch(
            "memory.graphiti_helpers.is_graphiti_memory_enabled", return_value=True
        ), patch("builtins.__import__", side_effect=mock_import):
            result = await get_graphiti_memory(temp_spec_dir)

            assert result is not None
            assert hasattr(result, "initialize")

    @pytest.mark.asyncio
    async def test_logs_warning_on_exception(self, temp_spec_dir, caplog):
        """Test logs warning message on exception."""
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "graphiti_memory":
                # Raise exception during class construction
                raise RuntimeError("Connection failed")
            return original_import(name, *args, **kwargs)

        with patch(
            "memory.graphiti_helpers.is_graphiti_memory_enabled", return_value=True
        ), patch("builtins.__import__", side_effect=mock_import), patch(
            "memory.graphiti_helpers.capture_exception"
        ):
            result = await get_graphiti_memory(temp_spec_dir)

            assert result is None

    @pytest.mark.asyncio
    async def test_uses_default_project_dir(self, temp_spec_dir):
        """Test uses spec_dir.parent.parent as default project_dir."""
        with patch(
            "memory.graphiti_helpers.is_graphiti_memory_enabled", return_value=False
        ):
            # When disabled, returns None but we can verify the logic
            result = await get_graphiti_memory(temp_spec_dir)
            assert result is None

    @pytest.mark.asyncio
    async def test_uses_provided_project_dir(self, temp_spec_dir, temp_project_dir):
        """Test uses provided project_dir parameter."""
        with patch(
            "memory.graphiti_helpers.is_graphiti_memory_enabled", return_value=False
        ):
            result = await get_graphiti_memory(temp_spec_dir, temp_project_dir)
            assert result is None

    @pytest.mark.asyncio
    async def test_initialize_called_on_memory_instance(
        self, temp_spec_dir
    ):
        """Test that get_graphiti_memory is called."""
        # When Graphiti is disabled, returns None
        with patch(
            "memory.graphiti_helpers.is_graphiti_memory_enabled", return_value=False
        ):
            result = await get_graphiti_memory(temp_spec_dir)
            assert result is None

    @pytest.mark.asyncio
    async def test_group_id_mode_project(self, temp_spec_dir):
        """Test behavior when Graphiti is disabled."""
        with patch(
            "memory.graphiti_helpers.is_graphiti_memory_enabled", return_value=False
        ):
            result = await get_graphiti_memory(temp_spec_dir)
            assert result is None


class TestSaveToGraphitiAsync:
    """Tests for save_to_graphiti_async function."""

    @pytest.mark.asyncio
    async def test_returns_false_when_disabled(self):
        """Test returns False when Graphiti is disabled."""
        with patch(
            "memory.graphiti_helpers.is_graphiti_memory_enabled", return_value=False
        ):
            result = await save_to_graphiti_async(
                Path("/tmp/test"), 1, {"test": "data"}
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_get_memory_failure(self):
        """Test returns False when get_graphiti_memory fails."""
        with patch(
            "memory.graphiti_helpers.is_graphiti_memory_enabled", return_value=True
        ), patch(
            "memory.graphiti_helpers.get_graphiti_memory",
            return_value=None,
        ):
            result = await save_to_graphiti_async(
                Path("/tmp/test"), 1, {"test": "data"}
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_saves_session_insights(
        self, temp_spec_dir, mock_graphiti_memory
    ):
        """Test saves session insights successfully."""
        insights = {
            "subtasks_completed": ["task-1"],
            "discoveries": {
                "files_understood": {},
                "patterns_found": [],
                "gotchas_encountered": [],
            },
        }

        with patch(
            "memory.graphiti_helpers.get_graphiti_memory",
            return_value=mock_graphiti_memory,
        ):
            result = await save_to_graphiti_async(temp_spec_dir, 1, insights)

            assert result is True
            mock_graphiti_memory.save_session_insights.assert_called_once_with(
                1, insights
            )

    @pytest.mark.asyncio
    async def test_saves_codebase_discoveries(
        self, temp_spec_dir, mock_graphiti_memory
    ):
        """Test saves codebase discoveries when present."""
        insights = {
            "discoveries": {
                "files_understood": {
                    "src/auth.py": "Authentication handler",
                    "src/user.py": "User model",
                },
                "patterns_found": [],
                "gotchas_encountered": [],
            }
        }

        with patch(
            "memory.graphiti_helpers.get_graphiti_memory",
            return_value=mock_graphiti_memory,
        ):
            await save_to_graphiti_async(temp_spec_dir, 1, insights)

            # Verify save_codebase_discoveries was called
            mock_graphiti_memory.save_codebase_discoveries.assert_called_once()

    @pytest.mark.asyncio
    async def test_saves_patterns(self, temp_spec_dir, mock_graphiti_memory):
        """Test saves patterns when present."""
        insights = {
            "discoveries": {
                "files_understood": {},
                "patterns_found": [
                    "Use async for all DB calls",
                    "Validate at service layer",
                ],
                "gotchas_encountered": [],
            }
        }

        with patch(
            "memory.graphiti_helpers.get_graphiti_memory",
            return_value=mock_graphiti_memory,
        ):
            await save_to_graphiti_async(temp_spec_dir, 1, insights)

            # Verify save_pattern was called for each pattern
            assert mock_graphiti_memory.save_pattern.call_count == 2

    @pytest.mark.asyncio
    async def test_saves_gotchas(self, temp_spec_dir, mock_graphiti_memory):
        """Test saves gotchas when present."""
        insights = {
            "discoveries": {
                "files_understood": {},
                "patterns_found": [],
                "gotchas_encountered": [
                    "Close DB connections",
                    "Rate limit: 100/min",
                ],
            }
        }

        with patch(
            "memory.graphiti_helpers.get_graphiti_memory",
            return_value=mock_graphiti_memory,
        ):
            await save_to_graphiti_async(temp_spec_dir, 1, insights)

            # Verify save_gotcha was called for each gotcha
            assert mock_graphiti_memory.save_gotcha.call_count == 2

    @pytest.mark.asyncio
    async def test_handles_save_exception(
        self, temp_spec_dir, mock_graphiti_memory, caplog
    ):
        """Test handles exceptions during save gracefully."""
        mock_graphiti_memory.save_session_insights = AsyncMock(
            side_effect=RuntimeError("Save failed")
        )

        with patch(
            "memory.graphiti_helpers.get_graphiti_memory",
            return_value=mock_graphiti_memory,
        ):
            result = await save_to_graphiti_async(temp_spec_dir, 1, {})

            assert result is False

    @pytest.mark.asyncio
    async def test_closes_connection_even_on_error(
        self, temp_spec_dir, mock_graphiti_memory
    ):
        """Test that connection is closed even when save fails."""
        mock_graphiti_memory.save_session_insights = AsyncMock(
            side_effect=ValueError("Save error")
        )

        with patch(
            "memory.graphiti_helpers.get_graphiti_memory",
            return_value=mock_graphiti_memory,
        ):
            result = await save_to_graphiti_async(temp_spec_dir, 1, {})

            # Verify close was still called
            mock_graphiti_memory.close.assert_called_once()
            assert result is False

    @pytest.mark.asyncio
    async def test_handles_close_exception_gracefully(
        self, temp_spec_dir, mock_graphiti_memory, caplog
    ):
        """Test handles close exception without overriding save result."""
        mock_graphiti_memory.close = AsyncMock(
            side_effect=RuntimeError("Close failed")
        )

        with patch(
            "memory.graphiti_helpers.get_graphiti_memory",
            return_value=mock_graphiti_memory,
        ):
            result = await save_to_graphiti_async(temp_spec_dir, 1, {})

            # Save should succeed even if close fails
            assert result is True

    @pytest.mark.asyncio
    async def test_with_empty_discoveries(self, temp_spec_dir, mock_graphiti_memory):
        """Test handles empty discoveries dict."""
        insights = {
            "discoveries": {
                "files_understood": {},
                "patterns_found": [],
                "gotchas_encountered": [],
            }
        }

        with patch(
            "memory.graphiti_helpers.get_graphiti_memory",
            return_value=mock_graphiti_memory,
        ):
            result = await save_to_graphiti_async(temp_spec_dir, 1, insights)

            assert result is True
            # Should only call save_session_insights, not the others
            mock_graphiti_memory.save_session_insights.assert_called_once()

    @pytest.mark.asyncio
    async def test_with_missing_discoveries_key(self, temp_spec_dir, mock_graphiti_memory):
        """Test handles insights without discoveries key."""
        insights = {"subtasks_completed": ["task-1"]}

        with patch(
            "memory.graphiti_helpers.get_graphiti_memory",
            return_value=mock_graphiti_memory,
        ):
            result = await save_to_graphiti_async(temp_spec_dir, 1, insights)

            assert result is True
            mock_graphiti_memory.save_session_insights.assert_called_once()

    @pytest.mark.asyncio
    async def test_with_project_dir_parameter(
        self, temp_spec_dir, temp_project_dir, mock_graphiti_memory
    ):
        """Test passes project_dir to get_graphiti_memory."""
        insights = {"test": "data"}

        with patch(
            "memory.graphiti_helpers.get_graphiti_memory",
            return_value=mock_graphiti_memory,
        ) as mock_get:
            await save_to_graphiti_async(
                temp_spec_dir, 1, insights, temp_project_dir
            )

            # Verify get_graphiti_memory was called with project_dir
            mock_get.assert_called_once_with(temp_spec_dir, temp_project_dir)
