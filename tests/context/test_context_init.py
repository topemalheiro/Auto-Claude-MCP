"""Tests for context/__init__.py - Context package exports."""

import pytest

from context import (
    # Main builder
    ContextBuilder,
    # Models
    FileMatch,
    TaskContext,
    # Components
    CodeSearcher,
    ServiceMatcher,
    KeywordExtractor,
    FileCategorizer,
    PatternDiscoverer,
    # Graphiti integration
    fetch_graph_hints,
    is_graphiti_enabled,
    # Serialization
    serialize_context,
    save_context,
    load_context,
)


class TestContextModuleExports:
    """Tests for context module public API exports."""

    def test_context_builder_export(self):
        """Test that ContextBuilder is exported."""
        assert ContextBuilder is not None

    def test_file_match_export(self):
        """Test that FileMatch is exported."""
        assert FileMatch is not None

    def test_task_context_export(self):
        """Test that TaskContext is exported."""
        assert TaskContext is not None

    def test_code_searcher_export(self):
        """Test that CodeSearcher is exported."""
        assert CodeSearcher is not None

    def test_service_matcher_export(self):
        """Test that ServiceMatcher is exported."""
        assert ServiceMatcher is not None

    def test_keyword_extractor_export(self):
        """Test that KeywordExtractor is exported."""
        assert KeywordExtractor is not None

    def test_file_categorizer_export(self):
        """Test that FileCategorizer is exported."""
        assert FileCategorizer is not None

    def test_pattern_discoverer_export(self):
        """Test that PatternDiscoverer is exported."""
        assert PatternDiscoverer is not None

    def test_fetch_graph_hints_export(self):
        """Test that fetch_graph_hints is exported."""
        assert fetch_graph_hints is not None

    def test_is_graphiti_enabled_export(self):
        """Test that is_graphiti_enabled is exported."""
        assert is_graphiti_enabled is not None

    def test_serialize_context_export(self):
        """Test that serialize_context is exported."""
        assert serialize_context is not None

    def test_save_context_export(self):
        """Test that save_context is exported."""
        assert save_context is not None

    def test_load_context_export(self):
        """Test that load_context is exported."""
        assert load_context is not None

    def test_module_has_all_attribute(self):
        """Test that module has __all__ attribute."""
        import context

        assert hasattr(context, "__all__")
        assert isinstance(context.__all__, list)

    def test_all_exports_exist(self):
        """Test that all exports in __all__ actually exist."""
        import context

        for name in context.__all__:
            assert hasattr(context, name), f"{name} in __all__ but not exported"

    def test_expected_exports_in_all(self):
        """Test that expected exports are in __all__."""
        import context

        expected = {
            "ContextBuilder",
            "FileMatch",
            "TaskContext",
            "CodeSearcher",
            "ServiceMatcher",
            "KeywordExtractor",
            "FileCategorizer",
            "PatternDiscoverer",
            "fetch_graph_hints",
            "is_graphiti_enabled",
            "serialize_context",
            "save_context",
            "load_context",
        }

        assert set(context.__all__) >= expected


class TestContextModuleImports:
    """Tests for context module import structure."""

    def test_import_from_submodules_works(self):
        """Test that direct imports from submodules work."""
        from context.builder import ContextBuilder as DirectContextBuilder
        from context.models import FileMatch as DirectFileMatch, TaskContext as DirectTaskContext
        from context.search import CodeSearcher as DirectCodeSearcher
        from context.service_matcher import ServiceMatcher as DirectServiceMatcher
        from context.keyword_extractor import KeywordExtractor as DirectKeywordExtractor
        from context.categorizer import FileCategorizer as DirectFileCategorizer
        from context.pattern_discovery import PatternDiscoverer as DirectPatternDiscoverer
        from context.graphiti_integration import (
            fetch_graph_hints as DirectFetchGraphHints,
            is_graphiti_enabled as DirectIsGraphitiEnabled,
        )
        from context.serialization import (
            serialize_context as DirectSerializeContext,
            save_context as DirectSaveContext,
            load_context as DirectLoadContext,
        )

        assert DirectContextBuilder is ContextBuilder
        assert DirectFileMatch is FileMatch
        assert DirectTaskContext is TaskContext
        assert DirectCodeSearcher is CodeSearcher
        assert DirectServiceMatcher is ServiceMatcher
        assert DirectKeywordExtractor is KeywordExtractor
        assert DirectFileCategorizer is FileCategorizer
        assert DirectPatternDiscoverer is PatternDiscoverer
        assert DirectFetchGraphHints is fetch_graph_hints
        assert DirectIsGraphitiEnabled is is_graphiti_enabled
        assert DirectSerializeContext is serialize_context
        assert DirectSaveContext is save_context
        assert DirectLoadContext is load_context

    def test_no_circular_imports(self):
        """Test that importing context doesn't cause circular imports."""
        import importlib
        import sys

        # Remove from cache if present
        if "context" in sys.modules:
            del sys.modules["context"]

        # Should import without issues
        import context

        assert context is not None


class TestContextModuleFacade:
    """Tests for context module as a facade."""

    def test_facade_reexports_from_builder(self):
        """Test that context re-exports ContextBuilder from builder."""
        from context import ContextBuilder
        from context.builder import ContextBuilder as BuilderFromSub

        assert ContextBuilder is BuilderFromSub

    def test_facade_reexports_from_models(self):
        """Test that context re-exports models from models."""
        from context import FileMatch, TaskContext
        from context.models import FileMatch as FileMatchFromSub, TaskContext as TaskContextFromSub

        assert FileMatch is FileMatchFromSub
        assert TaskContext is TaskContextFromSub

    def test_facade_reexports_from_search(self):
        """Test that context re-exports CodeSearcher from search."""
        from context import CodeSearcher
        from context.search import CodeSearcher as SearcherFromSub

        assert CodeSearcher is SearcherFromSub

    def test_facade_reexports_from_service_matcher(self):
        """Test that context re-exports ServiceMatcher from service_matcher."""
        from context import ServiceMatcher
        from context.service_matcher import ServiceMatcher as MatcherFromSub

        assert ServiceMatcher is MatcherFromSub

    def test_facade_reexports_from_keyword_extractor(self):
        """Test that context re-exports KeywordExtractor from keyword_extractor."""
        from context import KeywordExtractor
        from context.keyword_extractor import KeywordExtractor as ExtractorFromSub

        assert KeywordExtractor is ExtractorFromSub

    def test_facade_reexports_from_categorizer(self):
        """Test that context re-exports FileCategorizer from categorizer."""
        from context import FileCategorizer
        from context.categorizer import FileCategorizer as CategorizerFromSub

        assert FileCategorizer is CategorizerFromSub

    def test_facade_reexports_from_pattern_discovery(self):
        """Test that context re-exports PatternDiscoverer from pattern_discovery."""
        from context import PatternDiscoverer
        from context.pattern_discovery import PatternDiscoverer as DiscovererFromSub

        assert PatternDiscoverer is DiscovererFromSub

    def test_facade_reexports_from_graphiti_integration(self):
        """Test that context re-exports graphiti functions from graphiti_integration."""
        from context import fetch_graph_hints, is_graphiti_enabled
        from context.graphiti_integration import (
            fetch_graph_hints as HintsFromSub,
            is_graphiti_enabled as EnabledFromSub,
        )

        assert fetch_graph_hints is HintsFromSub
        assert is_graphiti_enabled is EnabledFromSub

    def test_facade_reexports_from_serialization(self):
        """Test that context re-exports serialization functions."""
        from context import load_context, save_context, serialize_context
        from context.serialization import (
            load_context as LoadFromSub,
            save_context as SaveFromSub,
            serialize_context as SerializeFromSub,
        )

        assert serialize_context is SerializeFromSub
        assert save_context is SaveFromSub
        assert load_context is LoadFromSub


class TestContextModuleTypes:
    """Tests for context module exported types."""

    def test_context_builder_is_class(self):
        """Test that ContextBuilder is a class."""
        assert isinstance(ContextBuilder, type)

    def test_file_match_is_class(self):
        """Test that FileMatch is a class."""
        from dataclasses import is_dataclass

        assert is_dataclass(FileMatch)

    def test_task_context_is_class(self):
        """Test that TaskContext is a class."""
        from dataclasses import is_dataclass

        assert is_dataclass(TaskContext)

    def test_code_searcher_is_class(self):
        """Test that CodeSearcher is a class."""
        assert isinstance(CodeSearcher, type)

    def test_service_matcher_is_class(self):
        """Test that ServiceMatcher is a class."""
        assert isinstance(ServiceMatcher, type)

    def test_keyword_extractor_is_class(self):
        """Test that KeywordExtractor is a class."""
        assert isinstance(KeywordExtractor, type)

    def test_file_categorizer_is_class(self):
        """Test that FileCategorizer is a class."""
        assert isinstance(FileCategorizer, type)

    def test_pattern_discoverer_is_class(self):
        """Test that PatternDiscoverer is a class."""
        assert isinstance(PatternDiscoverer, type)

    def test_fetch_graph_hints_is_callable(self):
        """Test that fetch_graph_hints is callable."""
        assert callable(fetch_graph_hints)

    def test_is_graphiti_enabled_is_callable(self):
        """Test that is_graphiti_enabled is callable."""
        assert callable(is_graphiti_enabled)

    def test_serialize_context_is_callable(self):
        """Test that serialize_context is callable."""
        assert callable(serialize_context)

    def test_save_context_is_callable(self):
        """Test that save_context is callable."""
        assert callable(save_context)

    def test_load_context_is_callable(self):
        """Test that load_context is callable."""
        assert callable(load_context)


class TestContextModuleIntegration:
    """Tests for context module integration points."""

    def test_file_match_has_expected_attributes(self):
        """Test that FileMatch has expected attributes."""
        match = FileMatch(
            path="/path/to/file.py",
            service="test-service",
            reason="Test reason",
            relevance_score=0.8,
        )

        assert hasattr(match, "path")
        assert hasattr(match, "service")
        assert hasattr(match, "reason")
        assert hasattr(match, "relevance_score")

    def test_task_context_has_expected_attributes(self):
        """Test that TaskContext has expected attributes."""
        context = TaskContext(
            task_description="Test task",
            scoped_services=[],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={},
        )

        assert hasattr(context, "task_description")
        assert hasattr(context, "scoped_services")
        assert hasattr(context, "files_to_modify")

    def test_is_graphiti_enabled_returns_bool(self):
        """Test that is_graphiti_enabled returns a boolean."""
        result = is_graphiti_enabled()
        assert isinstance(result, bool)
