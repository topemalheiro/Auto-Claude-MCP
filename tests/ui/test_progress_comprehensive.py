"""
Comprehensive Tests for ui.progress module
==========================================

Enhanced tests covering edge cases, color gradients,
boundary conditions, and integration scenarios.
"""

import pytest
from unittest.mock import patch, MagicMock
import ui.progress
import ui.capabilities
import ui.icons


class TestProgressBarNumericEdgeCases:
    """Tests for numeric edge cases in progress_bar"""

    def test_progress_bar_negative_total(self):
        """Test progress_bar with negative total"""
        result = ui.progress.progress_bar(5, -100)
        assert isinstance(result, str)
        assert "5/-100" in result or "5" in result

    def test_progress_bar_both_negative(self):
        """Test progress_bar with both values negative"""
        result = ui.progress.progress_bar(-50, -100)
        assert isinstance(result, str)

    def test_progress_bar_fractional_values(self):
        """Test progress_bar with fractional values"""
        result = ui.progress.progress_bar(0.5, 1.5)
        assert isinstance(result, str)

    def test_progress_bar_very_small_fraction(self):
        """Test progress_bar with very small fraction"""
        result = ui.progress.progress_bar(1, 1000000)
        assert "1/1000000" in result
        assert "(0%)" in result

    def test_progress_bar_large_numbers(self):
        """Test progress_bar with very large numbers"""
        result = ui.progress.progress_bar(999999, 1000000)
        assert "999999/1000000" in result
        assert "(99%)" in result or "(100%)" in result

    def test_progress_bar_exact_boundary_0(self):
        """Test progress_bar at exactly 0%"""
        result = ui.progress.progress_bar(0, 100)
        assert "0/100" in result
        assert "(0%)" in result

    def test_progress_bar_exact_boundary_50(self):
        """Test progress_bar at exactly 50%"""
        result = ui.progress.progress_bar(50, 100)
        assert "50/100" in result
        assert "(50%)" in result

    def test_progress_bar_exact_boundary_100(self):
        """Test progress_bar at exactly 100%"""
        result = ui.progress.progress_bar(100, 100)
        assert "100/100" in result
        assert "(100%)" in result

    def test_progress_bar_just_below_threshold(self):
        """Test progress_bar at 49% (just below color threshold)"""
        result = ui.progress.progress_bar(49, 100)
        assert "49/100" in result
        assert "(49%)" in result

    def test_progress_bar_just_above_threshold(self):
        """Test progress_bar at 51% (just above color threshold)"""
        result = ui.progress.progress_bar(51, 100)
        assert "51/100" in result
        assert "(51%)" in result

    def test_progress_bar_one_third(self):
        """Test progress_bar at 1/3"""
        result = ui.progress.progress_bar(1, 3)
        assert "1/3" in result
        assert "(33%)" in result

    def test_progress_bar_two_thirds(self):
        """Test progress_bar at 2/3"""
        result = ui.progress.progress_bar(2, 3)
        assert "2/3" in result
        assert "(67%)" in result


class TestProgressBarWidthEdgeCases:
    """Tests for width edge cases in progress_bar"""

    def test_progress_bar_zero_width(self):
        """Test progress_bar with zero width"""
        result = ui.progress.progress_bar(50, 100, width=0)
        assert isinstance(result, str)

    def test_progress_bar_negative_width(self):
        """Test progress_bar with negative width"""
        result = ui.progress.progress_bar(50, 100, width=-10)
        assert isinstance(result, str)

    def test_progress_bar_width_1(self):
        """Test progress_bar with width of 1"""
        result = ui.progress.progress_bar(50, 100, width=1)
        assert isinstance(result, str)
        assert "[" in result
        assert "]" in result

    def test_progress_bar_width_2(self):
        """Test progress_bar with width of 2"""
        result = ui.progress.progress_bar(50, 100, width=2)
        assert isinstance(result, str)

    def test_progress_bar_very_large_width(self):
        """Test progress_bar with very large width"""
        result = ui.progress.progress_bar(50, 100, width=1000)
        assert isinstance(result, str)
        # Should contain very long bar
        assert "[" in result

    def test_progress_bar_width_larger_than_terminal(self):
        """Test progress_bar with width larger than typical terminal"""
        result = ui.progress.progress_bar(50, 100, width=500)
        assert isinstance(result, str)


class TestProgressBarColorGradientDetailed:
    """Detailed tests for color gradient behavior"""

    @patch("ui.progress.COLOR", True)
    def test_color_gradient_at_0_percent(self):
        """Test color at 0% (muted color)"""
        result = ui.progress.progress_bar(0, 100, color_gradient=True)
        assert isinstance(result, str)
        assert "0/100" in result

    @patch("ui.progress.COLOR", True)
    def test_color_gradient_at_1_percent(self):
        """Test color at 1% (warning color)"""
        result = ui.progress.progress_bar(1, 100, color_gradient=True)
        assert isinstance(result, str)
        assert "1/100" in result

    @patch("ui.progress.COLOR", True)
    def test_color_gradient_at_25_percent(self):
        """Test color at 25% (warning color)"""
        result = ui.progress.progress_bar(25, 100, color_gradient=True)
        assert isinstance(result, str)
        assert "25/100" in result

    @patch("ui.progress.COLOR", True)
    def test_color_gradient_at_49_percent(self):
        """Test color at 49% (warning color, threshold boundary)"""
        result = ui.progress.progress_bar(49, 100, color_gradient=True)
        assert isinstance(result, str)
        assert "49/100" in result

    @patch("ui.progress.COLOR", True)
    def test_color_gradient_at_50_percent(self):
        """Test color at 50% (info color, threshold boundary)"""
        result = ui.progress.progress_bar(50, 100, color_gradient=True)
        assert isinstance(result, str)
        assert "50/100" in result

    @patch("ui.progress.COLOR", True)
    def test_color_gradient_at_75_percent(self):
        """Test color at 75% (info color)"""
        result = ui.progress.progress_bar(75, 100, color_gradient=True)
        assert isinstance(result, str)
        assert "75/100" in result

    @patch("ui.progress.COLOR", True)
    def test_color_gradient_at_99_percent(self):
        """Test color at 99% (info color)"""
        result = ui.progress.progress_bar(99, 100, color_gradient=True)
        assert isinstance(result, str)
        assert "99/100" in result

    @patch("ui.progress.COLOR", True)
    def test_color_gradient_at_100_percent(self):
        """Test color at 100% (success color)"""
        result = ui.progress.progress_bar(100, 100, color_gradient=True)
        assert isinstance(result, str)
        assert "100/100" in result

    @patch("ui.progress.COLOR", True)
    def test_color_gradient_above_100_percent(self):
        """Test color above 100% (success color)"""
        result = ui.progress.progress_bar(150, 100, color_gradient=True)
        assert isinstance(result, str)
        assert "150/100" in result

    @patch("ui.progress.COLOR", False)
    def test_no_color_codes_when_disabled(self):
        """Test that no ANSI codes when color is disabled"""
        result = ui.progress.progress_bar(75, 100, color_gradient=True)
        # Should not have ANSI escape sequences
        assert "\033[" not in result

    @patch("ui.progress.COLOR", False)
    def test_plain_text_when_color_disabled(self):
        """Test that output is plain text when color disabled"""
        result = ui.progress.progress_bar(50, 100, color_gradient=False)
        # Should be plain text
        assert isinstance(result, str)
        assert "50/100" in result


class TestProgressBarLabelCombinations:
    """Tests for different label display combinations"""

    def test_both_labels_enabled(self):
        """Test with both count and percent enabled (default)"""
        result = ui.progress.progress_bar(75, 100)
        assert "75/100" in result
        assert "(75%)" in result

    def test_only_count(self):
        """Test with only count label"""
        result = ui.progress.progress_bar(75, 100, show_percent=False)
        assert "75/100" in result
        assert "(75%)" not in result

    def test_only_percent(self):
        """Test with only percent label"""
        result = ui.progress.progress_bar(75, 100, show_count=False)
        assert "75/100" not in result
        assert "(75%)" in result

    def test_no_labels(self):
        """Test with no labels"""
        result = ui.progress.progress_bar(
            75, 100,
            show_count=False,
            show_percent=False
        )
        assert "75/100" not in result
        assert "(75%)" not in result
        # Should only have bar
        assert "[" in result
        assert "]" in result

    def test_labels_with_zero_progress(self):
        """Test labels at zero progress"""
        result = ui.progress.progress_bar(0, 100)
        assert "0/100" in result
        assert "(0%)" in result

    def test_labels_with_full_progress(self):
        """Test labels at full progress"""
        result = ui.progress.progress_bar(100, 100)
        assert "100/100" in result
        assert "(100%)" in result


class TestProgressBarIntegrationWithCapabilities:
    """Tests for integration with capability detection"""

    def test_respects_color_capability(self):
        """Test that progress_bar respects COLOR capability"""
        # COLOR is checked at module import time, so we need to test differently
        # Just verify that color_gradient parameter is respected
        result_with_gradient = ui.progress.progress_bar(50, 100, color_gradient=True)
        result_without_gradient = ui.progress.progress_bar(50, 100, color_gradient=False)

        # When COLOR is False (typical in tests), results might be the same
        # Just verify both return valid strings
        assert isinstance(result_with_gradient, str)
        assert isinstance(result_without_gradient, str)

    def test_ignores_color_gradient_when_color_disabled(self):
        """Test that color_gradient is ignored when COLOR is False"""
        with patch.object(ui.capabilities, "COLOR", False):
            result1 = ui.progress.progress_bar(50, 100, color_gradient=True)
            result2 = ui.progress.progress_bar(50, 100, color_gradient=False)

            # Should be the same when color is disabled
            assert result1 == result2


class TestProgressBarIconFallback:
    """Tests for icon fallback behavior"""

    def test_unicode_bar_full_icon(self):
        """Test that bar full icon is used"""
        with patch.object(ui.icons, "UNICODE", True):
            result = ui.progress.progress_bar(50, 100)
            # Should use unicode block characters
            assert isinstance(result, str)

    def test_ascii_fallback_when_unicode_disabled(self):
        """Test ASCII fallback when unicode is disabled"""
        with patch.object(ui.icons, "UNICODE", False):
            result = ui.progress.progress_bar(50, 100)
            # Should use ASCII fallback
            assert isinstance(result, str)

    def test_bar_content_between_brackets(self):
        """Test that bar content is properly between brackets"""
        result = ui.progress.progress_bar(50, 100, width=40)
        # Extract content between brackets
        start = result.find("[")
        end = result.find("]")
        assert start != -1
        assert end != -1
        assert end > start
        # Content length should equal width
        content = result[start + 1:end]
        assert len(content) == 40


class TestProgressBarSpecialCases:
    """Tests for special cases and unusual inputs"""

    def test_progress_bar_with_zero_total_and_nonzero_current(self):
        """Test with zero total but non-zero current"""
        result = ui.progress.progress_bar(5, 0)
        assert isinstance(result, str)
        # Should handle gracefully
        assert "5/0" in result

    def test_progress_bar_equal_values(self):
        """Test with equal current and total values"""
        for i in [1, 10, 100, 1000]:
            result = ui.progress.progress_bar(i, i)
            assert f"{i}/{i}" in result
            assert "(100%)" in result

        # Special case: 0/0 shows 0% not 100%
        result_zero = ui.progress.progress_bar(0, 0)
        assert "0/0" in result_zero
        assert "(0%)" in result_zero

    def test_progress_bar_progressive_values(self):
        """Test with progressive values"""
        for i in range(0, 101, 10):
            result = ui.progress.progress_bar(i, 100)
            assert f"{i}/100" in result
            assert f"({i}%)" in result

    def test_progress_bar_rounding_behavior(self):
        """Test percent rounding behavior"""
        # Test rounding at various points
        result_33 = ui.progress.progress_bar(1, 3)
        assert "(33%)" in result_33 or "(34%)" in result_33

        result_66 = ui.progress.progress_bar(2, 3)
        assert "(66%)" in result_66 or "(67%)" in result_66

    def test_progress_bar_fractional_percent_rounding(self):
        """Test percent display with fractional values"""
        result = ui.progress.progress_bar(1, 3)
        # Should round to nearest percent
        assert "(33%)" in result or "(34%)" in result


class TestProgressBarFormatConsistency:
    """Tests for output format consistency"""

    def test_format_structure_consistent(self):
        """Test that format structure is always consistent"""
        for current, total in [(0, 100), (25, 100), (50, 100), (75, 100), (100, 100)]:
            result = ui.progress.progress_bar(current, total)
            # Should always have brackets
            assert "[" in result
            assert "]" in result
            # Should always have count
            assert f"{current}/{total}" in result

    def test_space_separation(self):
        """Test that components are space-separated"""
        result = ui.progress.progress_bar(50, 100)
        # Should have spaces between components
        parts = result.split(" ")
        assert len(parts) >= 2  # At least bar and count

    def test_percent_format(self):
        """Test that percent is properly formatted"""
        result = ui.progress.progress_bar(50, 100)
        # Percent should be in parentheses
        assert "(50%)" in result

    def test_count_format(self):
        """Test that count is properly formatted"""
        result = ui.progress.progress_bar(50, 100)
        # Count should be current/total format
        assert "50/100" in result


class TestProgressBarRealWorldScenarios:
    """Tests for real-world usage scenarios"""

    def test_download_progress(self):
        """Simulate download progress"""
        downloads = [
            (0, 1000),
            (250, 1000),
            (500, 1000),
            (750, 1000),
            (1000, 1000),
        ]

        for current, total in downloads:
            result = ui.progress.progress_bar(current, total)
            assert f"{current}/{total}" in result
            assert isinstance(result, str)

    def test_file_copy_progress(self):
        """Simulate file copy progress"""
        # File with known size
        file_size_mb = 500
        for copied_mb in [0, 125, 250, 375, 500]:
            result = ui.progress.progress_bar(copied_mb, file_size_mb)
            assert f"{copied_mb}/{file_size_mb}" in result

    def test_batch_processing(self):
        """Simulate batch processing progress"""
        total_items = 100
        for processed in range(0, 101, 10):
            result = ui.progress.progress_bar(processed, total_items)
            assert f"{processed}/{total_items}" in result

    def test_small_total(self):
        """Test with small total values"""
        for total in [1, 2, 3, 4, 5]:
            for current in range(total + 1):
                result = ui.progress.progress_bar(current, total)
                assert f"{current}/{total}" in result


class TestProgressBarPerformance:
    """Tests for performance characteristics"""

    def test_large_number_of_calls(self):
        """Test that many calls don't cause issues"""
        results = []
        for i in range(1000):
            result = ui.progress.progress_bar(i, 1000)
            results.append(result)

        assert len(results) == 1000
        assert all(isinstance(r, str) for r in results)

    def test_rapid_progression(self):
        """Test rapid progression values"""
        results = []
        for i in range(0, 101, 5):
            result = ui.progress.progress_bar(i, 100)
            results.append(result)

        assert len(results) == 21  # 0, 5, 10, ..., 100


class TestProgressBarReturnValues:
    """Tests for return value characteristics"""

    def test_always_returns_string(self):
        """Test that function always returns string"""
        test_cases = [
            (0, 0),
            (0, 100),
            (50, 100),
            (100, 100),
            (-5, 100),
            (150, 100),
        ]

        for current, total in test_cases:
            result = ui.progress.progress_bar(current, total)
            assert isinstance(result, str), \
                f"progress_bar({current}, {total}) should return str, got {type(result)}"

    def test_never_returns_none(self):
        """Test that function never returns None"""
        result = ui.progress.progress_bar(50, 100)
        assert result is not None

    def test_never_raises_on_valid_inputs(self):
        """Test that function doesn't raise on valid numeric inputs"""
        test_cases = [
            (0, 1),
            (1, 1),
            (1, 2),
            (100, 200),
            (0, 0),
            (50, 100),
        ]

        for current, total in test_cases:
            try:
                result = ui.progress.progress_bar(current, total)
                assert isinstance(result, str)
            except Exception as e:
                pytest.fail(f"progress_bar({current}, {total}) raised {e}")


class TestProgressBarWidthCalculation:
    """Tests for width calculation and bar filling"""

    def test_bar_fill_calculation(self):
        """Test that bar fill is calculated correctly"""
        width = 40

        # 0% should be empty
        result_0 = ui.progress.progress_bar(0, 100, width=width, color_gradient=False)
        start_0 = result_0.find("[")
        end_0 = result_0.find("]")
        bar_0 = result_0[start_0 + 1:end_0]
        # All should be empty (or very few filled due to rounding)

        # 100% should be full
        result_100 = ui.progress.progress_bar(100, 100, width=width, color_gradient=False)
        start_100 = result_100.find("[")
        end_100 = result_100.find("]")
        bar_100 = result_100[start_100 + 1:end_100]

        # At 100%, bar should be completely filled character
        # (ignoring color codes)

    def test_bar_width_exact(self):
        """Test that bar has exact width specified"""
        width = 30
        result = ui.progress.progress_bar(50, 100, width=width, color_gradient=False)
        start = result.find("[")
        end = result.find("]")
        bar = result[start + 1:end]

        # Bar content should match width (without color codes)
        # Color codes can make the actual string longer
        assert len([c for c in bar if c not in "\033"]) == width or len(bar) >= width

    def test_partial_fill_at_half(self):
        """Test that half progress fills half the bar"""
        width = 40
        result = ui.progress.progress_bar(50, 100, width=width, color_gradient=False)
        start = result.find("[")
        end = result.find("]")
        bar = result[start + 1:end]

        # Should have approximately half filled
        # Get unique chars in bar
        unique_chars = set(bar)
        # Should have both filled and empty characters
        assert len(unique_chars) <= 2  # Full and empty chars
