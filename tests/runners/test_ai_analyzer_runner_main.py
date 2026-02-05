"""Tests for ai_analyzer_runner"""

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_main(tmp_path):
    """Test main with proper arguments and mocked AIAnalyzerRunner"""

    # Arrange - Create test index file
    index_path = tmp_path / "comprehensive_analysis.json"
    index_path.write_text('{"test": "data"}', encoding="utf-8")

    # Mock sys.argv
    original_argv = sys.argv
    sys.argv = ['ai_analyzer_runner.py', '--project-dir', str(tmp_path)]

    # Create async function that returns empty list
    async def mock_run_full_analysis(*args, **kwargs):
        return []

    # Create mock for AIAnalyzerRunner
    mock_analyzer = MagicMock()
    mock_analyzer.run_full_analysis = mock_run_full_analysis
    mock_analyzer.print_summary = MagicMock()

    try:
        # Mock the ai_analyzer module import
        with patch.dict('sys.modules', {'ai_analyzer': MagicMock(AIAnalyzerRunner=MagicMock(return_value=mock_analyzer))}):
            from runners.ai_analyzer_runner import main

            # Act
            result = main()

            # Assert
            assert result == 0  # Success exit code
            mock_analyzer.print_summary.assert_called_once()
    finally:
        sys.argv = original_argv


def test_main_with_empty_inputs(tmp_path):
    """Test main with empty inputs (missing index file)"""

    # Arrange - Use empty directory (no index file)
    original_argv = sys.argv
    sys.argv = ['ai_analyzer_runner.py', '--project-dir', str(tmp_path)]

    try:
        from runners.ai_analyzer_runner import main

        # Act
        result = main()

        # Assert - Should return error code since index file doesn't exist
        assert result == 1
    finally:
        sys.argv = original_argv


def test_main_with_invalid_input(tmp_path):
    """Test main with invalid input"""

    # Arrange - Create invalid JSON file
    index_path = tmp_path / "comprehensive_analysis.json"
    index_path.write_text('invalid json content', encoding="utf-8")

    original_argv = sys.argv
    sys.argv = ['ai_analyzer_runner.py', '--project-dir', str(tmp_path)]

    try:
        from runners.ai_analyzer_runner import main

        # Act & Assert - Should handle JSON parse error
        # May raise exception or return error code
        with pytest.raises((json.JSONDecodeError, Exception)):
            main()
    finally:
        sys.argv = original_argv


def test_main_with_import_error(tmp_path):
    """Test main when AIAnalyzerRunner import fails"""

    # Arrange - Create test index file
    index_path = tmp_path / "comprehensive_analysis.json"
    index_path.write_text('{"test": "data"}', encoding="utf-8")

    original_argv = sys.argv
    sys.argv = ['ai_analyzer_runner.py', '--project-dir', str(tmp_path)]

    try:
        # Mock import to raise ImportError
        with patch.dict('sys.modules', {'ai_analyzer': None}):
            # Delete the module if it exists
            import runners.ai_analyzer_runner
            # Force reimport
            import importlib
            importlib.reload(runners.ai_analyzer_runner)

            from runners.ai_analyzer_runner import main

            # Act
            result = main()

            # Assert - Should return error code
            assert result == 1
    finally:
        sys.argv = original_argv
