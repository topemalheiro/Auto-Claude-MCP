"""Tests for cost_estimator"""

from runners.ai_analyzer.cost_estimator import CostEstimator
from runners.ai_analyzer.models import CostEstimate
from pathlib import Path
import pytest


def test_CostEstimator___init__():
    """Test CostEstimator.__init__"""
    # Arrange
    project_dir = Path("/tmp/test")
    project_index = {"services": {}}

    # Act
    instance = CostEstimator(project_dir, project_index)

    # Assert
    assert instance is not None
    assert instance.project_dir == project_dir
    assert instance.project_index == project_index


def test_CostEstimator_estimate_cost_empty_services():
    """Test CostEstimator.estimate_cost with empty services"""
    # Arrange
    project_dir = Path("/tmp/test")
    project_index = {"services": {}}
    instance = CostEstimator(project_dir, project_index)

    # Act
    result = instance.estimate_cost()

    # Assert
    assert result is not None
    assert isinstance(result, CostEstimate)
    assert result.estimated_tokens == 0
    assert result.estimated_cost_usd == 0.0
    assert result.files_to_analyze == 0
    assert result.routes_count == 0
    assert result.models_count == 0


def test_CostEstimator_estimate_cost_with_services():
    """Test CostEstimator.estimate_cost with services"""
    # Arrange
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test Python file
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text("print('test')")

        project_dir = Path(tmpdir)
        project_index = {
            "services": {
                "test_service": {
                    "api": {"total_routes": 10},
                    "database": {"total_models": 5},
                }
            }
        }
        instance = CostEstimator(project_dir, project_index)

        # Act
        result = instance.estimate_cost()

        # Assert
        assert result is not None
        assert isinstance(result, CostEstimate)
        assert result.estimated_tokens > 0
        assert result.estimated_cost_usd > 0
        assert result.files_to_analyze >= 1
        assert result.routes_count == 10
        assert result.models_count == 5
