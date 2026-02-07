"""Comprehensive tests for queries.py module."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from integrations.graphiti.queries_pkg.queries import GraphitiQueries


@pytest.fixture
def mock_graphiti_core():
    """Mock graphiti_core module for all tests."""
    mock_episode_type = MagicMock()
    mock_episode_type.text = "text"
    mock_nodes = MagicMock()
    mock_nodes.EpisodeType = mock_episode_type
    mock_graphiti = MagicMock()
    mock_graphiti.nodes = mock_nodes

    with patch.dict("sys.modules", {"graphiti_core": mock_graphiti, "graphiti_core.nodes": mock_nodes}):
        yield


class TestGraphitiQueriesInit:
    """Tests for GraphitiQueries initialization."""

    def test_init(self):
        """Test GraphitiQueries.__init__ stores all parameters."""
        client = MagicMock()
        group_id = "test-group"
        spec_context_id = "test-spec"

        instance = GraphitiQueries(client, group_id, spec_context_id)

        assert instance.client == client
        assert instance.group_id == group_id
        assert instance.spec_context_id == spec_context_id


class TestAddSessionInsight:
    """Tests for add_session_insight method."""

    @pytest.mark.asyncio
    async def test_add_session_insight_success(self, mock_graphiti_core):
        """Test add_session_insight succeeds."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        result = await instance.add_session_insight(1, {"test": "data"})

        assert result is True
        client.graphiti.add_episode.assert_called_once()

        # Verify the call arguments
        call_args = client.graphiti.add_episode.call_args
        assert "session_001_test-spec" in call_args[1]["name"]

    @pytest.mark.asyncio
    async def test_add_session_insight_includes_timestamp(self, mock_graphiti_core):
        """Test add_session_insight includes timestamp."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        await instance.add_session_insight(1, {"test": "data"})

        call_args = client.graphiti.add_episode.call_args
        episode_body = json.loads(call_args[1]["episode_body"])
        assert "timestamp" in episode_body
        assert episode_body["session_number"] == 1

    @pytest.mark.asyncio
    async def test_add_session_insight_error_handling(self, mock_graphiti_core):
        """Test add_session_insight handles errors gracefully."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock(side_effect=Exception("Test error"))

        instance = GraphitiQueries(client, "test-group", "test-spec")
        result = await instance.add_session_insight(1, {"test": "data"})

        assert result is False

    @pytest.mark.asyncio
    async def test_add_session_insight_session_number_padding(self, mock_graphiti_core):
        """Test session number is zero-padded to 3 digits."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")

        await instance.add_session_insight(1, {})
        call_args = client.graphiti.add_episode.call_args
        assert "session_001_" in call_args[1]["name"]

        await instance.add_session_insight(123, {})
        call_args = client.graphiti.add_episode.call_args
        assert "session_123_" in call_args[1]["name"]


class TestAddCodebaseDiscoveries:
    """Tests for add_codebase_discoveries method."""

    @pytest.mark.asyncio
    async def test_add_codebase_discoveries_success(self, mock_graphiti_core):
        """Test add_codebase_discoveries with valid discoveries."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        discoveries = {"file1.py": "Main module", "file2.py": "Helper functions"}

        result = await instance.add_codebase_discoveries(discoveries)

        assert result is True
        client.graphiti.add_episode.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_codebase_discoveries_empty(self, mock_graphiti_core):
        """Test add_codebase_discoveries with empty dict returns True."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        result = await instance.add_codebase_discoveries({})

        assert result is True
        client.graphiti.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_codebase_discoveries_includes_timestamp(self, mock_graphiti_core):
        """Test add_codebase_discoveries includes timestamp."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        await instance.add_codebase_discoveries({"file.py": "purpose"})

        call_args = client.graphiti.add_episode.call_args
        episode_body = json.loads(call_args[1]["episode_body"])
        assert "timestamp" in episode_body
        assert episode_body["files"] == {"file.py": "purpose"}

    @pytest.mark.asyncio
    async def test_add_codebase_discoveries_error_handling(self, mock_graphiti_core):
        """Test add_codebase_discoveries handles errors."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock(side_effect=Exception("DB error"))

        instance = GraphitiQueries(client, "test-group", "test-spec")
        result = await instance.add_codebase_discoveries({"file.py": "purpose"})

        assert result is False


class TestAddPattern:
    """Tests for add_pattern method."""

    @pytest.mark.asyncio
    async def test_add_pattern_success(self, mock_graphiti_core):
        """Test add_pattern with valid pattern."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        result = await instance.add_pattern("Use dependency injection for testability")

        assert result is True
        client.graphiti.add_episode.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_pattern_includes_timestamp(self, mock_graphiti_core):
        """Test add_pattern includes timestamp."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        await instance.add_pattern("Test pattern")

        call_args = client.graphiti.add_episode.call_args
        episode_body = json.loads(call_args[1]["episode_body"])
        assert "timestamp" in episode_body
        assert episode_body["pattern"] == "Test pattern"

    @pytest.mark.asyncio
    async def test_add_pattern_long_text(self, mock_graphiti_core):
        """Test add_pattern with long pattern text."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        long_pattern = "x" * 500
        result = await instance.add_pattern(long_pattern)

        assert result is True

    @pytest.mark.asyncio
    async def test_add_pattern_error_handling(self, mock_graphiti_core):
        """Test add_pattern handles errors."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock(side_effect=RuntimeError("Connection failed"))

        instance = GraphitiQueries(client, "test-group", "test-spec")
        result = await instance.add_pattern("Test pattern")

        assert result is False


class TestAddGotcha:
    """Tests for add_gotcha method."""

    @pytest.mark.asyncio
    async def test_add_gotcha_success(self, mock_graphiti_core):
        """Test add_gotcha with valid gotcha."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        result = await instance.add_gotcha("Always validate JWT tokens server-side")

        assert result is True
        client.graphiti.add_episode.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_gotcha_includes_timestamp(self, mock_graphiti_core):
        """Test add_gotcha includes timestamp."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        await instance.add_gotcha("Test gotcha")

        call_args = client.graphiti.add_episode.call_args
        episode_body = json.loads(call_args[1]["episode_body"])
        assert "timestamp" in episode_body
        assert episode_body["gotcha"] == "Test gotcha"

    @pytest.mark.asyncio
    async def test_add_gotcha_error_handling(self, mock_graphiti_core):
        """Test add_gotcha handles errors."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock(side_effect=ValueError("Invalid input"))

        instance = GraphitiQueries(client, "test-group", "test-spec")
        result = await instance.add_gotcha("Test gotcha")

        assert result is False


class TestAddTaskOutcome:
    """Tests for add_task_outcome method."""

    @pytest.mark.asyncio
    async def test_add_task_outcome_success(self, mock_graphiti_core):
        """Test add_task_outcome with valid outcome."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        result = await instance.add_task_outcome(
            task_id="task-1",
            success=True,
            outcome="Implemented OAuth login successfully",
        )

        assert result is True
        client.graphiti.add_episode.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_task_outcome_with_metadata(self, mock_graphiti_core):
        """Test add_task_outcome with metadata."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        result = await instance.add_task_outcome(
            task_id="task-1",
            success=True,
            outcome="Success",
            metadata={"files_changed": 5, "duration_seconds": 120},
        )

        assert result is True

        call_args = client.graphiti.add_episode.call_args
        episode_body = json.loads(call_args[1]["episode_body"])
        assert episode_body["files_changed"] == 5
        assert episode_body["duration_seconds"] == 120

    @pytest.mark.asyncio
    async def test_add_task_outcome_includes_all_fields(self, mock_graphiti_core):
        """Test add_task_outcome includes all expected fields."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        await instance.add_task_outcome("task-1", False, "Failed due to timeout")

        call_args = client.graphiti.add_episode.call_args
        episode_body = json.loads(call_args[1]["episode_body"])

        assert episode_body["task_id"] == "task-1"
        assert episode_body["success"] is False
        assert episode_body["outcome"] == "Failed due to timeout"
        assert "timestamp" in episode_body

    @pytest.mark.asyncio
    async def test_add_task_outcome_name_generation(self, mock_graphiti_core):
        """Test task outcome name includes task ID."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        await instance.add_task_outcome("my-task-123", True, "Success")

        call_args = client.graphiti.add_episode.call_args
        assert "task_outcome_my-task-123_" in call_args[1]["name"]

    @pytest.mark.asyncio
    async def test_add_task_outcome_error_handling(self, mock_graphiti_core):
        """Test add_task_outcome handles errors."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock(side_effect=IOError("Disk full"))

        instance = GraphitiQueries(client, "test-group", "test-spec")
        result = await instance.add_task_outcome("task-1", True, "Success")

        assert result is False


class TestAddStructuredInsights:
    """Tests for add_structured_insights method."""

    @pytest.mark.asyncio
    async def test_add_structured_insights_empty(self, mock_graphiti_core):
        """Test add_structured_insights with empty dict returns True."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        result = await instance.add_structured_insights({})

        assert result is True
        client.graphiti.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_structured_insights_file_insights(self, mock_graphiti_core):
        """Test add_structured_insights with file insights."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        insights = {
            "file_insights": [
                {
                    "path": "src/auth.py",
                    "purpose": "Authentication module",
                    "changes_made": "Added OAuth support",
                    "patterns_used": ["factory pattern"],
                    "gotchas": [],
                }
            ]
        }

        result = await instance.add_structured_insights(insights)

        assert result is True
        assert client.graphiti.add_episode.call_count == 1

    @pytest.mark.asyncio
    async def test_add_structured_insights_patterns_discovered(self, mock_graphiti_core):
        """Test add_structured_insights with patterns."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        insights = {
            "patterns_discovered": [
                {"pattern": "Use async/await for I/O operations", "applies_to": "backend", "example": "file reading"},
                {"pattern": "Dependency injection", "applies_to": "services"},
            ]
        }

        result = await instance.add_structured_insights(insights)

        assert result is True
        assert client.graphiti.add_episode.call_count == 2

    @pytest.mark.asyncio
    async def test_add_structured_insights_gotchas_discovered(self, mock_graphiti_core):
        """Test add_structured_insights with gotchas."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        insights = {
            "gotchas_discovered": [
                {"gotcha": "Never hardcode credentials", "trigger": "deployment", "solution": "Use env vars"},
            ]
        }

        result = await instance.add_structured_insights(insights)

        assert result is True
        assert client.graphiti.add_episode.call_count == 1

    @pytest.mark.asyncio
    async def test_add_structured_insights_approach_outcome(self, mock_graphiti_core):
        """Test add_structured_insights with approach outcome."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        insights = {
            "subtask_id": "task-1",
            "approach_outcome": {
                "success": True,
                "approach_used": "Used existing library",
                "why_it_worked": "Well-maintained and documented",
                "alternatives_tried": ["custom implementation"],
            },
        }

        result = await instance.add_structured_insights(insights)

        assert result is True
        assert client.graphiti.add_episode.call_count == 1

    @pytest.mark.asyncio
    async def test_add_structured_insights_recommendations(self, mock_graphiti_core):
        """Test add_structured_insights with recommendations."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        insights = {
            "subtask_id": "task-1",
            "session_num": 1,
            "success": True,
            "recommendations": [
                "Add more tests",
                "Document API endpoints",
            ],
        }

        result = await instance.add_structured_insights(insights)

        assert result is True

    @pytest.mark.asyncio
    async def test_add_structured_insights_all_types(self, mock_graphiti_core):
        """Test add_structured_insights with all insight types."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        insights = {
            "file_insights": [{"path": "test.py", "purpose": "Test file"}],
            "patterns_discovered": [{"pattern": "Test pattern"}],
            "gotchas_discovered": [{"gotcha": "Test gotcha"}],
            "subtask_id": "task-1",
            "approach_outcome": {"success": True, "approach_used": "Test approach"},
            "recommendations": ["Test recommendation"],
        }

        result = await instance.add_structured_insights(insights)

        assert result is True
        # Should call add_episode for each non-empty insight type
        assert client.graphiti.add_episode.call_count >= 4

    @pytest.mark.asyncio
    async def test_add_structured_insights_string_patterns(self, mock_graphiti_core):
        """Test add_structured_insights handles string patterns."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        insights = {
            "patterns_discovered": ["String pattern 1", "String pattern 2"],
            "gotchas_discovered": ["String gotcha 1"],
        }

        result = await instance.add_structured_insights(insights)

        assert result is True
        assert client.graphiti.add_episode.call_count == 3

    @pytest.mark.asyncio
    async def test_add_structured_insights_duplicate_facts_error(self, mock_graphiti_core):
        """Test add_structured_insights handles duplicate_facts errors."""
        client = MagicMock()
        client.graphiti = MagicMock()

        # Simulate duplicate_facts error for first call
        client.graphiti.add_episode = AsyncMock(side_effect=[Exception("duplicate_facts error"), AsyncMock()])

        instance = GraphitiQueries(client, "test-group", "test-spec")
        insights = {
            "file_insights": [{"path": "test.py", "purpose": "Test"}],
        }

        result = await instance.add_structured_insights(insights)

        # Should still return True despite duplicate_facts error
        assert result is True

    @pytest.mark.asyncio
    async def test_add_structured_insights_partial_failure(self, mock_graphiti_core):
        """Test add_structured_insights returns True if some episodes fail."""
        client = MagicMock()
        client.graphiti = MagicMock()

        # First succeeds, second fails
        client.graphiti.add_episode = AsyncMock(side_effect=[None, Exception("Failed")])

        instance = GraphitiQueries(client, "test-group", "test-spec")
        insights = {
            "patterns_discovered": ["pattern 1", "pattern 2"],
        }

        result = await instance.add_structured_insights(insights)

        # Should return True if at least one succeeded
        assert result is True

    @pytest.mark.asyncio
    async def test_add_structured_insights_complete_failure(self, mock_graphiti_core):
        """Test add_structured_insights returns False if all fail."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock(side_effect=Exception("All failed"))

        instance = GraphitiQueries(client, "test-group", "test-spec")
        insights = {
            "patterns_discovered": ["pattern 1"],
        }

        result = await instance.add_structured_insights(insights)

        assert result is False

    @pytest.mark.asyncio
    async def test_add_structured_insights_exception_handling(self, mock_graphiti_core):
        """Test add_structured_insights outer exception handling."""
        client = MagicMock()
        client.graphiti = MagicMock()
        # Non-duplicate error should be caught
        client.graphiti.add_episode = AsyncMock(side_effect=Exception("Non-duplicate error"))

        instance = GraphitiQueries(client, "test-group", "test-spec")
        insights = {
            "patterns_discovered": ["pattern 1"],
        }

        result = await instance.add_structured_insights(insights)

        # First failure logs debug, continues, total_count=1, saved_count=0
        # After loop, saved_count=0, total_count=1, returns False
        assert result is False

    @pytest.mark.asyncio
    async def test_add_structured_insights_changed_files(self, mock_graphiti_core):
        """Test add_structured_insights includes changed_files."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        insights = {
            "subtask_id": "task-1",
            "approach_outcome": {"success": True, "approach_used": "Test"},
            "changed_files": ["file1.py", "file2.py"],
        }

        await instance.add_structured_insights(insights)

        call_args = client.graphiti.add_episode.call_args
        episode_body = json.loads(call_args[1]["episode_body"])
        assert episode_body["changed_files"] == ["file1.py", "file2.py"]

    @pytest.mark.asyncio
    async def test_add_structured_insights_recommendations_with_session(self, mock_graphiti_core):
        """Test add_structured_insights recommendations include session info."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        insights = {
            "subtask_id": "task-1",
            "session_num": 5,
            "success": True,
            "recommendations": ["Test recommendation"],
        }

        await instance.add_structured_insights(insights)

        call_args = client.graphiti.add_episode.call_args
        episode_body = json.loads(call_args[1]["episode_body"])
        assert episode_body["subtask_id"] == "task-1"
        assert episode_body["session_number"] == 5
        assert episode_body["success"] is True

    @pytest.mark.asyncio
    async def test_add_structured_insights_outcome_without_subtask_id(self, mock_graphiti_core):
        """Test add_structured_insights outcome without subtask_id."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        insights = {
            "approach_outcome": {"success": True, "approach_used": "Test"},
        }

        await instance.add_structured_insights(insights)

        call_args = client.graphiti.add_episode.call_args
        episode_body = json.loads(call_args[1]["episode_body"])
        assert episode_body["task_id"] == "unknown"

    @pytest.mark.asyncio
    async def test_add_structured_insights_minimal_dict_pattern(self, mock_graphiti_core):
        """Test add_structured_insights with minimal dict pattern."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        insights = {
            "patterns_discovered": [
                {"pattern": "Minimal"},  # Has pattern key
                {"other_key": "value"},  # No pattern key
            ]
        }

        await instance.add_structured_insights(insights)

        # Should handle both cases
        assert client.graphiti.add_episode.call_count == 2

    @pytest.mark.asyncio
    async def test_add_structured_insights_minimal_dict_gotcha(self, mock_graphiti_core):
        """Test add_structured_insights with minimal dict gotcha."""
        client = MagicMock()
        client.graphiti = MagicMock()
        client.graphiti.add_episode = AsyncMock()

        instance = GraphitiQueries(client, "test-group", "test-spec")
        insights = {
            "gotchas_discovered": [
                {"gotcha": "Test gotcha"},  # Has gotcha key
                {"other_key": "value"},  # No gotcha key
            ]
        }

        await instance.add_structured_insights(insights)

        assert client.graphiti.add_episode.call_count == 2
