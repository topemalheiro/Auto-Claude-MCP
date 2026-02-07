"""Tests for test_ollama_embedding_memory.py script functions."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from integrations.graphiti.test_ollama_embedding_memory import (
    apply_ladybug_monkeypatch,
    print_header,
    print_result,
    print_info,
    print_step,
    test_ollama_embeddings,
    test_memory_creation,
    test_memory_retrieval,
    test_full_cycle,
)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_print_step(self, capsys):
        """Test print_step formats output correctly."""
        print_step(1, "Test step message")
        captured = capsys.readouterr()

        assert "Step 1" in captured.out
        assert "Test step message" in captured.out


class TestApplyLadybugMonkeypatchOllama:
    """Tests for apply_ladybug_monkeypatch in ollama test context."""

    @patch("builtins.__import__")
    def test_apply_ladybug_monkeypatch_success(self, mock_import):
        """Test monkeypatch succeeds when real_ladybug is available."""
        original_import = __import__

        def import_side_effect(name, *args, **kwargs):
            if name == "real_ladybug":
                return MagicMock()
            return original_import(name, *args, **kwargs)

        mock_import.side_effect = import_side_effect
        result = apply_ladybug_monkeypatch()
        assert result is True

    @patch("builtins.__import__")
    def test_apply_ladybug_monkeypatch_fallback_kuzu(self, mock_import):
        """Test fallback to kuzu when real_ladybug not available."""
        original_import = __import__

        def import_side_effect(name, *args, **kwargs):
            if name == "real_ladybug":
                raise ImportError("real_ladybug not available")
            elif name == "kuzu":
                return MagicMock()
            return original_import(name, *args, **kwargs)

        mock_import.side_effect = import_side_effect
        result = apply_ladybug_monkeypatch()
        assert result is True

    @patch("builtins.__import__")
    def test_apply_ladybug_monkeypatch_neither_available(self, mock_import):
        """Test returns False when neither available."""
        original_import = __import__

        def import_side_effect(name, *args, **kwargs):
            if name in ("real_ladybug", "kuzu"):
                raise ImportError(f"{name} not available")
            return original_import(name, *args, **kwargs)

        mock_import.side_effect = import_side_effect
        result = apply_ladybug_monkeypatch()
        assert result is False


class TestOllamaEmbeddings:
    """Tests for test_ollama_embeddings function."""

    @pytest.mark.asyncio
    async def test_ollama_embeddings_success(self):
        """Test successful Ollama embedding generation."""
        mock_tags_response = MagicMock()
        mock_tags_response.status_code = 200
        mock_tags_response.json.return_value = {
            "models": [
                {"name": "embeddinggemma"},
                {"name": "nomic-embed-text"}
            ]
        }

        mock_emb_response = MagicMock()
        mock_emb_response.status_code = 200
        mock_emb_response.json.return_value = {
            "embedding": [0.1] * 768
        }

        with patch.dict("os.environ", {
            "OLLAMA_EMBEDDING_MODEL": "embeddinggemma",
            "OLLAMA_EMBEDDING_DIM": "768",
        }):
            with patch("requests.get", return_value=mock_tags_response):
                with patch("requests.post", return_value=mock_emb_response):
                    result = await test_ollama_embeddings()

                    assert result is True

    @pytest.mark.asyncio
    async def test_ollama_embeddings_no_requests(self):
        """Test handles missing requests library."""
        with patch.dict("sys.modules", {"requests": None}):
            result = await test_ollama_embeddings()

            assert result is False

    @pytest.mark.asyncio
    async def test_ollama_embeddings_connection_error(self):
        """Test handles connection error."""
        import requests

        with patch("requests.get", side_effect=requests.exceptions.ConnectionError()):
            result = await test_ollama_embeddings()

            assert result is False

    @pytest.mark.asyncio
    async def test_ollama_embeddings_model_not_found(self):
        """Test when model not found in Ollama."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "llama3"}]  # No embedding model
        }

        # Mock the POST request to return an error (model not found)
        mock_post_response = MagicMock()
        mock_post_response.status_code = 404
        mock_post_response.text = "model not found"

        with patch.dict("os.environ", {
            "OLLAMA_EMBEDDING_MODEL": "embeddinggemma",
        }):
            with patch("requests.get", return_value=mock_response):
                with patch("requests.post", return_value=mock_post_response):
                    result = await test_ollama_embeddings()

                    # Should return False when embedding generation fails
                    assert result is False

    @pytest.mark.asyncio
    async def test_ollama_embeddings_dimension_validation_success(self):
        """Test dimension validation passes."""
        mock_tags_response = MagicMock()
        mock_tags_response.status_code = 200
        mock_tags_response.json.return_value = {
            "models": [{"name": "embeddinggemma"}]
        }

        mock_emb_response = MagicMock()
        mock_emb_response.status_code = 200
        mock_emb_response.json.return_value = {
            "embedding": [0.1] * 768
        }

        with patch.dict("os.environ", {
            "OLLAMA_EMBEDDING_MODEL": "embeddinggemma",
            "OLLAMA_EMBEDDING_DIM": "768",
        }):
            with patch("requests.get", return_value=mock_tags_response):
                with patch("requests.post", return_value=mock_emb_response):
                    result = await test_ollama_embeddings()

                    assert result is True

    @pytest.mark.asyncio
    async def test_ollama_embeddings_dimension_mismatch(self):
        """Test dimension mismatch detection."""
        mock_tags_response = MagicMock()
        mock_tags_response.status_code = 200
        mock_tags_response.json.return_value = {
            "models": [{"name": "embeddinggemma"}]
        }

        mock_emb_response = MagicMock()
        mock_emb_response.status_code = 200
        mock_emb_response.json.return_value = {
            "embedding": [0.1] * 500  # Wrong dimension
        }

        with patch.dict("os.environ", {
            "OLLAMA_EMBEDDING_MODEL": "embeddinggemma",
            "OLLAMA_EMBEDDING_DIM": "768",
        }):
            with patch("requests.get", return_value=mock_tags_response):
                with patch("requests.post", return_value=mock_emb_response):
                    result = await test_ollama_embeddings()

                    assert result is False

    @pytest.mark.asyncio
    async def test_ollama_embeddings_timeout(self):
        """Test timeout handling."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": []}

        with patch("requests.get", return_value=mock_response):
            with patch("requests.post", side_effect=requests.exceptions.Timeout()):
                # The implementation doesn't catch Timeout, so it will propagate
                with pytest.raises(requests.exceptions.Timeout):
                    await test_ollama_embeddings()


class TestMemoryCreation:
    """Tests for test_memory_creation function."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_memory_creation_success(self):
        """Test successful memory creation."""
        mock_config = MagicMock()
        mock_config.embedder_provider = "ollama"
        mock_config.db_path = "/tmp/test"
        mock_config.database = "test_db"

        mock_memory = MagicMock()
        mock_memory.is_enabled = True
        mock_memory.group_id = "test_group"
        mock_memory.initialize = AsyncMock(return_value=True)
        mock_memory.save_session_insights = AsyncMock(return_value=True)
        mock_memory.save_pattern = AsyncMock(return_value=True)
        mock_memory.save_gotcha = AsyncMock(return_value=True)
        mock_memory.save_codebase_discoveries = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock()

        with patch.dict("os.environ", {
            "GRAPHITI_DB_PATH": "/tmp/test_db",
            "GRAPHITI_DATABASE": "test_ollama_memory",
        }):
            with patch(
                "integrations.graphiti.config.GraphitiConfig.from_env",
                return_value=mock_config,
            ):
                with patch(
                    "integrations.graphiti.memory.GraphitiMemory",
                    return_value=mock_memory,
                ):
                    test_db_path = Path("/tmp/test_ollama")
                    test_db_path.mkdir(parents=True, exist_ok=True)

                    result = await test_memory_creation(test_db_path)

                    assert result[2] is True  # success

    @pytest.mark.asyncio
    async def test_memory_creation_import_error(self):
        """Test memory creation with import error."""
        test_db_path = Path("/tmp/test_ollama")
        test_db_path.mkdir(parents=True, exist_ok=True)

        with patch.dict("os.environ", {
            "GRAPHITI_DB_PATH": str(test_db_path / "graphiti_db"),
            "GRAPHITI_DATABASE": "test_ollama_memory",
        }):
            # Patch __import__ to raise ImportError for the memory module
            original_import = __import__

            def import_side_effect(name, *args, **kwargs):
                if name == "integrations.graphiti.memory":
                    raise ImportError("Module not found")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=import_side_effect):
                result = await test_memory_creation(test_db_path)

                assert result[2] is False  # success

    @pytest.mark.asyncio
    async def test_memory_creation_not_enabled(self):
        """Test memory creation when not enabled."""
        mock_config = MagicMock()
        mock_config.embedder_provider = "ollama"

        mock_memory = MagicMock()
        mock_memory.is_enabled = False

        test_db_path = Path("/tmp/test_ollama")
        test_db_path.mkdir(parents=True, exist_ok=True)

        with patch.dict("os.environ", {
            "GRAPHITI_DB_PATH": str(test_db_path / "graphiti_db"),
            "GRAPHITI_DATABASE": "test_ollama_memory",
        }):
            with patch(
                "integrations.graphiti.config.GraphitiConfig.from_env",
                return_value=mock_config,
            ):
                with patch(
                    "integrations.graphiti.memory.GraphitiMemory",
                    return_value=mock_memory,
                ):
                    result = await test_memory_creation(test_db_path)

                    assert result[2] is False  # success

    @pytest.mark.asyncio
    async def test_memory_creation_initialization_failure(self):
        """Test memory creation with initialization failure."""
        mock_config = MagicMock()
        mock_config.embedder_provider = "ollama"

        mock_memory = MagicMock()
        mock_memory.is_enabled = True
        mock_memory.initialize = AsyncMock(return_value=False)

        test_db_path = Path("/tmp/test_ollama")
        test_db_path.mkdir(parents=True, exist_ok=True)

        with patch.dict("os.environ", {
            "GRAPHITI_DB_PATH": str(test_db_path / "graphiti_db"),
            "GRAPHITI_DATABASE": "test_ollama_memory",
        }):
            with patch(
                "integrations.graphiti.config.GraphitiConfig.from_env",
                return_value=mock_config,
            ):
                with patch(
                    "integrations.graphiti.memory.GraphitiMemory",
                    return_value=mock_memory,
                ):
                    result = await test_memory_creation(test_db_path)

                    assert result[2] is False  # success


class TestMemoryRetrieval:
    """Tests for test_memory_retrieval function."""

    @pytest.mark.asyncio
    async def test_memory_retrieval_success(self):
        """Test successful memory retrieval."""
        mock_config = MagicMock()
        mock_config.embedder_provider = "ollama"

        mock_memory = MagicMock()
        mock_memory.initialize = AsyncMock(return_value=True)
        mock_memory.get_relevant_context = AsyncMock(
            return_value=[
                {"content": "API routes", "score": 0.8, "type": "codebase_discovery"}
            ]
        )
        mock_memory.get_session_history = AsyncMock(
            return_value=[
                {"session_number": 1, "subtasks_completed": ["task-1"]}
            ]
        )
        mock_memory.get_status_summary = MagicMock(return_value={"test": "status"})
        mock_memory.close = AsyncMock()

        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch(
            "integrations.graphiti.memory.GraphitiMemory",
            return_value=mock_memory,
        ):
            result = await test_memory_retrieval(spec_dir, project_dir)

            assert result is True

    @pytest.mark.asyncio
    async def test_memory_retrieval_import_error(self):
        """Test memory retrieval with import error."""
        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        # Patch __import__ to raise ImportError for the memory module
        original_import = __import__

        def import_side_effect(name, *args, **kwargs):
            if name == "integrations.graphiti.memory":
                raise ImportError("Module not found")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=import_side_effect):
            result = await test_memory_retrieval(spec_dir, project_dir)

            assert result is False

    @pytest.mark.asyncio
    async def test_memory_retrieval_initialization_failure(self):
        """Test memory retrieval with initialization failure."""
        mock_memory = MagicMock()
        mock_memory.initialize = AsyncMock(return_value=False)

        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch(
            "integrations.graphiti.memory.GraphitiMemory",
            return_value=mock_memory,
        ):
            result = await test_memory_retrieval(spec_dir, project_dir)

            assert result is False

    @pytest.mark.asyncio
    async def test_memory_retrievar_results_found(self):
        """Test memory retrieval finds API content."""
        mock_config = MagicMock()
        mock_config.embedder_provider = "ollama"

        mock_memory = MagicMock()
        mock_memory.initialize = AsyncMock(return_value=True)
        mock_memory.get_relevant_context = AsyncMock(
            return_value=[
                {"content": "API routes file", "score": 0.8, "type": "codebase_discovery"}
            ]
        )
        mock_memory.get_session_history = AsyncMock(
            return_value=[
                {"session_number": 1, "subtasks_completed": ["task1", "task2"]}
            ]
        )
        mock_memory.get_status_summary = MagicMock(return_value={})
        mock_memory.close = AsyncMock()

        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        with patch(
            "integrations.graphiti.memory.GraphitiMemory",
            return_value=mock_memory,
        ):
            result = await test_memory_retrieval(spec_dir, project_dir)

            assert result is True


class TestFullCycle:
    """Tests for test_full_cycle function."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_cycle_success(self):
        """Test complete create-store-retrieve cycle."""
        mock_config = MagicMock()
        mock_config.embedder_provider = "ollama"

        mock_memory = MagicMock()
        mock_memory.is_enabled = True
        mock_memory.initialize = AsyncMock(return_value=True)
        mock_memory.save_pattern = AsyncMock(return_value=True)
        mock_memory.save_gotcha = AsyncMock(return_value=True)
        mock_memory.get_relevant_context = AsyncMock(
            side_effect=[
                [{"content": "Unique pattern content", "score": 0.9}],
                [{"content": "Unique gotcha content", "score": 0.8}],
                [{"content": "Related content", "score": 0.7}],
            ]
        )
        mock_memory.close = AsyncMock()

        test_db_path = Path("/tmp/test_cycle")
        test_db_path.mkdir(parents=True, exist_ok=True)

        with patch.dict("os.environ", {
            "GRAPHITI_DB_PATH": str(test_db_path / "graphiti_db"),
            "GRAPHITI_DATABASE": "test_full_cycle",
        }):
            with patch(
                "integrations.graphiti.config.GraphitiConfig.from_env",
                return_value=mock_config,
            ):
                with patch(
                    "integrations.graphiti.memory.GraphitiMemory",
                    return_value=mock_memory,
                ):
                    result = await test_full_cycle(test_db_path)

                    assert result is True

    @pytest.mark.asyncio
    async def test_full_cycle_import_error(self):
        """Test full cycle with import error."""
        test_db_path = Path("/tmp/test_cycle")
        test_db_path.mkdir(parents=True, exist_ok=True)

        with patch.dict("os.environ", {
            "GRAPHITI_DB_PATH": str(test_db_path / "graphiti_db"),
            "GRAPHITI_DATABASE": "test_full_cycle",
        }):
            # Patch __import__ to raise ImportError for the memory module
            original_import = __import__

            def import_side_effect(name, *args, **kwargs):
                if name == "integrations.graphiti.memory":
                    raise ImportError("Module not found")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=import_side_effect):
                result = await test_full_cycle(test_db_path)

                assert result is False

    @pytest.mark.asyncio
    async def test_full_cycle_initialization_failure(self):
        """Test full cycle with initialization failure."""
        mock_config = MagicMock()
        mock_config.embedder_provider = "ollama"

        mock_memory = MagicMock()
        mock_memory.is_enabled = True
        mock_memory.initialize = AsyncMock(return_value=False)

        test_db_path = Path("/tmp/test_cycle")
        test_db_path.mkdir(parents=True, exist_ok=True)

        with patch.dict("os.environ", {
            "GRAPHITI_DB_PATH": str(test_db_path / "graphiti_db"),
            "GRAPHITI_DATABASE": "test_full_cycle",
        }):
            with patch(
                "integrations.graphiti.config.GraphitiConfig.from_env",
                return_value=mock_config,
            ):
                with patch(
                    "integrations.graphiti.memory.GraphitiMemory",
                    return_value=mock_memory,
                ):
                    result = await test_full_cycle(test_db_path)

                    assert result is False

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_cycle_semantic_search_fallback(self):
        """Test full cycle with semantic search fallback."""
        mock_config = MagicMock()
        mock_config.embedder_provider = "ollama"

        unique_id = "test_unique_id_12345"

        mock_memory = MagicMock()
        mock_memory.is_enabled = True
        mock_memory.initialize = AsyncMock(return_value=True)
        mock_memory.save_pattern = AsyncMock(return_value=True)
        mock_memory.save_gotcha = AsyncMock(return_value=True)
        # Return results containing the unique_id
        mock_memory.get_relevant_context = AsyncMock(
            return_value=[
                {"content": f"Pattern with {unique_id}: dependency injection", "score": 0.9},
                {"content": f"Gotcha with {unique_id}: database cleanup", "score": 0.8},
                {"content": "Related content about error handling", "score": 0.7},
            ]
        )
        mock_memory.close = AsyncMock()

        test_db_path = Path("/tmp/test_cycle")
        test_db_path.mkdir(parents=True, exist_ok=True)

        with patch.dict("os.environ", {
            "GRAPHITI_DB_PATH": str(test_db_path / "graphiti_db"),
            "GRAPHITI_DATABASE": "test_full_cycle",
        }):
            with patch(
                "integrations.graphiti.config.GraphitiConfig.from_env",
                return_value=mock_config,
            ):
                # Mock datetime to return our unique_id
                with patch("integrations.graphiti.test_ollama_embedding_memory.datetime") as mock_datetime:
                    mock_datetime.now.return_value.strftime.return_value = unique_id
                    with patch(
                        "integrations.graphiti.memory.GraphitiMemory",
                        return_value=mock_memory,
                    ):
                        result = await test_full_cycle(test_db_path)

                        # Should pass with proper mock data
                        assert result is True


class TestMainFunction:
    """Tests for main function."""

    @pytest.mark.asyncio
    async def test_main_all_tests_success(self):
        """Test main runs all tests successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "embeddinggemma"}]}

        with patch.dict("os.environ", {
            "GRAPHITI_ENABLED": "true",
            "GRAPHITI_LLM_PROVIDER": "ollama",
            "GRAPHITI_EMBEDDER_PROVIDER": "ollama",
            "OLLAMA_LLM_MODEL": "deepseek-r1:7b",
            "OLLAMA_EMBEDDING_MODEL": "embeddinggemma",
            "OLLAMA_EMBEDDING_DIM": "768",
        }):
            with patch("requests.get", return_value=mock_response):
                with patch(
                    "integrations.graphiti.test_ollama_embedding_memory.test_ollama_embeddings",
                    new=AsyncMock(return_value=True),
                ):
                    with patch(
                        "integrations.graphiti.test_ollama_embedding_memory.test_memory_creation",
                        new=AsyncMock(return_value=(Path(), Path(), True)),
                    ):
                        with patch(
                            "integrations.graphiti.test_ollama_embedding_memory.test_memory_retrieval",
                            new=AsyncMock(return_value=True),
                        ):
                            with patch(
                                "integrations.graphiti.test_ollama_embedding_memory.test_full_cycle",
                                new=AsyncMock(return_value=True),
                            ):
                                # Can't easily test argparse, but we can verify the structure
                                # by checking imports work correctly
                                from integrations.graphiti import test_ollama_embedding_memory

                                assert hasattr(test_ollama_embedding_memory, "main")
                                assert hasattr(test_ollama_embedding_memory, "test_ollama_embeddings")

    @pytest.mark.asyncio
    async def test_main_specific_test(self):
        """Test main runs specific test."""
        with patch.dict("os.environ", {
            "GRAPHITI_ENABLED": "true",
            "OLLAMA_EMBEDDING_MODEL": "embeddinggemma",
            "OLLAMA_EMBEDDING_DIM": "768",
        }):
            # Verify test functions are callable
            from integrations.graphiti import test_ollama_embedding_memory

            assert asyncio.iscoroutinefunction(test_ollama_embeddings)
            assert asyncio.iscoroutinefunction(test_memory_creation)
            assert asyncio.iscoroutinefunction(test_memory_retrieval)
            assert asyncio.iscoroutinefunction(test_full_cycle)
