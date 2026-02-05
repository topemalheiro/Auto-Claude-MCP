"""
Comprehensive tests for queries_pkg/search.py module.

Tests GraphitiSearch class including context retrieval, session history,
task outcomes, and pattern/gotcha search functionality.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import hashlib

import pytest

from integrations.graphiti.queries_pkg.search import GraphitiSearch
from integrations.graphiti.queries_pkg.schema import (
    EPISODE_TYPE_SESSION_INSIGHT,
    EPISODE_TYPE_PATTERN,
    EPISODE_TYPE_GOTCHA,
    EPISODE_TYPE_TASK_OUTCOME,
    MAX_CONTEXT_RESULTS,
    GroupIdMode,
)


class TestGraphitiSearchInit:
    """Tests for GraphitiSearch initialization."""

    def test_init_default_values(self):
        """Test GraphitiSearch initialization with default values."""
        mock_client = MagicMock()
        group_id = "test_group"
        spec_context_id = "spec_123"
        group_id_mode = GroupIdMode.SPEC
        project_dir = Path("/test/project")

        search = GraphitiSearch(
            client=mock_client,
            group_id=group_id,
            spec_context_id=spec_context_id,
            group_id_mode=group_id_mode,
            project_dir=project_dir,
        )

        assert search.client == mock_client
        assert search.group_id == group_id
        assert search.spec_context_id == spec_context_id
        assert search.group_id_mode == group_id_mode
        assert search.project_dir == project_dir


class TestGetRelevantContext:
    """Tests for get_relevant_context method."""

    @pytest.mark.asyncio
    async def test_get_relevant_context_basic(self):
        """Test basic context retrieval."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()
        mock_result = MagicMock()
        mock_result.content = "test content"
        mock_result.score = 0.9
        mock_result.type = "pattern"
        mock_graphiti.search = AsyncMock(return_value=[mock_result])
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        results = await search.get_relevant_context("test query")

        assert len(results) == 1
        assert results[0]["content"] == "test content"
        assert results[0]["score"] == 0.9
        assert results[0]["type"] == "pattern"

        mock_graphiti.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_relevant_context_custom_num_results(self):
        """Test get_relevant_context with custom num_results."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        await search.get_relevant_context("test query", num_results=5)

        call_args = mock_graphiti.search.call_args
        assert call_args.kwargs["num_results"] == 5

    @pytest.mark.asyncio
    async def test_get_relevant_context_respects_max_limit(self):
        """Test get_relevant_context respects MAX_CONTEXT_RESULTS."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        # Request more than MAX_CONTEXT_RESULTS
        await search.get_relevant_context("test query", num_results=100)

        call_args = mock_graphiti.search.call_args
        # Should be capped at MAX_CONTEXT_RESULTS
        assert call_args.kwargs["num_results"] == MAX_CONTEXT_RESULTS

    @pytest.mark.asyncio
    async def test_get_relevant_context_spec_mode_without_project(self):
        """Test spec mode without including project context."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="spec_group_123",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        await search.get_relevant_context(
            "test query",
            include_project_context=False
        )

        call_args = mock_graphiti.search.call_args
        # Should only search spec group
        assert call_args.kwargs["group_ids"] == ["spec_group_123"]

    @pytest.mark.asyncio
    async def test_get_relevant_context_spec_mode_with_project(self):
        """Test spec mode with including project context."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        mock_client.graphiti = mock_graphiti

        project_dir = Path("/test/project")
        project_name = project_dir.name
        path_hash = hashlib.md5(
            str(project_dir.resolve()).encode(),
            usedforsecurity=False
        ).hexdigest()[:8]
        expected_project_group_id = f"project_{project_name}_{path_hash}"

        search = GraphitiSearch(
            client=mock_client,
            group_id="spec_group_123",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=project_dir,
        )

        await search.get_relevant_context(
            "test query",
            include_project_context=True
        )

        call_args = mock_graphiti.search.call_args
        # Should search both spec and project groups
        assert "spec_group_123" in call_args.kwargs["group_ids"]
        assert expected_project_group_id in call_args.kwargs["group_ids"]

    @pytest.mark.asyncio
    async def test_get_relevant_context_project_mode(self):
        """Test project mode context retrieval."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="project_group_123",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.PROJECT,
            project_dir=Path("/test/project"),
        )

        await search.get_relevant_context("test query")

        call_args = mock_graphiti.search.call_args
        # Should only search project group
        assert call_args.kwargs["group_ids"] == ["project_group_123"]

    @pytest.mark.asyncio
    async def test_get_relevant_context_with_min_score_filter(self):
        """Test get_relevant_context with min_score filtering."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()

        # Create results with varying scores
        results = []
        for i, score in enumerate([0.9, 0.7, 0.5, 0.3, 0.1]):
            result = MagicMock()
            result.content = f"content_{i}"
            result.score = score
            result.type = "pattern"
            results.append(result)

        mock_graphiti.search = AsyncMock(return_value=results)
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        filtered_results = await search.get_relevant_context(
            "test query",
            min_score=0.5
        )

        # Should only return results with score >= 0.5
        assert len(filtered_results) == 3
        assert all(r["score"] >= 0.5 for r in filtered_results)

    @pytest.mark.asyncio
    async def test_get_relevant_context_result_fact_attribute(self):
        """Test get_relevant_context uses fact attribute when content not present."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()

        mock_result = MagicMock()
        # No content attribute
        del mock_result.content
        mock_result.fact = "fact content"
        mock_result.score = 0.8
        mock_result.type = "gotcha"

        mock_graphiti.search = AsyncMock(return_value=[mock_result])
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        results = await search.get_relevant_context("test query")

        assert len(results) == 1
        assert results[0]["content"] == "fact content"

    @pytest.mark.asyncio
    async def test_get_relevant_context_result_str_conversion(self):
        """Test get_relevant_context converts result to string."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()

        mock_result = MagicMock()
        # No content or fact attribute
        del mock_result.content
        del mock_result.fact
        mock_result.score = 0.8
        mock_result.__str__ = lambda self: "string representation"

        mock_graphiti.search = AsyncMock(return_value=[mock_result])
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        results = await search.get_relevant_context("test query")

        assert len(results) == 1
        assert results[0]["content"] == "string representation"

    @pytest.mark.asyncio
    @patch("integrations.graphiti.queries_pkg.search.capture_exception")
    async def test_get_relevant_context_exception_handling(self, mock_capture):
        """Test get_relevant_context handles exceptions gracefully."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(side_effect=RuntimeError("Search failed"))
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        results = await search.get_relevant_context("test query")

        assert results == []
        mock_capture.assert_called()

    @pytest.mark.asyncio
    async def test_get_relevant_context_empty_query(self):
        """Test get_relevant_context with empty query."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        results = await search.get_relevant_context("")

        assert results == []
        mock_graphiti.search.assert_called_once()


class TestGetSessionHistory:
    """Tests for get_session_history method."""

    @pytest.mark.asyncio
    async def test_get_session_history_basic(self):
        """Test basic session history retrieval."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()

        # Create mock session insight
        session_data = {
            "type": EPISODE_TYPE_SESSION_INSIGHT,
            "spec_id": "spec_123",
            "session_number": 5,
            "summary": "Session completed successfully",
        }
        mock_result = MagicMock()
        mock_result.content = json.dumps(session_data)
        mock_result.score = 0.9

        mock_graphiti.search = AsyncMock(return_value=[mock_result])
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        sessions = await search.get_session_history()

        assert len(sessions) == 1
        assert sessions[0]["session_number"] == 5

    @pytest.mark.asyncio
    async def test_get_session_history_spec_only_filters_correctly(self):
        """Test get_session_history with spec_only=True filters by spec."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()

        # Create results for different specs
        results = []
        for spec_id, session_num in [("spec_123", 1), ("spec_456", 2)]:
            data = {
                "type": EPISODE_TYPE_SESSION_INSIGHT,
                "spec_id": spec_id,
                "session_number": session_num,
            }
            mock_result = MagicMock()
            mock_result.content = json.dumps(data)
            results.append(mock_result)

        mock_graphiti.search = AsyncMock(return_value=results)
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        sessions = await search.get_session_history(spec_only=True)

        # Should only return sessions for spec_123
        assert len(sessions) == 1
        assert sessions[0]["spec_id"] == "spec_123"

    @pytest.mark.asyncio
    async def test_get_session_history_spec_only_false_returns_all(self):
        """Test get_session_history with spec_only=False returns all sessions."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()

        # Create results for different specs
        results = []
        for spec_id, session_num in [("spec_123", 1), ("spec_456", 2)]:
            data = {
                "type": EPISODE_TYPE_SESSION_INSIGHT,
                "spec_id": spec_id,
                "session_number": session_num,
            }
            mock_result = MagicMock()
            mock_result.content = json.dumps(data)
            results.append(mock_result)

        mock_graphiti.search = AsyncMock(return_value=results)
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        sessions = await search.get_session_history(spec_only=False)

        # Should return all sessions
        assert len(sessions) == 2

    @pytest.mark.asyncio
    async def test_get_session_history_custom_limit(self):
        """Test get_session_history with custom limit."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()

        # Create more results than limit
        results = []
        for i in range(10):
            data = {
                "type": EPISODE_TYPE_SESSION_INSIGHT,
                "spec_id": "spec_123",
                "session_number": i,
            }
            mock_result = MagicMock()
            mock_result.content = json.dumps(data)
            results.append(mock_result)

        mock_graphiti.search = AsyncMock(return_value=results)
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        sessions = await search.get_session_history(limit=3)

        # Should limit to 3 results
        assert len(sessions) == 3

    @pytest.mark.asyncio
    async def test_get_session_history_sorts_by_session_number(self):
        """Test get_session_history sorts by session_number descending."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()

        # Create results with random session numbers
        results = []
        for session_num in [5, 2, 8, 1]:
            data = {
                "type": EPISODE_TYPE_SESSION_INSIGHT,
                "spec_id": "spec_123",
                "session_number": session_num,
            }
            mock_result = MagicMock()
            mock_result.content = json.dumps(data)
            results.append(mock_result)

        mock_graphiti.search = AsyncMock(return_value=results)
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        sessions = await search.get_session_history()

        # Should be sorted descending
        session_numbers = [s["session_number"] for s in sessions]
        assert session_numbers == [8, 5, 2, 1]

    @pytest.mark.asyncio
    async def test_get_session_history_handles_dict_data(self):
        """Test get_session_history handles already-dict data."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()

        # Create result with dict instead of JSON string
        data = {
            "type": EPISODE_TYPE_SESSION_INSIGHT,
            "spec_id": "spec_123",
            "session_number": 3,
        }
        mock_result = MagicMock()
        mock_result.content = data  # Dict, not string
        mock_result.fact = None

        mock_graphiti.search = AsyncMock(return_value=[mock_result])
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        sessions = await search.get_session_history()

        assert len(sessions) == 1
        assert sessions[0]["session_number"] == 3

    @pytest.mark.asyncio
    async def test_get_session_history_skips_non_dict_data(self):
        """Test get_session_history skips non-dict data (ACS-215 fix)."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()

        # Create result with invalid data
        mock_result = MagicMock()
        mock_result.content = "just a string, not a dict"
        mock_result.fact = None

        mock_graphiti.search = AsyncMock(return_value=[mock_result])
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        sessions = await search.get_session_history()

        # Should skip invalid data
        assert len(sessions) == 0

    @pytest.mark.asyncio
    @patch("integrations.graphiti.queries_pkg.search.capture_exception")
    async def test_get_session_history_exception_handling(self, mock_capture):
        """Test get_session_history handles exceptions gracefully."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(side_effect=RuntimeError("Search failed"))
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        sessions = await search.get_session_history()

        assert sessions == []
        mock_capture.assert_called()


class TestGetSimilarTaskOutcomes:
    """Tests for get_similar_task_outcomes method."""

    @pytest.mark.asyncio
    async def test_get_similar_task_outcomes_basic(self):
        """Test basic similar task outcomes retrieval."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()

        # Create mock task outcome
        task_data = {
            "type": EPISODE_TYPE_TASK_OUTCOME,
            "task_id": "task_123",
            "success": True,
            "outcome": "Task completed successfully",
        }
        mock_result = MagicMock()
        mock_result.content = json.dumps(task_data)
        mock_result.score = 0.85

        mock_graphiti.search = AsyncMock(return_value=[mock_result])
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        outcomes = await search.get_similar_task_outcomes("Implement feature X")

        assert len(outcomes) == 1
        assert outcomes[0]["task_id"] == "task_123"
        assert outcomes[0]["success"] is True
        assert outcomes[0]["outcome"] == "Task completed successfully"

    @pytest.mark.asyncio
    async def test_get_similar_task_outcomes_includes_score(self):
        """Test get_similar_task_outcomes includes relevance score."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()

        task_data = {
            "type": EPISODE_TYPE_TASK_OUTCOME,
            "task_id": "task_123",
            "success": True,
            "outcome": "Done",
        }
        mock_result = MagicMock()
        mock_result.content = json.dumps(task_data)
        mock_result.score = 0.92

        mock_graphiti.search = AsyncMock(return_value=[mock_result])
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        outcomes = await search.get_similar_task_outcomes("test task")

        assert outcomes[0]["score"] == 0.92

    @pytest.mark.asyncio
    async def test_get_similar_task_outcomes_respects_limit(self):
        """Test get_similar_task_outcomes respects limit parameter."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()

        # Create more results than limit
        results = []
        for i in range(10):
            task_data = {
                "type": EPISODE_TYPE_TASK_OUTCOME,
                "task_id": f"task_{i}",
                "success": True,
                "outcome": f"Outcome {i}",
            }
            mock_result = MagicMock()
            mock_result.content = json.dumps(task_data)
            results.append(mock_result)

        mock_graphiti.search = AsyncMock(return_value=results)
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        outcomes = await search.get_similar_task_outcomes("test task", limit=3)

        assert len(outcomes) == 3

    @pytest.mark.asyncio
    @patch("integrations.graphiti.queries_pkg.search.capture_exception")
    async def test_get_similar_task_outcomes_exception_handling(self, mock_capture):
        """Test get_similar_task_outcomes handles exceptions gracefully."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(side_effect=RuntimeError("Search failed"))
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        outcomes = await search.get_similar_task_outcomes("test task")

        assert outcomes == []
        mock_capture.assert_called()


class TestGetPatternsAndGotchas:
    """Tests for get_patterns_and_gotchas method."""

    @pytest.mark.asyncio
    async def test_get_patterns_and_gotchas_basic(self):
        """Test basic patterns and gotchas retrieval."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()

        # Create pattern result
        pattern_data = {
            "type": EPISODE_TYPE_PATTERN,
            "pattern": "Use async/await for I/O operations",
            "applies_to": "backend services",
            "example": "async def fetch_data(): ...",
        }
        pattern_result = MagicMock()
        pattern_result.content = json.dumps(pattern_data)
        pattern_result.score = 0.9

        # Create gotcha result
        gotcha_data = {
            "type": EPISODE_TYPE_GOTCHA,
            "gotcha": "Forgetting to await async functions",
            "trigger": "Using async without await",
            "solution": "Always await async calls",
        }
        gotcha_result = MagicMock()
        gotcha_result.content = json.dumps(gotcha_data)
        gotcha_result.score = 0.85

        mock_graphiti.search = AsyncMock(
            side_effect=[
                [pattern_result],  # First call for patterns
                [gotcha_result],   # Second call for gotchas
            ]
        )
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        patterns, gotchas = await search.get_patterns_and_gotchas("async operations")

        assert len(patterns) == 1
        assert patterns[0]["pattern"] == "Use async/await for I/O operations"
        assert patterns[0]["score"] == 0.9

        assert len(gotchas) == 1
        assert gotchas[0]["gotcha"] == "Forgetting to await async functions"
        assert gotchas[0]["score"] == 0.85

    @pytest.mark.asyncio
    async def test_get_patterns_and_gotchas_filters_by_min_score(self):
        """Test get_patterns_and_gotchas filters by min_score."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()

        # Create results with varying scores
        pattern_results = []
        for score in [0.9, 0.7, 0.4, 0.2]:
            data = {
                "type": EPISODE_TYPE_PATTERN,
                "pattern": f"Pattern {score}",
                "applies_to": "all",
                "example": "example",
            }
            mock_result = MagicMock()
            mock_result.content = json.dumps(data)
            mock_result.score = score
            pattern_results.append(mock_result)

        mock_graphiti.search = AsyncMock(
            side_effect=[
                pattern_results,
                [],  # No gotchas
            ]
        )
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        patterns, gotchas = await search.get_patterns_and_gotchas(
            "test query",
            min_score=0.5
        )

        # Should only return patterns with score >= 0.5
        assert len(patterns) == 2
        assert all(p["score"] >= 0.5 for p in patterns)

    @pytest.mark.asyncio
    async def test_get_patterns_and_gotchas_respects_num_results(self):
        """Test get_patterns_and_gotchas respects num_results limit."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()

        # Create many results
        pattern_results = []
        for i in range(10):
            data = {
                "type": EPISODE_TYPE_PATTERN,
                "pattern": f"Pattern {i}",
                "applies_to": "all",
                "example": "example",
            }
            mock_result = MagicMock()
            mock_result.content = json.dumps(data)
            mock_result.score = 0.9 - (i * 0.05)
            pattern_results.append(mock_result)

        mock_graphiti.search = AsyncMock(
            side_effect=[
                pattern_results,
                [],  # No gotchas
            ]
        )
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        patterns, gotchas = await search.get_patterns_and_gotchas(
            "test query",
            num_results=3
        )

        assert len(patterns) == 3

    @pytest.mark.asyncio
    async def test_get_patterns_and_gotchas_sorts_by_score(self):
        """Test get_patterns_and_gotchas sorts by score descending."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()

        # Create results with random scores
        pattern_results = []
        for score in [0.5, 0.9, 0.3, 0.8]:
            data = {
                "type": EPISODE_TYPE_PATTERN,
                "pattern": f"Pattern {score}",
                "applies_to": "all",
                "example": "example",
            }
            mock_result = MagicMock()
            mock_result.content = json.dumps(data)
            mock_result.score = score
            pattern_results.append(mock_result)

        mock_graphiti.search = AsyncMock(
            side_effect=[
                pattern_results,
                [],
            ]
        )
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        patterns, gotchas = await search.get_patterns_and_gotchas("test query")

        # Should be sorted by score descending
        scores = [p["score"] for p in patterns]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_get_patterns_and_gotchas_skips_non_dict_data(self):
        """Test get_patterns_and_gotchas skips non-dict data (ACS-215 fix)."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()

        # Create invalid result
        mock_result = MagicMock()
        mock_result.content = "not a dict"
        mock_result.score = 0.9

        mock_graphiti.search = AsyncMock(
            side_effect=[
                [mock_result],
                [],
            ]
        )
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        patterns, gotchas = await search.get_patterns_and_gotchas("test query")

        # Should skip invalid data
        assert len(patterns) == 0

    @pytest.mark.asyncio
    @patch("integrations.graphiti.queries_pkg.search.capture_exception")
    async def test_get_patterns_and_gotchas_exception_handling(self, mock_capture):
        """Test get_patterns_and_gotchas handles exceptions gracefully."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(side_effect=RuntimeError("Search failed"))
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        patterns, gotchas = await search.get_patterns_and_gotchas("test query")

        assert patterns == []
        assert gotchas == []
        mock_capture.assert_called()

    @pytest.mark.asyncio
    async def test_get_patterns_and_gotchas_empty_results(self):
        """Test get_patterns_and_gotchas with no results."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        patterns, gotchas = await search.get_patterns_and_gotchas("test query")

        assert patterns == []
        assert gotchas == []


class TestGraphitiSearchIntegration:
    """Integration tests for GraphitiSearch."""

    @pytest.mark.asyncio
    async def test_full_search_workflow(self):
        """Test complete search workflow with multiple methods."""
        mock_client = MagicMock()
        mock_graphiti = MagicMock()

        # Mock get_relevant_context
        context_result = MagicMock()
        context_result.content = "context info"
        context_result.score = 0.9
        context_result.type = "info"

        # Mock get_session_history
        session_data = {
            "type": EPISODE_TYPE_SESSION_INSIGHT,
            "spec_id": "spec_123",
            "session_number": 1,
            "summary": "Session 1",
        }
        session_result = MagicMock()
        session_result.content = json.dumps(session_data)

        mock_graphiti.search = AsyncMock(
            side_effect=[
                [context_result],  # First call: get_relevant_context
                [session_result],  # Second call: get_session_history
                [],                # Third call: patterns
                [],                # Fourth call: gotchas
            ]
        )
        mock_client.graphiti = mock_graphiti

        search = GraphitiSearch(
            client=mock_client,
            group_id="test_group",
            spec_context_id="spec_123",
            group_id_mode=GroupIdMode.SPEC,
            project_dir=Path("/test/project"),
        )

        # Call multiple methods
        context = await search.get_relevant_context("query")
        sessions = await search.get_session_history()
        patterns, gotchas = await search.get_patterns_and_gotchas("query")

        assert len(context) == 1
        assert len(sessions) == 1
        assert patterns == []
        assert gotchas == []
