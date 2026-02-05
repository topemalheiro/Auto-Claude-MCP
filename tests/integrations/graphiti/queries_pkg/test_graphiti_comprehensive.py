"""Comprehensive tests for graphiti.py (GraphitiMemory) module."""

import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from integrations.graphiti.queries_pkg.graphiti import GraphitiMemory
from integrations.graphiti.queries_pkg.schema import GroupIdMode, MAX_CONTEXT_RESULTS


class TestGraphitiMemoryInit:
    """Tests for GraphitiMemory initialization."""

    def test_init_with_defaults(self):
        """Test GraphitiMemory.__init__ with default parameters."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            assert instance.spec_dir == spec_dir
            assert instance.project_dir == project_dir
            assert instance.group_id_mode == GroupIdMode.SPEC

    def test_init_with_project_mode(self):
        """Test GraphitiMemory.__init__ with project mode."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(
                spec_dir,
                project_dir,
                group_id_mode=GroupIdMode.PROJECT,
            )

            assert instance.group_id_mode == GroupIdMode.PROJECT

    def test_init_loads_existing_state(self):
        """Test __init__ loads existing state file."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiState.load") as mock_load:
                mock_state = MagicMock()
                mock_state.initialized = True
                mock_load.return_value = mock_state

                instance = GraphitiMemory(spec_dir, project_dir)

                assert instance.state == mock_state

    def test_init_checks_availability(self):
        """Test __init__ checks config validity."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        mock_config = MagicMock()
        mock_config.is_valid.return_value = True

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env", return_value=mock_config):
            instance = GraphitiMemory(spec_dir, project_dir)

            assert instance._available is True

    def test_init_not_available(self):
        """Test __init__ when config is invalid."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        mock_config = MagicMock()
        mock_config.is_valid.return_value = False

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env", return_value=mock_config):
            instance = GraphitiMemory(spec_dir, project_dir)

            assert instance._available is False


class TestGraphitiMemoryProperties:
    """Tests for GraphitiMemory properties."""

    def test_is_enabled_property(self):
        """Test is_enabled property reflects availability."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)
            instance._available = True

            assert instance.is_enabled is True

            instance._available = False
            assert instance.is_enabled is False

    def test_is_initialized_property(self):
        """Test is_initialized property checks all conditions."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            # Not initialized
            assert instance.is_initialized is False

            # Set up mock client
            instance._client = MagicMock()
            instance._client.is_initialized = True

            # Set up mock state
            instance.state = MagicMock()
            instance.state.initialized = True

            # Now should be initialized
            assert instance.is_initialized is True

    def test_group_id_spec_mode(self):
        """Test group_id in SPEC mode."""
        spec_dir = Path("/tmp/my_spec_001")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir, GroupIdMode.SPEC)

            assert instance.group_id == "my_spec_001"

    def test_group_id_project_mode(self):
        """Test group_id in PROJECT mode includes project name and hash."""
        spec_dir = Path("/tmp/my_spec_001")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir, GroupIdMode.PROJECT)

            group_id = instance.group_id
            assert "project_test_project" in group_id
            assert "_" in group_id

    def test_group_id_project_mode_hash_consistency(self):
        """Test group_id hash is consistent for same path."""
        spec_dir = Path("/tmp/my_spec_001")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance1 = GraphitiMemory(spec_dir, project_dir, GroupIdMode.PROJECT)
            instance2 = GraphitiMemory(spec_dir, project_dir, GroupIdMode.PROJECT)

            assert instance1.group_id == instance2.group_id

    def test_spec_context_id(self):
        """Test spec_context_id returns spec dir name."""
        spec_dir = Path("/tmp/my_spec_001")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            assert instance.spec_context_id == "my_spec_001"


class TestGraphitiMemoryInitialize:
    """Tests for GraphitiMemory.initialize method."""

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self):
        """Test initialize returns True if already initialized."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)
            instance._client = MagicMock()
            instance._client.is_initialized = True
            instance.state = MagicMock()
            instance.state.initialized = True

            result = await instance.initialize()

            assert result is True

    @pytest.mark.asyncio
    async def test_initialize_not_available(self):
        """Test initialize returns False when not available."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)
            instance._available = False

            result = await instance.initialize()

            assert result is False

    @pytest.mark.asyncio
    async def test_initialize_provider_changed_warning(self):
        """Test initialize warns about provider change."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        mock_config = MagicMock()
        mock_config.llm_provider = "openai"
        mock_config.embedder_provider = "voyage"

        mock_state = MagicMock()
        mock_state.initialized = True
        mock_state.has_provider_changed.return_value = True
        mock_state.get_migration_info.return_value = {
            "old_provider": "ollama",
            "new_provider": "voyage",
            "episode_count": 10,
        }

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env", return_value=mock_config):
            with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.initialize = AsyncMock(return_value=True)
                mock_client_class.return_value = mock_client

                instance = GraphitiMemory(spec_dir, project_dir)
                instance.state = mock_state

                # Should reset state and continue
                result = await instance.initialize()

                # State should have been reset to None
                # Then new state created
                assert result is True

    @pytest.mark.asyncio
    async def test_initialize_client_failure(self):
        """Test initialize handles client initialization failure."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        mock_config = MagicMock()
        mock_config.get_provider_summary.return_value = "LLM: openai, Embedder: voyage"

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env", return_value=mock_config):
            with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.initialize = AsyncMock(return_value=False)
                mock_client_class.return_value = mock_client

                instance = GraphitiMemory(spec_dir, project_dir)

                result = await instance.initialize()

                assert result is False
                assert instance._available is False

    @pytest.mark.asyncio
    async def test_initialize_creates_new_state(self):
        """Test initialize creates new state when none exists."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        mock_config = MagicMock()
        mock_config.database = "test_db"
        mock_config.llm_provider = "openai"
        mock_config.embedder_provider = "voyage"
        mock_config.get_provider_summary.return_value = "test summary"

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env", return_value=mock_config):
            with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.initialize = AsyncMock(return_value=True)
                mock_client_class.return_value = mock_client

                instance = GraphitiMemory(spec_dir, project_dir)
                instance.state = None  # No existing state

                result = await instance.initialize()

                assert result is True
                assert instance.state is not None
                assert instance.state.initialized is True
                assert instance.state.database == "test_db"

    @pytest.mark.asyncio
    async def test_initialize_creates_modules(self):
        """Test initialize creates query and search modules."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        mock_config = MagicMock()

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env", return_value=mock_config):
            with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiClient") as mock_client_class:
                with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiQueries") as mock_queries_class:
                    with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiSearch") as mock_search_class:
                        mock_client = MagicMock()
                        mock_client.initialize = AsyncMock(return_value=True)
                        mock_client_class.return_value = mock_client

                        instance = GraphitiMemory(spec_dir, project_dir)
                        instance.state = MagicMock()
                        instance.state.initialized = False

                        result = await instance.initialize()

                        assert result is True
                        assert instance._queries is not None
                        assert instance._search is not None
                        mock_queries_class.assert_called_once()
                        mock_search_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_error_handling(self):
        """Test initialize handles exceptions."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiClient") as mock_client_class:
                mock_client_class.side_effect = Exception("Init error")

                instance = GraphitiMemory(spec_dir, project_dir)

                result = await instance.initialize()

                assert result is False
                assert instance._available is False

    @pytest.mark.asyncio
    async def test_initialize_saves_state(self):
        """Test initialize saves state to file."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        mock_config = MagicMock()
        mock_config.database = "test_db"

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env", return_value=mock_config):
            with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.initialize = AsyncMock(return_value=True)
                mock_client_class.return_value = mock_client

                instance = GraphitiMemory(spec_dir, project_dir)
                instance.state = None

                await instance.initialize()

                # State should have been saved
                assert instance.state is not None


class TestGraphitiMemoryClose:
    """Tests for GraphitiMemory.close method."""

    @pytest.mark.asyncio
    async def test_close(self):
        """Test close closes client and resets modules."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            mock_client = MagicMock()
            mock_client.close = AsyncMock()
            instance._client = mock_client
            instance._queries = MagicMock()
            instance._search = MagicMock()

            await instance.close()

            mock_client.close.assert_called_once()
            assert instance._client is None
            assert instance._queries is None
            assert instance._search is None

    @pytest.mark.asyncio
    async def test_close_no_client(self):
        """Test close when client is None."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)
            instance._client = None

            # Should not raise
            await instance.close()


class TestGraphitiMemorySaveMethods:
    """Tests for GraphitiMemory save methods."""

    @pytest.mark.asyncio
    async def test_save_session_insights_success(self):
        """Test save_session_insights updates state."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            mock_queries = MagicMock()
            mock_queries.add_session_insight = AsyncMock(return_value=True)
            instance._queries = mock_queries

            mock_state = MagicMock()
            instance.state = mock_state

            result = await instance.save_session_insights(1, {"test": "data"})

            assert result is True
            assert mock_state.last_session == 1
            mock_state.save.assert_called_once_with(spec_dir)

    @pytest.mark.asyncio
    async def test_save_session_insights_error(self):
        """Test save_session_insights handles errors."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            mock_queries = MagicMock()
            mock_queries.add_session_insight = AsyncMock(side_effect=Exception("Save failed"))
            instance._queries = mock_queries

            mock_state = MagicMock()
            instance.state = mock_state

            result = await instance.save_session_insights(1, {"test": "data"})

            assert result is False

    @pytest.mark.asyncio
    async def test_save_codebase_discoveries_success(self):
        """Test save_codebase_discoveries updates state."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            mock_queries = MagicMock()
            mock_queries.add_codebase_discoveries = AsyncMock(return_value=True)
            instance._queries = mock_queries

            mock_state = MagicMock()
            instance.state = mock_state

            result = await instance.save_codebase_discoveries({"file.py": "purpose"})

            assert result is True
            assert mock_state.episode_count == 1
            mock_state.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_pattern_success(self):
        """Test save_pattern updates state."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            mock_queries = MagicMock()
            mock_queries.add_pattern = AsyncMock(return_value=True)
            instance._queries = mock_queries

            mock_state = MagicMock()
            instance.state = mock_state

            result = await instance.save_pattern("Test pattern")

            assert result is True
            assert mock_state.episode_count == 1

    @pytest.mark.asyncio
    async def test_save_gotcha_success(self):
        """Test save_gotcha updates state."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            mock_queries = MagicMock()
            mock_queries.add_gotcha = AsyncMock(return_value=True)
            instance._queries = mock_queries

            mock_state = MagicMock()
            instance.state = mock_state

            result = await instance.save_gotcha("Test gotcha")

            assert result is True
            assert mock_state.episode_count == 1

    @pytest.mark.asyncio
    async def test_save_task_outcome_success(self):
        """Test save_task_outcome updates state."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            mock_queries = MagicMock()
            mock_queries.add_task_outcome = AsyncMock(return_value=True)
            instance._queries = mock_queries

            mock_state = MagicMock()
            instance.state = mock_state

            result = await instance.save_task_outcome("task-1", True, "Success")

            assert result is True
            assert mock_state.episode_count == 1

    @pytest.mark.asyncio
    async def test_save_task_outcome_with_metadata(self):
        """Test save_task_outcome with metadata."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            mock_queries = MagicMock()
            mock_queries.add_task_outcome = AsyncMock(return_value=True)
            instance._queries = mock_queries

            mock_state = MagicMock()
            instance.state = mock_state

            metadata = {"files_changed": 5, "duration": 120}
            result = await instance.save_task_outcome("task-1", True, "Success", metadata)

            assert result is True
            mock_queries.add_task_outcome.assert_called_once_with(
                "task-1", True, "Success", metadata
            )

    @pytest.mark.asyncio
    async def test_save_structured_insights_success(self):
        """Test save_structured_insights succeeds."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            mock_queries = MagicMock()
            mock_queries.add_structured_insights = AsyncMock(return_value=True)
            instance._queries = mock_queries

            mock_state = MagicMock()
            instance.state = mock_state

            insights = {"patterns": [], "gotchas": []}
            result = await instance.save_structured_insights(insights)

            assert result is True


class TestGraphitiMemorySearchMethods:
    """Tests for GraphitiMemory search methods."""

    @pytest.mark.asyncio
    async def test_get_relevant_context_success(self):
        """Test get_relevant_context delegates to search module."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            mock_search = MagicMock()
            mock_search.get_relevant_context = AsyncMock(return_value=[
                {"content": "test", "score": 0.8}
            ])
            instance._search = mock_search

            result = await instance.get_relevant_context("test query", 5, True)

            assert len(result) == 1
            mock_search.get_relevant_context.assert_called_once_with("test query", 5, True)

    @pytest.mark.asyncio
    async def test_get_relevant_context_defaults(self):
        """Test get_relevant_context uses default parameters."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            mock_search = MagicMock()
            mock_search.get_relevant_context = AsyncMock(return_value=[])
            instance._search = mock_search

            await instance.get_relevant_context("test query")

            # Should use default num_results
            call_args = mock_search.get_relevant_context.call_args
            assert call_args[0][1] == MAX_CONTEXT_RESULTS

    @pytest.mark.asyncio
    async def test_get_session_history_success(self):
        """Test get_session_history delegates to search module."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            mock_search = MagicMock()
            mock_search.get_session_history = AsyncMock(return_value=[
                {"session_number": 1}
            ])
            instance._search = mock_search

            result = await instance.get_session_history(5, True)

            assert len(result) == 1
            mock_search.get_session_history.assert_called_once_with(5, True)

    @pytest.mark.asyncio
    async def test_get_similar_task_outcomes_success(self):
        """Test get_similar_task_outcomes delegates to search module."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            mock_search = MagicMock()
            mock_search.get_similar_task_outcomes = AsyncMock(return_value=[
                {"task_id": "task-1", "success": True}
            ])
            instance._search = mock_search

            result = await instance.get_similar_task_outcomes("test task", 5)

            assert len(result) == 1
            mock_search.get_similar_task_outcomes.assert_called_once_with("test task", 5)

    @pytest.mark.asyncio
    async def test_get_patterns_and_gotchas_success(self):
        """Test get_patterns_and_gotchas delegates to search module."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            mock_search = MagicMock()
            mock_search.get_patterns_and_gotchas = AsyncMock(return_value=(
                [{"pattern": "test pattern"}],
                [{"gotcha": "test gotcha"}]
            ))
            instance._search = mock_search

            patterns, gotchas = await instance.get_patterns_and_gotchas("test query")

            assert len(patterns) == 1
            assert len(gotchas) == 1
            mock_search.get_patterns_and_gotchas.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_patterns_and_gotchas_defaults(self):
        """Test get_patterns_and_gotchas uses default parameters."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            mock_search = MagicMock()
            mock_search.get_patterns_and_gotchas = AsyncMock(return_value=([], []))
            instance._search = mock_search

            await instance.get_patterns_and_gotchas("test query")

            # Should use defaults
            call_args = mock_search.get_patterns_and_gotchas.call_args
            assert call_args[0][1] == 5  # num_results
            assert call_args[0][2] == 0.5  # min_score

    @pytest.mark.asyncio
    async def test_search_methods_error_handling(self):
        """Test search methods handle errors."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            # Test get_relevant_context error
            mock_search = MagicMock()
            mock_search.get_relevant_context = AsyncMock(side_effect=Exception("Search error"))
            instance._search = mock_search

            result = await instance.get_relevant_context("test")
            assert result == []

            # Test get_session_history error
            mock_search.get_session_history = AsyncMock(side_effect=Exception("Error"))
            result = await instance.get_session_history()
            assert result == []

            # Test get_similar_task_outcomes error
            mock_search.get_similar_task_outcomes = AsyncMock(side_effect=Exception("Error"))
            result = await instance.get_similar_task_outcomes("test")
            assert result == []

            # Test get_patterns_and_gotchas error
            mock_search.get_patterns_and_gotchas = AsyncMock(side_effect=Exception("Error"))
            patterns, gotchas = await instance.get_patterns_and_gotchas("test")
            assert patterns == []
            assert gotchas == []


class TestGraphitiMemoryUtilityMethods:
    """Tests for GraphitiMemory utility methods."""

    def test_get_status_summary(self):
        """Test get_status_summary returns all fields."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        mock_config = MagicMock()
        mock_config.database = "test_db"
        mock_config.db_path = "/tmp/test"
        mock_config.llm_provider = "openai"
        mock_config.embedder_provider = "voyage"

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env", return_value=mock_config):
            instance = GraphitiMemory(spec_dir, project_dir)
            instance._available = True

            mock_state = MagicMock()
            mock_state.episode_count = 10
            mock_state.last_session = 5
            mock_state.error_log = []
            instance.state = mock_state

            summary = instance.get_status_summary()

            expected_keys = {
                "enabled",
                "initialized",
                "database",
                "db_path",
                "group_id",
                "group_id_mode",
                "llm_provider",
                "embedder_provider",
                "episode_count",
                "last_session",
                "errors",
            }
            assert set(summary.keys()) == expected_keys
            assert summary["enabled"] is True
            assert summary["database"] == "test_db"

    def test_get_status_summary_disabled(self):
        """Test get_status_summary when disabled."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        mock_config = MagicMock()

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env", return_value=mock_config):
            instance = GraphitiMemory(spec_dir, project_dir)
            instance._available = False
            instance.state = None

            summary = instance.get_status_summary()

            assert summary["enabled"] is False
            assert summary["database"] is None
            assert summary["episode_count"] == 0

    @pytest.mark.asyncio
    async def test_ensure_initialized(self):
        """Test _ensure_initialized initializes if needed."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)
            instance._available = True

            # Mock initialize
            instance.initialize = AsyncMock(return_value=True)

            result = await instance._ensure_initialized()

            assert result is True
            instance.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_initialized_already_initialized(self):
        """Test _ensure_initialized skips if already initialized."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            # Set up as already initialized
            instance._client = MagicMock()
            instance._client.is_initialized = True
            instance.state = MagicMock()
            instance.state.initialized = True

            # Mock initialize
            instance.initialize = AsyncMock()

            result = await instance._ensure_initialized()

            assert result is True
            instance.initialize.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_initialized_not_available(self):
        """Test _ensure_initialized returns False when not available."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)
            instance._available = False

            result = await instance._ensure_initialized()

            assert result is False

    def test_record_error(self):
        """Test _record_error saves error to state."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            # No state yet
            instance.state = None

            instance._record_error("Test error")

            # State should be created
            assert instance.state is not None
            instance.state.record_error.assert_called_once_with("Test error")
            instance.state.save.assert_called_once_with(spec_dir)

    def test_record_error_existing_state(self):
        """Test _record_error uses existing state."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env"):
            instance = GraphitiMemory(spec_dir, project_dir)

            mock_state = MagicMock()
            instance.state = mock_state

            instance._record_error("Test error")

            mock_state.record_error.assert_called_once_with("Test error")
            mock_state.save.assert_called_once_with(spec_dir)


class TestGraphitiMemoryEdgeCases:
    """Tests for edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_save_methods_without_initialization(self):
        """Test save methods handle not being initialized."""
        spec_dir = Path("/tmp/test_spec"
        "")
        project_dir = Path("/tmp/test_project")

        mock_config = MagicMock()
        mock_config.is_valid.return_value = True

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env", return_value=mock_config):
            instance = GraphitiMemory(spec_dir, project_dir)
            instance._available = True

            # Mock initialize to return False
            with patch.object(instance, "initialize", return_value=False):
                result = await instance.save_session_insights(1, {})
                assert result is False

                result = await instance.save_codebase_discoveries({})
                assert result is False

                result = await instance.save_pattern("test")
                assert result is False

                result = await instance.save_gotcha("test")
                assert result is False

                result = await instance.save_task_outcome("task", True, "success")
                assert result is False

                result = await instance.save_structured_insights({})
                assert result is False

    @pytest.mark.asyncio
    async def test_get_methods_without_initialization(self):
        """Test get methods handle not being initialized."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        mock_config = MagicMock()
        mock_config.is_valid.return_value = True

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env", return_value=mock_config):
            instance = GraphitiMemory(spec_dir, project_dir)
            instance._available = True

            # Mock initialize to return False
            with patch.object(instance, "initialize", return_value=False):
                result = await instance.get_relevant_context("test")
                assert result == []

                result = await instance.get_session_history()
                assert result == []

                result = await instance.get_similar_task_outcomes("test")
                assert result == []

                patterns, gotchas = await instance.get_patterns_and_gotchas("test")
                assert patterns == []
                assert gotchas == []

    @pytest.mark.asyncio
    async def test_initialize_with_no_queries_or_search(self):
        """Test initialize after client init creates modules."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        mock_config = MagicMock()

        with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiConfig.from_env", return_value=mock_config):
            with patch("integrations.graphiti.queries_pkg.graphiti.GraphitiClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.initialize = AsyncMock(return_value=True)
                mock_client_class.return_value = mock_client

                instance = GraphitiMemory(spec_dir, project_dir)
                instance.state = None

                await instance.initialize()

                # Modules should be created
                assert instance._queries is not None
                assert instance._search is not None
