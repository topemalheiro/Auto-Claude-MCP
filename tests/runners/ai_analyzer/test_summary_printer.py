"""Tests for summary_printer"""

from runners.ai_analyzer.summary_printer import SummaryPrinter
import pytest


def test_SummaryPrinter_print_summary():
    """Test SummaryPrinter.print_summary"""
    # Arrange
    insights = {
        "overall_score": 85,
        "analysis_timestamp": "2024-01-01T00:00:00",
        "code_relationships": {"score": 90},
        "business_logic": {"score": 80},
        "architecture": {"score": 85},
        "security": {"vulnerabilities": [{"type": "SQL Injection", "severity": "high"}]},
        "performance": {"bottlenecks": [{"type": "N+1 Query", "location": "posts.py:120"}]},
        "code_quality": {"score": 75},
    }

    # Act - Should not raise exception
    SummaryPrinter.print_summary(insights)

    # Assert - No exception raised is success
    assert True


def test_SummaryPrinter_print_summary_with_error():
    """Test SummaryPrinter.print_summary with error"""
    # Arrange
    insights = {"error": "Claude SDK not installed"}

    # Act - Should not raise exception
    SummaryPrinter.print_summary(insights)

    # Assert - No exception raised is success
    assert True


def test_SummaryPrinter_print_cost_estimate():
    """Test SummaryPrinter.print_cost_estimate"""
    # Arrange
    cost_estimate = {
        "estimated_tokens": 10000,
        "estimated_cost_usd": 0.09,
        "files_to_analyze": 50,
    }

    # Act - Should not raise exception
    SummaryPrinter.print_cost_estimate(cost_estimate)

    # Assert - No exception raised is success
    assert True
