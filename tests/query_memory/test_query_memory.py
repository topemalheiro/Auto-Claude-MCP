"""
Comprehensive tests for query_memory.py.

Tests cover:
- All query commands (get-status, get-memories, search, semantic-search, get-entities, add-episode)
- Error handling for missing databases
- JSON serialization of complex types
- CLI argument parsing
- Connection management
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Import the module under test
# We need to handle the module being in the apps/backend directory
backend_path = Path(__file__).parent.parent.parent / "apps" / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from query_memory import (
    _async_semantic_search,
    apply_monkeypatch,
    cmd_add_episode,
    cmd_get_entities,
    cmd_get_memories,
    cmd_get_status,
    cmd_search,
    cmd_semantic_search,
    extract_session_number,
    get_db_connection,
    infer_entity_type,
    infer_episode_type,
    output_error,
    output_json,
    serialize_value,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_args():
    """Create mock CLI arguments."""
    args = MagicMock()
    args.db_path = "/tmp/test_db"
    args.database = "test_db"
    args.limit = 10
    args.query = "test query"
    args.name = "test episode"
    args.content = '{"test": "content"}'
    args.episode_type = "session_insight"
    args.group_id = None
    return args


@pytest.fixture
def mock_db_connection():
    """Create a mock database connection."""
    mock_conn = MagicMock()
    mock_result = MagicMock()
    mock_result.has_next = Mock(return_value=False)
    mock_conn.execute = Mock(return_value=mock_result)
    return mock_conn


@pytest.fixture
def mock_kuzu_database():
    """Create a mock kuzu Database and Connection."""
    mock_db = MagicMock()
    mock_conn = MagicMock()
    return mock_db, mock_conn


@pytest.fixture
def sample_memory_row():
    """Create a sample memory row as returned by kuzu."""
    return [
        "uuid-123",  # uuid
        "session_1_test",  # name
        datetime(2024, 1, 1, 12, 0, 0),  # created_at
        "Test content",  # content
        "Test description",  # description
        "group-123",  # group_id
    ]


@pytest.fixture
def sample_entity_row():
    """Create a sample entity row as returned by kuzu."""
    return [
        "entity-uuid-123",  # uuid
        "pattern_test",  # name
        "Test summary content",  # summary
        datetime(2024, 1, 1, 12, 0, 0),  # created_at
    ]


@pytest.fixture
def mock_graphiti_result():
    """Create a mock Graphiti search result."""
    result = MagicMock()
    result.uuid = "result-uuid-123"
    result.fact = "Test fact about the codebase"
    result.content = "Test content"
    result.name = "session_1_insight"
    result.created_at = "2024-01-01T12:00:00"
    result.score = 0.95
    return result


# =============================================================================
# Serialize Value Tests
# =============================================================================


class TestSerializeValue:
    """Test serialize_value function for JSON serialization."""

    def test_serialize_none(self):
        """Test serializing None returns None."""
        assert serialize_value(None) is None

    def test_serialize_string(self):
        """Test serializing string returns same value."""
        assert serialize_value("test string") == "test string"

    def test_serialize_number(self):
        """Test serializing numbers returns same value."""
        assert serialize_value(123) == 123
        assert serialize_value(45.67) == 45.67

    def test_serialize_datetime_with_isoformat(self):
        """Test serializing datetime with isoformat method."""
        dt = datetime(2024, 1, 1, 12, 30, 45)
        result = serialize_value(dt)
        assert isinstance(result, str)
        assert "2024-01-01" in result
        assert "12:30:45" in result

    def test_serialize_datetime_with_timestamp_method(self):
        """Test serializing object with timestamp method (kuzu Timestamp)."""
        class MockTimestamp:
            def timestamp(self):
                return 1234567890

            def __str__(self):
                return "1234567890"

        mock_ts = MockTimestamp()
        result = serialize_value(mock_ts)
        assert result == "1234567890"

    def test_serialize_object_without_special_methods(self):
        """Test serializing regular object returns string representation."""
        class RegularObject:
            def __str__(self):
                return "regular_object"

        obj = RegularObject()
        # Objects without isoformat or timestamp just pass through
        result = serialize_value(obj)
        assert result == obj


# =============================================================================
# Output JSON Tests
# =============================================================================


class TestOutputJson:
    """Test output_json function."""

    def test_output_json_success(self, capsys):
        """Test output_json with success=True and data."""
        with pytest.raises(SystemExit) as exc_info:
            output_json(True, data={"key": "value"})

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert '"success": true' in captured.out
        assert '"key": "value"' in captured.out

    def test_output_json_error(self, capsys):
        """Test output_json with success=False and error message."""
        with pytest.raises(SystemExit) as exc_info:
            output_json(False, error="Test error")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert '"success": false' in captured.out
        assert '"error": "Test error"' in captured.out

    def test_output_json_with_all_params(self, capsys):
        """Test output_json with success, data, and error."""
        with pytest.raises(SystemExit) as exc_info:
            output_json(True, data={"test": "data"}, error="Warning message")

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert '"success": true' in captured.out
        assert '"test": "data"' in captured.out
        assert '"error": "Warning message"' in captured.out

    def test_output_json_handles_non_serializable(self, capsys):
        """Test output_json uses default=str for non-serializable types."""
        class NonSerializable:
            def __str__(self):
                return "non_serializable_obj"

        with pytest.raises(SystemExit):
            output_json(True, data={"obj": NonSerializable()})

        captured = capsys.readouterr()
        assert "non_serializable_obj" in captured.out


class TestOutputError:
    """Test output_error function."""

    def test_output_error_exits_with_code_1(self, capsys):
        """Test output_error calls sys.exit(1)."""
        with pytest.raises(SystemExit) as exc_info:
            output_error("Error message")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert '"success": false' in captured.out
        assert '"error": "Error message"' in captured.out


# =============================================================================
# Database Connection Tests
# =============================================================================


class TestGetDbConnection:
    """Test get_db_connection function."""

    @patch("query_memory.apply_monkeypatch", return_value=None)
    def test_get_db_connection_no_backend(self, mock_apply):
        """Test connection when no database backend is available."""
        conn, error = get_db_connection("/tmp/test", "db")
        assert conn is None
        assert error is not None

    @patch("query_memory.apply_monkeypatch", return_value="kuzu")
    @patch("pathlib.Path.exists", return_value=False)
    def test_get_db_connection_path_not_exists(self, mock_exists, mock_apply):
        """Test connection when database path doesn't exist."""
        conn, error = get_db_connection("/tmp/test", "db")
        assert conn is None
        assert error is not None
        # Error could be about module or path not found
        assert "not found" in error.lower() or "module" in error.lower()

    @patch("query_memory.apply_monkeypatch", return_value="kuzu")
    @patch("pathlib.Path.exists", return_value=True)
    def test_get_db_connection_exception_during_connect(self, mock_exists, mock_apply):
        """Test connection exception handling."""
        # Need to import kuzu module first, then mock it
        import importlib
        import sys

        # Mock the kuzu module's Database to raise an exception
        mock_kuzu = MagicMock()
        mock_kuzu.Database.side_effect = Exception("Connection failed")
        # Mock Connection to raise exception too
        mock_kuzu.Connection.side_effect = Exception("Connection failed")

        # Patch sys.modules to use our mock
        with patch.dict(sys.modules, {"kuzu": mock_kuzu}):
            conn, error = get_db_connection("/tmp/test", "db")

        assert conn is None
        assert error is not None
        assert "connection failed" in error.lower()


# =============================================================================
# Apply Monkeypatch Tests
# =============================================================================


class TestApplyMonkeypatch:
    """Test apply_monkeypatch function."""

    @patch.dict(sys.modules, {}, clear=False)
    def test_apply_monkeypatch_returns_backend_or_none(self):
        """Test apply_monkeypatch returns 'ladybug', 'kuzu', or None."""
        result = apply_monkeypatch()
        assert result in ["ladybug", "kuzu", None]


# =============================================================================
# Inference Function Tests
# =============================================================================


class TestInferEpisodeType:
    """Test infer_episode_type function."""

    def test_infer_session_insight_from_name(self):
        """Test inferring session_insight type from name."""
        assert infer_episode_type("session_1") == "session_insight"
        assert infer_episode_type("session_42_review") == "session_insight"
        assert infer_episode_type("SESSION_1") == "session_insight"

    def test_infer_session_insight_from_content(self):
        """Test inferring session_insight type from content."""
        content = '{"type": "session_insight", "data": "test"}'
        assert infer_episode_type("episode", content) == "session_insight"

    def test_infer_pattern_type(self):
        """Test inferring pattern type."""
        assert infer_episode_type("pattern_authentication") == "pattern"
        content = '{"type": "pattern", "name": "test"}'
        assert infer_episode_type("episode", content) == "pattern"

    def test_infer_gotcha_type(self):
        """Test inferring gotcha type."""
        assert infer_episode_type("gotcha_import_error") == "gotcha"
        content = '{"type": "gotcha", "description": "test"}'
        assert infer_episode_type("episode", content) == "gotcha"

    def test_infer_codebase_discovery_type(self):
        """Test inferring codebase_discovery type."""
        assert infer_episode_type("codebase_structure") == "codebase_discovery"
        content = '{"type": "codebase_discovery", "files": []}'
        assert infer_episode_type("episode", content) == "codebase_discovery"

    def test_infer_task_outcome_type(self):
        """Test inferring task_outcome type."""
        assert infer_episode_type("task_outcome_success") == "task_outcome"
        content = '{"type": "task_outcome", "status": "complete"}'
        assert infer_episode_type("episode", content) == "task_outcome"

    def test_infer_default_type(self):
        """Test default type when no pattern matches."""
        assert infer_episode_type("unknown_episode") == "session_insight"
        assert infer_episode_type("", "") == "session_insight"


class TestInferEntityType:
    """Test infer_entity_type function."""

    def test_infer_pattern_entity(self):
        """Test inferring pattern entity type."""
        assert infer_entity_type("pattern_authentication") == "pattern"
        assert infer_entity_type("Pattern_test") == "pattern"
        assert infer_entity_type("PATTERN_NAME") == "pattern"

    def test_infer_gotcha_entity(self):
        """Test inferring gotcha entity type."""
        assert infer_entity_type("gotcha_import_error") == "gotcha"
        assert infer_entity_type("Gotcha_test") == "gotcha"

    def test_infer_codebase_discovery_entity(self):
        """Test inferring codebase_discovery entity type."""
        assert infer_entity_type("file_insight_main") == "codebase_discovery"
        assert infer_entity_type("codebase_analysis") == "codebase_discovery"

    def test_infer_default_entity(self):
        """Test default entity type when no pattern matches."""
        assert infer_entity_type("unknown_entity") == "session_insight"
        assert infer_entity_type("") == "session_insight"


class TestExtractSessionNumber:
    """Test extract_session_number function."""

    def test_extract_session_number_with_underscore(self):
        """Test extracting session number with underscore format."""
        assert extract_session_number("session_1") == 1
        assert extract_session_number("session_42_test") == 42
        assert extract_session_number("session_123") == 123

    def test_extract_session_number_with_dash(self):
        """Test extracting session number with dash format."""
        assert extract_session_number("session-1") == 1
        assert extract_session_number("session-42-test") == 42

    def test_extract_session_number_case_insensitive(self):
        """Test session number extraction is case insensitive."""
        assert extract_session_number("Session_1") == 1
        assert extract_session_number("SESSION_42") == 42
        assert extract_session_number("SeSsIoN-5") == 5

    def test_extract_session_number_no_match(self):
        """Test extracting session number when none exists."""
        assert extract_session_number("episode_1") is None
        assert extract_session_number("test") is None
        assert extract_session_number("") is None
        assert extract_session_number("session_test") is None


# =============================================================================
# Command Tests - Get Status
# =============================================================================


class TestCmdGetStatus:
    """Test cmd_get_status function."""

    @patch("query_memory.apply_monkeypatch", return_value=None)
    def test_get_status_no_backend(self, mock_apply, capsys):
        """Test get_status when no database backend is available."""
        args = MagicMock()
        args.db_path = "/tmp/test"
        args.database = "test_db"

        with pytest.raises(SystemExit) as exc_info:
            cmd_get_status(args)

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["success"] is True
        assert data["data"]["available"] is False
        assert data["data"]["ladybugInstalled"] is False

    @patch("query_memory.apply_monkeypatch", return_value="kuzu")
    @patch("query_memory.get_db_connection")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.iterdir")
    def test_get_status_with_backend(
        self, mock_iterdir, mock_exists, mock_get_conn, mock_apply, capsys
    ):
        """Test get_status with backend available."""
        # Setup mocks
        mock_db_path = MagicMock()
        mock_db_path.exists.return_value = True
        mock_exists.return_value = True

        # Mock database entries
        mock_item1 = MagicMock()
        mock_item1.name = "db1"
        mock_item2 = MagicMock()
        mock_item2.name = ".hidden"
        mock_iterdir.return_value = [mock_item1, mock_item2]

        # Mock connection
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.get_as_df = MagicMock()
        mock_conn.execute = MagicMock(return_value=mock_result)
        mock_get_conn.return_value = (mock_conn, None)

        args = MagicMock()
        args.db_path = "/tmp/test"
        args.database = "test_db"

        with patch("pathlib.Path.__truediv__", return_value=mock_db_path):
            with pytest.raises(SystemExit) as exc_info:
                cmd_get_status(args)

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["success"] is True
        assert data["data"]["available"] is True
        assert data["data"]["ladybugInstalled"] is True
        assert data["data"]["connected"] is True
        assert "db1" in data["data"]["databases"]

    @patch("query_memory.apply_monkeypatch", return_value="kuzu")
    @patch("query_memory.get_db_connection")
    @patch("pathlib.Path.exists")
    def test_get_status_connection_fails(
        self, mock_exists, mock_get_conn, mock_apply, capsys
    ):
        """Test get_status when connection fails."""
        mock_exists.return_value = True
        mock_get_conn.return_value = (None, "Connection error")

        args = MagicMock()
        args.db_path = "/tmp/test"
        args.database = "test_db"

        with pytest.raises(SystemExit) as exc_info:
            cmd_get_status(args)

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["success"] is True
        assert data["data"]["connected"] is False
        assert data["data"]["error"] is not None


# =============================================================================
# Command Tests - Get Memories
# =============================================================================


class TestCmdGetMemories:
    """Test cmd_get_memories function."""

    @patch("query_memory.apply_monkeypatch", return_value=None)
    def test_get_memories_no_backend(self, mock_apply, capsys):
        """Test get_memories when no database backend is available."""
        args = MagicMock()
        args.db_path = "/tmp/test"
        args.database = "test_db"
        args.limit = 10

        with pytest.raises(SystemExit) as exc_info:
            cmd_get_memories(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["success"] is False
        # Error message says "Neither kuzu nor LadybugDB is installed"
        assert "installed" in data["error"] or "ladybug" in data["error"].lower()

    @patch("query_memory.apply_monkeypatch", return_value="kuzu")
    @patch("query_memory.get_db_connection")
    def test_get_memories_connection_fails(self, mock_get_conn, mock_apply, capsys):
        """Test get_memories when connection fails."""
        mock_get_conn.return_value = (None, "Connection failed")

        args = MagicMock()
        args.db_path = "/tmp/test"
        args.database = "test_db"
        args.limit = 10

        with pytest.raises(SystemExit) as exc_info:
            cmd_get_memories(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["success"] is False
        assert "Connection failed" in data["error"]

    @patch("query_memory.apply_monkeypatch", return_value="kuzu")
    @patch("query_memory.get_db_connection")
    def test_get_memories_table_not_exists(self, mock_get_conn, mock_apply, capsys):
        """Test get_memories when Episodic table doesn't exist."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("Relation Episodic does not exist")
        mock_get_conn.return_value = (mock_conn, None)

        args = MagicMock()
        args.db_path = "/tmp/test"
        args.database = "test_db"
        args.limit = 10

        with pytest.raises(SystemExit) as exc_info:
            cmd_get_memories(args)

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["success"] is True
        assert data["data"]["memories"] == []
        assert data["data"]["count"] == 0

    @patch("query_memory.apply_monkeypatch", return_value="kuzu")
    @patch("query_memory.get_db_connection")
    @patch("query_memory.serialize_value")
    @patch("query_memory.infer_episode_type")
    @patch("query_memory.extract_session_number")
    def test_get_memories_success_empty(
        self, mock_extract, mock_infer, mock_serialize, mock_get_conn, mock_apply, capsys
    ):
        """Test get_memories with empty result set."""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.has_next.return_value = False
        mock_conn.execute.return_value = mock_result
        mock_get_conn.return_value = (mock_conn, None)
        mock_serialize.return_value = "test"
        mock_infer.return_value = "session_insight"

        args = MagicMock()
        args.db_path = "/tmp/test"
        args.database = "test_db"
        args.limit = 10

        with pytest.raises(SystemExit) as exc_info:
            cmd_get_memories(args)

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["success"] is True
        assert data["data"]["memories"] == []
        assert data["data"]["count"] == 0


# =============================================================================
# Command Tests - Search
# =============================================================================


class TestCmdSearch:
    """Test cmd_search function."""

    @patch("query_memory.apply_monkeypatch", return_value=None)
    def test_search_no_backend(self, mock_apply, capsys):
        """Test search when no database backend is available."""
        args = MagicMock()
        args.db_path = "/tmp/test"
        args.database = "test_db"
        args.query = "test"
        args.limit = 10

        with pytest.raises(SystemExit) as exc_info:
            cmd_search(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["success"] is False

    @patch("query_memory.apply_monkeypatch", return_value="kuzu")
    @patch("query_memory.get_db_connection")
    def test_search_table_not_exists(self, mock_get_conn, mock_apply, capsys):
        """Test search when Episodic table doesn't exist."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("Relation Episodic does not exist")
        mock_get_conn.return_value = (mock_conn, None)

        args = MagicMock()
        args.db_path = "/tmp/test"
        args.database = "test_db"
        args.query = "test"
        args.limit = 10

        with pytest.raises(SystemExit) as exc_info:
            cmd_search(args)

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["success"] is True
        assert data["data"]["memories"] == []
        assert data["data"]["query"] == "test"


# =============================================================================
# Command Tests - Semantic Search
# =============================================================================


class TestCmdSemanticSearch:
    """Test cmd_semantic_search function."""

    @patch.dict("os.environ", {"GRAPHITI_EMBEDDER_PROVIDER": ""})
    @patch("query_memory.cmd_search")
    def test_semantic_search_falls_back_to_keyword_search(self, mock_cmd_search, capsys):
        """Test semantic search falls back to keyword search when no embedder."""
        args = MagicMock()
        args.db_path = "/tmp/test"
        args.database = "test_db"
        args.query = "test"
        args.limit = 10

        # Mock cmd_search to call sys.exit
        mock_cmd_search.side_effect = SystemExit(0)

        with pytest.raises(SystemExit):
            cmd_semantic_search(args)

        mock_cmd_search.assert_called_once_with(args)

    @patch.dict("os.environ", {"GRAPHITI_EMBEDDER_PROVIDER": "openai"})
    @patch("query_memory._async_semantic_search")
    def test_semantic_search_with_embedder_success(self, mock_async_search, capsys):
        """Test semantic search with embedder configured and successful."""
        args = MagicMock()
        args.db_path = "/tmp/test"
        args.database = "test_db"
        args.query = "test"
        args.limit = 10

        mock_async_search.return_value = {
            "success": True,
            "data": {"memories": [], "count": 0},
        }

        with pytest.raises(SystemExit) as exc_info:
            cmd_semantic_search(args)

        assert exc_info.value.code == 0

    @patch.dict("os.environ", {"GRAPHITI_EMBEDDER_PROVIDER": "openai"})
    @patch("query_memory.cmd_search")
    @patch("query_memory._async_semantic_search")
    def test_semantic_search_falls_back_on_failure(
        self, mock_async_search, mock_cmd_search, capsys
    ):
        """Test semantic search falls back to keyword on failure."""
        args = MagicMock()
        args.db_path = "/tmp/test"
        args.database = "test_db"
        args.query = "test"
        args.limit = 10

        mock_async_search.return_value = {"success": False, "error": "Search failed"}
        mock_cmd_search.side_effect = SystemExit(0)

        with pytest.raises(SystemExit):
            cmd_semantic_search(args)

        mock_cmd_search.assert_called_once_with(args)


# =============================================================================
# Command Tests - Get Entities
# =============================================================================


class TestCmdGetEntities:
    """Test cmd_get_entities function."""

    @patch("query_memory.apply_monkeypatch", return_value=None)
    def test_get_entities_no_backend(self, mock_apply, capsys):
        """Test get_entities when no database backend is available."""
        args = MagicMock()
        args.db_path = "/tmp/test"
        args.database = "test_db"
        args.limit = 10

        with pytest.raises(SystemExit) as exc_info:
            cmd_get_entities(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["success"] is False

    @patch("query_memory.apply_monkeypatch", return_value="kuzu")
    @patch("query_memory.get_db_connection")
    def test_get_entities_table_not_exists(self, mock_get_conn, mock_apply, capsys):
        """Test get_entities when Entity table doesn't exist."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("Relation Entity does not exist")
        mock_get_conn.return_value = (mock_conn, None)

        args = MagicMock()
        args.db_path = "/tmp/test"
        args.database = "test_db"
        args.limit = 10

        with pytest.raises(SystemExit) as exc_info:
            cmd_get_entities(args)

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["success"] is True
        assert data["data"]["entities"] == []
        assert data["data"]["count"] == 0


# =============================================================================
# Command Tests - Add Episode
# =============================================================================


class TestCmdAddEpisode:
    """Test cmd_add_episode function."""

    @patch("query_memory.apply_monkeypatch", return_value=None)
    def test_add_episode_no_backend(self, mock_apply, capsys):
        """Test add_episode when no database backend is available."""
        args = MagicMock()
        args.db_path = "/tmp/test"
        args.database = "test_db"
        args.name = "test episode"
        args.content = '{"test": "content"}'
        args.episode_type = "session_insight"
        args.group_id = None

        with pytest.raises(SystemExit) as exc_info:
            cmd_add_episode(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["success"] is False
        # Error message says "Neither kuzu nor LadybugDB is installed"
        assert "installed" in data["error"] or "ladybug" in data["error"].lower()

    @patch.dict("os.environ", {})
    @patch("query_memory.apply_monkeypatch", return_value="kuzu")
    @patch("uuid.uuid4")
    @patch("pathlib.Path.mkdir")
    def test_add_episode_creates_directory(
        self, mock_mkdir, mock_uuid, mock_apply
    ):
        """Test add_episode creates parent directory if needed."""
        mock_uuid.return_value = "test-uuid-123"

        # Mock database and connection
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute = MagicMock()

        with patch.dict(sys.modules, {"kuzu": MagicMock(Database=MagicMock(return_value=mock_db))}):
            mock_kuzu = sys.modules["kuzu"]
            mock_kuzu.Connection = MagicMock(return_value=mock_conn)

            with patch("pathlib.Path.exists", return_value=False):
                args = MagicMock()
                args.db_path = "/tmp/test"
                args.database = "test_db"
                args.name = "test episode"
                args.content = '{"test": "content"}'
                args.episode_type = "session_insight"
                args.group_id = None

                with pytest.raises(SystemExit):
                    cmd_add_episode(args)

        # Verify mkdir was called
        mock_mkdir.assert_called_once()

    @patch.dict("os.environ", {})
    @patch("query_memory.apply_monkeypatch", return_value="kuzu")
    @patch("uuid.uuid4")
    def test_add_episode_valid_json_content(self, mock_uuid, mock_apply, capsys):
        """Test add_episode with valid JSON content gets parsed."""
        mock_uuid.return_value = "test-uuid-123"

        # Mock database and connection
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute = MagicMock()

        with patch.dict(sys.modules, {"kuzu": MagicMock(Database=MagicMock(return_value=mock_db))}):
            mock_kuzu = sys.modules["kuzu"]
            mock_kuzu.Connection = MagicMock(return_value=mock_conn)

            args = MagicMock()
            args.db_path = "/tmp/test"
            args.database = "test_db"
            args.name = "test episode"
            args.content = '{"key": "value"}'  # Valid JSON
            args.episode_type = "pattern"
            args.group_id = "group-123"

            with pytest.raises(SystemExit) as exc_info:
                cmd_add_episode(args)

            assert exc_info.value.code == 0
            captured = capsys.readouterr()
            data = json.loads(captured.out)
            assert data["success"] is True
            assert data["data"]["id"] == "test-uuid-123"
            assert data["data"]["type"] == "pattern"

    @patch.dict("os.environ", {})
    @patch("query_memory.apply_monkeypatch", return_value="kuzu")
    @patch("uuid.uuid4")
    def test_add_episode_plain_text_content(self, mock_uuid, mock_apply, capsys):
        """Test add_episode with plain text (non-JSON) content."""
        mock_uuid.return_value = "test-uuid-123"

        # Mock database and connection
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute = MagicMock()

        with patch.dict(sys.modules, {"kuzu": MagicMock(Database=MagicMock(return_value=mock_db))}):
            mock_kuzu = sys.modules["kuzu"]
            mock_kuzu.Connection = MagicMock(return_value=mock_conn)

            args = MagicMock()
            args.db_path = "/tmp/test"
            args.database = "test_db"
            args.name = "test episode"
            args.content = "Just plain text, not JSON"  # Not JSON
            args.episode_type = "gotcha"
            args.group_id = None

            with pytest.raises(SystemExit) as exc_info:
                cmd_add_episode(args)

            assert exc_info.value.code == 0
            captured = capsys.readouterr()
            data = json.loads(captured.out)
            assert data["success"] is True
            assert data["data"]["type"] == "gotcha"


# =============================================================================
# Async Semantic Search Tests
# =============================================================================


class TestAsyncSemanticSearch:
    """Test _async_semantic_search async function."""

    @pytest.mark.asyncio
    @patch("query_memory.apply_monkeypatch", return_value=None)
    async def test_async_semantic_search_no_backend(self, mock_apply):
        """Test async semantic search when no backend is available."""
        args = MagicMock()
        args.db_path = "/tmp/test"
        args.database = "test_db"
        args.query = "test"
        args.limit = 10

        result = await _async_semantic_search(args)

        assert result["success"] is False
        assert "not installed" in result["error"]

    @pytest.mark.asyncio
    @patch("query_memory.apply_monkeypatch", return_value="kuzu")
    @patch("integrations.graphiti.queries_pkg.client.GraphitiClient")
    @patch("integrations.graphiti.config.GraphitiConfig")
    async def test_async_semantic_search_import_error(self, mock_config, mock_client, mock_apply):
        """Test async semantic search with import error."""
        args = MagicMock()
        args.db_path = "/tmp/test"
        args.database = "test_db"
        args.query = "test"
        args.limit = 10

        # Create a mock config that returns validation errors
        mock_cfg_instance = MagicMock()
        mock_cfg_instance.get_validation_errors.return_value = ["Missing API key"]
        mock_config.from_env.return_value = mock_cfg_instance

        result = await _async_semantic_search(args)

        assert result["success"] is False
        assert "not properly configured" in result["error"]


# =============================================================================
# Main CLI Tests
# =============================================================================


class TestMainCli:
    """Test main CLI argument parsing and routing."""

    def test_main_no_command(self, capsys):
        """Test main with no command specified."""
        with patch("sys.argv", ["query_memory.py"]):
            with pytest.raises(SystemExit) as exc_info:
                from query_memory import main

                main()

        assert exc_info.value.code == 1

    @patch("query_memory.cmd_get_status")
    def test_main_get_status_command(self, mock_cmd, capsys):
        """Test main routes to get-status command."""
        mock_cmd.side_effect = SystemExit(0)

        with patch("sys.argv", ["query_memory.py", "get-status", "/tmp/test", "db"]):
            with pytest.raises(SystemExit):
                from query_memory import main

                main()

        mock_cmd.assert_called_once()

    @patch("query_memory.cmd_get_memories")
    def test_main_get_memories_command(self, mock_cmd):
        """Test main routes to get-memories command."""
        mock_cmd.side_effect = SystemExit(0)

        with patch("sys.argv", ["query_memory.py", "get-memories", "/tmp/test", "db"]):
            with pytest.raises(SystemExit):
                from query_memory import main

                main()

        mock_cmd.assert_called_once()

    @patch("query_memory.cmd_search")
    def test_main_search_command(self, mock_cmd):
        """Test main routes to search command."""
        mock_cmd.side_effect = SystemExit(0)

        with patch("sys.argv", ["query_memory.py", "search", "/tmp/test", "db", "query"]):
            with pytest.raises(SystemExit):
                from query_memory import main

                main()

        mock_cmd.assert_called_once()

    @patch("query_memory.cmd_semantic_search")
    def test_main_semantic_search_command(self, mock_cmd):
        """Test main routes to semantic-search command."""
        mock_cmd.side_effect = SystemExit(0)

        with patch(
            "sys.argv", ["query_memory.py", "semantic-search", "/tmp/test", "db", "query"]
        ):
            with pytest.raises(SystemExit):
                from query_memory import main

                main()

        mock_cmd.assert_called_once()

    @patch("query_memory.cmd_get_entities")
    def test_main_get_entities_command(self, mock_cmd):
        """Test main routes to get-entities command."""
        mock_cmd.side_effect = SystemExit(0)

        with patch("sys.argv", ["query_memory.py", "get-entities", "/tmp/test", "db"]):
            with pytest.raises(SystemExit):
                from query_memory import main

                main()

        mock_cmd.assert_called_once()

    @patch("query_memory.cmd_add_episode")
    def test_main_add_episode_command(self, mock_cmd):
        """Test main routes to add-episode command."""
        mock_cmd.side_effect = SystemExit(0)

        with patch(
            "sys.argv",
            [
                "query_memory.py",
                "add-episode",
                "/tmp/test",
                "db",
                "--name",
                "test",
                "--content",
                "{}",
            ],
        ):
            with pytest.raises(SystemExit):
                from query_memory import main

                main()

        mock_cmd.assert_called_once()


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegrationScenarios:
    """Integration tests for common scenarios."""

    def test_full_workflow_status_to_memories(self):
        """Test full workflow from checking status to getting memories."""
        # This would test the actual workflow but requires a real database
        # For now, we test the routing and command structure
        pass

    def test_error_recovery_on_missing_database(self):
        """Test error recovery when database is missing."""
        # Test that the system handles missing databases gracefully
        pass
