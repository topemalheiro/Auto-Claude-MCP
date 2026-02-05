"""Comprehensive tests for search.py module."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from integrations.graphiti.queries_pkg.search import GraphitiSearch
from integrations.graphiti.queries_pkg.schema import GroupIdMode, MAX_CONTEXT_RESULTS


@pytest.fixture
def mock_client():
    """Create a mock GraphitiClient."""
    client = MagicMock()
    client.graphiti = MagicMock()
    client.graphiti.search = AsyncMock(return_value=[])
    return client


@pytest.fixture
def search(mock_client):
    """Create a GraphitiSearch instance."""
    return GraphitiSearch(
        client=mock_client,
        group_id="test-group",
        spec_context_id="test-spec",
        group_id_mode=GroupIdMode.SPEC,
        project_dir=Path("/tmp/test_project")
    )


class TestGraphitiSearchInit:
    """Tests for GraphitiSearch.__init__"""

    def test_init_stores_attributes(self, mock_client):
        """Test initialization stores all attributes."""
        search = GraphitiSearch(
            client=mock_client,
            group_id="test-group",
            spec_context_id="test-spec",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/tmp/test_project")
        )

        assert search.client == mock_client
        assert search.group_id == "test-group"
        assert search.spec_context_id == "test-spec"
        assert search.group_id_mode == GroupIdMode.SPEC
        assert search.project_dir == Path("/tmp/test_project")


class TestGetRelevantContext:
    """Tests for get_relevant_context method."""

    @pytest.mark.asyncio
    async def test_get_relevant_context_success(self, search, mock_client):
        """Test successful context retrieval."""
        mock_result = MagicMock()
        mock_result.content = "Test content about database connections"
        mock_result.score = 0.85
        mock_result.type = "pattern"

        mock_client.graphiti.search.return_value = [mock_result]

        results = await search.get_relevant_context("database patterns")

        assert len(results) == 1
        assert results[0]["content"] == "Test content about database connections"
        assert results[0]["score"] == 0.85
        assert results[0]["type"] == "pattern"

    @pytest.mark.asyncio
    async def test_get_relevant_context_empty(self, search, mock_client):
        """Test empty results."""
        mock_client.graphiti.search.return_value = []

        results = await search.get_relevant_context("nothing")

        assert results == []

    @pytest.mark.asyncio
    async def test_get_relevant_context_with_fact_attribute(self, search, mock_client):
        """Test when result has fact attribute instead of content."""
        mock_result = MagicMock()
        del mock_result.content  # Remove content
        mock_result.fact = "Fact about patterns"
        mock_result.score = 0.75
        mock_result.type = "gotcha"

        mock_client.graphiti.search.return_value = [mock_result]

        results = await search.get_relevant_context("patterns")

        assert len(results) == 1
        assert results[0]["content"] == "Fact about patterns"

    @pytest.mark.asyncio
    async def test_get_relevant_context_with_str_result(self, search, mock_client):
        """Test when result has neither content nor fact (uses str)."""
        mock_result = MagicMock()
        del mock_result.content
        del mock_result.fact
        mock_result.score = 0.65
        mock_result.type = "unknown"
        mock_result.__str__ = lambda self: "String representation"

        mock_client.graphiti.search.return_value = [mock_result]

        results = await search.get_relevant_context("test")

        assert len(results) == 1
        assert results[0]["content"] == "String representation"

    @pytest.mark.asyncio
    async def test_get_relevant_context_with_min_score_filter(self, search, mock_client):
        """Test minimum score filtering."""
        mock_results = [
            MagicMock(content="High score", score=0.9, type="pattern"),
            MagicMock(content="Low score", score=0.3, type="gotcha"),
            MagicMock(content="Medium score", score=0.6, type="pattern"),
        ]
        mock_client.graphiti.search.return_value = mock_results

        results = await search.get_relevant_context("test", min_score=0.5)

        assert len(results) == 2
        assert all(r["score"] >= 0.5 for r in results)

    @pytest.mark.asyncio
    async def test_get_relevant_context_include_project_context_spec_mode(self, search, mock_client):
        """Test project context inclusion in SPEC mode."""
        search.group_id_mode = GroupIdMode.SPEC
        search.project_dir = Path("/tmp/auto_claude")

        results = await search.get_relevant_context("test", include_project_context=True)

        # Should search both spec and project groups
        mock_client.graphiti.search.assert_called_once()
        call_args = mock_client.graphiti.search.call_args
        group_ids = call_args[1]["group_ids"]
        assert len(group_ids) == 2  # spec and project groups

    @pytest.mark.asyncio
    async def test_get_relevant_context_no_project_context(self, search, mock_client):
        """Test without including project context."""
        results = await search.get_relevant_context("test", include_project_context=False)

        mock_client.graphiti.search.assert_called_once()
        call_args = mock_client.graphiti.search.call_args
        group_ids = call_args[1]["group_ids"]
        assert group_ids == ["test-group"]

    @pytest.mark.asyncio
    async def test_get_relevant_context_exception_handling(self, search, mock_client):
        """Test exception handling."""
        mock_client.graphiti.search.side_effect = RuntimeError("Search failed")

        results = await search.get_relevant_context("test")

        assert results == []


class TestGetSessionHistory:
    """Tests for get_session_history method."""

    @pytest.mark.asyncio
    async def test_get_session_history_success(self, search, mock_client):
        """Test successful session history retrieval."""
        mock_result = MagicMock()
        mock_result.content = json.dumps({
            "type": "session_insight",
            "spec_id": "test-spec",
            "session_number": 1,
            "subtasks_completed": ["task-1"]
        })
        mock_result.fact = None
        mock_result.score = 0.8

        mock_client.graphiti.search.return_value = [mock_result]

        results = await search.get_session_history(limit=5)

        assert len(results) == 1
        assert results[0]["session_number"] == 1

    @pytest.mark.asyncio
    async def test_get_session_history_filters_by_spec(self, search, mock_client):
        """Test filtering by spec when spec_only=True."""
        mock_result1 = MagicMock(
            content=json.dumps({
                "type": "session_insight",
                "spec_id": "test-spec",
                "session_number": 1
            }),
            fact=None
        )
        mock_result2 = MagicMock(
            content=json.dumps({
                "type": "session_insight",
                "spec_id": "other-spec",
                "session_number": 2
            }),
            fact=None
        )

        mock_client.graphiti.search.return_value = [mock_result1, mock_result2]

        results = await search.get_session_history(limit=5, spec_only=True)

        # Should only return test-spec results
        assert all(r["spec_id"] == "test-spec" for r in results)

    @pytest.mark.asyncio
    async def test_get_session_history_all_specs(self, search, mock_client):
        """Test returning all specs when spec_only=False."""
        mock_result = MagicMock(
            content=json.dumps({
                "type": "session_insight",
                "spec_id": "any-spec",
                "session_number": 1
            }),
            fact=None
        )

        mock_client.graphiti.search.return_value = [mock_result]

        results = await search.get_session_history(limit=5, spec_only=False)

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_session_history_sorting(self, search, mock_client):
        """Test results are sorted by session_number descending."""
        mock_results = [
            MagicMock(
                content=json.dumps({
                    "type": "session_insight",
                    "spec_id": "test-spec",  # Add spec_id to pass filter
                    "session_number": 1
                }),
                fact=None,
                score=0.8
            ),
            MagicMock(
                content=json.dumps({
                    "type": "session_insight",
                    "spec_id": "test-spec",  # Add spec_id to pass filter
                    "session_number": 3
                }),
                fact=None,
                score=0.8
            ),
            MagicMock(
                content=json.dumps({
                    "type": "session_insight",
                    "spec_id": "test-spec",  # Add spec_id to pass filter
                    "session_number": 2
                }),
                fact=None,
                score=0.8
            ),
        ]

        mock_client.graphiti.search.return_value = mock_results

        results = await search.get_session_history(limit=5, spec_only=True)

        # Should be sorted by session_number descending
        assert len(results) == 3
        assert results[0]["session_number"] == 3
        assert results[1]["session_number"] == 2
        assert results[2]["session_number"] == 1

    @pytest.mark.asyncio
    async def test_get_session_history_respects_limit(self, search, mock_client):
        """Test limit parameter is respected."""
        mock_results = [
            MagicMock(
                content=json.dumps({
                    "type": "session_insight",
                    "spec_id": "test-spec",
                    "session_number": i
                }),
                fact=None
            ) for i in range(10)
        ]

        mock_client.graphiti.search.return_value = mock_results

        results = await search.get_session_history(limit=3, spec_only=True)

        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_get_session_history_handles_invalid_json(self, search, mock_client):
        """Test handling of malformed JSON."""
        mock_result = MagicMock()
        mock_result.content = "invalid json"
        mock_result.fact = None

        mock_client.graphiti.search.return_value = [mock_result]

        results = await search.get_session_history(limit=5)

        # Should skip invalid results
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_get_session_history_exception_handling(self, search, mock_client):
        """Test exception handling."""
        mock_client.graphiti.search.side_effect = RuntimeError("Search failed")

        results = await search.get_session_history(limit=5)

        assert results == []


class TestGetSimilarTaskOutcomes:
    """Tests for get_similar_task_outcomes method."""

    @pytest.mark.asyncio
    async def test_get_similar_task_outcomes_success(self, search, mock_client):
        """Test successful task outcomes retrieval."""
        mock_result = MagicMock()
        mock_result.content = json.dumps({
            "type": "task_outcome",
            "task_id": "auth-implementation",
            "success": True,
            "outcome": "OAuth integration completed successfully",
            "score": 0.85
        })
        mock_result.score = 0.85

        mock_client.graphiti.search.return_value = [mock_result]

        results = await search.get_similar_task_outcomes("Implement OAuth", limit=5)

        assert len(results) == 1
        assert results[0]["task_id"] == "auth-implementation"
        assert results[0]["success"] is True

    @pytest.mark.asyncio
    async def test_get_similar_task_outcomes_respects_limit(self, search, mock_client):
        """Test limit parameter."""
        mock_results = [
            MagicMock(
                content=json.dumps({
                    "type": "task_outcome",
                    "task_id": f"task-{i}",
                    "success": True
                }),
                score=0.8
            ) for i in range(10)
        ]

        mock_client.graphiti.search.return_value = mock_results

        results = await search.get_similar_task_outcomes("test", limit=3)

        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_get_similar_task_outcomes_exception_handling(self, search, mock_client):
        """Test exception handling."""
        mock_client.graphiti.search.side_effect = RuntimeError("Search failed")

        results = await search.get_similar_task_outcomes("test")

        assert results == []


class TestGetPatternsAndGotchas:
    """Tests for get_patterns_and_gotchas method."""

    @pytest.mark.asyncio
    async def test_get_patterns_and_gotchas_success(self, search, mock_client):
        """Test successful patterns and gotchas retrieval."""
        # Mock pattern results
        pattern_result = MagicMock()
        pattern_result.content = json.dumps({
            "type": "pattern",
            "pattern": "Use DI for database",
            "applies_to": "backend services",
            "example": "Injecting DB connection"
        })
        pattern_result.score = 0.9

        # Mock gotcha results
        gotcha_result = MagicMock()
        gotcha_result.content = json.dumps({
            "type": "gotcha",
            "gotcha": "Close DB connections",
            "trigger": "Long-running processes",
            "solution": "Use context managers"
        })
        gotcha_result.score = 0.85

        def search_side_effect(*args, **kwargs):
            query = kwargs.get("query", "")
            if "pattern:" in query:
                return [pattern_result]
            else:
                return [gotcha_result]

        mock_client.graphiti.search.side_effect = search_side_effect

        patterns, gotchas = await search.get_patterns_and_gotchas("database connection")

        assert len(patterns) == 1
        assert len(gotchas) == 1
        assert patterns[0]["pattern"] == "Use DI for database"
        assert gotchas[0]["gotcha"] == "Close DB connections"

    @pytest.mark.asyncio
    async def test_get_patterns_and_gotchas_filters_by_min_score(self, search, mock_client):
        """Test minimum score filtering."""
        pattern_results = [
            MagicMock(
                content=json.dumps({"type": "pattern", "pattern": "High score"}),
                score=0.9
            ),
            MagicMock(
                content=json.dumps({"type": "pattern", "pattern": "Low score"}),
                score=0.3
            ),
        ]

        def search_side_effect(*args, **kwargs):
            return pattern_results

        mock_client.graphiti.search.side_effect = search_side_effect

        patterns, gotchas = await search.get_patterns_and_gotchas("test", min_score=0.5)

        assert len(patterns) == 1
        assert patterns[0]["score"] == 0.9

    @pytest.mark.asyncio
    async def test_get_patterns_and_gotchas_respects_num_results(self, search, mock_client):
        """Test num_results parameter."""
        pattern_results = [
            MagicMock(
                content=json.dumps({"type": "pattern", "pattern": f"Pattern {i}"}),
                score=0.8 + (i * 0.01)
            ) for i in range(10)
        ]

        def search_side_effect(*args, **kwargs):
            return pattern_results

        mock_client.graphiti.search.side_effect = search_side_effect

        patterns, gotchas = await search.get_patterns_and_gotchas("test", num_results=3)

        assert len(patterns) <= 3

    @pytest.mark.asyncio
    async def test_get_patterns_and_gotchas_sorting(self, search, mock_client):
        """Test results are sorted by score."""
        pattern_results = [
            MagicMock(
                content=json.dumps({"type": "pattern", "pattern": f"Pattern {i}"}),
                score=0.5 + (i * 0.1)
            ) for i in [3, 1, 2]  # Unordered scores
        ]

        def search_side_effect(*args, **kwargs):
            return pattern_results

        mock_client.graphiti.search.side_effect = search_side_effect

        patterns, gotchas = await search.get_patterns_and_gotchas("test", num_results=10)

        # Should be sorted by score descending
        scores = [p["score"] for p in patterns]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_get_patterns_and_gotchas_exception_handling(self, search, mock_client):
        """Test exception handling."""
        mock_client.graphiti.search.side_effect = RuntimeError("Search failed")

        patterns, gotchas = await search.get_patterns_and_gotchas("test")

        assert patterns == []
        assert gotchas == []

    @pytest.mark.asyncio
    async def test_get_patterns_and_gotchas_handles_invalid_json(self, search, mock_client):
        """Test handling of malformed JSON."""
        mock_result = MagicMock()
        mock_result.content = "invalid json"
        mock_result.score = 0.9

        mock_client.graphiti.search.return_value = [mock_result]

        patterns, gotchas = await search.get_patterns_and_gotchas("test")

        # Should skip invalid results
        assert len(patterns) == 0
        assert len(gotchas) == 0

    @pytest.mark.asyncio
    async def test_get_patterns_and_gotchas_filters_non_dict_content(self, search, mock_client):
        """Test filtering non-dict content (fix for ACS-215)."""
        # Return list instead of dict (malformed)
        mock_result = MagicMock()
        mock_result.content = json.dumps(["not", "a", "dict"])
        mock_result.score = 0.9

        mock_client.graphiti.search.return_value = [mock_result]

        patterns, gotchas = await search.get_patterns_and_gotchas("test")

        # Should skip non-dict results
        assert len(patterns) == 0
        assert len(gotchas) == 0
