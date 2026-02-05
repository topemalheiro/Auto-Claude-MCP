"""
Comprehensive Tests for context.builder module
==============================================

Tests for ContextBuilder class including edge cases, error handling,
and all context building functionality paths.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import pytest

from context.builder import ContextBuilder
from context.models import FileMatch, TaskContext


class TestContextBuilderInit:
    """Tests for ContextBuilder.__init__"""

    def test_init_resolves_path(self, tmp_path):
        """Test that project_dir is resolved to absolute path"""
        project_dir = tmp_path / "test" / ".." / "test_project"
        # Create the directory to avoid FileNotFoundError
        project_dir.mkdir(parents=True, exist_ok=True)
        builder = ContextBuilder(project_dir)
        assert builder.project_dir == project_dir.resolve()

    def test_init_with_absolute_path(self, tmp_path):
        """Test initialization with absolute path"""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir(parents=True, exist_ok=True)
        builder = ContextBuilder(project_dir)
        assert builder.project_dir == project_dir.resolve()

    def test_init_creates_project_index_when_missing(self, tmp_path):
        """Test that project index is created when .auto-claude doesn't exist"""
        # Mock analyze_project to return a test index
        mock_index = {"services": {"api": {"path": "api"}}}
        with patch('analyzer.analyze_project', return_value=mock_index):
            builder = ContextBuilder(tmp_path)
            assert builder.project_index == mock_index

    def test_init_with_custom_project_index(self, tmp_path):
        """Test initialization with provided project index"""
        custom_index = {"services": {"web": {"path": "web"}}}
        builder = ContextBuilder(tmp_path, project_index=custom_index)
        assert builder.project_index == custom_index


class TestLoadProjectIndex:
    """Tests for _load_project_index method"""

    def test_load_project_index_from_valid_file(self, tmp_path):
        """Test loading project index from valid JSON file"""
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir(parents=True)
        index_file = auto_claude_dir / "project_index.json"

        test_index = {
            "services": {
                "api": {"path": "apps/api", "language": "python"}
            }
        }

        index_file.write_text(json.dumps(test_index), encoding="utf-8")

        builder = ContextBuilder(tmp_path)
        assert builder.project_index == test_index

    def test_load_project_index_when_auto_claude_missing(self, tmp_path):
        """Test that analyze_project is called when .auto-claude doesn't exist"""
        mock_index = {"services": {}}

        with patch('analyzer.analyze_project', return_value=mock_index) as mock_analyze:
            builder = ContextBuilder(tmp_path)
            mock_analyze.assert_called_once_with(tmp_path)
            assert builder.project_index == mock_index

    def test_load_project_index_with_corrupted_json(self, tmp_path):
        """Test handling of corrupted JSON file"""
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir(parents=True)
        index_file = auto_claude_dir / "project_index.json"

        # Write invalid JSON
        index_file.write_text("{invalid json", encoding="utf-8")

        mock_index = {"services": {"fallback": {"path": "fallback"}}}

        with patch('analyzer.analyze_project', return_value=mock_index) as mock_analyze:
            builder = ContextBuilder(tmp_path)
            mock_analyze.assert_called_once()
            assert builder.project_index == mock_index

    def test_load_project_index_with_unicode_decode_error(self, tmp_path):
        """Test handling of file with encoding issues"""
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir(parents=True)
        index_file = auto_claude_dir / "project_index.json"

        # Write file with encoding that will cause issues
        index_file.write_bytes(b'\xff\xfe invalid utf-8')

        mock_index = {"services": {}}

        with patch('analyzer.analyze_project', return_value=mock_index) as mock_analyze:
            builder = ContextBuilder(tmp_path)
            mock_analyze.assert_called_once()
            assert builder.project_index == mock_index

    def test_load_project_index_with_os_error(self, tmp_path):
        """Test handling of OS errors when reading file"""
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir(parents=True)
        index_file = auto_claude_dir / "project_index.json"

        # Write valid content
        index_file.write_text('{"services": {}}', encoding="utf-8")

        mock_index = {"services": {}}

        # Mock open to raise OSError
        with patch('builtins.open', side_effect=OSError("Permission denied")):
            with patch('analyzer.analyze_project', return_value=mock_index) as mock_analyze:
                builder = ContextBuilder(tmp_path)
                mock_analyze.assert_called_once()
                assert builder.project_index == mock_index


class TestBuildContext:
    """Tests for build_context method"""

    def test_build_context_basic(self, tmp_path):
        """Test basic context building"""
        project_index = {
            "services": {
                "api": {"path": "api", "language": "python"}
            }
        }

        api_dir = tmp_path / "api"
        api_dir.mkdir(parents=True)

        builder = ContextBuilder(tmp_path, project_index=project_index)

        with patch.object(builder.searcher, 'search_service', return_value=[]):
            with patch.object(builder.service_matcher, 'suggest_services', return_value=['api']):
                with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=['auth']):
                    with patch.object(builder.categorizer, 'categorize_matches', return_value=([], [])):
                        with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value={}):
                            context = builder.build_context("Add authentication")

                            assert context.task_description == "Add authentication"
                            assert context.scoped_services == ['api']
                            assert isinstance(context, TaskContext)

    def test_build_context_with_explicit_services(self, tmp_path):
        """Test context building with explicit service list"""
        project_index = {
            "services": {
                "api": {"path": "api", "language": "python"}
            }
        }

        api_dir = tmp_path / "api"
        api_dir.mkdir(parents=True)

        builder = ContextBuilder(tmp_path, project_index=project_index)

        with patch.object(builder.searcher, 'search_service', return_value=[]):
            with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=['test']):
                with patch.object(builder.categorizer, 'categorize_matches', return_value=([], [])):
                    with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value={}):
                        context = builder.build_context(
                            "Add authentication",
                            services=['api'],
                            keywords=['login', 'user']
                        )

                        assert context.scoped_services == ['api']

    def test_build_context_with_explicit_keywords(self, tmp_path):
        """Test context building with explicit keywords (no extraction)"""
        project_index = {
            "services": {
                "web": {"path": "web", "language": "typescript"}
            }
        }

        web_dir = tmp_path / "web"
        web_dir.mkdir(parents=True)

        builder = ContextBuilder(tmp_path, project_index=project_index)

        with patch.object(builder.searcher, 'search_service', return_value=[]):
            with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=['auto']) as mock_extract:
                with patch.object(builder.categorizer, 'categorize_matches', return_value=([], [])):
                    with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value={}):
                        # When keywords are provided, extract_keywords should not be called
                        context = builder.build_context(
                            "Add component",
                            keywords=['button', 'click']
                        )

                        mock_extract.assert_not_called()

    def test_build_context_with_matches(self, tmp_path):
        """Test context building with file matches"""
        project_index = {
            "services": {
                "api": {"path": "api", "language": "python"}
            }
        }

        api_dir = tmp_path / "api"
        api_dir.mkdir(parents=True)

        builder = ContextBuilder(tmp_path, project_index=project_index)

        matches = [
            FileMatch(
                path="api/auth.py",
                service="api",
                reason="Contains: authentication",
                relevance_score=8,
                matching_lines=[]
            )
        ]

        with patch.object(builder.searcher, 'search_service', return_value=matches):
            with patch.object(builder.service_matcher, 'suggest_services', return_value=['api']):
                with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=['auth']):
                    with patch.object(builder.categorizer, 'categorize_matches', return_value=(matches, [])):
                        with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value={}):
                            context = builder.build_context("Add authentication")

                            # FileMatch objects should be serialized to dicts
                            assert all(isinstance(f, dict) for f in context.files_to_modify)

    def test_build_context_serializes_file_matches(self, tmp_path):
        """Test that FileMatch objects are properly serialized"""
        project_index = {"services": {"api": {"path": "api"}}}
        api_dir = tmp_path / "api"
        api_dir.mkdir(parents=True)

        builder = ContextBuilder(tmp_path, project_index=project_index)

        # Mix of FileMatch objects and dicts
        modify_matches = [
            FileMatch(path="api/auth.py", service="api", reason="Modify", relevance_score=8, matching_lines=[]),
            {"path": "api/user.py", "service": "api", "reason": "Also modify", "relevance_score": 7, "matching_lines": []}
        ]

        with patch.object(builder.searcher, 'search_service', return_value=[]):
            with patch.object(builder.service_matcher, 'suggest_services', return_value=['api']):
                with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=['test']):
                    with patch.object(builder.categorizer, 'categorize_matches', return_value=(modify_matches, [])):
                        with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value={}):
                            context = builder.build_context("Test")

                            # All should be dicts
                            assert all(isinstance(f, dict) for f in context.files_to_modify)
                            assert len(context.files_to_modify) == 2

    def test_build_context_include_graph_hints_false(self, tmp_path):
        """Test that graph hints are not fetched when include_graph_hints=False"""
        project_index = {"services": {}}
        builder = ContextBuilder(tmp_path, project_index=project_index)

        with patch.object(builder.service_matcher, 'suggest_services', return_value=[]):
            with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=[]):
                with patch.object(builder.categorizer, 'categorize_matches', return_value=([], [])):
                    with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value={}):
                        with patch('context.builder.is_graphiti_enabled', return_value=True):
                            context = builder.build_context("Test", include_graph_hints=False)

                            assert context.graph_hints == []

    def test_build_context_event_loop_exists(self, tmp_path):
        """Test handling when async event loop already exists"""
        project_index = {"services": {}}
        builder = ContextBuilder(tmp_path, project_index=project_index)

        # Simulate being in an async context
        async def in_async_context():
            with patch.object(builder.service_matcher, 'suggest_services', return_value=[]):
                with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=[]):
                    with patch.object(builder.categorizer, 'categorize_matches', return_value=([], [])):
                        with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value={}):
                            with patch('context.builder.is_graphiti_enabled', return_value=True):
                                # When event loop exists, graph_hints should be empty
                                context = builder.build_context("Test", include_graph_hints=True)
                                return context

        # Run in async context to simulate the scenario
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            context = loop.run_until_complete(in_async_context())
            assert context.graph_hints == []
        finally:
            loop.close()

    def test_build_context_runtime_error_handling(self, tmp_path):
        """Test RuntimeError handling during event loop check"""
        project_index = {"services": {}}
        builder = ContextBuilder(tmp_path, project_index=project_index)

        with patch.object(builder.service_matcher, 'suggest_services', return_value=[]):
            with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=[]):
                with patch.object(builder.categorizer, 'categorize_matches', return_value=([], [])):
                    with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value={}):
                        with patch('context.builder.is_graphiti_enabled', return_value=True):
                            # Patch asyncio.get_running_loop to raise RuntimeError
                            with patch('asyncio.get_running_loop', side_effect=RuntimeError):
                                with patch('asyncio.run', return_value=[]):
                                    context = builder.build_context("Test")
                                    assert context.graph_hints == []

    def test_build_context_graphiti_exception(self, tmp_path):
        """Test graceful handling when fetch_graph_hints raises exception"""
        project_index = {"services": {}}
        builder = ContextBuilder(tmp_path, project_index=project_index)

        with patch.object(builder.service_matcher, 'suggest_services', return_value=[]):
            with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=[]):
                with patch.object(builder.categorizer, 'categorize_matches', return_value=([], [])):
                    with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value={}):
                        with patch('context.builder.is_graphiti_enabled', return_value=True):
                            # Patch asyncio.run to raise exception
                            with patch('asyncio.run', side_effect=Exception("Graphiti error")):
                                context = builder.build_context("Test")
                                # Should handle gracefully and return empty hints
                                assert context.graph_hints == []

    def test_build_context_missing_service_path(self, tmp_path):
        """Test handling when service has no 'path' key"""
        project_index = {
            "services": {
                "api": {"language": "python"}  # No 'path' key
            }
        }

        builder = ContextBuilder(tmp_path, project_index=project_index)

        with patch.object(builder.service_matcher, 'suggest_services', return_value=['api']):
            with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=['test']):
                with patch.object(builder.categorizer, 'categorize_matches', return_value=([], [])):
                    with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value={}):
                        # Should use service_name as fallback path
                        context = builder.build_context("Test")
                        assert context.scoped_services == ['api']

    def test_build_context_relative_service_path(self, tmp_path):
        """Test that relative service paths are resolved correctly"""
        project_index = {
            "services": {
                "api": {"path": "services/api", "language": "python"}
            }
        }

        # Create the service directory
        api_dir = tmp_path / "services" / "api"
        api_dir.mkdir(parents=True)

        builder = ContextBuilder(tmp_path, project_index=project_index)

        with patch.object(builder.searcher, 'search_service') as mock_search:
            with patch.object(builder.service_matcher, 'suggest_services', return_value=['api']):
                with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=['test']):
                    with patch.object(builder.categorizer, 'categorize_matches', return_value=([], [])):
                        with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value={}):
                            context = builder.build_context("Test")

                            # Should resolve to absolute path
                            called_path = mock_search.call_args[0][0]
                            assert called_path.is_absolute()
                            assert "services/api" in str(called_path)

    def test_build_context_absolute_service_path(self, tmp_path):
        """Test that absolute service paths are used as-is"""
        project_index = {
            "services": {
                "api": {"path": str(tmp_path / "api"), "language": "python"}
            }
        }

        api_dir = tmp_path / "api"
        api_dir.mkdir(parents=True)

        builder = ContextBuilder(tmp_path, project_index=project_index)

        with patch.object(builder.searcher, 'search_service') as mock_search:
            with patch.object(builder.service_matcher, 'suggest_services', return_value=['api']):
                with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=['test']):
                    with patch.object(builder.categorizer, 'categorize_matches', return_value=([], [])):
                        with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value={}):
                            context = builder.build_context("Test")

                            # Should use absolute path directly
                            called_path = mock_search.call_args[0][0]
                            assert called_path == api_dir

    def test_build_context_nonexistent_service(self, tmp_path):
        """Test handling when service doesn't exist in index"""
        project_index = {"services": {}}
        builder = ContextBuilder(tmp_path, project_index=project_index)

        with patch.object(builder.service_matcher, 'suggest_services', return_value=['nonexistent']):
            with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=['test']):
                with patch.object(builder.categorizer, 'categorize_matches', return_value=([], [])):
                    with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value={}):
                        context = builder.build_context("Test")
                        # Should handle gracefully
                        assert context.scoped_services == ['nonexistent']


class TestBuildContextAsync:
    """Tests for build_context_async method"""

    @pytest.mark.asyncio
    async def test_build_context_async_basic(self, tmp_path):
        """Test basic async context building"""
        project_index = {
            "services": {
                "web": {"path": "web", "language": "typescript"}
            }
        }

        web_dir = tmp_path / "web"
        web_dir.mkdir(parents=True)

        builder = ContextBuilder(tmp_path, project_index=project_index)

        with patch.object(builder.searcher, 'search_service', return_value=[]):
            with patch.object(builder.service_matcher, 'suggest_services', return_value=['web']):
                with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=['component']):
                    with patch.object(builder.categorizer, 'categorize_matches', return_value=([], [])):
                        with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value={}):
                            context = await builder.build_context_async("Add component")

                            assert context.task_description == "Add component"
                            assert context.scoped_services == ['web']

    @pytest.mark.asyncio
    async def test_build_context_async_with_graph_hints(self, tmp_path):
        """Test async context building with graph hints"""
        project_index = {"services": {}}
        builder = ContextBuilder(tmp_path, project_index=project_index)

        graph_hints = ["Previous work: Added auth"]

        with patch.object(builder.service_matcher, 'suggest_services', return_value=[]):
            with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=[]):
                with patch.object(builder.categorizer, 'categorize_matches', return_value=([], [])):
                    with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value={}):
                        with patch('context.builder.fetch_graph_hints', new_callable=AsyncMock, return_value=graph_hints):
                            context = await builder.build_context_async("Test", include_graph_hints=True)

                            assert context.graph_hints == graph_hints

    @pytest.mark.asyncio
    async def test_build_context_async_exception_handling(self, tmp_path):
        """Test async context building handles fetch_graph_hints exceptions"""
        project_index = {"services": {}}
        builder = ContextBuilder(tmp_path, project_index=project_index)

        with patch.object(builder.service_matcher, 'suggest_services', return_value=[]):
            with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=[]):
                with patch.object(builder.categorizer, 'categorize_matches', return_value=([], [])):
                    with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value={}):
                        # Mock fetch_graph_hints to raise exception
                        with patch('context.builder.fetch_graph_hints', new_callable=AsyncMock, side_effect=Exception("Graphiti error")):
                            # Should propagate exception in async version
                            with pytest.raises(Exception, match="Graphiti error"):
                                await builder.build_context_async("Test", include_graph_hints=True)

    @pytest.mark.asyncio
    async def test_build_context_async_no_graph_hints(self, tmp_path):
        """Test async context building with include_graph_hints=False"""
        project_index = {"services": {}}
        builder = ContextBuilder(tmp_path, project_index=project_index)

        with patch.object(builder.service_matcher, 'suggest_services', return_value=[]):
            with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=[]):
                with patch.object(builder.categorizer, 'categorize_matches', return_value=([], [])):
                    with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value={}):
                        with patch('context.builder.fetch_graph_hints', new_callable=AsyncMock) as mock_fetch:
                            context = await builder.build_context_async("Test", include_graph_hints=False)

                            # fetch_graph_hints should not be called
                            mock_fetch.assert_not_called()
                            assert context.graph_hints == []


class TestGetServiceContext:
    """Tests for _get_service_context method"""

    def test_get_service_context_from_file(self, tmp_path):
        """Test loading context from SERVICE_CONTEXT.md"""
        project_index = {"services": {}}
        builder = ContextBuilder(tmp_path, project_index=project_index)

        service_path = tmp_path / "api"
        service_path.mkdir(parents=True)

        context_file = service_path / "SERVICE_CONTEXT.md"
        content = "# API Service\n\nThis handles authentication."
        context_file.write_text(content, encoding="utf-8")

        service_info = {"path": "api", "language": "python"}

        result = builder._get_service_context(service_path, "api", service_info)

        assert result["source"] == "SERVICE_CONTEXT.md"
        assert "API Service" in result["content"]

    def test_get_service_context_truncates_long_content(self, tmp_path):
        """Test that SERVICE_CONTEXT.md content is truncated to 2000 chars"""
        project_index = {"services": {}}
        builder = ContextBuilder(tmp_path, project_index=project_index)

        service_path = tmp_path / "api"
        service_path.mkdir(parents=True)

        context_file = service_path / "SERVICE_CONTEXT.md"
        # Create content longer than 2000 chars
        long_content = "x" * 3000
        context_file.write_text(long_content, encoding="utf-8")

        service_info = {"path": "api", "language": "python"}

        result = builder._get_service_context(service_path, "api", service_info)

        assert result["source"] == "SERVICE_CONTEXT.md"
        assert len(result["content"]) == 2000

    def test_get_service_context_generated_from_info(self, tmp_path):
        """Test generating context from service_info when no file exists"""
        project_index = {"services": {}}
        builder = ContextBuilder(tmp_path, project_index=project_index)

        service_path = tmp_path / "web"
        service_path.mkdir(parents=True)

        service_info = {
            "path": "web",
            "language": "typescript",
            "framework": "react",
            "type": "frontend",
            "entry_point": "src/main.tsx",
            "key_directories": {"components": "src/components"}
        }

        result = builder._get_service_context(service_path, "web", service_info)

        assert result["source"] == "generated"
        assert result["language"] == "typescript"
        assert result["framework"] == "react"
        assert result["type"] == "frontend"
        assert result["entry_point"] == "src/main.tsx"

    def test_get_service_context_missing_optional_keys(self, tmp_path):
        """Test handling when service_info has missing optional keys"""
        project_index = {"services": {}}
        builder = ContextBuilder(tmp_path, project_index=project_index)

        service_path = tmp_path / "api"
        service_path.mkdir(parents=True)

        # Minimal service_info with only required keys
        service_info = {"path": "api"}

        result = builder._get_service_context(service_path, "api", service_info)

        assert result["source"] == "generated"
        # Optional keys should be None
        assert result.get("language") is None
        assert result.get("framework") is None
        assert result.get("type") is None

    def test_get_service_context_empty_service_info(self, tmp_path):
        """Test handling when service_info is empty"""
        project_index = {"services": {}}
        builder = ContextBuilder(tmp_path, project_index=project_index)

        service_path = tmp_path / "minimal"
        service_path.mkdir(parents=True)

        service_info = {}

        result = builder._get_service_context(service_path, "minimal", service_info)

        assert result["source"] == "generated"
        # Should have default None values
        assert result.get("language") is None

    def test_get_service_context_with_key_directories(self, tmp_path):
        """Test that key_directories are properly included"""
        project_index = {"services": {}}
        builder = ContextBuilder(tmp_path, project_index=project_index)

        service_path = tmp_path / "api"
        service_path.mkdir(parents=True)

        service_info = {
            "path": "api",
            "key_directories": {
                "controllers": "src/controllers",
                "models": "src/models"
            }
        }

        result = builder._get_service_context(service_path, "api", service_info)

        assert result["source"] == "generated"
        assert result["key_directories"] == {
            "controllers": "src/controllers",
            "models": "src/models"
        }
