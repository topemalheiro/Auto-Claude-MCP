"""Tests for analysis/__init__.py - Analysis module exports."""

import pytest

from analysis import (
    ProjectAnalyzer,
    ModularProjectAnalyzer,
    ServiceAnalyzer,
    analyze_project,
    analyze_service,
    RiskClassifier,
    SecurityScanner,
    CIDiscovery,
    TestDiscovery,
)


class TestAnalysisModuleExports:
    """Tests for analysis module public API exports."""

    def test_project_analyzer_export(self):
        """Test that ProjectAnalyzer is exported."""
        assert ProjectAnalyzer is not None

    def test_modular_project_analyzer_export(self):
        """Test that ModularProjectAnalyzer is exported."""
        assert ModularProjectAnalyzer is not None

    def test_service_analyzer_export(self):
        """Test that ServiceAnalyzer is exported."""
        assert ServiceAnalyzer is not None

    def test_analyze_project_export(self):
        """Test that analyze_project is exported."""
        assert analyze_project is not None

    def test_analyze_service_export(self):
        """Test that analyze_service is exported."""
        assert analyze_service is not None

    def test_risk_classifier_export(self):
        """Test that RiskClassifier is exported."""
        assert RiskClassifier is not None

    def test_security_scanner_export(self):
        """Test that SecurityScanner is exported."""
        assert SecurityScanner is not None

    def test_ci_discovery_export(self):
        """Test that CIDiscovery is exported."""
        assert CIDiscovery is not None

    def test_test_discovery_export(self):
        """Test that TestDiscovery is exported."""
        assert TestDiscovery is not None

    def test_module_has_all_attribute(self):
        """Test that module has __all__ attribute."""
        import analysis

        assert hasattr(analysis, "__all__")
        assert isinstance(analysis.__all__, list)

    def test_all_exports_exist(self):
        """Test that all exports in __all__ actually exist."""
        import analysis

        for name in analysis.__all__:
            assert hasattr(analysis, name), f"{name} in __all__ but not exported"

    def test_expected_exports_in_all(self):
        """Test that expected exports are in __all__."""
        import analysis

        expected = {
            "ProjectAnalyzer",
            "ModularProjectAnalyzer",
            "ServiceAnalyzer",
            "analyze_project",
            "analyze_service",
            "RiskClassifier",
            "SecurityScanner",
            "CIDiscovery",
            "TestDiscovery",
        }

        assert set(analysis.__all__) >= expected


class TestAnalysisModuleImports:
    """Tests for analysis module import structure."""

    def test_import_from_analyzers_submodule_works(self):
        """Test that direct imports from analyzers submodule work."""
        from analysis.analyzers import (
            ProjectAnalyzer as DirectModularProjectAnalyzer,
            ServiceAnalyzer as DirectServiceAnalyzer,
            analyze_project as DirectAnalyzeProject,
            analyze_service as DirectAnalyzeService,
        )

        assert DirectModularProjectAnalyzer is ModularProjectAnalyzer
        assert DirectServiceAnalyzer is ServiceAnalyzer
        assert DirectAnalyzeProject is analyze_project
        assert DirectAnalyzeService is analyze_service

    def test_import_from_root_modules_works(self):
        """Test that direct imports from root modules work."""
        from analysis.project_analyzer import ProjectAnalyzer as DirectProjectAnalyzer
        from analysis.risk_classifier import RiskClassifier as DirectRiskClassifier
        from analysis.security_scanner import SecurityScanner as DirectSecurityScanner
        from analysis.test_discovery import TestDiscovery as DirectTestDiscovery
        from analysis.ci_discovery import CIDiscovery as DirectCIDiscovery

        assert DirectProjectAnalyzer is ProjectAnalyzer
        assert DirectRiskClassifier is RiskClassifier
        assert DirectSecurityScanner is SecurityScanner
        assert DirectTestDiscovery is TestDiscovery
        assert DirectCIDiscovery is CIDiscovery

    def test_no_circular_imports(self):
        """Test that importing analysis doesn't cause circular imports."""
        import importlib
        import sys

        # Remove from cache if present
        if "analysis" in sys.modules:
            del sys.modules["analysis"]

        # Should import without issues
        import analysis

        assert analysis is not None


class TestAnalysisModuleFacade:
    """Tests for analysis module as a facade."""

    def test_facade_reexports_from_analyzers(self):
        """Test that analysis re-exports from analyzers submodule."""
        from analysis import ModularProjectAnalyzer, ServiceAnalyzer, analyze_project, analyze_service
        from analysis.analyzers import (
            ProjectAnalyzer as AnalyzerModular,
            ServiceAnalyzer as AnalyzerService,
            analyze_project as AnalyzerAnalyzeProject,
            analyze_service as AnalyzerAnalyzeService,
        )

        assert ModularProjectAnalyzer is AnalyzerModular
        assert ServiceAnalyzer is AnalyzerService
        assert analyze_project is AnalyzerAnalyzeProject
        assert analyze_service is AnalyzerAnalyzeService

    def test_facade_reexports_from_root_modules(self):
        """Test that analysis re-exports from root module files."""
        from analysis import ProjectAnalyzer, RiskClassifier, SecurityScanner, TestDiscovery, CIDiscovery
        from analysis.project_analyzer import ProjectAnalyzer as RootProjectAnalyzer
        from analysis.risk_classifier import RiskClassifier as RootRiskClassifier
        from analysis.security_scanner import SecurityScanner as RootSecurityScanner
        from analysis.test_discovery import TestDiscovery as RootTestDiscovery
        from analysis.ci_discovery import CIDiscovery as RootCIDiscovery

        assert ProjectAnalyzer is RootProjectAnalyzer
        assert RiskClassifier is RootRiskClassifier
        assert SecurityScanner is RootSecurityScanner
        assert TestDiscovery is RootTestDiscovery
        assert CIDiscovery is RootCIDiscovery


class TestAnalysisModuleTypes:
    """Tests for analysis module exported types."""

    def test_project_analyzer_is_class(self):
        """Test that ProjectAnalyzer is a class."""
        assert isinstance(ProjectAnalyzer, type)

    def test_modular_project_analyzer_is_class(self):
        """Test that ModularProjectAnalyzer is a class."""
        assert isinstance(ModularProjectAnalyzer, type)

    def test_service_analyzer_is_class(self):
        """Test that ServiceAnalyzer is a class."""
        assert isinstance(ServiceAnalyzer, type)

    def test_risk_classifier_is_class(self):
        """Test that RiskClassifier is a class."""
        assert isinstance(RiskClassifier, type)

    def test_security_scanner_is_class(self):
        """Test that SecurityScanner is a class."""
        assert isinstance(SecurityScanner, type)

    def test_ci_discovery_is_class(self):
        """Test that CIDiscovery is a class."""
        assert isinstance(CIDiscovery, type)

    def test_test_discovery_is_class(self):
        """Test that TestDiscovery is a class."""
        assert isinstance(TestDiscovery, type)

    def test_analyze_project_is_callable(self):
        """Test that analyze_project is callable."""
        assert callable(analyze_project)

    def test_analyze_service_is_callable(self):
        """Test that analyze_service is callable."""
        assert callable(analyze_service)


class TestAnalysisModuleIntegration:
    """Tests for analysis module integration points."""

    def test_two_project_analyzers_are_distinct(self):
        """Test that ProjectAnalyzer and ModularProjectAnalyzer are distinct."""
        # These should be different classes from different modules
        assert ProjectAnalyzer is not ModularProjectAnalyzer

    def test_project_analyzer_from_project_analyzer_module(self):
        """Test that ProjectAnalyzer comes from project_analyzer module."""
        from analysis import project_analyzer

        # Should be able to import the module
        assert project_analyzer is not None
        assert hasattr(project_analyzer, "ProjectAnalyzer")

    def test_modular_project_analyzer_from_analyzers(self):
        """Test that ModularProjectAnalyzer comes from analyzers submodule."""
        from analysis import analyzers

        # Should be able to import from analyzers
        assert analyzers is not None
        assert hasattr(analyzers, "ProjectAnalyzer")
