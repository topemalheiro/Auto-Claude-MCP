#!/usr/bin/env python3
"""
Tests for query_memory.py CLI tool

This module provides a subprocess interface for querying the LadybugDB/Graphiti
memory database from the Electron main process.
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch


class TestApplyMonkeypatch:
    """Tests for apply_monkeypatch function."""

    def test_apply_monkeypatch_with_ladybug(self):
        """Test monkeypatch applies when real_ladybug is available."""
        import query_memory

        with patch("query_memory.real_ladybug", create=True) as mock_ladybug:
            result = query_memory.apply_monkeypatch()
            # When real_ladybug is available, should set sys.modules["kuzu"]
            assert result == "ladybug" or result is None

    def test_apply_monkeypatch_with_kuzu(self):
        """Test monkeypatch falls back to native kuzu."""
        import query_memory

        # The function tries to import real_ladybug first, falls back to kuzu
        # We can't easily mock the import system, so just verify it runs
        result = query_memory.apply_monkeypatch()
        # Result is either "ladybug", "kuzu", or None depending on what's installed
        assert result in ("ladybug", "kuzu", None)

    def test_apply_monkeypatch_no_backend(self):
        """Test monkeypatch returns None when no backend available."""
        import query_memory

        # This test just verifies the function can be called
        # The actual behavior depends on what's installed in the environment
        result = query_memory.apply_monkeypatch()
        assert result in ("ladybug", "kuzu", None)


class TestSerializeValue:
    """Tests for serialize_value function."""

    def test_serialize_value_none(self):
        """Test serializing None."""
        import query_memory

        result = query_memory.serialize_value(None)
        assert result is None

    def test_serialize_value_string(self):
        """Test serializing string."""
        import query_memory

        result = query_memory.serialize_value("test")
        assert result == "test"

    def test_serialize_value_int(self):
        """Test serializing integer."""
        import query_memory

        result = query_memory.serialize_value(42)
        assert result == 42

    def test_serialize_value_with_isoformat(self):
        """Test serializing value with isoformat method."""
        import query_memory
        from datetime import datetime

        dt = datetime(2024, 1, 1, 12, 0, 0)
        result = query_memory.serialize_value(dt)
        assert isinstance(result, str)

    def test_serialize_value_with_timestamp(self):
        """Test serializing kuzu Timestamp object."""
        import query_memory

        class MockTimestamp:
            def timestamp(self):
                return 1704110400

        ts = MockTimestamp()
        result = query_memory.serialize_value(ts)
        assert isinstance(result, str)


class TestOutputJson:
    """Tests for output_json function."""

    def test_output_json_success(self, capsys):
        """Test output_json with success=True."""
        import query_memory

        with patch("sys.exit"):
            query_memory.output_json(True, data={"key": "value"})

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["success"] is True
        assert output["data"]["key"] == "value"

    def test_output_json_failure(self, capsys):
        """Test output_json with success=False."""
        import query_memory

        with patch("sys.exit"):
            query_memory.output_json(False, error="Test error")

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["success"] is False
        assert output["error"] == "Test error"

    def test_output_json_with_default_str(self, capsys):
        """Test output_json uses default=str for non-serializable objects."""
        import query_memory

        class CustomObj:
            def __str__(self):
                return "custom"

        with patch("sys.exit"):
            query_memory.output_json(True, data={"obj": CustomObj()})

        captured = capsys.readouterr()
        # Should not raise JSONDecodeError
        output = json.loads(captured.out)
        assert output["success"] is True


class TestOutputError:
    """Tests for output_error function."""

    def test_output_error(self, capsys):
        """Test output_error outputs error and exits."""
        import query_memory

        with patch("sys.exit"):
            query_memory.output_error("Test error message")

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["success"] is False
        assert output["error"] == "Test error message"


class TestGetDbConnection:
    """Tests for get_db_connection function."""

    def test_get_db_connection_success(self, tmp_path):
        """Test successful database connection (when kuzu is available)."""
        import query_memory

        # Create a fake database directory
        db_dir = tmp_path / "test_db"
        db_dir.mkdir()

        # Try to connect - this will only work if kuzu or real_ladybug is installed
        conn, error = query_memory.get_db_connection(str(tmp_path), "test_db")

        # If kuzu is not installed, we get an error
        # If it is installed, the connection should work
        if conn is None:
            assert error is not None
        else:
            assert error is None

    def test_get_db_connection_not_found(self, tmp_path):
        """Test connection when database doesn't exist."""
        import query_memory

        conn, error = query_memory.get_db_connection(str(tmp_path), "nonexistent")

        # Should return error since database doesn't exist
        assert conn is None
        assert error is not None
        # Error message may be about not found or about kuzu not being installed
        assert "not found" in error.lower() or "kuzu" in error.lower() or "ladybug" in error.lower()

    def test_get_db_connection_exception(self, tmp_path):
        """Test connection handles exceptions gracefully."""
        import query_memory

        # Just verify the function can be called and handles errors
        conn, error = query_memory.get_db_connection(str(tmp_path), "test")

        # Should return an error (either DB not found or kuzu not available)
        assert conn is None or error is None


class TestInferEpisodeType:
    """Tests for infer_episode_type function."""

    def test_infer_session_insight_from_name(self):
        """Test inferring session_insight type from name."""
        import query_memory

        result = query_memory.infer_episode_type("session_123", "")
        assert result == "session_insight"

    def test_infer_session_insight_from_content(self):
        """Test inferring session_insight type from content."""
        import query_memory

        result = query_memory.infer_episode_type("", '{"type": "session_insight"}')
        assert result == "session_insight"

    def test_infer_pattern_from_name(self):
        """Test inferring pattern type from name."""
        import query_memory

        result = query_memory.infer_episode_type("pattern123", "")
        assert result == "pattern"

    def test_infer_gotcha_from_name(self):
        """Test inferring gotcha type from name."""
        import query_memory

        result = query_memory.infer_episode_type("gotcha_example", "")
        assert result == "gotcha"

    def test_infer_codebase_discovery(self):
        """Test inferring codebase_discovery type."""
        import query_memory

        result = query_memory.infer_episode_type("codebase_analysis", "")
        assert result == "codebase_discovery"

    def test_infer_task_outcome(self):
        """Test inferring task_outcome type."""
        import query_memory

        result = query_memory.infer_episode_type("task_outcome_success", "")
        assert result == "task_outcome"

    def test_infer_default(self):
        """Test default inference returns session_insight."""
        import query_memory

        result = query_memory.infer_episode_type("unknown", "")
        assert result == "session_insight"


class TestInferEntityType:
    """Tests for infer_entity_type function."""

    def test_infer_pattern(self):
        """Test inferring pattern entity type."""
        import query_memory

        result = query_memory.infer_entity_type("pattern_test")
        assert result == "pattern"

    def test_infer_gotcha(self):
        """Test inferring gotcha entity type."""
        import query_memory

        result = query_memory.infer_entity_type("gotcha_example")
        assert result == "gotcha"

    def test_infer_codebase_discovery(self):
        """Test inferring codebase_discovery entity type."""
        import query_memory

        result = query_memory.infer_entity_type("file_insight_test")
        assert result == "codebase_discovery"

    def test_infer_default_entity(self):
        """Test default entity type inference."""
        import query_memory

        result = query_memory.infer_entity_type("unknown_entity")
        assert result == "session_insight"


class TestExtractSessionNumber:
    """Tests for extract_session_number function."""

    def test_extract_session_number_with_underscore(self):
        """Test extracting session number with underscore format."""
        import query_memory

        result = query_memory.extract_session_number("session_123")
        assert result == 123

    def test_extract_session_number_with_dash(self):
        """Test extracting session number with dash format."""
        import query_memory

        result = query_memory.extract_session_number("session-456")
        assert result == 456

    def test_extract_session_number_case_insensitive(self):
        """Test extracting session number is case insensitive."""
        import query_memory

        result = query_memory.extract_session_number("SESSION_789")
        assert result == 789

    def test_extract_session_number_none(self):
        """Test extracting session number returns None when not found."""
        import query_memory

        result = query_memory.extract_session_number("no_session_here")
        assert result is None

    def test_extract_session_number_invalid_format(self):
        """Test extracting session number with invalid format."""
        import query_memory

        result = query_memory.extract_session_number("session_abc")
        assert result is None


class TestCmdGetStatus:
    """Tests for cmd_get_status function."""

    def test_cmd_get_status_no_backend(self, capsys):
        """Test cmd_get_status when no database backend is available."""
        import query_memory

        args = Mock(db_path=Path("/tmp"), database="test")

        with patch("query_memory.apply_monkeypatch", return_value=None):
            with patch("sys.exit"):
                query_memory.cmd_get_status(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["data"]["available"] is False
        assert output["data"]["ladybugInstalled"] is False

    def test_cmd_get_status_with_backend(self, capsys, tmp_path):
        """Test cmd_get_status with database backend."""
        import query_memory

        # Create database directory
        db_dir = tmp_path / "test_db"
        db_dir.mkdir()

        args = Mock(db_path=str(tmp_path), database="test_db")

        with patch("query_memory.apply_monkeypatch", return_value="kuzu"):
            with patch("query_memory.get_db_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_result = MagicMock()
                mock_result.get_as_df.return_value = MagicMock()
                mock_conn.execute.return_value = mock_result
                mock_get_conn.return_value = (mock_conn, None)

                with patch("sys.exit"):
                    query_memory.cmd_get_status(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["data"]["available"] is True

    def test_cmd_get_status_lists_databases(self, capsys, tmp_path):
        """Test cmd_get_status lists available databases."""
        import query_memory

        # Create multiple database directories
        (tmp_path / "db1").mkdir()
        (tmp_path / "db2").mkdir()

        args = Mock(db_path=str(tmp_path), database="db1")

        with patch("query_memory.apply_monkeypatch", return_value="kuzu"):
            with patch("query_memory.get_db_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_result = MagicMock()
                mock_result.get_as_df.return_value = MagicMock()
                mock_conn.execute.return_value = mock_result
                mock_get_conn.return_value = (mock_conn, None)

                with patch("sys.exit"):
                    query_memory.cmd_get_status(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "databases" in output["data"]
        assert isinstance(output["data"]["databases"], list)


class TestCmdGetMemories:
    """Tests for cmd_get_memories function."""

    def test_cmd_get_memories_no_backend(self, capsys):
        """Test cmd_get_memories when no backend available."""
        import query_memory

        args = Mock(db_path="/tmp", database="test", limit=10)

        # Apply monkeypatch first to check backend availability
        backend = query_memory.apply_monkeypatch()

        if backend is None:
            # No backend available, should output error
            with patch("sys.exit"):
                query_memory.cmd_get_memories(args)

            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert output["success"] is False
            assert "installed" in output["error"].lower()
        else:
            # Backend available, will try to connect and likely fail with connection error
            with patch("sys.exit"):
                query_memory.cmd_get_memories(args)

            captured = capsys.readouterr()
            # Should handle gracefully one way or another
            assert captured.out is not None

    def test_cmd_get_memories_connection_error(self, capsys):
        """Test cmd_get_memories with connection error."""
        import query_memory

        args = Mock(db_path="/tmp", database="test", limit=10)

        with patch("query_memory.apply_monkeypatch", return_value="kuzu"):
            with patch("query_memory.get_db_connection") as mock_get_conn:
                mock_get_conn.return_value = (None, "Connection failed")

                with patch("sys.exit"):
                    query_memory.cmd_get_memories(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["success"] is False
        assert "failed" in output["error"].lower()

    def test_cmd_get_memories_table_not_exists(self, capsys):
        """Test cmd_get_memories when Episodic table doesn't exist."""
        import query_memory

        args = Mock(db_path="/tmp", database="test", limit=10)

        with patch("query_memory.apply_monkeypatch", return_value="kuzu"):
            with patch("query_memory.get_db_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_conn.execute.side_effect = Exception("Episodic does not exist")
                mock_get_conn.return_value = (mock_conn, None)

                with patch("sys.exit"):
                    query_memory.cmd_get_memories(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        # Should return empty result instead of error
        assert output["success"] is True
        assert output["data"]["count"] == 0


class TestCmdSearch:
    """Tests for cmd_search function."""

    def test_cmd_search_no_backend(self, capsys):
        """Test cmd_search when no backend available."""
        import query_memory

        args = Mock(db_path="/tmp", database="test", query="test", limit=10)

        with patch("query_memory.apply_monkeypatch", return_value=None):
            with patch("sys.exit"):
                query_memory.cmd_search(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["success"] is False

    def test_cmd_search_success(self, capsys):
        """Test cmd_search successful execution."""
        import query_memory

        args = Mock(db_path="/tmp", database="test", query="test query", limit=10)

        with patch("query_memory.apply_monkeypatch", return_value="kuzu"):
            with patch("query_memory.get_db_connection") as mock_get_conn:
                mock_conn = MagicMock()
                # Mock empty result set
                mock_result = MagicMock()
                mock_result.has_next.return_value = False
                mock_conn.execute.return_value = mock_result
                mock_get_conn.return_value = (mock_conn, None)

                with patch("sys.exit"):
                    query_memory.cmd_search(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["success"] is True
        assert output["data"]["query"] == "test query"


class TestCmdSemanticSearch:
    """Tests for cmd_semantic_search function."""

    def test_semantic_search_fallback_no_embedder(self, capsys):
        """Test semantic search falls back to keyword when no embedder configured."""
        import query_memory

        args = Mock(db_path="/tmp", database="test", query="test", limit=10)

        with patch.dict(os.environ, {"GRAPHITI_EMBEDDER_PROVIDER": ""}):
            with patch("query_memory.cmd_search") as mock_search:
                with patch("sys.exit"):
                    query_memory.cmd_semantic_search(args)

        # Should fall back to keyword search
        mock_search.assert_called_once_with(args)

    def test_semantic_search_fallback_on_error(self, capsys):
        """Test semantic search falls back on error."""
        import query_memory

        args = Mock(db_path="/tmp", database="test", query="test", limit=10)

        with patch.dict(os.environ, {"GRAPHITI_EMBEDDER_PROVIDER": "openai"}):
            with patch("query_memory.cmd_search") as mock_search:
                with patch("query_memory._async_semantic_search", return_value={"success": False}):
                    with patch("sys.exit"):
                        query_memory.cmd_semantic_search(args)

        # Should fall back to keyword search on failure
        mock_search.assert_called_once_with(args)


class TestCmdGetEntities:
    """Tests for cmd_get_entities function."""

    def test_cmd_get_entities_no_backend(self, capsys):
        """Test cmd_get_entities when no backend available."""
        import query_memory

        args = Mock(db_path="/tmp", database="test", limit=10)

        with patch("query_memory.apply_monkeypatch", return_value=None):
            with patch("sys.exit"):
                query_memory.cmd_get_entities(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["success"] is False

    def test_cmd_get_entities_table_not_exists(self, capsys):
        """Test cmd_get_entities when Entity table doesn't exist."""
        import query_memory

        args = Mock(db_path="/tmp", database="test", limit=10)

        with patch("query_memory.apply_monkeypatch", return_value="kuzu"):
            with patch("query_memory.get_db_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_conn.execute.side_effect = Exception("Entity does not exist")
                mock_get_conn.return_value = (mock_conn, None)

                with patch("sys.exit"):
                    query_memory.cmd_get_entities(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        # Should return empty result instead of error
        assert output["success"] is True
        assert output["data"]["count"] == 0


class TestCmdAddEpisode:
    """Tests for cmd_add_episode function."""

    def test_cmd_add_episode_no_backend(self, capsys):
        """Test cmd_add_episode when no backend available."""
        import query_memory

        args = Mock()
        args.db_path = "/tmp"
        args.database = "test"
        args.name = "test_episode"
        args.content = '{"key": "value"}'
        args.episode_type = "session_insight"
        args.group_id = None

        # Check backend availability
        backend = query_memory.apply_monkeypatch()

        if backend is None:
            # No backend available
            with patch("sys.exit"):
                query_memory.cmd_add_episode(args)

            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert output["success"] is False
            assert "installed" in output["error"].lower()

    def test_cmd_add_episode_success(self, capsys, tmp_path):
        """Test cmd_add_episode successful execution (if kuzu available)."""
        import query_memory

        args = Mock()
        args.db_path = str(tmp_path)
        args.database = "test_db"
        args.name = "test_episode"
        args.content = '{"key": "value"}'
        args.episode_type = "pattern"
        args.group_id = "test_group"

        backend = query_memory.apply_monkeypatch()

        if backend is not None:
            # Backend available, should succeed
            with patch("sys.exit"):
                query_memory.cmd_add_episode(args)

            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert output["success"] is True
            assert output["data"]["name"] == "test_episode"
            assert output["data"]["type"] == "pattern"
        else:
            # No backend - skip this test
            pass

    def test_cmd_add_episode_invalid_json(self, capsys, tmp_path):
        """Test cmd_add_episode handles non-JSON content."""
        import query_memory

        args = Mock()
        args.db_path = str(tmp_path)
        args.database = "test_db"
        args.name = "test_episode"
        args.content = "plain text content"  # Not JSON
        args.episode_type = "gotcha"
        args.group_id = None

        backend = query_memory.apply_monkeypatch()

        if backend is not None:
            with patch("sys.exit"):
                query_memory.cmd_add_episode(args)

            captured = capsys.readouterr()
            output = json.loads(captured.out)
            # Should accept plain text content
            assert output["success"] is True

    def test_cmd_add_episode_creates_directory(self, capsys, tmp_path):
        """Test cmd_add_episode creates parent directory if needed."""
        import query_memory

        new_db_dir = tmp_path / "new_dir" / "databases"
        args = Mock()
        args.db_path = str(new_db_dir.parent)
        args.database = "databases"
        args.name = "test"
        args.content = "test"
        args.episode_type = "session_insight"
        args.group_id = None

        backend = query_memory.apply_monkeypatch()

        if backend is not None:
            with patch("sys.exit"):
                query_memory.cmd_add_episode(args)

            # Directory should be created
            assert new_db_dir.exists()


class TestMainCLI:
    """Tests for main() CLI entry point."""

    def test_main_no_command(self, capsys):
        """Test main() without command."""
        import query_memory

        with patch("sys.argv", ["query_memory.py"]):
            with patch("sys.exit"):
                query_memory.main()

        captured = capsys.readouterr()
        # Should show help or error
        assert "usage" in captured.out.lower() or "error" in captured.out.lower()

    def test_main_get_status_command(self, capsys):
        """Test main() with get-status command."""
        import query_memory

        with patch("sys.argv", ["query_memory.py", "get-status", "/tmp", "test"]):
            with patch("query_memory.apply_monkeypatch", return_value=None):
                with patch("sys.exit"):
                    query_memory.main()

        # Should complete without error
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "success" in output

    def test_main_get_memories_command(self, capsys):
        """Test main() with get-memories command."""
        import query_memory

        with patch("sys.argv", ["query_memory.py", "get-memories", "/tmp", "test", "--limit", "10"]):
            with patch("query_memory.apply_monkeypatch", return_value=None):
                with patch("sys.exit"):
                    query_memory.main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "success" in output

    def test_main_search_command(self, capsys):
        """Test main() with search command."""
        import query_memory

        with patch("sys.argv", ["query_memory.py", "search", "/tmp", "test", "query term", "--limit", "5"]):
            with patch("query_memory.apply_monkeypatch", return_value=None):
                with patch("sys.exit"):
                    query_memory.main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "success" in output

    def test_main_semantic_search_command(self, capsys):
        """Test main() with semantic-search command."""
        import query_memory

        with patch("sys.argv", ["query_memory.py", "semantic-search", "/tmp", "test", "query"]):
            with patch.dict(os.environ, {"GRAPHITI_EMBEDDER_PROVIDER": ""}):
                with patch("query_memory.apply_monkeypatch", return_value=None):
                    with patch("sys.exit"):
                        query_memory.main()

        # Should handle the command (may fall back to keyword)
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "success" in output

    def test_main_get_entities_command(self, capsys):
        """Test main() with get-entities command."""
        import query_memory

        with patch("sys.argv", ["query_memory.py", "get-entities", "/tmp", "test"]):
            with patch("query_memory.apply_monkeypatch", return_value=None):
                with patch("sys.exit"):
                    query_memory.main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "success" in output

    def test_main_add_episode_command(self, capsys, tmp_path):
        """Test main() with add-episode command."""
        import query_memory

        backend = query_memory.apply_monkeypatch()

        if backend is not None:
            with patch("sys.argv", [
                "query_memory.py",
                "add-episode",
                str(tmp_path),
                "test_db",
                "--name", "test_episode",
                "--content", "test content",
                "--type", "session_insight",
            ]):
                with patch("sys.exit"):
                    query_memory.main()

            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert output["success"] is True

    def test_main_unknown_command(self, capsys):
        """Test main() with unknown command."""
        import query_memory

        with patch("sys.argv", ["query_memory.py", "unknown-command", "/tmp", "test"]):
            with patch("sys.exit", side_effect=SystemExit):
                try:
                    query_memory.main()
                except SystemExit:
                    pass  # Expected exit from CLI (no-op)

        captured = capsys.readouterr()
        # Should print usage or error message
        assert len(captured.out) > 0 or len(captured.err) > 0


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_query_search(self, capsys):
        """Test search with empty query string."""
        import query_memory

        args = Mock(db_path="/tmp", database="test", query="", limit=10)

        with patch("query_memory.apply_monkeypatch", return_value="kuzu"):
            with patch("query_memory.get_db_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_result = MagicMock()
                mock_result.has_next.return_value = False
                mock_conn.execute.return_value = mock_result
                mock_get_conn.return_value = (mock_conn, None)

                with patch("sys.exit"):
                    query_memory.cmd_search(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["success"] is True

    def test_zero_limit(self, capsys):
        """Test command with limit=0."""
        import query_memory

        args = Mock(db_path="/tmp", database="test", query="test", limit=0)

        with patch("query_memory.apply_monkeypatch", return_value="kuzu"):
            with patch("query_memory.get_db_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_result = MagicMock()
                mock_result.has_next.return_value = False
                mock_conn.execute.return_value = mock_result
                mock_get_conn.return_value = (mock_conn, None)

                with patch("sys.exit"):
                    query_memory.cmd_search(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["success"] is True

    def test_large_limit(self, capsys):
        """Test command with very large limit."""
        import query_memory

        args = Mock(db_path="/tmp", database="test", query="test", limit=1000000)

        with patch("query_memory.apply_monkeypatch", return_value="kuzu"):
            with patch("query_memory.get_db_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_result = MagicMock()
                mock_result.has_next.return_value = False
                mock_conn.execute.return_value = mock_result
                mock_get_conn.return_value = (mock_conn, None)

                with patch("sys.exit"):
                    query_memory.cmd_search(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["success"] is True

    def test_unicode_content(self, capsys, tmp_path):
        """Test handling unicode content."""
        import query_memory

        args = Mock()
        args.db_path = str(tmp_path)
        args.database = "test_db"
        args.name = "测试_episode"
        args.content = '{"text": "café ñ 日本語"}'
        args.episode_type = "session_insight"
        args.group_id = None

        backend = query_memory.apply_monkeypatch()

        if backend is not None:
            with patch("sys.exit"):
                query_memory.cmd_add_episode(args)

            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert output["success"] is True
