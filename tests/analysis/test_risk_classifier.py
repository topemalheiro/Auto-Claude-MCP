"""Tests for risk_classifier module"""

from analysis.risk_classifier import (
    RiskClassifier,
    RiskAssessment,
    ComplexityAnalysis,
    ScopeAnalysis,
    IntegrationAnalysis,
    InfrastructureAnalysis,
    KnowledgeAnalysis,
    RiskAnalysis,
    ValidationRecommendations,
    AssessmentFlags,
    load_risk_assessment,
    get_validation_requirements,
    main,
)
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
import pytest
import tempfile
import shutil
import json


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    project_path = Path(temp_dir)
    yield project_path
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def spec_dir(temp_dir):
    """Create a spec directory with complexity assessment."""
    spec_path = temp_dir / "specs" / "001"
    spec_path.mkdir(parents=True)

    assessment_data = {
        "complexity": "standard",
        "workflow_type": "feature",
        "confidence": 0.8,
        "reasoning": "Standard feature implementation",
        "analysis": {
            "scope": {
                "estimated_files": 5,
                "estimated_services": 1,
                "is_cross_cutting": False,
                "notes": "Single service feature"
            },
            "integrations": {
                "external_services": [],
                "new_dependencies": [],
                "research_needed": False,
                "notes": ""
            },
            "infrastructure": {
                "docker_changes": False,
                "database_changes": False,
                "config_changes": False,
                "notes": ""
            },
            "knowledge": {
                "patterns_exist": True,
                "research_required": False,
                "unfamiliar_tech": [],
                "notes": ""
            },
            "risk": {
                "level": "low",
                "concerns": [],
                "notes": ""
            }
        },
        "recommended_phases": ["planning", "implementation", "testing"],
        "flags": {
            "needs_research": False,
            "needs_self_critique": False,
            "needs_infrastructure_setup": False
        },
        "validation_recommendations": {
            "risk_level": "low",
            "skip_validation": False,
            "minimal_mode": True,
            "test_types_required": ["unit"],
            "security_scan_required": False,
            "staging_deployment_required": False,
            "reasoning": "Low risk, standard feature"
        },
        "created_at": "2024-01-01T00:00:00Z"
    }

    (spec_path / "complexity_assessment.json").write_text(json.dumps(assessment_data))
    return spec_path


@pytest.fixture
def spec_dir_no_assessment(temp_dir):
    """Create a spec directory without complexity assessment."""
    spec_path = temp_dir / "specs" / "002"
    spec_path.mkdir(parents=True)
    return spec_path


@pytest.fixture
def spec_dir_old_format(temp_dir):
    """Create a spec directory with old format assessment (no validation_recommendations)."""
    spec_path = temp_dir / "specs" / "003"
    spec_path.mkdir(parents=True)

    # Old format without validation_recommendations section
    assessment_data = {
        "complexity": "standard",
        "workflow_type": "feature",
        "confidence": 0.7,
        "reasoning": "Old format assessment",
        "analysis": {
            "scope": {
                "estimated_files": 3,
                "estimated_services": 1,
                "is_cross_cutting": False,
                "notes": ""
            },
            "integrations": {
                "external_services": [],
                "new_dependencies": [],
                "research_needed": False,
                "notes": ""
            },
            "infrastructure": {
                "docker_changes": False,
                "database_changes": False,
                "config_changes": False,
                "notes": ""
            },
            "knowledge": {
                "patterns_exist": True,
                "research_required": False,
                "unfamiliar_tech": [],
                "notes": ""
            },
            "risk": {
                "level": "medium",
                "concerns": ["Some concern"],
                "notes": ""
            }
        },
        "recommended_phases": ["planning", "implementation"],
        "flags": {
            "needs_research": False,
            "needs_self_critique": False,
            "needs_infrastructure_setup": False
        }
    }

    (spec_path / "complexity_assessment.json").write_text(json.dumps(assessment_data))
    return spec_path


class TestRiskClassifierInit:
    """Tests for RiskClassifier initialization."""

    def test_init(self):
        """Test RiskClassifier initializes with empty cache."""
        classifier = RiskClassifier()
        assert isinstance(classifier._cache, dict)
        assert len(classifier._cache) == 0


class TestLoadAssessment:
    """Tests for load_assessment method."""

    def test_load_valid_assessment(self, spec_dir):
        """Test loading a valid assessment."""
        classifier = RiskClassifier()
        result = classifier.load_assessment(spec_dir)
        assert result is not None
        assert isinstance(result, RiskAssessment)
        assert result.complexity == "standard"
        assert result.workflow_type == "feature"

    def test_load_no_assessment_file(self, spec_dir_no_assessment):
        """Test loading when assessment file doesn't exist."""
        classifier = RiskClassifier()
        result = classifier.load_assessment(spec_dir_no_assessment)
        assert result is None

    def test_load_invalid_json(self, temp_dir):
        """Test loading invalid JSON returns None."""
        spec_path = temp_dir / "specs" / "invalid"
        spec_path.mkdir(parents=True)
        (spec_path / "complexity_assessment.json").write_text("{invalid json}")

        classifier = RiskClassifier()
        result = classifier.load_assessment(spec_path)
        assert result is None

    def test_load_uses_cache(self, spec_dir):
        """Test that loading uses cache."""
        classifier = RiskClassifier()
        result1 = classifier.load_assessment(spec_dir)
        result2 = classifier.load_assessment(spec_dir)
        assert result1 is result2

    def test_parse_all_sections(self, spec_dir):
        """Test all sections are parsed correctly."""
        classifier = RiskClassifier()
        result = classifier.load_assessment(spec_dir)
        assert result is not None

        # Check analysis sections
        assert isinstance(result.analysis, ComplexityAnalysis)
        assert isinstance(result.analysis.scope, ScopeAnalysis)
        assert isinstance(result.analysis.integrations, IntegrationAnalysis)
        assert isinstance(result.analysis.infrastructure, InfrastructureAnalysis)
        assert isinstance(result.analysis.knowledge, KnowledgeAnalysis)
        assert isinstance(result.analysis.risk, RiskAnalysis)

        # Check other sections
        assert isinstance(result.flags, AssessmentFlags)
        assert isinstance(result.validation, ValidationRecommendations)

    def test_parse_old_format_infers_validation(self, spec_dir_old_format):
        """Test old format infers validation recommendations."""
        classifier = RiskClassifier()
        result = classifier.load_assessment(spec_dir_old_format)
        assert result is not None
        assert isinstance(result.validation, ValidationRecommendations)
        # Should be inferred from analysis
        assert result.validation.risk_level in ["low", "medium", "high"]


class TestShouldSkipValidation:
    """Tests for should_skip_validation method."""

    def test_skip_when_flagged(self, temp_dir):
        """Test skip_validation is respected."""
        spec_path = temp_dir / "specs" / "skip"
        spec_path.mkdir(parents=True)
        data = {
            "complexity": "simple",
            "workflow_type": "feature",
            "confidence": 1.0,
            "reasoning": "",
            "analysis": {
                "scope": {"estimated_files": 1, "estimated_services": 1, "is_cross_cutting": False, "notes": ""},
                "integrations": {"external_services": [], "new_dependencies": [], "research_needed": False, "notes": ""},
                "infrastructure": {"docker_changes": False, "database_changes": False, "config_changes": False, "notes": ""},
                "knowledge": {"patterns_exist": True, "research_required": False, "unfamiliar_tech": [], "notes": ""},
                "risk": {"level": "low", "concerns": [], "notes": ""}
            },
            "recommended_phases": [],
            "flags": {"needs_research": False, "needs_self_critique": False, "needs_infrastructure_setup": False},
            "validation_recommendations": {
                "risk_level": "trivial",
                "skip_validation": True,
                "minimal_mode": False,
                "test_types_required": [],
                "security_scan_required": False,
                "staging_deployment_required": False,
                "reasoning": ""
            }
        }
        (spec_path / "complexity_assessment.json").write_text(json.dumps(data))

        classifier = RiskClassifier()
        result = classifier.should_skip_validation(spec_path)
        assert result is True

    def test_no_skip_when_no_assessment(self, spec_dir_no_assessment):
        """Test doesn't skip when no assessment found."""
        classifier = RiskClassifier()
        result = classifier.should_skip_validation(spec_dir_no_assessment)
        assert result is False  # When in doubt, don't skip


class TestShouldUseMinimalMode:
    """Tests for should_use_minimal_mode method."""

    def test_minimal_mode_when_flagged(self, spec_dir):
        """Test minimal_mode flag is respected."""
        classifier = RiskClassifier()
        result = classifier.should_use_minimal_mode(spec_dir)
        assert result is True

    def test_no_minimal_when_no_assessment(self, spec_dir_no_assessment):
        """Test doesn't use minimal mode when no assessment."""
        classifier = RiskClassifier()
        result = classifier.should_use_minimal_mode(spec_dir_no_assessment)
        assert result is False


class TestGetRequiredTestTypes:
    """Tests for get_required_test_types method."""

    def test_returns_test_types(self, spec_dir):
        """Test returns test types from assessment."""
        classifier = RiskClassifier()
        result = classifier.get_required_test_types(spec_dir)
        assert result == ["unit"]

    def test_default_when_no_assessment(self, spec_dir_no_assessment):
        """Test defaults to unit tests when no assessment."""
        classifier = RiskClassifier()
        result = classifier.get_required_test_types(spec_dir_no_assessment)
        assert result == ["unit"]

    def test_multiple_test_types(self, temp_dir):
        """Test with multiple test types required."""
        spec_path = temp_dir / "specs" / "multi"
        spec_path.mkdir(parents=True)
        data = {
            "complexity": "complex",
            "workflow_type": "feature",
            "confidence": 0.5,
            "reasoning": "",
            "analysis": {
                "scope": {"estimated_files": 10, "estimated_services": 2, "is_cross_cutting": True, "notes": ""},
                "integrations": {"external_services": [], "new_dependencies": [], "research_needed": False, "notes": ""},
                "infrastructure": {"docker_changes": False, "database_changes": False, "config_changes": False, "notes": ""},
                "knowledge": {"patterns_exist": True, "research_required": False, "unfamiliar_tech": [], "notes": ""},
                "risk": {"level": "high", "concerns": [], "notes": ""}
            },
            "recommended_phases": [],
            "flags": {"needs_research": False, "needs_self_critique": False, "needs_infrastructure_setup": False},
            "validation_recommendations": {
                "risk_level": "high",
                "skip_validation": False,
                "minimal_mode": False,
                "test_types_required": ["unit", "integration", "e2e"],
                "security_scan_required": False,
                "staging_deployment_required": False,
                "reasoning": ""
            }
        }
        (spec_path / "complexity_assessment.json").write_text(json.dumps(data))

        classifier = RiskClassifier()
        result = classifier.get_required_test_types(spec_path)
        assert set(result) == {"unit", "integration", "e2e"}


class TestRequiresSecurityScan:
    """Tests for requires_security_scan method."""

    def test_security_scan_required(self, temp_dir):
        """Test when security scan is required."""
        spec_path = temp_dir / "specs" / "security"
        spec_path.mkdir(parents=True)
        data = {
            "complexity": "standard",
            "workflow_type": "feature",
            "confidence": 0.7,
            "reasoning": "",
            "analysis": {
                "scope": {"estimated_files": 5, "estimated_services": 1, "is_cross_cutting": False, "notes": ""},
                "integrations": {"external_services": [], "new_dependencies": [], "research_needed": False, "notes": ""},
                "infrastructure": {"docker_changes": False, "database_changes": False, "config_changes": False, "notes": ""},
                "knowledge": {"patterns_exist": True, "research_required": False, "unfamiliar_tech": [], "notes": ""},
                "risk": {"level": "medium", "concerns": ["security: password handling"], "notes": ""}
            },
            "recommended_phases": [],
            "flags": {"needs_research": False, "needs_self_critique": False, "needs_infrastructure_setup": False},
            "validation_recommendations": {
                "risk_level": "high",
                "skip_validation": False,
                "minimal_mode": False,
                "test_types_required": ["unit"],
                "security_scan_required": True,
                "staging_deployment_required": False,
                "reasoning": "Security concerns"
            }
        }
        (spec_path / "complexity_assessment.json").write_text(json.dumps(data))

        classifier = RiskClassifier()
        result = classifier.requires_security_scan(spec_path)
        assert result is True

    def test_no_security_scan_when_not_required(self, spec_dir):
        """Test when security scan is not required."""
        classifier = RiskClassifier()
        result = classifier.requires_security_scan(spec_dir)
        assert result is False

    def test_no_security_scan_when_no_assessment(self, spec_dir_no_assessment):
        """Test doesn't require security scan when no assessment."""
        classifier = RiskClassifier()
        result = classifier.requires_security_scan(spec_dir_no_assessment)
        assert result is False


class TestRequiresStagingDeployment:
    """Tests for requires_staging_deployment method."""

    def test_staging_required(self, temp_dir):
        """Test when staging deployment is required."""
        spec_path = temp_dir / "specs" / "staging"
        spec_path.mkdir(parents=True)
        data = {
            "complexity": "complex",
            "workflow_type": "feature",
            "confidence": 0.6,
            "reasoning": "",
            "analysis": {
                "scope": {"estimated_files": 10, "estimated_services": 1, "is_cross_cutting": False, "notes": ""},
                "integrations": {"external_services": [], "new_dependencies": [], "research_needed": False, "notes": ""},
                "infrastructure": {"docker_changes": False, "database_changes": True, "config_changes": False, "notes": ""},
                "knowledge": {"patterns_exist": True, "research_required": False, "unfamiliar_tech": [], "notes": ""},
                "risk": {"level": "medium", "concerns": [], "notes": ""}
            },
            "recommended_phases": [],
            "flags": {"needs_research": False, "needs_self_critique": False, "needs_infrastructure_setup": False},
            "validation_recommendations": {
                "risk_level": "high",
                "skip_validation": False,
                "minimal_mode": False,
                "test_types_required": ["unit"],
                "security_scan_required": False,
                "staging_deployment_required": True,
                "reasoning": "Database changes"
            }
        }
        (spec_path / "complexity_assessment.json").write_text(json.dumps(data))

        classifier = RiskClassifier()
        result = classifier.requires_staging_deployment(spec_path)
        assert result is True

    def test_no_staging_when_not_required(self, spec_dir):
        """Test when staging deployment is not required."""
        classifier = RiskClassifier()
        result = classifier.requires_staging_deployment(spec_dir)
        assert result is False


class TestGetRiskLevel:
    """Tests for get_risk_level method."""

    def test_returns_risk_level(self, spec_dir):
        """Test returns risk level from assessment."""
        classifier = RiskClassifier()
        result = classifier.get_risk_level(spec_dir)
        assert result == "low"

    def test_default_when_no_assessment(self, spec_dir_no_assessment):
        """Test defaults to medium when no assessment."""
        classifier = RiskClassifier()
        result = classifier.get_risk_level(spec_dir_no_assessment)
        assert result == "medium"


class TestGetComplexity:
    """Tests for get_complexity method."""

    def test_returns_complexity(self, spec_dir):
        """Test returns complexity from assessment."""
        classifier = RiskClassifier()
        result = classifier.get_complexity(spec_dir)
        assert result == "standard"

    def test_default_when_no_assessment(self, spec_dir_no_assessment):
        """Test defaults to standard when no assessment."""
        classifier = RiskClassifier()
        result = classifier.get_complexity(spec_dir_no_assessment)
        assert result == "standard"


class TestGetValidationSummary:
    """Tests for get_validation_summary method."""

    def test_returns_full_summary(self, spec_dir):
        """Test returns complete validation summary."""
        classifier = RiskClassifier()
        result = classifier.get_validation_summary(spec_dir)
        assert result["risk_level"] == "low"
        assert result["complexity"] == "standard"
        assert result["skip_validation"] is False
        assert result["minimal_mode"] is True
        assert result["test_types"] == ["unit"]
        assert result["security_scan"] is False
        assert result["staging_deployment"] is False
        assert result["confidence"] == 0.8

    def test_returns_default_when_no_assessment(self, spec_dir_no_assessment):
        """Test returns default summary when no assessment."""
        classifier = RiskClassifier()
        result = classifier.get_validation_summary(spec_dir_no_assessment)
        assert result["risk_level"] == "unknown"
        assert result["complexity"] == "unknown"
        assert result["skip_validation"] is False
        assert result["test_types"] == ["unit"]


class TestClearCache:
    """Tests for clear_cache method."""

    def test_clear_cache(self, spec_dir):
        """Test clearing the cache."""
        classifier = RiskClassifier()
        classifier.load_assessment(spec_dir)
        assert len(classifier._cache) > 0
        classifier.clear_cache()
        assert len(classifier._cache) == 0


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_load_risk_assessment_function(self, spec_dir):
        """Test load_risk_assessment convenience function."""
        result = load_risk_assessment(spec_dir)
        assert result is not None
        assert isinstance(result, RiskAssessment)

    def test_get_validation_requirements_function(self, spec_dir):
        """Test get_validation_requirements convenience function."""
        result = get_validation_requirements(spec_dir)
        assert isinstance(result, dict)
        assert "risk_level" in result
        assert "complexity" in result


class TestMainCLI:
    """Tests for main CLI function."""

    def test_main_with_valid_assessment(self, spec_dir, capsys):
        """Test main with valid assessment."""
        with patch("sys.argv", ["risk_classifier", str(spec_dir)]):
            main()
        captured = capsys.readouterr()
        assert "Risk Level" in captured.out

    def test_main_json_output(self, spec_dir, capsys):
        """Test main with JSON output."""
        with patch("sys.argv", ["risk_classifier", str(spec_dir), "--json"]):
            main()
        captured = capsys.readouterr()
        import json
        try:
            data = json.loads(captured.out)
            assert "risk_level" in data
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")


class TestRiskAssessmentDataclass:
    """Tests for RiskAssessment dataclass."""

    def test_risk_level_property(self, spec_dir):
        """Test risk_level property returns validation risk level."""
        classifier = RiskClassifier()
        assessment = classifier.load_assessment(spec_dir)
        assert assessment.risk_level == assessment.validation.risk_level


class TestInferValidationRecommendations:
    """Tests for _infer_validation_recommendations method."""

    def test_infers_from_risk_level(self, spec_dir_old_format):
        """Test infers recommendations from risk level."""
        classifier = RiskClassifier()
        assessment = classifier.load_assessment(spec_dir_old_format)
        # Old format has risk.level = "medium"
        assert assessment.validation.risk_level == "medium"
        # Should infer test types
        assert len(assessment.validation.test_types_required) > 0

    def test_infers_security_from_concerns(self, temp_dir):
        """Test infers security scan from concerns."""
        spec_path = temp_dir / "specs" / "infer-security"
        spec_path.mkdir(parents=True)
        data = {
            "complexity": "standard",
            "workflow_type": "feature",
            "confidence": 0.7,
            "reasoning": "",
            "analysis": {
                "scope": {"estimated_files": 5, "estimated_services": 1, "is_cross_cutting": False, "notes": ""},
                "integrations": {"external_services": [], "new_dependencies": [], "research_needed": False, "notes": ""},
                "infrastructure": {"docker_changes": False, "database_changes": False, "config_changes": False, "notes": ""},
                "knowledge": {"patterns_exist": True, "research_required": False, "unfamiliar_tech": [], "notes": ""},
                "risk": {"level": "medium", "concerns": ["API key exposure risk"], "notes": ""}
            },
            "recommended_phases": [],
            "flags": {"needs_research": False, "needs_self_critique": False, "needs_infrastructure_setup": False}
        }
        (spec_path / "complexity_assessment.json").write_text(json.dumps(data))

        classifier = RiskClassifier()
        assessment = classifier.load_assessment(spec_path)
        # Should infer security scan needed due to API key concern
        assert assessment.validation.security_scan_required is True

    def test_infers_staging_from_database(self, temp_dir):
        """Test infers staging deployment from database changes."""
        spec_path = temp_dir / "specs" / "infer-staging"
        spec_path.mkdir(parents=True)
        data = {
            "complexity": "standard",
            "workflow_type": "feature",
            "confidence": 0.7,
            "reasoning": "",
            "analysis": {
                "scope": {"estimated_files": 5, "estimated_services": 1, "is_cross_cutting": False, "notes": ""},
                "integrations": {"external_services": [], "new_dependencies": [], "research_needed": False, "notes": ""},
                "infrastructure": {"docker_changes": False, "database_changes": True, "config_changes": False, "notes": ""},
                "knowledge": {"patterns_exist": True, "research_required": False, "unfamiliar_tech": [], "notes": ""},
                "risk": {"level": "medium", "concerns": [], "notes": ""}
            },
            "recommended_phases": [],
            "flags": {"needs_research": False, "needs_self_critique": False, "needs_infrastructure_setup": False}
        }
        (spec_path / "complexity_assessment.json").write_text(json.dumps(data))

        classifier = RiskClassifier()
        assessment = classifier.load_assessment(spec_path)
        # Should infer staging needed due to database changes
        assert assessment.validation.staging_deployment_required is True
