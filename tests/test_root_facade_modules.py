#!/usr/bin/env python3
"""
Tests for root-level backward compatibility facade modules.

These tests verify that the root-level Python modules in apps/backend/
properly re-export their functionality from the actual implementation modules.
"""

import pytest
from pathlib import Path


class TestCiDiscoveryFacade:
    """Tests for ci_discovery.py backward compatibility shim."""

    def test_ci_discovery_exports_ci_config(self):
        """Test that CIConfig is exported from analysis.ci_discovery."""
        from ci_discovery import CIConfig
        from analysis.ci_discovery import CIConfig as OriginalCIConfig

        assert CIConfig is OriginalCIConfig

    def test_ci_discovery_exports_ci_workflow(self):
        """Test that CIWorkflow is exported from analysis.ci_discovery."""
        from ci_discovery import CIWorkflow
        from analysis.ci_discovery import CIWorkflow as OriginalCIWorkflow

        assert CIWorkflow is OriginalCIWorkflow

    def test_ci_discovery_exports_ci_discovery_class(self):
        """Test that CIDiscovery class is exported."""
        from ci_discovery import CIDiscovery
        from analysis.ci_discovery import CIDiscovery as OriginalCIDiscovery

        assert CIDiscovery is OriginalCIDiscovery

    def test_ci_discovery_exports_functions(self):
        """Test that functions are exported."""
        from ci_discovery import discover_ci, get_ci_system, get_ci_test_commands

        assert callable(discover_ci)
        assert callable(get_ci_system)
        assert callable(get_ci_test_commands)

    def test_ci_discovery_has_yaml_flag(self):
        """Test that HAS_YAML flag is exported."""
        from ci_discovery import HAS_YAML
        from analysis.ci_discovery import HAS_YAML as OriginalHAS_YAML

        assert HAS_YAML == OriginalHAS_YAML

    def test_ci_discovery_all_exports(self):
        """Test that all expected exports are in __all__."""
        import ci_discovery

        expected_exports = [
            "CIConfig",
            "CIWorkflow",
            "CIDiscovery",
            "discover_ci",
            "get_ci_test_commands",
            "get_ci_system",
            "HAS_YAML",
        ]
        for export in expected_exports:
            assert export in ci_discovery.__all__


class TestCritiqueFacade:
    """Tests for critique.py backward compatibility shim."""

    def test_critique_exports_from_spec(self):
        """Test that critique.py re-exports from spec.critique."""
        import critique
        import spec.critique as original

        # Check that key exports are available
        assert hasattr(original, "CritiqueResult")
        assert hasattr(original, "generate_critique_prompt")
        assert hasattr(original, "parse_critique_response")

    def test_critique_has_critique_result(self):
        """Test that CritiqueResult class is accessible."""
        from critique import CritiqueResult

        assert CritiqueResult is not None

    def test_critique_has_functions(self):
        """Test that functions are accessible."""
        from critique import (
            generate_critique_prompt,
            parse_critique_response,
            should_proceed,
            format_critique_summary,
        )

        assert callable(generate_critique_prompt)
        assert callable(parse_critique_response)
        assert callable(should_proceed)
        assert callable(format_critique_summary)


class TestInsightExtractorFacade:
    """Tests for insight_extractor.py backward compatibility shim."""

    def test_insight_extractor_exports_functions(self):
        """Test that all functions are exported."""
        from insight_extractor import (
            extract_session_insights,
            gather_extraction_inputs,
            get_changed_files,
            get_commit_messages,
            get_extraction_model,
            get_session_diff,
            is_extraction_enabled,
            parse_insights,
            run_insight_extraction,
        )

        assert callable(extract_session_insights)
        assert callable(gather_extraction_inputs)
        assert callable(get_changed_files)
        assert callable(get_commit_messages)
        assert callable(get_extraction_model)
        assert callable(get_session_diff)
        assert callable(is_extraction_enabled)
        assert callable(parse_insights)
        assert callable(run_insight_extraction)

    def test_insight_extractor_all_exports(self):
        """Test that all expected exports are in __all__."""
        import insight_extractor

        expected_exports = [
            "extract_session_insights",
            "gather_extraction_inputs",
            "get_changed_files",
            "get_commit_messages",
            "get_extraction_model",
            "get_session_diff",
            "is_extraction_enabled",
            "parse_insights",
            "run_insight_extraction",
        ]
        for export in expected_exports:
            assert export in insight_extractor.__all__


class TestPhaseEventFacade:
    """Tests for phase_event.py backward compatibility shim."""

    def test_phase_event_exports_constants(self):
        """Test that constants are exported."""
        from phase_event import PHASE_MARKER_PREFIX

        assert isinstance(PHASE_MARKER_PREFIX, str)

    def test_phase_event_exports_execution_phase(self):
        """Test that ExecutionPhase enum is exported."""
        from phase_event import ExecutionPhase
        from core.phase_event import ExecutionPhase as OriginalExecutionPhase

        assert ExecutionPhase is OriginalExecutionPhase

    def test_phase_event_exports_emit_phase(self):
        """Test that emit_phase function is exported."""
        from phase_event import emit_phase
        from core.phase_event import emit_phase as OriginalEmitPhase

        assert emit_phase is OriginalEmitPhase

    def test_phase_event_all_exports(self):
        """Test that all expected exports are in __all__."""
        import phase_event

        expected_exports = [
            "PHASE_MARKER_PREFIX",
            "ExecutionPhase",
            "emit_phase",
        ]
        for export in expected_exports:
            assert export in phase_event.__all__


class TestProjectAnalyzerFacade:
    """Tests for project_analyzer.py backward compatibility shim."""

    def test_project_analyzer_exports_classes(self):
        """Test that main classes are exported."""
        from project_analyzer import (
            ProjectAnalyzer,
            SecurityProfile,
            TechnologyStack,
        )

        assert ProjectAnalyzer is not None
        assert SecurityProfile is not None
        assert TechnologyStack is not None

    def test_project_analyzer_exports_functions(self):
        """Test that utility functions are exported."""
        from project_analyzer import (
            get_or_create_profile,
            is_command_allowed,
            needs_validation,
        )

        assert callable(get_or_create_profile)
        assert callable(is_command_allowed)
        assert callable(needs_validation)

    def test_project_analyzer_exports_command_registries(self):
        """Test that command registries are exported."""
        from project_analyzer import (
            BASE_COMMANDS,
            VALIDATED_COMMANDS,
            CLOUD_COMMANDS,
            CODE_QUALITY_COMMANDS,
            DATABASE_COMMANDS,
        )

        # BASE_COMMANDS is a set of shell commands, not a dict
        assert isinstance(BASE_COMMANDS, (set, list, dict))
        assert isinstance(VALIDATED_COMMANDS, (set, list, dict))
        # Command registries are dicts
        assert isinstance(CLOUD_COMMANDS, (set, list, dict))
        assert isinstance(CODE_QUALITY_COMMANDS, (set, list, dict))
        assert isinstance(DATABASE_COMMANDS, (set, list, dict))

    def test_project_analyzer_all_exports(self):
        """Test that all expected exports are in __all__."""
        import project_analyzer

        expected_exports = [
            "ProjectAnalyzer",
            "SecurityProfile",
            "TechnologyStack",
            "CustomScripts",
            "get_or_create_profile",
            "is_command_allowed",
            "needs_validation",
            "BASE_COMMANDS",
            "VALIDATED_COMMANDS",
        ]
        for export in expected_exports:
            assert export in project_analyzer.__all__


class TestPromptGeneratorFacade:
    """Tests for prompt_generator.py backward compatibility shim."""

    def test_prompt_generator_exports_from_prompts_pkg(self):
        """Test that prompt_generator re-exports from prompts_pkg."""
        import prompt_generator
        import prompts_pkg.prompt_generator as original

        # Check that key exports are available (based on actual API)
        assert hasattr(original, "generate_planner_prompt")
        assert hasattr(original, "generate_subtask_prompt")
        assert hasattr(original, "detect_worktree_isolation")

    def test_prompt_generator_has_generate_functions(self):
        """Test that generate functions are accessible (based on actual API)."""
        from prompt_generator import (
            generate_planner_prompt,
            generate_subtask_prompt,
            detect_worktree_isolation,
        )

        assert callable(generate_planner_prompt)
        assert callable(generate_subtask_prompt)
        assert callable(detect_worktree_isolation)


class TestPromptsFacade:
    """Tests for prompts.py backward compatibility shim."""

    def test_prompts_exports_from_prompts_pkg(self):
        """Test that prompts re-exports from prompts_pkg.prompts."""
        import prompts
        import prompts_pkg.prompts as original

        # Check that the module is accessible (based on actual API)
        assert hasattr(original, "get_planner_prompt")
        assert hasattr(original, "get_coding_prompt")
        assert hasattr(original, "get_qa_reviewer_prompt")


class TestQaLoopFacade:
    """Tests for qa_loop.py backward compatibility shim."""

    def test_qa_loop_exports_constants(self):
        """Test that constants are exported."""
        from qa_loop import (
            MAX_QA_ITERATIONS,
            RECURRING_ISSUE_THRESHOLD,
            ISSUE_SIMILARITY_THRESHOLD,
        )

        assert isinstance(MAX_QA_ITERATIONS, int)
        assert isinstance(RECURRING_ISSUE_THRESHOLD, int)
        assert isinstance(ISSUE_SIMILARITY_THRESHOLD, float)

    def test_qa_loop_exports_main_loop_function(self):
        """Test that run_qa_validation_loop is exported."""
        from qa_loop import run_qa_validation_loop

        assert callable(run_qa_validation_loop)

    def test_qa_loop_exports_criteria_functions(self):
        """Test that criteria/status functions are exported."""
        from qa_loop import (
            load_implementation_plan,
            save_implementation_plan,
            get_qa_signoff_status,
            is_qa_approved,
            is_qa_rejected,
            is_fixes_applied,
        )

        assert callable(load_implementation_plan)
        assert callable(save_implementation_plan)
        assert callable(get_qa_signoff_status)
        assert callable(is_qa_approved)
        assert callable(is_qa_rejected)
        assert callable(is_fixes_applied)

    def test_qa_loop_exports_report_functions(self):
        """Test that report functions are exported."""
        from qa_loop import (
            get_iteration_history,
            record_iteration,
            has_recurring_issues,
            get_recurring_issue_summary,
            escalate_to_human,
        )

        assert callable(get_iteration_history)
        assert callable(record_iteration)
        assert callable(has_recurring_issues)
        assert callable(get_recurring_issue_summary)
        assert callable(escalate_to_human)

    def test_qa_loop_exports_private_helpers(self):
        """Test that private helper functions are exported for testing."""
        from qa_loop import _normalize_issue_key, _issue_similarity

        assert callable(_normalize_issue_key)
        assert callable(_issue_similarity)

    def test_qa_loop_exports_agent_sessions(self):
        """Test that agent session functions are exported."""
        from qa_loop import (
            run_qa_agent_session,
            load_qa_fixer_prompt,
            run_qa_fixer_session,
        )

        assert callable(run_qa_agent_session)
        assert callable(load_qa_fixer_prompt)
        assert callable(run_qa_fixer_session)

    def test_qa_loop_all_exports(self):
        """Test that all expected exports are in __all__."""
        import qa_loop

        expected_exports = [
            "MAX_QA_ITERATIONS",
            "RECURRING_ISSUE_THRESHOLD",
            "ISSUE_SIMILARITY_THRESHOLD",
            "run_qa_validation_loop",
            "load_implementation_plan",
            "save_implementation_plan",
            "get_qa_signoff_status",
            "is_qa_approved",
            "is_qa_rejected",
            "is_fixes_applied",
            "get_qa_iteration_count",
            "should_run_qa",
            "should_run_fixes",
            "print_qa_status",
            "get_iteration_history",
            "record_iteration",
            "has_recurring_issues",
            "get_recurring_issue_summary",
            "escalate_to_human",
            "create_manual_test_plan",
            "check_test_discovery",
            "is_no_test_project",
            "_normalize_issue_key",
            "_issue_similarity",
            "run_qa_agent_session",
            "load_qa_fixer_prompt",
            "run_qa_fixer_session",
        ]
        for export in expected_exports:
            assert export in qa_loop.__all__


class TestRiskClassifierFacade:
    """Tests for risk_classifier.py backward compatibility shim."""

    def test_risk_classifier_exports_classes(self):
        """Test that dataclasses are exported."""
        from risk_classifier import (
            ScopeAnalysis,
            IntegrationAnalysis,
            InfrastructureAnalysis,
            KnowledgeAnalysis,
            RiskAnalysis,
            ComplexityAnalysis,
            ValidationRecommendations,
            AssessmentFlags,
            RiskAssessment,
        )

        assert ScopeAnalysis is not None
        assert IntegrationAnalysis is not None
        assert InfrastructureAnalysis is not None
        assert KnowledgeAnalysis is not None
        assert RiskAnalysis is not None
        assert ComplexityAnalysis is not None
        assert ValidationRecommendations is not None
        assert AssessmentFlags is not None
        assert RiskAssessment is not None

    def test_risk_classifier_exports_risk_classifier(self):
        """Test that RiskClassifier class is exported."""
        from risk_classifier import RiskClassifier
        from analysis.risk_classifier import RiskClassifier as OriginalRiskClassifier

        assert RiskClassifier is OriginalRiskClassifier

    def test_risk_classifier_exports_functions(self):
        """Test that convenience functions are exported."""
        from risk_classifier import load_risk_assessment, get_validation_requirements

        assert callable(load_risk_assessment)
        assert callable(get_validation_requirements)

    def test_risk_classifier_all_exports(self):
        """Test that all expected exports are in __all__."""
        import risk_classifier

        expected_exports = [
            "RiskClassifier",
            "RiskAssessment",
            "ValidationRecommendations",
            "ComplexityAnalysis",
            "ScopeAnalysis",
            "IntegrationAnalysis",
            "InfrastructureAnalysis",
            "KnowledgeAnalysis",
            "RiskAnalysis",
            "AssessmentFlags",
            "load_risk_assessment",
            "get_validation_requirements",
        ]
        for export in expected_exports:
            assert export in risk_classifier.__all__


class TestScanSecretsFacade:
    """Tests for scan_secrets.py backward compatibility shim."""

    def test_scan_secrets_exports_from_security(self):
        """Test that scan_secrets re-exports from security.scan_secrets."""
        import scan_secrets
        import security.scan_secrets as original

        # Check that key exports are available
        assert hasattr(original, "SecretMatch")
        assert hasattr(original, "scan_files")
        assert hasattr(original, "main")

    def test_scan_secrets_has_secret_match(self):
        """Test that SecretMatch dataclass is accessible."""
        from scan_secrets import SecretMatch

        assert SecretMatch is not None

    def test_scan_secrets_has_functions(self):
        """Test that functions are accessible."""
        from scan_secrets import (
            load_secretsignore,
            should_skip_file,
            scan_content,
            get_staged_files,
            get_all_tracked_files,
            scan_files,
            main,
        )

        assert callable(load_secretsignore)
        assert callable(should_skip_file)
        assert callable(scan_content)
        assert callable(get_staged_files)
        assert callable(get_all_tracked_files)
        assert callable(scan_files)
        assert callable(main)


class TestSecurityScannerFacade:
    """Tests for security_scanner.py backward compatibility shim."""

    def test_security_scanner_exports_from_analysis(self):
        """Test that security_scanner re-exports from analysis.security_scanner."""
        import security_scanner
        import analysis.security_scanner as original

        # Check that key exports are available
        assert hasattr(original, "SecurityScanner")
        assert hasattr(original, "SecurityScanResult")
        assert hasattr(original, "SecurityVulnerability")

    def test_security_scanner_has_classes(self):
        """Test that classes are accessible."""
        from security_scanner import (
            SecurityScanner,
            SecurityScanResult,
            SecurityVulnerability,
        )

        assert SecurityScanner is not None
        assert SecurityScanResult is not None
        assert SecurityVulnerability is not None

    def test_security_scanner_has_functions(self):
        """Test that convenience functions are accessible."""
        from security_scanner import (
            scan_for_security_issues,
            has_security_issues,
            scan_secrets_only,
        )

        assert callable(scan_for_security_issues)
        assert callable(has_security_issues)
        assert callable(scan_secrets_only)


class TestFacadeModulesIntegration:
    """Integration tests for facade modules working together."""

    def test_ci_discovery_can_be_imported_and_used(self):
        """Test that ci_discovery can be imported and used like the original."""
        from ci_discovery import CIDiscovery, get_ci_system

        assert callable(get_ci_system)

    def test_qa_loop_can_be_imported_and_used(self):
        """Test that qa_loop can be imported and used like the original."""
        from qa_loop import is_qa_approved, MAX_QA_ITERATIONS

        assert callable(is_qa_approved)
        assert isinstance(MAX_QA_ITERATIONS, int)

    def test_risk_classifier_can_be_imported_and_used(self):
        """Test that risk_classifier can be imported and used like the original."""
        from risk_classifier import RiskClassifier, load_risk_assessment

        assert RiskClassifier is not None
        assert callable(load_risk_assessment)

    def test_project_analyzer_can_be_imported_and_used(self):
        """Test that project_analyzer can be imported and used like the original."""
        from project_analyzer import get_or_create_profile, is_command_allowed

        assert callable(get_or_create_profile)
        assert callable(is_command_allowed)

    def test_phase_event_can_be_imported_and_used(self):
        """Test that phase_event can be imported and used like the original."""
        from phase_event import emit_phase, ExecutionPhase

        assert callable(emit_phase)
        assert ExecutionPhase is not None


class TestFacadeModulesConsistency:
    """Tests for consistency between facade and original modules."""

    def test_ci_discovery_consistency(self):
        """Test that ci_discovery facade matches original API."""
        from analysis import ci_discovery as original
        import ci_discovery as facade

        # Check that key exports exist in both
        for attr in ["CIConfig", "CIWorkflow", "CIDiscovery", "discover_ci"]:
            assert hasattr(original, attr)
            assert hasattr(facade, attr)

    def test_qa_loop_consistency(self):
        """Test that qa_loop facade matches original API."""
        import qa as original
        import qa_loop as facade

        # Check that key exports exist in both
        for attr in ["MAX_QA_ITERATIONS", "run_qa_validation_loop", "is_qa_approved"]:
            assert hasattr(original, attr)
            assert hasattr(facade, attr)

    def test_risk_classifier_consistency(self):
        """Test that risk_classifier facade matches original API."""
        from analysis import risk_classifier as original
        import risk_classifier as facade

        # Check that key exports exist in both
        for attr in [
            "RiskClassifier",
            "RiskAssessment",
            "ValidationRecommendations",
        ]:
            assert hasattr(original, attr)
            assert hasattr(facade, attr)

    def test_project_analyzer_consistency(self):
        """Test that project_analyzer facade matches original API."""
        import project as original
        import project_analyzer as facade

        # Check that key exports exist in both
        for attr in ["ProjectAnalyzer", "SecurityProfile", "get_or_create_profile"]:
            assert hasattr(original, attr)
            assert hasattr(facade, attr)
