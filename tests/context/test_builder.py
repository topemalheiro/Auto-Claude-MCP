"""Tests for builder"""

from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
import json

import pytest


class TestContextBuilder:
    """Tests for ContextBuilder class"""

    def test_init_with_project_dir(self, tmp_path):
        """Test ContextBuilder initialization with project directory"""
        from context.builder import ContextBuilder

        builder = ContextBuilder(tmp_path)

        assert builder.project_dir == tmp_path.resolve()
        assert builder.project_index is not None
        assert builder.searcher is not None
        assert builder.service_matcher is not None
        assert builder.keyword_extractor is not None
        assert builder.categorizer is not None
        assert builder.pattern_discoverer is not None

    def test_init_with_project_index(self, tmp_path):
        """Test ContextBuilder initialization with provided project index"""
        from context.builder import ContextBuilder

        custom_index = {
            "services": {
                "api": {
                    "path": "apps/api",
                    "language": "python"
                }
            }
        }

        builder = ContextBuilder(tmp_path, project_index=custom_index)

        assert builder.project_index == custom_index

    def test_load_project_index_from_file(self, tmp_path):
        """Test loading project index from .auto-claude/project_index.json"""
        from context.builder import ContextBuilder

        # Create .auto-claude directory and index file
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir(parents=True)
        index_file = auto_claude_dir / "project_index.json"

        test_index = {
            "services": {
                "web": {"path": "apps/web", "language": "typescript"}
            }
        }

        index_file.write_text(json.dumps(test_index), encoding="utf-8")

        builder = ContextBuilder(tmp_path)

        assert builder.project_index == test_index

    def test_load_project_index_handles_corrupted_file(self, tmp_path):
        """Test that corrupted index file triggers regeneration"""
        from context.builder import ContextBuilder

        # Create .auto-claude directory and corrupted index file
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir(parents=True)
        index_file = auto_claude_dir / "project_index.json"

        index_file.write_text("{invalid json", encoding="utf-8")

        # Mock analyze_project to avoid actual analysis
        with patch('analyzer.analyze_project') as mock_analyze:
            mock_analyze.return_value = {"services": {}}
            builder = ContextBuilder(tmp_path)
            # analyze_project should be called as fallback
            assert mock_analyze.called

    def test_build_context_basic(self, tmp_path):
        """Test basic context building"""
        from context.builder import ContextBuilder

        project_index = {
            "services": {
                "api": {
                    "path": "api",
                    "language": "python",
                    "type": "backend"
                }
            }
        }

        # Create service directory
        api_dir = tmp_path / "api"
        api_dir.mkdir(parents=True)

        builder = ContextBuilder(tmp_path, project_index=project_index)

        with patch.object(builder.searcher, 'search_service', return_value=[]):
            with patch.object(builder.service_matcher, 'suggest_services', return_value=['api']):
                with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=['test']):
                    with patch.object(builder.categorizer, 'categorize_matches', return_value=([], [])):
                        with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value=[]):
                            context = builder.build_context("Add authentication to API")

                            assert context.task_description == "Add authentication to API"
                            assert context.scoped_services == ['api']
                            assert context.files_to_modify == []
                            assert context.files_to_reference == []
                            assert context.patterns_discovered == []

    def test_build_context_with_explicit_services(self, tmp_path):
        """Test context building with explicit service list"""
        from context.builder import ContextBuilder

        project_index = {
            "services": {
                "api": {"path": "api", "language": "python"}
            }
        }

        api_dir = tmp_path / "api"
        api_dir.mkdir(parents=True)

        builder = ContextBuilder(tmp_path, project_index=project_index)

        with patch.object(builder.searcher, 'search_service', return_value=[]):
            with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=['auth']):
                with patch.object(builder.categorizer, 'categorize_matches', return_value=([], [])):
                    with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value=[]):
                        context = builder.build_context(
                            "Add authentication",
                            services=['api'],
                            keywords=['login', 'user']
                        )

                        assert context.scoped_services == ['api']
                        # Keywords should be overridden by explicit parameter

    @pytest.mark.asyncio
    async def test_build_context_async_basic(self, tmp_path):
        """Test async context building"""
        from context.builder import ContextBuilder

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
                        with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value=[]):
                            with patch('context.builder.fetch_graph_hints', new_callable=AsyncMock, return_value=[]):
                                context = await builder.build_context_async("Add user profile component")

                                assert context.task_description == "Add user profile component"
                                assert context.scoped_services == ['web']

    @pytest.mark.asyncio
    async def test_build_context_async_with_graph_hints(self, tmp_path):
        """Test async context building with Graphiti hints"""
        from context.builder import ContextBuilder

        project_index = {"services": {}}
        builder = ContextBuilder(tmp_path, project_index=project_index)

        graph_hints = ["Previous work: Added login form", "Consider using existing auth service"]

        with patch.object(builder.service_matcher, 'suggest_services', return_value=[]):
            with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=[]):
                with patch.object(builder.categorizer, 'categorize_matches', return_value=([], [])):
                    with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value=[]):
                        with patch('context.builder.fetch_graph_hints', new_callable=AsyncMock, return_value=graph_hints):
                            with patch('context.builder.is_graphiti_enabled', return_value=True):
                                context = await builder.build_context_async("Add forgot password", include_graph_hints=True)

                                assert context.graph_hints == graph_hints

    def test_build_context_sync_graphiti_disabled(self, tmp_path):
        """Test sync context building when Graphiti is disabled"""
        from context.builder import ContextBuilder

        project_index = {"services": {}}
        builder = ContextBuilder(tmp_path, project_index=project_index)

        with patch.object(builder.service_matcher, 'suggest_services', return_value=[]):
            with patch.object(builder.keyword_extractor, 'extract_keywords', return_value=[]):
                with patch.object(builder.categorizer, 'categorize_matches', return_value=([], [])):
                    with patch.object(builder.pattern_discoverer, 'discover_patterns', return_value=[]):
                        with patch('context.builder.is_graphiti_enabled', return_value=False):
                            context = builder.build_context("Test task", include_graph_hints=True)

                            assert context.graph_hints == []

    def test_get_service_context_from_file(self, tmp_path):
        """Test _get_service_context loads from SERVICE_CONTEXT.md"""
        from context.builder import ContextBuilder

        project_index = {"services": {}}
        builder = ContextBuilder(tmp_path, project_index=project_index)

        service_path = tmp_path / "api"
        service_path.mkdir(parents=True)

        context_file = service_path / "SERVICE_CONTEXT.md"
        context_content = "# API Service\n\nThis is the main API service."
        context_file.write_text(context_content, encoding="utf-8")

        service_info = {"path": "api", "language": "python"}

        result = builder._get_service_context(service_path, "api", service_info)

        assert result["source"] == "SERVICE_CONTEXT.md"
        assert "API Service" in result["content"]

    def test_get_service_context_generated(self, tmp_path):
        """Test _get_service_context generates basic context"""
        from context.builder import ContextBuilder

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
