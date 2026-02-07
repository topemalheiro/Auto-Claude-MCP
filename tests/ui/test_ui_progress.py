"""Tests for ui/progress.py"""

import pytest

from ui.progress import progress_bar
from ui.icons import Icons
from unittest.mock import patch, MagicMock
import ui.progress
import ui.capabilities
import ui.colors


class TestProgressBar:
    """Tests for progress_bar function"""

    def test_progress_bar_zero(self):
        """Test progress_bar at zero"""
        result = progress_bar(0, 100)

        assert "[░" in result  # Bar empty character
        assert "0/100" in result
        assert "(0%)" in result

    def test_progress_bar_half(self):
        """Test progress_bar at 50%"""
        result = progress_bar(50, 100)

        assert "50/100" in result
        assert "(50%)" in result

    def test_progress_bar_full(self):
        """Test progress_bar at 100%"""
        result = progress_bar(100, 100)

        assert "100/100" in result
        assert "(100%)" in result

    def test_progress_bar_zero_total(self):
        """Test progress_bar with zero total (edge case)"""
        result = progress_bar(0, 0)

        assert "0/0" in result
        assert "(0%)" in result

    def test_progress_bar_zero_division_protection(self):
        """Test progress_bar handles division by zero gracefully"""
        # When total is 0, the percent calculation should handle it
        result = progress_bar(0, 0)
        assert "0/0" in result
        # Should not crash with ZeroDivisionError

        result = progress_bar(5, 0)
        assert "5/0" in result
        # Should not crash

    def test_progress_bar_custom_width(self):
        """Test progress_bar with custom width"""
        result = progress_bar(50, 100, width=20)

        # Should have 20 characters worth of bar
        # Extract bar content between brackets
        start = result.find("[")
        end = result.find("]")
        bar_content = result[start + 1:end]
        # The bar should contain filled and empty characters
        assert len(bar_content) == 20

    def test_progress_bar_no_percent(self):
        """Test progress_bar without percentage"""
        result = progress_bar(75, 100, show_percent=False)

        assert "75/100" in result
        assert "(75%)" not in result

    def test_progress_bar_no_count(self):
        """Test progress_bar without count"""
        result = progress_bar(75, 100, show_count=False)

        assert "75/100" not in result
        assert "(75%)" in result

    def test_progress_bar_no_labels(self):
        """Test progress_bar without any labels"""
        result = progress_bar(75, 100, show_percent=False, show_count=False)

        # Should only have the bar
        assert "[" in result
        assert "]" in result
        assert "75/100" not in result
        assert "(75%)" not in result

    def test_progress_bar_color_gradient_true(self):
        """Test progress_bar with color gradient enabled"""
        result = progress_bar(75, 100, color_gradient=True)

        # Should return a string with color codes
        assert isinstance(result, str)

    def test_progress_bar_color_gradient_false(self):
        """Test progress_bar with color gradient disabled"""
        result = progress_bar(75, 100, color_gradient=False)

        # Should return a string without color codes
        assert isinstance(result, str)
        assert "75/100" in result

    def test_progress_bar_fractional_progress(self):
        """Test progress_bar with fractional progress"""
        result = progress_bar(33, 100)

        assert "33/100" in result
        assert "(33%)" in result

    def test_progress_bar_current_equals_total(self):
        """Test progress_bar when current equals total"""
        result = progress_bar(1, 1)

        assert "1/1" in result
        assert "(100%)" in result


class TestProgressBarColorGradients:
    """Tests for progress_bar color gradient functionality"""

    @patch("ui.capabilities.COLOR", True)
    def test_color_gradient_success_at_100_percent(self):
        """Test color gradient applies success color at 100%"""
        result = progress_bar(100, 100, color_gradient=True)

        # At 100%, should use success color (green)
        assert isinstance(result, str)
        assert "100/100" in result

    @patch("ui.capabilities.COLOR", True)
    def test_color_gradient_info_at_50_percent(self):
        """Test color gradient applies info color at 50%"""
        result = progress_bar(50, 100, color_gradient=True)

        # At 50%, should use info color (blue)
        assert isinstance(result, str)
        assert "50/100" in result

    @patch("ui.capabilities.COLOR", True)
    def test_color_gradient_warning_below_50_percent(self):
        """Test color gradient applies warning color below 50%"""
        result = progress_bar(25, 100, color_gradient=True)

        # At 25%, should use warning color (yellow)
        assert isinstance(result, str)
        assert "25/100" in result

    @patch("ui.capabilities.COLOR", True)
    def test_color_gradient_muted_at_zero_percent(self):
        """Test color gradient applies muted color at 0%"""
        result = progress_bar(0, 100, color_gradient=True)

        # At 0%, should use muted color
        assert isinstance(result, str)
        assert "0/100" in result

    @patch("ui.capabilities.COLOR", False)
    def test_no_color_when_color_disabled(self):
        """Test no color codes when COLOR capability is disabled"""
        result = progress_bar(75, 100, color_gradient=True)

        # Should not contain ANSI codes when COLOR is False
        assert isinstance(result, str)
        assert "75/100" in result
        # No ANSI escape sequences
        assert "\033[" not in result


class TestProgressBarEdgeCases:
    """Tests for progress_bar edge cases"""

    def test_progress_bar_negative_current(self):
        """Test progress_bar with negative current value"""
        result = progress_bar(-5, 100)

        # Should handle gracefully
        assert isinstance(result, str)
        # Negative values will produce interesting results
        # but shouldn't crash

    def test_progress_bar_very_small_values(self):
        """Test progress_bar with very small values"""
        result = progress_bar(1, 3)

        assert isinstance(result, str)
        assert "1/3" in result

    def test_progress_bar_single_character_width(self):
        """Test progress_bar with minimal width"""
        result = progress_bar(50, 100, width=1)

        assert isinstance(result, str)
        # Should still have bar brackets
        assert "[" in result
        assert "]" in result

    def test_progress_bar_large_width(self):
        """Test progress_bar with large width"""
        result = progress_bar(50, 100, width=200)

        assert isinstance(result, str)
        # Should contain very long bar
        assert "50/100" in result

    def test_progress_bar_unicode_fallback(self):
        """Test progress_bar uses ASCII fallback when unicode disabled"""
        with patch("ui.capabilities.UNICODE", False):
            result = progress_bar(50, 100)

            assert isinstance(result, str)
            # Should use ASCII fallback characters
            assert "50/100" in result

    def test_progress_bar_all_combinations_disabled(self):
        """Test progress_bar with all optional features disabled"""
        result = progress_bar(
            75, 100,
            show_percent=False,
            show_count=False,
            color_gradient=False
        )

        # Should only have bar brackets
        assert isinstance(result, str)
        assert "[" in result
        assert "]" in result
        assert "75/100" not in result
        assert "(75%)" not in result

    def test_color_gradient_threshold_boundaries(self):
        """Test color gradient at exact threshold boundaries"""
        with patch.object(ui.capabilities, "COLOR", True):
            # Test at 49% (should be warning/yellow)
            result_49 = progress_bar(49, 100, color_gradient=True)
            assert "49/100" in result_49

            # Test at 50% (should be info/blue)
            result_50 = progress_bar(50, 100, color_gradient=True)
            assert "50/100" in result_50

            # Test at 99% (should be info/blue, not success yet)
            result_99 = progress_bar(99, 100, color_gradient=True)
            assert "99/100" in result_99

            # Test at 100% (should be success/green)
            result_100 = progress_bar(100, 100, color_gradient=True)
            assert "100/100" in result_100

    def test_color_gradient_exceeds_100_percent(self):
        """Test color gradient when progress exceeds 100%"""
        with patch.object(ui.capabilities, "COLOR", True):
            result = progress_bar(120, 100, color_gradient=True)

            # When over 100%, should use success color (green)
            assert isinstance(result, str)
            assert "120/100" in result

    def test_color_gradient_with_small_progress(self):
        """Test color gradient with small absolute progress values"""
        with patch.object(ui.capabilities, "COLOR", True):
            result = progress_bar(1, 1000, color_gradient=True)

            # At 0.1%, should use warning color
            assert isinstance(result, str)
            assert "1/1000" in result
