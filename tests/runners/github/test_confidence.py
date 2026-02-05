"""Tests for confidence (deprecated module)"""

from runners.github.confidence import ConfidenceFactors, ConfidenceScorer, ScoredFinding, ConfidenceLevel, FalsePositiveRisk
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import warnings


def test_ConfidenceFactors_to_dict():
    """Test ConfidenceFactors.to_dict"""

    # Arrange
    factors = ConfidenceFactors(
        pattern_matches=5,
        pattern_accuracy=0.85,
        file_type_accuracy=0.90,
        category_accuracy=0.75,
        code_evidence_count=3,
        similar_findings_count=2,
        historical_sample_size=100,
        historical_accuracy=0.80,
        severity_weight=1.5
    )

    # Act
    result = factors.to_dict()

    # Assert
    assert result == {
        "pattern_matches": 5,
        "pattern_accuracy": 0.85,
        "file_type_accuracy": 0.90,
        "category_accuracy": 0.75,
        "code_evidence_count": 3,
        "similar_findings_count": 2,
        "historical_sample_size": 100,
        "historical_accuracy": 0.80,
        "severity_weight": 1.5,
    }


def test_ScoredFinding_to_dict():
    """Test ScoredFinding.to_dict"""

    # Arrange
    factors = ConfidenceFactors(pattern_matches=5, pattern_accuracy=0.85)
    finding = ScoredFinding(
        finding_id="test-123",
        original_finding={"type": "bug", "message": "Fix this"},
        confidence=85.0,
        confidence_level=ConfidenceLevel.HIGH,
        false_positive_risk=FalsePositiveRisk.LOW,
        factors=factors,
        evidence=["code line 1", "code line 2"],
        explanation_basis="Pattern matching"
    )

    # Act
    result = finding.to_dict()

    # Assert
    assert result["finding_id"] == "test-123"
    assert result["confidence"] == 85.0
    assert result["confidence_level"] == "high"
    assert result["false_positive_risk"] == "low"
    # Note: is_high_confidence and should_highlight are properties, not in to_dict()
    assert finding.is_high_confidence is True
    assert finding.should_highlight is True
    assert result["evidence"] == ["code line 1", "code line 2"]


def test_ScoredFinding_is_high_confidence():
    """Test ScoredFinding.is_high_confidence property"""

    # Arrange & Act
    high_conf = ScoredFinding(
        finding_id="high",
        original_finding={},
        confidence=80.0,
        confidence_level=ConfidenceLevel.HIGH,
        false_positive_risk=FalsePositiveRisk.LOW,
        factors=ConfidenceFactors()
    )

    low_conf = ScoredFinding(
        finding_id="low",
        original_finding={},
        confidence=50.0,
        confidence_level=ConfidenceLevel.MEDIUM,
        false_positive_risk=FalsePositiveRisk.MEDIUM,
        factors=ConfidenceFactors()
    )

    # Assert
    assert high_conf.is_high_confidence is True
    assert low_conf.is_high_confidence is False


def test_ScoredFinding_should_highlight():
    """Test ScoredFinding.should_highlight property"""

    # Arrange
    high_conf_low_risk = ScoredFinding(
        finding_id="good",
        original_finding={},
        confidence=80.0,
        confidence_level=ConfidenceLevel.HIGH,
        false_positive_risk=FalsePositiveRisk.LOW,
        factors=ConfidenceFactors()
    )

    high_conf_high_risk = ScoredFinding(
        finding_id="risky",
        original_finding={},
        confidence=80.0,
        confidence_level=ConfidenceLevel.HIGH,
        false_positive_risk=FalsePositiveRisk.HIGH,
        factors=ConfidenceFactors()
    )

    # Assert
    assert high_conf_low_risk.should_highlight is True
    assert high_conf_high_risk.should_highlight is False


def test_ConfidenceScorer___init__():
    """Test ConfidenceScorer.__init__"""

    # Arrange & Act (learning_tracker is optional, patterns is optional)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        scorer = ConfidenceScorer(learning_tracker=None, patterns=[])

    # Assert
    assert scorer.learning_tracker is None
    assert scorer.patterns == []


def test_ConfidenceScorer_score_finding():
    """Test ConfidenceScorer.score_finding"""

    # Arrange
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        scorer = ConfidenceScorer(learning_tracker=None, patterns=[])

        finding = {
            "type": "bug",
            "category": "security",
            "file_path": "app/auth.py",
            "message": "Missing input validation"
        }

        context = {
            "file_type": "python",
            "pr_number": 123
        }

        # Act
        result = scorer.score_finding(finding, context)

    # Assert
    assert result is not None
    assert isinstance(result, ScoredFinding)
    assert hasattr(result, "confidence")
    assert hasattr(result, "false_positive_risk")


def test_ConfidenceScorer_explain_confidence():
    """Test ConfidenceScorer.explain_confidence"""

    # Arrange
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        scorer = ConfidenceScorer(learning_tracker=None, patterns=[])

        factors = ConfidenceFactors(
            pattern_matches=3,
            pattern_accuracy=0.90,
            code_evidence_count=2
        )

        scored = ScoredFinding(
            finding_id="test",
            original_finding={"type": "bug"},
            confidence=85.0,
            confidence_level=ConfidenceLevel.HIGH,
            false_positive_risk=FalsePositiveRisk.LOW,
            factors=factors,
            explanation_basis="Strong pattern match"
        )

        # Act
        result = scorer.explain_confidence(scored)

    # Assert
    assert result is not None
    assert isinstance(result, str)


def test_ConfidenceScorer_filter_by_confidence():
    """Test ConfidenceScorer.filter_by_confidence"""

    # Arrange
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        scorer = ConfidenceScorer(learning_tracker=None, patterns=[])

        findings = [
            ScoredFinding(
                finding_id="high1",
                original_finding={},
                confidence=90.0,
                confidence_level=ConfidenceLevel.VERY_HIGH,
                false_positive_risk=FalsePositiveRisk.LOW,
                factors=ConfidenceFactors()
            ),
            ScoredFinding(
                finding_id="low1",
                original_finding={},
                confidence=40.0,
                confidence_level=ConfidenceLevel.LOW,
                false_positive_risk=FalsePositiveRisk.HIGH,
                factors=ConfidenceFactors()
            ),
            ScoredFinding(
                finding_id="high2",
                original_finding={},
                confidence=80.0,
                confidence_level=ConfidenceLevel.HIGH,
                false_positive_risk=FalsePositiveRisk.MEDIUM,
                factors=ConfidenceFactors()
            )
        ]

        # Act - filter by 75% confidence, exclude high FP risk
        result = scorer.filter_by_confidence(findings, min_confidence=0.75, exclude_high_fp_risk=True)

    # Assert
    assert len(result) == 2  # high1 and high2
    assert all(f.confidence >= 75.0 for f in result)


def test_ConfidenceScorer_get_summary():
    """Test ConfidenceScorer.get_summary"""

    # Arrange
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        scorer = ConfidenceScorer(learning_tracker=None, patterns=[])

        findings = [
            ScoredFinding(
                finding_id="f1",
                original_finding={"category": "security"},
                confidence=90.0,
                confidence_level=ConfidenceLevel.VERY_HIGH,
                false_positive_risk=FalsePositiveRisk.LOW,
                factors=ConfidenceFactors()
            ),
            ScoredFinding(
                finding_id="f2",
                original_finding={"category": "performance"},
                confidence=60.0,
                confidence_level=ConfidenceLevel.MEDIUM,
                false_positive_risk=FalsePositiveRisk.MEDIUM,
                factors=ConfidenceFactors()
            )
        ]

        # Act
        result = scorer.get_summary(findings)

    # Assert
    assert result["total"] == 2
    assert result["avg_confidence"] == 75.0
    assert result["by_level"] == {"very_high": 1, "medium": 1}
    assert result["by_risk"] == {"low": 1, "medium": 1}
    assert result["high_confidence_count"] == 1
