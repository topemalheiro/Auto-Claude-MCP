"""Tests for runner.py - AIAnalyzerRunner class"""

from runners.ai_analyzer.runner import AIAnalyzerRunner
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time


def test_AIAnalyzerRunner___init__():
    """Test AIAnalyzerRunner.__init__"""
    # Arrange
    project_dir = Path("/tmp/test")
    project_index = {"services": {}}

    # Act
    instance = AIAnalyzerRunner(project_dir, project_index)

    # Assert
    assert instance is not None
    assert instance.project_dir == project_dir
    assert instance.project_index == project_index
    assert instance.cache_manager is not None
    assert instance.cost_estimator is not None
    assert instance.result_parser is not None
    assert instance.summary_printer is not None


@pytest.mark.asyncio
async def test_AIAnalyzerRunner_run_full_analysis():
    """Test AIAnalyzerRunner.run_full_analysis"""
    # Arrange
    import tempfile
    from unittest.mock import patch, MagicMock

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        project_index = {"services": {}}
        skip_cache = True
        selected_analyzers = None
        instance = AIAnalyzerRunner(project_dir, project_index)

        # Mock Claude SDK to prevent actual API calls
        with patch("runners.ai_analyzer.runner.CLAUDE_SDK_AVAILABLE", False):
            # Act
            result = await instance.run_full_analysis(skip_cache, selected_analyzers)

            # Assert - Should return error dict when SDK is not available
            assert result is not None
            assert isinstance(result, dict)
            assert "error" in result


@pytest.mark.asyncio
async def test_AIAnalyzerRunner_run_full_analysis_with_cache():
    """Test AIAnalyzerRunner.run_full_analysis with cached result"""
    from unittest.mock import patch
    import tempfile
    import json

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        project_index = {"services": {}}
        instance = AIAnalyzerRunner(project_dir, project_index)

        # Create a cached result
        cached_data = {
            "analysis_timestamp": "2024-01-01T00:00:00",
            "project_dir": str(project_dir),
            "overall_score": 85,
        }
        cache_dir = project_dir / ".auto-claude" / "ai_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "ai_insights.json"
        cache_file.write_text(json.dumps(cached_data), encoding="utf-8")

        # Mock get_cached_result to return our cached data
        with patch.object(
            instance.cache_manager, "get_cached_result", return_value=cached_data
        ):
            # Act
            result = await instance.run_full_analysis(skip_cache=False)

            # Assert - Should return cached result
            assert result == cached_data


@pytest.mark.asyncio
async def test_AIAnalyzerRunner_run_full_analysis_with_selected_analyzers():
    """Test AIAnalyzerRunner.run_full_analysis with specific analyzers"""
    from unittest.mock import patch, AsyncMock
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        project_index = {
            "services": {
                "backend": {
                    "api": {"routes": [], "total_routes": 0},
                    "database": {"models": {}, "total_models": 0},
                }
            }
        }
        instance = AIAnalyzerRunner(project_dir, project_index)

        # Mock the SDK and dependencies
        with patch("runners.ai_analyzer.runner.CLAUDE_SDK_AVAILABLE", True):
            with patch.object(
                instance, "_run_single_analyzer", new=AsyncMock()
            ) as mock_run_analyzer:
                mock_run_analyzer.return_value = {"score": 75}

                # Act - run only security analyzer
                result = await instance.run_full_analysis(
                    skip_cache=True, selected_analyzers=["security"]
                )

                # Assert - Should have run only the security analyzer
                assert "overall_score" in result
                assert result["overall_score"] == 75
                mock_run_analyzer.assert_called_once_with("security")


@pytest.mark.asyncio
async def test_AIAnalyzerRunner_run_full_analysis_with_invalid_analyzer():
    """Test AIAnalyzerRunner.run_full_analysis handles invalid analyzer names"""
    from unittest.mock import patch, AsyncMock
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        project_index = {
            "services": {
                "backend": {
                    "api": {"routes": [], "total_routes": 0},
                    "database": {"models": {}, "total_models": 0},
                }
            }
        }
        instance = AIAnalyzerRunner(project_dir, project_index)

        # Mock the SDK and dependencies
        with patch("runners.ai_analyzer.runner.CLAUDE_SDK_AVAILABLE", True):
            with patch.object(
                instance, "_run_single_analyzer", new=AsyncMock()
            ) as mock_run_analyzer:
                mock_run_analyzer.return_value = {"score": 80}

                # Act - run with invalid analyzer name
                result = await instance.run_full_analysis(
                    skip_cache=True, selected_analyzers=["invalid_analyzer", "security"]
                )

                # Assert - Should skip invalid analyzer and run valid one
                assert "overall_score" in result
                # Should only call once for security (invalid skipped)
                assert mock_run_analyzer.call_count == 1


@pytest.mark.asyncio
async def test_AIAnalyzerRunner_run_full_analysis_analyzer_error_handling():
    """Test AIAnalyzerRunner.run_full_analysis handles analyzer errors"""
    from unittest.mock import patch, AsyncMock
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        project_index = {
            "services": {
                "backend": {
                    "api": {"routes": [], "total_routes": 0},
                    "database": {"models": {}, "total_models": 0},
                }
            }
        }
        instance = AIAnalyzerRunner(project_dir, project_index)

        # Mock the SDK and dependencies
        with patch("runners.ai_analyzer.runner.CLAUDE_SDK_AVAILABLE", True):
            with patch.object(
                instance, "_run_single_analyzer", new=AsyncMock()
            ) as mock_run_analyzer:
                # First analyzer succeeds, second fails
                mock_run_analyzer.side_effect = [
                    {"score": 80},
                    Exception("Analyzer error"),
                ]

                # Act
                result = await instance.run_full_analysis(skip_cache=True)

                # Assert - Should handle error gracefully
                assert "overall_score" in result
                # Error should be stored in result
                assert any("error" in str(v) for v in result.values() if isinstance(v, dict))


@pytest.mark.asyncio
async def test_AIAnalyzerRunner_print_summary():
    """Test AIAnalyzerRunner.print_summary"""
    # Arrange
    project_dir = Path("/tmp/test")
    project_index = {"services": {}}
    insights = {
        "overall_score": 85,
        "analysis_timestamp": "2024-01-01T00:00:00",
        "code_relationships": {"score": 90},
        "security": {"vulnerabilities": []},
        "performance": {"bottlenecks": []},
    }
    instance = AIAnalyzerRunner(project_dir, project_index)

    # Act - Should not raise exception
    instance.print_summary(insights)

    # Assert - No exception raised is success
    assert True


def test_AIAnalyzerRunner_get_analyzers_to_run_all():
    """Test _get_analyzers_to_run returns all analyzers when none specified"""
    project_dir = Path("/tmp/test")
    project_index = {"services": {}}
    instance = AIAnalyzerRunner(project_dir, project_index)

    # Act
    analyzers = instance._get_analyzers_to_run(None)

    # Assert - Should return all analyzers
    assert len(analyzers) == 6  # 6 built-in analyzers
    assert "code_relationships" in analyzers
    assert "security" in analyzers
    assert "performance" in analyzers


def test_AIAnalyzerRunner_get_analyzers_to_run_selected():
    """Test _get_analyzers_to_run with selected analyzers"""
    project_dir = Path("/tmp/test")
    project_index = {"services": {}}
    instance = AIAnalyzerRunner(project_dir, project_index)

    # Act
    analyzers = instance._get_analyzers_to_run(["security", "performance"])

    # Assert
    assert analyzers == ["security", "performance"]


def test_AIAnalyzerRunner_get_analyzers_to_run_with_invalid():
    """Test _get_analyzers_to_run filters out invalid analyzers"""
    project_dir = Path("/tmp/test")
    project_index = {"services": {}}
    instance = AIAnalyzerRunner(project_dir, project_index)

    # Act - mix of valid and invalid
    analyzers = instance._get_analyzers_to_run(
        ["security", "invalid_analyzer", "performance"]
    )

    # Assert - should skip invalid
    assert "security" in analyzers
    assert "performance" in analyzers
    assert "invalid_analyzer" not in analyzers
    assert len(analyzers) == 2


@pytest.mark.asyncio
async def test_AIAnalyzerRunner_run_single_analyzer():
    """Test _run_single_analyzer method"""
    from unittest.mock import patch, AsyncMock
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        project_index = {
            "services": {
                "backend": {
                    "api": {
                        "routes": [
                            {"methods": ["GET"], "path": "/api/users", "file": "users.py"}
                        ],
                        "total_routes": 1,
                    },
                    "database": {"models": {"User": {}}, "total_models": 1},
                }
            }
        }
        instance = AIAnalyzerRunner(project_dir, project_index)

        # Mock ClaudeAnalysisClient
        with patch(
            "runners.ai_analyzer.runner.ClaudeAnalysisClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.run_analysis_query = AsyncMock(return_value='{"score": 85}')
            mock_client_class.return_value = mock_client

            # Act
            result = await instance._run_single_analyzer("code_relationships")

            # Assert
            assert result is not None
            assert "score" in result


def test_AIAnalyzerRunner_calculate_overall_score():
    """Test _calculate_overall_score method"""
    project_dir = Path("/tmp/test")
    project_index = {"services": {}}
    instance = AIAnalyzerRunner(project_dir, project_index)

    analyzers_run = ["security", "performance", "code_quality"]
    insights = {
        "security": {"score": 80},
        "performance": {"score": 70},
        "code_quality": {"score": 90},
    }

    # Act
    score = instance._calculate_overall_score(analyzers_run, insights)

    # Assert - average of 80, 70, 90 = 240/3 = 80
    assert score == 80


def test_AIAnalyzerRunner_calculate_overall_score_with_errors():
    """Test _calculate_overall_score excludes analyzers with errors"""
    project_dir = Path("/tmp/test")
    project_index = {"services": {}}
    instance = AIAnalyzerRunner(project_dir, project_index)

    analyzers_run = ["security", "performance", "code_quality"]
    insights = {
        "security": {"score": 80},
        "performance": {"error": "Failed to analyze"},
        "code_quality": {"score": 90},
    }

    # Act - should only average security and code_quality
    score = instance._calculate_overall_score(analyzers_run, insights)

    # Assert - average of 80, 90 = 170/2 = 85
    assert score == 85


def test_AIAnalyzerRunner_calculate_overall_score_empty():
    """Test _calculate_overall_score with no valid scores"""
    project_dir = Path("/tmp/test")
    project_index = {"services": {}}
    instance = AIAnalyzerRunner(project_dir, project_index)

    analyzers_run = []
    insights = {}

    # Act
    score = instance._calculate_overall_score(analyzers_run, insights)

    # Assert - should return 0 for empty list
    assert score == 0


@pytest.mark.asyncio
async def test_AIAnalyzerRunner_run_analyzers():
    """Test _run_analyzers method"""
    from unittest.mock import AsyncMock
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        project_index = {"services": {}}
        instance = AIAnalyzerRunner(project_dir, project_index)

        # Mock _run_single_analyzer
        with patch.object(
            instance, "_run_single_analyzer", new=AsyncMock()
        ) as mock_run:
            mock_run.side_effect = [
                {"score": 80, "result": "security"},
                {"score": 75, "result": "performance"},
            ]

            insights = {}

            # Act
            await instance._run_analyzers(["security", "performance"], insights)

            # Assert
            assert "security" in insights
            assert "performance" in insights
            assert insights["security"]["score"] == 80
            assert insights["performance"]["score"] == 75
