"""Tests for models"""

from runners.ai_analyzer.models import AnalysisResult, AnalyzerType
import pytest


def test_AnalyzerType_all_analyzers():
    """Test AnalyzerType.all_analyzers"""
    # Act
    result = AnalyzerType.all_analyzers()

    # Assert
    assert result is not None
    assert isinstance(result, list)
    assert len(result) == 6
    assert "code_relationships" in result
    assert "business_logic" in result
    assert "architecture" in result
    assert "security" in result
    assert "performance" in result
    assert "code_quality" in result


def test_AnalysisResult_to_dict():
    """Test AnalysisResult.to_dict"""
    # Arrange
    instance = AnalysisResult(
        analysis_timestamp="2024-01-01T00:00:00",
        project_dir="/tmp/test",
        cost_estimate={"estimated_tokens": 1000, "estimated_cost_usd": 0.01},
        overall_score=85,
        analyzers={"code_relationships": {"score": 90}},
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result is not None
    assert isinstance(result, dict)
    assert result["analysis_timestamp"] == "2024-01-01T00:00:00"
    assert result["project_dir"] == "/tmp/test"
    assert result["overall_score"] == 85
    assert result["cost_estimate"]["estimated_tokens"] == 1000
    assert "code_relationships" in result
